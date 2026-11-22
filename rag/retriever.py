"""
rag/retriever.py

Fachada padronizada de recuperação do CTB Assist (Requisitos R5, R6 e R9).
Expõe `buscar_legislacao(query, k)` de forma síncrona e assíncrona, além de
uma CLI rápida para validação isolada sem precisar do LangGraph.

Uso via CLI:
    python -m rag.retriever "O que acontece se eu avançar o sinal vermelho?"
    python -m rag.retriever "instrutor autônomo aulas práticas" --documento CONTRAN -k 3
"""

import argparse
import asyncio
from typing import Any

from agent.adapters.vectorstores.qdrant_adapter import QdrantVectorStoreAdapter
from agent.domain.value_objects.topico import Topico
from rag.ingestion import criar_qdrant_client


async def buscar_legislacao_async(
    query: str,
    k: int = 5,
    documento: str | None = None,
    topico: str | None = None,
    artigo: str | None = None,
    vector_store: QdrantVectorStoreAdapter | None = None,
) -> list[dict[str, Any]]:
    """
    Recupera dispositivos legais relevantes do CTB, Resolução CONTRAN nº 1.020/2025
    e MBFT, retornando dicionários padronizados prontos para consumo pelo agente e Streamlit.
    """
    if not query or not query.strip():
        return []

    topico_vo = Topico(topico) if topico else None

    if vector_store is not None:
        fontes = await vector_store.buscar_documentos(
            query=query,
            k=k,
            topico=topico_vo,
            documento=documento,
            artigo=artigo,
        )
        return [f.to_dict() for f in fontes]

    client = criar_qdrant_client()
    try:
        vs = await QdrantVectorStoreAdapter.criar(client)
        fontes = await vs.buscar_documentos(
            query=query,
            k=k,
            topico=topico_vo,
            documento=documento,
            artigo=artigo,
        )
        return [f.to_dict() for f in fontes]
    finally:
        await client.close()


def buscar_legislacao(
    query: str,
    k: int = 5,
    documento: str | None = None,
    topico: str | None = None,
    artigo: str | None = None,
) -> list[dict[str, Any]]:
    """Versão síncrona da função padronizada `buscar_legislacao(query, k)`."""
    return asyncio.run(
        buscar_legislacao_async(
            query=query,
            k=k,
            documento=documento,
            topico=topico,
            artigo=artigo,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI de teste do retriever jurídico do CTB Assist."
    )
    parser.add_argument("query", help="Pergunta ou dispositivo legal a buscar.")
    parser.add_argument("-k", type=int, default=5, help="Número de resultados.")
    parser.add_argument(
        "--documento",
        choices=["CTB", "CONTRAN", "MBFT"],
        default=None,
        help="Filtra a busca por norma específica.",
    )
    parser.add_argument(
        "--artigo",
        default=None,
        help="Filtra por número exato de artigo (ex.: 208, 165-A).",
    )
    args = parser.parse_args()

    resultados = buscar_legislacao(
        query=args.query,
        k=args.k,
        documento=args.documento,
        artigo=args.artigo,
    )

    if not resultados:
        print("Nenhum dispositivo legal encontrado para a consulta.")
        return

    for idx, item in enumerate(resultados, start=1):
        print(f"\n[{idx}] {item['referencia']} (score={item['score']})")
        print("-" * 80)
        preview = item["texto"]
        print(preview[:700] + ("..." if len(preview) > 700 else ""))


if __name__ == "__main__":
    main()
