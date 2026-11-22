"""Testes da ponte assíncrona: um único event loop de fundo e orquestrador criado uma vez."""

import asyncio
import threading

import pytest

from streamlit_app import runtime


def test_runner_usa_sempre_o_mesmo_loop_e_thread():
    runner = runtime.AsyncRunner()

    async def info():
        return id(asyncio.get_running_loop()), threading.current_thread().name

    primeiro, segundo = runner.run(info()), runner.run(info())
    assert primeiro == segundo
    assert primeiro[1] == "ctb-assist-loop"


def test_runner_propaga_excecoes():
    runner = runtime.AsyncRunner()

    async def falha():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        runner.run(falha())


def test_servico_cria_o_orquestrador_uma_vez_e_repassa_o_thread_id(monkeypatch):
    criados, recebidos = [], []

    async def fabrica():
        criados.append(1)
        return "orq"

    async def turno(pergunta, thread_id, orquestrador):
        recebidos.append((pergunta, thread_id, orquestrador))
        return {"resposta": "ok"}

    monkeypatch.setattr(runtime, "executar_agente_async", turno)
    servico = runtime.AgentService(runtime.AsyncRunner(), fabrica)

    assert servico.perguntar("a", "t1") == {"resposta": "ok"}
    servico.perguntar("b", "t2")
    assert len(criados) == 1
    assert recebidos == [("a", "t1", "orq"), ("b", "t2", "orq")]


def test_falha_ao_criar_orquestrador_tenta_de_novo_no_turno_seguinte(monkeypatch):
    tentativas = []

    async def fabrica():
        tentativas.append(1)
        if len(tentativas) == 1:
            raise RuntimeError("sem chave")
        return "orq"

    async def turno(pergunta, thread_id, orquestrador):
        return {"resposta": "ok"}

    monkeypatch.setattr(runtime, "executar_agente_async", turno)
    servico = runtime.AgentService(runtime.AsyncRunner(), fabrica)

    with pytest.raises(RuntimeError, match="sem chave"):
        servico.perguntar("a", "t")
    assert servico.perguntar("b", "t") == {"resposta": "ok"}
    assert len(tentativas) == 2
