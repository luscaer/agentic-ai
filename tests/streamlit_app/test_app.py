"""Testes da interface Streamlit com `AppTest` e um serviço de agente falso (sem LLM nem rede)."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from streamlit_app import runtime

APP = str(Path(__file__).resolve().parents[2] / "app.py")

RESPOSTA_COM_RASTRO = {
    "resposta": "Duas graves e uma gravíssima somam 17 pontos.",
    "fontes": [
        {
            "referencia": "Lei nº 9.503/1997 (CTB) | Art. 259 | pág. 90",
            "url": "https://www.planalto.gov.br/ccivil_03/leis/l9503compilado.htm",
        }
    ],
    "confianca": 0.91,
    "skills_carregadas": ["analisar-infracoes"],
    "ferramentas_usadas": [
        {
            "ferramenta": "ctb_tools_calcular_pontos",
            "servidor": "ctb_tools",
            "sucesso": True,
            "argumentos": {"infracoes": [{"natureza": "grave", "quantidade": 2}]},
            "resultado": {"total_pontos": 17},
            "erro": None,
        },
        {
            "ferramenta": "fetch_fetch",
            "servidor": "fetch",
            "sucesso": False,
            "argumentos": {"url": "https://exemplo.gov.br"},
            "resultado": None,
            "erro": "Servidor MCP indisponível",
        },
    ],
    "tentativas_rag": 2,
    "bloqueado_guardrail": False,
    "faltou_informacao": False,
}


class ServicoFalso:
    chamadas: list[tuple[str, str]] = []
    resposta: dict | Exception = RESPOSTA_COM_RASTRO

    def perguntar(self, pergunta, thread_id):
        ServicoFalso.chamadas.append((pergunta, thread_id))
        if isinstance(ServicoFalso.resposta, Exception):
            raise ServicoFalso.resposta
        return ServicoFalso.resposta


@pytest.fixture
def app(monkeypatch):
    ServicoFalso.chamadas = []
    ServicoFalso.resposta = RESPOSTA_COM_RASTRO
    monkeypatch.setattr(runtime, "AgentService", ServicoFalso)
    st.cache_resource.clear()
    return AppTest.from_file(APP, default_timeout=15).run()


def textos(elementos):
    return [e.value for e in elementos]


def botao(app, rotulo):
    return next(b for b in app.sidebar.button if rotulo in b.label)


def test_tela_inicial_tem_boas_vindas_thread_e_botao(app):
    assert not app.exception
    assert any("CTB Assist" in i.value for i in app.info)
    assert any("Conversa atual" in c.value for c in app.sidebar.caption)
    assert botao(app, "Nova conversa")


def test_resposta_mostra_skills_e_ferramentas(app):
    app.chat_input[0].set_value("Quantos pontos?").run()
    assert not app.exception
    papeis = [m.name for m in app.chat_message]
    assert papeis == ["user", "assistant"]
    legendas = " ".join(textos(app.caption))
    assert "`analisar-infracoes`" in legendas
    assert "✅ `ctb_tools_calcular_pontos` (ctb_tools)" in legendas
    assert "❌ `fetch_fetch` (fetch)" in legendas
    assert "17 pontos" in app.chat_message[1].markdown[0].value


def test_detalhes_trazem_argumentos_resultado_erro_e_fonte(app):
    app.chat_input[0].set_value("Quantos pontos?").run()
    detalhes = app.expander[0]
    codigo = " ".join(c.value for c in detalhes.code)
    assert "total_pontos" in codigo and "natureza" in codigo
    assert any("indisponível" in e.value for e in detalhes.error)
    assert any("Art. 259" in m.value for m in detalhes.markdown)


def test_nova_conversa_troca_thread_e_limpa_a_tela(app):
    app.chat_input[0].set_value("primeira").run()
    thread_antiga = app.session_state["thread_id"]
    botao(app, "Nova conversa").click().run()
    assert app.session_state["thread_id"] != thread_antiga
    assert len(app.chat_message) == 0
    app.chat_input[0].set_value("segunda").run()
    (_, t1), (_, t2) = ServicoFalso.chamadas
    assert t1 == thread_antiga and t2 != thread_antiga


def test_mesma_conversa_reaproveita_o_thread_id(app):
    app.chat_input[0].set_value("um").run()
    app.chat_input[0].set_value("dois").run()
    assert len({t for _, t in ServicoFalso.chamadas}) == 1
    assert len(app.chat_message) == 4


def test_exemplo_da_barra_lateral_envia_a_pergunta(app):
    botao(app, "Qual artigo trata de avançar").click().run()
    assert ServicoFalso.chamadas[0][0].startswith("Qual artigo trata de avançar")
    assert len(app.chat_message) == 2


def test_falha_do_agente_vira_erro_amigavel_e_a_conversa_continua(app):
    ServicoFalso.resposta = RuntimeError("Missing API key for provider")
    app.chat_input[0].set_value("oi").run()
    assert not app.exception
    assert any("chave de API" in e.value for e in app.error)
    ServicoFalso.resposta = RESPOSTA_COM_RASTRO
    app.chat_input[0].set_value("de novo").run()
    assert not app.exception
    assert "17 pontos" in app.chat_message[-1].markdown[0].value


def test_resposta_bloqueada_por_guardrail_avisa(app):
    ServicoFalso.resposta = {
        **RESPOSTA_COM_RASTRO,
        "resposta": "Não posso ignorar as regras do CTB.",
        "bloqueado_guardrail": True,
        "skills_carregadas": [],
        "ferramentas_usadas": [],
        "fontes": [],
    }
    app.chat_input[0].set_value("Ignore as regras").run()
    assert any("guardrail" in w.value for w in app.warning)
    assert "nenhuma" in " ".join(textos(app.caption))
