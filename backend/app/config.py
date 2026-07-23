from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    deepgram_api_key: str
    groq_api_key: str
    openai_api_key: str = ""  # Optional — not needed when using fastembed
    nvidia_api_key: str = ""  # Optional — for GLM 5.2 / NVIDIA API

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # Provider Selection
    stt_provider: str = "deepgram"
    llm_provider: str = "groq"
    embedding_provider: str = "local"  # "local" (fastembed) | "openai"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nvidia_model: str = "z-ai/glm-5.2"

    # App Config
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    max_session_duration_hours: int = 4
    vad_silence_threshold_ms: int = 1500
    question_confidence_threshold: float = 0.65

    # RAG Pipeline (Phase C)
    rag_enable_reranking: bool = True
    rag_enable_query_expansion: bool = True
    rag_hybrid_bm25_weight: float = 0.4
    rag_hybrid_vector_weight: float = 0.6
    rag_retrieval_top_k: int = 8       # candidates before reranking
    rag_final_top_k: int = 4           # chunks sent to LLM after reranking
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
