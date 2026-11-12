---
date: 2026-08-04
source_type: study
tags: [docker, container, devops]
---

# Docker 기초

맥북에서 개발하고 맥미니에서 운영하려면 두 환경을 똑같이 맞춰야 한다. "내 컴퓨터에서는 되는데"를 피하려고 Docker를 제대로 배웠다. 맥에서는 OrbStack으로 실행한다.

## 이미지와 컨테이너

- 이미지: 애플리케이션과 실행 환경을 묶은 읽기 전용 템플릿. 클래스에 비유할 수 있다.
- 컨테이너: 이미지를 실행한 인스턴스. 객체에 비유할 수 있다.

컨테이너는 가상 머신이 아니다. 호스트 커널을 공유하면서 프로세스, 파일 시스템, 네트워크를 격리한 것이다. 그래서 가볍고 빨리 뜬다. 맥에서는 리눅스 커널이 없으므로 내부적으로 경량 리눅스 VM 위에서 돌아간다.

## Dockerfile 작성

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 레이어 캐시와 명령 순서

각 명령은 레이어가 되고, 변경이 없으면 캐시를 재사용한다. 한 레이어가 바뀌면 그 아래 레이어는 전부 다시 빌드된다. 그래서 자주 바뀌지 않는 의존성 설치를 먼저, 자주 바뀌는 소스 코드 복사를 나중에 둔다.

헷갈렸던 점: 처음에 `COPY . .`를 맨 위에 뒀더니 코드 한 줄만 고쳐도 의존성을 매번 새로 설치했다. 프론트엔드에서 `package.json`만 먼저 복사하고 `npm ci` 하던 패턴과 같은 이유였다.

### .dockerignore

`.git`, `node_modules`, `.venv`, `.env`는 빌드 컨텍스트에서 제외한다. 특히 `.env`가 이미지에 들어가면 비밀 값이 이미지에 남는다.

## 자주 쓰는 명령

```bash
docker build -t lsb-api .
docker run -p 8000:8000 --env-file .env lsb-api
docker ps
docker logs -f <container>
docker exec -it <container> sh
```

`-p 8000:8000`은 "호스트 포트:컨테이너 포트"다. 컨테이너 안 서버가 `127.0.0.1`에만 바인딩되면 밖에서 접근이 안 된다. 그래서 `--host 0.0.0.0`이 필요하다. 이것도 처음에 한참 헤맸다.

## 데이터는 컨테이너 밖에

컨테이너를 지우면 안의 파일도 사라진다. 지속되어야 하는 데이터는 볼륨에 둔다.

- named volume: Docker가 관리하는 저장소. DB 데이터에 적합.
- bind mount: 호스트 폴더를 그대로 연결. 노트 폴더(`~/Notes`)를 읽기 전용으로 연결할 때 적합.

```bash
docker run -v pgdata:/var/lib/postgresql/data postgres:16
docker run -v ~/Notes:/notes:ro lsb-api
```

`:ro`로 읽기 전용 마운트를 하면 앱이 원본 노트를 실수로 수정할 수 없다. "원본 수정 금지"라는 프로젝트 원칙을 인프라 수준에서 보장하는 방법이다.

## 이미지 크기 줄이기

- `slim`이나 `alpine` 베이스 이미지 사용(alpine은 Python 휠 호환 문제가 있을 수 있음)
- 멀티 스테이지 빌드로 빌드 도구는 최종 이미지에서 제외
- 불필요한 캐시 파일 삭제

## 다음 단계

컨테이너 여러 개(API, DB, 워커, 프론트)를 한 번에 띄우는 건 docker compose 노트에 정리한다.
