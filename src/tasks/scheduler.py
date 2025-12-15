"""Task scheduler that bridges planner output and execution."""

from __future__ import annotations

from typing import Iterable

from .task import Task, TaskGraph, TaskStatus


class TaskScheduler:
    """Simple FIFO scheduler built on top of TaskGraph."""

    def __init__(self) -> None:
        self.graph = TaskGraph()

    def load_plan(self, plan: Iterable[dict]) -> None:
        """Load planner output into the DAG."""

        for node in plan:
            task = Task(
                task_id=node["id"],
                summary=node["summary"],
                assignee=node["assignee"],
            )
            self.graph.add_task(task, node.get("depends_on"))

    def next_task(self) -> Task | None:
        ready = self.graph.get_ready_tasks()
        return ready[0] if ready else None

    def mark_done(self, task_id: str, outputs: dict[str, str] | None = None) -> None:
        task: Task = self.graph.graph.nodes[task_id]["payload"]
        task.status = TaskStatus.DONE
        if outputs:
            task.outputs.update(outputs)

    def mark_failed(self, task_id: str, reason: str) -> None:
        task: Task = self.graph.graph.nodes[task_id]["payload"]
        task.status = TaskStatus.FAILED
        task.outputs["error"] = reason

    def finished(self) -> bool:
        return self.graph.all_done()

