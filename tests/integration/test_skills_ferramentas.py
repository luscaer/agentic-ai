"""Os nomes de ferramentas MCP citados nas skills devem existir no servidor real."""

import re
from pathlib import Path

from agent.adapters.mcp import FastMCPAdapter
from mcp_servers.config import servers

RE_NOME = re.compile(r"`(ctb_tools_\w+)`")


async def test_skills_citam_apenas_ferramentas_existentes():
    adapter = FastMCPAdapter({"ctb_tools": servers["ctb_tools"]}, timeout_chamada=30)
    existentes = {f.nome for f in await adapter.listar_ferramentas()}
    assert existentes, "servidor CTB Tools não respondeu"

    citados: dict[str, set[str]] = {}
    for skill in Path("skills").glob("*/SKILL.md"):
        nomes = set(RE_NOME.findall(skill.read_text(encoding="utf-8")))
        if nomes:
            citados[skill.parent.name] = nomes

    assert "analisar-infracoes" in citados
    for skill, nomes in citados.items():
        assert nomes <= existentes, f"{skill} cita ferramentas inexistentes: {nomes - existentes}"
