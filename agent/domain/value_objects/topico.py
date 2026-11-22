"""
agent/domain/value_objects/topico.py

Value Object imutável que representa o tópico de uma consulta ou documento.
Normaliza a entrada (strip + lower) e rejeita valores vazios.
"""

from dataclasses import dataclass
from agent.domain.exceptions import ValorInvalidoError


@dataclass(frozen=True)
class Topico:
    """
    Value Object imutável para tópico.

    Exemplos:
    --------
    >>> t = Topico(valor="  Classificação contábil e orçamentária  ")
    >>> str(t)
    'classificação contábil e orçamentária'
    """

    valor: str

    def __post_init__(self) -> None:
        normalizado = self.valor.strip().lower()

        if not normalizado:
            raise ValorInvalidoError(
                "topico", "não pode ser vazio ou conter apenas espaços"
            )

        object.__setattr__(self, "valor", normalizado)

    def __str__(self) -> str:
        return self.valor
