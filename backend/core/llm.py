"""Unified async LLM client (Anthropic Claude Messages API via httpx).

One client instance is shared by all services — nodes must never create
their own SDK clients. API keys come from the environment only.
"""

import asyncio
import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_RETRIES = 3
REQUEST_TIMEOUT = 60.0
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class LLMError(Exception):
    pass


class LLMUnavailableError(LLMError):
    """No API key configured — caller must degrade gracefully."""


def extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a model response."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise LLMError("模型响应中未找到 JSON")


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = REQUEST_TIMEOUT,
        max_tokens: int = 2048,
    ) -> None:
        if not api_key:
            raise LLMUnavailableError("ANTHROPIC_API_KEY 未配置")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._timeout = timeout

    async def complete(self, prompt: str, system: str | None = None) -> str:
        return await self.complete_messages(prompt, system)

    async def complete_messages(self, content: str | list[dict], system: str | None = None) -> str:
        """Send a user message (text or multimodal content blocks)."""
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            body["system"] = system
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    resp = await client.post(ANTHROPIC_URL, json=body, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("content", [])
                    return "".join(part.get("text", "") for part in content)
                except (httpx.HTTPError, KeyError, TypeError) as exc:
                    last_error = exc
                    logger.warning("LLM request failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(1.0 * 2 ** (attempt - 1))
        raise LLMError(f"LLM 连续 {MAX_RETRIES} 次调用失败: {last_error}")

    async def complete_structured(self, prompt: str, schema: type[T], system: str | None = None) -> T:
        text = await self.complete(prompt, system)
        try:
            return schema.model_validate(extract_json(text))
        except (json.JSONDecodeError, ValidationError, LLMError) as exc:
            raise LLMError(f"LLM 结构化输出解析失败: {exc}") from exc


class FakeLLMClient:
    """Deterministic offline client used by tests and the demo mode.

    Returns a canned JSON payload; `canned` can be overridden per use case.
    """

    def __init__(self, canned: dict[str, Any] | None = None) -> None:
        self.canned = canned or {}

    async def complete(self, prompt: str, system: str | None = None) -> str:
        return json.dumps(self.canned, ensure_ascii=False)

    async def complete_messages(self, content: str | list[dict], system: str | None = None) -> str:
        return json.dumps(self.canned, ensure_ascii=False)

    async def complete_structured(self, prompt: str, schema: type[T], system: str | None = None) -> T:
        return schema.model_validate(self.canned)


def build_llm_from_settings(settings) -> LLMClient | FakeLLMClient | None:
    """Real client when a key is configured; None means "run without LLM"."""
    if settings.ANTHROPIC_API_KEY:
        return LLMClient(api_key=settings.ANTHROPIC_API_KEY, model=settings.ANTHROPIC_MODEL)
    return None
