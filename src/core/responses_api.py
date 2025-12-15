"""OpenAI Responses API 支持 - 用于 gpt-5.1-codex 等模型"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from openai import AsyncOpenAI
from rich.console import Console

from .config import get_settings

console = Console()
logger = logging.getLogger(__name__)


class ResponsesAPIManager:
    """管理 OpenAI Responses API 调用（用于 gpt-5.1-codex）"""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.clients: List[AsyncOpenAI] = []

        # 加载 API keys
        self._load_api_keys()

    def _load_api_keys(self):
        """从文件加载 API keys"""
        key_file = Path(self.settings.openai_api_key_file)

        if key_file.exists():
            try:
                content = key_file.read_text(encoding='utf-8')
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        client = AsyncOpenAI(
                            api_key=line,
                            base_url=self.settings.openai_base_url
                        )
                        self.clients.append(client)
                logger.info(f"Loaded {len(self.clients)} API keys for Responses API")
            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")

        # Fallback to single key
        if not self.clients and self.settings.openai_api_key:
            client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url
            )
            self.clients.append(client)

        if not self.clients:
            logger.warning("No API keys available for Responses API")

    async def call_responses_api(
        self,
        input_content: str,
        model: str = "gpt-5.1-codex",
        max_output_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """调用 Responses API

        Args:
            input_content: 输入内容（可以是字符串或消息列表）
            model: 模型名称
            max_output_tokens: 最大输出 tokens

        Returns:
            响应内容字典
        """
        if not self.clients:
            raise RuntimeError("No API clients available")

        # 使用第一个可用的 client
        client = self.clients[0]

        try:
            # 调用 Responses API
            # 参考: https://platform.openai.com/docs/models/gpt-5.1-codex
            response = await client.responses.create(
                model=model,
                input=input_content,
                max_output_tokens=max_output_tokens,
            )

            # 解析响应
            # Responses API 返回格式可能不同于 Chat Completions
            if hasattr(response, 'output') and response.output:
                # 提取文本内容
                output_text = ""
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "message":
                        for content in item.content:
                            if hasattr(content, 'type') and content.type == "output_text":
                                output_text += content.text

                return {
                    "content": output_text.strip(),
                    "model": response.model if hasattr(response, 'model') else model,
                    "usage": {
                        "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                        "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
                        "total_tokens": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0,
                    }
                }
            else:
                # Fallback 解析
                return {
                    "content": str(response),
                    "model": model,
                    "usage": {}
                }

        except Exception as e:
            logger.error(f"Responses API call failed: {e}")
            raise

    async def call_parallel(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-5.1-codex",
        n_parallel: int = 2,
        max_tokens: int = 4000,
        **kwargs  # 忽略其他参数（如 reasoning_effort, temperature）
    ) -> List[Dict[str, Any]]:
        """并行调用 Responses API（兼容接口）

        Args:
            messages: 消息列表（将被转换为 input 格式）
            model: 模型名称
            n_parallel: 并行数量
            max_tokens: 最大 tokens

        Returns:
            响应列表
        """
        # 将 messages 转换为 input 字符串
        input_content = self._messages_to_input(messages)

        # 创建并行任务
        tasks = []
        for i in range(min(n_parallel, len(self.clients))):
            client = self.clients[i % len(self.clients)]
            task = self._single_call(client, input_content, model, max_tokens)
            tasks.append(task)

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤成功的结果
        successful = []
        for result in results:
            if isinstance(result, dict) and "error" not in result:
                successful.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Parallel call failed: {result}")

        if not successful:
            raise RuntimeError("All parallel Responses API calls failed")

        return successful

    async def _single_call(
        self,
        client: AsyncOpenAI,
        input_content: str,
        model: str,
        max_output_tokens: int,
    ) -> Dict[str, Any]:
        """单次 API 调用"""
        try:
            response = await client.responses.create(
                model=model,
                input=input_content,
                max_output_tokens=max_output_tokens,
            )

            # 解析响应
            output_text = ""
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "message":
                        for content in item.content:
                            if hasattr(content, 'type') and content.type == "output_text":
                                output_text += content.text

            return {
                "content": output_text.strip() if output_text else str(response),
                "model": getattr(response, 'model', model),
                "usage": {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
                    "total_tokens": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0,
                }
            }

        except Exception as e:
            logger.error(f"Responses API single call failed: {e}")
            return {"error": str(e)}

    def _messages_to_input(self, messages: List[Dict[str, str]]) -> str:
        """将 messages 格式转换为 Responses API 的 input 格式"""
        # 简单策略：将所有消息拼接成一个字符串
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
