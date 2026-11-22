"""
agent/domain/value_objects/confianca_resposta.py

Value Object imutável que representa o grau de confiança de uma resposta.
Encapsula a lógica de avaliação — nenhuma camada externa compara floats diretamente.
"""

from dataclasses import dataclass
from agent.domain.exceptions import ValorInvalidoError


@dataclass(frozen=True)
class ConfiancaResposta:
    """
    Value Object imutável para confiança de resposta.

    O valor deve estar entre 0.0 e 1.0 (inclusive).
    A avaliação de limiar é responsabilidade deste objeto — não do chamador.

    Exemplos
    --------
    >>> c = ConfiancaResposta(valor=0.85)
    >>> c.esta_abaixo_do_threshold(0.7)
    False
    >>> c.esta_abaixo_do_threshold(0.9)
    True
    """

    valor: float

    def __post_init__(self) -> None:
        if not isinstance(self.valor, (int, float)):
            raise ValorInvalidoError("confianca", "deve ser um número")

        if not (0.0 <= self.valor <= 1.0):
            raise ValorInvalidoError(
                "confianca", f"deve estar entre 0.0 e 1.0 (recebido: {self.valor})"
            )

    def esta_abaixo_do_threshold(self, threshold: float) -> bool:
        """
        Retorna True se a confiança for menor que o limiar aceitável.

        Parâmetros
        ----------
        threshold : float
            Limiar mínimo aceitável, tipicamente vindo de configuração do sistema.
        """
        return self.valor < threshold

    def __str__(self) -> str:
        return f"{self.valor:.2f}"
