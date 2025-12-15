"""Memory system for maintaining conversation context and task history."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List
from collections import deque

from rich.console import Console

console = Console()


@dataclass
class Artifact:
    """Represents a file or code artifact created/modified by agents."""

    path: str
    content: str
    artifact_type: str  # 'file', 'code', 'document', etc.
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["modified_at"] = self.modified_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Create from dictionary."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["modified_at"] = datetime.fromisoformat(data["modified_at"])
        return cls(**data)


@dataclass
class TaskExecution:
    """Record of a task execution."""

    task_id: str
    agent_type: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)  # List of artifact paths

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        data["end_time"] = self.end_time.isoformat() if self.end_time else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskExecution":
        """Create from dictionary."""
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        return cls(**data)


@dataclass
class ConversationMessage:
    """Single conversation message."""

    role: str  # 'system', 'user', 'assistant', 'agent'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class ProjectMemory:
    """Maintains project-wide memory including context, tasks, and artifacts."""

    def __init__(self, project_name: str, max_context_messages: int = 100):
        """Initialize project memory.

        Args:
            project_name: Name of the project
            max_context_messages: Maximum conversation messages to keep in context
        """
        self.project_name = project_name
        self.max_context_messages = max_context_messages

        # Conversation history (limited for context management)
        self.conversation: deque = deque(maxlen=max_context_messages)

        # Full conversation history (unlimited)
        self.full_history: List[ConversationMessage] = []

        # Task execution history
        self.task_history: Dict[str, TaskExecution] = {}

        # Artifacts (files, documents, etc.)
        self.artifacts: Dict[str, Artifact] = {}

        # Project metadata
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "project_name": project_name,
        }

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to conversation history.

        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata
        """
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.conversation.append(message)
        self.full_history.append(message)

    def add_task_execution(self, execution: TaskExecution) -> None:
        """Add task execution record.

        Args:
            execution: TaskExecution object
        """
        self.task_history[execution.task_id] = execution

    def update_task_status(
        self,
        task_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Update task execution status.

        Args:
            task_id: Task identifier
            status: New status
            output_data: Optional output data
            error: Optional error message
        """
        if task_id in self.task_history:
            execution = self.task_history[task_id]
            execution.status = status
            execution.end_time = datetime.now()
            if output_data:
                execution.output_data.update(output_data)
            if error:
                execution.error = error
        else:
            console.print(f"[yellow]Warning: Task {task_id} not found in history[/yellow]")

    def add_artifact(self, artifact: Artifact) -> None:
        """Add or update an artifact.

        Args:
            artifact: Artifact object
        """
        if artifact.path in self.artifacts:
            artifact.modified_at = datetime.now()
        self.artifacts[artifact.path] = artifact

    def get_artifact(self, path: str) -> Optional[Artifact]:
        """Get artifact by path.

        Args:
            path: Artifact path

        Returns:
            Artifact if found, None otherwise
        """
        return self.artifacts.get(path)

    def get_recent_context(self, n: int = 10) -> List[ConversationMessage]:
        """Get recent conversation messages.

        Args:
            n: Number of recent messages

        Returns:
            List of recent messages
        """
        return list(self.conversation)[-n:]

    def get_context_summary(self, max_chars: int = 2000) -> str:
        """Get compressed context summary.

        Args:
            max_chars: Maximum characters in summary

        Returns:
            Context summary string
        """
        recent_messages = self.get_recent_context(20)
        summary_parts = []

        for msg in recent_messages:
            role_prefix = f"[{msg.role}]"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            summary_parts.append(f"{role_prefix} {content}")

        summary = "\n".join(summary_parts)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n... (truncated)"

        return summary

    def get_task_summary(self) -> Dict[str, int]:
        """Get task execution summary.

        Returns:
            Dictionary with status counts
        """
        summary = {
            "total": len(self.task_history),
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "pending": 0,
        }

        for execution in self.task_history.values():
            if execution.status in summary:
                summary[execution.status] += 1

        return summary

    def save(self, filepath: Path) -> None:
        """Save memory to file.

        Args:
            filepath: Path to save file
        """
        data = {
            "metadata": self.metadata,
            "conversation": [msg.to_dict() for msg in self.full_history],
            "task_history": {
                task_id: execution.to_dict()
                for task_id, execution in self.task_history.items()
            },
            "artifacts": {
                path: artifact.to_dict()
                for path, artifact in self.artifacts.items()
            },
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]Memory saved to {filepath}[/green]")

    @classmethod
    def load(cls, filepath: Path) -> "ProjectMemory":
        """Load memory from file.

        Args:
            filepath: Path to load file

        Returns:
            ProjectMemory instance
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        memory = cls(project_name=data["metadata"]["project_name"])
        memory.metadata = data["metadata"]

        # Load conversation
        for msg_data in data["conversation"]:
            message = ConversationMessage.from_dict(msg_data)
            memory.conversation.append(message)
            memory.full_history.append(message)

        # Load task history
        for task_id, exec_data in data["task_history"].items():
            memory.task_history[task_id] = TaskExecution.from_dict(exec_data)

        # Load artifacts
        for path, artifact_data in data["artifacts"].items():
            memory.artifacts[path] = Artifact.from_dict(artifact_data)

        console.print(f"[green]Memory loaded from {filepath}[/green]")
        return memory

    def clear(self) -> None:
        """Clear all memory."""
        self.conversation.clear()
        self.full_history.clear()
        self.task_history.clear()
        self.artifacts.clear()
        console.print("[yellow]Memory cleared[/yellow]")
