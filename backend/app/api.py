"""HTTP API (FastAPI). Run: uv run uvicorn app.api:app --reload"""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import session_dep
from app.ingest.pipeline import INGESTIBLE_SOURCES, ingest_source
from app.llm.chat import ChatModel, make_chat
from app.llm.embeddings import Embedder, make_embedder
from app.llm.errors import ModelServerError
from app.models import Chunk, Entry
from app.qa import answer_question
from app.search import search

log = logging.getLogger(__name__)


@lru_cache
def get_embedder() -> Embedder:
    return make_embedder(get_settings())


@lru_cache
def get_chat() -> ChatModel:
    return make_chat(get_settings())


SessionDep = Annotated[Session, Depends(session_dep)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
ChatDep = Annotated[ChatModel, Depends(get_chat)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


class IngestRequest(BaseModel):
    source_type: str = "study"
    reembed: bool = False


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)


def _model_unavailable(exc: ModelServerError) -> HTTPException:
    log.warning("model server error: %s", exc)
    return HTTPException(
        status_code=503,
        detail="모델 서버에 연결할 수 없습니다. LLM_BASE_URL / EMBED_BASE_URL 설정과 서버 상태를 확인하세요.",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Serendipity Journal API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health(session: SessionDep, settings: SettingsDep) -> dict:
        try:
            session.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        return {
            "status": "ok" if db_ok else "degraded",
            "db": db_ok,
            "llm_base_url": settings.llm_base_url,
            "embed_base_url": settings.embed_base_url
            if settings.embed_provider == "openai"
            else "hash (offline)",
        }

    @app.get("/api/stats")
    def stats(session: SessionDep) -> dict:
        by_source = dict(
            session.execute(
                select(Entry.source_type, func.count()).group_by(Entry.source_type)
            ).all()
        )
        return {
            "entries": sum(by_source.values()),
            "chunks": session.scalar(select(func.count()).select_from(Chunk)) or 0,
            "by_source": by_source,
        }

    @app.post("/api/ingest")
    def ingest(
        body: IngestRequest, session: SessionDep, settings: SettingsDep, embedder: EmbedderDep
    ) -> dict:
        if body.source_type not in INGESTIBLE_SOURCES:
            raise HTTPException(400, f"source_type must be one of {list(INGESTIBLE_SOURCES)}")
        try:
            report = ingest_source(
                session, settings, body.source_type, embedder, reembed=body.reembed
            )
        except ModelServerError as exc:
            raise _model_unavailable(exc) from exc
        return report.as_dict()

    @app.get("/api/search")
    def search_endpoint(
        session: SessionDep,
        embedder: EmbedderDep,
        q: Annotated[str, Query(min_length=1, max_length=2000)],
        k: Annotated[int, Query(ge=1, le=50)] = 5,
    ) -> dict:
        try:
            hits = search(session, embedder, q, mode="study_qa", k=k)
        except ModelServerError as exc:
            raise _model_unavailable(exc) from exc
        return {"results": [h.as_dict() for h in hits]}

    @app.post("/api/ask")
    def ask(body: AskRequest, session: SessionDep, embedder: EmbedderDep, chat: ChatDep) -> dict:
        try:
            result = answer_question(session, embedder, chat, body.question, k=body.k)
        except ModelServerError as exc:
            raise _model_unavailable(exc) from exc
        return result.as_dict()

    return app


app = create_app()
