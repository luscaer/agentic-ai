"""
agent/domain/entities/manual.py
 
Entidade que representa um manual ou documento de referência no domínio.
Possui identidade própria (id) e gerencia seu estado de indexação no banco vetorial.
"""

from dataclasses import dataclass, replace

from agent.domain.exceptions import ValorInvalidoError
from agent.domain.value_objects.topico import Topico

@dataclass(frozen=True, eq=False)
class Manual:
    """
    Entidade que encapsula um manual de referência do sistema.

    Sua identidade é definida exclusivamente pelo `id`. Possui controle de
    estado para rastrear se seu conteúdo já foi processado e transformado 
    em embeddings no banco vetorial.

    Exemplos
    --------
    >>> topico = Topico(valor="icms")
    >>> manual = Manual(
    ...     id=101,
    ...     titulo="Manual de Retenção do ICMS",
    ...     topico=topico,
    ...     caminho_arquivo="/docs/icms_retencao.pdf"
    ... )
    >>> manual.vetor_indexado
    False
    >>> manual = manual.marcar_como_indexado()
    >>> manual.vetor_indexado
    True
    >>> manual2 = Manual(id=101, titulo="Nome Diferente", topico=topico, caminho_arquivo="")
    >>> manual == manual2  # A igualdade testa APENAS o ID
    True
    """

    id: int
    titulo: str
    topico: Topico
    caminho_arquivo: str

    vetor_indexado: bool = False
    descricao: str | None = None

    def __post_init__(self) -> None:
        """Garante que a entidade seja instanciada em um estado consistente."""
        if self.id <= 0:
            raise ValorInvalidoError("ID", f"deve ser um inteiro positivo (recebido: {self.id}).")
        
        if not self.titulo or not self.titulo.strip():
            raise ValorInvalidoError("titulo", "não pode estar vazio.")
            
        if not self.caminho_arquivo or not self.caminho_arquivo.strip():
            raise ValorInvalidoError("caminho", "não pode estar vazio.")

    def marcar_como_indexado(self) -> "Manual":
        """
        Registra que o manual foi lido, fracionado (chunked) e seus 
        embeddings foram inseridos no banco vetorial com sucesso.
        """
        return replace(self, vetor_indexado=True)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Manual):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        status = "Indexado" if self.vetor_indexado else "Pendente"
        return (
            f"Manual(id={self.id}, "
            f"titulo={self.titulo!r}, "
            f"status={status})"
        )