"""
agent/domain/ports/driven/skill_port.py

Port (contrato) para descoberta e carregamento sob demanda de Skills (`SKILL.md`).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SkillCatalogoItem:
    """Metadados leves de uma skill exibidos no catálogo do System Prompt."""

    nome: str
    descricao: str
    caminho: str


@dataclass(frozen=True)
class SkillCarregada:
    """Conteúdo completo de uma skill carregada sob demanda."""

    nome: str
    descricao: str
    instrucoes: str
    caminho: str


class SkillPort(Protocol):
    """Contrato para listagem de catálogo e carregamento sob demanda de skills."""

    def listar_catalogo(self) -> list[SkillCatalogoItem]:
        """Retorna todas as skills disponíveis (apenas metadados do frontmatter)."""
        ...

    def formatar_catalogo_para_prompt(self) -> str:
        """Formata o catálogo de skills para injeção na mensagem de sistema."""
        ...

    def carregar_skill(self, nome: str) -> SkillCarregada | None:
        """Lê o conteúdo completo do SKILL.md correspondente ao nome solicitado."""
        ...
