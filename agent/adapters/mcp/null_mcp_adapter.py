"""
agent/adapters/mcp/null_mcp_adapter.py

Adapter de fallback para MCPToolPort quando os servidores MCP (FastMCP próprio
e MCP Fetch do Integrante 2) ainda não estão conectados.
"""

from typing import Any

from agent.domain.ports.driven.mcp_tool_port import (
    FerramentaMCPInfo,
    ResultadoFerramentaMCP,
)


class NullMCPAdapter:
    """Retorna lista vazia de ferramentas e resposta graciosa se chamado."""

    async def listar_ferramentas(self) -> list[FerramentaMCPInfo]:
        return []

    async def executar_ferramenta(
        self, nome: str, argumentos: dict[str, Any]
    ) -> ResultadoFerramentaMCP:
        return ResultadoFerramentaMCP(
            ferramenta=nome,
            servidor="indisponivel",
            sucesso=False,
            argumentos=argumentos,
            erro="Nenhum servidor MCP está conectado no momento.",
        )
