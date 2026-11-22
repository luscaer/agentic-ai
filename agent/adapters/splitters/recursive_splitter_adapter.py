"""
agent/adapters/splitters/recursive_splitter_adapter.py

Adapter concreto que implementa DocumentSplitterPort usando o
RecursiveCharacterTextSplitter do LangChain.

Divide cada página do DocumentoExtraido em chunks menores, preservando
o número de página e os metadados de origem em cada chunk gerado.
"""

import asyncio

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from agent.config.configuration import settings
from agent.domain.exceptions import ValorInvalidoError
from agent.domain.value_objects.documento_extraido import (
    DocumentoExtraido,
    PaginaExtraida,
)


class RecursiveSplitterAdapter:
    """
    Implementa DocumentSplitterPort usando RecursiveCharacterTextSplitter.

    A estratégia recursiva tenta dividir nesta ordem de prioridade:
      1. Parágrafos (\\n\\n) — preserva o melhor contexto
      2. Linhas (\\n)
      3. Sentenças (. ; ,)
      4. Espaços ( )
      5. Caracteres individuais — último recurso

    Cada página do DocumentoExtraido é dividida independentemente,
    garantindo que chunks nunca cruzem fronteiras de página.
    Os metadados da página de origem são herdados por cada chunk —
    prontos para o payload do VectorStore.

    Exemplos
    --------
    >>> adapter = RecursiveSplitterAdapter()
    >>> chunks = await adapter.dividir(documento_extraido)
    >>> chunks[0].pagina
    1
    >>> chunks[0].metadados["origem"]
    'manuais/siafi_2024.pdf'
    """

    def __init__(self) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.SPLITTER_CHUNK_SIZE,
            chunk_overlap=settings.SPLITTER_CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", ";", ",", " ", ""],
        )

        logger.debug(
            "RecursiveSplitterAdapter inicializado | chunk_size={} | overlap={}",
            settings.SPLITTER_CHUNK_SIZE,
            settings.SPLITTER_CHUNK_OVERLAP,
        )

    async def dividir(self, documento: DocumentoExtraido) -> list[PaginaExtraida]:
        """
        Divide todas as páginas de um documento em chunks de forma não-bloqueante.

        Parâmetros
        ----------
        documento : DocumentoExtraido
            Documento completo extraído pelo DocumentLoaderPort.

        Retorna
        -------
        list[PaginaExtraida]
            Chunks prontos para indexação, cada um com página de origem
            e metadados herdados para o payload do VectorStore.
        """
        logger.debug(
            "Iniciando divisão | origem='{}' | páginas={}",
            documento.origem,
            documento.total_paginas,
        )

        chunks = await asyncio.to_thread(self._dividir_sync, documento)

        logger.info(
            "Divisão concluída | origem='{}' | páginas={} | chunks={}",
            documento.origem,
            documento.total_paginas,
            len(chunks),
        )

        return chunks

    def _dividir_sync(self, documento: DocumentoExtraido) -> list[PaginaExtraida]:
        """
        Lógica síncrona de divisão — separada para facilitar testes unitários.

        Processa cada página individualmente para garantir que chunks
        nunca cruzem fronteiras de página.
        """
        chunks: list[PaginaExtraida] = []

        for pagina in documento.paginas:
            textos = self._splitter.split_text(pagina.texto)

            if not textos:
                logger.warning(
                    "Nenhum chunk gerado para página {} | origem='{}'",
                    pagina.pagina,
                    documento.origem,
                )
                continue

            for texto in textos:
                chunks.append(
                    PaginaExtraida(
                        pagina=pagina.pagina,
                        texto=texto,
                        metadados=pagina.metadados,
                    )
                )

        if not chunks:
            raise ValorInvalidoError(
                "chunks",
                f"nenhum chunk gerado para '{documento.origem}' — "
                "verifique se o PDF não está escaneado sem OCR",
            )

        return chunks
