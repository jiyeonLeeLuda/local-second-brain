"""entries and chunks with pgvector

Revision ID: 0001
Revises:
Create Date: 2026-11-12

The embedding dimension is fixed at migration time from EMBED_DIM. Switching to an
embedding model with a different dimension needs a new migration and a full re-embed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.config import get_settings

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dim = get_settings().embed_dim
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="ko"),
        sa.Column("sensitivity", sa.String(16), nullable=False, server_default="private"),
        sa.Column("date", sa.Date),
        sa.Column("date_confidence", sa.String(8), nullable=False, server_default="low"),
        sa.Column("tags", sa.Text, nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("approved", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_type", "file_path"),
        sa.CheckConstraint(
            "source_type IN ('journal','memo','study','en-docs','research')",
            name="ck_entries_source_type",
        ),
    )
    op.create_index("ix_entries_source_type", "entries", ["source_type"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entry_id",
            sa.Integer,
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idx", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("heading_path", sa.Text, nullable=False, server_default=""),
        sa.Column("embedding", Vector(dim), nullable=False),
        sa.Column("embed_model", sa.String(128), nullable=False),
        sa.Column("is_filler", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("excluded", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_chunks_entry_id", "chunks", ["entry_id"])
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("entries")
