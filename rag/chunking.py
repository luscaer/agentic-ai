"""
rag/chunking.py

Reexporta os parsers e splitters jurídicos dedicados da Arquitetura Hexagonal
para uso direto em scripts de ingestão e testes isolados do módulo `rag/`.
"""

from agent.adapters.loaders.mbft_parser_adapter import MBFTParserAdapter
from agent.adapters.loaders.pdf_loader_adapter import PDFLoaderAdapter
from agent.adapters.splitters.legal_splitter_adapter import (
    LegalArticleSplitterAdapter,
    inferir_metadados_norma,
)

__all__ = [
    "LegalArticleSplitterAdapter",
    "MBFTParserAdapter",
    "PDFLoaderAdapter",
    "inferir_metadados_norma",
]
