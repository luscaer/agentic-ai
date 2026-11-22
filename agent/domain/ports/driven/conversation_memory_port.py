"""
agent/domain/ports/driven/conversation_memory_port.py

Port (contrato) para persistência de contexto conversacional.
Define O QUE o sistema precisa — não COMO será feito.
"""

from typing import Protocol

from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.resumo_conversa import ResumoConversa


class ConversationMemoryPort(Protocol):
    """
    Contrato para o sistema de memória conversacional.

    Abstrai o mecanismo de armazenamento (Redis, banco relacional, memória...)
    expondo apenas operações de domínio: obter e salvar contexto de sessão.
    """

    async def obter_contexto(
        self, sessao_id: str
    ) -> tuple[HistoricoConversa, ResumoConversa | None]:
        """
        Recupera o contexto conversacional de uma sessão.

        Parâmetros
        ----------
        sessao_id : str
            Identificador único da sessão do usuário.

        Retorna
        -------
        tuple[HistoricoConversa, ResumoConversa | None]
            Histórico de mensagens recentes e resumo comprimido, se existir.
            O resumo é None quando a sessão é nova ou nunca foi comprimida.
        """
        ...

    async def salvar_contexto(
        self,
        sessao_id: str,
        historico: HistoricoConversa,
        resumo: ResumoConversa | None,
    ) -> None:
        """
        Persiste o contexto conversacional de uma sessão.

        Parâmetros
        ----------
        sessao_id : str
            Identificador único da sessão do usuário.
        historico : HistoricoConversa
            Janela de mensagens recentes a ser persistida.
        resumo : ResumoConversa | None
            Resumo comprimido da conversa, ou None se ainda não foi gerado.
        """
        ...
