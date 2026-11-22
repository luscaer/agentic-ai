"""
adapters/orchestrator/nodes/recuperar_memoria.py
 
Nó 1 do grafo LangGraph — recuperação de memória conversacional.
"""

from loguru import logger
 
from agent.adapters.orchestrator.state import AgenteState
from agent.domain.ports.driven.conversation_memory_port import ConversationMemoryPort
 
 
class RecuperarMemoriaNode:
    """
    Nó responsável por carregar o contexto conversacional da sessão.
 
    Busca o histórico de mensagens recentes e o resumo de longo prazo
    via ConversationMemoryPort, injetando-os na Consulta antes que
    qualquer outro nó precise deles.
 
    Recebe apenas o port que usa — sem conhecimento dos demais colaboradores
    do grafo (LLM, VectorStore, Reranker...).
 
    Integração com LangGraph
    ------------------------
    Registrado via `builder.add_node("recuperar_memoria", RecuperarMemoriaNode(memory))`.
    O LangGraph chama `__call__` automaticamente ao executar o nó,
    passando o estado atual e fundindo o dict retornado no estado global.
 
    Exemplos
    --------
    >>> node = RecuperarMemoriaNode(memory=redis_memory_adapter)
    >>> builder.add_node("recuperar_memoria", node)
    """

    def __init__(self, memory: ConversationMemoryPort) -> None:
        self._memory = memory

    async def __call__(self, state: AgenteState) -> dict:
        """
        Executa a recuperação de memória e atualiza a Consulta no estado.
 
        Parâmetros
        ----------
        state : AgenteState
            Estado atual do grafo. Espera `consulta` com `sessao_id` preenchido.
 
        Retorna
        -------
        dict
            Dicionário com a chave `consulta` atualizada com `historico` e `resumo`.
            O LangGraph funde automaticamente com o restante do estado global.
        """

        consulta = state["consulta"]

        logger.debug(
            "Nó recuperar_memoria | sessao_id='{}'",
            consulta.sessao_id,
        )

        historico, resumo = await self._memory.obter_contexto(sessao_id=consulta.sessao_id)

        consulta.historico = historico
        consulta.resumo = resumo

        logger.debug(
            "Memória recuperada | sessao_id='{}' | mensagens={} | resumo={}",
            consulta.sessao_id,
            len(historico),
            "presente" if resumo else "ausente",
        )

        return {"consulta": consulta}