"""Minimal OpenAI-compatible chat client (no SDK, so any local server works)."""

import re
from typing import Protocol

import httpx

from app.config import Settings
from app.llm.errors import ModelServerError

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    """Qwen3-style reasoning blocks are not part of the answer."""
    text = _THINK.sub("", text)
    if "</think>" in text:  # opening tag consumed by the server's chat template
        text = text.split("</think>", 1)[1]
    return text.strip()


class ChatModel(Protocol):
    model_name: str

    def complete(self, messages: list[dict], temperature: float = 0.2) -> str: ...


class OpenAIChat:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.model_name = settings.llm_model
        self.disable_thinking = settings.llm_disable_thinking
        self._client = client or httpx.Client(
            base_url=settings.llm_base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=settings.llm_timeout_s,
        )

    def complete(self, messages: list[dict], temperature: float = 0.2) -> str:
        body: dict = {"model": self.model_name, "messages": messages, "temperature": temperature}
        if self.disable_thinking:
            # Honored by llama.cpp-based servers (Lemonade, llama-server) with --jinja.
            # Qwen3.5 ignores the "/no_think" text switch, so this is the reliable way:
            # measured on the Mac mini, a one-line answer went from 68s to 2.7s.
            body["chat_template_kwargs"] = {"enable_thinking": False}
        try:
            resp = self._client.post("chat/completions", json=body)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise ModelServerError(f"chat request failed: {exc}") from exc
        return strip_thinking(content)


def make_chat(settings: Settings) -> ChatModel:
    return OpenAIChat(settings)
