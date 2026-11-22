"""
agent/adapters/vectorstores/qdrant_adapter.py

Adapter concreto que implementa VectorStorePort usando Qdrant com FastEmbed
(busca híbrida Dense + Sparse BM42 com fusão RRF).

Suporta:
- Execução local persistente em disco (`AsyncQdrantClient(path=...)`), em memória
  (`:memory:`) para testes ou via servidor Docker (`url=...`).
- IDs determinísticos (UUID5) para indexação idempotente.
- Metadados jurídicos completos (`documento`, `norma`, `artigo`, `inciso`,
  `codigo_enquadramento`, `tema`, `url`, `pagina`).
- Busca global ou filtrada por tópico/documento/artigo, com reforço automático
  quando a query cita explicitamente um número de artigo (ex.: "Art. 208").
"""

import re
import uuid

from loguru import logger
from qdrant_client import AsyncQdrantClient, models

from agent.config.configuration import settings
from agent.domain.value_objects.documento_extraido import PaginaExtraida
from agent.domain.value_objects.fonte_documento import FonteDocumento
from agent.domain.value_objects.topico import Topico

_RE_QUERY_ARTIGO = re.compile(
    r"\b(?:art\.?|artigo)\s*(\d+(?:-[A-Z])?)\b", re.IGNORECASE
)
_UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class QdrantVectorStoreAdapter:
    """Implementa VectorStorePort usando Qdrant como backend de busca híbrida."""

    COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME
    DENSE_MODEL = settings.QDRANT_DENSE_MODEL
    DENSE_VECTOR_NAME = "dense"
    SPARSE_MODEL = settings.QDRANT_SPARSE_MODEL
    SPARSE_VECTOR_NAME = "sparse"
    TOP_K = settings.QDRANT_TOP_K

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str | None = None,
    ) -> None:
        self._client = client
        self.COLLECTION_NAME = collection_name or settings.QDRANT_COLLECTION_NAME
        self._client.set_model(self.DENSE_MODEL, vector_name=self.DENSE_VECTOR_NAME)
        self._client.set_sparse_model(
            self.SPARSE_MODEL, vector_name=self.SPARSE_VECTOR_NAME
        )

    @classmethod
    async def criar(
        cls,
        client: AsyncQdrantClient,
        collection_name: str | None = None,
    ) -> "QdrantVectorStoreAdapter":
        """Factory async — garante que a collection existe antes de usar."""
        instancia = cls(client, collection_name=collection_name)
        await instancia._garantir_collection()
        return instancia

    async def _garantir_collection(self) -> None:
        if await self._client.collection_exists(self.COLLECTION_NAME):
            logger.debug("Collection '{}' já existe.", self.COLLECTION_NAME)
            return

        logger.info(
            "Criando collection '{}' com vetores dense ({}) e sparse ({})...",
            self.COLLECTION_NAME,
            self.DENSE_MODEL,
            self.SPARSE_MODEL,
        )

        await self._client.create_collection(
            collection_name=self.COLLECTION_NAME,
            on_disk_payload=True,
            vectors_config={
                self.DENSE_VECTOR_NAME: models.VectorParams(
                    size=self._client.get_embedding_size(self.DENSE_MODEL),
                    distance=models.Distance.COSINE,
                    on_disk=True,
                ),
            },
            sparse_vectors_config={
                self.SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    modifier=models.Modifier.IDF
                )
            },
        )
        logger.info("Collection '{}' criada com sucesso.", self.COLLECTION_NAME)

    # ------------------------------------------------------------------
    # VectorStorePort — implementações
    # ------------------------------------------------------------------

    async def adicionar_documentos(
        self,
        manual_id: int,
        topico: Topico,
        chunks: list[PaginaExtraida],
        batch_size: int = 64,
    ) -> None:
        """Indexa chunks no Qdrant em lotes com IDs determinísticos (idempotente)."""
        logger.info(
            "Indexando | manual_id={} | tópico='{}' | chunks={}",
            manual_id,
            topico.valor,
            len(chunks),
        )

        for inicio in range(0, len(chunks), batch_size):
            lote = chunks[inicio : inicio + batch_size]
            pontos = []
            for idx, chunk in enumerate(lote, start=inicio):
                chave_id = (
                    f"{manual_id}|{chunk.metadados.get('documento', '')}|"
                    f"{chunk.metadados.get('artigo', '')}|"
                    f"{chunk.metadados.get('codigo_enquadramento', '')}|"
                    f"{chunk.pagina}|{idx}|{chunk.texto[:120]}"
                )
                point_id = str(uuid.uuid5(_UUID_NAMESPACE, chave_id))
                pontos.append(
                    models.PointStruct(
                        id=point_id,
                        vector={
                            self.DENSE_VECTOR_NAME: models.Document(
                                text=chunk.texto, model=self.DENSE_MODEL
                            ),
                            self.SPARSE_VECTOR_NAME: models.Document(
                                text=chunk.texto, model=self.SPARSE_MODEL
                            ),
                        },
                        payload={
                            **chunk.metadados,
                            "topico": topico.valor,
                            "manual_id": manual_id,
                            "document": chunk.texto,
                            "pagina": chunk.pagina,
                        },
                    )
                )

            await self._client.upsert(
                collection_name=self.COLLECTION_NAME, points=pontos
            )

        logger.info(
            "Indexação concluída | manual_id={} | {} chunks.",
            manual_id,
            len(chunks),
        )

    async def buscar_documentos(
        self,
        query: str,
        k: int = 5,
        topico: Topico | None = None,
        documento: str | None = None,
        artigo: str | None = None,
    ) -> list[FonteDocumento]:
        """
        Executa busca híbrida (Dense + Sparse BM42 + RRF) com filtros opcionais.
        Se a query citar explicitamente um número de artigo (ex.: 'Art. 208'),
        combina correspondência exata do artigo com a busca semântica híbrida.
        """
        if not query or not query.strip():
            return []

        condicoes: list[models.Condition] = []
        if topico is not None:
            condicoes.append(
                models.FieldCondition(
                    key="topico", match=models.MatchValue(value=topico.valor)
                )
            )
        if documento:
            condicoes.append(
                models.FieldCondition(
                    key="documento", match=models.MatchValue(value=documento.upper())
                )
            )
        if artigo:
            condicoes.append(
                models.FieldCondition(
                    key="artigo", match=models.MatchValue(value=artigo.upper())
                )
            )

        filtro = models.Filter(must=condicoes) if condicoes else None

        resultados = (
            await self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                prefetch=[
                    models.Prefetch(
                        query=models.Document(text=query, model=self.DENSE_MODEL),
                        using=self.DENSE_VECTOR_NAME,
                        limit=max(k * 3, 10),
                        filter=filtro,
                    ),
                    models.Prefetch(
                        query=models.Document(text=query, model=self.SPARSE_MODEL),
                        using=self.SPARSE_VECTOR_NAME,
                        limit=max(k * 3, 10),
                        filter=filtro,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=k,
            )
        ).points

        fontes = [self._converter_para_fonte(r) for r in resultados]

        # Reforço: se o usuário mencionou explicitamente "Art. X" e nenhum filtro de artigo
        # foi aplicado, garante que o dispositivo exato apareça no topo se existir no índice.
        if not artigo:
            m_art = _RE_QUERY_ARTIGO.search(query)
            if m_art:
                art_num = m_art.group(1).upper()
                ja_presente = any(
                    (f.artigo or "").upper() == art_num for f in fontes
                )
                if not ja_presente:
                    extras = await self.buscar_documentos(
                        query=query,
                        k=2,
                        topico=topico,
                        documento=documento,
                        artigo=art_num,
                    )
                    if extras:
                        fontes = (extras + fontes)[:k]

        return fontes

    async def buscar_por_topico(
        self, query: str, topico: Topico
    ) -> list[FonteDocumento]:
        """Mantém compatibilidade com a assinatura anterior do port."""
        return await self.buscar_documentos(
            query=query, k=self.TOP_K, topico=topico
        )

    async def remover_por_manual(self, manual_id: int) -> None:
        logger.info("Removendo chunks do manual_id={}...", manual_id)
        await self._client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="manual_id", match=models.MatchValue(value=manual_id)
                        )
                    ]
                )
            ),
        )

    def _converter_para_fonte(self, ponto) -> FonteDocumento:
        payload = ponto.payload or {}
        return FonteDocumento(
            pagina=int(payload.get("pagina", 1)),
            trecho_preview=payload.get("document", ""),
            score_relevancia=float(ponto.score) if ponto.score is not None else None,
            documento=str(payload.get("documento", "CTB")),
            norma=str(payload.get("norma", "Lei nº 9.503/1997 (CTB)")),
            artigo=payload.get("artigo"),
            inciso=payload.get("inciso"),
            codigo_enquadramento=payload.get("codigo_enquadramento"),
            tema=payload.get("tema"),
            url=payload.get("url"),
            origem=payload.get("origem"),
        )
