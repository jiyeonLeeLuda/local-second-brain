# Q&A run: Qwen3.5-9B-GGUF / Qwen3-Embedding-0.6B-GGUF

| id | 인용 있음 | 정답 파일 인용 | 시간(s) |
|---|---|---|---|
| q01 | O | O | 9.8 |
| q02 | O | O | 6.1 |
| q03 | O | O | 14.5 |
| q04 | O | O | 4.7 |
| q05 | O | O | 5.2 |
| q06 | O | O | 14.4 |
| q07 | O | O | 6.4 |
| q08 | O | O | 12.1 |
| q09 | O | O | 6.4 |
| q10 | O | O | 8.5 |

인용 포함 10/10 (100%), 정답 파일 인용 10/10 (100%)

## q01. 태그 배열 컬럼에 특정 태그가 들어 있는 노트를 빨리 찾으려면 어떤 종류의 인덱스를 써야 해?

태그 배열 컬럼에 특정 태그가 들어 있는 노트를 빠르게 찾으려면 **GIN (Generalized Inverted Index)** 인덱스를 사용해야 합니다.

B-tree 인덱스는 배열 전체 값이 같은지만 확인할 수 있지만, 원소 포함 여부는 검색할 수 없습니다. 반면 GIN 인덱스는 배열, JSONB, tsvector처럼 한 행에 여러 요소가 들어 있는 컬럼에서 특정 요소를 포함하는 행을 빠르게 찾아냅니다 [1].

- [1] study/postgres-indexes.md — Postgres 인덱스: B-tree와 GIN > GIN 인덱스 > 값 하나에 여러 요소가 들어 있을 때 (0.617)
- [2] study/rag-evaluation.md — RAG 검색 평가: hit rate와 MRR > 평가 세트 만들기 (0.614)
- [3] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > 연산자 클래스를 맞춰야 한다 (0.602)
- [4] study/rest-api-design.md — REST API 설계 원칙 > 필터, 정렬, 검색 (0.600)
- [5] study/rag-pipeline-overview.md — RAG 파이프라인 전체 그림 > 인덱싱 단계 (오프라인) > 2. 청킹 (0.595)

## q02. 파일명에 해시가 들어간 JS 번들은 왜 1년 동안 캐시해도 문제가 없을까?

파일명에 해시 (콘텐츠 해시) 가 들어간 JS 번드는, 파일의 내용이 바뀌면 파일명 자체가 변경되기 때문입니다. 따라서 사용자가 오래된 캐시를 참조하더라도 실제로는 새로운 파일명을 가진 리소스를 받아오게 되어, 오래 캐시해도 문제가 없습니다. [1]

- [1] study/http-caching.md — HTTP 캐싱 정리 > Cache-Control 헤더 > 빌드 파일 전략 (0.653)
- [2] study/http-caching.md — HTTP 캐싱 정리 (0.621)
- [3] study/http-caching.md — HTTP 캐싱 정리 > 정리 (0.609)
- [4] study/redis-caching.md — Redis와 애플리케이션 캐싱 > 캐시 무효화 (0.586)
- [5] study/redis-caching.md — Redis와 애플리케이션 캐싱 > 캐시 스탬피드 (0.576)

## q03. LEFT JOIN을 썼는데 오른쪽에 매칭 안 되는 행들이 결과에서 사라졌어. 왜 그런 거야?

LEFT JOIN을 사용했는데 오른쪽 테이블의 조건을 `WHERE` 절에 작성하면, 조인이 완료된 결과에서 오른쪽 테이블의 값이 없는 행 (NULL) 이 걸러져서 사실상 **INNER JOIN**이 되는 효과가 발생합니다.

따라서 오른쪽 테이블의 조건은 `ON` 절에 포함해야 합니다.

*   **잘못된 예 (WHERE 사용):**
    ```sql
    LEFT JOIN chunks c ON c.entry_id = e.id
    WHERE c.excluded = false
    ```
    이 경우 짝이 없는 행은 `c.excluded` 가 NULL 이 되어 `= false` 조건을 통과하지 못해 사라집니다. [1]

*   **올바른 예 (ON 사용):**
    ```sql
    LEFT JOIN chunks c ON c.entry_id = e.id AND c.excluded = false
    ```
    조건을 조인 조건에 넣어야 왼쪽 테이블의 모든 행이 유지됩니다. [1]

- [1] study/sql-joins.md — SQL JOIN 정리 > LEFT JOIN > ON과 WHERE의 차이 (0.699)
- [2] study/sql-joins.md — SQL JOIN 정리 > RIGHT JOIN과 FULL OUTER JOIN (0.569)
- [3] study/sql-joins.md — SQL JOIN 정리 > 조인과 집계를 함께 쓸 때 주의 (0.561)
- [4] study/sql-joins.md — SQL JOIN 정리 > LEFT JOIN > 짝이 없어도 왼쪽은 남긴다 (0.559)
- [5] study/sql-joins.md — SQL JOIN 정리 > INNER JOIN (0.548)

## q04. Postgres의 기본 격리 수준은 뭐고, Read Uncommitted로 설정하면 실제로 어떻게 동작해?

Postgres 의 기본 격리 수준은 **Read Committed**입니다. [1]

Read Uncommitted 로 설정하더라도 실제로는 **Read Committed**로 동작합니다. [1]

- [1] study/transactions-isolation.md — 트랜잭션과 격리 수준 > 격리 수준 > Postgres의 특징 (0.791)
- [2] study/transactions-isolation.md — 트랜잭션과 격리 수준 > 격리 수준 (0.737)
- [3] study/transactions-isolation.md — 트랜잭션과 격리 수준 > 동시성에서 생기는 이상 현상 > Dirty Read (0.623)
- [4] study/transactions-isolation.md — 트랜잭션과 격리 수준 > 동시성에서 생기는 이상 현상 > Non-repeatable Read (0.574)
- [5] study/testing-pytest.md — 테스트 피라미드와 pytest > 외부 의존 대체하기 > 테스트용 DB (0.558)

## q05. SQLAlchemy에서 부모를 먼저 조회한 뒤 자식을 IN 쿼리 한 번으로 묶어 가져오는 로딩 옵션은?

SQLAlchemy에서 부모를 먼저 조회한 뒤 자식을 `WHERE entry_id IN (...)` 한 번으로 가져오는 로딩 옵션은 **`selectinload`**입니다. [1]

- [1] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > selectinload (0.756)
- [2] study/n-plus-one.md — N+1 쿼리 문제 > 해결 방법 > joinedload (0.745)
- [3] study/n-plus-one.md — N+1 쿼리 문제 > 정리 (0.639)
- [4] study/n-plus-one.md — N+1 쿼리 문제 > 헷갈렸던 점 (0.618)
- [5] study/n-plus-one.md — N+1 쿼리 문제 > 문제 상황 (0.594)

## q06. 워커가 죽으면 같은 작업이 다시 실행될 수 있다는데, 작업 코드는 어떻게 짜야 안전해?

워커가 죽으면 같은 작업이 다시 실행될 수 있으므로, 작업 코드는 **멱등성 (Idempotency)**을 갖춰야 안전합니다.

즉, 동일한 작업을 여러 번 실행해도 결과가 같아야 합니다.
*   **안전한 예시:** "노트 42 를 재인덱싱"과 같이 기존 데이터를 지우고 다시 넣는 작업은 두 번 실행해도 결과가 동일하므로 안전합니다. [1]
*   **위험한 예시:** "카운트 +1"과 같이 상태를 누적하는 작업은 두 번 실행되면 결과가 틀리므로 안전하지 않습니다. [1]

현실적으로 '정확히 한 번' (exactly-once) 을 보장하는 것은 어렵거나 비싸므로, '최소 한 번' (at-least-once) 전달을 보장하는 큐 시스템에서 멱등한 작업을 사용하는 것이 현실적인 해법입니다. [1]

- [1] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 전달 보장과 멱등성 > at-least-once (0.568)
- [2] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 전달 보장과 멱등성 > 재시도와 데드 레터 큐 (0.507)
- [3] study/llm-tool-calling-agents.md — LLM 도구 호출과 에이전트 > 워크플로와 에이전트의 구분 (0.473)
- [4] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 왜 요청 밖으로 빼야 하나 (0.456)
- [5] study/message-queues-background-jobs.md — 메시지 큐와 백그라운드 작업 > 내 프로젝트 계획 (0.454)

## q07. API 컨테이너에서 DB 주소를 localhost로 적었더니 연결이 안 돼. 뭘 써야 해?

API 컨테이너 내부에서는 `localhost`이 그 컨테이너 자신을 가리키므로 DB 연결이 안 됩니다. 대신 서비스 이름인 `db`를 사용해야 합니다.

```
DATABASE_URL=postgresql://postgres:pw@db:5432/lsb
```
[1]

- [1] study/docker-compose.md — docker compose로 여러 서비스 묶기 > 서비스 간 네트워크 (0.676)
- [2] study/testing-pytest.md — 테스트 피라미드와 pytest > 외부 의존 대체하기 > 테스트용 DB (0.546)
- [3] study/docker-basics.md — Docker 기초 > 자주 쓰는 명령 (0.535)
- [4] study/docker-compose.md — docker compose로 여러 서비스 묶기 > 포트 노출과 보안 (0.523)
- [5] study/ci-basics.md — CI 기초: GitHub Actions > 서비스 컨테이너 (0.506)

## q08. docker stop을 하면 앱이 바로 안 꺼지고 항상 10초쯤 기다렸다가 강제로 죽는 이유는?

`docker stop` 은 PID 1 에 `SIGTERM` 을 보내고, 10 초 안에 종료되지 않으면 `SIGKILL` 을 보내 강제 종료합니다 [1].

Dockerfile 에서 `CMD uvicorn ...` 처럼 **셸 형식**으로 명령을 작성하면, 셸이 PID 1 이 되어 자식 프로세스에게 시그널을 전달하지 못합니다 [1]. 이로 인해 자식 프로세스가 종료되지 않아 10 초 대기 후 강제 종료되는 현상이 발생합니다.

해결을 위해서는 `CMD ["uvicorn", ...]` 와 같이 **exec 형식**으로 작성하여 PID 1 이 실제 애플리케이션이 되도록 해야 합니다 [1].

- [1] study/linux-process-permissions.md — 리눅스 프로세스와 권한 > 프로세스 기본 > 컨테이너의 PID 1 문제 (0.635)
- [2] study/docker-compose.md — docker compose로 여러 서비스 묶기 > depends_on과 healthcheck (0.468)
- [3] study/linux-process-permissions.md — 리눅스 프로세스와 권한 > 프로세스 기본 > 시그널 (0.464)
- [4] study/linux-process-permissions.md — 리눅스 프로세스와 권한 > 컨테이너와 사용자 > root로 돌리지 않기 (0.457)
- [5] study/linux-process-permissions.md — 리눅스 프로세스와 권한 > 프로세스 기본 > PID와 부모 프로세스 (0.447)

## q09. Why is it better to create an IVFFlat index only after the table already contains data?

IVFFlat 인덱스는 클러스터 중심을 생성 시점의 데이터로 결정하기 때문에, 데이터가 어느 정도 쌓인 뒤에 만들어야 합니다. 빈 테이블에 인덱스를 만들면 품질이 나빠집니다.[3]

- [1] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > IVFFlat 인덱스 > 동작 원리 (0.791)
- [2] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > HNSW 인덱스 > 특징 (0.790)
- [3] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > IVFFlat 인덱스 > 특징 (0.776)
- [4] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > HNSW 인덱스 > 동작 원리 (0.710)
- [5] study/pgvector-hnsw-ivfflat.md — pgvector와 벡터 인덱스(HNSW, IVFFlat) > 연산자 클래스를 맞춰야 한다 (0.689)

## q10. Which retrieval metric gives more credit when the correct chunk is ranked first rather than third?

**Mean Reciprocal Rank (MRR)** 가 정답이 1 위일 때 3 위일 때보다 더 높은 점수를 줍니다.

MRR 은 정답이 처음 나타나는 순위의 역수를 계산하므로, 순위가 높을수록 보상이 커집니다. 예를 들어 1 위일 때는 1.0, 3 위일 때는 약 0.33 의 점수가 부여됩니다. [2]

- [1] study/rag-evaluation.md — RAG 검색 평가: hit rate와 MRR > 정답 판정 기준 (0.702)
- [2] study/rag-evaluation.md — RAG 검색 평가: hit rate와 MRR > 지표 > MRR (Mean Reciprocal Rank) (0.700)
- [3] study/rag-pipeline-overview.md — RAG 파이프라인 전체 그림 > 질의 단계 (온라인) > 5. 재정렬 (선택) (0.678)
- [4] study/rag-evaluation.md — RAG 검색 평가: hit rate와 MRR > 지표 > Hit Rate (Recall@k) (0.669)
- [5] study/rag-evaluation.md — RAG 검색 평가: hit rate와 MRR > 지표 > nDCG (0.651)
