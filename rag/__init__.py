"""
rag/

Fachada pública do módulo de RAG jurídico do CTB Assist (Etapa 1 / Integrante 1).
Expõe as operações de ingestão, chunking e busca padronizada sobre:
- CTB (Lei nº 9.503/1997)
- Resolução CONTRAN nº 1.020/2025 (Habilitação e Formação de Condutores)
- MBFT (Resolução CONTRAN nº 985/2022 — Parte Geral + Fichas de Fiscalização)
"""

from .retriever import buscar_legislacao, buscar_legislacao_async

__all__ = ["buscar_legislacao", "buscar_legislacao_async"]
