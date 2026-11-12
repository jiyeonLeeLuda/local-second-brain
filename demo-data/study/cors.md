---
date: 2026-06-21
source_type: study
tags: [cors, browser, security, http]
---

# CORS 제대로 이해하기

프론트엔드 개발자라면 누구나 콘솔에서 빨간 CORS 에러를 본 적이 있을 것이다. 나는 그동안 "백엔드에 헤더 열어 달라고 하면 된다"로 끝냈다. 이번에 FastAPI 서버와 Next.js 개발 서버를 따로 띄우면서 직접 해결해야 해서 정리한다.

## 동일 출처 정책부터

브라우저는 기본적으로 다른 출처(origin)로의 요청 결과를 JS가 읽지 못하게 막는다. 출처는 `scheme + host + port` 조합이다.

- `http://localhost:3000`과 `http://localhost:8000`은 포트가 달라서 다른 출처다.
- `https://a.com`과 `http://a.com`도 다른 출처다.

CORS는 이 제한을 "서버가 허락한 경우에만" 풀어 주는 메커니즘이다.

### 오해했던 부분

CORS는 서버를 보호하는 장치가 아니다. 요청은 서버에 도착하고 서버는 처리까지 한다. 브라우저가 응답을 JS에 넘겨주지 않을 뿐이다. curl이나 서버 간 호출에는 CORS가 아예 적용되지 않는다. 그래서 CORS를 보안 수단으로 믿으면 안 되고, 인증과 권한 검사는 서버에서 따로 해야 한다.

## 단순 요청과 프리플라이트

### 단순 요청

`GET`, `HEAD`, `POST` 중 하나이고, `Content-Type`이 `text/plain`, `multipart/form-data`, `application/x-www-form-urlencoded` 중 하나면 바로 보낸다. 응답에 `Access-Control-Allow-Origin`이 맞게 있으면 JS가 읽을 수 있다.

### 프리플라이트 요청

`Content-Type: application/json`이나 `Authorization` 헤더를 붙이면 단순 요청이 아니게 된다. 브라우저는 먼저 `OPTIONS` 요청으로 허락을 묻는다.

```
OPTIONS /api/notes
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type
```

서버가 `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`로 허락하면 그다음에 진짜 요청이 간다. Network 탭에 요청이 두 번 찍히는 이유가 이거였다. `Access-Control-Max-Age`로 프리플라이트 결과를 캐시할 수 있다.

## 쿠키와 자격 증명

쿠키를 함께 보내려면 양쪽 설정이 모두 필요하다.

- 클라이언트: `fetch(url, { credentials: "include" })`
- 서버: `Access-Control-Allow-Credentials: true`
- 이때 `Access-Control-Allow-Origin`에 `*`를 쓸 수 없다. 정확한 출처를 적어야 한다.

이것 때문에 한참 헤맸다. 와일드카드를 써 놓고 쿠키가 안 간다고 고민했었다.

## FastAPI에서 설정하기

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

운영 환경에서는 허용 출처를 환경변수로 받는다.

## 개발 서버 프록시라는 대안

Next.js의 rewrites로 `/api/*`를 백엔드로 넘기면 브라우저 입장에서는 같은 출처라 CORS 자체가 생기지 않는다. 개발 편의로는 이 방법이 가장 간단하다. 다만 운영 구조와 다르면 배포 때 다시 문제가 생기니, 처음부터 같은 구조로 맞추는 게 좋겠다고 생각했다.
