"""Command line entry points.

uv run python -m app.cli ingest --source study
uv run python -m app.cli search "B-tree 인덱스는 언제 쓰나"
uv run python -m app.cli ask "JWT와 세션 인증의 차이는?"
uv run python -m app.cli eval ../eval/study_questions.yaml --k 5
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import yaml

from app.config import get_settings
from app.db import make_session
from app.ingest.pipeline import INGESTIBLE_SOURCES, ingest_source
from app.llm.chat import make_chat
from app.llm.embeddings import make_embedder
from app.qa import answer_question
from app.search import search


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    embedder = make_embedder(settings)
    with make_session() as session:
        for source in args.source:
            report = ingest_source(session, settings, source, embedder, reembed=args.reembed)
            print(json.dumps(report.as_dict(), ensure_ascii=False))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    embedder = make_embedder(get_settings())
    with make_session() as session:
        for hit in search(session, embedder, args.query, k=args.k):
            print(f"{hit.score:.3f}  {hit.file_path}  [{hit.heading_path}]")
            print("      " + hit.text[:160].replace("\n", " "))
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    settings = get_settings()
    with make_session() as session:
        result = answer_question(
            session, make_embedder(settings), make_chat(settings), args.question, k=args.k
        )
    print(result.answer, "\n")
    for i, hit in enumerate(result.sources, start=1):
        print(f"[{i}] {hit.file_path} — {hit.heading_path} ({hit.score:.3f})")
    return 0


def evaluate_retrieval(questions: list[dict], run_search, k: int) -> dict:
    """Hit@k and MRR. A hit = a result from expected_file whose heading path
    contains expected_heading (if given)."""
    rows, hits_at_k, rr_sum = [], 0, 0.0
    for q in questions:
        results = run_search(q["question"], k)
        rank = None
        for i, hit in enumerate(results, start=1):
            same_file = hit.file_path.endswith("/" + q["expected_file"])
            heading_ok = q.get("expected_heading", "") in hit.heading_path
            if same_file and heading_ok:
                rank = i
                break
        hits_at_k += rank is not None
        rr_sum += 1.0 / rank if rank else 0.0
        rows.append({"id": q["id"], "rank": rank, "question": q["question"]})
    n = len(questions) or 1
    return {"n": len(questions), "k": k, "hit_rate": hits_at_k / n, "mrr": rr_sum / n, "rows": rows}


def cmd_eval(args: argparse.Namespace) -> int:
    questions = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))
    embedder = make_embedder(get_settings())
    with make_session() as session:
        result = evaluate_retrieval(
            questions, lambda q, k: search(session, embedder, q, k=k), args.k
        )
    for row in result["rows"]:
        mark = f"rank {row['rank']}" if row["rank"] else "MISS"
        print(f"{row['id']}  {mark:>7}  {row['question']}")
    print(
        f"\nmodel={embedder.model_name} n={result['n']} "
        f"hit@{result['k']}={result['hit_rate']:.2f} MRR={result['mrr']:.3f}"
    )
    return 0


_CITATION = re.compile(r"\[(\d+)\]")


def cmd_qa_eval(args: argparse.Namespace) -> int:
    """Answer every question and write a Markdown report for manual review."""
    settings = get_settings()
    questions = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))[: args.limit]
    embedder, chat = make_embedder(settings), make_chat(settings)
    lines = [
        f"# Q&A run: {chat.model_name} / {embedder.model_name}",
        "",
        "| id | 인용 있음 | 정답 파일 인용 | 시간(s) |",
        "|---|---|---|---|",
    ]
    details, cited_any, cited_expected = [], 0, 0
    with make_session() as session:
        for q in questions:
            start = time.perf_counter()
            result = answer_question(session, embedder, chat, q["question"], k=args.k)
            secs = time.perf_counter() - start
            cited = {int(n) for n in _CITATION.findall(result.answer)}
            cited_files = {
                result.sources[n - 1].file_path for n in cited if 0 < n <= len(result.sources)
            }
            has_cite = bool(cited_files)
            has_expected = any(f.endswith("/" + q["expected_file"]) for f in cited_files)
            cited_any += has_cite
            cited_expected += has_expected
            lines.append(
                f"| {q['id']} | {'O' if has_cite else 'X'} | {'O' if has_expected else 'X'} | {secs:.1f} |"
            )
            details += [f"## {q['id']}. {q['question']}", "", result.answer, ""]
            details += [
                f"- [{i}] {h.file_path} — {h.heading_path} ({h.score:.3f})"
                for i, h in enumerate(result.sources, start=1)
            ]
            details.append("")
            print(f"{q['id']} cite={has_cite} expected={has_expected} {secs:.1f}s", flush=True)
    n = len(questions) or 1
    lines += [
        "",
        f"인용 포함 {cited_any}/{len(questions)} ({cited_any / n:.0%}), "
        f"정답 파일 인용 {cited_expected}/{len(questions)} ({cited_expected / n:.0%})",
        "",
        *details,
    ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"saved: {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="index notes (only changed files are re-embedded)")
    p.add_argument("--source", nargs="+", default=["study"], choices=INGESTIBLE_SOURCES)
    p.add_argument("--reembed", action="store_true", help="re-embed even unchanged files")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("search", help="vector search without the LLM")
    p.add_argument("query")
    p.add_argument("--k", type=int, default=5)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ask", help="answer from notes with citations")
    p.add_argument("question")
    p.add_argument("--k", type=int, default=5)
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("eval", help="retrieval hit@k / MRR on a question set")
    p.add_argument("file")
    p.add_argument("--k", type=int, default=5)
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("qa-eval", help="answer a question set and write a Markdown report")
    p.add_argument("file")
    p.add_argument("--out", default="qa_report.md")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--k", type=int, default=5)
    p.set_defaults(func=cmd_qa_eval)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
