"""
agent/domain/dictionaries/jargoes.py

Banco de conhecimento de domínio de trânsito: mapeia expressões coloquiais
de motoristas para a terminologia técnica do CTB (Lei nº 9.503/1997),
da Resolução CONTRAN nº 1.020/2025 e do MBFT (Resolução CONTRAN nº 985/2022).
"""

JARGOES_TRANSITO_CTB: dict[str, str] = {
    # --- Infrações de Circulação e Sinalização ---
    "furar sinal": "avançar o sinal vermelho do semáforo ou o de parada obrigatória (Art. 208 CTB)",
    "passar no vermelho": "avançar o sinal vermelho do semáforo (Art. 208 CTB)",
    "contramão": "transitar pela contramão de direção (Art. 186 CTB)",
    "furar bloqueio": "transpor bloqueio viário policial ou com/sem sinalização (Art. 209 e Art. 210 CTB)",
    "excesso de velocidade": "transitar em velocidade superior à máxima permitida para o local (Art. 218 CTB)",
    "radar": "transitar em velocidade superior à máxima permitida medida por instrumento hábil (Art. 218 CTB)",
    "ultrapassagem proibida": "ultrapassar pela contramão em faixa contínua amarela, curvas, aclives ou interseções (Art. 203 CTB)",
    "acostamento": "transitar ou ultrapassar pelo acostamento (Art. 193 e Art. 202 CTB)",
    "farol apagado": "transitar com o farol desregulado ou apagado / luz baixa em rodovias de pista simples (Art. 250 CTB)",
    # --- Álcool, Toxicológico e Direção Perigosa ---
    "bafômetro": "dirigir sob a influência de álcool ou recusar teste de alcoolemia (Art. 165 e Art. 165-A CTB)",
    "lei seca": "dirigir sob a influência de álcool ou substância psicoativa ou recusa ao teste do etilômetro (Art. 165 e Art. 165-A CTB)",
    "recusar bafômetro": "recusar-se a ser submetido a teste, exame clínico ou perícia para certificar influência de álcool (Art. 165-A CTB)",
    "racha": "disputar corrida / participar de competição não autorizada em via pública (Art. 173 e Art. 174 CTB)",
    "empinar moto": "conduzir motocicleta fazendo malabarismo ou equilibrando-se apenas em uma roda (Art. 244, III CTB)",
    "sem capacete": "conduzir motocicleta sem usar capacete de segurança ou vestuário de acordo com o CONTRAN (Art. 244, I e II CTB)",
    # --- Celular, Cinto e Estacionamento ---
    "celular no volante": "dirigir utilizando-se de telefone celular ou segurando/manuseando telefone celular (Art. 252, VI e parágrafo único CTB)",
    "mexer no celular": "dirigir segurando ou manuseando telefone celular (Art. 252, parágrafo único CTB)",
    "sem cinto": "deixar o condutor ou passageiro de usar o cinto de segurança (Art. 167 CTB)",
    "vaga de idoso": "estacionar nas vagas reservadas às pessoas com deficiência ou idosos sem credencial (Art. 181, XX CTB)",
    "vaga de pcd": "estacionar nas vagas reservadas às pessoas com deficiência ou idosos sem credencial (Art. 181, XX CTB)",
    "estacionar na calçada": "estacionar o veículo no passeio ou sobre faixa destinada a pedestre (Art. 181, VIII CTB)",
    "estacionar na garagem": "estacionar onde houver guia de calçada (meio-fio) rebaixada destinada à entrada ou saída de veículos (Art. 181, IX CTB)",
    "fila dupla": "estacionar ao lado de outro veículo em fila dupla (Art. 181, XI CTB)",
    # --- Documentação, Veículo e Licenciamento ---
    "documento atrasado": "conduzir o veículo que não esteja registrado e devidamente licenciado (Art. 230, V CTB)",
    "licenciamento vencido": "conduzir veículo não devidamente licenciado (Art. 230, V CTB)",
    "sem cnh": "dirigir veículo sem possuir CNH, PPD ou ACC (Art. 162, I CTB)",
    "cnh vencida": "dirigir veículo com validade da CNH vencida há mais de trinta dias (Art. 162, V CTB)",
    "cnh suspensa": "dirigir veículo com CNH ou PPD cassada ou com suspensão do direito de dirigir (Art. 162, II CTB)",
    # --- Habilitação, PPD e Resolução CONTRAN nº 1.020/2025 ---
    "carteira provisória": "Permissão para Dirigir (PPD) com validade de um ano e regras para obtenção da CNH definitiva (Art. 148 CTB e Resolução CONTRAN nº 1.020/2025)",
    "ppd": "Permissão para Dirigir (PPD), infrações impeditivas e expedição da CNH definitiva (Art. 148, § 3º CTB e Resolução CONTRAN nº 1.020/2025)",
    "pegar a definitiva": "expedição da CNH definitiva após 1 ano de PPD sem infração grave ou gravíssima nem reincidência em média (Art. 148, § 3º CTB e Resolução CONTRAN nº 1.020/2025)",
    "instrutor autônomo": "aulas práticas de direção veicular com instrutores de trânsito autônomos após Licença de Aprendizagem (Art. 36 da Resolução CONTRAN nº 1.020/2025)",
    "primeira habilitação": "processo de formação de condutores, exames teórico e prático, Licença de Aprendizagem e PPD (Resolução CONTRAN nº 1.020/2025 e Art. 140 a 148 CTB)",
    "validade da cnh": "prazo de vigência do exame de aptidão física e mental de 10, 5 ou 3 anos por faixa etária (Art. 147, § 2º CTB)",
    "toxicológico": "exame toxicológico de larga janela de detecção para categorias C, D e E e penalidades por atraso ou resultado positivo (Art. 148-A, Art. 165-B, Art. 165-C e Art. 165-D CTB)",
    "ear": "exercício de atividade remunerada ao veículo (EAR), limite de 40 pontos independente da natureza das infrações e avaliação psicológica (Art. 261, § 5º CTB e Resolução CONTRAN nº 1.020/2025)",
    # --- Pontuação, Multas, Defesa e MBFT ---
    "limite de pontos": "suspensão do direito de dirigir por pontuação escalonada de 20, 30 ou 40 pontos em 12 meses conforme infrações gravíssimas e EAR (Art. 261, § 1º CTB)",
    "fator multiplicador": "agravamento do valor da multa de natureza gravíssima por fator multiplicador (2x, 3x, 5x, 10x, 20x, 60x) conforme previsão expressa no artigo do CTB (Art. 258, § 2º CTB)",
    "recorrer da multa": "defesa prévia da autuação, recurso à JARI e segunda instância (Art. 280 a 290 CTB)",
    "converter em advertência": "imposição de penalidade de advertência por escrito para infração leve ou média sem reincidência nos últimos 12 meses (Art. 267 CTB)",
    "indicar condutor": "identificação do real condutor infrator no prazo legal (Art. 257, § 7º CTB)",
    "sem abordagem": "constatação da infração sem abordagem e preenchimento obrigatório do campo de observações do AIT (MBFT — Resolução CONTRAN nº 985/2022)",
    "duas multas ao mesmo tempo": "infrações concomitantes e vedação de lavratura simultânea de autos de infração (MBFT Parte Geral e Fichas de Fiscalização)",
}


def formatar_jargoes_para_prompt(dicionario: dict[str, str]) -> str:
    """Formata o dicionário de jargões em bullet points para injeção no prompt."""
    return "\n".join(
        f"- '{jargao}' -> '{tecnico}'" for jargao, tecnico in dicionario.items()
    )
