"""
agent/config/configuration.py

Gerenciamento centralizado de configurações e variáveis de ambiente do CTB Assist.
Utiliza Pydantic Settings para validação de tipos, carregamento automático do .env
e defaults seguros que permitem execução local imediata (Qdrant em disco e checkpointer em memória).
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais da aplicação CTB Assist."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )

    # =========================
    # LLM CONFIGURATION
    # =========================
    LLM_PROVIDER: str = Field(
        default="google_genai",
        description="Provider de LLM usado pelo sistema (ex: google_genai, openai, ollama, groq)",
    )
    LLM_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Nome do modelo de LLM principal",
    )
    LLM_BASE_URL: str | None = Field(
        default=None,
        description="URL base customizada para a API do LLM, se aplicável",
    )
    LLM_API_KEY: str | None = Field(
        default=None,
        description="Chave de API do provedor de LLM",
    )
    LLM_TEMPERATURE: float = Field(
        default=0.0,
        description="Temperatura para controle da criatividade das respostas",
    )
    LLM_MAX_TOKENS: int = Field(
        default=2048,
        description="Limite máximo de tokens gerados por resposta",
    )
    LLM_MAX_RETRIES: int = Field(
        default=3,
        description="Número máximo de tentativas em caso de erro na API",
    )
    LLM_TIMEOUT: float = Field(
        default=120.0,
        description="Tempo máximo de espera (em segundos) por uma resposta",
    )
    SUMMARIZER_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Modelo de LLM usado para sumarizar conversas longas",
    )
    LLM_MAX_HISTORY_MESSAGES: int = Field(
        default=20,
        description="Limite de mensagens no contexto da LLM antes de resumir",
    )
    LLM_CONFIANCA_MINIMA: float = Field(
        default=0.25,
        description="Confiança mínima requerida para considerar uma evidência relevante",
    )

    # =========================
    # AGENTIC RAG & SKILLS
    # =========================
    MAX_RETRIEVAL_ATTEMPTS: int = Field(
        default=3,
        description="Número máximo de reformulações/buscas no loop do RAG agêntico",
    )
    MAX_AGENT_STEPS: int = Field(
        default=8,
        description="Número máximo de decisões do roteador em um único turno (proteção contra loops)",
    )
    SKILLS_DIR: str = Field(
        default="./skills",
        description="Diretório contendo os arquivos SKILL.md carregados sob demanda",
    )

    # =========================
    # QDRANT CONFIGURATION
    # =========================
    QDRANT_URL: str | None = Field(
        default=None,
        description="URL de conexão com servidor Qdrant remoto/Docker (opcional; se vazio usa QDRANT_PATH local)",
    )
    QDRANT_PATH: str = Field(
        default="./data/qdrant",
        description="Caminho local persistente do Qdrant em disco quando QDRANT_URL não for informado",
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="ctb_assist_docs",
        description="Nome da collection principal no Qdrant",
    )
    QDRANT_DENSE_MODEL: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="Nome do modelo de embeddings densos configurado no Qdrant/FastEmbed",
    )
    QDRANT_DENSE_SIZE: int = Field(
        default=384,
        description="Dimensão dos vetores densos (paraphrase-multilingual-MiniLM-L12-v2=384, multilingual-e5-large=1024)",
    )
    QDRANT_SPARSE_MODEL: str = Field(
        default="Qdrant/bm42-all-minilm-l6-v2-attentions",
        description="Nome do modelo de embeddings esparsos configurado no Qdrant/FastEmbed",
    )
    QDRANT_TOP_K: int = Field(
        default=8,
        description="Quantidade padrão de documentos retornados pela busca híbrida do Qdrant",
    )

    # =========================
    # SPLITTER & DOCS CONFIGURATION
    # =========================
    DOCS_DIR: str = Field(
        default="./docs",
        description="Diretório contendo os PDFs oficiais (CTB, Resolução 1.020/2025 e MBFT)",
    )
    PROCESSED_DATA_DIR: str = Field(
        default="./data/processed",
        description="Diretório para salvar artefatos processados (ex.: MBFT estruturado em JSON/MD)",
    )
    SPLITTER_CHUNK_SIZE: int = Field(
        default=1400,
        description="Tamanho alvo de cada chunk em caracteres para artigos extensos",
    )
    SPLITTER_CHUNK_OVERLAP: int = Field(
        default=120,
        description="Sobreposição entre sub-chunks consecutivos quando necessário",
    )

    # =========================
    # RERANKER CONFIGURATION
    # =========================
    RERANKER_ENABLED: bool = Field(
        default=True,
        description="Liga o reranker cross-encoder; se desligado ou indisponível, mantém a ordem da busca",
    )
    RERANKER_MODEL: str = Field(
        default="BAAI/bge-reranker-v2-m3-int8",
        description="Cross-encoder multilíngue suportado pelo fastembed (ONNX, ~570 MB, baixado no 1º uso)",
    )
    RERANKER_TOP_K: int = Field(
        default=5,
        description="Quantidade de documentos mantidos após o reranking",
    )
    RERANKER_BATCH_SIZE: int = Field(
        default=8,
        description="Tamanho do lote para processamento do reranker",
    )

    # =========================
    # MEMORY / REDIS (OPTIONAL)
    # =========================
    REDIS_URL: str | None = Field(
        default=None,
        description="URL do Redis para memória externa (opcional; padrão usa memória em RAM / MemorySaver)",
    )
    TIME_TO_LIVE: int = Field(
        default=86400,
        description="Tempo de vida (segundos) do contexto de uma conversa no Redis",
    )

    # =========================
    # MCP SERVERS (OPTIONAL)
    # =========================
    MCP_CTB_SERVER_URL: str | None = Field(
        default=None,
        description="URL/comando do servidor FastMCP próprio de cálculos e validações do CTB",
    )
    MCP_FETCH_ENABLED: bool = Field(
        default=True,
        description="Habilita integração com servidor MCP Fetch da comunidade quando configurado",
    )


settings = Settings()
