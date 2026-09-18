"""Anthropic (Claude) provider — the default, and the only one that backs
DevCopilot.run_agent()'s tool-use loop today (see supports_tools)."""

import base64
import logging
import mimetypes
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import anthropic
from anthropic.types import MessageParam, TextBlock

from arc_devkit.copilot.providers.base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)

_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _build_image_block(image_path: str) -> dict:
    path = Path(image_path)
    mime, _ = mimetypes.guess_type(str(path))
    if mime not in _SUPPORTED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type '{mime}'. Supported: {_SUPPORTED_IMAGE_TYPES}")
    data = base64.standard_b64encode(path.read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _build_messages(self, history: list[ChatMessage]) -> list[dict]:
        messages = []
        for msg in history:
            if msg.image_path and msg.role == "user":
                content: list[dict] | str = [
                    _build_image_block(msg.image_path),
                    {"type": "text", "text": msg.content},
                ]
            else:
                content = msg.content
            messages.append({"role": msg.role, "content": content})
        return messages

    def ask(self, system: str, history: list[ChatMessage], max_tokens: int) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=cast(list[MessageParam], self._build_messages(history)),
        )
        text_blocks = [b for b in message.content if isinstance(b, TextBlock)]
        return text_blocks[0].text if text_blocks else ""

    def ask_stream(self, system: str, history: list[ChatMessage], max_tokens: int) -> Iterator[str]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=cast(list[MessageParam], self._build_messages(history)),
        ) as stream:
            yield from stream.text_stream

    def count_tokens(self, system: str, prompt: str) -> int:
        response = self.client.messages.count_tokens(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.input_tokens

    @property
    def supports_tools(self) -> bool:
        return True
