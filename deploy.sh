#!/usr/bin/env bash
# Update and (re)start the stack on the Mac mini.
#   On the Mac mini:            ./deploy.sh
#   From the MacBook over SSH:  DEPLOY_HOST=user@macmini ./deploy.sh
set -euo pipefail

REPO_PATH="${REPO_PATH:-~/local-second-brain}"

if [[ -n "${DEPLOY_HOST:-}" ]]; then
  exec ssh "$DEPLOY_HOST" "cd $REPO_PATH && ./deploy.sh"
fi

cd "$(dirname "$0")"
[[ -f .env ]] || { echo "missing .env (cp .env.example .env and edit it)"; exit 1; }
grep -qE '^BIND_ADDR=0\.0\.0\.0' .env && { echo "refusing BIND_ADDR=0.0.0.0 (plan §12)"; exit 1; }

git pull --ff-only
docker compose up -d --build
docker compose ps
echo "backend health:"
for _ in $(seq 1 30); do
  if docker compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())" 2>/dev/null; then
    exit 0
  fi
  sleep 2
done
echo "backend did not become healthy; see: docker compose logs backend" >&2
exit 1
