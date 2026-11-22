"""
agent/domain/entities/documento_indexado.py

Entidade que representa um manual indexado no sistema de busca vetorial.
"""

from datetime import datetime
from dataclasses import dataclass

from agent.domain.value_objects.topico import Topico


@dataclass(frozen=True)
class DocumentoIndexado:
    """
    Entidade imutável que representa um documento indexado no vector store.

    Frozen porque um documento indexado é um fato consumado: uma vez registrado,
    seus metadados não mudam. Para reindexar, um novo DocumentoIndexado é criado.

    Exemplos
    --------
    >>> from datetime import datetime
    >>> doc = DocumentoIndexado(
    ...     manual_id=42,
    ...     topico=Topico(valor="reembolso"),
    ...     chunks_count=18,
    ...     indexado_em=datetime(2025, 1, 10, 14, 30),
    ... )
    >>> str(doc.topico)
    'reembolso'
    >>> doc.chunks_count
    18
    """

    manual_id: int
    topico: Topico
    chunks_count: int
    indexado_em: datetime

    def __str__(self) -> str:
        return (
            f"Manual {self.manual_id} | "
            f"Tópico: {self.topico} | "
            f"Chunks: {self.chunks_count} | "
            f"Indexado em: {self.indexado_em:%d/%m/%Y %H:%M}"
        )
