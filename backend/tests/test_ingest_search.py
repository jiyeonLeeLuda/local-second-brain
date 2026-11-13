import os

import pytest
from sqlalchemy import func, select

from app.cli import evaluate_retrieval
from app.ingest.pipeline import ingest_source, iter_note_files
from app.llm.errors import ModelServerError
from app.models import Chunk, Entry
from app.search import search
from tests.conftest import write_note

INDEX_NOTE = "# 인덱스\n\n## B-tree\n\nB-tree 인덱스는 범위 검색과 정렬에 강하다.\n\n## GIN\n\nGIN 인덱스는 배열과 JSONB 검색에 쓴다."
DOCKER_NOTE = "# 도커\n\n## 네트워크\n\n컨테이너끼리는 브리지 네트워크로 통신한다."
JWT_NOTE = "# 인증\n\n## JWT\n\nJWT 토큰은 서버가 상태를 저장하지 않는 인증 방식이다."


@pytest.fixture
def populated(notes_dir):
    study = notes_dir / "study"
    write_note(study, "postgres-indexes.md", INDEX_NOTE)
    write_note(study, "docker.md", DOCKER_NOTE)
    write_note(study, "sub/jwt.md", JWT_NOTE)
    return study


def test_first_ingest_adds_everything(session, settings, embedder, populated):
    report = ingest_source(session, settings, "study", embedder)
    assert (report.scanned, report.added, report.unchanged, report.errors) == (3, 3, 0, [])
    assert report.chunks_embedded == session.scalar(select(func.count()).select_from(Chunk))
    paths = set(session.scalars(select(Entry.file_path)))
    assert paths == {"postgres-indexes.md", "docker.md", "sub/jwt.md"}


def test_rerun_only_processes_changes(session, settings, embedder, populated):
    ingest_source(session, settings, "study", embedder)
    again = ingest_source(session, settings, "study", embedder)
    assert (again.added, again.updated, again.unchanged, again.chunks_embedded) == (0, 0, 3, 0)

    write_note(populated, "docker.md", DOCKER_NOTE + "\n\n## 볼륨\n\n볼륨은 데이터를 보존한다.")
    (populated / "sub/jwt.md").unlink()
    third = ingest_source(session, settings, "study", embedder)
    assert (third.updated, third.deleted, third.unchanged) == (1, 1, 1)
    docker = session.scalar(select(Entry).where(Entry.file_path == "docker.md"))
    assert [c.heading_path for c in docker.chunks] == ["도커 > 네트워크", "도커 > 볼륨"]


def test_source_files_are_never_modified(session, settings, embedder, populated):
    before = {p: p.read_bytes() for p in populated.rglob("*.md")}
    ingest_source(session, settings, "study", embedder)
    assert before == {p: p.read_bytes() for p in populated.rglob("*.md")}


def test_journal_is_refused_until_private_schema_exists(session, settings, embedder):
    with pytest.raises(ValueError, match="journal"):
        ingest_source(session, settings, "journal", embedder)


def test_hidden_files_and_symlink_escapes_are_skipped(notes_dir, tmp_path):
    study = notes_dir / "study"
    write_note(study, "ok.md", "# ok")
    write_note(study, ".obsidian/cache.md", "# hidden")
    outside = tmp_path / "secret.md"
    outside.write_text("# 비밀 일기", "utf-8")
    os.symlink(outside, study / "link.md")
    assert [p.name for p in iter_note_files(study)] == ["ok.md"]


def test_model_server_failure_aborts_without_partial_rows(session, settings, populated):
    class Broken:
        model_name, dim = "broken", 1024

        def embed(self, texts):
            raise ModelServerError("down")

    with pytest.raises(ModelServerError):
        ingest_source(session, settings, "study", Broken())
    assert session.scalar(select(func.count()).select_from(Entry)) == 0


def test_changing_embed_model_triggers_reembed(session, settings, embedder, populated):
    ingest_source(session, settings, "study", embedder)

    class Other:
        model_name, dim = "other-model", 1024

        def embed(self, texts):
            return embedder.embed(texts)

    report = ingest_source(session, settings, "study", Other())
    assert report.updated == 3


def test_search_finds_relevant_section(session, settings, embedder, populated):
    ingest_source(session, settings, "study", embedder)
    hits = search(session, embedder, "B-tree 인덱스 범위 검색", k=3)
    assert hits[0].file_path == "study/postgres-indexes.md"
    assert hits[0].heading_path == "인덱스 > B-tree"
    assert hits[0].score > hits[-1].score


def test_search_respects_exclusions_and_unapproved_research(
    session, settings, embedder, populated, notes_dir
):
    research = notes_dir / "research"
    write_note(research, "draft.md", "# 조사\n\n## B-tree\n\nB-tree 인덱스 범위 검색 조사 결과")
    ingest_source(session, settings, "study", embedder)
    ingest_source(session, settings, "research", embedder)

    files = {h.file_path for h in search(session, embedder, "B-tree 인덱스 범위 검색", k=10)}
    assert "research/draft.md" not in files  # unapproved agent output stays in the inbox

    for chunk in session.scalars(select(Chunk).join(Entry).where(Entry.file_path == "docker.md")):
        chunk.excluded = True
    session.commit()
    files = {h.file_path for h in search(session, embedder, "도커 네트워크", k=10)}
    assert "study/docker.md" not in files


def test_evaluate_retrieval_metrics():
    class Hit:
        def __init__(self, f, h):
            self.file_path, self.heading_path = f, h

    results = {
        "q1": [Hit("study/a.md", "A > x")],
        "q2": [Hit("study/z.md", ""), Hit("study/b.md", "B > y")],
        "q3": [Hit("study/z.md", "")],
    }
    questions = [
        {"id": "q1", "question": "q1", "expected_file": "a.md", "expected_heading": "x"},
        {"id": "q2", "question": "q2", "expected_file": "b.md"},
        {"id": "q3", "question": "q3", "expected_file": "c.md"},
    ]
    out = evaluate_retrieval(questions, lambda q, k: results[q], k=5)
    assert out["hit_rate"] == pytest.approx(2 / 3)
    assert out["mrr"] == pytest.approx((1 + 0.5 + 0) / 3)


def test_source_dirs_map_sources_to_vault_folders(session, settings, embedder, notes_dir):
    write_note(
        notes_dir / "02_notes" / "ai", "rag.md", "# RAG\n\n## 개요\n\n검색 후 생성하는 방식이다."
    )
    write_note(notes_dir / "study", "ignored.md", "# 이 폴더는 매핑 때문에 안 읽힌다")
    mapped = settings.model_copy(update={"source_dirs": {"study": "02_notes"}})
    report = ingest_source(session, mapped, "study", embedder)
    assert report.scanned == 1
    assert session.scalar(select(Entry.file_path)) == "ai/rag.md"


def test_source_dirs_accept_absolute_paths(settings, tmp_path):
    mapped = settings.model_copy(update={"source_dirs": {"memo": str(tmp_path / "elsewhere")}})
    assert mapped.source_root("memo") == tmp_path / "elsewhere"
    assert mapped.source_root("study") == settings.notes_dir / "study"
