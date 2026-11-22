"""
rag/ingestion.py

Pipeline e CLI de ingestão dos 3 documentos oficiais do CTB Assist:
1. docs/L9503Compilado.pdf       -> CTB (Lei nº 9.503/1997) via LegalArticleSplitterAdapter
2. docs/Resolucao10202025.pdf    -> Resolução CONTRAN nº 1.020/2025 via LegalArticleSplitterAdapter
3. docs/MBFT_CONTRAN.pdf         -> MBFT (Resolução CONTRAN nº 985/2022) via MBFTParserAdapter

Uso via CLI:
    python -m rag.ingestion
    python -m rag.ingestion --somente-parsing   # gera e valida chunks/JSON sem indexar no Qdrant
    python -m rag.ingestion --sem-mbft          # indexa apenas CTB + Resolução 1.020/2025
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from loguru import logger
from qdrant_client import AsyncQdrantClient

from agent.adapters.loaders.mbft_parser_adapter import MBFTParserAdapter
from agent.adapters.loaders.pdf_loader_adapter import PDFLoaderAdapter
from agent.adapters.splitters.legal_splitter_adapter import LegalArticleSplitterAdapter
from agent.adapters.vectorstores.qdrant_adapter import QdrantVectorStoreAdapter
from agent.config.configuration import settings
from agent.domain.value_objects.documento_extraido import PaginaExtraida
from agent.domain.value_objects.topico import Topico


def criar_qdrant_client() -> AsyncQdrantClient:
    """Cria cliente Qdrant remoto (se QDRANT_URL definido) ou local persistente em disco."""
    if settings.QDRANT_URL:
        logger.info("Conectando ao Qdrant remoto em '{}'", settings.QDRANT_URL)
        return AsyncQdrantClient(url=settings.QDRANT_URL)
    qdrant_path = Path(settings.QDRANT_PATH)
    qdrant_path.mkdir(parents=True, exist_ok=True)
    logger.info("Usando Qdrant local persistente em '{}'", qdrant_path)
    return AsyncQdrantClient(path=str(qdrant_path))


async def preparar_chunks_documentos(
    docs_dir: str | None = None,
    incluir_mbft: bool = True,
    salvar_cache_dir: str | None = None,
) -> dict[str, list[PaginaExtraida]]:
    """
    Executa os parsers dedicados para os PDFs encontrados em `docs_dir`
    e retorna um dicionário `{chave_documento: list[PaginaExtraida]}`.
    """
    base = Path(docs_dir or settings.DOCS_DIR)
    loader = PDFLoaderAdapter()
    legal_splitter = LegalArticleSplitterAdapter()
    cache_dir = salvar_cache_dir or settings.PROCESSED_DATA_DIR

    resultado: dict[str, list[PaginaExtraida]] = {}

    ctb_path = base / "L9503Compilado.pdf"
    if ctb_path.exists():
        doc_ctb = await loader.carregar(str(ctb_path))
        resultado["ctb"] = await legal_splitter.dividir(doc_ctb)
    else:
        logger.warning("CTB não encontrado em '{}'", ctb_path)

    res_path = base / "Resolucao10202025.pdf"
    if res_path.exists():
        doc_res = await loader.carregar(str(res_path))
        resultado["resolucao_1020"] = await legal_splitter.dividir(doc_res)
    else:
        logger.warning("Resolução CONTRAN 1.020/2025 não encontrada em '{}'", res_path)

    mbft_path = base / "MBFT_CONTRAN.pdf"
    if incluir_mbft and mbft_path.exists():
        mbft_parser = MBFTParserAdapter(salvar_cache_dir=cache_dir)
        resultado["mbft"] = await mbft_parser.carregar_e_estruturar(str(mbft_path))
    elif incluir_mbft:
        logger.warning("MBFT não encontrado em '{}'", mbft_path)

    return resultado


async def executar_ingestao(
    docs_dir: str | None = None,
    incluir_mbft: bool = True,
    somente_parsing: bool = False,
) -> dict[str, Any]:
    """Executa o pipeline completo de parsing e (opcionalmente) indexação no Qdrant."""
    chunks_por_doc = await preparar_chunks_documentos(
        docs_dir=docs_dir,
        incluir_mbft=incluir_mbft,
    )

    resumo = {k: len(v) for k, v in chunks_por_doc.items()}
    logger.info("Resumo do parsing | {}", resumo)

    if somente_parsing:
        out_dir = Path(settings.PROCESSED_DATA_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "resumo_parsing.json").write_text(
            json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return resumo

    client = criar_qdrant_client()
    try:
        vector_store = await QdrantVectorStoreAdapter.criar(client)

        mapa_ids = {
            "ctb": (1, Topico("legislacao_ctb")),
            "resolucao_1020": (2, Topico("habilitacao")),
            "mbft": (3, Topico("fiscalizacao_mbft")),
        }

        for chave, chunks in chunks_por_doc.items():
            if not chunks:
                continue
            manual_id, topico = mapa_ids[chave]
            await vector_store.adicionar_documentos(
                manual_id=manual_id,
                topico=topico,
                chunks=chunks,
            )
    finally:
        await client.close()

    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingestão da base documental do CTB Assist (CTB + Res. 1.020/2025 + MBFT)."
    )
    parser.add_argument(
        "--docs-dir",
        default=settings.DOCS_DIR,
        help="Diretório contendo os PDFs oficiais.",
    )
    parser.add_argument(
        "--sem-mbft",
        action="store_true",
        help="Ignora o MBFT e processa apenas CTB e Resolução 1.020/2025.",
    )
    parser.add_argument(
        "--somente-parsing",
        action="store_true",
        help="Executa apenas os parsers e salva o resumo/cache sem indexar no Qdrant.",
    )
    args = parser.parse_args()

    resumo = asyncio.run(
        executar_ingestao(
            docs_dir=args.docs_dir,
            incluir_mbft=not args.sem_mbft,
            somente_parsing=args.somente_parsing,
        )
    )
    print("Ingestão concluída:", json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
