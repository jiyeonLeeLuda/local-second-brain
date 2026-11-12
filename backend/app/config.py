"""Runtime settings, read from environment variables or a .env file.

Machine-specific values (DB URL, model server address, notes folder) live only in
the environment so the same code runs on the MacBook (demo data) and the Mac mini
(real notes) without changes.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Storage
    database_url: str = "postgresql+psycopg://localhost:5432/lsb_dev"
    notes_dir: Path = REPO_DIR / "demo-data"

    # OpenAI-compatible model server (Lemonade, llama-server, Ollama, LM Studio ...)
    llm_base_url: str = "http://localhost:13305/api/v1"
    llm_api_key: str = "local"
    llm_model: str = "Qwen3-8B-GGUF"
    llm_timeout_s: float = 120.0
    llm_disable_thinking: bool = True

    # Embeddings. "openai" calls EMBED_BASE_URL/embeddings; "hash" is an offline,
    # deterministic lexical embedder used for tests and for running without a model server.
    embed_provider: Literal["openai", "hash"] = "openai"
    embed_base_url: str = "http://localhost:13305/api/v1"
    embed_api_key: str = "local"
    embed_model: str = "bge-m3"
    embed_dim: int = 1024
    embed_batch_size: int = 32

    # Chunking
    chunk_max_chars: int = 1200
    chunk_min_chars: int = 40

    # Retrieval
    search_top_k: int = 5

    # Web
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
