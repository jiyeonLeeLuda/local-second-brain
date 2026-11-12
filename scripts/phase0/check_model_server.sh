#!/usr/bin/env bash
# Phase 0: probe an OpenAI-compatible model server (Lemonade, llama-server, Ollama ...).
# Usage: ./check_model_server.sh [host] [chat-model] [embed-model]
#   ./check_model_server.sh localhost Qwen3-8B-GGUF bge-m3
#   ./check_model_server.sh 100.x.y.z            # Mac mini over Tailscale
# Tries the common port/path combinations and reports which ones answer.
set -uo pipefail
HOST="${1:-localhost}"
CHAT_MODEL="${2:-Qwen3-8B-GGUF}"
EMBED_MODEL="${3:-bge-m3}"

found=""
for port in 13305 8000 11434 8080 1234; do
  for prefix in /api/v1 /v1; do
    url="http://$HOST:$port$prefix"
    code=$(curl -s -o /tmp/lsb_models.json -w '%{http_code}' --max-time 3 "$url/models")
    if [[ "$code" == "200" ]]; then
      echo "OK  $url/models"
      python3 -c "import json;d=json.load(open('/tmp/lsb_models.json'));print('    models:', ', '.join(m['id'] for m in d.get('data',[]))[:600])"
      found="$url"; break 2
    fi
  done
done
[[ -z "$found" ]] && { echo "no OpenAI-compatible server found on $HOST"; exit 1; }

if ! python3 -c "import json,sys;d=json.load(open('/tmp/lsb_models.json'));sys.exit(0 if '$CHAT_MODEL' in [m['id'] for m in d['data']] else 1)"; then
  # Prefer the model already in memory so the probe does not swap models on a shared server.
  loaded=$(curl -s --max-time 3 "$found/health" | python3 -c "import json,sys;print(json.load(sys.stdin).get('model_loaded') or '')" 2>/dev/null)
  echo "WARN: $CHAT_MODEL is not downloaded on this server; using ${loaded:-the first listed model}"
  CHAT_MODEL=${loaded:-$(python3 -c "import json;print(json.load(open('/tmp/lsb_models.json'))['data'][0]['id'])")}
fi

echo; echo "== chat ($CHAT_MODEL)"
curl -s --max-time 180 -o /tmp/lsb_chat.json -w 'HTTP %{http_code}, %{time_total}s\n' "$found/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$CHAT_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"한 문장으로 자기소개 해줘\"}],\"chat_template_kwargs\":{\"enable_thinking\":false}}"
python3 -c "import json;d=json.load(open('/tmp/lsb_chat.json'));print('   ', d['choices'][0]['message']['content'][:300])" 2>/dev/null || cat /tmp/lsb_chat.json

echo; echo "== embeddings ($EMBED_MODEL)"
curl -s --max-time 60 -o /tmp/lsb_emb.json -w 'HTTP %{http_code}, %{time_total}s\n' "$found/embeddings" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$EMBED_MODEL\",\"input\":[\"B-tree 인덱스는 범위 검색에 강하다\",\"B-tree indexes are good at range queries\"]}"
python3 - <<'PY' 2>/dev/null || { echo "    embeddings not available:"; head -c 400 /tmp/lsb_emb.json; echo; }
import json, math
d = json.load(open('/tmp/lsb_emb.json'))
a, b = (x['embedding'] for x in sorted(d['data'], key=lambda x: x['index']))
cos = sum(x*y for x, y in zip(a, b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)))
print(f"    dim={len(a)}  ko/en cosine={cos:.3f}   -> set EMBED_DIM={len(a)} in .env")
PY
echo; echo "Base URL to put in .env: $found"
