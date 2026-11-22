"""
agent/adapters/orchestrator/langgraph_adapter.py

Adapter que implementa o motor de orquestração do CTB Assist via LangGraph (`StateGraph`).
Evolui o fluxo linear anterior para um RAG Agêntico completo com:
- Guardrails de entrada e saída como nós do grafo
- Roteador central (`roteador_agente`) com catálogo de Skills
- Carregamento de Skills (`SKILL.md`) sob demanda
- Loop de RAG Agêntico (`reescrever_query` -> `buscar_documentos` -> `avaliar_evidencias`)
  com reformulação automática limitada por `MAX_RETRIEVAL_ATTEMPTS`
- Execução de ferramentas MCP (`executar_mcp`)
- Memória conversacional persistida por `thread_id` via Checkpointer (`MemorySaver`)
"""

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from loguru import logger

from agent.adapters.guardrails.default_guardrail_adapter import DefaultGuardrailAdapter
from agent.adapters.mcp.null_mcp_adapter import NullMCPAdapter
from agent.adapters.memory.in_memory_memory_adapter import (
    InMemoryConversationMemoryAdapter,
    SimpleSummarizerAdapter,
)
from agent.adapters.orchestrator.nodes import (
    AvaliarEvidenciasNode,
    BuscarDocumentosNode,
    CarregarSkillNode,
    ExecutarMCPNode,
    GerarRespostaNode,
    GuardrailEntradaNode,
    GuardrailSaidaNode,
    RecuperarMemoriaNode,
    ReescreverQueryNode,
    RoteadorAgenteNode,
    SalvarMemoriaNode,
)
from agent.adapters.orchestrator.state import AgenteState
from agent.adapters.skills.filesystem_skill_adapter import FileSystemSkillAdapter
from agent.config.configuration import settings
from agent.domain.entities.consulta import Consulta
from agent.domain.entities.resposta_ia import RespostaIA
from agent.domain.ports.driven.conversation_memory_port import ConversationMemoryPort
from agent.domain.ports.driven.guardrail_port import GuardrailPort
from agent.domain.ports.driven.llm_port import LLMPort
from agent.domain.ports.driven.mcp_tool_port import MCPToolPort
from agent.domain.ports.driven.reranker_port import RerankerPort
from agent.domain.ports.driven.skill_port import SkillPort
from agent.domain.ports.driven.summarizer_port import SummarizerPort
from agent.domain.ports.driven.vector_store_port import VectorStorePort
from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.topico import Topico


class LangGraphOrchestratorAdapter:
    """Orquestrador RAG Agêntico do CTB Assist construído com `StateGraph` + Checkpointer."""

    def __init__(
        self,
        llm: LLMPort,
        vector_store: VectorStorePort,
        reranker: RerankerPort,
        memory: ConversationMemoryPort | None = None,
        summarizer: SummarizerPort | None = None,
        skill_port: SkillPort | None = None,
        mcp_port: MCPToolPort | None = None,
        guardrail_port: GuardrailPort | None = None,
        checkpointer: Any | None = None,
        max_retrieval_attempts: int | None = None,
    ) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._reranker = reranker
        self._memory = memory or InMemoryConversationMemoryAdapter()
        self._summarizer = summarizer or SimpleSummarizerAdapter()
        self._skill_port = skill_port or FileSystemSkillAdapter()
        self._mcp_port = mcp_port or NullMCPAdapter()
        self._guardrail = guardrail_port or DefaultGuardrailAdapter()
        self._checkpointer = checkpointer if checkpointer is not None else MemorySaver()
        self._max_retrieval_attempts = (
            max_retrieval_attempts or settings.MAX_RETRIEVAL_ATTEMPTS
        )

        self._graph = self._build_graph()
        logger.debug("LangGraphOrchestratorAdapter (CTB Assist) compilado com checkpointer.")

    @property
    def graph(self):
        """Expõe o grafo compilado para inspeção, visualização Mermaid ou testes."""
        return self._graph

    async def executar(
        self,
        pergunta: str,
        topico_str: str = "transito_ctb",
        sessao_id: str = "default",
    ) -> RespostaIA:
        """Executa um turno completo do agente isolado por `thread_id` (`sessao_id`)."""
        topico = Topico(valor=topico_str)

        estado_inicial: AgenteState = {
            "messages": [HumanMessage(content=pergunta)],
            "consulta": Consulta(
                sessao_id=sessao_id,
                pergunta_original=pergunta,
                topico=topico,
                historico=HistoricoConversa(),
                resumo=None,
                pergunta_reescrita=None,
            ),
            "passos_agente": 0,
            "retrieval_attempts": 0,
            "query_atual": None,
            "filtro_documento": None,
            "feedback_avaliador": None,
            "evidencias_suficientes": False,
            "documentos_recuperados": [],
            "retrieved_docs": [],
            "loaded_skills": [],
            "skills_conteudo": {},
            "tool_results": [],
            "guardrail_bloqueado": False,
            "guardrail_motivo": None,
            "decisao_roteador": None,
        }

        config = {"configurable": {"thread_id": sessao_id}}
        estado_final = await self._graph.ainvoke(estado_inicial, config=config)
        return estado_final["resposta"]

    # ------------------------------------------------------------------
    # Construção explícita do StateGraph (Requisito 1)
    # ------------------------------------------------------------------

    def _build_graph(self):
        builder = StateGraph(AgenteState)

        builder.add_node("guardrail_entrada", GuardrailEntradaNode(self._guardrail))
        builder.add_node("recuperar_memoria", RecuperarMemoriaNode(self._memory))
        builder.add_node(
            "roteador_agente",
            RoteadorAgenteNode(
                llm=self._llm,
                skill_port=self._skill_port,
                mcp_port=self._mcp_port,
                max_tentativas_rag=self._max_retrieval_attempts,
            ),
        )
        builder.add_node("carregar_skill", CarregarSkillNode(self._skill_port))
        builder.add_node("reescrever_query", ReescreverQueryNode(self._llm))
        builder.add_node(
            "buscar_documentos",
            BuscarDocumentosNode(self._vector_store, self._reranker),
        )
        builder.add_node(
            "avaliar_evidencias",
            AvaliarEvidenciasNode(
                llm=self._llm,
                max_tentativas=self._max_retrieval_attempts,
            ),
        )
        builder.add_node("executar_mcp", ExecutarMCPNode(self._mcp_port))
        builder.add_node("gerar_resposta", GerarRespostaNode(self._llm))
        builder.add_node("guardrail_saida", GuardrailSaidaNode(self._guardrail))
        builder.add_node(
            "salvar_memoria", SalvarMemoriaNode(self._memory, self._summarizer)
        )

        # Fluxo de entrada -> guardrail -> memória -> roteador
        builder.add_edge(START, "guardrail_entrada")
        builder.add_conditional_edges(
            "guardrail_entrada",
            self._apos_guardrail_entrada,
            {
                "bloqueado": END,
                "permitido": "recuperar_memoria",
            },
        )
        builder.add_edge("recuperar_memoria", "roteador_agente")

        # Decisões do roteador
        builder.add_conditional_edges(
            "roteador_agente",
            self._rotear_acao,
            {
                "carregar_skill": "carregar_skill",
                "buscar_rag": "reescrever_query",
                "chamar_mcp": "executar_mcp",
                "gerar_resposta": "gerar_resposta",
            },
        )

        # Retorno de Skill e MCP ao roteador
        builder.add_edge("carregar_skill", "roteador_agente")
        builder.add_edge("executar_mcp", "roteador_agente")

        # Loop de RAG Agêntico com reformulação
        builder.add_edge("reescrever_query", "buscar_documentos")
        builder.add_edge("buscar_documentos", "avaliar_evidencias")
        builder.add_conditional_edges(
            "avaliar_evidencias",
            self._apos_avaliar_evidencias,
            {
                "reformular": "reescrever_query",
                "continuar": "roteador_agente",
            },
        )

        # Saída segura + persistência de memória
        builder.add_edge("gerar_resposta", "guardrail_saida")
        builder.add_edge("guardrail_saida", "salvar_memoria")
        builder.add_edge("salvar_memoria", END)

        return builder.compile(checkpointer=self._checkpointer)

    def _apos_guardrail_entrada(self, state: AgenteState) -> str:
        if state.get("guardrail_bloqueado"):
            return "bloqueado"
        return "permitido"

    def _rotear_acao(self, state: AgenteState) -> str:
        decisao = state.get("decisao_roteador")
        if decisao is None:
            return "gerar_resposta"
        return decisao.acao

    def _apos_avaliar_evidencias(self, state: AgenteState) -> str:
        suficientes = state.get("evidencias_suficientes", True)
        tentativas = state.get("retrieval_attempts", 0)
        if not suficientes and tentativas < self._max_retrieval_attempts:
            return "reformular"
        return "continuar"
