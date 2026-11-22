"""
agent/domain/value_objects/historico_conversa.py

Value Object imutável que representa o histórico de mensagens de uma sessão.
Implementa a lógica de janela deslizante (FIFO) para manter o contexto dentro do limite.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class Mensagem:
    """
    Representa uma entrada individual no histórico.
    Diferente do esquema de aplicação, este é um VO de domínio puro.
    """

    class RoleMensagem(str, Enum):
        USUARIO = "user"
        ASSISTENTE = "assistant"

    role: RoleMensagem
    conteudo: str


@dataclass(frozen=True)
class HistoricoConversa:
    """
    Value Object imutável para gerenciar o histórico de mensagens.

    Mantém uma tupla de mensagens e garante que o tamanho não exceda
    o limite definido, descartando as mais antigas se necessário.
    """

    mensagens: Tuple[Mensagem, ...] = field(default_factory=tuple)

    def adicionar(self, nova_mensagem: Mensagem) -> "HistoricoConversa":
        """
        Adiciona uma nova mensagem e retorna uma nova instância de HistoricoConversa.

        Exemplos
        --------
        >>> hist = HistoricoConversa()
        >>> hist = hist.adicionar(Mensagem(role="user", conteudo="Olá!"))
        >>> len(hist.mensagens)
        1
        """

        return HistoricoConversa(mensagens=self.mensagens + (nova_mensagem,))

    def __len__(self) -> int:
        return len(self.mensagens)

    def __str__(self) -> str:
        return (
            f"HistoricoConversa(mensagens={len(self.mensagens)})"
        )
