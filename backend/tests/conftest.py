import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import BACKEND_DIR, Settings
from app.llm.embeddings import HashEmbedder

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/lsb_test")
DIM = 1024  # must match the Vector() dim the models were imported with


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DB_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip(f"test database not reachable: {TEST_DB_URL}")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS chunks, entries, alembic_version CASCADE"))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")  # exercise the real migration, not create_all
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE chunks, entries RESTART IDENTITY CASCADE"))
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    yield s
    s.close()


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    root = tmp_path / "notes"
    (root / "study").mkdir(parents=True)
    return root


@pytest.fixture
def settings(notes_dir: Path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=TEST_DB_URL,
        notes_dir=notes_dir,
        embed_provider="hash",
        embed_dim=DIM,
        llm_base_url="http://llm.invalid/v1",
    )


@pytest.fixture
def embedder() -> HashEmbedder:
    return HashEmbedder(DIM)


def write_note(root: Path, rel: str, body: str, date: str = "2026-10-01") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ndate: {date}\ntags: [test]\n---\n{body}", encoding="utf-8")
    return path
