import argparse
import asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp_servers.config import servers


async def main(url: str | None = None):
    async with Client({"mcpServers": servers}) as client:
        print("Ferramentas:", [tool.name for tool in await client.list_tools()])
        if url:
            try:
                resultado = await client.call_tool(
                    "fetch_fetch", {"url": url, "max_length": 2000},
                )
            except ToolError as erro:
                raise SystemExit(f"Falha ao buscar a página: {erro}") from erro
            for conteudo in resultado.content:
                if conteudo.type == "text":
                    print(conteudo.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testa CTB Tools e MCP Fetch sem agente.")
    parser.add_argument("--url", help="URL pública para testar a ferramenta Fetch")
    argumentos = parser.parse_args()
    asyncio.run(main(argumentos.url))
