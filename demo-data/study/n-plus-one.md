---
date: 2026-07-23
source_type: study
tags: [orm, sqlalchemy, performance, database]
---

# N+1 쿼리 문제

ORM을 쓰기 시작하면서 가장 먼저 경고받은 문제다. 면접 단골 질문이라고 해서 원리와 해결법을 확실히 정리해 둔다.

## 문제 상황

노트 목록과 각 노트의 청크 개수를 보여주는 화면을 만든다고 하자.

```python
entries = session.scalars(select(Entry)).all()   # 쿼리 1번
for e in entries:
    print(e.file_path, len(e.chunks))             # 노트마다 쿼리 1번씩
```

노트가 100개면 목록 조회 1번 + 청크 조회 100번, 총 101번의 쿼리가 나간다. 그래서 N+1이다. 코드만 보면 쿼리가 보이지 않아서 더 위험하다. `e.chunks`에 처음 접근하는 순간 지연 로딩(lazy loading)으로 쿼리가 실행되기 때문이다.

### 프론트엔드에서 겪은 비슷한 일

목록 컴포넌트에서 각 아이템이 자기 상세 API를 따로 호출하던 구조가 있었다. 화면에 카드가 50개면 요청이 51번 나갔다. 네트워크 탭이 폭포처럼 길어졌던 기억이 난다. 원리가 완전히 같다. 그때도 해결책은 목록 API에서 필요한 데이터를 한 번에 내려받는 것이었다.

## 발견하는 방법

- SQLAlchemy 엔진에 `echo=True`를 켜서 실제 SQL 로그를 본다.
- 테스트에서 쿼리 횟수를 세는 이벤트 리스너를 달아 기준치를 넘으면 실패하게 만든다.
- 응답 시간이 데이터 개수에 비례해서 늘어나면 의심한다.

## 해결 방법

### joinedload

JOIN 한 번으로 부모와 자식을 함께 가져온다.

```python
stmt = select(Entry).options(joinedload(Entry.chunks))
```

1:N 관계에서는 부모 행이 자식 수만큼 복제되어 전송되므로, 자식이 많으면 데이터 양이 커진다.

### selectinload

부모를 먼저 조회한 뒤, 자식을 `WHERE entry_id IN (...)` 한 번으로 가져온다. 총 2번의 쿼리.

```python
stmt = select(Entry).options(selectinload(Entry.chunks))
```

1:N 컬렉션에는 보통 selectinload가 더 낫다고 한다. 중복 전송이 없기 때문이다.

### 집계만 필요하면 집계 쿼리로

청크 "개수"만 필요하다면 청크 객체를 다 불러올 이유가 없다. SQL JOIN 노트에서 쓴 것처럼 `LEFT JOIN` + `GROUP BY`로 한 번에 숫자만 가져오는 게 가장 효율적이다.

## 헷갈렸던 점

- async SQLAlchemy에서는 지연 로딩이 아예 오류를 낸다. 암묵적인 I/O가 이벤트 루프 밖에서 일어날 수 없기 때문이다. 오히려 N+1을 강제로 드러내 줘서 좋다고 생각했다.
- GraphQL에서도 같은 문제가 생기고, DataLoader라는 배치 도구로 해결한다. 프론트에서 Apollo를 쓸 때 들어 본 이름이 여기서 이어졌다.

## 정리

1. ORM 속성 접근이 쿼리일 수 있다는 걸 항상 의식한다.
2. 컬렉션은 `selectinload`, 단일 관계는 `joinedload`가 기본 선택.
3. 숫자만 필요하면 집계 쿼리.
4. 로그로 실제 쿼리 수를 확인한다.
