---
date: 2026-07-19
source_type: study
tags: [database, migration, alembic, python]
---

# DB 마이그레이션과 Alembic

맥북(개발)과 맥미니(운영)의 DB를 분리하기로 하면서 "테이블 구조를 어떻게 똑같이 맞추지?"라는 문제가 생겼다. 손으로 `ALTER TABLE`을 두 번 치는 건 언젠가 실수한다. 그래서 마이그레이션 도구를 공부했다.

## 마이그레이션이란

스키마 변경을 코드 파일로 기록하고, 순서대로 적용하는 방식이다. Git이 소스 코드의 변경 이력을 관리하듯, 마이그레이션은 DB 구조의 변경 이력을 관리한다. 프론트엔드에 비유하면 package-lock처럼 "이 상태를 재현할 수 있는 기록"이다.

## Alembic 기본 흐름

```bash
alembic init migrations
alembic revision --autogenerate -m "add chunks table"
alembic upgrade head
alembic downgrade -1
```

### 리비전 파일의 구조

```python
revision = "a1b2c3"
down_revision = "9f8e7d"

def upgrade():
    op.add_column("chunks", sa.Column("heading_path", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("chunks", "heading_path")
```

각 파일은 `down_revision`으로 이전 파일을 가리켜서 연결 리스트를 이룬다. DB에는 `alembic_version` 테이블이 있고 현재 적용된 리비전 ID가 저장된다.

## autogenerate를 믿으면 안 되는 이유

`--autogenerate`는 SQLAlchemy 모델과 실제 DB를 비교해서 변경 사항을 추측한다. 편하지만 한계가 있다.

- 컬럼 이름 변경을 "삭제 + 추가"로 인식한다. 그대로 적용하면 데이터가 날아간다.
- 일부 타입 변경, 서버 기본값, 확장 기능(pgvector의 `vector` 타입 등)은 제대로 감지 못 하는 경우가 있다.
- 그래서 생성된 파일은 반드시 열어서 읽고 고쳐야 한다.

헷갈렸던 점: autogenerate가 "자동 마이그레이션"이 아니라 "초안 작성기"라는 것. 커밋 전 리뷰가 필수다.

## 데이터가 있는 테이블을 바꿀 때

### NOT NULL 컬럼 추가

이미 행이 있는 테이블에 `NOT NULL` 컬럼을 그냥 추가하면 실패한다. 단계를 나눈다.

1. nullable로 컬럼 추가
2. 기존 행에 값 채우기(데이터 마이그레이션)
3. NOT NULL 제약 추가

### 확장 기능 활성화

pgvector를 쓰려면 먼저 확장을 켜는 마이그레이션이 필요하다.

```python
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

## 개발/운영 환경에서의 운영 규칙

내 프로젝트에서 정한 규칙이다.

- 마이그레이션 파일은 Git으로 관리하고, 맥북에서만 생성한다.
- 맥미니에서는 `git pull` 후 `alembic upgrade head`만 실행한다. 컨테이너 시작 스크립트에 넣어도 된다.
- 운영 DB에 직접 `ALTER TABLE` 하지 않는다. 한 번이라도 손으로 바꾸면 이력과 실제가 어긋난다.
- 이미 운영에 적용된 리비전 파일은 수정하지 않는다. 고칠 게 있으면 새 리비전을 만든다.

## downgrade는 꼭 써야 할까

개인 프로젝트라면 실제로 downgrade를 쓸 일은 드물다. 그래도 개발 중에 같은 마이그레이션을 고쳐 가며 반복 적용할 때 `downgrade -1` → 수정 → `upgrade head`가 편해서 작성해 두는 게 낫다. 데이터를 지우는 downgrade는 운영에서 실행하지 않도록 주의한다.
