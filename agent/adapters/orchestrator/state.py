"""
agent/adapters/orchestrator/state.py

Define o estado compartilhado (`AgenteState`) do grafo LangGraph do CTB Assist.
Compatível tanto com a Arquitetura Hexagonal interna quanto com o contrato de
integração combinado com o Integrante 2 (`messages`, `retrieved_docs`,
`retrieval_attempts`, `tool_results`, `loaded_skills`, `final_response`).
"""

from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph.message import add_messages

from agent.domain.entities.consulta import Consulta
from agent.domain.entities.resposta_ia import RespostaIA
from agent.domain.ports.driven.llm_port import DecisaoRoteador
from agent.domain.value_objects.confianca_resposta import ConfiancaResposta
from agent.domain.value_objects.fonte_documento import FonteDocumento


class AgenteState(TypedDict):
    """Estado compartilhado entre todos os nós do grafo LangGraph (RAG Agêntico)."""

    # --- Histórico gerenciado pelo Checkpointer do LangGraph (por thread_id) ---
    messages: Annotated[list[Any], add_messages]

    # --- Entidade de domínio do turno atual ---
    consulta: Consulta

    # --- Controle do loop do Roteador e RAG Agêntico ---
    decisao_roteador: NotRequired[DecisaoRoteador | None]
    passos_agente: NotRequired[int]
    retrieval_attempts: NotRequired[int]
    query_atual: NotRequired[str | None]
    filtro_documento: NotRequired[str | None]
    feedback_avaliador: NotRequired[str | None]
    evidencias_suficientes: NotRequired[bool]

    # --- Evidências recuperadas (VO interno + contrato dict para integração) ---
    documentos_recuperados: NotRequired[list[FonteDocumento]]
    retrieved_docs: NotRequired[list[dict[str, Any]]]
    confianca: NotRequired[ConfiancaResposta]

    # --- Skills carregadas sob demanda ---
    loaded_skills: NotRequired[list[str]]
    skills_conteudo: NotRequired[dict[str, str]]

    # --- Ferramentas MCP acionadas ---
    tool_results: NotRequired[list[dict[str, Any]]]

    # --- Guardrails ---
    guardrail_bloqueado: NotRequired[bool]
    guardrail_motivo: NotRequired[str | None]

    # --- Saída final do turno ---
    resposta: NotRequired[RespostaIA]
    final_response: NotRequired[str]
