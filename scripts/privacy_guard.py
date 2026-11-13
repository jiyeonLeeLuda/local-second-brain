#!/usr/bin/env python3
"""Block personal records (journal / morning pages) from entering this public repo.

  python3 scripts/privacy_guard.py --staged   # pre-commit hook: files being committed
  python3 scripts/privacy_guard.py --all      # CI: every tracked file

Rules
1. No .env files (only .env.example) and no Obsidian vault config (.obsidian/).
2. No file under a journal-like folder (journal, morning_page, 모닝페이지, 일기 ...),
   unless it is under demo-data/ and its frontmatter says `synthetic: true`.
3. No Markdown/text with frontmatter `source_type: journal` unless `synthetic: true`.
4. Extra private patterns from `.private-patterns` (git-ignored, one regex per line),
   checked against paths and file contents. Put your real folder names and paths there
   so they never have to appear in the public repo.
Standard library only.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATTERNS_FILE = REPO / ".private-patterns"
JOURNAL_SEGMENT = re.compile(
    r"^(\d+[_-])?(journal|journals|diary|morning[_ -]?pages?|모닝\s?페이지|일기)$", re.IGNORECASE
)
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
SELF = {"scripts/privacy_guard.py"}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True).stdout


def list_files(staged: bool) -> list[str]:
    if staged:
        out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    else:
        out = git("ls-files", "-z")
    return [p for p in out.decode().split("\0") if p]


def read(path: str, staged: bool) -> bytes:
    if staged:
        return git("show", f":{path}")
    return (REPO / path).read_bytes()


def frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER.match(text)
    if not m:
        return {}
    fields = {}
    for line in m[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip().strip("\"'").lower()
    return fields


def load_private_patterns() -> list[re.Pattern]:
    if not PATTERNS_FILE.exists():
        return []
    patterns = []
    for line in PATTERNS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line, re.IGNORECASE))
    return patterns


def check(path: str, data: bytes, private: list[re.Pattern]) -> list[str]:
    problems = []
    p = Path(path)
    if p.name.startswith(".env") and p.name != ".env.example" and not p.name.endswith(".example"):
        problems.append("secret env file")
    if ".obsidian" in p.parts:
        problems.append("Obsidian vault config")

    text = data.decode("utf-8", errors="ignore") if p.suffix.lower() in TEXT_SUFFIXES else ""
    meta = frontmatter(text) if text else {}
    synthetic = meta.get("synthetic") == "true"

    if any(JOURNAL_SEGMENT.match(part) for part in p.parts[:-1]):
        if not (p.parts[0] == "demo-data" and synthetic):
            problems.append("file in a journal folder (demo data needs `synthetic: true`)")
    if meta.get("source_type") == "journal" and not synthetic:
        problems.append("frontmatter source_type: journal without `synthetic: true`")

    if path not in SELF:
        content = data.decode("utf-8", errors="ignore")
        for pattern in private:
            if pattern.search(path):
                problems.append(f"path matches private pattern /{pattern.pattern}/")
            elif pattern.search(content):
                problems.append(f"content matches private pattern /{pattern.pattern}/")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--all", action="store_true")
    args = ap.parse_args()

    private = load_private_patterns()
    failures = {}
    for path in list_files(args.staged):
        try:
            data = read(path, args.staged)
        except (OSError, subprocess.CalledProcessError):
            continue
        if problems := check(path, data, private):
            failures[path] = problems

    if not failures:
        print(f"privacy guard: ok ({len(private)} private patterns)")
        return 0
    print("privacy guard: BLOCKED. These files look like personal records:", file=sys.stderr)
    for path, problems in failures.items():
        for problem in problems:
            print(f"  {path}: {problem}", file=sys.stderr)
    print("Remove them from the commit (git restore --staged <file>).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
