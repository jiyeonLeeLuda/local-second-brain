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
    # Optional per-source folders, relative to notes_dir (or absolute), e.g. an Obsidian
    # vault: SOURCE_DIRS='{"journal": "<morning-page-folder>", "study": "<notes-folder>"}'.
    # Sources not listed default to notes_dir/<source_type>.
    source_dirs: dict[str, str] = {}

    # OpenAI-compatible model server (Lemonade, llama-server, Ollama, LM Studio ...)
    llm_base_url: str = "http://localhost:13305/api/v1"
    llm_api_key: str = "local"
    llm_model: str = "Qwen3.5-9B-GGUF"
    llm_timeout_s: float = 120.0
    llm_disable_thinking: bool = True

    # Embeddings. "openai" calls EMBED_BASE_URL/embeddings; "hash" is an offline,
    # deterministic lexical embedder used for tests and for running without a model server.
    embed_provider: Literal["openai", "hash"] = "openai"
    embed_base_url: str = "http://localhost:13305/api/v1"
    embed_api_key: str = "local"
    embed_model: str = "Qwen3-Embedding-0.6B-GGUF"
    embed_dim: int = 1024
    embed_batch_size: int = 32
    # Prepended to search queries only (not to stored passages). Qwen3-Embedding is trained
    # with this query format; it lifted MRR 0.817 -> 0.900 on the demo eval set.
    # Set to an empty string for embedding models that don't use instructions.
    embed_query_instruction: str = (
        "Instruct: Given a question, retrieve passages from personal study notes "
        "that answer it\nQuery: "
    )

    # Chunking
    chunk_max_chars: int = 1200
    chunk_min_chars: int = 40

    # Retrieval
    search_top_k: int = 5

    # Web
    cors_origins: list[str] = ["http://localhost:3000"]

    def source_root(self, source_type: str) -> Path:
        configured = self.source_dirs.get(source_type)
        if not configured:
            return self.notes_dir / source_type
        path = Path(configured).expanduser()
        return path if path.is_absolute() else self.notes_dir / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
