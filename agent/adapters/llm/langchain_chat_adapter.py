"""
agent/adapters/llm/langchain_chat_adapter.py

Adapter concreto que implementa LLMPort usando LangChain Expression Language (LCEL)
para todo o ciclo agêntico do CTB Assist:
- Roteamento (`decidir_proxima_acao`)
- Reescrita/reformulação de query (`reescrever_query`)
- Avaliação de suficiência de evidências (`avaliar_suficiencia_evidencias`)
- Geração fundamentada (`gerar_resposta`)
"""

from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from pydantic import BaseModel, Field

from agent.adapters.llm.prompts.base_prompt import PROMPT_SISTEMA
from agent.adapters.llm.prompts.evidence_evaluator_prompt import (
    EVIDENCE_EVALUATOR_PROMPT,
)
from agent.adapters.llm.prompts.query_rewrite_prompt import QUERY_REWRITE_PROMPT
from agent.adapters.llm.prompts.router_prompt import ROUTER_PROMPT
from agent.domain.dictionaries.jargoes import (
    JARGOES_TRANSITO_CTB,
    formatar_jargoes_para_prompt,
)
from agent.domain.ports.driven.llm_port import AvaliacaoEvidencias, DecisaoRoteador
from agent.domain.value_objects.historico_conversa import HistoricoConversa, Mensagem
from agent.domain.value_objects.resultado_geracao_llm import ResultadoGeracao
from agent.domain.value_objects.resumo_conversa import ResumoConversa
from agent.domain.value_objects.topico import Topico


class SchemaRespostaLLM(BaseModel):
    faltou_informacao: bool = Field(
        description="True se as evidências normativas não foram suficientes para responder com segurança."
    )
    conteudo: str = Field(
        description="Resposta fundamentada em português (PT-BR) com citações de artigos e normas."
    )


class SchemaDecisaoRoteador(BaseModel):
    acao: Literal["buscar_rag", "carregar_skill", "chamar_mcp", "gerar_resposta"] = (
        Field(description="Próxima ação a ser executada pelo grafo.")
    )
    justificativa: str = Field(description="Motivo objetivo da decisão tomada.")
    skill_nome: str | None = Field(
        default=None,
        description="Nome exato da skill do catálogo quando acao == 'carregar_skill'.",
    )
    query_busca: str | None = Field(
        default=None,
        description="Consulta sugerida quando acao == 'buscar_rag'.",
    )
    filtro_documento: Literal["CTB", "CONTRAN", "MBFT"] | None = Field(
        default=None,
        description="Filtro opcional de norma ('CTB', 'CONTRAN' ou 'MBFT').",
    )
    ferramenta_mcp: str | None = Field(
        default=None,
        description="Nome da ferramenta MCP quando acao == 'chamar_mcp'.",
    )
    argumentos_mcp: dict[str, Any] = Field(
        default_factory=dict,
        description="Argumentos JSON da ferramenta MCP quando acao == 'chamar_mcp'.",
    )


class SchemaAvaliacaoEvidencias(BaseModel):
    suficientes: bool = Field(
        description="True se as evidências já permitem responder com fundamentação."
    )
    justificativa: str = Field(
        description="Explicação curta do que foi encontrado ou do que ainda falta."
    )
    query_reformulada: str | None = Field(
        default=None,
        description="Nova query mais específica caso suficientes == False.",
    )
    filtro_documento: Literal["CTB", "CONTRAN", "MBFT"] | None = Field(
        default=None,
        description="Filtro opcional de documento para a nova busca.",
    )


class LangChainChatAdapter:
    """Implementação concreta do LLMPort usando LangChain."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

        self._rag_chain = PROMPT_SISTEMA | self._llm.with_structured_output(
            SchemaRespostaLLM
        )
        self._router_chain = ROUTER_PROMPT | self._llm.with_structured_output(
            SchemaDecisaoRoteador
        )
        self._evaluator_chain = (
            EVIDENCE_EVALUATOR_PROMPT
            | self._llm.with_structured_output(SchemaAvaliacaoEvidencias)
        )
        self._rewrite_chain = QUERY_REWRITE_PROMPT | self._llm | StrOutputParser()

        logger.debug("LangChainChatAdapter (CTB Assist) inicializado.")

    async def decidir_proxima_acao(
        self,
        pergunta: str,
        historico: HistoricoConversa,
        catalogo_skills: str,
        skills_carregadas: list[str],
        documentos_resumo: str,
        ferramentas_mcp_disponiveis: str,
        resultados_mcp_resumo: str,
        tentativas_rag: int,
        max_tentativas_rag: int,
    ) -> DecisaoRoteador:
        historico_lc = self._converter_historico(historico)
        res: SchemaDecisaoRoteador = await self._router_chain.ainvoke(
            {
                "catalogo_skills": catalogo_skills,
                "skills_carregadas": ", ".join(skills_carregadas) or "Nenhuma",
                "ferramentas_mcp": ferramentas_mcp_disponiveis
                or "Nenhuma ferramenta MCP conectada.",
                "documentos_resumo": documentos_resumo
                or "Nenhuma evidência recuperada ainda.",
                "resultados_mcp": resultados_mcp_resumo
                or "Nenhuma ferramenta MCP executada ainda.",
                "tentativas_rag": tentativas_rag,
                "max_tentativas_rag": max_tentativas_rag,
                "historico": historico_lc,
                "question": pergunta,
            }
        )
        return DecisaoRoteador(
            acao=res.acao,
            justificativa=res.justificativa,
            skill_nome=res.skill_nome,
            query_busca=res.query_busca,
            filtro_documento=res.filtro_documento,
            ferramenta_mcp=res.ferramenta_mcp,
            argumentos_mcp=res.argumentos_mcp,
        )

    async def reescrever_query(
        self,
        pergunta: str,
        topico: Topico,
        historico: HistoricoConversa,
        feedback_anterior: str | None = None,
    ) -> str:
        historico_lc = self._converter_historico(historico)
        resultado = await self._rewrite_chain.ainvoke(
            {
                "topico": topico.valor,
                "historico": historico_lc,
                "question": pergunta,
                "vocabulario_tecnico": formatar_jargoes_para_prompt(
                    JARGOES_TRANSITO_CTB
                ),
                "feedback_anterior": feedback_anterior
                or "Primeira tentativa de busca.",
            }
        )
        return resultado.strip()

    async def avaliar_suficiencia_evidencias(
        self,
        pergunta: str,
        query_atual: str,
        evidencias_texto: str,
        tentativa_atual: int,
        max_tentativas: int,
    ) -> AvaliacaoEvidencias:
        res: SchemaAvaliacaoEvidencias = await self._evaluator_chain.ainvoke(
            {
                "question": pergunta,
                "query_atual": query_atual,
                "evidencias": evidencias_texto or "Nenhum trecho retornado.",
                "tentativa_atual": tentativa_atual,
                "max_tentativas": max_tentativas,
            }
        )
        return AvaliacaoEvidencias(
            suficientes=res.suficientes,
            justificativa=res.justificativa,
            query_reformulada=res.query_reformulada,
            filtro_documento=res.filtro_documento,
        )

    async def gerar_resposta(
        self,
        contexto: str,
        pergunta: str,
        topico: Topico,
        historico: HistoricoConversa,
        resumo: ResumoConversa | None,
        skills_ativas: str = "",
        resultados_mcp: str = "",
    ) -> ResultadoGeracao:
        historico_lc = self._converter_historico(historico)
        texto_resumo = (
            resumo.conteudo if resumo else "Nenhum resumo de conversa anterior."
        )

        resultado: SchemaRespostaLLM = await self._rag_chain.ainvoke(
            {
                "skills_ativas": skills_ativas or "Nenhuma skill carregada neste turno.",
                "resultados_mcp": resultados_mcp
                or "Nenhuma ferramenta MCP executada neste turno.",
                "context": contexto,
                "resumo": texto_resumo,
                "historico": historico_lc,
                "question": pergunta,
            }
        )

        return ResultadoGeracao(
            conteudo=resultado.conteudo,
            faltou_informacao=resultado.faltou_informacao,
        )

    def _converter_historico(self, historico: HistoricoConversa) -> list[BaseMessage]:
        mensagens_lc: list[BaseMessage] = []
        for msg in historico.mensagens:
            if msg.role == Mensagem.RoleMensagem.USUARIO:
                mensagens_lc.append(HumanMessage(content=msg.conteudo))
            elif msg.role == Mensagem.RoleMensagem.ASSISTENTE:
                mensagens_lc.append(AIMessage(content=msg.conteudo))
            else:
                mensagens_lc.append(HumanMessage(content=msg.conteudo))
        return mensagens_lc
