---
date: 2026-08-08
source_type: study
tags: [docker, compose, devops]
---

# docker compose로 여러 서비스 묶기

Docker 기초 노트에서 컨테이너 하나를 띄우는 법을 익혔다. 실제 프로젝트는 API 서버, Postgres, 워커, 프론트엔드가 함께 돌아야 해서 `docker run`을 여러 번 치는 건 현실적이지 않다. compose 파일 하나로 정의하고 한 명령으로 올리는 방법을 정리한다.

## 기본 구조

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s

  api:
    build: ./backend
    env_file: .env
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ${NOTES_DIR}:/notes:ro

volumes:
  pgdata:
```

```bash
docker compose up -d --build
docker compose logs -f api
docker compose down
```

## 서비스 간 네트워크

compose는 기본 네트워크를 만들고, 서비스 이름을 호스트 이름으로 쓸 수 있게 해 준다. API 컨테이너에서 DB 주소는 `localhost`가 아니라 `db`다.

```
DATABASE_URL=postgresql://postgres:pw@db:5432/lsb
```

헷갈렸던 점: 컨테이너 안에서 `localhost`는 그 컨테이너 자신이다. 호스트 맥에서 돌고 있는 LLM 서버에 접근하려면 `host.docker.internal`을 써야 한다. 맥미니의 Lemonade 서버를 API 컨테이너에서 부를 때 이 주소가 필요할 것이다.

## depends_on과 healthcheck

`depends_on`만 쓰면 "DB 컨테이너가 시작된 뒤"에 API를 시작할 뿐, DB가 접속을 받을 준비가 됐는지는 보장하지 않는다. 그래서 첫 실행 때 API가 DB 연결 실패로 죽곤 한다. `healthcheck`와 `condition: service_healthy`를 같이 써야 한다. 그래도 앱 쪽에 연결 재시도 로직을 두는 게 더 튼튼하다.

## 포트 노출과 보안

`ports: "8000:8000"`이라고만 쓰면 모든 네트워크 인터페이스에 열린다. 운영 서버에서는 `127.0.0.1:8000:8000`처럼 로컬에만 묶고, 원격 접근은 Tailscale로만 하기로 했다. DB 포트는 아예 노출하지 않는다. 서비스끼리는 내부 네트워크로 통신하니 외부 포트가 필요 없다.

## 환경별 설정 분리

### override 파일

`compose.yaml`에 공통 설정을 두고, `compose.override.yaml`에 개발용 설정(소스 코드 bind mount, `--reload`)을 둔다. compose는 override 파일을 자동으로 합친다. 운영에서는 `-f compose.yaml -f compose.prod.yaml`처럼 명시적으로 고른다.

### .env 파일

`${DB_PASSWORD}` 같은 변수는 같은 폴더의 `.env`에서 읽는다. `.env`는 Git에 올리지 않고 `.env.example`만 올린다. 맥북은 `NOTES_DIR=./demo-data`, 맥미니는 `NOTES_DIR=~/Notes`처럼 기기별로 다르게 둔다.

## 배포 흐름

계획한 배포는 단순하다.

```bash
# deploy.sh (맥미니에서 실행)
git pull && docker compose up -d --build && docker compose exec api alembic upgrade head
```

마이그레이션 적용까지 한 줄로 묶었다. 나중에 CI 노트에 정리한 GitHub Actions로 자동화할 수도 있지만, 처음에는 손으로 실행하는 편이 무슨 일이 일어나는지 이해하기 좋다.
