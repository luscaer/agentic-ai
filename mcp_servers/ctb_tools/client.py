import asyncio
from pathlib import Path
import sys
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def criar_transporte() -> StdioTransport:
    return StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_servers.ctb_tools.server"],
        cwd=str(Path(__file__).resolve().parents[2]),
    )


async def main():
    async with Client(criar_transporte()) as client:
        print("Ferramentas:", [tool.name for tool in await client.list_tools()])


if __name__ == "__main__":
    asyncio.run(main())
