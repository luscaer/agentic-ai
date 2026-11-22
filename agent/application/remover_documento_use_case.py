"""
application/remover_documento_use_case.py

Use Case responsável pelo pipeline completo de remoção de um manual.
Orquestra: carregamento → extração de texto → chunking → indexação vetorial.
"""
from loguru import logger
from agent.domain.ports.driven.vector_store_port import VectorStorePort

class RemoverDocumentoUseCase: 
    """
        Caso de uso responsável por deletar todos os chunks de um manual no banco vetorial.
        Garante que documentos desatualizados ou excluídos não sejam mais recuperados
        pela inteligência artificial nas buscas semânticas. O Use Case delega a exclusão
        para a VectorStorePort baseada no ID único do manual.
        Exemplos
        --------
        >>> use_case = RemoverDocumentoUseCase(vector_store)
        >>> await use_case.executar(manual_id=42)
    """

    def __init__(
        self,
        vector_store: VectorStorePort
    ) -> None:
        self._vector_store = vector_store

    async def executar(
        self,
        manual_id: int
    ) -> None:

        logger.info(
            f"Remoção de Chunks Iniciada  | manual_id={manual_id}"
        )
        await self._vector_store.remover_por_manual(manual_id)