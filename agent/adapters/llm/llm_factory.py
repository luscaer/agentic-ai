"""
agent/adapters/llm/llm_factory.py

Factory para instanciação dinâmica de clientes de LLM do LangChain.
Isola a lógica de inicialização (chaves, URLs, parâmetros) do adapter principal.
"""

from typing import Any, Protocol

from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
from loguru import logger

from agent.adapters.llm.exceptions import LLMInitError
from agent.config.configuration import settings
from agent.domain.exceptions import ValorInvalidoError


class LLMFactory(Protocol):
    """
    Contrato para criação de clientes de chat (BaseChatModel).

    Esta factory vive na camada de infraestrutura/adapters. Ela permite que
    o sistema instancie diferentes modelos (ex: OpenAI, Mistral, Ollama)
    baseado em configurações dinâmicas, sem acoplar o adapter a uma
    implementação específica de LLM.
    """

    def create(
        self,
        model_name: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,  # <-- Mantém para flexibilidade total
    ) -> BaseChatModel:
        """
        Constrói e retorna um cliente de chat pronto para uso.

        Parâmetros
        ----------
        model_name : str
            Identificador do modelo a ser instanciado (ex: 'gpt-4o', 'mistral').
        temperature: float | None
            Criatividade do modelo
        max_tokens: int | None
            Quantidade máxima de tokens possíveis de serem gerados
        **kwargs : Any
            Parâmetros adicionais para a inicialização do modelo, como `api_key` ou `base_url`.

        Retorna
        -------
        BaseChatModel
            Instância configurada do modelo de linguagem do LangChain.
        """
        ...


class LangChainLLMFactory:
    """
    Cria instâncias de BaseChatModel configuradas via settings.

    Providers suportados nativamente pelo init_chat_model:
    - ollama       → Modelos locais
    - openai       → GPT-* ou APIs compatíveis (usando base_url)
    - google_genai → Gemini via API do Google
    - groq         → Modelos open-source super rápidos via Groq

    Exemplos
    --------
    >>> factory = LangChainLLMFactory()
    >>> model = factory.create("gpt-4o-mini", 0.1, 1024)
    """

    def __init__(self) -> None:
        logger.debug(
            "LangChainLLMFactory inicializada | provider='{}' | base_url='{}'",
            settings.LLM_PROVIDER,
            settings.LLM_BASE_URL or "padrão do provider",
        )

    def create(
        self,
        model_name: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """
        Instancia e retorna um cliente de chat configurado.

        Parâmetros
        ----------
        model_name : str
            Nome do modelo a ser instanciado (ex.: "gpt-4o-mini", "llama3.2").

        Retorna
        -------
        BaseChatModel
            Cliente LangChain pronto para uso.

        Levanta
        -------
        ValorInvalidoError
            Se model_name ou LLM_PROVIDER estiverem vazios.
        LLMInitError
            Se o provider falhar durante a inicialização.
        """
        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        normalizado = model_name.strip()
        if not normalizado:
            raise ValorInvalidoError("model_name", "não pode ser vazio")

        provider = settings.LLM_PROVIDER.strip()
        if not provider:
            raise ValorInvalidoError("LLM_PROVIDER", "não configurado no settings")

        model_id = f"{provider}:{normalizado}"

        with logger.contextualize(model=model_id, provider=provider):
            logger.debug(
                "Configurando modelo | temperature={} | max_tokens={}",
                temp,
                tokens,
            )
            try:
                model = self._build_model(provider, normalizado, temp, tokens, **kwargs)
                logger.info("Modelo '{}' inicializado com sucesso.", model_id)
                return model
            except Exception as e:
                logger.error("Falha ao inicializar '{}' | erro={}", model_id, e)
                raise LLMInitError(model_id=model_id, motivo=str(e)) from e

    def _build_model(
        self, 
        provider: str, 
        model_name: str, 
        temperature: float, 
        max_tokens: int,
        **extra_kwargs: Any
    ) -> BaseChatModel:
        """
        Delega a criação do cliente para o init_chat_model do LangChain,
        injetando as configurações globais do sistema.
        """
        llm_args: dict[str, Any] = {
            "temperature": temperature,
            "max_retries": settings.LLM_MAX_RETRIES,
            "timeout": settings.LLM_TIMEOUT,
        }

        if provider == "google_genai":
            llm_args["max_output_tokens"] = max_tokens
        else:
            llm_args["max_tokens"] = max_tokens

        if settings.LLM_API_KEY:
            llm_args["api_key"] = settings.LLM_API_KEY
            
        if settings.LLM_BASE_URL:
            llm_args["base_url"] = settings.LLM_BASE_URL

        llm_args.update(extra_kwargs)

        return init_chat_model(model_name, model_provider=provider, **llm_args)
