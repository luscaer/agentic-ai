"""
agent/graph.py

Fachada de alto nível do grafo LangGraph do CTB Assist (Tarefa A2 / B4).
Fornece `executar_agente(pergunta, thread_id)` retornando resposta, fontes,
ferramentas MCP acionadas e skills carregadas — pronto para o Streamlit (`app.py`)
e para testes interativos via CLI (`python -m agent.graph`).
"""

import asyncio
from typing import Any

from agent.adapters.orchestrator.langgraph_adapter import LangGraphOrchestratorAdapter
from agent.config.factory import get_real_langgraph_orchestrator
from agent.domain.ports.driven.guardrail_port import GuardrailPort
from agent.domain.ports.driven.mcp_tool_port import MCPToolPort

_ORQUESTRADOR_SINGLETON: LangGraphOrchestratorAdapter | None = None


async def obter_orquestrador(
    mcp_port: MCPToolPort | None = None,
    guardrail_port: GuardrailPort | None = None,
    recriar: bool = False,
) -> LangGraphOrchestratorAdapter:
    """Retorna uma instância reutilizável do orquestrador (preservando o checkpointer em RAM)."""
    global _ORQUESTRADOR_SINGLETON
    if _ORQUESTRADOR_SINGLETON is None or recriar:
        _ORQUESTRADOR_SINGLETON = await get_real_langgraph_orchestrator(
            mcp_port=mcp_port,
            guardrail_port=guardrail_port,
        )
    return _ORQUESTRADOR_SINGLETON


async def executar_agente_async(
    pergunta: str,
    thread_id: str = "default",
    topico: str = "transito_ctb",
    orquestrador: LangGraphOrchestratorAdapter | None = None,
) -> dict[str, Any]:
    """
    Executa um turno do CTB Assist e retorna o contrato padronizado para o Streamlit:
    {
        "resposta": str,
        "fontes": list[dict],
        "confianca": float,
        "skills_carregadas": list[str],
        "ferramentas_usadas": list[dict],
        "tentativas_rag": int,
        "bloqueado_guardrail": bool,
        "faltou_informacao": bool,
    }
    """
    motor = orquestrador or await obter_orquestrador()
    resposta = await motor.executar(
        pergunta=pergunta,
        topico_str=topico,
        sessao_id=thread_id,
    )
    return resposta.to_dict()


def executar_agente(
    pergunta: str,
    thread_id: str = "default",
    topico: str = "transito_ctb",
) -> dict[str, Any]:
    """Versão síncrona de `executar_agente_async` para uso direto no Streamlit."""
    return asyncio.run(
        executar_agente_async(
            pergunta=pergunta,
            thread_id=thread_id,
            topico=topico,
        )
    )


async def _cli_interativo() -> None:
    print("CTB Assist — Modo Interativo CLI (digite 'sair' para encerrar, 'nova' para nova conversa)")
    thread_id = "cli-sessao-1"
    turno = 1
    orquestrador = await obter_orquestrador()

    while True:
        pergunta = input(f"\n[{thread_id}] Você: ").strip()
        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit"}:
            break
        if pergunta.lower() == "nova":
            turno += 1
            thread_id = f"cli-sessao-{turno}"
            print(f"--- Nova conversa iniciada ({thread_id}) ---")
            continue

        res = await executar_agente_async(
            pergunta=pergunta,
            thread_id=thread_id,
            orquestrador=orquestrador,
        )
        print(f"\nCTB Assist:\n{res['resposta']}")
        print(
            f"\n[Auditoria] skills={res['skills_carregadas']} | "
            f"mcps={[f.get('ferramenta') for f in res['ferramentas_usadas']]} | "
            f"tentativas_rag={res['tentativas_rag']} | fontes={len(res['fontes'])}"
        )


if __name__ == "__main__":
    asyncio.run(_cli_interativo())
