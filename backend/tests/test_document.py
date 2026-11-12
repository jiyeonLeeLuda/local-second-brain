import os
from datetime import date
from pathlib import Path

from app.ingest.document import detect_language, parse_file, parse_text


def test_frontmatter_fields(tmp_path: Path):
    p = tmp_path / "note.md"
    p.write_text("---\ndate: 2026-07-03\ntags: [db, sql]\n---\n# 조인 정리\n\n본문", "utf-8")
    doc = parse_file(p)
    assert doc.title == "조인 정리"
    assert doc.date == date(2026, 7, 3)
    assert doc.date_confidence == "high"
    assert doc.tags == ["db", "sql"]
    assert doc.language == "ko"
    assert "---" not in doc.body


def test_date_from_filename(tmp_path: Path):
    p = tmp_path / "2026-11-02.md"
    p.write_text("오늘의 모닝페이지", "utf-8")
    doc = parse_file(p)
    assert doc.date == date(2026, 11, 2)
    assert doc.date_confidence == "high"
    assert doc.title == "2026-11-02"


def test_date_falls_back_to_mtime_with_low_confidence(tmp_path: Path):
    p = tmp_path / "memo.txt"
    p.write_text("날짜 없는 메모", "utf-8")
    os.utime(p, (1_780_000_000, 1_780_000_000))
    doc = parse_file(p)
    assert doc.date_confidence == "low"
    assert doc.date is not None


def test_malformed_frontmatter_keeps_body():
    doc = parse_text(b"---\ndate: [unclosed\n---\nbody text", Path("x.md"))
    assert "body text" in doc.body


def test_hash_changes_with_content():
    a = parse_text(b"one", Path("a.md")).content_hash
    b = parse_text(b"two", Path("a.md")).content_hash
    assert a != b and len(a) == 64


def test_detect_language():
    assert detect_language("FastAPI는 비동기 웹 프레임워크다") == "ko"
    assert detect_language("FastAPI is an async web framework") == "en"
