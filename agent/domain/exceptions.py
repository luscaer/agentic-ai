"""
exceptions.py
Hierarquia de exceções de domínio.

Regra: nenhuma referência a HTTP aqui. A tradução para status codes
acontece exclusivamente na camada de API (Épico 6).
"""


class DomainError(Exception):
    """Classe base para todos os erros de domínio da aplicação."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


# ---------------------------------------------------------------------------
# Erros de validação de Value Objects
# ---------------------------------------------------------------------------


class ValorInvalidoError(DomainError):
    """
    Levantada quando um Value Object recebe um valor fora das regras de negócio.

    Parâmetros
    ----------
    campo : str
        Nome do campo/atributo que falhou a validação (ex.: "topico", "confianca").
    razao : str
        Descrição legível do motivo da falha (ex.: "não pode ser vazio").

    Camada de API → 422 Unprocessable Entity
    """

    def __init__(self, campo: str, razao: str) -> None:
        self.campo = campo
        self.razao = razao
        super().__init__(f"Valor inválido para '{campo}': {razao}")


# ---------------------------------------------------------------------------
# Erros de persistência / consulta
# ---------------------------------------------------------------------------


class DocumentoNaoEncontradoError(DomainError):
    """
    Levantada quando um documento buscado não existe no repositório.

    Parâmetros
    ----------
    documento_id : str
        Identificador do documento não encontrado.

    Camada de API → 404 Not Found
    """

    def __init__(self, documento_id: str) -> None:
        self.documento_id = documento_id
        super().__init__(f"Documento '{documento_id}' não encontrado.")


# ---------------------------------------------------------------------------
# Erros de regra de negócio
# ---------------------------------------------------------------------------


class OperacaoNaoPermitidaError(DomainError):
    """
    Levantada quando uma operação viola uma invariante ou política de negócio.

    Parâmetros
    ----------
    motivo : str
        Explicação da política que foi violada.

    Camada de API → 409 Conflict
    """

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(f"Operação não permitida: {motivo}")
