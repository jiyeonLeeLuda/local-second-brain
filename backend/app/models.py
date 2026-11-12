"""Phase 1 tables: entries (one per source file) and chunks (retrievable units).

Later phases add abstractions, derived, glossary, resurfacing_log, feedback, jobs,
and a separate `private` schema for journal rows (see docs/plan-v0.3.md §7, §12).
"""

import datetime as dt

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings

SOURCE_TYPES = ("journal", "memo", "study", "en-docs", "research")


class Base(DeclarativeBase):
    pass


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (UniqueConstraint("source_type", "file_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Path relative to NOTES_DIR/<source_type>, never absolute, so the DB is portable.
    file_path: Mapped[str] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512))
    language: Mapped[str] = mapped_column(String(8), default="ko")
    sensitivity: Mapped[str] = mapped_column(String(16), default="private")
    date: Mapped[dt.date | None] = mapped_column(Date)
    date_confidence: Mapped[str] = mapped_column(String(8), default="low")
    tags: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    imported_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="Chunk.idx"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    heading_path: Mapped[str] = mapped_column(Text, default="")
    embedding = mapped_column(Vector(get_settings().embed_dim))
    embed_model: Mapped[str] = mapped_column(String(128))
    is_filler: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)

    entry: Mapped[Entry] = relationship(back_populates="chunks")
