"""Incremental import: NOTES_DIR/<source_type>/**/*.md -> entries + embedded chunks.

Only changed files are re-chunked and re-embedded (content hash comparison).
Files removed from disk are removed from the index. Source files are never
modified, moved or deleted (plan §8).
"""

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.ingest.chunking import CHUNKERS
from app.ingest.document import parse_file
from app.llm.embeddings import Embedder
from app.llm.errors import ModelServerError
from app.models import Chunk, Entry

log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt"}

# Defaults until the labeling step (Phase 2) exists. Frontmatter `sensitivity` overrides.
DEFAULT_SENSITIVITY = {"memo": "private", "study": "semi", "en-docs": "public", "research": "semi"}

# Journal rows must live in the `private` schema with separate DB grants (plan §12).
# That arrives in Phase 3, so importing journal is refused until then.
INGESTIBLE_SOURCES = tuple(DEFAULT_SENSITIVITY)


@dataclass
class IngestReport:
    source_type: str
    scanned: int = 0
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0
    chunks_embedded: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def iter_note_files(root: Path) -> list[Path]:
    """Supported files under root, skipping hidden paths and anything that
    resolves outside root (symlink escapes)."""
    if not root.is_dir():
        return []
    real_root = root.resolve()
    files = []
    for path in root.rglob("*"):
        rel_parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if not path.resolve().is_relative_to(real_root):
            log.warning("skipping %s: resolves outside %s", path, real_root)
            continue
        files.append(path)
    return sorted(files)


def _needs_reembed(entry: Entry, embedder: Embedder) -> bool:
    return any(chunk.embed_model != embedder.model_name for chunk in entry.chunks)


def ingest_source(
    session: Session,
    settings: Settings,
    source_type: str,
    embedder: Embedder,
    *,
    reembed: bool = False,
) -> IngestReport:
    if source_type not in INGESTIBLE_SOURCES:
        raise ValueError(
            f"source_type {source_type!r} is not ingestible yet "
            f"(allowed: {', '.join(INGESTIBLE_SOURCES)})"
        )

    report = IngestReport(source_type=source_type)
    root = settings.notes_dir / source_type
    chunker = CHUNKERS[source_type]
    existing = {
        e.file_path: e
        for e in session.scalars(select(Entry).where(Entry.source_type == source_type))
    }
    seen: set[str] = set()

    for path in iter_note_files(root):
        rel = path.relative_to(root).as_posix()
        seen.add(rel)
        report.scanned += 1
        try:
            doc = parse_file(path)
            entry = existing.get(rel)
            if (
                entry is not None
                and entry.content_hash == doc.content_hash
                and not reembed
                and not _needs_reembed(entry, embedder)
            ):
                report.unchanged += 1
                continue

            drafts = chunker(
                doc.body,
                title=doc.title,
                max_chars=settings.chunk_max_chars,
                min_chars=settings.chunk_min_chars,
            )
            vectors = embedder.embed([d.embedding_text() for d in drafts]) if drafts else []

            is_new = entry is None
            if entry is None:
                entry = Entry(file_path=rel, source_type=source_type)
                session.add(entry)

            entry.title = doc.title[:512]
            entry.language = doc.language
            entry.sensitivity = str(
                doc.metadata.get("sensitivity") or DEFAULT_SENSITIVITY[source_type]
            )
            entry.date = doc.date
            entry.date_confidence = doc.date_confidence
            entry.tags = ",".join(doc.tags)
            entry.content_hash = doc.content_hash
            entry.approved = bool(doc.metadata.get("approved", source_type != "research"))
            entry.chunks = [
                Chunk(
                    idx=i,
                    text=draft.text,
                    heading_path=draft.heading_path,
                    embedding=vector,
                    embed_model=embedder.model_name,
                )
                for i, (draft, vector) in enumerate(zip(drafts, vectors, strict=True))
            ]
            session.commit()  # per file, so a long run can resume after a failure
            report.chunks_embedded += len(drafts)
            if is_new:
                report.added += 1
            else:
                report.updated += 1
        except ModelServerError:
            session.rollback()
            raise  # every following file would fail the same way; stop early
        except Exception as exc:
            session.rollback()
            # Never log note content, only the path and error type (plan §12).
            log.error("ingest failed for %s/%s: %s", source_type, rel, type(exc).__name__)
            report.errors.append(f"{rel}: {exc}")

    for rel, entry in existing.items():
        if rel not in seen:
            session.delete(entry)
            report.deleted += 1
    session.commit()
    return report
