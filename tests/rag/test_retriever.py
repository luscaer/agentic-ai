"""
tests/rag/test_retriever.py

Testes da fachada `buscar_legislacao` (Requisitos R5, R8, R9):
- Consulta direta por artigo
- Pergunta em linguagem natural
- Filtro por documento (CTB / CONTRAN / MBFT)
- Consulta vazia / sem resultados
"""

import pytest

from agent.domain.value_objects.fonte_documento import FonteDocumento
from rag.retriever import buscar_legislacao_async


class FakeVectorStore:
    """Stub determinístico de VectorStorePort para validar a fachada `rag/retriever.py`."""

    def __init__(self, docs: list[FonteDocumento]) -> None:
        self._docs = docs

    async def buscar_documentos(
        self,
        query: str,
        k: int = 5,
        topico=None,
        documento: str | None = None,
        artigo: str | None = None,
    ) -> list[FonteDocumento]:
        q = query.lower()
        filtrados = []
        for d in self._docs:
            if documento and d.documento.upper() != documento.upper():
                continue
            if artigo and (d.artigo or "").upper() != artigo.upper():
                continue
            score = 0.0
            for termo in q.split():
                if len(termo) > 2 and termo in d.trecho_preview.lower():
                    score += 0.2
            if d.artigo and d.artigo.lower() in q:
                score += 0.8
            if score > 0:
                filtrados.append((score, d))

        filtrados.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in filtrados[:k]]


@pytest.fixture
def fake_store() -> FakeVectorStore:
    return FakeVectorStore(
        [
            FonteDocumento(
                pagina=62,
                trecho_preview="Art. 208. Avançar o sinal vermelho do semáforo ou o de parada obrigatória: Infração - gravíssima; Penalidade - multa.",
                score_relevancia=0.92,
                documento="CTB",
                norma="Lei nº 9.503/1997 (CTB)",
                artigo="208",
                tema="infracoes",
                url="https://www.planalto.gov.br/ccivil_03/leis/l9503compilado.htm",
            ),
            FonteDocumento(
                pagina=11,
                trecho_preview="Art. 36. Após a aprovação nos exames teóricos e a expedição da Licença de Aprendizagem, o candidato deverá iniciar aulas práticas junto a instrutores de trânsito autônomos ou autoescolas.",
                score_relevancia=0.89,
                documento="CONTRAN",
                norma="Resolução CONTRAN nº 1.020/2025",
                artigo="36",
                tema="habilitacao",
            ),
            FonteDocumento(
                pagina=101,
                trecho_preview="# Ficha MBFT 516-91 — Art. 165\nÉ vedada a lavratura simultânea de autos de infração com base nos artigos 165 e 165-A na mesma abordagem.",
                score_relevancia=0.88,
                documento="MBFT",
                norma="Resolução CONTRAN nº 985/2022 (MBFT)",
                artigo="165",
                codigo_enquadramento="516-91",
                tema="fiscalizacao_mbft",
            ),
        ]
    )


@pytest.mark.asyncio
async def test_retriever_busca_direta_por_artigo(fake_store: FakeVectorStore) -> None:
    res = await buscar_legislacao_async(
        "Art. 208 sinal vermelho", k=3, vector_store=fake_store
    )
    assert len(res) >= 1
    assert res[0]["artigo"] == "208"
    assert res[0]["documento"] == "CTB"
    assert "Lei nº 9.503/1997" in res[0]["fonte"]


@pytest.mark.asyncio
async def test_retriever_filtro_resolucao_contran(fake_store: FakeVectorStore) -> None:
    res = await buscar_legislacao_async(
        "instrutores autônomos aulas práticas",
        k=3,
        documento="CONTRAN",
        vector_store=fake_store,
    )
    assert len(res) == 1
    assert res[0]["documento"] == "CONTRAN"
    assert res[0]["artigo"] == "36"


@pytest.mark.asyncio
async def test_retriever_filtro_mbft(fake_store: FakeVectorStore) -> None:
    res = await buscar_legislacao_async(
        "lavratura simultânea artigos 165 e 165-A",
        k=3,
        documento="MBFT",
        vector_store=fake_store,
    )
    assert len(res) == 1
    assert res[0]["codigo_enquadramento"] == "516-91"


@pytest.mark.asyncio
async def test_retriever_consulta_vazia_ou_fora_escopo(
    fake_store: FakeVectorStore,
) -> None:
    assert await buscar_legislacao_async("   ", vector_store=fake_store) == []
    assert (
        await buscar_legislacao_async(
            "receita de lasanha bolonhesa", vector_store=fake_store
        )
        == []
    )
