# Serendipity Journal (가칭)

흩어진 내 기록(일기, 메모, 스터디 노트) 사이에서 영감과 성찰을 돌려주는 개인용 로컬 시스템입니다.
모든 데이터와 모델은 집에 있는 Mac mini 안에서만 돕니다. 전체 계획은 [docs/plan-v0.3.md](docs/plan-v0.3.md)에 있습니다.

현재 단계는 **Phase 1: 공통 엔진 + 스터디 Q&A**입니다.

## 구조

```
backend/     FastAPI. 가져오기 → 청킹 → 임베딩 → Postgres+pgvector → 검색 → LLM
frontend/    Next.js. 스터디 Q&A 화면
demo-data/   공개 가능한 데모 노트 (실제 개인 기록은 저장소 밖 ~/Notes)
eval/        검색 평가 질문
scripts/     Phase 0 점검 스크립트
docs/        계획서, 설계 결정 기록(ADR), 측정 결과
```

## 맥북에서 개발

필요한 것: Homebrew Postgres 17 + pgvector, [uv](https://docs.astral.sh/uv/), Node 22.18 이상.

```bash
brew install postgresql@17 pgvector && brew services start postgresql@17
createdb lsb_dev && createdb lsb_test
cp .env.example .env            # LLM_BASE_URL 등 기기별 값 수정

cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.cli ingest --source study
uv run python -m app.cli ask "JWT와 세션 인증의 차이는?"
uv run uvicorn app.api:app --reload     # http://localhost:8000/docs

cd ../frontend
npm install && npm run dev              # http://localhost:3000
```

모델 서버 없이 돌리려면 `.env`에 `EMBED_PROVIDER=hash`를 둡니다. 검색은 되고, 답변 생성만 503을 돌려줍니다.

테스트:

```bash
cd backend && uv run pytest        # lsb_test DB 사용
cd frontend && npm test && npm run lint && npm run typecheck
```

## Mac mini에서 실행

```bash
git clone https://github.com/jiyeonLeeLuda/local-second-brain.git ~/local-second-brain
cd ~/local-second-brain
cp .env.example .env   # POSTGRES_PASSWORD, HOST_NOTES_DIR=/Users/<you>/Notes, EMBED_* 설정
./scripts/phase0/check_model_server.sh localhost   # 모델 서버 주소, 임베딩 차원 확인
./deploy.sh            # git pull + docker compose up -d --build
```

- 노트 폴더는 컨테이너에 읽기 전용으로 마운트됩니다.
- 앱은 `BIND_ADDR`(기본 127.0.0.1)에만 열립니다. 원격 접속은 Tailscale IP를 지정합니다.
- 컨테이너는 호스트의 Lemonade를 `host.docker.internal:13305`로 호출합니다.

## 평가

```bash
cd backend
uv run python -m app.cli eval ../eval/study_questions.yaml --k 5      # 검색 hit@k, MRR
uv run python -m app.cli qa-eval ../eval/study_questions.yaml --out ../docs/results/qa.md
```

측정 결과는 [docs/results/](docs/results/)에 기록합니다.

## 원칙

- 원본은 언제나 내가 쓴 MD 파일입니다. 앱은 읽기만 합니다.
- 경계는 프롬프트가 아니라 권한과 코드로 강제합니다. 검색 대상 소스는 서버 코드에 고정되어 있습니다.
- 쓰는 동안 AI는 개입하지 않고, 성찰을 재촉하지 않습니다.
