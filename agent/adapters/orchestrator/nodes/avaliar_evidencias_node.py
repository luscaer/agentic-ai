"""
agent/adapters/orchestrator/nodes/avaliar_evidencias_node.py

Nó Avaliador de Evidências do RAG Agêntico.
Julga se os dispositivos recuperados são suficientes ou se o grafo deve
reformular a consulta e tentar uma nova busca (respeitando MAX_RETRIEVAL_ATTEMPTS).
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.config.configuration import settings
from agent.domain.ports.driven.llm_port import LLMPort


class AvaliarEvidenciasNode:
    """Avalia a suficiência das evidências recuperadas pelo RAG."""

    def __init__(
        self,
        llm: LLMPort,
        max_tentativas: int | None = None,
    ) -> None:
        self._llm = llm
        self._max_tentativas = max_tentativas or settings.MAX_RETRIEVAL_ATTEMPTS

    async def __call__(self, state: AgenteState) -> dict:
        consulta = state["consulta"]
        tentativa_atual = state.get("retrieval_attempts", 1)
        query_atual = state.get("query_atual") or consulta.pergunta_original
        docs = state.get("documentos_recuperados", [])

        evidencias_texto = "\n\n".join(
            f"[{d.referencia_curta}]\n{d.trecho_preview[:600]}" for d in docs[:5]
        )

        avaliacao = await self._llm.avaliar_suficiencia_evidencias(
            pergunta=consulta.pergunta_original,
            query_atual=query_atual,
            evidencias_texto=evidencias_texto,
            tentativa_atual=tentativa_atual,
            max_tentativas=self._max_tentativas,
        )

        suficientes = avaliacao.suficientes or (tentativa_atual >= self._max_tentativas)

        logger.info(
            "Avaliador de evidências (tentativa {}/{}) | suficientes={} | motivo='{}'",
            tentativa_atual,
            self._max_tentativas,
            suficientes,
            avaliacao.justificativa,
        )

        update: dict = {
            "evidencias_suficientes": suficientes,
            "feedback_avaliador": avaliacao.justificativa,
        }
        if not suficientes:
            if avaliacao.query_reformulada:
                update["query_atual"] = avaliacao.query_reformulada
            update["filtro_documento"] = avaliacao.filtro_documento

        return update
