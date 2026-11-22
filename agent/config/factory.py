"""
agent/config/factory.py

Fábrica de composição (Dependency Injection) da Arquitetura Hexagonal do CTB Assist.
Conecta os adapters reais (Qdrant local ou remoto, LLM via LangChain, Skills em disco,
Checkpointer MemorySaver, Memória em RAM ou Redis, Guardrails e MCPs).
"""

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from qdrant_client import AsyncQdrantClient

from agent.adapters.guardrails.default_guardrail_adapter import DefaultGuardrailAdapter
from agent.adapters.llm.langchain_chat_adapter import LangChainChatAdapter
from agent.adapters.llm.langchain_summarizer_adapter import LangChainSummarizerAdapter
from agent.adapters.llm.llm_factory import LangChainLLMFactory
from agent.adapters.loaders.pdf_loader_adapter import PDFLoaderAdapter
from agent.adapters.mcp.null_mcp_adapter import NullMCPAdapter
from agent.adapters.memory.in_memory_memory_adapter import (
    InMemoryConversationMemoryAdapter,
    SimpleSummarizerAdapter,
)
from agent.adapters.orchestrator.langgraph_adapter import LangGraphOrchestratorAdapter
from agent.adapters.retrieval.cross_encoder_reranker_adapter import NullRerankerAdapter
from agent.adapters.skills.filesystem_skill_adapter import FileSystemSkillAdapter
from agent.adapters.splitters.legal_splitter_adapter import LegalArticleSplitterAdapter
from agent.adapters.vectorstores.qdrant_adapter import QdrantVectorStoreAdapter
from agent.application.indexar_documento_use_case import IndexarDocumentoUseCase
from agent.application.remover_documento_use_case import RemoverDocumentoUseCase
from agent.config.configuration import settings
from agent.domain.ports.driven.conversation_memory_port import ConversationMemoryPort
from agent.domain.ports.driven.document_loader_port import DocumentLoaderPort
from agent.domain.ports.driven.document_splitter_port import DocumentSplitterPort
from agent.domain.ports.driven.guardrail_port import GuardrailPort
from agent.domain.ports.driven.llm_port import LLMPort
from agent.domain.ports.driven.mcp_tool_port import MCPToolPort
from agent.domain.ports.driven.reranker_port import RerankerPort
from agent.domain.ports.driven.skill_port import SkillPort
from agent.domain.ports.driven.summarizer_port import SummarizerPort
from agent.domain.ports.driven.vector_store_port import VectorStorePort


def create_qdrant_client() -> AsyncQdrantClient:
    """Cria AsyncQdrantClient remoto (se QDRANT_URL definido) ou local em disco."""
    if settings.QDRANT_URL:
        return AsyncQdrantClient(url=settings.QDRANT_URL)
    qdrant_path = Path(settings.QDRANT_PATH)
    qdrant_path.mkdir(parents=True, exist_ok=True)
    return AsyncQdrantClient(path=str(qdrant_path))


def build_langgraph_orchestrator(
    llm: LLMPort,
    vector_store: VectorStorePort,
    reranker: RerankerPort | None = None,
    memory: ConversationMemoryPort | None = None,
    summarizer: SummarizerPort | None = None,
    skill_port: SkillPort | None = None,
    mcp_port: MCPToolPort | None = None,
    guardrail_port: GuardrailPort | None = None,
    checkpointer: Any | None = None,
) -> LangGraphOrchestratorAdapter:
    """Constrói o orquestrador via injeção de dependências (facilita mocks e testes)."""
    return LangGraphOrchestratorAdapter(
        llm=llm,
        vector_store=vector_store,
        reranker=reranker or NullRerankerAdapter(),
        memory=memory or InMemoryConversationMemoryAdapter(),
        summarizer=summarizer or SimpleSummarizerAdapter(),
        skill_port=skill_port or FileSystemSkillAdapter(),
        mcp_port=mcp_port or NullMCPAdapter(),
        guardrail_port=guardrail_port or DefaultGuardrailAdapter(),
        checkpointer=checkpointer if checkpointer is not None else MemorySaver(),
    )


async def get_real_langgraph_orchestrator(
    mcp_port: MCPToolPort | None = None,
    guardrail_port: GuardrailPort | None = None,
    checkpointer: Any | None = None,
) -> LangGraphOrchestratorAdapter:
    """Instancia e conecta todos os adapters reais do CTB Assist."""
    llm_factory = LangChainLLMFactory()
    llm = LangChainChatAdapter(llm=llm_factory.create(settings.LLM_MODEL))

    try:
        summarizer_llm = llm_factory.create(settings.SUMMARIZER_MODEL)
        summarizer: SummarizerPort = LangChainSummarizerAdapter(llm=summarizer_llm)
    except Exception:
        summarizer = SimpleSummarizerAdapter()

    qdrant_client = create_qdrant_client()
    vector_store = await QdrantVectorStoreAdapter.criar(qdrant_client)

    memory: ConversationMemoryPort = InMemoryConversationMemoryAdapter()
    if settings.REDIS_URL:
        import redis.asyncio as aioredis
        from agent.adapters.memory.redis_memory_adapter import RedisMemoryAdapter

        redis_client = aioredis.from_url(settings.REDIS_URL)
        memory = RedisMemoryAdapter(client=redis_client, ttl=settings.TIME_TO_LIVE)

    return build_langgraph_orchestrator(
        llm=llm,
        vector_store=vector_store,
        reranker=NullRerankerAdapter(),
        memory=memory,
        summarizer=summarizer,
        skill_port=FileSystemSkillAdapter(settings.SKILLS_DIR),
        mcp_port=mcp_port or NullMCPAdapter(),
        guardrail_port=guardrail_port or DefaultGuardrailAdapter(),
        checkpointer=checkpointer if checkpointer is not None else MemorySaver(),
    )


def build_ingestion_use_case(
    loader: DocumentLoaderPort,
    splitter: DocumentSplitterPort,
    vector_store: VectorStorePort,
) -> IndexarDocumentoUseCase:
    return IndexarDocumentoUseCase(
        loader=loader,
        splitter=splitter,
        vector_store=vector_store,
    )


async def get_real_ingestion_use_case() -> IndexarDocumentoUseCase:
    loader = PDFLoaderAdapter()
    splitter = LegalArticleSplitterAdapter()
    qdrant_client = create_qdrant_client()
    vector_store = await QdrantVectorStoreAdapter.criar(client=qdrant_client)
    return build_ingestion_use_case(
        loader=loader,
        splitter=splitter,
        vector_store=vector_store,
    )


def build_remove_use_case(
    vector_store: VectorStorePort,
) -> RemoverDocumentoUseCase:
    return RemoverDocumentoUseCase(vector_store=vector_store)


async def get_real_remove_use_case() -> RemoverDocumentoUseCase:
    qdrant_client = create_qdrant_client()
    vector_store = await QdrantVectorStoreAdapter.criar(client=qdrant_client)
    return build_remove_use_case(vector_store=vector_store)
