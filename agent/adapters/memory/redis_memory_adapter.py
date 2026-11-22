"""
agent/adapters/memory/redis_memory_adapter.py

Adapter concreto que implementa ConversationMemoryPort usando Redis.
Responsável por serializar/desserializar os VOs de domínio para JSON
e persistir o contexto conversacional por sessão.
"""

import json
from datetime import datetime

import redis.asyncio
from loguru import logger

from agent.domain.value_objects.historico_conversa import HistoricoConversa, Mensagem
from agent.domain.value_objects.resumo_conversa import ResumoConversa


class RedisMemoryAdapter:
    """
    Implementa ConversationMemoryPort usando Redis como backend de memória.

    Cada sessão ocupa duas chaves no Redis:
      - sessao:{sessao_id}:historico  → lista de mensagens serializada em JSON
      - sessao:{sessao_id}:resumo     → resumo serializado em JSON (ausente se None)

    Exemplos
    --------
    >>> client = aioredis.from_url("redis://localhost:6379")
    >>> adapter = RedisMemoryAdapter(client, ttl)
    """

    KEY_HISTORICO = "sessao:{}:historico"
    KEY_RESUMO = "sessao:{}:resumo"

    def __init__(self, client: redis.asyncio.Redis, ttl: int) -> None:
        self._client = client
        self._ttl = ttl

    # ------------------------------------------------------------------
    # ConversationMemoryPort — implementações
    # ------------------------------------------------------------------

    async def obter_contexto(
        self, sessao_id: str
    ) -> tuple[HistoricoConversa, ResumoConversa | None]:
        """
        Recupera o histórico e o resumo de uma sessão.

        Retorna um HistoricoConversa vazio e resumo None
        quando a sessão ainda não existe — comportamento esperado
        para a primeira mensagem de um novo atendimento.
        """
        logger.debug("Buscando contexto | sessao_id='{}'", sessao_id)

        historico_raw, resumo_raw = await self._client.mget(
            self.KEY_HISTORICO.format(sessao_id),
            self.KEY_RESUMO.format(sessao_id),
        )

        historico = (
            self._desserializar_historico(historico_raw)
            if historico_raw
            else HistoricoConversa()
        )

        resumo = self._desserializar_resumo(resumo_raw) if resumo_raw else None

        logger.debug(
            "Contexto obtido | sessao_id='{}' | mensagens={} | resumo={}",
            sessao_id,
            len(historico),
            "presente" if resumo else "ausente",
        )

        return historico, resumo

    async def salvar_contexto(
        self,
        sessao_id: str,
        historico: HistoricoConversa,
        resumo: ResumoConversa | None,
    ) -> None:
        """
        Persiste o histórico e o resumo de uma sessão.

        Renova o TTL a cada salvamento a sessão expira apenas
        após o período de inatividade, não a partir da primeira mensagem.
        """
        logger.debug(
            "Salvando contexto | sessao_id='{}' | mensagens={}",
            sessao_id,
            len(historico),
        )

        async with self._client.pipeline(transaction=True) as pipe:
            pipe.set(
                self.KEY_HISTORICO.format(sessao_id),
                self._serializar_historico(historico),
                ex=self._ttl,
            )

            if resumo is not None:
                pipe.set(
                    self.KEY_RESUMO.format(sessao_id),
                    self._serializar_resumo(resumo),
                    ex=self._ttl,
                )
            else:
                pipe.delete(self.KEY_RESUMO.format(sessao_id))
            
            await pipe.execute()

        logger.info(
            "Contexto salvo | sessao_id='{}' | mensagens={} | resumo={}",
            sessao_id,
            len(historico),
            "presente" if resumo else "ausente",
        )

    # ------------------------------------------------------------------
    # Serialização: domínio → JSON
    # ------------------------------------------------------------------

    def _serializar_historico(self, historico: HistoricoConversa) -> str:
        """Converte HistoricoConversa para JSON string."""

        return json.dumps(
            [{"role": m.role, "conteudo": m.conteudo} for m in historico.mensagens],
            ensure_ascii=False,
        )

    def _serializar_resumo(self, resumo: ResumoConversa) -> str:
        """Converte ResumoConversa para JSON string."""

        return json.dumps(
            {
                "resumo_texto": resumo.resumo_texto,
                "atualizado_em": resumo.atualizado_em.isoformat(),
                "total_turnos_resumidos": resumo.total_turnos_resumidos,
            },
            ensure_ascii=False,
        )

    # ------------------------------------------------------------------
    # Desserialização: JSON → domínio
    # ------------------------------------------------------------------

    def _desserializar_historico(self, raw: bytes) -> HistoricoConversa:
        """Reconstrói HistoricoConversa a partir do JSON armazenado no Redis."""
        dados = json.loads(raw)
        mensagens = tuple(
            Mensagem(role=Mensagem.RoleMensagem(m["role"]), conteudo=m["conteudo"]) for m in dados
        )
        return HistoricoConversa(mensagens=mensagens)

    def _desserializar_resumo(self, raw: bytes) -> ResumoConversa:
        """Reconstrói ResumoConversa a partir do JSON armazenado no Redis."""
        dados = json.loads(raw)
        return ResumoConversa(
            resumo_texto=dados["resumo_texto"],
            atualizado_em=datetime.fromisoformat(dados["atualizado_em"]),
            total_turnos_resumidos=dados["total_turnos_resumidos"],
        )
