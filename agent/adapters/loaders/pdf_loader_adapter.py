"""
agent/adapters/document_loaders/pdf_loader_adapter.py

Adapter concreto que implementa DocumentLoaderPort usando PyMuPDF (fitz).
Única classe do projeto que sabe extrair texto de PDFs —
o domínio recebe um DocumentoExtraido com páginas rastreáveis.
"""

import asyncio
from pathlib import Path

import fitz
from loguru import logger

from agent.domain.exceptions import DocumentoNaoEncontradoError
from agent.domain.value_objects.documento_extraido import (
    DocumentoExtraido,
    PaginaExtraida,
)


class PDFLoaderAdapter:
    """
    Implementa DocumentLoaderPort extraindo texto de arquivos PDF por página.

    Usa asyncio.to_thread para não bloquear o loop de eventos do FastAPI
    durante a leitura de disco — operação inerentemente síncrona no PyMuPDF.

    Cada página vira uma PaginaExtraida com número real da página e metadados
    de origem — garantindo rastreabilidade completa no pipeline de ingestão.

    A lógica de extração fica em _extrair (método síncrono privado)
    para permitir testes unitários sem necessidade de async.

    Exemplos
    --------
    >>> adapter = PDFLoaderAdapter()
    >>> doc = await adapter.carregar("manuais/siafi_2024.pdf")
    >>> doc.total_paginas
    42
    >>> doc.paginas[0].metadados["origem"]
    'manuais/siafi_2024.pdf'
    """

    async def carregar(self, origem: str) -> DocumentoExtraido:
        """
        Extrai o texto de um PDF por página de forma não-bloqueante.

        Parâmetros
        ----------
        origem : str
            Caminho local para o arquivo PDF a ser carregado.

        Retorna
        -------
        DocumentoExtraido
            Documento com todas as páginas extraídas e metadados de rastreabilidade.

        Levanta
        -------
        DocumentoNaoEncontradoError
            Se o arquivo não existir no caminho informado.
        """
        logger.debug("Iniciando carregamento do PDF | origem='{}'", origem)

        documento = await asyncio.to_thread(self._extrair, origem)

        logger.info(
            "PDF carregado | origem='{}' | páginas={} | caracteres={}",
            origem,
            documento.total_paginas,
            documento.total_caracteres,
        )

        return documento

    def _extrair(self, origem: str) -> str:
        """
        Lógica síncrona de extração de texto via PyMuPDF, página a página.

        Páginas sem texto (ex.: imagens escaneadas sem OCR) são ignoradas
        com um WARNING — não interrompem a extração das demais.

        Parâmetros
        ----------
        origem : str
            Caminho local para o arquivo PDF.

        Retorna
        -------
        DocumentoExtraido
            Documento com páginas não-vazias extraídas.

        Levanta
        -------
        DocumentoNaoEncontradoError
            Se o arquivo não existir no caminho informado.
        """

        if not Path(origem).exists():
            logger.error("Arquivo não encontrado | origem='{}'", origem)
            raise DocumentoNaoEncontradoError(documento_id=origem)

        paginas: list[PaginaExtraida] = []

        with fitz.open(origem) as doc:
            for numero_pagina, pagina in enumerate(doc, start=1):
                texto = pagina.get_text()

                if not texto.strip():
                    logger.warning(
                        "Página sem texto ignorada | origem='{}' | página={}",
                        origem,
                        numero_pagina,
                    )
                    continue

                paginas.append(
                    PaginaExtraida(
                        pagina=numero_pagina,
                        texto=texto,
                        metadados={"origem": origem},
                    )
                )

        logger.debug(
            "Extração concluída | origem='{}' | páginas_extraídas={}",
            origem,
            len(paginas),
        )

        return DocumentoExtraido(origem=origem, paginas=tuple(paginas))
