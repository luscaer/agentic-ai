"""
agent/domain/entities/resposta_ia.py

Entidade que representa a resposta final gerada pelo CTB Assist.
Encapsula o conteúdo textual, as fontes normativas citadas, a confiança
e os rastros de auditoria exigidos pela interface Streamlit (skills carregadas,
ferramentas MCP acionadas, tentativas de RAG e status de guardrails).
"""

from dataclasses import dataclass, field
from typing import Any

from agent.domain.value_objects.confianca_resposta import ConfiancaResposta
from agent.domain.value_objects.fonte_documento import FonteDocumento


@dataclass
class RespostaIA:
    """Entidade que encapsula a resposta final do agente com rastreabilidade completa."""

    conteudo: str
    fontes: list[FonteDocumento] = field(default_factory=list)
    confianca: ConfiancaResposta = field(default_factory=lambda: ConfiancaResposta(0.0))
    skills_carregadas: list[str] = field(default_factory=list)
    ferramentas_usadas: list[dict[str, Any]] = field(default_factory=list)
    tentativas_rag: int = 0
    bloqueado_guardrail: bool = False
    faltou_informacao: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serializa a resposta para consumo direto pelo Streamlit ou APIs."""
        return {
            "resposta": self.conteudo,
            "fontes": [f.to_dict() for f in self.fontes],
            "confianca": round(self.confianca.valor, 4),
            "skills_carregadas": list(self.skills_carregadas),
            "ferramentas_usadas": list(self.ferramentas_usadas),
            "tentativas_rag": self.tentativas_rag,
            "bloqueado_guardrail": self.bloqueado_guardrail,
            "faltou_informacao": self.faltou_informacao,
        }
