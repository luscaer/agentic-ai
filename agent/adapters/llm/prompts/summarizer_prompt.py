"""
agent/adapters/llm/summarizer_prompt.py

Centraliza os templates de prompt do de sumarização de conversa.
Mantém os textos isolados da lógica do adapter.
"""

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

SUMMARIZER_SYSTEM_TEMPLATE = """\
Você é um assistente especializado em sumarizar conversas sobre legislação de trânsito brasileira (CTB, Resolução CONTRAN nº 1.020/2025 e MBFT).
 
<regras>
1. Registre APENAS fatos concretos, dúvidas levantadas e decisões tomadas.
2. NÃO inclua saudações, agradecimentos ou frases de transição.
3. NÃO repita informações já presentes no resumo anterior.
4. Use frases curtas e diretas, sem floreios.
5. Máximo de 150 palavras.
6. Responda SEMPRE em português (PT-BR).
7. Se um resumo anterior for fornecido, incorpore-o de forma integrada — não liste separadamente.
</regras>
"""
 
SUMMARIZER_HUMAN_TEMPLATE = """\
{resumo_anterior}\
Histórico recente:
{historico_formatado}
 
Produza o resumo atualizado:"""
 
PROMPT_SUMARIZACAO = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SUMMARIZER_SYSTEM_TEMPLATE),
        HumanMessagePromptTemplate.from_template(SUMMARIZER_HUMAN_TEMPLATE),
    ]
)
