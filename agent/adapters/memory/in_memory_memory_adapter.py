"""
agent/adapters/memory/in_memory_memory_adapter.py

Implementação em memória do ConversationMemoryPort e SummarizerPort de fallback,
permitindo execução local e testes isolados por `thread_id`/`sessao_id` sem Redis.
"""

from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.resumo_conversa import ResumoConversa


class InMemoryConversationMemoryAdapter:
    """Mantém histórico e resumo isolados por `sessao_id` em memória."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[HistoricoConversa, ResumoConversa | None]] = {}

    async def obter_contexto(
        self, sessao_id: str
    ) -> tuple[HistoricoConversa, ResumoConversa | None]:
        return self._store.get(sessao_id, (HistoricoConversa(), None))

    async def salvar_contexto(
        self,
        sessao_id: str,
        historico: HistoricoConversa,
        resumo: ResumoConversa | None = None,
    ) -> None:
        self._store[sessao_id] = (historico, resumo)

    async def limpar_sessao(self, sessao_id: str) -> None:
        self._store.pop(sessao_id, None)


class SimpleSummarizerAdapter:
    """Sumarizador determinístico de fallback para ambientes sem modelo dedicado."""

    async def resumir_conversa(
        self,
        historico: HistoricoConversa,
        resumo_anterior: ResumoConversa | None = None,
    ) -> ResumoConversa:
        partes = []
        if resumo_anterior and resumo_anterior.conteudo:
            partes.append(resumo_anterior.conteudo)
        for msg in historico.mensagens[-6:]:
            partes.append(f"{msg.role.value}: {msg.conteudo[:200]}")
        texto = " | ".join(partes).strip() or "Conversa sobre legislação de trânsito."
        return ResumoConversa(conteudo=texto[:1500])
