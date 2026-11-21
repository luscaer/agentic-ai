import json
from decimal import Decimal
from pathlib import Path
from .schemas import EntradaMultas, EntradaPontos

TABELA = json.loads(
    (Path(__file__).parent / "data" / "valores_infracoes.json").read_text(encoding="utf-8")
)


def calcular_pontos(infracoes: list) -> dict:
    """Soma os pontos nominais por natureza (art. 259, caput)."""
    entrada = EntradaPontos(infracoes=infracoes)
    itens = []
    for infracao in entrada.infracoes:
        pontos = TABELA["naturezas"][infracao.natureza]["pontos"]
        itens.append({
            **infracao.model_dump(),
            "pontos_unitarios": pontos,
            "subtotal_pontos": pontos * infracao.quantidade,
        })
    return {
        "itens": itens,
        "total_pontos": sum(item["subtotal_pontos"] for item in itens),
        "base_legal": "CTB, art. 259, incisos I a IV",
        "observacao": (
            "Soma nominal por natureza, não saldo oficial da CNH. "
            "Não aplica as exceções do art. 259, § 4º, nem avalia responsabilidade, "
            "advertência, datas, EAR ou suspensão. "
        ),
    }


def calcular_valor_multas(infracoes: list) -> dict:
    """Calcula valores nominais com fatores declarados, sem inferir enquadramento."""
    entrada = EntradaMultas(infracoes=infracoes)
    itens = []
    total = Decimal("0.00")
    for infracao in entrada.infracoes:
        base = Decimal(TABELA["naturezas"][infracao.natureza]["valor"])
        unitario = base * infracao.multiplicador
        subtotal = unitario * infracao.quantidade
        total += subtotal
        itens.append({
            **infracao.model_dump(),
            "valor_base": format(base, ".2f"),
            "valor_unitario": format(unitario, ".2f"),
            "subtotal": format(subtotal, ".2f"),
        })
    return {
        "itens": itens,
        "total": format(total, ".2f"),
        "moeda": "REAL",
        "base_legal": "CTB, art. 258, incisos I a IV e § 2º",
        "observacao": (
            "Simulação nominal, sem descontos, juros ou conversão em advertência. "
            "Multiplicadores e fundamentos são declarados pelo solicitante; "
            "sua aplicabilidade jurídica não é validada. Não infere reincidência."
        ),
    }
