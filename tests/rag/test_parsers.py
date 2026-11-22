"""
tests/rag/test_parsers.py

Testes unitários dos parsers dedicados para os 3 documentos oficiais do CTB Assist:
1. CTB (L9503Compilado.pdf) via LegalArticleSplitterAdapter
2. Resolução CONTRAN nº 1.020/2025 (Resolucao10202025.pdf) via LegalArticleSplitterAdapter
3. MBFT (MBFT_CONTRAN.pdf) via MBFTParserAdapter
"""

from pathlib import Path

import pytest

from agent.adapters.loaders.mbft_parser_adapter import MBFTParserAdapter
from agent.adapters.loaders.pdf_loader_adapter import PDFLoaderAdapter
from agent.adapters.splitters.legal_splitter_adapter import LegalArticleSplitterAdapter
from agent.domain.value_objects.documento_extraido import (
    DocumentoExtraido,
    PaginaExtraida,
)

DOCS_DIR = Path("docs")


@pytest.mark.asyncio
async def test_legal_splitter_preserva_caput_em_artigo_extenso() -> None:
    """Artigo longo (ex.: Art. 181) dividido por incisos deve manter o caput em todos os sub-chunks."""
    incisos = "\n".join(
        f"{rom} - estacionar o veículo em situação irregular número {i} conforme sinalização viária:\n"
        f"Infração - grave;\nPenalidade - multa;\nMedida administrativa - remoção do veículo."
        for i, rom in enumerate(["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"], start=1)
    )
    texto = (
        "L9503Compilado\n21/11/2026, 19:12\n"
        "CAPÍTULO XV - DAS INFRAÇÕES\n"
        f"Art. 181. Estacionar o veículo:\n{incisos}"
    )
    doc = DocumentoExtraido(
        origem="docs/L9503Compilado.pdf",
        paginas=(PaginaExtraida(pagina=55, texto=texto),),
    )

    splitter = LegalArticleSplitterAdapter(max_chunk_size=700)
    chunks = await splitter.dividir(doc)

    assert len(chunks) >= 2
    for ch in chunks:
        assert "Art. 181. Estacionar o veículo:" in ch.texto
        assert "L9503Compilado\n21/11/2026" not in ch.texto
        assert ch.metadados["documento"] == "CTB"
        assert ch.metadados["artigo"] == "181"
        assert ch.metadados["inciso"] is not None


@pytest.mark.asyncio
async def test_legal_splitter_ctb_pdf_real() -> None:
    ctb_path = DOCS_DIR / "L9503Compilado.pdf"
    if not ctb_path.exists():
        pytest.skip("L9503Compilado.pdf não presente em docs/")

    loader = PDFLoaderAdapter()
    splitter = LegalArticleSplitterAdapter()

    doc = await loader.carregar(str(ctb_path))
    chunks = await splitter.dividir(doc)

    assert len(chunks) > 200
    art208 = [c for c in chunks if c.metadados.get("artigo") == "208"]
    assert art208, "Art. 208 (avançar sinal vermelho) deve estar indexado"
    assert "sinal vermelho" in art208[0].texto.lower()
    assert "gravíssima" in art208[0].texto.lower()

    art181 = [c for c in chunks if c.metadados.get("artigo") == "181"]
    assert len(art181) >= 2
    assert all("Art. 181" in c.texto for c in art181)


@pytest.mark.asyncio
async def test_legal_splitter_resolucao_1020_pdf_real() -> None:
    res_path = DOCS_DIR / "Resolucao10202025.pdf"
    if not res_path.exists():
        pytest.skip("Resolucao10202025.pdf não presente em docs/")

    loader = PDFLoaderAdapter()
    splitter = LegalArticleSplitterAdapter()

    doc = await loader.carregar(str(res_path))
    chunks = await splitter.dividir(doc)

    assert len(chunks) > 50
    art36 = [c for c in chunks if c.metadados.get("artigo") == "36"]
    assert art36, "Art. 36 da Resolução 1.020/2025 (instrutores autônomos) deve existir"
    assert "autônomos" in art36[0].texto.lower()
    assert art36[0].metadados["documento"] == "CONTRAN"
    assert "1.020/2025" in art36[0].metadados["norma"]


@pytest.mark.asyncio
async def test_mbft_parser_amostra_real() -> None:
    """Valida a extração estruturada da Parte Geral e de Fichas do MBFT real."""
    mbft_path = DOCS_DIR / "MBFT_CONTRAN.pdf"
    if not mbft_path.exists():
        pytest.skip("MBFT_CONTRAN.pdf não presente em docs/")

    import fitz

    parser = MBFTParserAdapter()
    with fitz.open(str(mbft_path)) as doc:
        primeira = parser._encontrar_primeira_ficha(doc)
        assert primeira > 10, "Deve detectar a Parte Geral antes da 1ª ficha"

        # Extrai a primeira ficha (páginas 24-25 -> Código 751-01, Art. 95)
        grupos = parser._agrupar_paginas_por_ficha(doc, primeira)
        assert len(grupos) > 300
        ficha_0 = parser._extrair_ficha(doc, grupos[0], str(mbft_path))
        assert ficha_0 is not None
        assert ficha_0["codigo_enquadramento"] == "751-01"
        assert ficha_0["artigo"] == "95"
        assert ficha_0["quando_autuar"]
        assert ficha_0["quando_nao_autuar"]

        chunk_md = parser._ficha_para_chunk(ficha_0)
        assert "# Ficha MBFT 751-01" in chunk_md.texto
        assert "## Quando Autuar" in chunk_md.texto
        assert "## Quando NÃO Autuar" in chunk_md.texto
        assert chunk_md.metadados["documento"] == "MBFT"
        assert chunk_md.metadados["artigo"] == "95"
