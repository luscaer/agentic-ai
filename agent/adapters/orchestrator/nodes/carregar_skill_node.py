"""
agent/adapters/orchestrator/nodes/carregar_skill_node.py

Nó responsável por carregar o conteúdo completo de uma `SKILL.md` sob demanda
e registrar seu nome em `loaded_skills` (para rastreabilidade na interface Streamlit).
"""

from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.ports.driven.skill_port import SkillPort


class CarregarSkillNode:
    """Carrega sob demanda uma skill solicitada pelo RoteadorAgenteNode."""

    def __init__(self, skill_port: SkillPort) -> None:
        self._skill_port = skill_port

    async def __call__(self, state: AgenteState) -> dict:
        decisao = state.get("decisao_roteador")
        nome_skill = decisao.skill_nome if decisao else None

        loaded_skills = list(state.get("loaded_skills", []))
        skills_conteudo = dict(state.get("skills_conteudo", {}))

        if not nome_skill:
            return {"loaded_skills": loaded_skills, "skills_conteudo": skills_conteudo}

        skill = self._skill_port.carregar_skill(nome_skill)
        if skill is None:
            logger.warning("CarregarSkillNode | skill '{}' não encontrada.", nome_skill)
            return {"loaded_skills": loaded_skills, "skills_conteudo": skills_conteudo}

        if skill.nome not in loaded_skills:
            loaded_skills.append(skill.nome)
        skills_conteudo[skill.nome] = skill.instrucoes

        logger.info("Skill ativada no estado | nome='{}'", skill.nome)
        return {
            "loaded_skills": loaded_skills,
            "skills_conteudo": skills_conteudo,
        }
