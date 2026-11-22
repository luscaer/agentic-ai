"""
agent/domain/ports/driven/reranker_port.py

Port (contrato) para reranqueamento de documentos recuperados.
"""

from typing import Protocol

from agent.domain.value_objects.fonte_documento import FonteDocumento


class RerankerPort(Protocol):
    """
    Contrato para o reranqueador de documentos.

    Recebe os documentos recuperados pelo vector store e os reordena
    por relevância semântica em relação à query — refinando o resultado
    antes de enviá-los à LLM.
    """

    async def reranquear(
        self,
        query: str,
        documentos: list[FonteDocumento],
    ) -> list[FonteDocumento]:
        """
        Reordena documentos por relevância semântica em relação à query.

        Parâmetros
        ----------
        query : str
            Pergunta do usuário (original ou reescrita) usada como referência.
        documentos : list[FonteDocumento]
            Documentos recuperados pelo vector store, em ordem inicial de score.

        Retorna
        -------
        list[FonteDocumento]
            Os mesmos documentos reordenados por relevância semântica,
            do mais para o menos relevante.
        """
        ...
