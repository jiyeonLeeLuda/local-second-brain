import pytest
from fastapi.testclient import TestClient

from app.api import create_app, get_chat, get_embedder
from app.config import get_settings
from app.db import session_dep
from app.llm.errors import ModelServerError
from tests.conftest import write_note


class FakeChat:
    model_name = "fake"

    def __init__(self, fail=False):
        self.fail = fail
        self.messages = None

    def complete(self, messages, temperature=0.2):
        if self.fail:
            raise ModelServerError("down")
        self.messages = messages
        return "JWT는 상태를 저장하지 않는다 [1]"


@pytest.fixture
def client_factory(session, settings, embedder, notes_dir):
    write_note(
        notes_dir / "study",
        "jwt.md",
        "# 인증\n\n## JWT\n\nJWT 토큰은 서버가 상태를 저장하지 않는 인증 방식이다.",
    )

    def make(chat=None):
        app = create_app()
        app.dependency_overrides[session_dep] = lambda: session
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_embedder] = lambda: embedder
        app.dependency_overrides[get_chat] = lambda: chat or FakeChat()
        return TestClient(app)

    return make


def test_health_and_stats(client_factory):
    client = client_factory()
    health = client.get("/api/health").json()
    assert health["db"] is True and health["embed_base_url"] == "hash (offline)"
    assert client.get("/api/stats").json() == {"entries": 0, "chunks": 0, "by_source": {}}


def test_ingest_then_search_then_ask(client_factory):
    chat = FakeChat()
    client = client_factory(chat)
    report = client.post("/api/ingest", json={"source_type": "study"}).json()
    assert report["added"] == 1

    results = client.get("/api/search", params={"q": "JWT 인증", "k": 3}).json()["results"]
    assert results[0]["file_path"] == "study/jwt.md"

    body = client.post("/api/ask", json={"question": "JWT는 뭐야?"}).json()
    assert body["answer"].endswith("[1]")
    assert body["sources"][0]["n"] == 1
    assert "[1] (study/jwt.md" in chat.messages[1]["content"]


def test_ask_returns_503_when_model_server_down(client_factory):
    client = client_factory(FakeChat(fail=True))
    client.post("/api/ingest", json={"source_type": "study"})
    resp = client.post("/api/ask", json={"question": "JWT?"})
    assert resp.status_code == 503
    assert "모델 서버" in resp.json()["detail"]


def test_ask_without_index_does_not_call_llm(client_factory):
    chat = FakeChat()
    resp = client_factory(chat).post("/api/ask", json={"question": "아무거나"})
    assert resp.status_code == 200 and resp.json()["sources"] == []
    assert chat.messages is None


def test_journal_ingest_is_rejected(client_factory):
    resp = client_factory().post("/api/ingest", json={"source_type": "journal"})
    assert resp.status_code == 400


# Fields the frontend reads (frontend/src/lib/api/types.ts). Extra backend fields are fine.
FRONTEND_FIELDS = {
    "health": {"status", "db", "llm_base_url", "embed_base_url"},
    "stats": {"entries", "chunks", "by_source"},
    "ingest": {"scanned", "added", "updated", "unchanged", "deleted", "chunks_embedded"},
    "hit": {"chunk_id", "text", "heading_path", "file_path", "score"},
    "ask": {"answer", "sources"},
}


def test_responses_cover_frontend_contract(client_factory):
    client = client_factory()
    assert FRONTEND_FIELDS["health"] <= client.get("/api/health").json().keys()
    assert FRONTEND_FIELDS["stats"] <= client.get("/api/stats").json().keys()
    ingest = client.post("/api/ingest", json={"source_type": "study"}).json()
    assert FRONTEND_FIELDS["ingest"] <= ingest.keys()
    hit = client.get("/api/search", params={"q": "JWT"}).json()["results"][0]
    assert FRONTEND_FIELDS["hit"] <= hit.keys()
    ask = client.post("/api/ask", json={"question": "JWT?"}).json()
    assert FRONTEND_FIELDS["ask"] <= ask.keys()
    assert FRONTEND_FIELDS["hit"] | {"n"} <= ask["sources"][0].keys()
