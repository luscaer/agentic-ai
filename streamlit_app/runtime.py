import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from agent.graph import executar_agente_async, obter_orquestrador

TIMEOUT_PADRAO_S = 180.0

class AsyncRunner:
    """Executa corrotinas em um event loop permanente, rodando em uma thread de fundo."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="ctb-assist-loop", daemon=True
        )
        self._thread.start()

    def run(self, coro: Awaitable[Any], timeout: float | None = TIMEOUT_PADRAO_S) -> Any:
        """Roda a corrotina no loop de fundo e espera o resultado (propaga exceções)."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)


class AgentService:
    """Fachada síncrona do agente para a interface: pergunta + thread_id → resposta padronizada."""

    def __init__(
        self,
        runner: AsyncRunner | None = None,
        orquestrador_factory: Callable[[], Awaitable[Any]] = obter_orquestrador,
    ) -> None:
        self._runner = runner or AsyncRunner()
        self._orquestrador_factory = orquestrador_factory
        self._orquestrador: Any | None = None

    async def _turno(self, pergunta: str, thread_id: str) -> dict[str, Any]:
        # O orquestrador é criado sob demanda dentro do loop de fundo; se a criação falhar
        # (ex.: chave de API ausente), nada fica guardado e o próximo turno tenta de novo.
        if self._orquestrador is None:
            self._orquestrador = await self._orquestrador_factory()
        return await executar_agente_async(
            pergunta=pergunta, thread_id=thread_id, orquestrador=self._orquestrador
        )

    def perguntar(self, pergunta: str, thread_id: str) -> dict[str, Any]:
        """Executa um turno; devolve o contrato de `RespostaIA.to_dict()`."""
        logger.info("Turno da interface | thread_id='{}'", thread_id)
        return self._runner.run(self._turno(pergunta, thread_id))
