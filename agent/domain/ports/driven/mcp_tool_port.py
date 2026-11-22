"""
agent/domain/ports/driven/mcp_tool_port.py

Port (contrato) para descoberta e execução de ferramentas MCP
(servidor FastMCP próprio do CTB e servidor MCP Fetch da comunidade).
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FerramentaMCPInfo:
    """Descrição de uma ferramenta MCP disponível para o roteador."""

    nome: str
    servidor: str
    descricao: str
    parametros: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoFerramentaMCP:
    """Resultado padronizado de uma chamada a ferramenta MCP."""

    ferramenta: str
    servidor: str
    sucesso: bool
    argumentos: dict[str, Any] = field(default_factory=dict)
    resultado: Any = None
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ferramenta": self.ferramenta,
            "servidor": self.servidor,
            "sucesso": self.sucesso,
            "argumentos": self.argumentos,
            "resultado": self.resultado,
            "erro": self.erro,
        }


class MCPToolPort(Protocol):
    """Contrato para integração do grafo LangGraph com servidores MCP."""

    async def listar_ferramentas(self) -> list[FerramentaMCPInfo]:
        """Lista as ferramentas disponíveis nos servidores MCP conectados."""
        ...

    async def executar_ferramenta(
        self, nome: str, argumentos: dict[str, Any]
    ) -> ResultadoFerramentaMCP:
        """Executa uma ferramenta MCP e retorna resultado estruturado sem derrubar o grafo."""
        ...
