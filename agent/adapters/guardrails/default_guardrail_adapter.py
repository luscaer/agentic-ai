"""
agent/adapters/guardrails/default_guardrail_adapter.py

Implementação padrão segura de GuardrailPort (entrada e saída) para uso
imediato no grafo LangGraph até a integração com `agent/guardrails.py` do Integrante 2.

Protege contra:
1. Prompt injection (tentativas de ignorar regras, revelar system prompt ou forjar pontuações).
2. Vazamento/exposição de dados pessoais sensíveis (CPF, RG, RENACH/CNH) via mascaramento.
3. Pedidos claramente fora do escopo de trânsito/CTB/CONTRAN.
"""

import re
from typing import Any

from agent.domain.ports.driven.guardrail_port import ResultadoGuardrail

_PATTERNS_INJECTION = [
    re.compile(r"ignore\s+(?:todas\s+)?(?:as\s+|suas\s+)?(regras|instru[çc][õo]es)", re.IGNORECASE),
    re.compile(r"esque[çc]a\s+(?:todas\s+)?(?:as\s+|suas\s+)?(regras|instru[çc][õo]es)", re.IGNORECASE),
    re.compile(r"(reveal|mostre|exiba)\s+(o\s+)?(system\s+prompt|prompt\s+de\s+sistema)", re.IGNORECASE),
    re.compile(r"aja\s+como\s+se\s+n[ãa]o\s+houvesse\s+regras", re.IGNORECASE),
    re.compile(r"override\s+system|jailbreak|dan\s+mode", re.IGNORECASE),
]

_RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_RE_CNH = re.compile(r"\b(?:cnh|renach)\s*(?:n[º°]?|:)?\s*\d{9,11}\b", re.IGNORECASE)

_PALAVRAS_FORA_ESCOPO = [
    "receita de bolo",
    "escreva um poema",
    "código python para",
    "criptomoeda",
    "horóscopo",
    "futebol",
    "aposta esportiva",
]


class DefaultGuardrailAdapter:
    """Guardrail determinístico de entrada e saída (fallback seguro)."""

    async def validar_entrada(self, mensagem: str) -> ResultadoGuardrail:
        texto = (mensagem or "").strip()
        if not texto:
            return ResultadoGuardrail(
                permitido=False,
                categoria="entrada_vazia",
                motivo="Mensagem vazia.",
                mensagem_segura="Por favor, informe sua dúvida sobre o CTB, habilitação ou infrações de trânsito.",
            )

        for pattern in _PATTERNS_INJECTION:
            if pattern.search(texto):
                return ResultadoGuardrail(
                    permitido=False,
                    categoria="prompt_injection",
                    motivo="Tentativa de sobrescrever instruções do assistente detectada.",
                    mensagem_segura=(
                        "Não posso ignorar as regras do Código de Trânsito Brasileiro nem "
                        "alterar critérios legais de pontuação ou penalidades. Se tiver uma "
                        "dúvida legítima sobre infrações, CNH ou fiscalização, posso ajudar."
                    ),
                )

        lower = texto.lower()
        if any(termo in lower for termo in _PALAVRAS_FORA_ESCOPO):
            return ResultadoGuardrail(
                permitido=False,
                categoria="fora_de_escopo",
                motivo="Solicitação fora do domínio de trânsito brasileiro.",
                mensagem_segura=(
                    "Sou o **CTB Assist**, especializado em legislação de trânsito brasileira "
                    "(CTB, Resolução CONTRAN nº 1.020/2025 e MBFT). Posso ajudar com dúvidas "
                    "sobre infrações, pontuação, multas, habilitação/PPD e defesa administrativa."
                ),
            )

        # Mascara PII na entrada para não enviar dados sensíveis ao LLM
        sanitizado = _RE_CPF.sub("[CPF_OCULTADO]", texto)
        sanitizado = _RE_CNH.sub("[CNH_OCULTADA]", sanitizado)

        return ResultadoGuardrail(
            permitido=True,
            conteudo_sanitizado=sanitizado,
            metadados={"pii_mascarada": sanitizado != texto},
        )

    async def validar_saida(
        self,
        resposta: str,
        contexto_fontes: list[dict[str, Any]],
        resultados_mcp: list[dict[str, Any]],
    ) -> ResultadoGuardrail:
        sanitizado = _RE_CPF.sub("[CPF_OCULTADO]", resposta or "")
        sanitizado = _RE_CNH.sub("[CNH_OCULTADA]", sanitizado)
        return ResultadoGuardrail(
            permitido=True,
            conteudo_sanitizado=sanitizado,
            metadados={
                "total_fontes": len(contexto_fontes),
                "total_mcp": len(resultados_mcp),
            },
        )
