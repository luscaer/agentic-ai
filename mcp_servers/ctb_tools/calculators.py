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


def analisar_pontuacao(infracoes: list, data_referencia: str, ear: bool) -> dict:
    """Simula uma janela móvel de 12 meses pelas datas do cometimento."""
    from datetime import date
    from .schemas import EntradaAnalisePontuacao

    entrada = EntradaAnalisePontuacao(
        infracoes=infracoes, data_referencia=data_referencia, ear=ear,
    )
    referencia = date.fromisoformat(entrada.data_referencia)
    if referencia < date(2022, 4, 12):
        raise ValueError("Use data_referencia a partir de 2022-04-12: não simulamos a transição legal de 2021.")
    try:
        inicio = referencia.replace(year=referencia.year - 1)
    except ValueError:
        inicio = referencia.replace(year=referencia.year - 1, day=28)
    consideradas = []
    desconsideradas = []
    total = 0
    gravissimas = 0
    for infracao in sorted(entrada.infracoes, key=lambda item: item.data):
        dia = date.fromisoformat(infracao.data)
        item = infracao.model_dump()
        if dia > referencia:
            motivo = "posterior_a_referencia"
        elif dia <= inicio:
            motivo = "fora_da_janela"
        elif infracao.situacao != "pontuavel":
            motivo = infracao.situacao
        else:
            motivo = None
        if motivo:
            desconsideradas.append({**item, "motivo": motivo})
            continue
        subtotal = TABELA["naturezas"][infracao.natureza]["pontos"] * infracao.quantidade
        total += subtotal
        if infracao.natureza == "gravissima":
            gravissimas += infracao.quantidade
        consideradas.append({**item, "subtotal_pontos": subtotal, "acumulado_na_janela": total})
    if entrada.ear or gravissimas == 0:
        limite = 40
    elif gravissimas == 1:
        limite = 30
    else:
        limite = 20
    return {
        "inicio_exclusivo": inicio.isoformat(),
        "fim_inclusivo": referencia.isoformat(),
        "ear": entrada.ear,
        "consideradas": consideradas,
        "desconsideradas": desconsideradas,
        "total_pontos": total,
        "quantidade_gravissimas": gravissimas,
        "limite_pontos": limite,
        "limite_atingido": total >= limite,
        "pontos_ate_limite": max(0, limite - total),
        "base_legal": "CTB, arts. 259 § 4º e 261 I e § 5º; Res. CONTRAN 723/2018, alterada pela 844/2021, arts. 3º, 6º e 7º",
        "observacao": (
            "Simulação na data de referência, não saldo oficial. "
        ),
    }
