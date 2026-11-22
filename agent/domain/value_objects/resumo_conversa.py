"""
agent/domain/value_objects/resumo_conversa.py

Value Object imutável que representa o snapshot da memória de longo prazo.
Armazena o resumo textual processado pela LLM e metadados de controle.
"""

from datetime import datetime
from dataclasses import dataclass
from agent.domain.exceptions import ValorInvalidoError


@dataclass(frozen=True)
class ResumoConversa:
    """
    Value Object imutável para o resumo da conversa.

    Este objeto captura o estado atual da compreensão do bot sobre o contexto
    histórico, permitindo economia de tokens e manutenção da coerência.

    Exemplos
    --------
    >>> r = ResumoConversa(
    ...     resumo_texto="O usuário discutiu sobre arquitetura DDD.",
    ...     atualizado_em=datetime.now(),
    ...     total_turnos_resumidos=5
    ... )
    """

    resumo_texto: str
    atualizado_em: datetime
    total_turnos_resumidos: int

    def __post_init__(self) -> None:
        """
        Validações básicas para garantir a integridade do estado.
        """
        if self.total_turnos_resumidos < 0:
            raise ValorInvalidoError("total_turnos_resumidos", "não pode ser negativo")

    def __str__(self) -> str:
        return f"Resumo ({self.total_turnos_resumidos} turnos): {self.resumo_texto[:30]}..."
