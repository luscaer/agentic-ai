"""
agent/adapters/orchestrator/nodes/gerar_resposta_node.py

Nó de geração final da resposta fundamentada do CTB Assist.
Combina evidências normativas (CTB, Resolução 1.020/2025 e MBFT),
instruções das skills carregadas sob demanda e resultados de ferramentas MCP.
"""

import json

from langchain_core.messages import AIMessage
from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.entities.resposta_ia import RespostaIA
from agent.domain.ports.driven.llm_port import LLMPort
from agent.domain.value_objects.confianca_resposta import ConfiancaResposta
from agent.domain.value_objects.fonte_documento import FonteDocumento


class GerarRespostaNode:
    """Gera a resposta final com rastreabilidade completa de fontes, skills e MCPs."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def __call__(self, state: AgenteState) -> dict:
        consulta = state["consulta"]
        documentos = list(state.get("documentos_recuperados", []))
        confianca = state.get("confianca") or ConfiancaResposta(valor=0.0)
        loaded_skills = list(state.get("loaded_skills", []))
        skills_conteudo = state.get("skills_conteudo", {})
        tool_results = list(state.get("tool_results", []))
        tentativas_rag = state.get("retrieval_attempts", 0)

        contexto = self._formatar_contexto(documentos)
        skills_texto = self._formatar_skills(skills_conteudo)
        mcp_texto = self._formatar_mcp(tool_results)

        resultado_llm = await self._llm.gerar_resposta(
            contexto=contexto,
            pergunta=consulta.pergunta_original,
            topico=consulta.topico,
            historico=consulta.historico,
            resumo=consulta.resumo,
            skills_ativas=skills_texto,
            resultados_mcp=mcp_texto,
        )

        resposta = RespostaIA(
            conteudo=resultado_llm.conteudo,
            fontes=documentos,
            confianca=confianca,
            skills_carregadas=loaded_skills,
            ferramentas_usadas=tool_results,
            tentativas_rag=tentativas_rag,
            bloqueado_guardrail=False,
            faltou_informacao=resultado_llm.faltou_informacao,
        )

        logger.info(
            "Resposta gerada | fontes={} | skills={} | mcps={} | tentativas_rag={}",
            len(documentos),
            loaded_skills,
            [t.get("ferramenta") for t in tool_results],
            tentativas_rag,
        )

        return {
            "resposta": resposta,
            "final_response": resposta.conteudo,
            "messages": [AIMessage(content=resposta.conteudo)],
        }

    def _formatar_contexto(self, documentos: list[FonteDocumento]) -> str:
        if not documentos:
            return "Nenhum dispositivo legal relevante foi recuperado na base normativa."
        blocos = []
        for idx, doc in enumerate(documentos, start=1):
            blocos.append(f"### Evidência {idx} — {doc.referencia_curta}\n{doc.trecho_preview}")
        return "\n\n".join(blocos)

    def _formatar_skills(self, skills_conteudo: dict[str, str]) -> str:
        if not skills_conteudo:
            return "Nenhuma skill carregada neste turno."
        return "\n\n".join(
            f"### Skill `{nome}`\n{texto}" for nome, texto in skills_conteudo.items()
        )

    def _formatar_mcp(self, tool_results: list[dict]) -> str:
        if not tool_results:
            return "Nenhuma ferramenta MCP executada neste turno."
        return json.dumps(tool_results, ensure_ascii=False, indent=2)
