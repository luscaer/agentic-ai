"""
agent/domain/value_objects/resultado_geracao_llm.py

Value Object imutável que representa a saída de uma geração de LLM.
Encapsula o texto de resposta e metadados sobre a suficiência da informação.
"""

from dataclasses import dataclass
from agent.domain.exceptions import ValorInvalidoError


@dataclass(frozen=True)
class ResultadoGeracao:
    """
    Value Object imutável para o resultado da geração da LLM.

    Este objeto captura o conteúdo gerado pelo modelo de linguagem e 
    uma flag (faltou_informacao) que indica se o modelo declarou não ter
    contexto suficiente para responder completamente à pergunta.

    Exemplos
    --------
    >>> resultado = ResultadoGeracao(
    ...     conteudo="Segundo o manual, o prazo é de 5 dias úteis.",
    ...     faltou_informacao=False
    ... )
    >>> resultado.faltou_informacao
    False
    """

    conteudo: str
    faltou_informacao: bool

    def __post_init__(self) -> None:
        """
        Validações básicas para garantir a integridade do estado.
        """
        if not self.conteudo or not self.conteudo.strip():
            raise ValorInvalidoError("conteudo", "não pode estar vazio ou ser apenas espaços")

        def __str__(self) -> str:
            status_info = "Faltou Informação" if self.faltou_informacao else "Informação Completa"
            conteudo_truncado = self.conteudo if len(self.conteudo) <= 30 else f"{self.conteudo[:30]}..."
            
            return f"ResultadoGeracao [{status_info}]: {conteudo_truncado}"