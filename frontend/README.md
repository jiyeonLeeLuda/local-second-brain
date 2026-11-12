# frontend — 스터디 Q&A

Local Second Brain의 웹 UI입니다. Next.js(App Router) + TypeScript, 외부 UI 라이브러리 없이 CSS Modules만 사용합니다.

## 실행

```bash
cd frontend
npm install
cp .env.example .env.local   # 필요하면 BACKEND_URL 수정 (기본 http://localhost:8000)
npm run dev                  # http://localhost:3000
```

백엔드(FastAPI, `backend/`)가 먼저 떠 있어야 합니다.
브라우저는 같은 origin의 `/api/*`만 호출하고, `next.config.ts`의 rewrites가 `BACKEND_URL`로 프록시합니다(CORS 설정 불필요).
rewrites 대상은 빌드 시점에 고정되므로 `BACKEND_URL`을 바꾸면 dev 서버 재시작 / `npm run build` 재실행이 필요합니다.

| 스크립트 | 내용 |
|---|---|
| `npm run dev` | 개발 서버 |
| `npm run build && npm start` | 프로덕션 빌드/실행 |
| `npm run lint` | ESLint (next core-web-vitals + typescript) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | 인용 파서 단위 테스트 (`node:test`, Node 22.18+의 타입 스트리핑 사용, 추가 의존성 없음) |

## 기능

- **질문하기**: `POST /api/ask`. 답변 속 `[n]` 인용을 누르면 해당 출처 카드로 스크롤·강조·펼침. 본문에서 인용되지 않은 출처는 흐리게 표시, 출처 목록에 없는 번호는 링크 없이 원문 그대로 둠
- **검색만**: `GET /api/search`. LLM 없이 청크만 나열
- **상태 표시줄**: `/api/health`, `/api/stats` (백엔드·DB 상태, 노트/청크 수, LLM 서버 주소) + **다시 인덱싱**(`POST /api/ingest`, `source_type: "study"`) 결과 요약
- 503(모델 서버 연결 불가) 등 오류는 백엔드의 `detail`을 그대로 보여줌. `⌘/Ctrl + Enter`로 제출, 진행 중 요청 취소 가능

## 구조

```
src/
  app/                 layout, page(서버 컴포넌트), 전역 CSS 토큰(라이트/다크)
  lib/api/             타입이 지정된 API 클라이언트(types.ts, client.ts)
  lib/citations.ts     답변의 [1], [1, 2], [1-3] 인용 파싱 (+ .test.ts)
  hooks/               useRequest(로딩/에러/abort), useElapsedSeconds
  components/          StudyWorkspace, QuestionForm, ModeTabs, AnswerPanel,
                       SourceCard, SearchResults, StatusBar, ErrorNotice
```
