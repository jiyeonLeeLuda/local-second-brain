---
date: 2026-06-05
source_type: study
tags: [http, caching, performance]
---

# HTTP 캐싱 정리

새로고침했는데 예전 화면이 보이는 버그를 겪고 나서 HTTP 캐싱을 제대로 공부했다. 프론트엔드 빌드 파일에 해시를 붙이는 이유도 결국 여기서 출발한다.

## 캐시가 저장되는 곳

- 브라우저 캐시: 사용자 한 명만 쓰는 private 캐시
- CDN, 프록시: 여러 사용자가 공유하는 shared 캐시
- 서버 내부 캐시: Redis 같은 애플리케이션 캐시(이건 HTTP 캐싱과는 별개라서 Redis 노트에 따로 정리)

HTTP 캐싱은 앞의 두 가지를 응답 헤더로 제어하는 규칙이다.

## Cache-Control 헤더

### 주요 지시어

- `max-age=60`: 60초 동안은 서버에 묻지 않고 저장된 응답을 그대로 쓴다.
- `no-cache`: 저장은 해도 되지만 쓰기 전에 매번 서버에 검증해야 한다.
- `no-store`: 아예 저장하지 마라. 민감 정보에 쓴다.
- `private` / `public`: 공유 캐시에 저장해도 되는지.
- `immutable`: 유효 기간 안에는 절대 안 바뀌니 재검증도 하지 마라.

헷갈렸던 점: `no-cache`가 "캐시하지 마라"가 아니었다. 이름과 의미가 다르다. 진짜 저장을 막는 건 `no-store`다.

### 빌드 파일 전략

```
index.html          Cache-Control: no-cache
assets/app.3f9a1c.js  Cache-Control: public, max-age=31536000, immutable
```

HTML은 매번 검증하고, 파일명에 콘텐츠 해시가 들어간 JS/CSS는 1년 동안 캐시한다. 내용이 바뀌면 파일명이 바뀌니까 오래 캐시해도 문제가 없다. Next.js가 `_next/static` 아래 파일에 이렇게 해 주는 이유를 이제 알겠다.

## 조건부 요청과 재검증

유효 기간이 지나면 브라우저는 무조건 새로 받는 게 아니라 "바뀐 게 있으면 줘"라고 묻는다.

### ETag와 If-None-Match

서버가 응답에 `ETag: "abc123"`를 붙여 주면, 다음 요청에서 브라우저가 `If-None-Match: "abc123"`를 보낸다. 내용이 같으면 서버는 바디 없이 `304 Not Modified`만 돌려준다. 전송량이 확 줄어든다.

### Last-Modified와 If-Modified-Since

시간 기반 버전이다. 초 단위라서 정밀도가 떨어지므로 보통 ETag를 더 선호한다.

## Vary 헤더

같은 URL이라도 `Accept-Language`나 `Accept-Encoding`에 따라 응답이 다르면 `Vary`로 알려줘야 한다. 안 그러면 CDN이 한국어 사용자에게 영어 페이지를 줄 수도 있다. 쿠키나 `Authorization`에 따라 달라지는 응답은 애초에 `private`으로 두는 편이 안전하다.

## API 응답에도 캐싱을 쓸까

로컬 노트 앱 백엔드를 만들면서 고민했다. 노트 목록 API는 자주 바뀌니 `no-cache` + ETag가 적당해 보인다. 반면 임베딩 모델 정보처럼 거의 안 바뀌는 응답은 `max-age`를 길게 줘도 된다. 다만 개인 데이터는 반드시 `private`. 공유 캐시에 남으면 곤란하다.

## 정리

1. 저장 여부는 `no-store`, 매번 검증은 `no-cache`.
2. 해시 붙은 정적 파일은 길게, HTML은 짧게.
3. 304는 실패가 아니라 "그대로 써도 된다"는 신호다.
