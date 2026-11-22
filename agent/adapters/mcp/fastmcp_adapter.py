import json
import time
from typing import Any

from fastmcp import Client
from loguru import logger

from agent.domain.ports.driven.mcp_tool_port import (
    FerramentaMCPInfo,
    ResultadoFerramentaMCP,
)


class FastMCPAdapter:
    """Implementa `MCPToolPort` sobre `fastmcp.Client` com vários servidores (stdio)."""

    def __init__(
        self,
        servers: dict[str, dict[str, Any]],
        timeout_chamada: float = 60.0,
        ttl_catalogo: float = 300.0,
    ) -> None:
        self._servers = servers
        self._timeout_chamada = timeout_chamada
        self._ttl_catalogo = ttl_catalogo
        self._catalogo: list[FerramentaMCPInfo] = []
        self._catalogo_em: float | None = None

    def _cliente(self) -> Client:
        return Client({"mcpServers": self._servers})

    def _prefixo_manual(self) -> str | None:
        """Com um único servidor o FastMCP não prefixa; mantemos o nome canônico igual."""
        return next(iter(self._servers)) + "_" if len(self._servers) == 1 else None

    def _servidor_de(self, nome_ferramenta: str) -> str:
        """Com vários servidores o FastMCP prefixa o nome (`<servidor>_<ferramenta>`)."""
        candidatos = [s for s in self._servers if nome_ferramenta.startswith(f"{s}_")]
        return max(candidatos, key=len) if candidatos else "desconhecido"

    async def listar_ferramentas(self) -> list[FerramentaMCPInfo]:
        agora = time.monotonic()
        if (
            self._catalogo_em is not None
            and self._catalogo
            and agora - self._catalogo_em < self._ttl_catalogo
        ):
            return self._catalogo
        try:
            async with self._cliente() as client:
                ferramentas = await client.list_tools()
        except BaseException as erro:  # inclui ExceptionGroup do anyio
            if isinstance(erro, (KeyboardInterrupt, SystemExit)):
                raise
            logger.error("Falha ao listar ferramentas MCP: {!r}", erro)
            return []

        self._catalogo = [
            FerramentaMCPInfo(
                nome=f"{self._prefixo_manual() or ''}{t.name}",
                servidor=self._servidor_de(f"{self._prefixo_manual() or ''}{t.name}"),
                descricao=(t.description or "").strip(),
                parametros=dict(getattr(t, "input_schema", None) or t.inputSchema or {}),
            )
            for t in ferramentas
        ]
        self._catalogo_em = agora
        logger.info("Ferramentas MCP disponíveis: {}", [f.nome for f in self._catalogo])
        return self._catalogo

    async def executar_ferramenta(
        self, nome: str, argumentos: dict[str, Any]
    ) -> ResultadoFerramentaMCP:
        servidor = self._servidor_de(nome)

        def falha(erro: str) -> ResultadoFerramentaMCP:
            return ResultadoFerramentaMCP(
                ferramenta=nome,
                servidor=servidor,
                sucesso=False,
                argumentos=argumentos,
                erro=erro,
            )

        # Rejeita nomes inventados pelo LLM antes de abrir qualquer conexão de chamada.
        catalogo = await self.listar_ferramentas()
        if catalogo and nome not in {f.nome for f in catalogo}:
            return falha(
                f"Ferramenta '{nome}' inexistente. Disponíveis: {[f.nome for f in catalogo]}"
            )

        try:
            async with self._cliente() as client:
                nome_remoto = nome.removeprefix(self._prefixo_manual() or "\0")
                resposta = await client.call_tool(
                    nome_remoto,
                    argumentos,
                    timeout=self._timeout_chamada,
                    raise_on_error=False,
                )
        except BaseException as erro:
            if isinstance(erro, (KeyboardInterrupt, SystemExit)):
                raise
            logger.error("Falha ao executar ferramenta MCP '{}': {!r}", nome, erro)
            return falha(f"Servidor MCP indisponível ou sem resposta: {erro!r}")

        conteudo = self._extrair_conteudo(resposta)
        if resposta.is_error:
            return falha(str(conteudo))
        return ResultadoFerramentaMCP(
            ferramenta=nome,
            servidor=servidor,
            sucesso=True,
            argumentos=argumentos,
            resultado=conteudo,
        )

    @staticmethod
    def _extrair_conteudo(resposta: Any) -> Any:
        """Prefere o resultado estruturado; cai para o texto (ex.: páginas do Fetch)."""
        if resposta.structured_content is not None:
            return resposta.structured_content
        textos = [c.text for c in resposta.content if getattr(c, "type", "") == "text"]
        texto = "\n".join(textos)
        try:
            return json.loads(texto)
        except (ValueError, TypeError):
            return texto
