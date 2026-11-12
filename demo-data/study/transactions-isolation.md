---
date: 2026-07-15
source_type: study
tags: [database, transaction, postgres, concurrency]
---

# 트랜잭션과 격리 수준

노트를 재인덱싱할 때 "기존 청크 삭제 → 새 청크 삽입" 중간에 실패하면 청크가 하나도 없는 노트가 생긴다. 이걸 막는 게 트랜잭션이다. 동시성 문제까지 같이 정리했다.

## ACID

- Atomicity(원자성): 전부 성공하거나 전부 취소된다.
- Consistency(일관성): 제약 조건을 깨는 상태로 끝나지 않는다.
- Isolation(격리성): 동시에 실행되는 트랜잭션이 서로 간섭하지 않는 정도.
- Durability(지속성): 커밋된 결과는 장애 후에도 남는다.

```sql
BEGIN;
DELETE FROM chunks WHERE entry_id = 42;
INSERT INTO chunks (entry_id, idx, text) VALUES (42, 0, '...');
COMMIT;  -- 중간에 오류가 나면 ROLLBACK
```

SQLAlchemy에서는 `with session.begin():` 블록이 끝나면 커밋, 예외가 나면 롤백된다.

## 동시성에서 생기는 이상 현상

### Dirty Read

다른 트랜잭션이 아직 커밋하지 않은 값을 읽는 것. 그 트랜잭션이 롤백되면 존재하지 않았던 값을 본 셈이 된다.

### Non-repeatable Read

같은 트랜잭션 안에서 같은 행을 두 번 읽었는데, 그 사이 다른 트랜잭션이 수정하고 커밋해서 값이 달라지는 것.

### Phantom Read

같은 조건으로 두 번 조회했는데, 그 사이 다른 트랜잭션이 행을 추가해서 결과 행 개수가 달라지는 것.

### Lost Update

두 트랜잭션이 같은 값을 읽고 각자 +1 해서 쓰면, 하나의 증가가 사라진다. 프론트에서 상태를 두 번 업데이트할 때 이전 값을 기준으로 덮어쓰는 버그와 비슷한 느낌이다.

## 격리 수준

| 수준 | Dirty Read | Non-repeatable | Phantom |
|---|---|---|---|
| Read Uncommitted | 가능 | 가능 | 가능 |
| Read Committed | 방지 | 가능 | 가능 |
| Repeatable Read | 방지 | 방지 | 가능(표준 기준) |
| Serializable | 방지 | 방지 | 방지 |

### Postgres의 특징

- 기본값은 Read Committed다.
- Read Uncommitted를 지정해도 실제로는 Read Committed로 동작한다. Dirty Read는 Postgres에서 아예 일어나지 않는다.
- Postgres의 Repeatable Read는 스냅샷 기반이라 표준과 달리 Phantom도 막는다.
- Serializable에서는 충돌이 감지되면 트랜잭션이 직렬화 실패 오류로 끝난다. 애플리케이션이 재시도해야 한다.

헷갈렸던 점: 격리 수준을 올리면 "기다렸다가 안전하게 실행"되는 줄 알았는데, Postgres는 낙관적으로 실행하다가 충돌하면 실패시키는 방식이 많다. 재시도 로직이 필수다.

## Lost Update 막기

### SELECT ... FOR UPDATE

읽을 때부터 행에 잠금을 건다.

```sql
BEGIN;
SELECT view_count FROM entries WHERE id = 42 FOR UPDATE;
UPDATE entries SET view_count = view_count + 1 WHERE id = 42;
COMMIT;
```

사실 이 경우는 `UPDATE ... SET view_count = view_count + 1` 한 줄로 쓰면 원자적으로 처리되어 잠금이 필요 없다. 읽고 나서 애플리케이션 코드에서 계산하는 경우에만 `FOR UPDATE`가 필요하다.

### 낙관적 잠금

`version` 컬럼을 두고 `UPDATE ... WHERE id = 42 AND version = 3`처럼 갱신한다. 영향받은 행이 0이면 누군가 먼저 바꾼 것이니 다시 시도한다. 프론트엔드의 ETag 기반 충돌 감지와 같은 아이디어다.

## 내 프로젝트 적용

재인덱싱은 노트 단위로 한 트랜잭션. 임베딩 API 호출처럼 오래 걸리는 작업은 트랜잭션 밖에서 먼저 끝내고, DB 쓰기만 짧게 트랜잭션으로 묶기로 했다. 트랜잭션을 오래 열어 두면 잠금이 길어지기 때문이다.
