"""
agent/adapters/retrieval/cross_encoder_reranker_adapter.py

Reranqueamento semântico dos trechos recuperados pelo Qdrant.

O cross-encoder avalia cada par (consulta, trecho) em conjunto, o que separa melhor
artigos parecidos (ex.: incisos do art. 181) do que a similaridade de embeddings isolados.

O modelo é executado via `fastembed` (ONNX, sem PyTorch), dependência que já vem com
`qdrant-client[fastembed]`. O adapter recebe o modelo já instanciado (injeção de dependência):
carregar os pesos é custoso e deve ocorrer uma única vez, na fábrica (`build_reranker`).

Contrato esperado do modelo: `rerank(query, documents, batch_size=...)` devolvendo um score
bruto (logit) por documento, na mesma ordem — é o contrato de `fastembed.TextCrossEncoder`.
"""

import asyncio
import math
from dataclasses import replace
from typing import Any, Iterable, Protocol

from loguru import logger

from agent.config.configuration import settings
from agent.domain.value_objects.fonte_documento import FonteDocumento


class CrossEncoderModel(Protocol):
    """Subconjunto de `fastembed.rerank.cross_encoder.TextCrossEncoder` usado aqui."""

    def rerank(
        self, query: str, documents: Iterable[str], batch_size: int = ..., **kwargs: Any
    ) -> Iterable[float]: ...


def _sigmoid(logit: float) -> float:
    """Normaliza o logit bruto para [0.0, 1.0] (exigência de `FonteDocumento`/`ConfiancaResposta`)."""
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    e = math.exp(logit)  # evita overflow para logits muito negativos
    return e / (1.0 + e)


class CrossEncoderRerankerAdapter:
    """Implementa `RerankerPort` reordenando os documentos pelo score do cross-encoder."""

    def __init__(
        self,
        model: CrossEncoderModel,
        top_k: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        self._model = model
        self._top_k = top_k or settings.RERANKER_TOP_K
        self._batch_size = batch_size or settings.RERANKER_BATCH_SIZE
        logger.debug(
            "CrossEncoderRerankerAdapter inicializado | top_k={} | batch_size={}",
            self._top_k,
            self._batch_size,
        )

    async def reranquear(
        self, query: str, documentos: list[FonteDocumento]
    ) -> list[FonteDocumento]:
        """Devolve até `top_k` documentos, do mais ao menos relevante, com score em [0, 1]."""
        if not documentos:
            return []

        textos = [doc.trecho_preview for doc in documentos]
        # predição é CPU-bound e síncrona: fora do event loop
        logits = await asyncio.to_thread(
            lambda: list(self._model.rerank(query, textos, batch_size=self._batch_size))
        )
        if len(logits) != len(documentos):
            raise ValueError(
                f"Reranker devolveu {len(logits)} scores para {len(documentos)} documentos."
            )

        pontuados = [
            replace(doc, score_relevancia=_sigmoid(float(logit)))
            for doc, logit in zip(documentos, logits)
        ]
        pontuados.sort(key=lambda d: d.score_relevancia or 0.0, reverse=True)
        resultado = pontuados[: self._top_k]

        logger.info(
            "Reranqueamento concluído | entrada={} | retornados={} | score_max={:.4f}",
            len(documentos),
            len(resultado),
            resultado[0].score_relevancia or 0.0,
        )
        return resultado


class NullRerankerAdapter:
    """Adapter no-op: mantém a ordem original (reranker desligado ou indisponível)."""

    async def reranquear(
        self, query: str, documentos: list[FonteDocumento]
    ) -> list[FonteDocumento]:
        return documentos
