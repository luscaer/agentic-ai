from typing import Literal
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Infracao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    natureza: Literal["leve", "media", "grave", "gravissima"]
    quantidade: int = Field(default=1, strict=True, ge=1)

    @field_validator("natureza", mode="before")
    @classmethod
    def normalizar_natureza(cls, valor):
        if isinstance(valor, str):
            return "".join(
                c for c in unicodedata.normalize("NFD", valor.strip().lower())
                if not unicodedata.combining(c)
            )
        return valor


class Multa(Infracao):
    multiplicador: int = Field(default=1, strict=True, ge=1)
    fundamento_multiplicador: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def exigir_fundamento(self):
        if self.multiplicador > 1 and not (
            self.fundamento_multiplicador and self.fundamento_multiplicador.strip()
        ):
            raise ValueError(
                "Informe fundamento_multiplicador para fator maior que 1. "
                "A referência é declarada pelo solicitante, não validada juridicamente."
            )
        return self


class EntradaPontos(BaseModel):
    model_config = ConfigDict(extra="forbid")
    infracoes: list[Infracao]


class EntradaMultas(BaseModel):
    model_config = ConfigDict(extra="forbid")
    infracoes: list[Multa]
