---
date: 2026-08-20
source_type: study
tags: [testing, pytest, python, quality]
---

# 테스트 피라미드와 pytest

프론트엔드에서는 Jest와 Testing Library로 컴포넌트 테스트를 조금 써 봤다. 백엔드에서는 무엇을 얼마나 테스트해야 하는지 감이 없어서 테스트 피라미드부터 정리하고 pytest를 익혔다.

## 테스트 피라미드

### 세 층

- 단위 테스트(아래, 가장 많이): 함수 하나, 클래스 하나. 빠르고 외부 의존이 없다.
- 통합 테스트(가운데): DB, 외부 API 등 실제 구성 요소를 함께 쓴다.
- E2E 테스트(위, 가장 적게): 사용자 입장에서 전체 흐름을 확인한다. 느리고 깨지기 쉽다.

아래로 갈수록 빠르고 싸며 많이 쓰고, 위로 갈수록 느리고 비싸서 핵심 흐름만 쓴다.

### 프론트엔드 관점과의 차이

프론트에서는 "테스트 트로피" 모델처럼 통합 테스트 비중을 높이자는 의견도 많았다. 백엔드에서도 DB가 핵심인 앱이라면 실제 Postgres를 띄운 통합 테스트가 가치가 크다고 느꼈다. 비율보다 "자신 있게 배포할 수 있는가"가 기준이다.

## pytest 기본

```python
# tests/test_chunking.py
from app.chunking import split_by_heading

def test_split_keeps_heading_path():
    md = "# A\n본문\n## B\n내용"
    chunks = split_by_heading(md)
    assert chunks[1].heading_path == ["A", "B"]
```

`test_`로 시작하는 파일과 함수를 자동으로 찾는다. `assert` 하나로 비교하면 실패 시 값 차이를 자세히 보여준다. Jest의 `expect().toBe()`보다 단순해서 좋았다.

## fixture

테스트에 필요한 준비물을 함수로 정의하고 인자 이름으로 주입받는다.

```python
import pytest

@pytest.fixture
def sample_note(tmp_path):
    p = tmp_path / "note.md"
    p.write_text("# 제목\n본문")
    return p

def test_read_note(sample_note):
    assert read_note(sample_note).title == "제목"
```

`tmp_path`는 pytest가 제공하는 임시 폴더 fixture다. `scope="session"`을 주면 테스트 전체에서 한 번만 만든다(예: 테스트용 DB 연결).

## parametrize

같은 테스트를 여러 입력으로 돌린다.

```python
@pytest.mark.parametrize("text,expected", [
    ("", 0),
    ("# A", 1),
    ("# A\n## B", 2),
])
def test_chunk_count(text, expected):
    assert len(split_by_heading(text)) == expected
```

청킹 같은 순수 함수는 경계 사례(빈 문서, 제목만 있는 문서, 아주 긴 문단)를 parametrize로 몰아서 테스트하기 좋다.

## 외부 의존 대체하기

### LLM과 임베딩 호출

테스트에서 실제 LLM 서버를 부르면 느리고 결과가 매번 달라진다. 가짜 객체로 바꾼다.

- FastAPI는 `app.dependency_overrides`로 의존성을 교체한다.
- 임베딩은 텍스트 해시로 결정적인 벡터를 만드는 가짜 함수를 쓴다.
- `monkeypatch` fixture로 함수나 환경변수를 바꿀 수 있다.

헷갈렸던 점: 모든 걸 mock하면 테스트는 통과하는데 실제로는 안 돌아가는 상황이 생긴다. 경계(HTTP 클라이언트)만 대체하고 내부 로직은 진짜로 실행하는 게 좋다.

### 테스트용 DB

docker compose로 테스트 전용 Postgres를 띄우고, 테스트마다 트랜잭션을 열었다가 롤백하면 데이터가 남지 않는다.

## 무엇을 꼭 테스트할까

프로젝트 계획서의 품질 단계에 적은 항목이다: 청킹, 점수 함수, 권한 경계(일기가 면접 코치 검색에 섞이지 않는지), API. 특히 권한 경계는 버그가 나면 개인 정보가 노출되므로 가장 먼저 테스트하기로 했다.
