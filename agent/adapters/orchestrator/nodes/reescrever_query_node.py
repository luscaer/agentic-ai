"""
agent/adapters/orchestrator/nodes/reescrever_query_node.py

Nó do RAG Agêntico responsável por traduzir jargões de trânsito e reformular
a consulta para busca híbrida no Qdrant (CTB, Resolução 1.020/2025 e MBFT).
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.ports.driven.llm_port import LLMPort


class ReescreverQueryNode:
    """Reescreve ou reformula a pergunta do usuário para busca vetorial jurídica."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def __call__(self, state: AgenteState) -> dict:
        consulta = state["consulta"]
        base_query = state.get("query_atual") or consulta.pergunta_original
        feedback = state.get("feedback_avaliador")

        pergunta_reescrita = await self._llm.reescrever_query(
            pergunta=base_query,
            topico=consulta.topico,
            historico=consulta.historico,
            feedback_anterior=feedback,
        )

        consulta.pergunta_reescrita = pergunta_reescrita

        logger.debug(
            "Query reescrita | base='{}' | reescrita='{}'",
            base_query,
            pergunta_reescrita,
        )

        return {
            "consulta": consulta,
            "query_atual": pergunta_reescrita,
        }
