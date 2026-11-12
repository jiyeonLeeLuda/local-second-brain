"""Read one note file into a normalized ParsedDocument (no DB, no network)."""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import frontmatter

_DATE_IN_NAME = re.compile(r"(\d{4})[-_.]?(\d{2})[-_.]?(\d{2})")
_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")
_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)


@dataclass
class ParsedDocument:
    body: str
    title: str
    date: date | None
    date_confidence: str  # "high" | "low"
    language: str  # "ko" | "en"
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""
    metadata: dict = field(default_factory=dict)


def content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def detect_language(text: str) -> str:
    """Cheap heuristic: Korean if Hangul is a meaningful share of letters."""
    hangul = len(_HANGUL.findall(text))
    latin = len(_LATIN.findall(text))
    if hangul == 0 and latin == 0:
        return "ko"
    return "ko" if hangul / (hangul + latin) >= 0.15 else "en"


def _coerce_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        m = _DATE_IN_NAME.search(value)
        if m:
            try:
                return date(int(m[1]), int(m[2]), int(m[3]))
            except ValueError:
                return None
    return None


def resolve_date(meta: dict, path: Path) -> tuple[date | None, str]:
    """frontmatter date > date in filename > file mtime (low confidence)."""
    if (d := _coerce_date(meta.get("date"))) is not None:
        return d, "high"
    if (d := _coerce_date(path.stem)) is not None:
        return d, "high"
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date(), "low"
    except OSError:
        return None, "low"


def _normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return [str(t).strip() for t in value if str(t).strip()]


def parse_text(raw: bytes, path: Path) -> ParsedDocument:
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    try:
        post = frontmatter.loads(text)
        meta, body = dict(post.metadata), post.content
    except Exception:  # malformed frontmatter: keep the whole text as body
        meta, body = {}, text

    h1 = _H1.search(body)
    title = str(meta.get("title") or (h1[1] if h1 else path.stem)).strip()
    d, confidence = resolve_date(meta, path)
    language = str(meta.get("language") or detect_language(body))
    return ParsedDocument(
        body=body,
        title=title,
        date=d,
        date_confidence=confidence,
        language=language,
        tags=_normalize_tags(meta.get("tags")),
        content_hash=content_hash(raw),
        metadata=meta,
    )


def parse_file(path: Path) -> ParsedDocument:
    return parse_text(path.read_bytes(), path)
