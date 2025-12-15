"""Base agent class with common functionality."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.core.llm_client import LLMClient, Message
from src.core.memory import ProjectMemory
from src.core.config import get_settings
from rich.console import Console

console = Console()


@dataclass
class Task:
    """Represents a task for an agent."""

    task_id: str
    description: str
    dependencies: List[str]
    priority: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentResponse:
    """Response from an agent action."""

    success: bool
    data: Dict[str, Any]
    message: str
    artifacts: List[str] = None

    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[ProjectMemory] = None,
        temperature: float = 0.7
    ):
        """Initialize base agent.

        Args:
            name: Agent name
            llm_client: LLM client instance
            memory: Project memory instance
            temperature: LLM temperature
        """
        self.name = name
        self.settings = get_settings()
        self.llm_client = llm_client or self._create_default_client(temperature)
        self.memory = memory
        self.tools: Dict[str, callable] = {}

    def _create_default_client(self, temperature: float) -> LLMClient:
        """Create default LLM client.

        Args:
            temperature: Temperature setting

        Returns:
            LLMClient instance
        """
        return LLMClient(
            provider="deepseek",
            model=self.settings.default_model,
            temperature=temperature
        )

    def register_tool(self, name: str, tool_func: callable) -> None:
        """Register a tool for the agent to use.

        Args:
            name: Tool name
            tool_func: Tool function
        """
        self.tools[name] = tool_func
        console.print(f"[blue]{self.name}: Registered tool '{name}'[/blue]")

    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Use a registered tool.

        Args:
            tool_name: Name of the tool
            **kwargs: Tool arguments

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered")

        console.print(f"[blue]{self.name}: Using tool '{tool_name}'[/blue]")
        return self.tools[tool_name](**kwargs)

    @abstractmethod
    def think(self, task: Task, context: Optional[str] = None) -> str:
        """Generate reasoning/plan for the task.

        Args:
            task: Task to think about
            context: Additional context

        Returns:
            Thought/reasoning string
        """
        pass

    @abstractmethod
    def act(self, task: Task, thought: str) -> AgentResponse:
        """Execute action based on reasoning.

        Args:
            task: Task to execute
            thought: Reasoning from think()

        Returns:
            AgentResponse object
        """
        pass

    def reflect(self, task: Task, action_result: AgentResponse) -> str:
        """Reflect on action results and generate insights.

        Args:
            task: Original task
            action_result: Result from act()

        Returns:
            Reflection string
        """
        reflection_prompt = f"""
Reflect on the following task execution:

Task: {task.description}
Success: {action_result.success}
Result: {action_result.message}

Provide insights on:
1. What went well
2. What could be improved
3. Lessons learned
4. Suggestions for future similar tasks

Be concise and actionable.
"""

        messages = [
            Message(role="system", content=f"You are {self.name}, reflecting on your work."),
            Message(role="user", content=reflection_prompt)
        ]

        reflection = self.llm_client.chat(messages, temperature=0.5)
        console.print(f"[magenta]{self.name}: Reflection complete[/magenta]")

        if self.memory:
            self.memory.add_message(
                role="agent",
                content=f"[{self.name}] Reflection: {reflection}",
                metadata={"task_id": task.task_id, "agent": self.name}
            )

        return reflection

    def execute(self, task: Task, context: Optional[str] = None) -> AgentResponse:
        """Full execution cycle: think -> act -> reflect.

        Args:
            task: Task to execute
            context: Additional context

        Returns:
            AgentResponse from act()
        """
        console.print(f"[bold cyan]{self.name}: Starting task {task.task_id}[/bold cyan]")

        # Think
        thought = self.think(task, context)

        # Act
        result = self.act(task, thought)

        # Reflect (if successful or requested)
        if result.success or not result.success:  # Always reflect
            self.reflect(task, result)

        console.print(
            f"[bold cyan]{self.name}: Completed task {task.task_id} "
            f"(Success: {result.success})[/bold cyan]"
        )

        return result

    def get_system_prompt(self) -> str:
        """Get agent-specific system prompt.

        Returns:
            System prompt string
        """
        return f"You are {self.name}, a helpful AI assistant."

    def chat(
        self,
        user_message: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Simple chat interface.

        Args:
            user_message: User message
            context: Optional context
            temperature: Optional temperature override

        Returns:
            Assistant response
        """
        messages = [
            Message(role="system", content=self.get_system_prompt())
        ]

        if context:
            messages.append(Message(role="system", content=f"Context: {context}"))

        messages.append(Message(role="user", content=user_message))

        response = self.llm_client.chat(messages, temperature=temperature)

        if self.memory:
            self.memory.add_message("user", user_message)
            self.memory.add_message("assistant", response, metadata={"agent": self.name})

        return response
