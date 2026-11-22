"""
agent/ports/driving/indexar_documento_port.py

Port de ENTRADA chamado por um job administrativo em background.
Define o contrato do caso de uso de indexação de manuais.
"""

from typing import Protocol

from agent.domain.entities.documento_indexado import DocumentoIndexado


class IndexarDocumentoPort(Protocol):
    """
    Contrato para o caso de uso de indexação de documentos.

    Orquestra o pipeline de ingestão:
    carregamento → extração de texto → chunking → embeddings → indexação vetorial.

    Chamado por um job de background ou painel administrativo,
    nunca diretamente pelo fluxo de conversa do usuário.
    """

    async def executar(
        self,
        origem: str,
        manual_id: int,
        topico_str: str,
    ) -> DocumentoIndexado:
        """
        Indexa um documento no vector store e registra os metadados.

        Parâmetros
        ----------
        origem : str
            Caminho local ou URL do documento a ser indexado (PDF, URL...).
        manual_id : int
            Identificador do manual no sistema, usado para rastreabilidade
            e para remoção/reindexação futura.
        topico : str
            Tópico associado ao manual, usado como filtro nas buscas vetoriais.

        Retorna
        -------
        DocumentoIndexado
            Entidade com os metadados do documento recém-indexado,
            incluindo contagem de chunks e timestamp de indexação.
        """
        ...
