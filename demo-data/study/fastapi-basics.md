---
date: 2026-06-25
source_type: study
tags: [fastapi, python, backend]
---

# FastAPI 기초

백엔드 프레임워크로 FastAPI를 고른 이유는 타입 힌트 기반이라 TypeScript에 익숙한 나에게 친숙하고, OpenAPI 문서가 자동으로 생기기 때문이다. 첫 주에 익힌 내용을 정리한다.

## 최소 예제

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
```

`uvicorn main:app --reload`로 실행하면 `/docs`에서 Swagger UI가 바로 열린다. 프론트엔드 개발자에게 이 화면은 정말 반갑다. 백엔드 동료에게 "이 API 응답 형식이 뭐예요?"라고 물을 필요가 없어진다.

## 경로 파라미터와 쿼리 파라미터

함수 인자 선언만으로 어디서 값을 가져올지 결정된다.

```python
@app.get("/notes/{note_id}")
def get_note(note_id: int, include_chunks: bool = False):
    ...
```

- `note_id`는 경로에 있으니 경로 파라미터다.
- `include_chunks`는 경로에 없고 기본값이 있으니 쿼리 파라미터다.
- 타입이 `int`라서 `/notes/abc`로 요청하면 자동으로 422 응답이 나간다.

헷갈렸던 점: 검증 실패 시 400이 아니라 422가 기본이다. 프론트에서 에러 처리할 때 422 응답 바디의 `detail` 배열 구조를 알아 두면 폼 에러 표시에 바로 쓸 수 있다.

## 요청 바디와 응답 모델

바디는 Pydantic 모델로 선언한다. Pydantic 자체는 별도 노트에 자세히 정리했다.

```python
from pydantic import BaseModel

class NoteCreate(BaseModel):
    title: str
    body: str

class NoteOut(BaseModel):
    id: int
    title: str

@app.post("/notes", response_model=NoteOut, status_code=201)
def create_note(payload: NoteCreate):
    ...
```

`response_model`을 지정하면 반환 값에서 모델에 없는 필드는 걸러진다. 내부 필드(예: 원본 파일 경로)가 실수로 노출되는 걸 막는 장치가 된다.

## 의존성 주입

### Depends의 쓰임새

FastAPI에서 제일 신기했던 기능이다. 함수 인자에 `Depends(함수)`를 쓰면 요청마다 그 함수를 먼저 실행해서 결과를 넘겨준다.

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/notes")
def list_notes(db = Depends(get_db)):
    ...
```

`yield`를 쓰면 요청이 끝난 뒤 정리 코드(`finally`)가 실행된다. DB 세션, 현재 사용자 확인, 설정 객체 주입 등에 쓴다. React의 Context나 커스텀 훅으로 공통 로직을 꺼내 쓰던 감각과 비슷하다.

### 테스트에서의 장점

`app.dependency_overrides[get_db] = fake_db`처럼 의존성을 바꿔 끼울 수 있어서 테스트가 쉬워진다. pytest 노트에서 이 부분을 다시 다뤘다.

## 라우터 분리

파일이 커지면 `APIRouter`로 나눈다.

```python
router = APIRouter(prefix="/notes", tags=["notes"])
app.include_router(router)
```

## sync 함수와 async 함수

`def`로 선언하면 FastAPI가 스레드풀에서 실행하고, `async def`로 선언하면 이벤트 루프에서 실행한다. async 안에서 블로킹 함수(예: 동기 DB 드라이버, `time.sleep`)를 부르면 서버 전체가 멈출 수 있다. 이건 async/await 노트에서 더 깊게 파 봤다.

## 다음 할 일

- 에러 응답 형식을 REST 설계 노트에서 정한 형태로 통일하는 예외 핸들러 작성
- 설정을 `pydantic-settings`로 환경변수에서 읽기(`LLM_BASE_URL` 등)
