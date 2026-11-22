"""
agent/adapters/orchestrator/nodes/guardrail_entrada_node.py

Nó de entrada do grafo LangGraph: valida escopo, prompt injection e PII
antes de acionar o roteador ou consumir tokens do LLM.
"""

from langchain_core.messages import AIMessage
from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.entities.resposta_ia import RespostaIA
from agent.domain.ports.driven.guardrail_port import GuardrailPort
from agent.domain.value_objects.confianca_resposta import ConfiancaResposta


class GuardrailEntradaNode:
    """Executa validações de segurança na entrada do usuário."""

    def __init__(self, guardrail: GuardrailPort) -> None:
        self._guardrail = guardrail

    async def __call__(self, state: AgenteState) -> dict:
        consulta = state["consulta"]
        resultado = await self._guardrail.validar_entrada(consulta.pergunta_original)

        if not resultado.permitido:
            logger.warning(
                "Guardrail de entrada bloqueou mensagem | categoria='{}' | motivo='{}'",
                resultado.categoria,
                resultado.motivo,
            )
            msg_segura = resultado.mensagem_segura or (
                "Sua solicitação não pôde ser processada pelas políticas de segurança do CTB Assist."
            )
            resposta = RespostaIA(
                conteudo=msg_segura,
                fontes=[],
                confianca=ConfiancaResposta(1.0),
                skills_carregadas=[],
                ferramentas_usadas=[],
                tentativas_rag=0,
                bloqueado_guardrail=True,
            )
            return {
                "guardrail_bloqueado": True,
                "guardrail_motivo": resultado.motivo,
                "resposta": resposta,
                "final_response": msg_segura,
                "messages": [AIMessage(content=msg_segura)],
            }

        if resultado.conteudo_sanitizado and resultado.conteudo_sanitizado != consulta.pergunta_original:
            consulta.pergunta_original = resultado.conteudo_sanitizado

        return {
            "consulta": consulta,
            "guardrail_bloqueado": False,
            "guardrail_motivo": None,
        }
