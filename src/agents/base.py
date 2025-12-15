"""Abstract base class for all agents."""

from __future__ import annotations

import textwrap
from abc import ABC, abstractmethod
from typing import Any

from ..llm_client import LLMClient, LLMResponse, Message
from ..memory.state import ProjectMemory
from ..tools import ToolRegistry


class BaseAgent(ABC):
    """Shared helper logic for all role-specific agents."""

    def __init__(
        self,
        *,
        name: str,
        role: str,
        llm: LLMClient,
        memory: ProjectMemory,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.name = name
        self.role = role
        self.llm = llm
        self.memory = memory
        self.tools = tools

    @property
    def system_prompt(self) -> str:
        """Default system instructions overriding per-agent prompts if needed."""

        return textwrap.dedent(
            f"""
            You are {self.name}, acting as the {self.role} in a research-grade
            multi-agent system. Respond with structured JSON when possible.
            Always explain tool usage and cite files you touch.
            """
        ).strip()

    async def _chat(self, task: str, context: str | None = None) -> LLMResponse:
        messages: list[Message] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.memory.last_messages())
        user_prompt = f"Task:\n{task}"
        if context:
            user_prompt += f"\n\nAdditional Context:\n{context}"
        if self.tools:
            user_prompt += f"\n\nAvailable Tools:\n{self.tools.describe()}"
        messages.append({"role": "user", "content": user_prompt})
        response = await self.llm.aresponse(messages)
        self.memory.add(self.name, response.content)
        return response

    def call_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if not self.tools:
            raise RuntimeError(f"{self.name} has no tool registry configured.")
        return self.tools.call(name, *args, **kwargs)

    @abstractmethod
    async def act(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent-specific action."""

