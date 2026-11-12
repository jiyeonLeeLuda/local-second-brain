"""Embedding providers behind one small interface.

`OpenAIEmbedder` speaks the OpenAI-compatible /embeddings API, so Lemonade,
llama-server (--embedding), Ollama and LM Studio are interchangeable via env vars.
`HashEmbedder` is offline and deterministic: lexical, not semantic. It exists for
tests and for running the demo without a model server.
"""

import hashlib
import math
import re
from typing import Protocol

import httpx

from app.config import Settings
from app.llm.errors import ModelServerError

_WORD = re.compile(r"[\w가-힣]+", re.UNICODE)
_HANGUL_RUN = re.compile(r"[가-힣]{2,}")


class Embedder(Protocol):
    model_name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    def __init__(self, dim: int):
        self.dim = dim
        self.model_name = f"hash-{dim}"

    def _features(self, text: str) -> list[str]:
        lowered = text.lower()
        words = _WORD.findall(lowered)
        feats = [f"w:{w}" for w in words]
        # Korean attaches particles to nouns ("인덱스는", "인덱스를"), so add bigrams.
        for run in _HANGUL_RUN.findall(lowered):
            feats.extend(f"b:{run[i : i + 2]}" for i in range(len(run) - 1))
        return feats

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for feat in self._features(text):
            digest = hashlib.blake2b(feat.encode(), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            vec[0] = 1.0  # pgvector cosine distance is undefined for zero vectors
            return vec
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class OpenAIEmbedder:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.model_name = settings.embed_model
        self.dim = settings.embed_dim
        self.batch_size = settings.embed_batch_size
        self._client = client or httpx.Client(
            base_url=settings.embed_base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {settings.embed_api_key}"},
            timeout=settings.llm_timeout_s,
        )

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        try:
            resp = self._client.post("embeddings", json={"model": self.model_name, "input": batch})
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ModelServerError(f"embedding request failed: {exc}") from exc
        vectors = [d["embedding"] for d in data]
        if len(vectors) != len(batch):
            raise ModelServerError(f"expected {len(batch)} embeddings, got {len(vectors)}")
        if vectors and len(vectors[0]) != self.dim:
            raise ModelServerError(
                f"model {self.model_name} returned dim {len(vectors[0])}, "
                f"but EMBED_DIM={self.dim}. Update EMBED_DIM and re-run migrations."
            )
        return vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            out.extend(self._embed_batch(texts[i : i + self.batch_size]))
        return out


def make_embedder(settings: Settings) -> Embedder:
    if settings.embed_provider == "hash":
        return HashEmbedder(settings.embed_dim)
    return OpenAIEmbedder(settings)
