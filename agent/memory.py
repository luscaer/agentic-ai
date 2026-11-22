"""
agent/memory.py

Fachada pública de memória conversacional e checkpointer por `thread_id`
do CTB Assist (Tarefa A5 do planejamento).
"""

from langgraph.checkpoint.memory import MemorySaver

from agent.adapters.memory.in_memory_memory_adapter import (
    InMemoryConversationMemoryAdapter,
    SimpleSummarizerAdapter,
)


def criar_checkpointer() -> MemorySaver:
    """Retorna o checkpointer padrão do LangGraph isolado por `thread_id`."""
    return MemorySaver()


__all__ = [
    "InMemoryConversationMemoryAdapter",
    "MemorySaver",
    "SimpleSummarizerAdapter",
    "criar_checkpointer",
]
