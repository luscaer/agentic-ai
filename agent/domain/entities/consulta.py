"""
agent/domain/entities/consulta.py

Entidade que representa uma consulta feita pelo usuário ao agente.
Tem identidade própria (id) e evolui ao longo do pipeline
pergunta_reescrita começa como None e é preenchida pelo Router Node.
"""

from agent.domain.value_objects.resumo_conversa import ResumoConversa
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.topico import Topico


@dataclass(eq=False)
class Consulta:
    """
    Entidade que encapsula uma consulta do usuário e seu contexto conversacional.

    Exemplos
    --------
    >>> topico = Topico(valor="reembolso")
    >>> consulta = Consulta(
    ...     pergunta_original="Qual o prazo para reembolso?",
    ...     topico=topico,
    ...     historico=HistoricoConversa(mensagens=()),
    ... )
    >>> consulta.id  # UUID gerado automaticamente
    UUID('...')
    >>> consulta.pergunta_reescrita is None  # preenchida depois pelo Router Node
    True
    """

    sessao_id: str
    pergunta_original: str
    topico: Topico
    historico: HistoricoConversa

    id: UUID = field(default_factory=uuid4)
    resumo: ResumoConversa | None = None
    pergunta_reescrita: str | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Consulta):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"Sessão(id{self.sessao_id})"
            f"Consulta(id={self.id}, "
            f"topico={self.topico}, "
            f"pergunta_original={self.pergunta_original!r})"
        )
