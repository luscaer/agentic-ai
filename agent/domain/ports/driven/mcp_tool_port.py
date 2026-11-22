"""
agent/domain/ports/driven/mcp_tool_port.py

Port (contrato) para descoberta e execução de ferramentas MCP
(servidor FastMCP próprio do CTB e servidor MCP Fetch da comunidade).
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FerramentaMCPInfo:
    """Descrição de uma ferramenta MCP disponível para o roteador."""

    nome: str
    servidor: str
    descricao: str
    parametros: dict[str, Any] = field(default_factory=dict)

    def formatar_para_prompt(self) -> str:
        """Linha do catálogo do roteador: nome, servidor, descrição e JSON Schema dos argumentos."""
        texto = f"- `{self.nome}` ({self.servidor}): {self.descricao}"
        if self.parametros:
            schema = json.dumps(
                _sem_titulos(self.parametros), ensure_ascii=False, separators=(",", ":")
            )
            texto += f"\n  argumentos (JSON Schema): {schema}"
        return texto


def _sem_titulos(schema: Any) -> Any:
    """Remove `title` gerados automaticamente, que só gastam tokens do roteador."""
    if isinstance(schema, dict):
        return {
            k: _sem_titulos(v)
            for k, v in schema.items()
            if not (k == "title" and isinstance(v, str))
        }
    if isinstance(schema, list):
        return [_sem_titulos(i) for i in schema]
    return schema


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
