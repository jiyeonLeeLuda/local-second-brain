---
date: 2026-07-07
source_type: study
tags: [sql, database, postgres]
---

# SQL JOIN 정리

프론트에서는 API가 이미 합쳐서 내려준 데이터만 봤다. 이제 노트(entries)와 청크(chunks) 테이블을 직접 엮어야 해서 JOIN을 다시 공부했다. 예시는 내 프로젝트 테이블 구조를 단순화해서 쓴다.

```sql
entries(id, file_path, source_type, date)
chunks(id, entry_id, idx, text, heading_path)
```

## INNER JOIN

양쪽에 짝이 있는 행만 남긴다.

```sql
SELECT e.file_path, c.heading_path
FROM chunks c
JOIN entries e ON e.id = c.entry_id
WHERE e.source_type = 'study';
```

`JOIN`만 쓰면 기본이 INNER JOIN이다. 청크가 하나도 없는 노트는 결과에서 빠진다.

## LEFT JOIN

### 짝이 없어도 왼쪽은 남긴다

```sql
SELECT e.file_path, COUNT(c.id) AS chunk_count
FROM entries e
LEFT JOIN chunks c ON c.entry_id = e.id
GROUP BY e.file_path;
```

아직 청킹되지 않은 노트도 `chunk_count = 0`으로 나온다. 인덱싱이 빠진 파일을 찾을 때 유용하다.

### ON과 WHERE의 차이

가장 헷갈렸던 부분이다. LEFT JOIN에서 오른쪽 테이블 조건을 `WHERE`에 쓰면 사실상 INNER JOIN이 된다.

```sql
-- 의도: 모든 노트 + 제외되지 않은 청크 수
-- 잘못된 예: excluded 조건이 NULL 행을 없애 버림
LEFT JOIN chunks c ON c.entry_id = e.id
WHERE c.excluded = false

-- 올바른 예
LEFT JOIN chunks c ON c.entry_id = e.id AND c.excluded = false
```

`WHERE`는 조인이 끝난 결과에 적용되는데, 짝이 없는 행은 `c.excluded`가 NULL이라 `= false`를 통과하지 못한다. 이 차이로 숫자가 안 맞아서 한참 디버깅했다.

## RIGHT JOIN과 FULL OUTER JOIN

- RIGHT JOIN은 LEFT JOIN의 방향만 반대다. 테이블 순서를 바꿔 LEFT로 쓰는 게 읽기 쉬워서 거의 안 쓴다.
- FULL OUTER JOIN은 양쪽 모두 남긴다. 두 소스를 비교할 때(예: 파일 시스템 목록과 DB 목록의 차이) 쓸 수 있다.

## 셀프 조인

같은 테이블을 두 번 조인한다. 예를 들어 같은 노트 안에서 바로 다음 청크를 붙여서 보여주기.

```sql
SELECT a.text, b.text AS next_text
FROM chunks a
LEFT JOIN chunks b ON b.entry_id = a.entry_id AND b.idx = a.idx + 1;
```

검색 결과의 앞뒤 문맥을 보여줄 때 쓸 수 있겠다.

## 조인과 집계를 함께 쓸 때 주의

1:N 관계를 조인하면 왼쪽 행이 N번 복제된다. 그 상태에서 왼쪽 컬럼을 `SUM`하면 값이 부풀려진다. 집계는 먼저 서브쿼리나 CTE로 하고 나서 조인하는 습관을 들이기로 했다.

## ORM과의 관계

SQLAlchemy에서 relationship을 쓰면 JOIN을 직접 안 써도 되지만, 내부에서 어떤 SQL이 나가는지 모르면 N+1 문제가 생긴다. 그 내용은 N+1 노트에 따로 정리했다. 결국 ORM을 쓰더라도 JOIN은 알고 있어야 한다.
