# Q&A run: Qwen3.5-9B-GGUF / hash-1024

| id | 인용 있음 | 정답 파일 인용 | 시간(s) |
|---|---|---|---|
| q01 | X | X | 7.2 |
| q02 | O | O | 4.8 |
| q03 | O | O | 10.5 |
| q04 | O | O | 4.0 |
| q05 | O | O | 6.5 |
| q06 | O | O | 12.5 |
| q07 | O | O | 10.6 |
| q08 | X | X | 7.4 |
| q09 | X | X | 7.3 |
| q10 | X | X | 5.9 |

인용 포함 6/10 (60%), 정답 파일 인용 6/10 (60%)

## q01. 태그 배열 컬럼에 특정 태그가 들어 있는 노트를 빨리 찾으려면 어떤 종류의 인덱스를 써야 해?

태그 배열 컬럼에서 특정 태그가 들어 있는 노트를 빠르게 찾으려면 **GIN (Generalized Inverted Index)** 인덱스를 사용해야 합니다.

배열 컬럼 전체 값이 같은지 확인하는 것만으로는 원소 포함 여부를 찾을 수 없으므로, GIN 인덱스가 필요합니다.

```sql
CREATE INDEX idx_entries_tags ON entries USING GIN (tags);
SELECT * FROM entries WHERE tags @> ARRAY['postgres'];
```

- [1] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > 연산자 클래스를 맞춰야 한다 (0.275)
- [2] study/postgres-indexes.md — Postgres 인덱스: B-tree와 GIN (0.223)
- [3] study/postgres-indexes.md — Postgres 인덱스: B-tree와 GIN > GIN 인덱스 > 값 하나에 여러 요소가 들어 있을 때 (0.177)
- [4] study/postgres-indexes.md — Postgres 인덱스: B-tree와 GIN > 정리 (0.168)
- [5] study/rag-evaluation.md — RAG 검색 평가: hit rate와 MRR > 평가 세트 만들기 (0.164)

## q02. 파일명에 해시가 들어간 JS 번들은 왜 1년 동안 캐시해도 문제가 없을까?

파일명에 해시 (콘텐츠 해시) 가 들어간 JS 번드는, 파일의 내용이 바뀌면 파일명 자체가 변경되기 때문입니다. 따라서 오래 캐시되어 있더라도 최신 버전의 파일명으로 요청이 오면 새로운 파일을 받아올 수 있어 문제가 없습니다. [1]

- [1] study/http-caching.md — HTTP 캐싱 정리 > Cache-Control 헤더 > 빌드 파일 전략 (0.424)
- [2] study/rag-pipeline-overview.md — RAG 파이프라인 전체 그림 > 인덱싱 단계 (오프라인) > 1. 가져오기와 정규화 (0.122)
- [3] study/http-caching.md — HTTP 캐싱 정리 (0.111)
- [4] study/local-llm-serving.md — 로컬 LLM 서빙: llama.cpp와 OpenAI 호환 API > GGUF와 양자화 > 모델 파일 형식 (0.108)
- [5] study/fastapi-basics.md — FastAPI 기초 > 경로 파라미터와 쿼리 파라미터 (0.107)

## q03. LEFT JOIN을 썼는데 오른쪽에 매칭 안 되는 행들이 결과에서 사라졌어. 왜 그런 거야?

LEFT JOIN을 사용했는데 오른쪽 테이블의 조건을 `WHERE` 절에 작성하면, 조인이 완료된 결과에 해당 조건이 적용되어 짝이 없는 행 (NULL 값) 이 필터링되어 사라지기 때문입니다. 이는 사실상 INNER JOIN 과 동일한 결과가 나옵니다.

오른쪽 테이블의 조건은 `ON` 절에 포함시켜야 LEFT JOIN 의 특성을 유지할 수 있습니다.

*   **잘못된 예**: `WHERE c.excluded = false` (NULL 행이 제거됨) [2]
*   **올바른 예**: `ON c.entry_id = e.id AND c.excluded = false` (NULL 행이 유지됨) [2]

- [1] study/docker-basics.md — Docker 기초 (0.115)
- [2] study/sql-joins.md — SQL JOIN 정리 > LEFT JOIN > ON과 WHERE의 차이 (0.109)
- [3] study/chunking-strategies.md — 청킹 전략 비교 > 주요 방식 > 오버랩 (0.107)
- [4] study/fastapi-basics.md — FastAPI 기초 > 다음 할 일 (0.095)
- [5] study/pydantic.md — Pydantic으로 데이터 검증하기 (0.095)

## q04. Postgres의 기본 격리 수준은 뭐고, Read Uncommitted로 설정하면 실제로 어떻게 동작해?

Postgres 의 기본 격리 수준은 **Read Committed**입니다. [1]

Read Uncommitted 로 설정해도 실제로는 **Read Committed**로 동작하며, Dirty Read 는 아예 일어나지 않습니다. [1]

- [1] study/transactions-isolation.md — 트랜잭션과 격리 수준 > 격리 수준 > Postgres의 특징 (0.283)
- [2] study/pydantic.md — Pydantic으로 데이터 검증하기 > 기본 모델 > 변환과 검증의 경계 (0.124)
- [3] study/redis-caching.md — Redis와 애플리케이션 캐싱 > 정리 (0.118)
- [4] study/transactions-isolation.md — 트랜잭션과 격리 수준 > 격리 수준 (0.111)
- [5] study/ci-basics.md — CI 기초: GitHub Actions > CI와 CD (0.108)

## q05. SQLAlchemy에서 부모를 먼저 조회한 뒤 자식을 IN 쿼리 한 번으로 묶어 가져오는 로딩 옵션은?

SQLAlchemy 에서 부모를 먼저 조회한 뒤 자식을 `WHERE entry_id IN (...)` 한 번으로 가져오는 로딩 옵션은 **selectinload**입니다. [1]

- [1] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > selectinload (0.444)
- [2] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > joinedload (0.262)
- [3] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > 집계만 필요하면 집계 쿼리로 (0.185)
- [4] study/n-plus-one.md — N+1 쿼리 문제 > 정리 (0.158)
- [5] study/n-plus-one.md — N+1 쿼리 문제 > 문제 상황 (0.149)

## q06. 워커가 죽으면 같은 작업이 다시 실행될 수 있다는데, 작업 코드는 어떻게 짜야 안전해?

워커가 죽으면 같은 작업이 다시 실행될 수 있으므로, 작업 코드는 **멱등성 (idempotency)**을 갖도록 작성해야 안전합니다.

즉, 동일한 작업을 여러 번 실행해도 최종 결과가 같아져야 합니다. 예를 들어 "노트 42 를 재인덱싱"하는 작업은 기존 청크를 지우고 다시 넣으므로 두 번 실행해도 결과가 같지만, "카운트 +1"과 같이 상태가 누적되는 작업은 두 번 실행되면 틀리게 됩니다 [1].

- [1] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 전달 보장과 멱등성 > at-least-once (0.419)
- [2] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 왜 요청 밖으로 빼야 하나 (0.211)
- [3] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > FastAPI BackgroundTasks는 큐가 아니다 (0.199)
- [4] study/python-async-await.md — Python async/await 이해하기 > CPU 작업에는 안 맞는다 (0.198)
- [5] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 기본 구성 요소 > 프로듀서, 큐, 컨슈머 (0.180)

## q07. API 컨테이너에서 DB 주소를 localhost로 적었더니 연결이 안 돼. 뭘 써야 해?

API 컨테이너 내부에서는 `localhost`이 그 컨테이너 자신을 가리키므로 DB 주소로 쓸 수 없습니다. 대신 **서비스 이름** (예: `db`) 을 사용해야 합니다.

```
DATABASE_URL=postgresql://postgres:pw@db:5432/lsb
```

참고로, 만약 호스트 맥의 LLM 서버에 접근해야 한다면 `host.docker.internal` 주소를 사용해야 합니다. [1]

- [1] study/docker-compose.md — docker compose로 여러 서비스 묶기 > 서비스 간 네트워크 (0.360)
- [2] study/linux-process-permissions.md — 리눅스 프로세스와 권한 > 컨테이너와 사용자 > root로 돌리지 않기 (0.172)
- [3] study/docker-basics.md — Docker 기초 > 다음 단계 (0.162)
- [4] study/docker-compose.md — docker compose로 여러 서비스 묶기 > depends_on과 healthcheck (0.157)
- [5] study/docker-basics.md — Docker 기초 > 자주 쓰는 명령 (0.156)

## q08. docker stop을 하면 앱이 바로 안 꺼지고 항상 10초쯤 기다렸다가 강제로 죽는 이유는?

노트에서 근거를 찾지 못했습니다. 제공된 출처에는 `docker stop` 명령어의 동작 방식이나 10 초 대기 시간과 관련된 설명이 포함되어 있지 않습니다.

- [1] study/python-async-await.md — Python async/await 이해하기 > 이벤트 루프와 코루틴 > JS와 다른 점 (0.132)
- [2] study/docker-basics.md — Docker 기초 > 자주 쓰는 명령 (0.131)
- [3] study/n-plus-one.md — N+1 쿼리 문제 > 헷갈렸던 점 (0.098)
- [4] study/docker-compose.md — docker compose로 여러 서비스 묶기 > 기본 구조 (0.083)
- [5] study/testing-pytest.md — 테스트 피라미드와 pytest > 외부 의존 대체하기 > 테스트용 DB (0.079)

## q09. Why is it better to create an IVFFlat index only after the table already contains data?

노트에서 근거를 찾지 못했습니다. 제공된 출처에는 IVFFlat 인덱스를 생성할 때 테이블에 데이터가 이미 있어야 하는 이유나 권장 사항에 대한 설명이 없습니다.

- [1] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > IVFFlat 인덱스 > 동작 원리 (0.160)
- [2] study/postgres-indexes.md — Postgres 인덱스: B-tree와 GIN > B-tree 인덱스 > 기본값이자 가장 많이 쓰는 인덱스 (0.134)
- [3] study/llm-tool-calling-agents.md — LLM 도구 호출과 에이전트 > 도구 호출의 동작 방식 > 도구 설명이 곧 프롬프트다 (0.105)
- [4] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > 설치와 기본 사용 (0.103)
- [5] study/docker-basics.md — Docker 기초 > 자주 쓰는 명령 (0.100)

## q10. Which retrieval metric gives more credit when the correct chunk is ranked first rather than third?

노트에서 근거를 찾지 못했습니다. 제공된 노트에는 검색 평가 지표 (retrieval metric) 나 랭킹 점수에 대한 설명이 포함되어 있지 않습니다.

- [1] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > joinedload (0.132)
- [2] study/alembic-migrations.md — DB 마이그레이션과 Alembic > Alembic 기본 흐름 > 리비전 파일의 구조 (0.114)
- [3] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > selectinload (0.109)
- [4] study/docker-compose.md — docker compose로 여러 서비스 묶기 (0.091)
- [5] study/local-llm-serving.md — 로컬 LLM 서빙: llama.cpp와 OpenAI 호환 API > GGUF와 양자화 > 모델 파일 형식 (0.086)
