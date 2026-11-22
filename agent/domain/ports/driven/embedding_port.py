"""
agent/domain/ports/driven/embedding_port.py

Port (contrato) para geração de embeddings.
"""

from typing import Protocol


class EmbeddingPort(Protocol):
    """
    Contrato para o modelo de embeddings.

    Recebe textos brutos e devolve vetores de floats —
    sem expor qual modelo ou provedor está sendo usado.
    """

    async def gerar_embeddings(self, textos: list[str]) -> list[list[float]]:
        """
        Gera embeddings para uma lista de textos.

        Parâmetros
        ----------
        textos : list[str]
            Textos a serem vetorizados. Pode ser uma lista de chunks
            (indexação) ou uma lista com a query do usuário (busca).

        Retorna
        -------
        list[list[float]]
            Lista de vetores na mesma ordem dos textos de entrada.
        """
        ...
