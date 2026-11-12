"""Study Q&A: retrieve chunks, then ask the LLM to answer only from them with [n] citations."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm.chat import ChatModel
from app.llm.embeddings import Embedder
from app.search import SearchHit, search

SYSTEM_PROMPT = """너는 사용자의 스터디 노트를 근거로 질문에 답하는 도우미다.
규칙:
1. 아래 [출처] 목록에 있는 내용만 근거로 답한다. 출처에 없는 사실은 지어내지 않는다.
2. 근거로 쓴 문장 끝에 [1], [2]처럼 출처 번호를 붙인다.
3. 출처로 답할 수 없으면 "노트에서 근거를 찾지 못했습니다."라고 말하고, 관련된 출처가 있으면 무엇이 부족한지 짧게 덧붙인다.
4. 한국어로 간결하게 답한다. 영어 출처를 인용할 때도 설명은 한국어로 한다."""

NO_SOURCES_ANSWER = (
    "노트에서 근거를 찾지 못했습니다. 인덱싱된 노트가 없거나 질문과 관련된 문단이 없습니다."
)


@dataclass
class Answer:
    answer: str
    sources: list[SearchHit]

    def as_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": [{"n": i, **hit.as_dict()} for i, hit in enumerate(self.sources, start=1)],
        }


def build_messages(question: str, hits: list[SearchHit]) -> list[dict]:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(f"[{i}] ({hit.file_path} — {hit.heading_path})\n{hit.text}")
    user = "[출처]\n" + "\n\n".join(blocks) + f"\n\n[질문]\n{question}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def answer_question(
    session: Session, embedder: Embedder, chat: ChatModel, question: str, *, k: int = 5
) -> Answer:
    hits = search(session, embedder, question, mode="study_qa", k=k)
    if not hits:
        return Answer(answer=NO_SOURCES_ANSWER, sources=[])
    return Answer(answer=chat.complete(build_messages(question, hits)), sources=hits)
