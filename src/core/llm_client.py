"""LLM client with retry logic, parallel calls, and ReACT pattern support."""

import asyncio
import json
import time
from typing import Any, Optional, Literal, Dict, List, Union
from dataclasses import dataclass, field
from collections import defaultdict

import httpx
from openai import OpenAI, AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from rich.console import Console

from src.core.config import get_settings

console = Console()


@dataclass
class UsageStats:
    """Track API usage and costs."""

    total_requests: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    requests_by_model: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: int = 0

    def update(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float = 0.0
    ) -> None:
        """Update usage statistics."""
        self.total_requests += 1
        self.requests_by_model[model] += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_cost += cost

    def report(self) -> str:
        """Generate usage report."""
        return (
            f"Usage Stats:\n"
            f"  Total Requests: {self.total_requests}\n"
            f"  Total Tokens: {self.total_tokens:,} "
            f"(Prompt: {self.prompt_tokens:,}, Completion: {self.completion_tokens:,})\n"
            f"  Total Cost: ${self.total_cost:.4f}\n"
            f"  Errors: {self.errors}\n"
            f"  By Model: {dict(self.requests_by_model)}"
        )


@dataclass
class Message:
    """Chat message structure."""

    role: Literal["system", "user", "assistant"]
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to OpenAI format."""
        return {"role": self.role, "content": self.content}


@dataclass
class ReACTStep:
    """Single ReACT (Reasoning + Acting) step."""

    thought: str
    action: str
    observation: str
    reflection: Optional[str] = None


class LLMClient:
    """LLM client supporting multiple providers with robust retry logic."""

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """Initialize LLM client.

        Args:
            provider: LLM provider (openai, deepseek, qwen)
            model: Model name (uses default from settings if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.settings = get_settings()
        self.provider = provider.lower()
        self.model = model or self.settings.default_model
        self.temperature = temperature
        self.max_tokens = max_tokens or self.settings.max_tokens_per_request

        # Get API credentials
        api_key = self.settings.get_api_key(self.provider)
        if not api_key:
            console.print(
                f"[yellow]Warning: No API key found for {self.provider}. "
                f"Set {self.provider.upper()}_API_KEY environment variable.[/yellow]"
            )

        base_url = self.settings.get_base_url(self.provider)

        # Initialize clients
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Usage tracking
        self.usage_stats = UsageStats()

        # Rate limiting
        self._request_times: List[float] = []

    def _check_rate_limit(self) -> None:
        """Check and enforce rate limits."""
        now = time.time()
        # Remove requests older than 1 minute
        self._request_times = [t for t in self._request_times if now - t < 60]

        if len(self._request_times) >= self.settings.max_requests_per_minute:
            sleep_time = 60 - (now - self._request_times[0])
            if sleep_time > 0:
                console.print(
                    f"[yellow]Rate limit reached. Sleeping for {sleep_time:.1f}s...[/yellow]"
                )
                time.sleep(sleep_time)
                self._request_times = []

        self._request_times.append(now)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError)),
    )
    def chat(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send chat completion request with retry logic.

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional arguments for the API

        Returns:
            Assistant's response content
        """
        self._check_rate_limit()

        # Convert Message objects to dicts
        if messages and isinstance(messages[0], Message):
            messages = [msg.to_dict() for msg in messages]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs
            )

            # Update usage stats
            usage = response.usage
            if usage:
                self.usage_stats.update(
                    model=self.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )

            return response.choices[0].message.content

        except Exception as e:
            self.usage_stats.errors += 1
            console.print(f"[red]Error in chat completion: {e}[/red]")
            raise

    async def achat(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Async chat completion.

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional arguments for the API

        Returns:
            Assistant's response content
        """
        # Convert Message objects to dicts
        if messages and isinstance(messages[0], Message):
            messages = [msg.to_dict() for msg in messages]

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs
            )

            # Update usage stats
            usage = response.usage
            if usage:
                self.usage_stats.update(
                    model=self.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )

            return response.choices[0].message.content

        except Exception as e:
            self.usage_stats.errors += 1
            console.print(f"[red]Error in async chat completion: {e}[/red]")
            raise

    async def parallel_chat(
        self,
        message_lists: List[Union[List[Message], List[Dict[str, str]]]],
        **kwargs
    ) -> List[str]:
        """Execute multiple chat requests in parallel.

        Args:
            message_lists: List of message lists
            **kwargs: Additional arguments for the API

        Returns:
            List of responses
        """
        tasks = [self.achat(messages, **kwargs) for messages in message_lists]
        return await asyncio.gather(*tasks)

    def ensemble_vote(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        n: int = 3,
        **kwargs
    ) -> tuple:
        """Get multiple responses and return most common (ensemble voting).

        Args:
            messages: List of messages
            n: Number of responses to generate
            **kwargs: Additional arguments for the API

        Returns:
            Tuple of (most_common_response, all_responses)
        """
        responses = []
        for _ in range(n):
            response = self.chat(messages, **kwargs)
            responses.append(response)

        # Simple majority vote (could be more sophisticated)
        from collections import Counter
        vote_counts = Counter(responses)
        most_common = vote_counts.most_common(1)[0][0]

        return most_common, responses

    def react_step(
        self,
        context: str,
        thought_prompt: str,
        action_prompt: str,
        observation: str,
    ) -> ReACTStep:
        """Execute a single ReACT (Reasoning + Acting) step.

        Args:
            context: Current context/state
            thought_prompt: Prompt to generate reasoning
            action_prompt: Prompt to generate action
            observation: Result of previous action

        Returns:
            ReACTStep object
        """
        # Generate thought (reasoning)
        thought_messages = [
            Message(role="system", content="You are a helpful AI assistant that thinks step by step."),
            Message(role="user", content=f"{context}\n\n{thought_prompt}")
        ]
        thought = self.chat(thought_messages, temperature=0.3)

        # Generate action
        action_messages = [
            Message(role="system", content="You are a helpful AI assistant."),
            Message(role="user", content=f"{context}\n\nThought: {thought}\n\n{action_prompt}")
        ]
        action = self.chat(action_messages, temperature=0.5)

        return ReACTStep(
            thought=thought,
            action=action,
            observation=observation,
        )

    def get_usage_report(self) -> str:
        """Get usage statistics report."""
        return self.usage_stats.report()

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.usage_stats = UsageStats()
