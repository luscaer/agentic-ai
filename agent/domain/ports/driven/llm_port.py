"""
agent/domain/ports/driven/llm_port.py

Port (contrato) para o modelo de linguagem no fluxo de RAG Agêntico.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.resultado_geracao_llm import ResultadoGeracao
from agent.domain.value_objects.resumo_conversa import ResumoConversa
from agent.domain.value_objects.topico import Topico

AcaoRoteador = Literal["buscar_rag", "carregar_skill", "chamar_mcp", "gerar_resposta"]


@dataclass(frozen=True)
class DecisaoRoteador:
    """Decisão estruturada tomada pelo nó roteador do grafo LangGraph."""

    acao: AcaoRoteador
    justificativa: str
    skill_nome: str | None = None
    query_busca: str | None = None
    filtro_documento: str | None = None
    ferramenta_mcp: str | None = None
    argumentos_mcp: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AvaliacaoEvidencias:
    """Resultado da avaliação de suficiência das evidências recuperadas pelo RAG."""

    suficientes: bool
    justificativa: str
    query_reformulada: str | None = None
    filtro_documento: str | None = None


class LLMPort(Protocol):
    """Contrato para o modelo de linguagem no fluxo agêntico do CTB Assist."""

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
        skills_conteudo: str = "",
    ) -> DecisaoRoteador:
        """Decide o próximo passo do agente: buscar RAG, carregar skill, chamar MCP ou responder."""
        ...

    async def reescrever_query(
        self,
        pergunta: str,
        topico: Topico,
        historico: HistoricoConversa,
        feedback_anterior: str | None = None,
    ) -> str:
        """Reescreve a pergunta do usuário em uma query jurídica otimizada para busca híbrida."""
        ...

    async def avaliar_suficiencia_evidencias(
        self,
        pergunta: str,
        query_atual: str,
        evidencias_texto: str,
        tentativa_atual: int,
        max_tentativas: int,
    ) -> AvaliacaoEvidencias:
        """Avalia se os trechos recuperados respondem à pergunta ou se deve reformular a busca."""
        ...

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
        """Gera a resposta final fundamentada com base em evidências, skills e resultados MCP."""
        ...
