import json
import math

import httpx
import pytest

from app.config import Settings
from app.llm.chat import OpenAIChat, strip_thinking
from app.llm.embeddings import HashEmbedder, OpenAIEmbedder
from app.llm.errors import ModelServerError


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_hash_embedder_is_deterministic_and_normalized():
    e = HashEmbedder(256)
    v1, v2 = e.embed(["B-tree 인덱스", "B-tree 인덱스"])
    assert v1 == v2
    assert math.isclose(sum(x * x for x in v1), 1.0, rel_tol=1e-9)


def test_hash_embedder_prefers_lexical_overlap():
    e = HashEmbedder(1024)
    q, near, far = e.embed(["인덱스는 언제 쓰나", "인덱스를 쓰는 경우", "도커 컨테이너 네트워크"])
    assert _cos(q, near) > _cos(q, far)


def test_hash_embedder_never_returns_zero_vector():
    assert any(HashEmbedder(64).embed(["!!!"])[0])


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, embed_dim=3, embed_batch_size=2, **kw)


def _client(handler) -> httpx.Client:
    return httpx.Client(base_url="http://model.test/v1/", transport=httpx.MockTransport(handler))


def test_openai_embedder_batches_and_orders_by_index():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["input"])
        data = [
            {"index": i, "embedding": [float(len(t)), 0.0, 1.0]}
            for i, t in enumerate(body["input"])
        ]
        return httpx.Response(200, json={"data": list(reversed(data))})

    e = OpenAIEmbedder(_settings(), client=_client(handler))
    out = e.embed(["a", "bb", "ccc"])
    assert calls == [["a", "bb"], ["ccc"]]
    assert [v[0] for v in out] == [1.0, 2.0, 3.0]


def test_openai_embedder_rejects_wrong_dimension():
    def handler(request):
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1] * 5}]})

    e = OpenAIEmbedder(_settings(), client=_client(handler))
    with pytest.raises(ModelServerError, match="EMBED_DIM"):
        e.embed(["x"])


def test_openai_embedder_wraps_connection_errors():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ModelServerError):
        OpenAIEmbedder(_settings(), client=_client(handler)).embed(["x"])


def test_chat_disables_thinking_and_strips_reasoning():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        content = "<think>hmm</think>\n답변 [1]"
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    chat = OpenAIChat(_settings(llm_model="m"), client=_client(handler))
    assert chat.complete([{"role": "user", "content": "질문"}]) == "답변 [1]"
    assert seen["model"] == "m"
    assert seen["chat_template_kwargs"] == {"enable_thinking": False}
    assert seen["messages"][-1]["content"] == "질문"


def test_chat_http_error_becomes_model_server_error():
    chat = OpenAIChat(_settings(), client=_client(lambda r: httpx.Response(500, json={})))
    with pytest.raises(ModelServerError):
        chat.complete([{"role": "user", "content": "x"}])


def test_strip_thinking_when_open_tag_missing():
    assert strip_thinking("reasoning...</think>\n\n최종 답") == "최종 답"


def test_query_instruction_is_added_to_queries_only():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.extend(body["input"])
        return httpx.Response(
            200,
            json={
                "data": [{"index": i, "embedding": [1.0, 0, 0]} for i in range(len(body["input"]))]
            },
        )

    e = OpenAIEmbedder(_settings(embed_query_instruction="Q: "), client=_client(handler))
    e.embed(["passage"])
    e.embed_query("question")
    assert seen == ["passage", "Q: question"]
