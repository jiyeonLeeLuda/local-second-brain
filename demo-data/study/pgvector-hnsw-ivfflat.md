---
date: 2026-09-06
source_type: study
tags: [pgvector, postgres, vector-index, hnsw, ai]
---

# pgvector와 벡터 인덱스(HNSW, IVFFlat)

별도 벡터 DB를 띄우지 않고 이미 쓰는 Postgres에 벡터 검색을 붙이려고 pgvector를 선택했다. 노트, 메타데이터, 벡터를 한 DB에서 JOIN할 수 있다는 게 가장 큰 장점이다.

## 설치와 기본 사용

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
  id bigserial PRIMARY KEY,
  entry_id bigint REFERENCES entries(id),
  text text,
  embedding vector(1024)
);
```

### 거리 연산자

- `<->`: 유클리드 거리(L2)
- `<=>`: 코사인 거리(1 - 코사인 유사도)
- `<#>`: 음의 내적

```sql
SELECT id, text, embedding <=> $1 AS distance
FROM chunks
ORDER BY embedding <=> $1
LIMIT 5;
```

헷갈렸던 점: `<=>`는 유사도가 아니라 **거리**라서 작을수록 비슷하다. 그래서 `ORDER BY ... ASC`가 맞다. 임베딩 노트에서 정리한 코사인 유사도와 부호가 반대라는 걸 몇 번이나 잊었다.

## 왜 인덱스가 필요한가

인덱스가 없으면 모든 행과 거리를 계산하는 정확한 검색(exact search)을 한다. 수만 개까지는 괜찮지만 커질수록 느려진다. 벡터 인덱스는 근사 최근접 이웃(ANN) 검색으로, 약간의 정확도를 포기하고 속도를 얻는다. B-tree처럼 "정확한 답을 빠르게"가 아니라 "거의 맞는 답을 빠르게"다.

## IVFFlat 인덱스

### 동작 원리

벡터들을 `lists`개의 클러스터로 나누고, 검색할 때는 질문 벡터와 가까운 몇 개 클러스터(`probes`)만 뒤진다.

```sql
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
SET ivfflat.probes = 10;
```

### 특징

- 인덱스 생성이 빠르고 메모리를 적게 쓴다.
- 클러스터 중심을 생성 시점의 데이터로 정하므로, **데이터가 어느 정도 쌓인 뒤에 만들어야** 한다. 빈 테이블에 만들면 품질이 나쁘다.
- `probes`를 늘리면 정확도가 오르고 속도가 떨어진다.

## HNSW 인덱스

### 동작 원리

여러 층으로 된 그래프를 만든다. 위층은 듬성듬성 연결된 고속도로, 아래층은 촘촘한 골목길 같은 구조다. 위에서 대략적인 방향을 잡고 아래로 내려오며 가까운 이웃을 따라간다.

```sql
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
SET hnsw.ef_search = 40;
```

### 특징

- 같은 속도에서 IVFFlat보다 재현율(recall)이 대체로 좋다.
- 빈 테이블에 먼저 만들어도 된다. 데이터가 추가될 때 그래프가 갱신된다.
- 인덱스 생성이 느리고 메모리를 더 쓴다.
- `ef_search`를 올리면 정확도가 오르고 느려진다.

## 연산자 클래스를 맞춰야 한다

인덱스를 `vector_cosine_ops`로 만들었으면 쿼리도 `<=>`를 써야 인덱스가 쓰인다. `<->`로 검색하면 인덱스를 못 탄다. Postgres 인덱스 노트에서 배운 `EXPLAIN ANALYZE`로 확인한다.

## 필터와 함께 쓸 때의 함정

`WHERE source_type = 'study'` 같은 필터와 벡터 인덱스를 같이 쓰면, 인덱스가 먼저 상위 후보를 뽑은 뒤 필터를 적용해서 결과가 `LIMIT`보다 적게 나올 수 있다. 일기를 면접 코치 검색에서 제외하는 것처럼 필터가 중요한 경우, 필터 조건이 강하면 결과가 비어 버릴 수도 있다. 최신 pgvector에는 반복 인덱스 스캔 옵션이 있다고 하니 버전을 확인할 것.

## 내 선택

로컬 규모(수만 청크)에서는 인덱스 없이 정확한 검색도 충분히 빠를 수 있다. 처음엔 인덱스 없이 시작해서 정확한 결과를 기준선으로 삼고, 느려지면 HNSW를 추가해 재현율 차이를 비교해 보려고 한다. 평가 노트의 hit rate로 비교할 수 있다.
