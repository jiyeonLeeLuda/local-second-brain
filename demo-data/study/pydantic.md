---
date: 2026-07-03
source_type: study
tags: [python, pydantic, validation, fastapi]
---

# Pydantic으로 데이터 검증하기

TypeScript의 타입은 컴파일 시점에만 존재하고 런타임에는 사라진다. 그래서 프론트에서는 API 응답을 검증하려고 zod를 썼다. Python에서 그 역할을 하는 게 Pydantic이고, FastAPI의 요청/응답 처리 전체가 이 위에서 돌아간다.

## 기본 모델

```python
from pydantic import BaseModel, Field
from datetime import date

class Note(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    date: date
    tags: list[str] = []
    source_type: str = "study"
```

`Note(**data)`로 만들 때 타입이 맞지 않으면 `ValidationError`가 발생한다. 문자열 `"2026-07-03"`은 자동으로 `date` 객체로 변환된다.

### 변환과 검증의 경계

헷갈렸던 점: Pydantic은 기본적으로 "변환 가능하면 변환"한다(lax 모드). 예를 들어 `int` 필드에 `"3"`을 넣으면 3으로 바뀐다. 엄격하게 막고 싶으면 `strict=True`를 쓴다. zod는 기본이 엄격해서 반대로 생각하고 있었다.

## 커스텀 검증

### field_validator

필드 하나에 대한 규칙을 추가한다.

```python
from pydantic import field_validator

class Note(BaseModel):
    tags: list[str]

    @field_validator("tags")
    @classmethod
    def lower_tags(cls, v):
        return [t.strip().lower() for t in v]
```

### model_validator

여러 필드를 함께 봐야 할 때 쓴다. 예를 들어 `source_type`이 `research`면 `approved` 필드가 반드시 있어야 한다는 규칙.

## 직렬화

- `model.model_dump()`: dict로 변환
- `model.model_dump_json()`: JSON 문자열로 변환
- `exclude`, `include`로 필드를 고를 수 있다.

v1에서 쓰던 `.dict()`, `.json()`은 v2에서 이름이 바뀌었다. 인터넷 예제가 섞여 있어서 버전을 꼭 확인해야 한다.

## LLM 구조화 출력 검증에 쓰기

이번 프로젝트에서 Pydantic이 특히 중요한 이유다. 로컬 LLM에게 JSON으로 답하라고 해도 가끔 필드를 빼먹거나 형식을 틀린다. 응답을 모델로 검증하고 실패하면 다시 요청하는 구조를 만든다.

```python
class Extracted(BaseModel):
    topics: list[str]
    summary: str = Field(max_length=300)

schema = Extracted.model_json_schema()  # 프롬프트나 response_format에 전달

for attempt in range(3):
    raw = call_llm(prompt, schema)
    try:
        result = Extracted.model_validate_json(raw)
        break
    except ValidationError as e:
        prompt += f"\n이전 출력 오류: {e}"
```

`model_json_schema()`로 JSON Schema를 뽑아서 LLM 쪽 `response_format`에 넘길 수 있다는 게 편하다. 도구 호출 노트에서 다룬 함수 파라미터 스키마도 같은 방식으로 만들 수 있다.

## 설정 관리

`pydantic-settings`의 `BaseSettings`를 상속하면 환경변수에서 값을 읽어 타입까지 검증해 준다. `LLM_BASE_URL`, `EMBED_BASE_URL`, `DATABASE_URL`을 여기서 관리하면 맥북과 맥미니 설정 차이를 `.env` 파일로만 처리할 수 있다.

## 느낀 점

타입 힌트가 문서이자 검증 규칙이자 API 스키마가 된다는 점이 좋다. 프론트에서 zod 스키마와 TS 타입을 따로 관리하던 번거로움이 여기서는 하나로 합쳐진다.
