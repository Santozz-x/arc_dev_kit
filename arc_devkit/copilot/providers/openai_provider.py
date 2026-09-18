"""OpenAI (GPT) provider.

Requires `pip install arc-devkit[openai]` (openai). Method/parameter usage
(chat.completions.create with messages/model/max_tokens/stream) was checked
against the installed openai SDK's actual signature — not just
documentation. NOT VALIDATED end-to-end with a real OPENAI_API_KEY / live
API call. Verify it works before relying on it in production.
"""

import base64
import logging
import mimetypes
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from arc_devkit.copilot.providers.base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)


def _data_uri(image_path: str) -> str:
    mime, _ = mimetypes.guess_type(image_path)
    data = base64.standard_b64encode(Path(image_path).read_bytes()).decode()
    return f"data:{mime or 'image/png'};base64,{data}"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _build_messages(self, system: str, history: list[ChatMessage]) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system}]
        for msg in history:
            if msg.image_path and msg.role == "user":
                content: list[dict] | str = [
                    {"type": "text", "text": msg.content},
                    {"type": "image_url", "image_url": {"url": _data_uri(msg.image_path)}},
                ]
            else:
                content = msg.content
            messages.append({"role": msg.role, "content": content})
        return messages

    def ask(self, system: str, history: list[ChatMessage], max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(system, history),  # type: ignore[arg-type]
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def ask_stream(self, system: str, history: list[ChatMessage], max_tokens: int) -> Iterator[str]:
        from openai import Stream
        from openai.types.chat import ChatCompletionChunk

        stream = cast(
            "Stream[ChatCompletionChunk]",
            self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(system, history),  # type: ignore[arg-type]
                max_tokens=max_tokens,
                stream=True,
            ),
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
