"""Testes do FastMCPAdapter contra o servidor CTB Tools real (stdio, sem rede)."""

import pytest

from agent.adapters.mcp import FastMCPAdapter
from mcp_servers.config import servers

SO_CTB = {"ctb_tools": servers["ctb_tools"]}


@pytest.fixture
def adapter() -> FastMCPAdapter:
    return FastMCPAdapter(SO_CTB, timeout_chamada=30)


async def test_lista_ferramentas_com_schema(adapter):
    ferramentas = {f.nome: f for f in await adapter.listar_ferramentas()}
    assert set(ferramentas) == {
        "ctb_tools_calcular_pontos",
        "ctb_tools_calcular_valor_multas",
        "ctb_tools_analisar_pontuacao",
        "ctb_tools_validar_notificacao",
    }
    f = ferramentas["ctb_tools_calcular_pontos"]
    assert f.servidor == "ctb_tools"
    assert "gravissima" in f.parametros["properties"]["infracoes"]["items"]["properties"]["natureza"]["enum"]


async def test_catalogo_e_cacheado(adapter):
    primeira = await adapter.listar_ferramentas()
    assert await adapter.listar_ferramentas() is primeira


async def test_executa_calculo_deterministico(adapter):
    r = await adapter.executar_ferramenta(
        "ctb_tools_calcular_pontos",
        {"infracoes": [{"natureza": "grave", "quantidade": 2}, {"natureza": "gravissima"}]},
    )
    assert r.sucesso and r.servidor == "ctb_tools"
    assert r.resultado["total_pontos"] == 17


async def test_argumentos_invalidos_viram_erro_sem_excecao(adapter):
    r = await adapter.executar_ferramenta(
        "ctb_tools_calcular_pontos", {"infracoes": [{"natureza": "xx"}]}
    )
    assert not r.sucesso and "natureza" in r.erro


async def test_ferramenta_inexistente(adapter):
    r = await adapter.executar_ferramenta("inventada", {})
    assert not r.sucesso and "inexistente" in r.erro


async def test_servidor_indisponivel_nao_derruba():
    quebrado = FastMCPAdapter(
        {"ctb_tools": {"command": "/nao/existe", "args": []}}, timeout_chamada=5
    )
    assert await quebrado.listar_ferramentas() == []
    r = await quebrado.executar_ferramenta("ctb_tools_calcular_pontos", {"infracoes": []})
    assert not r.sucesso and r.erro


async def test_schema_chega_formatado_ao_prompt(adapter):
    ferramentas = await adapter.listar_ferramentas()
    texto = next(f for f in ferramentas if f.nome.endswith("calcular_pontos")).formatar_para_prompt()
    assert "`ctb_tools_calcular_pontos`" in texto
    assert "argumentos (JSON Schema)" in texto and "gravissima" in texto
    assert '"title"' not in texto
