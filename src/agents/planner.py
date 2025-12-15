"""Planning agent for task decomposition and dependency analysis."""

import json
from typing import Dict, Any, List, Optional
import networkx as nx

from src.agents.base_agent import BaseAgent, Task, AgentResponse, Message
from rich.console import Console
from rich.tree import Tree

console = Console()


class PlannerAgent(BaseAgent):
    """Agent responsible for planning and task decomposition."""

    def __init__(self, **kwargs):
        """Initialize planner agent."""
        super().__init__(name="PlannerAgent", temperature=0.3, **kwargs)
        self.dependency_graph = nx.DiGraph()

    def get_system_prompt(self) -> str:
        """Get system prompt for planner."""
        return """You are an expert planning agent specialized in:
1. Breaking down complex tasks into manageable subtasks
2. Identifying dependencies between tasks
3. Creating efficient execution schedules
4. Designing software architectures

Use Chain-of-Thought reasoning to think through problems step by step.
Be precise, systematic, and thorough in your planning."""

    def think(self, task: Task, context: Optional[str] = None) -> str:
        """Generate plan using Chain-of-Thought reasoning.

        Args:
            task: Task to plan
            context: Additional context

        Returns:
            Thought process as string
        """
        console.print(f"[yellow]{self.name}: Thinking about task...[/yellow]")

        prompt = f"""
Task: {task.description}

{f"Context: {context}" if context else ""}

Use Chain-of-Thought reasoning to break down this task:

1. Understand the Requirements:
   - What is the end goal?
   - What are the key components needed?
   - What constraints exist?

2. Identify Subtasks:
   - Break down into logical steps
   - Ensure subtasks are specific and actionable
   - Consider dependencies

3. Create Execution Order:
   - Which tasks must happen first?
   - Which tasks can run in parallel?
   - What is the critical path?

4. Estimate Complexity:
   - Which tasks are simple vs complex?
   - What resources are needed?
   - What could go wrong?

Provide your step-by-step reasoning, then output a JSON plan with:
{{
  "subtasks": [
    {{
      "id": "task_1",
      "description": "...",
      "dependencies": [],
      "priority": 1,
      "estimated_complexity": "low|medium|high"
    }}
  ],
  "execution_order": ["task_1", "task_2", ...],
  "parallel_groups": [[task_ids that can run in parallel]]
}}
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        thought = self.llm_client.chat(messages, temperature=0.3)

        if self.memory:
            self.memory.add_message(
                role="agent",
                content=f"[{self.name}] Thought: {thought}",
                metadata={"task_id": task.task_id, "phase": "thinking"}
            )

        return thought

    def act(self, task: Task, thought: str) -> AgentResponse:
        """Create execution plan based on reasoning.

        Args:
            task: Task to plan
            thought: Reasoning from think()

        Returns:
            AgentResponse with plan
        """
        console.print(f"[yellow]{self.name}: Creating execution plan...[/yellow]")

        try:
            # Extract JSON from thought
            plan_data = self._extract_plan_from_thought(thought)

            if not plan_data:
                return AgentResponse(
                    success=False,
                    data={},
                    message="Failed to extract valid plan from reasoning"
                )

            # Build dependency graph
            self._build_dependency_graph(plan_data["subtasks"])

            # Validate plan
            if not self._validate_plan(plan_data):
                return AgentResponse(
                    success=False,
                    data=plan_data,
                    message="Plan validation failed (circular dependencies detected)"
                )

            # Generate execution schedule
            schedule = self._create_execution_schedule(plan_data)

            result_data = {
                "plan": plan_data,
                "schedule": schedule,
                "dependency_graph": self._graph_to_dict()
            }

            # Visualize plan
            self._visualize_plan(plan_data)

            if self.memory:
                self.memory.add_message(
                    role="agent",
                    content=f"[{self.name}] Created plan with {len(plan_data['subtasks'])} subtasks",
                    metadata={"task_id": task.task_id, "plan": plan_data}
                )

            return AgentResponse(
                success=True,
                data=result_data,
                message=f"Successfully created plan with {len(plan_data['subtasks'])} subtasks"
            )

        except Exception as e:
            console.print(f"[red]{self.name}: Error creating plan: {e}[/red]")
            return AgentResponse(
                success=False,
                data={},
                message=f"Error creating plan: {str(e)}"
            )

    def _extract_plan_from_thought(self, thought: str) -> Optional[Dict[str, Any]]:
        """Extract JSON plan from thought text.

        Args:
            thought: Thought text containing JSON

        Returns:
            Parsed plan dictionary or None
        """
        try:
            # Find JSON in text
            start_idx = thought.find("{")
            end_idx = thought.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                # Try alternative format
                return self._create_simple_plan(thought)

            json_str = thought[start_idx:end_idx]
            plan = json.loads(json_str)

            # Validate structure
            if "subtasks" in plan and isinstance(plan["subtasks"], list):
                return plan
            else:
                return self._create_simple_plan(thought)

        except json.JSONDecodeError:
            return self._create_simple_plan(thought)

    def _create_simple_plan(self, thought: str) -> Dict[str, Any]:
        """Create simple plan from thought if JSON extraction fails.

        Args:
            thought: Thought text

        Returns:
            Simple plan dictionary
        """
        # Create a single-task plan
        return {
            "subtasks": [
                {
                    "id": "task_1",
                    "description": thought[:200] + "..." if len(thought) > 200 else thought,
                    "dependencies": [],
                    "priority": 1,
                    "estimated_complexity": "medium"
                }
            ],
            "execution_order": ["task_1"],
            "parallel_groups": [["task_1"]]
        }

    def _build_dependency_graph(self, subtasks: List[Dict[str, Any]]) -> None:
        """Build dependency graph from subtasks.

        Args:
            subtasks: List of subtask definitions
        """
        self.dependency_graph.clear()

        # Add nodes
        for subtask in subtasks:
            self.dependency_graph.add_node(
                subtask["id"],
                description=subtask["description"],
                priority=subtask.get("priority", 0),
                complexity=subtask.get("estimated_complexity", "medium")
            )

        # Add edges (dependencies)
        for subtask in subtasks:
            for dep in subtask.get("dependencies", []):
                if dep in self.dependency_graph:
                    self.dependency_graph.add_edge(dep, subtask["id"])

    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """Validate plan for circular dependencies.

        Args:
            plan: Plan dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for circular dependencies
            if not nx.is_directed_acyclic_graph(self.dependency_graph):
                console.print("[red]Circular dependencies detected![/red]")
                return False
            return True
        except Exception as e:
            console.print(f"[red]Error validating plan: {e}[/red]")
            return False

    def _create_execution_schedule(self, plan: Dict[str, Any]) -> List[List[str]]:
        """Create execution schedule using topological sort.

        Args:
            plan: Plan dictionary

        Returns:
            List of execution stages (each stage contains parallel tasks)
        """
        try:
            # Topological sort
            topo_order = list(nx.topological_sort(self.dependency_graph))

            # Group by level (tasks that can run in parallel)
            schedule = []
            processed = set()

            for task_id in topo_order:
                # Check if all dependencies are processed
                deps = list(self.dependency_graph.predecessors(task_id))
                if all(dep in processed for dep in deps):
                    # Find which level this task belongs to
                    level = max(
                        [schedule.index(next(s for s in schedule if dep in s)) for dep in deps],
                        default=-1
                    ) + 1

                    # Ensure schedule has enough levels
                    while len(schedule) <= level:
                        schedule.append([])

                    schedule[level].append(task_id)
                    processed.add(task_id)

            return schedule

        except Exception as e:
            console.print(f"[red]Error creating schedule: {e}[/red]")
            return [[task["id"]] for task in plan["subtasks"]]

    def _graph_to_dict(self) -> Dict[str, Any]:
        """Convert dependency graph to dictionary format.

        Returns:
            Graph as dictionary
        """
        return {
            "nodes": [
                {
                    "id": node,
                    **self.dependency_graph.nodes[node]
                }
                for node in self.dependency_graph.nodes()
            ],
            "edges": [
                {"from": u, "to": v}
                for u, v in self.dependency_graph.edges()
            ]
        }

    def _visualize_plan(self, plan: Dict[str, Any]) -> None:
        """Visualize plan as tree.

        Args:
            plan: Plan dictionary
        """
        tree = Tree(f"[bold cyan]Execution Plan[/bold cyan]")

        for i, subtask in enumerate(plan["subtasks"], 1):
            task_branch = tree.add(
                f"[yellow]{i}. {subtask['id']}[/yellow]: {subtask['description'][:60]}..."
            )
            if subtask.get("dependencies"):
                task_branch.add(f"[blue]Dependencies: {', '.join(subtask['dependencies'])}[/blue]")
            task_branch.add(
                f"[magenta]Complexity: {subtask.get('estimated_complexity', 'medium')}[/magenta]"
            )

        console.print(tree)

    def get_execution_order(self) -> List[str]:
        """Get execution order from dependency graph.

        Returns:
            List of task IDs in execution order
        """
        try:
            return list(nx.topological_sort(self.dependency_graph))
        except Exception:
            return list(self.dependency_graph.nodes())

    async def plan(self, objective: str) -> Dict[str, Any]:
        """Simplified planning method for natural language objectives.

        Args:
            objective: Natural language description of what to build

        Returns:
            Dictionary with:
                - plan_summary: Brief description
                - tasks: List of subtasks with descriptions
                - architecture: Suggested file structure
                - technologies: Required technologies
        """
        console.print(f"[yellow]{self.name}: Planning for objective: {objective}[/yellow]")

        prompt = f"""
You are a planning agent. Given the following objective, create a detailed plan.

Objective: {objective}

Think through this step-by-step:

1. **Understand Requirements**: What exactly needs to be built?
2. **Break Down Tasks**: What are the logical steps to complete this?
3. **Design Architecture**: What files are needed?
4. **Identify Technologies**: What languages/frameworks should be used?

Provide your response in EXACTLY this JSON format (no other text):

{{
    "plan_summary": "Brief 1-2 sentence description of what will be built",
    "tasks": [
        {{"id": 1, "description": "Specific task description"}},
        {{"id": 2, "description": "Another specific task"}}
    ],
    "architecture": {{
        "files": ["filename1.ext", "filename2.ext"]
    }},
    "technologies": ["Tech1", "Tech2", "Tech3"]
}}

Remember: Output ONLY the JSON object, nothing else.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        try:
            response = self.llm_client.chat(messages, temperature=0.3)

            # Extract JSON from response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                plan = json.loads(json_str)

                # Validate required fields
                if not all(key in plan for key in ["plan_summary", "tasks", "architecture", "technologies"]):
                    raise ValueError("Missing required fields in plan")

                console.print("[green]✓ Plan created successfully[/green]")

                if self.memory:
                    self.memory.add_message(
                        role="agent",
                        content=f"[{self.name}] Created plan: {plan['plan_summary']}",
                        metadata={"objective": objective, "plan": plan}
                    )

                return plan
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            console.print(f"[red]{self.name}: Error creating plan: {e}[/red]")
            # Return a fallback plan
            return {
                "plan_summary": f"Implementation of: {objective}",
                "tasks": [
                    {"id": 1, "description": objective}
                ],
                "architecture": {
                    "files": ["main.py"]
                },
                "technologies": ["Python"]
            }
