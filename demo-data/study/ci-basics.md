---
date: 2026-08-24
source_type: study
tags: [ci, github-actions, devops, testing]
---

# CI 기초: GitHub Actions

pytest로 테스트를 만들어도 실행을 잊으면 소용이 없다. 커밋할 때마다 자동으로 검사가 돌게 하는 CI를 공부했다. 회사에서는 이미 만들어진 파이프라인의 초록 체크만 봤는데, 직접 만드는 건 처음이다.

## CI와 CD

- CI(Continuous Integration): 코드를 자주 합치고, 합칠 때마다 빌드와 테스트를 자동으로 돌려 문제를 빨리 찾는다.
- CD(Continuous Delivery/Deployment): 검사를 통과한 코드를 배포 가능한 상태로 만들거나 실제로 배포까지 한다.

개인 프로젝트에서는 CI만 먼저 하고, 배포는 `deploy.sh`로 손으로 한다.

## 워크플로 파일 구조

`.github/workflows/ci.yml`에 정의한다.

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run pytest -q
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/postgres
```

### 용어 정리

- workflow: 파일 하나. 어떤 이벤트(`on`)에 반응할지 정한다.
- job: 독립된 실행 단위. 기본적으로 병렬로 돈다. `needs`로 순서를 정할 수 있다.
- step: job 안의 순서대로 실행되는 명령.
- action: 재사용 가능한 step 묶음(`uses:`).

헷갈렸던 점: job마다 새 가상 머신에서 시작한다. 앞 job에서 설치한 패키지나 만든 파일은 다음 job에 없다. 넘기려면 artifact나 캐시를 써야 한다.

## 서비스 컨테이너

`services`에 Postgres를 정의하면 job이 실행되는 동안 DB가 함께 뜬다. 통합 테스트를 CI에서도 실제 DB로 돌릴 수 있다. 다만 컨테이너가 준비되기 전에 테스트가 시작될 수 있어서, docker compose 노트에서처럼 health check 옵션을 주는 게 좋다.

## 무엇을 검사할까

1. 린트와 포맷(ruff): 빠르니까 가장 먼저.
2. 타입 검사(mypy 또는 pyright): 선택.
3. 단위 테스트와 통합 테스트.
4. 프론트엔드 빌드와 린트: Next.js 쪽은 별도 job으로 병렬 실행.

빠른 검사를 앞에 두면 실패를 빨리 알 수 있다.

## 비밀 값 다루기

CI에서 API 키가 필요하면 저장소 설정의 Secrets에 넣고 `${{ secrets.NAME }}`으로 참조한다. 로그에는 마스킹된다. 하지만 이 프로젝트의 CI에서는 LLM 서버를 부르지 않는다. 테스트에서 LLM 호출은 가짜 객체로 대체하기 때문이다(pytest 노트 참고). 외부 서비스에 의존하지 않는 CI가 더 안정적이다.

## 캐시로 빠르게

의존성 설치가 매번 반복되면 느리다. `setup-uv`의 캐시 옵션이나 `actions/cache`로 패키지 캐시를 재사용한다. 캐시 키에 lock 파일 해시를 넣으면 의존성이 바뀔 때만 새로 설치한다. Docker 레이어 캐시와 같은 발상이다.

## 느낀 점

CI는 "미래의 나를 위한 안전망"이다. 혼자 하는 프로젝트라 리뷰어가 없으니 CI가 리뷰어 역할을 일부 대신한다. 포트폴리오로 보여줄 때도 초록 체크 배지가 있으면 기본기를 갖춘 프로젝트로 보인다.
