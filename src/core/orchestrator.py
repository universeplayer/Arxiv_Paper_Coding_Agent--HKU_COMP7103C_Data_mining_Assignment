"""Orchestrator for coordinating multiple agents and managing task execution."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import networkx as nx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src.agents.base_agent import Task, AgentResponse
from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.reviewer import ReviewerAgent
from src.core.memory import ProjectMemory, TaskExecution
from src.core.config import get_settings
from src.tools import (
    create_file, read_file, write_file, delete_file,
    list_directory, create_directory,
    web_search, fetch_url,
    execute_python, execute_shell
)

console = Console()


class Orchestrator:
    """Orchestrates multi-agent task execution with dependency management."""

    def __init__(
        self,
        project_name: str,
        enable_parallel: Optional[bool] = None
    ):
        """Initialize orchestrator.

        Args:
            project_name: Name of the project
            enable_parallel: Enable parallel execution (uses settings if None)
        """
        self.project_name = project_name
        self.settings = get_settings()
        self.enable_parallel = (
            enable_parallel if enable_parallel is not None
            else self.settings.enable_parallel_execution
        )

        # Initialize memory
        self.memory = ProjectMemory(project_name=project_name)

        # Initialize agents
        self.planner = PlannerAgent(memory=self.memory)
        self.coder = CoderAgent(memory=self.memory)
        self.reviewer = ReviewerAgent(memory=self.memory)

        # Register tools for agents
        self._register_tools()

        # Task tracking
        self.tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, AgentResponse] = {}
        self.dependency_graph = nx.DiGraph()

        console.print(f"[bold green]Orchestrator initialized for project: {project_name}[/bold green]")

    def _register_tools(self) -> None:
        """Register tools for all agents."""
        tools = {
            # File operations
            "create_file": create_file,
            "read_file": read_file,
            "write_file": write_file,
            "delete_file": delete_file,
            "list_directory": list_directory,
            "create_directory": create_directory,
            # Web operations
            "web_search": web_search,
            "fetch_url": fetch_url,
            # Code execution
            "execute_python": execute_python,
            "execute_shell": execute_shell,
        }

        for agent in [self.planner, self.coder, self.reviewer]:
            for tool_name, tool_func in tools.items():
                agent.register_tool(tool_name, tool_func)

    def execute_project(
        self,
        objective: str,
        context: Optional[str] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """Execute complete project from high-level objective.

        Args:
            objective: High-level project objective
            context: Additional context
            max_iterations: Maximum planning iterations

        Returns:
            Execution results dictionary
        """
        console.print(f"\n[bold cyan]Starting project: {objective}[/bold cyan]\n")

        start_time = datetime.now()

        try:
            # Phase 1: Planning
            console.print("[bold yellow]Phase 1: Planning[/bold yellow]")
            plan_task = Task(
                task_id="planning",
                description=objective,
                dependencies=[],
                metadata={"context": context}
            )

            plan_result = self.planner.execute(plan_task, context=context)

            if not plan_result.success:
                return {
                    "success": False,
                    "error": "Planning failed",
                    "details": plan_result.message
                }

            # Extract plan
            plan_data = plan_result.data.get("plan", {})
            subtasks = plan_data.get("subtasks", [])

            # Create tasks from plan
            for subtask_spec in subtasks:
                task = Task(
                    task_id=subtask_spec["id"],
                    description=subtask_spec["description"],
                    dependencies=subtask_spec.get("dependencies", []),
                    priority=subtask_spec.get("priority", 0),
                    metadata=subtask_spec
                )
                self.tasks[task.task_id] = task

            # Build dependency graph
            self._build_dependency_graph()

            # Phase 2: Execution
            console.print("\n[bold yellow]Phase 2: Execution[/bold yellow]")
            execution_results = self._execute_tasks()

            # Phase 3: Review
            console.print("\n[bold yellow]Phase 3: Review[/bold yellow]")
            review_result = self._review_results(execution_results)

            # Compile results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            results = {
                "success": review_result.success,
                "project": self.project_name,
                "objective": objective,
                "duration_seconds": duration,
                "plan": plan_data,
                "tasks_completed": len(execution_results),
                "review": review_result.data,
                "artifacts": list(self.memory.artifacts.keys()),
                "task_summary": self.memory.get_task_summary()
            }

            # Save memory
            memory_path = self.settings.output_dir / f"{self.project_name}_memory.json"
            self.memory.save(memory_path)

            console.print(f"\n[bold green]Project completed in {duration:.1f}s[/bold green]")

            return results

        except Exception as e:
            console.print(f"\n[bold red]Project execution failed: {e}[/bold red]")
            return {
                "success": False,
                "error": str(e),
                "project": self.project_name
            }

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from tasks."""
        self.dependency_graph.clear()

        # Add all tasks as nodes
        for task_id, task in self.tasks.items():
            self.dependency_graph.add_node(task_id, task=task)

        # Add dependency edges
        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id in self.tasks:
                    self.dependency_graph.add_edge(dep_id, task_id)

        # Validate (check for cycles)
        if not nx.is_directed_acyclic_graph(self.dependency_graph):
            raise ValueError("Circular dependencies detected in task graph!")

    def _execute_tasks(self) -> Dict[str, AgentResponse]:
        """Execute tasks according to dependency order.

        Returns:
            Dictionary of task results
        """
        # Get topological order
        try:
            execution_order = list(nx.topological_sort(self.dependency_graph))
        except Exception:
            execution_order = list(self.tasks.keys())

        results = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task_progress = progress.add_task(
                f"Executing {len(execution_order)} tasks...",
                total=len(execution_order)
            )

            for task_id in execution_order:
                task = self.tasks[task_id]

                # Record task execution
                execution = TaskExecution(
                    task_id=task_id,
                    agent_type="CoderAgent",
                    status="in_progress",
                    input_data={"description": task.description}
                )
                self.memory.add_task_execution(execution)

                # Execute task
                console.print(f"\n[cyan]Executing task: {task_id}[/cyan]")
                result = self.coder.execute(task)

                # Update memory
                self.memory.update_task_status(
                    task_id=task_id,
                    status="completed" if result.success else "failed",
                    output_data=result.data,
                    error=None if result.success else result.message
                )

                results[task_id] = result

                progress.update(task_progress, advance=1)

                if not result.success:
                    console.print(f"[red]Task {task_id} failed: {result.message}[/red]")

        return results

    def _review_results(self, execution_results: Dict[str, AgentResponse]) -> AgentResponse:
        """Review execution results.

        Args:
            execution_results: Dictionary of task results

        Returns:
            Review result
        """
        # Collect all artifacts
        all_artifacts = []
        for result in execution_results.values():
            all_artifacts.extend(result.artifacts)

        # Create review task
        review_task = Task(
            task_id="final_review",
            description="Review all generated artifacts for quality and correctness",
            dependencies=[],
            metadata={"artifacts": all_artifacts}
        )

        # Execute review
        review_result = self.reviewer.execute(review_task)

        return review_result

    async def _execute_tasks_parallel(self, task_groups: List[List[str]]) -> Dict[str, AgentResponse]:
        """Execute tasks in parallel groups.

        Args:
            task_groups: List of task groups (each group executes in parallel)

        Returns:
            Dictionary of task results
        """
        results = {}

        for group in task_groups:
            # Execute tasks in group concurrently
            group_tasks = [self._execute_single_task_async(task_id) for task_id in group]
            group_results = await asyncio.gather(*group_tasks)

            for task_id, result in zip(group, group_results):
                results[task_id] = result

        return results

    async def _execute_single_task_async(self, task_id: str) -> AgentResponse:
        """Execute single task asynchronously.

        Args:
            task_id: Task identifier

        Returns:
            AgentResponse
        """
        task = self.tasks[task_id]

        # Record execution
        execution = TaskExecution(
            task_id=task_id,
            agent_type="CoderAgent",
            status="in_progress",
            input_data={"description": task.description}
        )
        self.memory.add_task_execution(execution)

        # Execute (run in thread pool for sync code)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.coder.execute, task)

        # Update memory
        self.memory.update_task_status(
            task_id=task_id,
            status="completed" if result.success else "failed",
            output_data=result.data
        )

        return result

    def save_results(self, results: Dict[str, Any], filepath: Optional[Path] = None) -> None:
        """Save execution results to file.

        Args:
            results: Results dictionary
            filepath: Output file path (auto-generated if None)
        """
        import json

        if filepath is None:
            filepath = self.settings.output_dir / f"{self.project_name}_results.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        console.print(f"[green]Results saved to {filepath}[/green]")

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable report.

        Args:
            results: Execution results

        Returns:
            Report as string
        """
        report_lines = [
            f"# Project Report: {self.project_name}",
            f"\n## Objective\n{results.get('objective', 'N/A')}",
            f"\n## Duration\n{results.get('duration_seconds', 0):.1f} seconds",
            f"\n## Status\n{'SUCCESS' if results.get('success') else 'FAILED'}",
            "\n## Tasks Completed",
            f"{results.get('tasks_completed', 0)} tasks",
            "\n## Artifacts Generated",
        ]

        for artifact in results.get("artifacts", []):
            report_lines.append(f"- {artifact}")

        report_lines.append("\n## Quality Review")
        review = results.get("review", {})
        report_lines.append(f"Quality Score: {review.get('quality_score', 0):.2f}/1.0")
        report_lines.append(f"Issues Found: {len(review.get('issues', []))}")

        return "\n".join(report_lines)
