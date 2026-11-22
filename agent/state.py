"""
agent/state.py

Fachada pública do estado do grafo LangGraph (alinhada com a Etapa 3 do planejamento).
Reexporta `AgenteState` da camada de orquestração hexagonal.
"""

from agent.adapters.orchestrator.state import AgenteState

__all__ = ["AgenteState"]
