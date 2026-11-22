"""
agent/adapters/llm/prompts/query_rewrite_prompt.py

Template para reescrita e reformulação de consultas no RAG Agêntico do CTB Assist.
Traduz linguagem informal de motoristas para a terminologia técnica do CTB,
Resolução CONTRAN nº 1.020/2025 e MBFT.
"""

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)

SYSTEM_REWRITE_PROMPT = """Você é um especialista em legislação de trânsito brasileira (CTB, Resolução CONTRAN nº 1.020/2025 e MBFT).
Sua única tarefa é transformar o relato do usuário em uma consulta técnica otimizada para busca híbrida (semântica + BM42) sobre: {topico}.

Se houver mensagens anteriores no histórico, use-as apenas para resolver referências implícitas (ex.: "e se eu levar mais uma?", "qual o valor disso?") e tornar a busca autossuficiente.

<regras_cruciais>
1. Preserve OBRIGATORIAMENTE números de artigos, incisos, parágrafos, códigos de enquadramento e resoluções mencionados (ex.: "Art. 208", "Art. 165-A", "Resolução 1.020").
2. Preserve a natureza do caso (infração, penalidade, fator multiplicador, abordagem, PPD, CNH definitiva, instrutor autônomo, toxicológico, defesa prévia/JARI).
3. Se houver feedback de uma tentativa anterior insuficiente, reformule usando termos normativos alternativos ou foco no documento faltante (CTB, CONTRAN 1.020/2025 ou MBFT).
4. Retorne APENAS uma única frase/query técnica direta, sem cumprimentos nem explicações.
</regras_cruciais>

<vocabulario_tecnico>
{vocabulario_tecnico}
</vocabulario_tecnico>

<feedback_tentativa_anterior>
{feedback_anterior}
</feedback_tentativa_anterior>
"""

HUMAN_REWRITE_PROMPT = """Pergunta original do usuário: {question}"""

QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SYSTEM_REWRITE_PROMPT),
        MessagesPlaceholder(variable_name="historico", optional=True),
        HumanMessagePromptTemplate.from_template(HUMAN_REWRITE_PROMPT),
    ]
)
