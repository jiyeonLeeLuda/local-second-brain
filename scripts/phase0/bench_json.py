#!/usr/bin/env python3
"""Phase 0: structured-output (JSON) success rate of a local model.

Runs N extraction requests with thinking on and off and reports parse/schema
success and latency. Standard library only, so it runs on the Mac mini as is.

  python3 scripts/phase0/bench_json.py --base-url http://localhost:13305/api/v1 \
      --model Qwen3-8B-GGUF --n 50
"""

import argparse
import json
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

SAMPLES = [
    "아침에 비가 와서 카페 창가에 앉아 오래 그림을 그렸다. 색이 번지는 걸 보면서 요즘 코드도 이렇게 경계가 흐려지는 느낌이라고 생각했다.",
    "FastAPI에서 Depends로 세션을 주입하니 테스트에서 오버라이드하기 쉬웠다. 프론트의 Context와 비슷하다는 걸 깨달았다.",
    "면접에서 인덱스를 왜 쓰냐는 질문에 제대로 답을 못 했다. B-tree와 쓰기 비용을 같이 설명했어야 했다.",
    "엄마와 통화하고 나서 마음이 조금 가벼워졌다. 이직 준비가 길어져도 괜찮다는 말을 들었다.",
    "pgvector의 HNSW 인덱스는 필터가 있으면 결과가 적게 나올 수 있다고 한다. iterative scan 옵션을 찾아봤다.",
    "전시회에서 본 모네의 수련 연작이 계속 떠오른다. 같은 대상을 시간마다 다르게 그린 것이 반복 실험 같았다.",
    "Docker 볼륨을 읽기 전용으로 마운트하면 앱이 원본을 실수로 지울 수 없다. 권한으로 강제하는 게 마음이 편하다.",
    "오늘은 아무것도 하기 싫었다. 그래도 산책은 했고 하늘 색이 좋았다.",
    "RAG 평가에서 hit rate와 MRR을 처음 계산해 봤다. 숫자가 생기니 개선 방향이 보인다.",
    "스터디에서 JWT와 세션의 차이를 설명하다가 로그아웃 처리에서 막혔다. 토큰 폐기는 결국 상태가 필요하다.",
]

SCHEMA_HINT = (
    '{"themes": [문자열 1~3개], "emotions": [문자열 0~3개], '
    '"entities": [문자열 0~5개], "summary": "한 문장 요약"}'
)
PROMPT = (
    "다음 글에서 정보를 추출해 JSON 하나만 출력해. 설명이나 코드펜스 없이 JSON만.\n"
    f"스키마: {SCHEMA_HINT}\n\n글:\n{{text}}"
)
THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def call(base_url: str, model: str, text: str, thinking: bool, json_mode: bool, timeout: float):
    content = PROMPT.replace("{text}", text)  # not .format(): the schema has braces
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    if "choices" not in data:  # e.g. {"error": ...} while the server swaps models
        raise RuntimeError(json.dumps(data, ensure_ascii=False)[:300])
    return data["choices"][0]["message"]["content"] or "", time.perf_counter() - start


def validate(raw: str) -> tuple[bool, str]:
    text = THINK.sub("", raw)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced[1]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return False, "parse"
    if not isinstance(obj, dict):
        return False, "not_object"
    for key in ("themes", "emotions", "entities"):
        if not isinstance(obj.get(key), list) or not all(isinstance(x, str) for x in obj[key]):
            return False, f"bad_{key}"
    if not isinstance(obj.get("summary"), str) or not obj["summary"].strip():
        return False, "bad_summary"
    return True, "fenced_ok" if fenced else "ok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:13305/api/v1")
    ap.add_argument("--model", default="Qwen3-8B-GGUF")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--json-mode", action="store_true", help="send response_format=json_object")
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument("--thinking", choices=["off", "on", "both"], default="both")
    ap.add_argument("--out", default=str(Path(__file__).parent / "results"))
    args = ap.parse_args()

    summary = {}
    modes = {"off": (False,), "on": (True,), "both": (False, True)}[args.thinking]
    for thinking in modes:
        label = "thinking_on" if thinking else "thinking_off"
        latencies, outcomes, errors = [], {}, []
        for i in range(args.n):
            text = SAMPLES[i % len(SAMPLES)]
            try:
                raw, secs = call(
                    args.base_url, args.model, text, thinking, args.json_mode, args.timeout
                )
                ok, reason = validate(raw)
                latencies.append(secs)
            except (urllib.error.URLError, TimeoutError, KeyError, RuntimeError) as exc:
                ok, reason = False, f"request:{type(exc).__name__}"
                errors.append(str(exc)[:300])
            outcomes[reason] = outcomes.get(reason, 0) + 1
            print(f"{label} {i + 1:>3}/{args.n} {'OK ' if ok else 'BAD'} {reason}", flush=True)
        success = sum(v for k, v in outcomes.items() if k in ("ok", "fenced_ok"))
        summary[label] = {
            "success_rate": success / args.n,
            "outcomes": outcomes,
            "latency_median_s": round(statistics.median(latencies), 2) if latencies else None,
            "latency_max_s": round(max(latencies), 2) if latencies else None,
            "error_samples": errors[:3],
        }

    result = {"model": args.model, "n": args.n, "json_mode": args.json_mode, **summary}
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"bench_json_{args.model}_{time.strftime('%Y%m%d-%H%M')}.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"saved: {out_file}")


if __name__ == "__main__":
    main()
