from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url, pool_pre_ping=True)


def make_session(url: str | None = None) -> Session:
    return sessionmaker(bind=get_engine(url), expire_on_commit=False)()


def session_dep() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = make_session()
    try:
        yield session
    finally:
        session.close()
