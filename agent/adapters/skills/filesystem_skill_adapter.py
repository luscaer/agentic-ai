"""
agent/adapters/skills/filesystem_skill_adapter.py

Adapter concreto de SkillPort que descobre arquivos `skills/*/SKILL.md`,
lê o frontmatter YAML (`name`, `description`) para montar o catálogo leve
no System Prompt e carrega o corpo completo sob demanda quando acionado pelo grafo.
"""

import re
from pathlib import Path

from loguru import logger

from agent.config.configuration import settings
from agent.domain.ports.driven.skill_port import SkillCarregada, SkillCatalogoItem

_RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _parse_frontmatter(conteudo: str, fallback_nome: str) -> tuple[str, str, str]:
    """Extrai (name, description, body) de um arquivo SKILL.md."""
    m = _RE_FRONTMATTER.match(conteudo.strip())
    if not m:
        return fallback_nome, "Procedimento especializado de domínio.", conteudo.strip()

    meta_raw, body = m.group(1), m.group(2).strip()
    nome = fallback_nome
    descricao = ""

    for linha in meta_raw.splitlines():
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        chave = chave.strip().lower()
        valor = valor.strip().strip('"').strip("'")
        if chave == "name" and valor:
            nome = valor
        elif chave == "description" and valor:
            descricao = valor

    return nome, descricao or "Procedimento especializado de domínio.", body


class FileSystemSkillAdapter:
    """Implementa SkillPort lendo arquivos `SKILL.md` sob demanda do sistema de arquivos."""

    def __init__(self, skills_dir: str | None = None) -> None:
        self._skills_dir = Path(skills_dir or settings.SKILLS_DIR)

    def listar_catalogo(self) -> list[SkillCatalogoItem]:
        if not self._skills_dir.exists():
            logger.warning("Diretório de skills não encontrado: '{}'", self._skills_dir)
            return []

        itens: list[SkillCatalogoItem] = []
        for skill_file in sorted(self._skills_dir.glob("*/SKILL.md")):
            try:
                conteudo = skill_file.read_text(encoding="utf-8")
                nome, descricao, _ = _parse_frontmatter(
                    conteudo, fallback_nome=skill_file.parent.name
                )
                itens.append(
                    SkillCatalogoItem(
                        nome=nome,
                        descricao=descricao,
                        caminho=str(skill_file),
                    )
                )
            except Exception as exc:
                logger.warning("Falha ao ler skill '{}': {}", skill_file, exc)

        return itens

    def formatar_catalogo_para_prompt(self) -> str:
        catalogo = self.listar_catalogo()
        if not catalogo:
            return "Nenhuma skill disponível no momento."
        return "\n".join(
            f"- `{item.nome}`: {item.descricao}" for item in catalogo
        )

    def carregar_skill(self, nome: str) -> SkillCarregada | None:
        alvo = nome.strip().lower()
        for item in self.listar_catalogo():
            if item.nome.lower() == alvo or Path(item.caminho).parent.name.lower() == alvo:
                conteudo = Path(item.caminho).read_text(encoding="utf-8")
                nome_real, descricao, corpo = _parse_frontmatter(
                    conteudo, fallback_nome=item.nome
                )
                logger.info("Skill carregada sob demanda | nome='{}'", nome_real)
                return SkillCarregada(
                    nome=nome_real,
                    descricao=descricao,
                    instrucoes=corpo,
                    caminho=item.caminho,
                )

        logger.warning("Skill solicitada não encontrada | nome='{}'", nome)
        return None
