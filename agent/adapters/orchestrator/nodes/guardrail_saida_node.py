"""
agent/adapters/orchestrator/nodes/guardrail_saida_node.py

Nó final de segurança do grafo LangGraph: valida e sanitiza a resposta gerada
antes de devolvê-la ao usuário e persistir na memória.
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.ports.driven.guardrail_port import GuardrailPort


class GuardrailSaidaNode:
    """Valida a resposta final contra vazamento de PII e violações de política."""

    def __init__(self, guardrail: GuardrailPort) -> None:
        self._guardrail = guardrail

    async def __call__(self, state: AgenteState) -> dict:
        resposta = state.get("resposta")
        if resposta is None:
            return {}

        resultado = await self._guardrail.validar_saida(
            resposta=resposta.conteudo,
            contexto_fontes=state.get("retrieved_docs", []),
            resultados_mcp=state.get("tool_results", []),
        )

        if not resultado.permitido:
            logger.warning(
                "Guardrail de saída bloqueou resposta | categoria='{}' | motivo='{}'",
                resultado.categoria,
                resultado.motivo,
            )
            msg_segura = resultado.mensagem_segura or (
                "Não foi possível entregar a resposta gerada com segurança. "
                "Reformule sua dúvida sobre o CTB ou habilitação."
            )
            resposta.conteudo = msg_segura
            resposta.bloqueado_guardrail = True
            return {
                "guardrail_bloqueado": True,
                "guardrail_motivo": resultado.motivo,
                "resposta": resposta,
                "final_response": msg_segura,
            }

        if resultado.conteudo_sanitizado and resultado.conteudo_sanitizado != resposta.conteudo:
            resposta.conteudo = resultado.conteudo_sanitizado
            return {
                "resposta": resposta,
                "final_response": resposta.conteudo,
            }

        return {"final_response": resposta.conteudo}
