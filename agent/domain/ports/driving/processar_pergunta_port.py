"""
agent/ports/driving/processar_pergunta_port.py

Port de ENTRADA — a API chama o domínio através desta interface.
Define o contrato do caso de uso principal: receber uma pergunta e devolver uma resposta.
"""

from typing import Protocol

from agent.domain.entities.resposta_ia import RespostaIA


class ProcessarPerguntaPort(Protocol):
    """
    Contrato para o caso de uso principal do agente.

    É o ponto de entrada do pipeline RAG completo:
    reescrita de query → busca vetorial → reranqueamento → geração → resposta.

    Chamado pela camada de API (FastAPI) a cada mensagem do usuário.
    """

    async def executar(
        self,
        pergunta: str,
        topico_str: str,
        sessao_id: str,
    ) -> RespostaIA:
        """
        Processa uma pergunta e retorna a resposta gerada pela IA.

        Parâmetros
        ----------
        pergunta : str
            Mensagem original enviada pelo usuário.
        topico : str
            Tópico da conversa, usado para filtrar a busca vetorial.
        sessao_id : str
            Identificador da sessão, usado para carregar e salvar o contexto
            conversacional (histórico e resumo).

        Retorna
        -------
        RespostaIA
            Entidade com a resposta gerada, fontes utilizadas e
            grau de confiança, pronta para serialização pela API.
        """
        ...
