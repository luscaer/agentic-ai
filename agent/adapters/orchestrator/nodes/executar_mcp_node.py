"""
agent/adapters/orchestrator/nodes/executar_mcp_node.py

Nó de execução de ferramentas MCP (servidor FastMCP próprio e MCP Fetch).
Registra o histórico de ferramentas chamadas em `tool_results` para o Streamlit.
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.ports.driven.mcp_tool_port import MCPToolPort


class ExecutarMCPNode:
    """Aciona a ferramenta MCP escolhida pelo RoteadorAgenteNode."""

    def __init__(self, mcp_port: MCPToolPort) -> None:
        self._mcp_port = mcp_port

    async def __call__(self, state: AgenteState) -> dict:
        decisao = state.get("decisao_roteador")
        tool_results = list(state.get("tool_results", []))

        if not decisao or not decisao.ferramenta_mcp:
            return {"tool_results": tool_results}

        logger.info(
            "Executando ferramenta MCP | nome='{}' | args={}",
            decisao.ferramenta_mcp,
            decisao.argumentos_mcp,
        )

        resultado = await self._mcp_port.executar_ferramenta(
            nome=decisao.ferramenta_mcp,
            argumentos=decisao.argumentos_mcp,
        )
        tool_results.append(resultado.to_dict())

        return {"tool_results": tool_results}
