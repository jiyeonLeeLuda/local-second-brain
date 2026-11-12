---
date: 2026-11-10
source_type: study
tags: [llm, local-llm, llama-cpp, inference, ai]
---

# 로컬 LLM 서빙: llama.cpp와 OpenAI 호환 API

클라우드 API 대신 맥미니에서 직접 모델을 돌리기로 했다. 개인 기록을 외부로 보내지 않기 위해서다. 로컬 추론 서버의 구조와 고를 때 볼 것들을 정리했다.

## 추론 서버의 역할

모델 파일(가중치)을 메모리에 올려 두고, HTTP 요청을 받아 토큰을 생성해 돌려주는 프로그램이다. 대표적인 선택지는 다음과 같다.

- llama.cpp의 `llama-server`: C/C++로 된 추론 엔진. 애플 실리콘에서는 Metal로 GPU를 쓴다.
- Ollama: llama.cpp 기반에 모델 관리 기능을 얹은 도구.
- LM Studio: GUI가 있는 데스크톱 앱. 서버 모드도 있다.
- Lemonade: 여러 백엔드를 묶은 로컬 서버. macOS 지원은 llama.cpp Metal 기반이다.

## GGUF와 양자화

### 모델 파일 형식

llama.cpp 계열은 GGUF 형식의 모델 파일을 쓴다. 가중치와 토크나이저, 채팅 템플릿 정보가 한 파일에 들어 있다.

### 양자화 수준 고르기

원래 16비트인 가중치를 4~8비트로 줄여 메모리를 아낀다. 파일 이름의 `Q4_K_M`, `Q8_0` 같은 표기가 양자화 방식이다.

- 8B 모델 기준 16비트는 약 16GB, Q4 계열은 약 5GB 정도다.
- 비트를 줄일수록 메모리와 속도는 좋아지고 품질은 조금씩 떨어진다.
- Q4_K_M이 품질과 크기의 균형점으로 많이 쓰인다.

헷갈렸던 점: 모델 파일 크기만 보고 메모리가 충분하다고 생각했는데, 실제로는 KV 캐시(대화 문맥을 담는 메모리)가 추가로 필요하다. 컨텍스트 길이를 늘리면 KV 캐시가 비례해서 커진다. 24GB 통합 메모리에서 생성 모델 2개와 임베딩 모델을 동시에 띄우려면 컨텍스트 길이를 신중하게 정해야 한다.

## OpenAI 호환 API

### 왜 중요한가

대부분의 로컬 서버가 OpenAI API와 같은 경로와 형식을 제공한다.

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-8b", "messages": [{"role": "user", "content": "안녕"}]}'

curl http://localhost:8080/v1/embeddings \
  -d '{"model": "bge-m3", "input": ["첫 문장", "두 번째 문장"]}'

curl http://localhost:8080/v1/models
```

덕분에 앱 코드는 `base_url`만 바꾸면 llama-server, Ollama, Lemonade, 클라우드 API를 자유롭게 오갈 수 있다. 환경변수 `LLM_BASE_URL`, `EMBED_BASE_URL`로 분리한 이유다.

```python
from openai import OpenAI
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key="local")
```

### 호환이 완벽하지는 않다

- 임베딩 엔드포인트가 없거나, 별도 옵션(`--embedding`)으로 따로 띄워야 하는 서버가 있다.
- `response_format`의 JSON Schema 제약, 도구 호출 지원 여부가 서버와 모델 템플릿마다 다르다.
- 스트리밍 응답의 세부 형식이 조금씩 다를 수 있다.

그래서 서버를 바꿀 때마다 확인할 체크리스트를 만들었다: 모델 목록, 채팅, 임베딩, JSON 출력, 도구 호출, 스트리밍.

## 성능 지표

- 프롬프트 처리 속도(prefill): 입력 토큰을 읽는 속도. RAG는 프롬프트가 길어서 이게 중요하다.
- 생성 속도(tokens/s): 출력 토큰을 만드는 속도.
- 첫 토큰까지 시간(TTFT): 사용자가 체감하는 대기 시간.

## 원격 접근과 보안

추론 서버는 기본적으로 인증이 약하다. `0.0.0.0`으로 열면 같은 네트워크의 누구나 쓸 수 있다. 맥미니 서버는 localhost나 Tailscale 인터페이스에만 열고, 공유기 포트포워딩은 하지 않는다. Linux 권한 노트에서 정리한 최소 권한 원칙과 같은 맥락이다.
