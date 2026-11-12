---
date: 2026-06-17
source_type: study
tags: [auth, oauth2, oidc, security]
---

# OAuth 2.0과 OpenID Connect

"구글로 로그인" 버튼을 프론트에서 여러 번 붙여 봤지만 SDK가 다 해 줘서 내부 흐름을 몰랐다. 인증 노트에 이어서 OAuth를 정리한다.

## OAuth 2.0은 인가 프로토콜이다

가장 먼저 바로잡은 오해: OAuth 2.0은 원래 "로그인"이 아니라 "권한 위임"을 위한 규약이다. 예를 들어 내 앱이 사용자의 구글 캘린더를 읽어도 되는지 허락받는 것. 사용자는 비밀번호를 내 앱에 주지 않고, 구글이 발급한 액세스 토큰만 내 앱에 전달된다.

### 등장인물

- Resource Owner: 사용자
- Client: 내 앱
- Authorization Server: 토큰을 발급하는 서버(구글 로그인 서버)
- Resource Server: 실제 데이터를 가진 API(캘린더 API)

## Authorization Code 흐름

웹 앱에서 가장 많이 쓰는 흐름이다.

1. 클라이언트가 사용자를 인가 서버로 리다이렉트한다. `client_id`, `redirect_uri`, `scope`, `state`를 붙인다.
2. 사용자가 로그인하고 동의한다.
3. 인가 서버가 `redirect_uri`로 일회용 `code`를 붙여 돌려보낸다.
4. 클라이언트 백엔드가 `code`와 `client_secret`으로 토큰 엔드포인트에 요청해 액세스 토큰을 받는다.

```
GET /authorize?response_type=code&client_id=abc
    &redirect_uri=https://app.example/callback
    &scope=openid%20email&state=xyz123
```

### state 파라미터의 역할

`state`는 요청을 보낼 때 만든 임의 값을 콜백에서 다시 확인해서 CSRF를 막는 용도다. 처음엔 왜 필요한지 몰랐는데, 공격자가 자기 code로 피해자를 로그인시키는 공격을 막는다는 걸 알고 납득했다.

### PKCE

SPA나 모바일 앱은 `client_secret`을 안전하게 숨길 수 없다. 그래서 PKCE를 쓴다. 클라이언트가 임의의 `code_verifier`를 만들고 해시값(`code_challenge`)을 처음 요청에 보낸 뒤, 토큰 교환 때 원래 값을 보내서 같은 클라이언트임을 증명한다. 요즘은 서버 앱에도 PKCE를 권장한다.

## OpenID Connect

OAuth 위에 "이 사람이 누구인가"를 얹은 것이 OIDC다.

- `scope`에 `openid`를 넣으면 액세스 토큰과 함께 ID 토큰이 온다.
- ID 토큰은 JWT 형식이고 `sub`, `email`, `iss`, `aud` 같은 사용자 정보가 들어 있다.
- 클라이언트는 서명, `iss`(발급자), `aud`(내 client_id인지), `exp`를 반드시 검증해야 한다.

헷갈렸던 점: 액세스 토큰은 API를 부르기 위한 것이고, ID 토큰은 클라이언트가 사용자를 식별하기 위한 것이다. ID 토큰을 API 호출에 쓰면 안 된다.

## 프론트엔드 관점에서 다시 보기

예전에 SPA에서 토큰을 받아 바로 localStorage에 넣던 구조는 지금 보면 위험하다. 요즘 권장되는 구조는 BFF(Backend for Frontend) 패턴이다. 토큰 교환은 백엔드가 하고, 브라우저에는 HttpOnly 세션 쿠키만 준다. 결국 세션 vs JWT 노트에서 정리한 결론과 연결된다.

## 남은 궁금증

MCP 같은 도구 연결 프로토콜에서도 원격 서버 인증에 OAuth를 쓴다고 들었다. 도구 호출 권한을 위임하는 구조라서 개념이 그대로 이어지는 것 같다. MCP 노트를 정리할 때 다시 확인해 보기로 했다.
