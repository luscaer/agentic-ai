"""
agent/domain/ports/driven/guardrail_port.py

Port (contrato) para guardrails de entrada e saída como nós do grafo LangGraph.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ResultadoGuardrail:
    """Resultado da avaliação de um guardrail (entrada ou saída)."""

    permitido: bool
    motivo: str | None = None
    categoria: str | None = None  # ex: "prompt_injection", "fora_de_escopo", "pii", "alucinacao"
    mensagem_segura: str | None = None
    conteudo_sanitizado: str | None = None
    metadados: dict[str, Any] = field(default_factory=dict)


class GuardrailPort(Protocol):
    """Contrato para validação de segurança na entrada e na saída do agente."""

    async def validar_entrada(self, mensagem: str) -> ResultadoGuardrail:
        """Valida a mensagem do usuário contra prompt injection, PII sensível e escopo."""
        ...

    async def validar_saida(
        self,
        resposta: str,
        contexto_fontes: list[dict[str, Any]],
        resultados_mcp: list[dict[str, Any]],
    ) -> ResultadoGuardrail:
        """Valida a resposta gerada antes de entregá-la ao usuário."""
        ...
