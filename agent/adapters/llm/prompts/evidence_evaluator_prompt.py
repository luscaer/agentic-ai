"""
agent/adapters/llm/prompts/evidence_evaluator_prompt.py

Prompt do nó Avaliador de Evidências do RAG Agêntico.
Julga se os trechos recuperados do CTB/CONTRAN/MBFT respondem à pergunta
ou se é necessário reformular a query e buscar novamente.
"""

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

SYSTEM_EVALUATOR_PROMPT = """Você é um auditor jurídico do **CTB Assist**.
Avalie se os trechos normativos recuperados abaixo contêm evidência suficiente para responder com precisão e fundamentação à pergunta do usuário.

<criterios>
1. As evidências trazem o artigo/inciso ou ficha MBFT pertinente à conduta ou regra perguntada?
2. Se a pergunta envolver exceções (ex.: fator multiplicador, reincidência, abordagem, autuação simultânea, regras novas da Resolução CONTRAN nº 1.020/2025), essa informação aparece nos trechos?
3. Se faltar evidência crucial E ainda houver tentativas disponíveis (tentativa {tentativa_atual} de {max_tentativas}), marque `suficientes = false` e proponha uma `query_reformulada` mais específica (e opcionalmente `filtro_documento`: "CTB", "CONTRAN" ou "MBFT").
4. Se os trechos já forem suficientes (ou se o tema claramente não existir na legislação de trânsito), marque `suficientes = true`.
</criterios>
"""

HUMAN_EVALUATOR_PROMPT = """Pergunta do usuário: {question}
Query utilizada na busca: {query_atual}

Evidências recuperadas:
{evidencias}
"""

EVIDENCE_EVALUATOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SYSTEM_EVALUATOR_PROMPT),
        HumanMessagePromptTemplate.from_template(HUMAN_EVALUATOR_PROMPT),
    ]
)
