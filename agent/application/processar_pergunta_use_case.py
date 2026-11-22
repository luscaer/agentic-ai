"""
agent/application/processar_pergunta_use_case.py

Use Case responsável pelo pipeline de resposta a consultas de usuários (RAG).
Orquestra: memória → reescrita de query → busca vetorial → reranking → LLM.

Regras:
- Depende exclusivamente de Ports (contratos) — zero acoplamento com frameworks.
- Mantém o estado da conversa e gerencia a compressão de memória (summarizer).
- Retorna a Entidade RespostaIA contendo rastreabilidade (fontes e confiança).
"""

from loguru import logger

from agent.domain.entities import Consulta
from agent.domain.entities import RespostaIA
from agent.domain.ports.driven import SummarizerPort
from agent.domain.ports.driven import ConversationMemoryPort
from agent.domain.ports.driven.llm_port import LLMPort
from agent.domain.ports.driven.reranker_port import RerankerPort
from agent.domain.ports.driven.vector_store_port import VectorStorePort
from agent.domain.value_objects.confianca_resposta import ConfiancaResposta
from agent.domain.value_objects.fonte_documento import FonteDocumento
from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.historico_conversa import Mensagem
from agent.domain.value_objects.topico import Topico


class ProcessarPerguntaUseCase:
    """
    Orquestra o pipeline de Geração Aumentada por Recuperação (RAG) do Agente.

    Fluxo:
        1. Recupera o contexto da sessão (histórico e resumo de longo prazo).
        2. Inicializa a Entidade de Consulta.
        3. Reescreve a pergunta para otimização de busca vetorial.
        4. Busca documentos no Vector Store baseando-se no Tópico.
        5. Aplica Reranking para refinar os documentos recuperados.
        6. Gera a resposta via LLM usando o contexto refinado.
        7. Atualiza e condensa o histórico de conversação (se necessário).
        8. Persiste o novo contexto na memória e retorna a Resposta.
    """

    def __init__(
        self,
        llm: LLMPort,
        vector_store: VectorStorePort,
        reranker: RerankerPort,
        memory: ConversationMemoryPort,
        summarizer: SummarizerPort,
        limite_mensagens: int,
    ) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._reranker = reranker
        self._memory = memory
        self._summarizer = summarizer
        self._limite_mensagens = limite_mensagens

    # ------------------------------------------------------------------
    # ProcessarPerguntaPort — implementação
    # ------------------------------------------------------------------

    async def executar(
        self,
        pergunta: str,
        topico_str: str,
        sessao_id: str,
    ) -> RespostaIA:
        """
        Executa o pipeline RAG para responder a uma dúvida do usuário.

        Parâmetros
        ----------
        pergunta : str
            A pergunta em linguagem natural enviada pelo usuário.
        topico : str
            O tópico/assunto identificado (ex: MCASP, ICMS) para filtragem.
        sessao_id : str
            O identificador único da sessão de chat para controle de memória.

        Retorna
        -------
        RespostaIA
            Entidade contendo o texto da resposta, nível de confiança,
            necessidade de escalação e as fontes utilizadas.
        """
        topico = Topico(valor=topico_str)

        logger.info(
            "Iniciando processamento de pergunta | sessao_id={} | tópico='{}'",
            sessao_id,
            topico.valor,
        )

        # 1. Recupera o contexto da sessão (histórico e resumo de longo prazo).
        historico, resumo = await self._memory.obter_contexto(sessao_id=sessao_id)

        # 2. Reescreve a pergunta para otimização de busca vetorial.
        pergunta_reescrita = await self._llm.reescrever_query(
            pergunta=pergunta, topico=topico, historico=historico
        )
        logger.debug("Query reescrita para busca: '{}'", pergunta_reescrita)

        # 3. Inicializa a Entidade de Consulta. 
        consulta = Consulta(
            sessao_id=sessao_id,
            pergunta_original=pergunta,
            topico=topico,
            historico=historico,
            resumo=resumo,
            pergunta_reescrita=pergunta_reescrita,
        )

        nova_msg_user = Mensagem(
            Mensagem.RoleMensagem.USUARIO, conteudo=consulta.pergunta_original
        )
        consulta.historico = consulta.historico.adicionar(nova_msg_user)

        # 4. Busca documentos no Vector Store baseando-se no Tópico.
        resultados = await self._vector_store.buscar_por_topico(
            query=pergunta_reescrita, topico=topico
        )

        # 5. Aplica Reranking para refinar os documentos recuperados.
        resultados_reranqueados = await self._reranker.reranquear(
            query=consulta.pergunta_reescrita, documentos=resultados
        )

        maior_score = (
            resultados_reranqueados[0].score_relevancia
            if resultados_reranqueados
            else 0.0
        )
        confianca = ConfiancaResposta(valor=maior_score)

        logger.debug(
            "Busca concluída | fontes_retornadas={} | score_maximo={:.2f}",
            len(resultados_reranqueados),
            maior_score,
        )

        # 6. Gera a resposta via LLM usando o contexto refinado.
        response = await self._llm.gerar_resposta(
            contexto=self._transformar_resultados(resultados_reranqueados),
            pergunta=consulta.pergunta_reescrita,
            topico=consulta.topico,
            historico=consulta.historico,
        )

        nova_msg_ai = Mensagem(role=Mensagem.RoleMensagem.ASSISTENTE, conteudo=response)
        consulta.historico = consulta.historico.adicionar(nova_msg_ai)

        # 7. Atualiza e condensa o histórico de conversação (se necessário).
        if len(consulta.historico.mensagens) >= self._limite_mensagens:
            logger.info("Limite de histórico atingido. Iniciando compressão (Summarizer).")
            novo_resumo = await self._summarizer.resumir_conversa(
                consulta.historico, consulta.resumo
            )
            consulta.historico = HistoricoConversa()
            consulta.resumo = novo_resumo

        # 8. Persiste o novo contexto na memória e retorna a Resposta.
        await self._memory.salvar_contexto(
            sessao_id=sessao_id, historico=consulta.historico, resumo=consulta.resumo
        )

        logger.info("Processamento concluído com sucesso | sessao_id={}", sessao_id)

        return RespostaIA(
            conteudo=response,
            fontes=resultados_reranqueados,
            confianca=confianca,
            necessita_escalacao=False,
        )

    def _transformar_resultados(self, resultados: list[FonteDocumento]) -> str:
        """
        Formata os documentos recuperados em um único bloco de texto para o prompt.
        """
        if not resultados:
            return "Nenhum documento relevante encontrado."

        return "\n\n".join([doc.trecho_preview for doc in resultados])
