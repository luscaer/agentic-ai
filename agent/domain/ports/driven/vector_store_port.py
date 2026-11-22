"""
agent/domain/ports/driven/vector_store_port.py

Port (contrato) para o repositório de busca vetorial do CTB Assist.
"""

from typing import Protocol

from agent.domain.value_objects.documento_extraido import PaginaExtraida
from agent.domain.value_objects.fonte_documento import FonteDocumento
from agent.domain.value_objects.topico import Topico


class VectorStorePort(Protocol):
    """Contrato para o sistema de busca vetorial híbrida (dense + sparse)."""

    async def adicionar_documentos(
        self, manual_id: int, topico: Topico, chunks: list[PaginaExtraida]
    ) -> None:
        """Indexa chunks de um documento normativo no vector store."""
        ...

    async def buscar_documentos(
        self,
        query: str,
        k: int = 5,
        topico: Topico | None = None,
        documento: str | None = None,
        artigo: str | None = None,
    ) -> list[FonteDocumento]:
        """
        Busca trechos relevantes no vector store com filtros opcionais por
        tópico, documento ('CTB', 'CONTRAN', 'MBFT') ou número de artigo.
        """
        ...

    async def buscar_por_topico(
        self, query: str, topico: Topico
    ) -> list[FonteDocumento]:
        """Compatibilidade com chamadas que filtram explicitamente por tópico."""
        ...

    async def remover_por_manual(self, manual_id: int) -> None:
        """Remove todos os chunks associados a um documento/manual_id."""
        ...
