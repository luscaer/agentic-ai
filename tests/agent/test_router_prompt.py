"""O prompt real do roteador deve conter o procedimento das skills carregadas."""

from agent.adapters.llm.prompts.router_prompt import ROUTER_PROMPT


def _renderizar(skills_conteudo: str) -> str:
    mensagens = ROUTER_PROMPT.format_messages(
        catalogo_skills="- `x`: y",
        skills_carregadas="x",
        skills_conteudo=skills_conteudo,
        ferramentas_mcp="Nenhuma ferramenta MCP conectada.",
        documentos_resumo="Nenhuma evidência recuperada ainda.",
        resultados_mcp="Nenhuma ferramenta MCP executada ainda.",
        tentativas_rag=0,
        max_tentativas_rag=3,
        historico=[],
        question="pergunta",
    )
    return mensagens[0].content


def test_prompt_inclui_procedimento_da_skill_carregada():
    texto = _renderizar("### Skill `analisar-infracoes`\nEtapa 1 — pergunte a reincidência")
    assert "<procedimentos_das_skills_carregadas>" in texto
    assert "Etapa 1 — pergunte a reincidência" in texto
    assert "siga as etapas dele NA ORDEM" in texto
