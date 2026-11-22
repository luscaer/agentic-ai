"""
application/indexar_documento_use_case.py

Use Case responsável pelo pipeline completo de indexação de um manual.
Orquestra: carregamento → extração de texto → chunking → indexação vetorial.
"""

from agent.domain.exceptions import ValorInvalidoError
from datetime import datetime, timezone

from loguru import logger

from agent.domain.entities import DocumentoIndexado
from agent.domain.ports.driven.vector_store_port import VectorStorePort
from agent.domain.ports.driven.document_splitter_port import DocumentSplitterPort
from agent.domain.ports.driven.document_loader_port import DocumentLoaderPort
from agent.domain.value_objects.topico import Topico


class IndexarDocumentoUseCase:
    """
    Orquestra o pipeline de ingestão de manuais contábeis.

    Fluxo:
        1. Carrega o arquivo (PDF, URL) via DocumentLoaderPort
        2. Valida que o texto extraído não está vazio
        3. Divide em chunks via DocumentSplitterPort
        4. Valida que a divisão gerou ao menos um chunk
        5. Indexa os chunks no vector store via VectorStorePort
        6. Retorna DocumentoIndexado com os metadados da operação

    Todos os colaboradores são injetados via construtor — o Use Case
    não sabe se está usando PyMuPDF, LangChain ou Qdrant.

    Exemplos
    --------
    >>> use_case = IndexarDocumentoUseCase(loader, splitter, vector_store, manual_repo)
    >>> doc = await use_case.executar(
    ...     origem="manuais/siafi_2024.pdf",
    ...     manual_id=42,
    ...     topico="execucao orcamentaria",
    ... )
    >>> doc.chunks_count
    18
    """

    def __init__(
        self,
        loader: DocumentLoaderPort,
        splitter: DocumentSplitterPort,
        vector_store: VectorStorePort,
    ) -> None:
        self._loader = loader
        self._splitter = splitter
        self._vector_store = vector_store

    # ------------------------------------------------------------------
    # IndexarDocumentoPort — implementação
    # ------------------------------------------------------------------

    async def executar(
        self,
        origem: str,
        manual_id: int,
        topico_str: str,
    ) -> DocumentoIndexado:
        """
        Executa o pipeline completo de indexação de um manual.

        Parâmetros
        ----------
        origem : str
            Caminho local ou URL do documento a ser indexado.
        manual_id : int
            Identificador do manual no sistema, usado para rastreabilidade
            e para remoção/reindexação futura.
        topico : str
            Tópico associado ao manual, usado como filtro nas buscas vetoriais.

        Retorna
        -------
        DocumentoIndexado
            Entidade com metadados da indexação: chunks gerados e timestamp.

        Levanta
        -------
        DocumentoNaoEncontradoError
            Se o arquivo não existir no caminho informado (propagado do loader).
        ValorInvalidoError
            Se o texto extraído estiver vazio ou a divisão não gerar chunks.
        """
        topico = Topico(valor=topico_str)

        logger.info(
            "Iniciando indexação | manual_id={} | tópico='{}' | origem='{}'",
            manual_id,
            topico.valor,
            origem,
        )

        documento = await self._loader.carregar(origem)
 
        logger.debug(
            "Documento carregado | manual_id={} | páginas={} | caracteres={}",
            manual_id,
            documento.total_paginas,
            documento.total_caracteres,
        )

        chunks = await self._splitter.dividir(documento=documento)

        if not chunks:
            logger.error(
                "Nenhum chunk gerado | manual_id={} | origem='{}'",
                manual_id,
                origem,
            )
            raise ValorInvalidoError(
                "chunks",
                f"a divisão do documento '{origem}' não gerou nenhum chunk — "
                "verifique as configurações de SPLITTER_CHUNK_SIZE",
            )

        logger.debug(
            "Chunks gerados | manual_id={} | chunks={}",
            manual_id,
            len(chunks),
        )

        await self._vector_store.adicionar_documentos(
            manual_id=manual_id, topico=topico, chunks=chunks
        )

        documento_indexado = DocumentoIndexado(
            manual_id=manual_id,
            topico=topico,
            chunks_count=len(chunks),
            indexado_em=datetime.now(timezone.utc),
        )

        logger.info(
            "Indexação concluída | manual_id={} | tópico='{}' | chunks={}",
            manual_id,
            topico.valor,
            documento_indexado.chunks_count,
        )
 
        return documento_indexado
