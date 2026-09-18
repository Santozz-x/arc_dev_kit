"""Google Gemini provider.

Requires `pip install arc-devkit[gemini]` (google-genai). This module's
method/type usage (Client, Content, Part.from_text/from_bytes,
GenerateContentConfig, generate_content/generate_content_stream/count_tokens)
was checked against google-genai 2.24.0's actual installed signatures — not
just documentation. NOT VALIDATED end-to-end with a real GEMINI_API_KEY /
live API call, though — no network call to Google's API has been made from
this code. Verify it works before relying on it in production.
"""

import logging
import mimetypes
from collections.abc import Iterator
from pathlib import Path

from arc_devkit.copilot.providers.base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _build_contents(self, history: list[ChatMessage]) -> list:
        from google.genai import types

        contents = []
        for msg in history:
            role = "model" if msg.role == "assistant" else "user"
            parts = [types.Part.from_text(text=msg.content)]
            if msg.image_path and msg.role == "user":
                mime, _ = mimetypes.guess_type(msg.image_path)
                data = Path(msg.image_path).read_bytes()
                parts.append(types.Part.from_bytes(data=data, mime_type=mime or "image/png"))
            contents.append(types.Content(role=role, parts=parts))
        return contents

    def ask(self, system: str, history: list[ChatMessage], max_tokens: int) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=self._build_contents(history),
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=max_tokens
            ),
        )
        return response.text or ""

    def ask_stream(self, system: str, history: list[ChatMessage], max_tokens: int) -> Iterator[str]:
        from google.genai import types

        stream = self.client.models.generate_content_stream(
            model=self.model,
            contents=self._build_contents(history),
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=max_tokens
            ),
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    def count_tokens(self, system: str, prompt: str) -> int:
        try:
            response = self.client.models.count_tokens(model=self.model, contents=prompt)
            return response.total_tokens or 0
        except Exception as exc:
            logger.debug("Gemini count_tokens unavailable: %s", exc)
            return 0
