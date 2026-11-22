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


class InfracaoDatada(Infracao): # herda de Infracao e acrescenta campos de data e situacao.
    data: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Data do cometimento: AAAA-MM-DD")
    situacao: Literal[
        "pontuavel", "suspensao_especifica", "excecao_art_259",
        "anulada", "advertencia",
    ] = Field(default="pontuavel", description="Classificação declarada; não inferida pela natureza")


class EntradaAnalisePontuacao(BaseModel): # valida todos os argumentos necessários à análise
    model_config = ConfigDict(extra="forbid")
    infracoes: list[InfracaoDatada]
    data_referencia: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    ear: bool = Field(strict=True, description="Exerce atividade remunerada ao veículo")


class Notificacao(BaseModel): # representa os dados de uma notificação de trânsito
    model_config = ConfigDict(extra="forbid")
    tipo: Literal["autuacao", "penalidade_multa"]
    numero_auto: str | None = None
    tipificacao: str | None = None
    local: str | None = None
    data_infracao: str | None = Field(default=None, description="AAAA-MM-DD")
    hora_infracao: str | None = Field(default=None, description="HH:MM ou HH:MM:SS")
    placa: str | None = None
    marca: str | None = None
    especie: str | None = None
    orgao_autuador: str | None = None
    agente_autuador: str | None = None
    equipamento: str | None = None
    prontuario_condutor: str | None = None
    assinatura_infrator: bool | None = Field(default=None, strict=True)
    data_expedicao: str | None = Field(default=None, description="AAAA-MM-DD; não é a data de recebimento")
    data_limite_defesa: str | None = None
    data_limite_recurso: str | None = None
