"""
agent/adapters/orchestrator/nodes/buscar_documentos_node.py

Nó de recuperação híbrida do RAG Agêntico (Qdrant Dense + Sparse BM42 + Reranker).
Acumula e deduplica evidências ao longo das tentativas de reformulação.
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.config.configuration import settings
from agent.domain.ports.driven.reranker_port import RerankerPort
from agent.domain.ports.driven.vector_store_port import VectorStorePort
from agent.domain.value_objects.confianca_resposta import ConfiancaResposta
from agent.domain.value_objects.fonte_documento import FonteDocumento


class BuscarDocumentosNode:
    """Executa busca híbrida e reranqueamento sobre CTB, Resolução 1.020/2025 e MBFT."""

    def __init__(
        self,
        vector_store: VectorStorePort,
        reranker: RerankerPort,
        top_k: int | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._reranker = reranker
        self._top_k = top_k or settings.QDRANT_TOP_K

    async def __call__(self, state: AgenteState) -> dict:
        consulta = state["consulta"]
        query = state.get("query_atual") or consulta.pergunta_reescrita or consulta.pergunta_original
        filtro_documento = state.get("filtro_documento")
        tentativas = state.get("retrieval_attempts", 0) + 1

        logger.info(
            "Nó buscar_documentos (tentativa {}) | doc_filter={} | query='{}'",
            tentativas,
            filtro_documento,
            query,
        )

        novos_docs = await self._vector_store.buscar_documentos(
            query=query,
            k=self._top_k,
            topico=None,
            documento=filtro_documento,
        )

        if novos_docs:
            novos_docs = await self._reranker.reranquear(
                query=query,
                documentos=novos_docs,
            )

        # Acumula evidências sem duplicar trechos já recuperados em tentativas anteriores
        acumulados: list[FonteDocumento] = list(state.get("documentos_recuperados", []))
        chaves_vistas = {
            (d.documento, d.artigo, d.codigo_enquadramento, d.pagina, d.trecho_preview[:80])
            for d in acumulados
        }
        for doc in novos_docs:
            chave = (
                doc.documento,
                doc.artigo,
                doc.codigo_enquadramento,
                doc.pagina,
                doc.trecho_preview[:80],
            )
            if chave not in chaves_vistas:
                acumulados.append(doc)
                chaves_vistas.add(chave)

        # Mantém os mais relevantes ordenados por score
        acumulados.sort(key=lambda d: d.score_relevancia or 0.0, reverse=True)
        acumulados = acumulados[: max(self._top_k, 8)]

        maior_score = (
            min(max(acumulados[0].score_relevancia or 0.0, 0.0), 1.0)
            if acumulados
            else 0.0
        )

        return {
            "retrieval_attempts": tentativas,
            "documentos_recuperados": acumulados,
            "retrieved_docs": [d.to_dict() for d in acumulados],
            "confianca": ConfiancaResposta(valor=maior_score),
        }
