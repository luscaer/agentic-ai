"""
adapters/orchestrator/nodes/salvar_memoria.py

Nó 5 do grafo LangGraph — persistência do contexto conversacional atualizado.
"""

from agent.config.configuration import settings
from loguru import logger

from agent.adapters.orchestrator.state import AgenteState
from agent.domain.ports.driven.conversation_memory_port import ConversationMemoryPort
from agent.domain.ports.driven.summarizer_port import SummarizerPort
from agent.domain.value_objects.historico_conversa import HistoricoConversa, Mensagem


LIMITE_MENSAGENS_PADRAO = settings.LLM_MAX_HISTORY_MESSAGES


class SalvarMemoriaNode:
    """
    Nó responsável por atualizar e persistir o contexto conversacional.

    Executa três responsabilidades em sequência:
        1. Adiciona a pergunta reescrita e a resposta da IA ao histórico
        2. Comprime o histórico via SummarizerPort se atingir o limite
        3. Persiste o novo contexto via ConversationMemoryPort

    A compressão (summarização) garante que sessões longas não ultrapassem
    a janela de contexto da LLM — padrão crítico para atendimentos contábeis
    que podem se estender por muitas perguntas na mesma sessão.

    Recebe ConversationMemoryPort e SummarizerPort — sem conhecimento de LLM
    principal, VectorStore ou notificação.

    Integração com LangGraph
    ------------------------
    Registrado via `builder.add_node("salvar_memoria", SalvarMemoriaNode(memory, summarizer))`.
    Espera `consulta` e `resposta` preenchidos pelos nós anteriores.
    Atualiza `consulta` no estado com o histórico e resumo finais.

    Exemplos
    --------
    >>> node = SalvarMemoriaNode(memory=redis_adapter, summarizer=summarizer_adapter)
    >>> builder.add_node("salvar_memoria", node)
    """

    def __init__(
        self,
        memory: ConversationMemoryPort,
        summarizer: SummarizerPort,
        limite_mensagens: int = LIMITE_MENSAGENS_PADRAO,
    ) -> None:
        self._memory = memory
        self._summarizer = summarizer
        self._limite_mensagens = limite_mensagens

    async def __call__(self, state: AgenteState) -> dict:
        """
        Atualiza o histórico, comprime se necessário e persiste no Redis.
 
        Parâmetros
        ----------
        state : AgenteState
            Estado atual. Espera `consulta` com `historico` e `resposta` preenchida.
 
        Retorna
        -------
        dict
            Dicionário com `consulta` atualizada com histórico e resumo finais.
        """
        consulta = state["consulta"]
        resposta = state["resposta"]

        historico = consulta.historico.adicionar(
            Mensagem(role=Mensagem.RoleMensagem.USUARIO, conteudo=consulta.pergunta_original)
        )
        historico = historico.adicionar(
            Mensagem(role=Mensagem.RoleMensagem.ASSISTENTE, conteudo=resposta.conteudo)
        )

        consulta.historico = historico

        if len(consulta.historico) >= self._limite_mensagens:
            logger.info(
                "Limite de histórico atingido | sessao_id='{}' | mensagens={}. Comprimindo...",
                consulta.sessao_id,
                len(consulta.historico),
            )

            novo_resumo = await self._summarizer.resumir_conversa(
                historico=consulta.historico,
                resumo_anterior=consulta.resumo,
            )

            consulta.historico = HistoricoConversa()
            consulta.resumo = novo_resumo
        
        await self._memory.salvar_contexto(
            sessao_id=consulta.sessao_id,
            historico=consulta.historico,
            resumo=consulta.resumo,
        )

        logger.debug(
            "Memória salva | sessao_id='{}' | mensagens={} | resumo={}",
            consulta.sessao_id,
            len(consulta.historico),
            "presente" if consulta.resumo else "ausente",
        )
 
        return {"consulta": consulta}