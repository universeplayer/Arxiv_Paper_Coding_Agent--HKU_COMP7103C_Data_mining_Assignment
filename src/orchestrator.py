"""Entry point for running the multi-agent workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .agents import CodeAgent, PlanningAgent, ReviewAgent
from .config import load_settings
from .llm_client import LLMClient
from .memory.state import ProjectMemory
from .tasks.scheduler import TaskScheduler
from .tools import build_default_tools

console = Console()


async def run(spec_path: Path, workspace: Path, max_steps: int) -> None:
    settings = load_settings()
    llm = LLMClient(settings)
    memory = ProjectMemory()

    workspace.mkdir(parents=True, exist_ok=True)
    tools = build_default_tools(workspace)

    agents = {
        "PlanningAgent": PlanningAgent(name="Planner", role="Project Planning Agent", llm=llm, memory=memory),
        "CodeAgent": CodeAgent(name="Coder", role="Code Generation Agent", llm=llm, memory=memory, tools=tools),
        "ReviewAgent": ReviewAgent(name="Reviewer", role="Code Evaluation Agent", llm=llm, memory=memory),
    }

    requirement = spec_path.read_text(encoding="utf-8")
    planner_result = await agents["PlanningAgent"].act(requirement=requirement)
    plan = planner_result["plan"]

    scheduler = TaskScheduler()
    scheduler.load_plan(plan)

    step = 0
    audit_log: list[dict] = []

    while step < max_steps and not scheduler.finished():
        task = scheduler.next_task()
        if not task:
            console.log("[yellow]No ready task available; breaking early.")
            break

        console.rule(f"[bold cyan]Step {step + 1}: {task.task_id} ({task.assignee})")

        agent = agents[task.assignee]
        try:
            if task.assignee == "PlanningAgent":
                result = await agent.act(requirement=requirement)
            elif task.assignee == "CodeAgent":
                result = await agent.act(task_summary=task.summary)
            else:
                result = await agent.act(artifact_summary=task.summary)
            scheduler.mark_done(task.task_id, outputs=result)
            audit_log.append({"task": task.task_id, "assignee": task.assignee, "result": result})
        except Exception as exc:  # noqa: BLE001
            scheduler.mark_failed(task.task_id, str(exc))
            audit_log.append({"task": task.task_id, "assignee": task.assignee, "error": str(exc)})
            console.log(f"[red]Task {task.task_id} failed: {exc}")
            break

        step += 1

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task ID")
    table.add_column("Assignee")
    table.add_column("Status")

    for node, data in scheduler.graph.graph.nodes(data=True):
        payload = data["payload"]
        table.add_row(node, payload.assignee, payload.status.value)

    console.print(table)

    log_path = workspace / "audit_log.json"
    log_path.write_text(json.dumps(audit_log, indent=2), encoding="utf-8")
    console.log(f"[green]Audit log saved to {log_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the research multi-agent orchestrator.")
    parser.add_argument("--spec", type=Path, required=True, help="Path to requirement markdown.")
    parser.add_argument("--workspace", type=Path, default=Path("./workspace_runs/default"))
    parser.add_argument("--max-steps", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run(args.spec, args.workspace, args.max_steps))


if __name__ == "__main__":
    main()

