"""Testes do reranker cross-encoder (modelo falso: não baixa pesos nem usa rede)."""

import math

import pytest

from agent.adapters.orchestrator.nodes.buscar_documentos_node import BuscarDocumentosNode
from agent.adapters.retrieval.cross_encoder_reranker_adapter import (
    CrossEncoderRerankerAdapter,
    NullRerankerAdapter,
)
from agent.config import factory
from agent.config.configuration import settings
from agent.domain.entities.consulta import Consulta
from agent.domain.value_objects.fonte_documento import FonteDocumento
from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.topico import Topico


class ModeloFalso:
    """Dá a cada texto o logit definido em `logits` (chave: texto)."""

    def __init__(self, logits: dict[str, float]) -> None:
        self.logits = logits
        self.chamadas: list[tuple[str, list[str], int]] = []

    def rerank(self, query, documents, batch_size=64, **_):
        documents = list(documents)
        self.chamadas.append((query, documents, batch_size))
        return [self.logits[d] for d in documents]


def doc(texto: str, artigo: str, score: float = 0.5) -> FonteDocumento:
    return FonteDocumento(trecho_preview=texto, artigo=artigo, score_relevancia=score)


DOCS = [doc("a", "1", 0.9), doc("b", "2", 0.8), doc("c", "3", 0.7)]


async def test_reordena_pelo_score_do_cross_encoder():
    modelo = ModeloFalso({"a": -3.0, "b": 4.0, "c": 0.0})
    r = await CrossEncoderRerankerAdapter(modelo, top_k=5, batch_size=2).reranquear("q", DOCS)
    assert [d.artigo for d in r] == ["2", "3", "1"]
    assert modelo.chamadas == [("q", ["a", "b", "c"], 2)]


async def test_score_normalizado_por_sigmoid():
    modelo = ModeloFalso({"a": 0.0, "b": 3.2, "c": -5.58})
    r = {d.artigo: d.score_relevancia for d in await CrossEncoderRerankerAdapter(modelo).reranquear("q", DOCS)}
    assert r["1"] == pytest.approx(0.5)
    assert r["2"] == pytest.approx(1 / (1 + math.exp(-3.2)))
    assert all(0.0 <= s <= 1.0 for s in r.values())


async def test_logits_extremos_nao_estouram():
    modelo = ModeloFalso({"a": -1000.0, "b": 1000.0, "c": 0.0})
    r = await CrossEncoderRerankerAdapter(modelo).reranquear("q", DOCS)
    assert r[0].score_relevancia == 1.0 and r[-1].score_relevancia == 0.0


async def test_top_k_trunca_e_nao_altera_originais():
    modelo = ModeloFalso({"a": 1.0, "b": 2.0, "c": 3.0})
    r = await CrossEncoderRerankerAdapter(modelo, top_k=2).reranquear("q", DOCS)
    assert [d.artigo for d in r] == ["3", "2"]
    assert [d.score_relevancia for d in DOCS] == [0.9, 0.8, 0.7]  # VO imutável


async def test_lista_vazia_nao_chama_o_modelo():
    modelo = ModeloFalso({})
    assert await CrossEncoderRerankerAdapter(modelo).reranquear("q", []) == []
    assert modelo.chamadas == []


async def test_quantidade_de_scores_incoerente_falha_claramente():
    class Ruim:
        def rerank(self, query, documents, batch_size=64, **_):
            return [1.0]

    with pytest.raises(ValueError, match="scores"):
        await CrossEncoderRerankerAdapter(Ruim()).reranquear("q", DOCS)


async def test_nulo_mantem_a_ordem():
    assert await NullRerankerAdapter().reranquear("q", DOCS) == DOCS


async def test_no_de_busca_usa_o_reranker_e_atualiza_confianca():
    class Store:
        async def buscar_documentos(self, **_):
            return list(DOCS)

    modelo = ModeloFalso({"a": -2.0, "b": 5.0, "c": 0.0})
    no = BuscarDocumentosNode(Store(), CrossEncoderRerankerAdapter(modelo, top_k=2))
    consulta = Consulta(
        sessao_id="s", pergunta_original="q", topico=Topico(valor="transito_ctb"),
        historico=HistoricoConversa(), resumo=None, pergunta_reescrita=None,
    )
    out = await no({"consulta": consulta})
    assert [d.artigo for d in out["documentos_recuperados"]] == ["2", "3"]
    assert out["confianca"].valor == pytest.approx(1 / (1 + math.exp(-5.0)))


def _config(monkeypatch, **campos):
    """`Settings` é imutável: substitui o objeto usado pela fábrica por uma cópia alterada."""
    monkeypatch.setattr(factory, "settings", settings.model_copy(update=campos))


def test_fabrica_respeita_reranker_desligado(monkeypatch):
    _config(monkeypatch, RERANKER_ENABLED=False)
    assert isinstance(factory.build_reranker(), NullRerankerAdapter)


def test_fabrica_cai_para_nulo_se_modelo_falha(monkeypatch):
    import fastembed.rerank.cross_encoder as ce

    def explode(*a, **k):
        raise RuntimeError("sem rede")

    _config(monkeypatch, RERANKER_ENABLED=True)
    monkeypatch.setattr(ce, "TextCrossEncoder", explode)
    assert isinstance(factory.build_reranker(), NullRerankerAdapter)


def test_fabrica_monta_adapter_real_com_o_modelo_configurado(monkeypatch):
    import fastembed.rerank.cross_encoder as ce

    criados = []
    _config(monkeypatch, RERANKER_ENABLED=True)
    monkeypatch.setattr(ce, "TextCrossEncoder", lambda model_name: criados.append(model_name) or ModeloFalso({}))
    assert isinstance(factory.build_reranker(), CrossEncoderRerankerAdapter)
    assert criados == [settings.RERANKER_MODEL]
