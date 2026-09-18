"""Ollama provider — local/self-hosted models, no API key required.

Uses Ollama's stable REST API (/api/chat) directly via httpx — no extra SDK
dependency, since httpx is already a core arc-devkit dependency. Requires a
local (or reachable) Ollama server with the requested model already pulled
(`ollama pull <model>`); this provider does not pull models for you.
"""

import base64
import json
import logging
import mimetypes
from collections.abc import Iterator
from pathlib import Path

import httpx

from arc_devkit.copilot.providers.base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 120.0


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model

    def _build_messages(self, system: str, history: list[ChatMessage]) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system}]
        for msg in history:
            m: dict = {"role": msg.role, "content": msg.content}
            if msg.image_path and msg.role == "user":
                mimetypes.guess_type(msg.image_path)  # validate it looks like an image path
                data = base64.standard_b64encode(Path(msg.image_path).read_bytes()).decode()
                m["images"] = [data]
            messages.append(m)
        return messages

    def ask(self, system: str, history: list[ChatMessage], max_tokens: int) -> str:
        resp = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self.model,
                "messages": self._build_messages(system, history),
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data: dict = resp.json()
        content: str = data.get("message", {}).get("content", "")
        return content

    def ask_stream(self, system: str, history: list[ChatMessage], max_tokens: int) -> Iterator[str]:
        with httpx.stream(
            "POST",
            f"{self._base_url}/api/chat",
            json={
                "model": self.model,
                "messages": self._build_messages(system, history),
                "stream": True,
                "options": {"num_predict": max_tokens},
            },
            timeout=_TIMEOUT_SECONDS,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break
