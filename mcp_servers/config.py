from pathlib import Path
import sys

servers = {
    "ctb_tools": {
        "command": sys.executable,
        "args": ["-m", "mcp_servers.ctb_tools.server"],
        "cwd": str(Path(__file__).resolve().parents[1]),
    },
    "fetch": {
        "command": sys.executable,
        "args": ["-m", "mcp_server_fetch"],
    },
}
