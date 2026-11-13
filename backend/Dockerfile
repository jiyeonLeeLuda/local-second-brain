FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# `exec` makes uvicorn PID 1 so `docker stop` (SIGTERM) shuts it down cleanly instead of
# waiting 10s for SIGKILL (see demo-data/study/linux-process-permissions.md).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.api:app --host 0.0.0.0 --port 8000"]
