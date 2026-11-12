"""Split note bodies into retrievable chunks.

- Heading chunking (study, en-docs): one chunk per section, with the heading path
  ("Title > Section > Subsection") kept as metadata. Long sections are packed by
  paragraph up to `max_chars`; fenced code blocks are never split.
- Length chunking (memo): paragraph packing without heading awareness.
"""

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SENTENCE_END = re.compile(r"(?<=[.!?。])\s+|(?<=다\.)\s+|\n")


@dataclass(frozen=True)
class ChunkDraft:
    text: str
    heading_path: str

    def embedding_text(self) -> str:
        """Text sent to the embedder: heading context helps short sections."""
        return f"{self.heading_path}\n\n{self.text}" if self.heading_path else self.text


def split_blocks(text: str) -> list[str]:
    """Split on blank lines, keeping fenced code blocks intact as one block."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
            current.append(line)
            continue
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if b]


def _hard_split(block: str, max_chars: int) -> list[str]:
    """Split an oversize non-code block by sentence, then by characters."""
    if block.lstrip().startswith(("```", "~~~")):
        return [block]  # never cut code; an oversize code chunk is acceptable
    pieces: list[str] = []
    current = ""
    for sentence in (s for s in _SENTENCE_END.split(block) if s and s.strip()):
        candidate = f"{current} {sentence}".strip() if current else sentence.strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
        while len(sentence) > max_chars:
            pieces.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        current = sentence.strip()
    if current:
        pieces.append(current)
    return pieces


def pack_blocks(blocks: list[str], max_chars: int) -> list[str]:
    """Greedily pack blocks into chunks of at most max_chars (code blocks may exceed)."""
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for block in blocks:
        parts = _hard_split(block, max_chars) if len(block) > max_chars else [block]
        for part in parts:
            added = len(part) + (2 if current else 0)
            if current and size + added > max_chars:
                chunks.append("\n\n".join(current))
                current, size = [], 0
                added = len(part)
            current.append(part)
            size += added
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _sections(body: str, title: str) -> list[tuple[str, str]]:
    """Return (heading_path, section_text) pairs in document order."""
    stack: list[tuple[int, str]] = []
    sections: list[tuple[str, str]] = []
    lines: list[str] = []
    in_fence = False

    def path() -> str:
        names = [name for _, name in stack]
        if title and (not names or names[0] != title):
            names.insert(0, title)
        return " > ".join(names)

    def flush() -> None:
        text = "\n".join(lines).strip()
        if text:
            sections.append((path(), text))
        lines.clear()

    for line in body.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            flush()
            level, name = len(m[1]), m[2].strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, name))
        else:
            lines.append(line)
    flush()
    return sections


def chunk_by_headings(
    body: str, title: str = "", max_chars: int = 1200, min_chars: int = 40
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for heading_path, text in _sections(body, title):
        for piece in pack_blocks(split_blocks(text), max_chars):
            drafts.append(ChunkDraft(text=piece, heading_path=heading_path))
    return _merge_tiny(drafts, min_chars)


def chunk_by_length(
    body: str, title: str = "", max_chars: int = 1200, min_chars: int = 40
) -> list[ChunkDraft]:
    pieces = pack_blocks(split_blocks(body), max_chars)
    return _merge_tiny([ChunkDraft(text=p, heading_path=title) for p in pieces], min_chars)


def _merge_tiny(drafts: list[ChunkDraft], min_chars: int) -> list[ChunkDraft]:
    """Fold chunks shorter than min_chars into the next chunk of the same section."""
    merged: list[ChunkDraft] = []
    carry: ChunkDraft | None = None
    for draft in drafts:
        if carry is not None:
            if carry.heading_path == draft.heading_path:
                draft = ChunkDraft(f"{carry.text}\n\n{draft.text}", draft.heading_path)
            else:
                merged.append(carry)
            carry = None
        if len(draft.text) < min_chars:
            carry = draft
        else:
            merged.append(draft)
    if carry is not None:
        if merged and merged[-1].heading_path == carry.heading_path:
            last = merged.pop()
            merged.append(ChunkDraft(f"{last.text}\n\n{carry.text}", last.heading_path))
        else:
            merged.append(carry)
    return merged


CHUNKERS = {
    "study": chunk_by_headings,
    "en-docs": chunk_by_headings,
    "research": chunk_by_headings,
    "memo": chunk_by_length,
}
