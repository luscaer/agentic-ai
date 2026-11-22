"""
agent/adapters/orchestrator/nodes/roteador_agente_node.py

Nó Roteador do RAG Agêntico: analisa pergunta, histórico, catálogo de skills,
evidências já coletadas e ferramentas MCP disponíveis para decidir o próximo passo.
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.config.configuration import settings
from agent.domain.ports.driven.llm_port import DecisaoRoteador, LLMPort
from agent.domain.ports.driven.mcp_tool_port import MCPToolPort
from agent.domain.ports.driven.skill_port import SkillPort


class RoteadorAgenteNode:
    """Decide dinamicamente entre carregar skill, consultar RAG, chamar MCP ou responder."""

    def __init__(
        self,
        llm: LLMPort,
        skill_port: SkillPort,
        mcp_port: MCPToolPort,
        max_tentativas_rag: int | None = None,
        max_passos: int | None = None,
    ) -> None:
        self._llm = llm
        self._skill_port = skill_port
        self._mcp_port = mcp_port
        self._max_tentativas_rag = max_tentativas_rag or settings.MAX_RETRIEVAL_ATTEMPTS
        self._max_passos = max_passos or settings.MAX_AGENT_STEPS

    async def __call__(self, state: AgenteState) -> dict:
        consulta = state["consulta"]
        passos = state.get("passos_agente", 0) + 1
        tentativas_rag = state.get("retrieval_attempts", 0)
        loaded_skills = list(state.get("loaded_skills", []))
        docs = state.get("documentos_recuperados", [])
        tool_results = state.get("tool_results", [])

        # Proteção determinística contra loops infinitos
        if passos > self._max_passos:
            logger.warning(
                "Limite de passos do roteador atingido ({}) — forçando geração de resposta.",
                self._max_passos,
            )
            return {
                "passos_agente": passos,
                "decisao_roteador": DecisaoRoteador(
                    acao="gerar_resposta",
                    justificativa="Limite máximo de iterações do roteador atingido.",
                ),
            }

        catalogo_skills = self._skill_port.formatar_catalogo_para_prompt()
        ferramentas_mcp = await self._mcp_port.listar_ferramentas()
        ferramentas_str = (
            "\n".join(f.formatar_para_prompt() for f in ferramentas_mcp)
            if ferramentas_mcp
            else "Nenhuma ferramenta MCP conectada."
        )

        docs_resumo = (
            "\n".join(f"- {d.referencia_curta}: {d.trecho_preview[:180]}" for d in docs[:6])
            if docs
            else "Nenhuma evidência recuperada ainda."
        )
        mcp_resumo = (
            "\n".join(
                f"- {r.get('ferramenta')}: sucesso={r.get('sucesso')} | resultado={str(r.get('resultado') or r.get('erro'))[:200]}"
                for r in tool_results
            )
            if tool_results
            else "Nenhuma ferramenta MCP executada ainda."
        )

        skills_conteudo = "\n\n".join(
            f"### Skill `{nome}`\n{texto}"
            for nome, texto in state.get("skills_conteudo", {}).items()
        )

        decisao = await self._llm.decidir_proxima_acao(
            pergunta=consulta.pergunta_original,
            historico=consulta.historico,
            catalogo_skills=catalogo_skills,
            skills_carregadas=loaded_skills,
            documentos_resumo=docs_resumo,
            ferramentas_mcp_disponiveis=ferramentas_str,
            resultados_mcp_resumo=mcp_resumo,
            tentativas_rag=tentativas_rag,
            max_tentativas_rag=self._max_tentativas_rag,
            skills_conteudo=skills_conteudo,
        )

        # Salvaguardas determinísticas sobre a decisão do LLM
        if decisao.acao == "buscar_rag" and tentativas_rag >= self._max_tentativas_rag:
            decisao = DecisaoRoteador(
                acao="gerar_resposta",
                justificativa="Limite máximo de tentativas de RAG atingido.",
            )
        elif decisao.acao == "carregar_skill" and (
            not decisao.skill_nome or decisao.skill_nome in loaded_skills
        ):
            decisao = DecisaoRoteador(
                acao="buscar_rag" if not docs and tentativas_rag < self._max_tentativas_rag else "gerar_resposta",
                justificativa="Skill já carregada ou não especificada.",
                query_busca=consulta.pergunta_original,
            )
        elif decisao.acao == "chamar_mcp" and not ferramentas_mcp:
            decisao = DecisaoRoteador(
                acao="buscar_rag" if not docs and tentativas_rag < self._max_tentativas_rag else "gerar_resposta",
                justificativa="Nenhuma ferramenta MCP conectada no momento.",
                query_busca=consulta.pergunta_original,
            )

        logger.info(
            "Roteador (passo {}) | acao='{}' | justificativa='{}'",
            passos,
            decisao.acao,
            decisao.justificativa,
        )

        update: dict = {
            "passos_agente": passos,
            "decisao_roteador": decisao,
        }
        if decisao.acao == "buscar_rag":
            if decisao.query_busca:
                update["query_atual"] = decisao.query_busca
            if decisao.filtro_documento:
                update["filtro_documento"] = decisao.filtro_documento

        return update
