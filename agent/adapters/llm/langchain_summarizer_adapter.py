"""
adapters/llm/langchain_summarizer_adapter.py
 
Adapter concreto que implementa SummarizerPort usando LangChain.
Usa um modelo dedicado tipicamente menor e mais barato que o modelo principal
já que sumarização é uma tarefa mecânica que não requer capacidades avançadas.
"""

from datetime import datetime, timezone
 
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
 
from agent.adapters.llm.prompts.summarizer_prompt import PROMPT_SUMARIZACAO
from agent.domain.value_objects.historico_conversa import HistoricoConversa
from agent.domain.value_objects.resumo_conversa import ResumoConversa
 
 
class LangChainSummarizerAdapter:
    """
    Implementa SummarizerPort comprimindo o histórico via LLM.
 
    Recebe o BaseChatModel pronto via injeção de dependência — consistente
    com o padrão do LangChainChatAdapter principal. Quem decide qual modelo
    usar (e com qual temperatura) é o container de dependências no startup.
 
    Exemplos
    --------
    >>> # No container de dependências (startup):
    >>> summarizer_llm = factory.create(settings.SUMMARIZER_MODEL)
    >>> adapter = LangChainSummarizerAdapter(llm=summarizer_llm)
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = PROMPT_SUMARIZACAO | llm | StrOutputParser()
        logger.debug("LangChainSummarizerAdapter inicializado e chain compilada.")


    async def resumir_conversa(
        self,
        historico: HistoricoConversa,
        resumo_anterior: ResumoConversa | None,
    ) -> ResumoConversa:
        """
        Comprime o histórico em um ResumoConversa atualizado.
 
        Incorpora o resumo anterior quando presente, garantindo
        que o contexto de longo prazo não seja perdido entre sumarizações.
 
        Parâmetros
        ----------
        historico : HistoricoConversa
            Janela de mensagens recentes a ser comprimida.
        resumo_anterior : ResumoConversa | None
            Resumo existente a ser incorporado, ou None na primeira sumarização.
 
        Retorna
        -------
        ResumoConversa
            Novo resumo consolidado com timestamp e contagem de turnos atualizada.
        """
        total_turnos = len(historico)

        logger.debug(
            "Iniciando sumarização | turnos={} | resumo_anterior={}",
            total_turnos,
            "presente" if resumo_anterior else "ausente",
        )

        resposta = await self._chain.ainvoke({
            "resumo_anterior": self._formatar_resumo_anterior(resumo_anterior),
            "historico_formatado": self._formatar_historico(historico)
        })

        resumo_texto = resposta.strip()
        turnos_anteriores = resumo_anterior.total_turnos_resumidos if resumo_anterior else 0

        resumo = ResumoConversa(
            resumo_texto=resumo_texto,
            atualizado_em=datetime.now(timezone.utc),
            total_turnos_resumidos=turnos_anteriores + total_turnos,
        )

        logger.info(
            "Sumarização concluída | turnos_resumidos={} | caracteres={}",
            resumo.total_turnos_resumidos,
            len(resumo_texto),
        )
 
        return resumo

    
    def _formatar_historico(self, historico: HistoricoConversa) -> str:
        """Formata mensagens como 'role: conteudo' por linha."""
        return "\n".join(
            f"{m.role.value}: {m.conteudo}"
            for m in historico.mensagens
        )
 
    def _formatar_resumo_anterior(self, resumo: ResumoConversa | None) -> str:
        """
        Formata o resumo anterior para injeção no prompt.
        Retorna string vazia quando não há resumo — o template
        renderiza limpo sem texto extra.
        """
        if resumo is None:
            return ""
        return f"Resumo anterior:\n{resumo.resumo_texto}\n\n"
 