"""
agent/domain/value_objects/fonte_documento.py

Value Object imutável que representa a referência a um trecho normativo
(CTB, Resolução CONTRAN ou MBFT) utilizado pelo agente para fundamentar respostas.
"""

from dataclasses import dataclass
from typing import Any

from agent.domain.exceptions import ValorInvalidoError


@dataclass(frozen=True)
class FonteDocumento:
    """
    Value Object imutável para fonte de documento jurídico/normativo.

    Encapsula o texto do dispositivo legal ou ficha do MBFT junto de seus
    metadados de rastreabilidade (norma, artigo, inciso, código de enquadramento,
    página e score de relevância).
    """

    trecho_preview: str
    score_relevancia: float | None = None
    pagina: int = 1
    documento: str = "CTB"
    norma: str = "Lei nº 9.503/1997 (CTB)"
    artigo: str | None = None
    inciso: str | None = None
    codigo_enquadramento: str | None = None
    tema: str | None = None
    url: str | None = None
    origem: str | None = None

    def __post_init__(self) -> None:
        if self.pagina < 1:
            raise ValorInvalidoError(
                "pagina",
                f"deve ser um número maior ou igual a 1 (recebido: {self.pagina})",
            )

    @property
    def referencia_curta(self) -> str:
        """Retorna citação legível (ex.: 'CTB — Art. 208 (pág. 62)')."""
        partes = [self.norma or self.documento]
        if self.artigo:
            art_txt = f"Art. {self.artigo}"
            if self.inciso:
                art_txt += f", {self.inciso}"
            partes.append(art_txt)
        if self.codigo_enquadramento:
            partes.append(f"Enquadramento {self.codigo_enquadramento}")
        partes.append(f"pág. {self.pagina}")
        return " | ".join(partes)

    def to_dict(self) -> dict[str, Any]:
        """Serializa para o formato padronizado de fachada (`rag/retriever.py` e Streamlit)."""
        return {
            "texto": self.trecho_preview,
            "documento": self.documento,
            "fonte": self.norma,
            "artigo": self.artigo,
            "inciso": self.inciso,
            "codigo_enquadramento": self.codigo_enquadramento,
            "tema": self.tema,
            "pagina": self.pagina,
            "url": self.url,
            "origem": self.origem,
            "score": round(self.score_relevancia, 4)
            if self.score_relevancia is not None
            else None,
            "referencia": self.referencia_curta,
        }

    def __str__(self) -> str:
        score = (
            f"{self.score_relevancia:.2f}"
            if self.score_relevancia is not None
            else "N/A"
        )
        preview = (
            self.trecho_preview[:160].replace("\n", " ") + "..."
            if len(self.trecho_preview) > 160
            else self.trecho_preview.replace("\n", " ")
        )
        return f'{self.referencia_curta} | Score: {score} | "{preview}"'
