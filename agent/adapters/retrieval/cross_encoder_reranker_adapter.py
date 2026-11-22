"""
adapters/retrieval/cross_encoder_reranker_adapter.py
 
Adapter concreto que implementa RerankerPort usando CrossEncoder da sentence-transformers.
Reordena os FonteDocumento recuperados pelo vector store por relevância semântica real,
refinando os resultados antes de enviá-los à LLM.
"""

# import asyncio
# from dataclasses import replace

# import numpy as np
# from loguru import logger
# from sentence_transformers import CrossEncoder
 
# from agent.config.configuration import settings
from agent.domain.value_objects.fonte_documento import FonteDocumento

# class CrossEncoderRerankerAdapter:
#     """
#     Implementa RerankerPort usando CrossEncoder para reranqueamento semântico.
 
#     O CrossEncoder avalia cada par (query, trecho) conjuntamente — diferente
#     do embedding que avalia cada texto isoladamente. Isso gera scores de
#     relevância mais precisos, especialmente para terminologia contábil específica
#     como "empenho", "liquidação" ou "RAP".
 
#     O modelo é recebido já instanciado via injeção de dependência — consistente
#     com o padrão do projeto (BaseChatModel, CrossEncoder, AsyncSession...).
#     A instanciação do CrossEncoder é custosa (carrega pesos do modelo) e deve
#     acontecer uma única vez no container de dependências do startup.
 
#     O predict() retorna logits brutos (sem intervalo definido). A sigmoid é
#     aplicada internamente para normalizar para [0.0, 1.0] — exigência do
#     domínio (ConfiancaResposta) e do VO FonteDocumento.
 
#     O predict() é CPU-bound e síncrono — delegado a asyncio.to_thread para
#     não bloquear o event loop do FastAPI durante o processamento em lote.
 
#     Exemplos
#     --------
#     >>> model = CrossEncoder(settings.RERANKER_MODEL, device=settings.RERANKER_DEVICE)
#     >>> adapter = CrossEncoderRerankerAdapter(model=model)
#     >>> fontes_reranqueadas = await adapter.reranquear(query, fontes_recuperadas)
#     """

#     def __init__(self, model: CrossEncoder) -> None:
#         self._model = model
#         self._top_k = settings.RERANKER_TOP_K
#         self._batch_size = settings.RERANKER_BATCH_SIZE

#         logger.debug(
#             "CrossEncoderRerankerAdapter inicializado | top_k={} | batch_size={}",
#             self._top_k,
#             self._batch_size,
#         )
    
#     # ------------------------------------------------------------------
#     # RerankerPort — implementação
#     # ------------------------------------------------------------------
 
#     async def reranquear(
#         self,
#         query: str,
#         documentos: list[FonteDocumento]
#     ) -> list[FonteDocumento]:
#         """
#         Reordena documentos por relevância semântica em relação à query.
 
#         Parâmetros
#         ----------
#         query : str
#             Pergunta do usuário (original ou reescrita) usada como referência.
#         documentos : list[FonteDocumento]
#             Documentos recuperados pelo vector store, em ordem inicial de score.
 
#         Retorna
#         -------
#         list[FonteDocumento]
#             Top-k documentos reordenados por relevância semântica,
#             do mais para o menos relevante, com score_relevancia normalizado
#             entre 0.0 e 1.0 via sigmoid.
#         """
#         if not documentos:
#             logger.debug("Nenhum documento para reranquear — retornando lista vazia.")
#             return []

#         pares = [(query, doc.trecho_preview) for doc in documentos]

#         logits = await asyncio.to_thread(
#             self._model.predict,
#             pares,
#             batch_size=self._batch_size,
#             convert_to_numpy=True,
#         )

#         scores = self._aplicar_sigmoid(logits)

#         documentos_com_score = [
#             replace(doc, score_relevancia=float(score))
#             for doc, score in zip(documentos, scores)
#         ]

#         documentos_com_score.sort(key=lambda d: d.score_relevancia or 0.0, reverse=True)
#         resultado = documentos_com_score[:self._top_k]

#         logger.info(
#             "Reranqueamento concluído | entrada={} | retornados={} | score_max={:.4f}",
#             len(documentos),
#             len(resultado),
#             resultado[0].score_relevancia or 0.0,
#         )
 
#         return resultado

#     # ------------------------------------------------------------------
#     # Auxiliares
#     # ------------------------------------------------------------------

#     def _aplicar_sigmoid(self, logits: np.ndarray) -> np.ndarray:
#         """
#         Normaliza logits brutos do CrossEncoder para o intervalo [0.0, 1.0].
 
#         O predict() do CrossEncoder retorna logits sem limites definidos
#         (ex.: -5.58, 0.0, 3.2). A sigmoid transforma esses valores em
#         probabilidades interpretáveis como grau de relevância.
 
#         Fórmula: sigmoid(x) = 1 / (1 + e^-x)
 
#         Exemplos
#         --------
#         logits  → sigmoid
#         -5.58   → 0.0037  (irrelevante)
#          0.00   → 0.5000  (neutro)
#          3.20   → 0.9608  (muito relevante)
#         """
#         return 1 / (1 + np.exp(-logits))

class NullRerankerAdapter:
    """Adapter no-op para testar o pipeline SEM reranker."""
    async def reranquear(
        self, query: str, documentos: list[FonteDocumento]
    ) -> list[FonteDocumento]:
        return documentos