"""API Key Pool Manager for parallel LLM calls with load balancing."""

import asyncio
from pathlib import Path
from typing import List, Optional
from collections import deque
from dataclasses import dataclass, field
import time

from openai import AsyncOpenAI
import httpx
from rich.console import Console
from anthropic import AsyncAnthropic

console = Console()

# 需要使用 Responses API 的模型列表
RESPONSES_API_MODELS = [
    "gpt-5.1-codex",
    "gpt-5.1-codex-mini",
    "gpt-5.1-codex-max",
]


@dataclass
class APIKeyInfo:
    """Information about a single API key."""
    
    key: str
    provider: str  # openai, qwen, etc.
    calls_count: int = 0
    last_used: float = 0.0
    errors: int = 0
    is_active: bool = True
    
    def mark_used(self):
        """Mark this key as recently used."""
        self.calls_count += 1
        self.last_used = time.time()
    
    def mark_error(self):
        """Mark an error for this key."""
        self.errors += 1
        if self.errors >= 3:  # Disable after 3 consecutive errors
            self.is_active = False
            console.print(f"[red]⚠ API key disabled due to errors: {self.key[:15]}...[/red]")


@dataclass
class APIKeyPool:
    """Pool of API keys with load balancing and rotation."""
    
    keys: List[APIKeyInfo] = field(default_factory=list)
    round_robin_index: int = 0
    
    def add_key(self, key: str, provider: str = "openai"):
        """Add a key to the pool."""
        if key and key.strip() and not key.startswith("#"):
            self.keys.append(APIKeyInfo(key=key.strip(), provider=provider))
    
    def get_next_key(self) -> Optional[APIKeyInfo]:
        """Get next available key using round-robin."""
        active_keys = [k for k in self.keys if k.is_active]
        
        if not active_keys:
            console.print("[red]✗ No active API keys available![/red]")
            return None
        
        # Round-robin selection
        key = active_keys[self.round_robin_index % len(active_keys)]
        self.round_robin_index += 1
        
        return key
    
    def get_least_used_key(self) -> Optional[APIKeyInfo]:
        """Get the least recently used active key."""
        active_keys = [k for k in self.keys if k.is_active]
        
        if not active_keys:
            return None
        
        return min(active_keys, key=lambda k: (k.calls_count, k.last_used))
    
    def get_keys_for_parallel(self, count: int) -> List[APIKeyInfo]:
        """Get multiple keys for parallel requests."""
        active_keys = [k for k in self.keys if k.is_active]
        
        if not active_keys:
            return []
        
        # Return up to 'count' keys, cycling if needed
        result = []
        for i in range(count):
            key = active_keys[i % len(active_keys)]
            result.append(key)
        
        return result
    
    @property
    def active_count(self) -> int:
        """Number of active keys."""
        return sum(1 for k in self.keys if k.is_active)
    
    @property
    def total_count(self) -> int:
        """Total number of keys."""
        return len(self.keys)
    
    def stats(self) -> str:
        """Get pool statistics."""
        if not self.keys:
            return "No API keys loaded"
        
        total_calls = sum(k.calls_count for k in self.keys)
        total_errors = sum(k.errors for k in self.keys)
        
        return (
            f"API Key Pool Stats:\n"
            f"  Total Keys: {self.total_count}\n"
            f"  Active Keys: {self.active_count}\n"
            f"  Total Calls: {total_calls}\n"
            f"  Total Errors: {total_errors}\n"
            f"  Avg Calls/Key: {total_calls / max(1, self.total_count):.1f}"
        )


class ParallelLLMManager:
    """Manager for parallel LLM API calls with multiple keys."""

    def __init__(self, settings_or_path = None):
        """Initialize parallel LLM manager.

        Args:
            settings_or_path: Either a Settings object or a Path to key file
        """
        from .config import Settings

        self.openai_pool = APIKeyPool()
        self.qwen_pool = APIKeyPool()
        self.settings = None
        self.request_timeout_seconds: float = 60.0

        # Handle Settings object or path
        if isinstance(settings_or_path, Settings):
            settings = settings_or_path
            self.settings = settings
            self.request_timeout_seconds = float(getattr(settings, "timeout_seconds", 60) or 60)
            self.openai_base_url = settings.openai_base_url
            self.qwen_base_url = settings.qwen_base_url
            # Also keep DeepSeek for model-based routing
            self.deepseek_base_url = settings.deepseek_base_url

            # Load from key files specified in settings
            if settings.openai_api_key_file:
                openai_file = Path(settings.openai_api_key_file)
                if openai_file.exists():
                    self._load_keys_from_file(openai_file, self.openai_pool, "openai")

            if settings.qwen_api_key_file:
                qwen_file = Path(settings.qwen_api_key_file)
                if qwen_file.exists():
                    self._load_keys_from_file(qwen_file, self.qwen_pool, "qwen")

            # Fallback: load single API keys from env/settings when key files are absent
            if settings.openai_api_key and self.openai_pool.total_count == 0:
                self.openai_pool.add_key(settings.openai_api_key, "openai")
            # Allow DeepSeek keys to participate via OpenAI SDK (compatible API)
            if settings.deepseek_api_key:
                # Add DeepSeek key to pool so parallel calls can use it
                self.openai_pool.add_key(settings.deepseek_api_key, "openai")
            if settings.qwen_api_key and self.qwen_pool.total_count == 0:
                self.qwen_pool.add_key(settings.qwen_api_key, "qwen")

        elif isinstance(settings_or_path, Path):
            # Legacy path-based initialization
            self.openai_base_url = "https://api.openai.com/v1"
            self.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            if settings_or_path.exists():
                self._load_keys_from_file(settings_or_path, self.openai_pool, "openai")
        else:
            # Default URLs
            self.openai_base_url = "https://api.openai.com/v1"
            self.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            self.deepseek_base_url = "https://api.deepseek.com/v1"

        console.print(f"[green]✓ Loaded {self.openai_pool.total_count} OpenAI/DeepSeek keys, "
                 f"{self.qwen_pool.total_count} Qwen keys[/green]")
    
    def _load_keys_from_file(self, filepath: Path, pool: APIKeyPool, provider: str):
        """Load API keys from a file."""
        try:
            content = filepath.read_text(encoding='utf-8')
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    pool.add_key(line, provider)
        except Exception as e:
            console.print(f"[yellow]⚠ Error loading keys from {filepath}: {e}[/yellow]")
    
    async def call_parallel(
        self,
        messages: List[dict],
        model: str = "gpt-4o-mini",
        n_parallel: int = 3,
        provider: str = "openai",
        temperature: float = None,  # 改为可选
        max_tokens: int = 4000,
        reasoning_effort: str = "medium",  # 新增：用于 gpt-5 系列
    ) -> List[dict]:
        """Make parallel API calls using multiple keys.

        Args:
            messages: Chat messages
            model: Model name
            n_parallel: Number of parallel calls
            provider: Provider name (openai or qwen)
            temperature: Sampling temperature (仅用于非 gpt-5 模型)
            max_tokens: Max tokens to generate
            reasoning_effort: Reasoning effort for gpt-5 models (low/medium/high)

        Returns:
            List of responses from parallel calls
        """
        # Select pool
        pool = self.openai_pool if provider == "openai" else self.qwen_pool
        base_url = self.openai_base_url if provider == "openai" else self.qwen_base_url
        # If using a DeepSeek model, route to DeepSeek base URL
        try:
            model_lower = (model or "").lower()
        except Exception:
            model_lower = ""
        if provider == "openai" and ("deepseek" in model_lower):
            # Prefer DeepSeek endpoint for deepseek-* models
            base_url = getattr(self, "deepseek_base_url", base_url)

        # Get keys for parallel execution
        keys = pool.get_keys_for_parallel(n_parallel)

        if not keys:
            raise RuntimeError(f"No active {provider} API keys available")

        adaptive_timeout = self._compute_timeout(max_tokens)

        # Create tasks for parallel execution
        tasks = []
        for key_info in keys[:n_parallel]:
            # Apply a strict network timeout; some endpoints can otherwise hang for a long time.
            client_timeout = httpx.Timeout(
                timeout=adaptive_timeout,
                connect=min(10.0, adaptive_timeout),
                read=adaptive_timeout,
                write=min(20.0, adaptive_timeout),
                pool=min(10.0, adaptive_timeout),
            )
            client = AsyncOpenAI(api_key=key_info.key, base_url=base_url, timeout=client_timeout)
            task = self._single_call(
                client,
                key_info,
                messages,
                model,
                temperature,
                max_tokens,
                reasoning_effort,
                timeout_seconds=adaptive_timeout,
            )
            tasks.append(task)
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful = []
        for result in results:
            if isinstance(result, dict) and "error" not in result:
                successful.append(result)
        
        if not successful:
            raise RuntimeError("All parallel API calls failed")

        return successful

    def _compute_timeout(self, max_tokens: Optional[int]) -> float:
        """Scale timeout based on requested tokens to avoid premature failures."""

        base_timeout = float(self.request_timeout_seconds or 60.0)
        if not max_tokens or max_tokens <= 0:
            return base_timeout

        multiplier = max(1.0, min(max_tokens / 2000.0, 5.0))
        return base_timeout * multiplier
    
    async def _single_call(
        self,
        client: AsyncOpenAI,
        key_info: APIKeyInfo,
        messages: List[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str = "medium",
        timeout_seconds: Optional[float] = None,
    ) -> dict:
        """Make a single API call."""
        try:
            effective_timeout = float(timeout_seconds or self.request_timeout_seconds or 60.0)
            # 检测是否需要使用 Responses API (gpt-5.1-codex系列)
            use_responses_api = any(x in model.lower() for x in RESPONSES_API_MODELS)

            if use_responses_api:
                # 使用 Responses API
                # 参考: https://platform.openai.com/docs/models/gpt-5.1-codex
                input_content = self._messages_to_input(messages)

                response = await asyncio.wait_for(
                    client.responses.create(
                        model=model,
                        input=input_content,
                        max_output_tokens=max_tokens,
                    ),
                    timeout=effective_timeout,
                )

                # 解析 Responses API 响应
                output_text = ""
                if hasattr(response, 'output') and response.output:
                    for item in response.output:
                        if hasattr(item, 'type') and item.type == "message":
                            for content in item.content:
                                if hasattr(content, 'type') and content.type == "output_text":
                                    output_text += content.text

                key_info.mark_used()

                return {
                    "content": output_text.strip() if output_text else str(response),
                    "model": getattr(response, 'model', model),
                    "usage": {
                        "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                        "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
                        "total_tokens": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0,
                    },
                    "finish_reason": "stop",
                }

            else:
                # 使用 Chat Completions API (传统模型和 GPT-5/O1/O3)
                # 检测是否是推理模型
                is_reasoning_model = any(x in model.lower() for x in ["gpt-5", "o1", "o3"])

                # 构建 API 参数
                api_params = {
                    "model": model,
                    "messages": messages,
                }

                # GPT-5/O1/O3 系列使用 max_completion_tokens，其他模型使用 max_tokens
                if is_reasoning_model:
                    api_params["max_completion_tokens"] = max_tokens
                    api_params["reasoning_effort"] = reasoning_effort
                else:
                    api_params["max_tokens"] = max_tokens
                    if temperature is not None:
                        api_params["temperature"] = temperature


                response = await asyncio.wait_for(
                    client.chat.completions.create(**api_params),
                    timeout=effective_timeout,
                )
            
            key_info.mark_used()

            choice = response.choices[0]
            content = choice.message.content

            # 检查内容是否为空
            if content is None or content.strip() == "":
                console.print(f"[red]⚠ API returned empty content for model {model}[/red]")
                console.print(f"[dim]Response: {response}[/dim]")
                content = ""  # 确保返回空字符串而不是 None

            return {
                "content": content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "finish_reason": choice.finish_reason,
            }
        
        except asyncio.TimeoutError:
            key_info.mark_error()
            msg = f"timeout after {timeout_seconds or self.request_timeout_seconds}s"
            console.print(f"[yellow]⚠ API call failed: {msg}[/yellow]")
            return {"error": msg}

        except Exception as e:
            key_info.mark_error()
            console.print(f"[yellow]⚠ API call failed: {e}[/yellow]")
            return {"error": str(e)}

    def _messages_to_input(self, messages: List[dict]) -> str:
        """将 messages 格式转换为 Responses API 的 input 格式"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")

        return "\n\n".join(parts)

    def get_stats(self) -> str:
        """Get statistics for all pools."""
        return (
            f"=== OpenAI Pool ===\n{self.openai_pool.stats()}\n\n"
            f"=== Qwen Pool ===\n{self.qwen_pool.stats()}"
        )
