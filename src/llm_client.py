"""LLM client wrapper specialized for gpt-5-mini without temperature support."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Iterable, Sequence

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from .config import Settings
from .keys import APIKeyManager

logger = logging.getLogger(__name__)


Message = dict[str, str]


@dataclass(slots=True)
class LLMResponse:
    """Simple container for model outputs."""

    content: str
    reasoning: str | None = None


class MockLLM:
    """Fallback stub used when no API key is configured."""

    async def message(self, messages: Sequence[Message]) -> LLMResponse:
        joined = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        pseudo = f"[MOCKED RESPONSE]\n{joined[:512]}"
        return LLMResponse(content=pseudo)


class LLMClient:
    """High-level helper that emulates temperature via candidate sampling."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._clients: list[OpenAI | MockLLM] = []
        self._mock_mode = False

        key_manager: APIKeyManager | None = None
        if settings.api_key_file:
            try:
                key_manager = APIKeyManager(settings.api_key_file)
                logger.info(
                    "Loaded %d API keys from %s",
                    len(key_manager.records),
                    settings.api_key_file,
                )
            except (FileNotFoundError, ValueError) as exc:
                logger.warning("Unable to load API keys from file: %s", exc)

        if key_manager:
            for record in key_manager.records:
                self._clients.append(
                    OpenAI(api_key=record.key, base_url=settings.openai_base_url)
                )
        elif settings.openai_api_key:
            self._clients.append(
                OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
            )

        if not self._clients:
            logger.warning("No API keys configured; falling back to MockLLM.")
            self._clients.append(MockLLM())
            self._mock_mode = True

    async def aresponse(self, messages: Sequence[Message]) -> LLMResponse:
        """Async interface for orchestration code."""

        if self._mock_mode:
            mock = self._clients[0]
            assert isinstance(mock, MockLLM)
            return await mock.message(messages)

        loop = asyncio.get_running_loop()
        tasks = []
        for idx in range(self.settings.candidate_count):
            client = self._clients[idx % len(self._clients)]
            tasks.append(loop.run_in_executor(None, self._call_with_client, client, messages))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses: list[LLMResponse] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("LLM request failed: %s", result)
                continue
            responses.append(result)

        if not responses:
            raise RuntimeError("All parallel LLM calls failed.")

        return responses[0] if len(responses) == 1 else random.choice(responses)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(Exception),
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(4),
    )
    def _call_with_client(self, client: OpenAI, messages: Sequence[Message]) -> LLMResponse:
        """Blocking OpenAI call executed via a specific client."""

        response = client.responses.create(
            model=self.settings.model_name,
            input=list(messages),
            max_output_tokens=self.settings.max_output_tokens,
        )
        candidates: Iterable = response.output
        texts: list[str] = []
        reasoning_chunks: list[str] = []
        for block in candidates:
            if block.type == "message":
                for content in block.content:
                    if content.type == "output_text":
                        texts.append(content.text)
                    if content.type == "reasoning":
                        reasoning_chunks.append(content.text)

        if not texts:
            raise RuntimeError("LLM response did not include any text content.")

        reasoning_content = "\n".join(reasoning_chunks) if reasoning_chunks else None
        return LLMResponse(content=texts[-1].strip(), reasoning=reasoning_content)

