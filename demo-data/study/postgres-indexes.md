---
date: 2026-07-11
source_type: study
tags: [postgres, index, database, performance]
---

# Postgres 인덱스: B-tree와 GIN

노트가 수천 개로 늘어나면 쿼리가 느려질 것이다. 인덱스를 언제, 어떤 종류로 걸어야 하는지 공부했다. 벡터 인덱스(HNSW, IVFFlat)는 pgvector 노트에 따로 있다.

## 인덱스가 하는 일

인덱스 없이 `WHERE entry_id = 42`를 실행하면 테이블 전체를 처음부터 끝까지 읽는다(Seq Scan). 인덱스는 책 뒤의 찾아보기처럼 값에서 행 위치로 바로 가는 별도 자료구조다.

대신 공짜는 아니다.

- 디스크 공간을 차지한다.
- INSERT, UPDATE마다 인덱스도 갱신해야 해서 쓰기가 느려진다.

## B-tree 인덱스

### 기본값이자 가장 많이 쓰는 인덱스

`CREATE INDEX`에 종류를 안 쓰면 B-tree가 만들어진다. 값이 정렬된 균형 트리라서 다음 연산에 강하다.

- 같음 비교: `=`
- 범위 비교: `<`, `>`, `BETWEEN`
- 정렬: `ORDER BY date`
- 앞부분 일치: `LIKE 'abc%'` (조건부)

```sql
CREATE INDEX idx_chunks_entry_id ON chunks (entry_id);
CREATE INDEX idx_entries_date ON entries (date);
```

### 복합 인덱스의 컬럼 순서

`(source_type, date)` 복합 인덱스는 `source_type`만 조건으로 쓰거나 둘 다 쓸 때는 효과가 있지만, `date`만 조건으로 쓰면 잘 활용되지 않는다. 전화번호부가 성으로 먼저 정렬되어 있어서 이름만으로는 찾기 어려운 것과 같다. 같음 조건 컬럼을 앞에, 범위 조건 컬럼을 뒤에 두는 게 일반적이다.

## GIN 인덱스

### 값 하나에 여러 요소가 들어 있을 때

GIN(Generalized Inverted Index)은 역색인이다. 배열, JSONB, 전문 검색(tsvector)처럼 한 행에 여러 요소가 들어 있는 컬럼에서 "이 요소를 포함하는 행"을 빠르게 찾는다.

```sql
-- tags가 text[] 일 때
CREATE INDEX idx_entries_tags ON entries USING GIN (tags);
SELECT * FROM entries WHERE tags @> ARRAY['postgres'];

-- 전문 검색
CREATE INDEX idx_chunks_fts ON chunks USING GIN (to_tsvector('simple', text));
```

헷갈렸던 점: B-tree로 배열 컬럼을 인덱싱하면 배열 전체 값이 같은지만 볼 수 있지, 원소 포함 여부는 못 찾는다. 포함 검색에는 GIN이 필요하다.

### 하이브리드 검색과의 연결

RAG에서 키워드 검색과 벡터 검색을 섞는 하이브리드 검색을 하려면 키워드 쪽은 GIN 전문 검색 인덱스나 `pg_trgm` 트라이그램 인덱스가 필요하다. 한국어는 기본 형태소 분석이 없어서 `simple` 설정이나 트라이그램이 현실적인 선택지라고 한다.

## 인덱스가 실제로 쓰이는지 확인하기

`EXPLAIN ANALYZE`로 실행 계획을 본다.

```sql
EXPLAIN ANALYZE SELECT * FROM chunks WHERE entry_id = 42;
```

`Index Scan`이 보이면 쓰인 것, `Seq Scan`이면 안 쓰인 것이다. 테이블이 작으면 플래너가 일부러 Seq Scan을 고르기도 한다. 인덱스를 거치는 것보다 그냥 다 읽는 게 빠르기 때문이다. 처음엔 인덱스가 고장 난 줄 알았다.

## 정리

- 기본은 B-tree. 같음, 범위, 정렬.
- 배열, JSONB, 전문 검색은 GIN.
- 외래 키 컬럼(`entry_id`)에는 Postgres가 자동으로 인덱스를 만들어 주지 않으니 직접 만든다.
- 추측하지 말고 `EXPLAIN ANALYZE`로 확인한다.
