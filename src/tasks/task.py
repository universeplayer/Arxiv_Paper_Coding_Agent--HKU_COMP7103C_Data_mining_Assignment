"""Task primitives used by the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

import networkx as nx


class TaskStatus(str, Enum):
    """Lifecycle phases for a task node."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class Task:
    """Single actionable unit scheduled to an agent."""

    task_id: str
    summary: str
    assignee: str
    status: TaskStatus = TaskStatus.PENDING
    outputs: dict[str, str] = field(default_factory=dict)


class TaskGraph:
    """Directed acyclic graph of tasks and their dependencies."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_task(self, task: Task, depends_on: Iterable[str] | None = None) -> None:
        self.graph.add_node(task.task_id, payload=task)
        for dep in depends_on or []:
            self.graph.add_edge(dep, task.task_id)

    def get_ready_tasks(self) -> list[Task]:
        ready: list[Task] = []
        for node, data in self.graph.nodes(data=True):
            task: Task = data["payload"]
            if task.status != TaskStatus.PENDING:
                continue
            predecessors = list(self.graph.predecessors(node))
            if all(self.graph.nodes[p]["payload"].status == TaskStatus.DONE for p in predecessors):
                ready.append(task)
        return ready

    def all_done(self) -> bool:
        return all(data["payload"].status == TaskStatus.DONE for _, data in self.graph.nodes(data=True))

