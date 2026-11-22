"""Grafo LangGraph + FastMCPAdapter real: o roteador recebe os schemas e o MCP é executado."""

import json
import re

from agent.adapters.guardrails.default_guardrail_adapter import DefaultGuardrailAdapter
from agent.adapters.mcp import FastMCPAdapter
from agent.adapters.orchestrator.langgraph_adapter import LangGraphOrchestratorAdapter
from agent.adapters.retrieval.cross_encoder_reranker_adapter import NullRerankerAdapter
from agent.adapters.skills.filesystem_skill_adapter import FileSystemSkillAdapter
from agent.domain.ports.driven.llm_port import DecisaoRoteador
from mcp_servers.config import servers
from tests.agent.test_langgraph_agentic import FakeAgenticLLM, FakeVectorStore


class LLMQueLeOSchema(FakeAgenticLLM):
    """Só chama a ferramenta se o catálogo do roteador trouxer nome exato e schema."""

    def __init__(self) -> None:
        super().__init__(forcar_reformulacao=False)
        self.catalogo_visto = ""

    async def decidir_proxima_acao(self, **kw) -> DecisaoRoteador:
        self.catalogo_visto = kw["ferramentas_mcp_disponiveis"]
        if "Nenhuma ferramenta MCP executada" in kw["resultados_mcp_resumo"] and kw["tentativas_rag"] >= 1:
            nome = re.search(r"`(\w*calcular_pontos)`", self.catalogo_visto).group(1)
            schema = json.loads(self.catalogo_visto.split("argumentos (JSON Schema): ")[1].splitlines()[0])
            assert "infracoes" in schema["properties"]
            return DecisaoRoteador(
                acao="chamar_mcp",
                justificativa="cálculo",
                ferramenta_mcp=nome,
                argumentos_mcp={"infracoes": [{"natureza": "grave", "quantidade": 2}, {"natureza": "gravissima"}]},
            )
        return await super().decidir_proxima_acao(**kw)


async def test_roteador_recebe_schema_e_executa_mcp_real():
    llm = LLMQueLeOSchema()
    grafo = LangGraphOrchestratorAdapter(
        llm=llm,
        vector_store=FakeVectorStore(),
        reranker=NullRerankerAdapter(),
        skill_port=FileSystemSkillAdapter("./skills"),
        mcp_port=FastMCPAdapter({"ctb_tools": servers["ctb_tools"]}, timeout_chamada=30),
        guardrail_port=DefaultGuardrailAdapter(),
    )
    r = await grafo.executar(
        pergunta="Duas graves e uma gravíssima: quantos pontos?", sessao_id="t-mcp-real"
    )
    assert "gravissima" in llm.catalogo_visto  # schema chegou ao roteador
    uso = r.ferramentas_usadas[0]
    assert uso["ferramenta"] == "ctb_tools_calcular_pontos" and uso["sucesso"]
    assert uso["resultado"]["total_pontos"] == 17
