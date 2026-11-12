---
date: 2026-06-29
source_type: study
tags: [python, async, concurrency]
---

# Python async/await 이해하기

JavaScript의 `async/await`는 매일 쓰는데, Python의 것은 비슷해 보이면서 미묘하게 달라서 정리가 필요했다. 특히 FastAPI에서 LLM 서버를 호출할 때 제대로 써야 한다.

## 이벤트 루프와 코루틴

### JS와 비슷한 점

- 둘 다 단일 스레드 이벤트 루프 위에서 동작한다.
- `await`에서 제어권을 이벤트 루프에 돌려주고, 그 사이 다른 작업이 진행된다.
- I/O 대기가 많은 작업(HTTP 호출, DB 쿼리)에 효과적이다.

### JS와 다른 점

JS에서는 `async` 함수를 호출하면 바로 실행이 시작되고 Promise가 반환된다. Python에서는 `async def` 함수를 호출하면 코루틴 객체만 만들어지고 **실행되지 않는다**. `await`하거나 태스크로 등록해야 실행된다.

```python
async def fetch():
    return 1

fetch()          # 아무 일도 안 일어남. 경고만 뜬다
await fetch()    # 실제 실행
```

처음에 이걸 몰라서 함수를 불렀는데 아무 로그도 안 찍혀 한참 헤맸다. 또 JS는 브라우저나 Node가 이벤트 루프를 항상 돌리고 있지만, Python 스크립트에서는 `asyncio.run(main())`으로 직접 루프를 시작해야 한다.

## 동시에 여러 작업 실행하기

### asyncio.gather

`Promise.all`에 해당한다.

```python
import asyncio, httpx

async def embed_all(texts):
    async with httpx.AsyncClient() as client:
        tasks = [client.post(EMBED_URL, json={"input": t}) for t in texts]
        return await asyncio.gather(*tasks)
```

### 동시 실행 개수 제한

로컬 LLM 서버에 요청을 수백 개 동시에 보내면 메모리가 터지거나 큐가 밀린다. `asyncio.Semaphore`로 동시 실행 수를 제한한다.

```python
sem = asyncio.Semaphore(4)

async def limited(coro):
    async with sem:
        return await coro
```

## 블로킹 코드를 섞을 때의 함정

async 함수 안에서 `requests.get()`이나 `time.sleep()` 같은 동기 함수를 쓰면 그동안 이벤트 루프 전체가 멈춘다. 다른 요청도 전부 대기한다. 이게 가장 흔한 실수라고 한다.

해결 방법은 세 가지다.

1. async를 지원하는 라이브러리를 쓴다(`httpx.AsyncClient`, `asyncpg`).
2. 어쩔 수 없는 동기 코드는 `await asyncio.to_thread(func, args)`로 스레드에 넘긴다.
3. FastAPI라면 엔드포인트 자체를 `def`로 선언해서 스레드풀에서 돌게 한다.

## CPU 작업에는 안 맞는다

async는 I/O 대기를 겹치는 기술이지 CPU 계산을 빠르게 하는 기술이 아니다. 임베딩 벡터의 대량 유사도 계산 같은 CPU 작업은 GIL 때문에 스레드로도 병렬화가 잘 안 된다. 이런 건 NumPy처럼 내부가 C로 된 라이브러리에 맡기거나, 별도 프로세스나 작업 큐로 보낸다. 작업 큐는 백그라운드 작업 노트에 정리했다.

## 정리

- 코루틴은 await해야 실행된다.
- 동시 실행은 `gather`, 개수 제한은 `Semaphore`.
- async 안에서 동기 블로킹 호출 금지.
- I/O 바운드에는 async, CPU 바운드에는 프로세스나 작업 큐.
