from fastmcp import FastMCP
from pydantic import Field
from mcp_servers.ctb_tools import calculators, validators
from mcp_servers.ctb_tools.schemas import Infracao, Multa, InfracaoDatada, Notificacao

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


@mcp.tool()
def analisar_pontuacao(infracoes: list[InfracaoDatada], data_referencia: str, ear: bool = Field(strict=True)) -> dict:
    """simula quantos pontos entram em uma janela de 12 meses e verifica se a soma atinge o limite correspondente ao condutor.

    Início exclusivo e fim inclusivo.
    Cada item contém natureza, quantidade, data do cometimento e situação declarada:
    pontuavel (padrão), suspensao_especifica, excecao_art_259, anulada ou advertencia.
    Só pontuáveis na janela entram na soma e na quantidade de gravíssimas.
    Não decide suspensão.
    """
    return calculators.analisar_pontuacao(infracoes, data_referencia, ear)


@mcp.tool()
def validar_notificacao(notificacao: Notificacao) -> dict:
    """Confere campos de notificação individual de autuação ou penalidade de multa 
    e aponta o que está faltando ou parece inconsistente.
    
    Informe tipo autuacao ou penalidade_multa e os campos transcritos disponíveis.
    Campos ausentes podem ser omitidos; datas são strings AAAA-MM-DD e hora HH:MM.
    Relata ausências, formatos inválidos e inconsistências cronológicas.
    Não exige assinatura/prontuário em todos os casos, não avalia prazos de expedição,
    editais, autenticidade ou requisitos específicos. Não conclui nulidade ou validade.
    """
    return validators.validar_notificacao(notificacao)


if __name__ == "__main__":
    mcp.run(show_banner=False)
