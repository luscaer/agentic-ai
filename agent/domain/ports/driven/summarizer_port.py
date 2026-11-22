"""
agent/domain/ports/driven/summarizer_port.py

Port (contrato) para compressão do histórico conversacional em resumo.
"""

from typing import Protocol

from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.resumo_conversa import ResumoConversa


class SummarizerPort(Protocol):
    """
    Contrato para o sumarizador de conversas.

    Responsável por comprimir o histórico em um ResumoConversa,
    evitando que a janela de contexto da LLM seja excedida em sessões longas.
    """

    async def resumir_conversa(
        self,
        historico: HistoricoConversa,
        resumo_anterior: ResumoConversa | None,
    ) -> ResumoConversa:
        """
        Gera ou atualiza o resumo comprimido da conversa.

        Parâmetros
        ----------
        historico : HistoricoConversa
            Janela de mensagens recentes a ser comprimida.
        resumo_anterior : ResumoConversa | None
            Resumo já existente da conversa, ou None se for a primeira compressão.
            Quando presente, deve ser incorporado ao novo resumo para não perder contexto.

        Retorna
        -------
        ResumoConversa
            Novo resumo consolidado, cobrindo o histórico anterior e o atual.
        """
        ...
