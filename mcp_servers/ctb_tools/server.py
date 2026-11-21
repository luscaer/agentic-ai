from fastmcp import FastMCP
from mcp_servers.ctb_tools import calculators
from mcp_servers.ctb_tools.schemas import Infracao, Multa

mcp = FastMCP("CTB Tools")

@mcp.tool()
def calcular_pontos(infracoes: list[Infracao]) -> dict: # validacao de entrada é feita pelo pydantic
    """Soma pontos nominais por natureza: leve 3, média 4, grave 5, gravíssima 7.

    Cada item recebe natureza e quantidade (inteiro positivo, padrão 1).
    Não calcula saldo oficial da CNH, exceções do art. 259 § 4º ou suspensão.
    Lista vazia retorna zero.
    """
    return calculators.calcular_pontos(infracoes)


@mcp.tool()
def calcular_valor_multas(infracoes: list[Multa]) -> dict:
    """Calcula multas nominais em Reais conforme o art. 258 do CTB.

    Cada item recebe natureza, quantidade e multiplicador (inteiros positivos,
    padrão 1). Fator maior que 1 exige fundamento_multiplicador declarado.
    Não verifica a aplicabilidade jurídica do fator, nem infere reincidência.
    Sem descontos ou juros. 
    Lista vazia retorna zero.
    """
    return calculators.calcular_valor_multas(infracoes)


if __name__ == "__main__":
    mcp.run(show_banner=False)
