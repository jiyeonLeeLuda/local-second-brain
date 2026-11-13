"""Vector search over chunks.

Which sources a mode may read is fixed here in server code, never taken from a
request or an LLM tool argument (plan §12).
"""

from dataclasses import dataclass

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.llm.embeddings import Embedder
from app.models import Chunk, Entry

MODE_SOURCES: dict[str, tuple[str, ...]] = {
    "study_qa": ("study", "en-docs", "research"),
}


@dataclass
class SearchHit:
    chunk_id: int
    text: str
    heading_path: str
    file_path: str
    source_type: str
    score: float  # cosine similarity, 1.0 = identical direction

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "heading_path": self.heading_path,
            "file_path": self.file_path,
            "source_type": self.source_type,
            "score": round(self.score, 4),
        }


def search(
    session: Session, embedder: Embedder, query: str, *, mode: str = "study_qa", k: int = 5
) -> list[SearchHit]:
    sources = MODE_SOURCES[mode]
    query_vec = embedder.embed_query(query)
    distance = Chunk.embedding.cosine_distance(query_vec)

    # Filtered HNSW scans can return fewer than k rows; let pgvector keep scanning.
    session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
    stmt = (
        select(Chunk, Entry, distance.label("distance"))
        .join(Entry, Chunk.entry_id == Entry.id)
        .where(
            Entry.source_type.in_(sources),
            Chunk.excluded.is_(False),
            Chunk.embed_model == embedder.model_name,
            or_(Entry.source_type != "research", Entry.approved.is_(True)),
        )
        .order_by(distance)
        .limit(k)
    )
    hits = [
        SearchHit(
            chunk_id=chunk.id,
            text=chunk.text,
            heading_path=chunk.heading_path,
            file_path=f"{entry.source_type}/{entry.file_path}",
            source_type=entry.source_type,
            score=1.0 - float(dist),
        )
        for chunk, entry, dist in session.execute(stmt)
    ]
    session.rollback()  # end the read transaction that holds SET LOCAL
    return hits
