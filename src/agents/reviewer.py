"""Review agent for quality assessment and testing."""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.agents.base_agent import BaseAgent, Task, AgentResponse, Message
from rich.console import Console
from rich.table import Table

console = Console()


class ReviewerAgent(BaseAgent):
    """Agent responsible for code review and quality assessment."""

    def __init__(self, **kwargs):
        """Initialize reviewer agent."""
        super().__init__(name="ReviewerAgent", temperature=0.2, **kwargs)

    def get_system_prompt(self) -> str:
        """Get system prompt for reviewer."""
        return """You are an expert code reviewer and quality assurance specialist focused on:
1. Code quality and best practices
2. Security vulnerabilities
3. Performance optimization
4. Test coverage and correctness
5. Documentation quality

Be thorough, constructive, and specific in your reviews.
Provide actionable feedback and concrete suggestions for improvement."""

    def think(self, task: Task, context: Optional[str] = None) -> str:
        """Plan review approach.

        Args:
            task: Review task
            context: Additional context

        Returns:
            Review plan
        """
        console.print(f"[yellow]{self.name}: Planning review...[/yellow]")

        prompt = f"""
Review Task: {task.description}

{f"Context: {context}" if context else ""}

Plan the review by considering:

1. Quality Criteria:
   - What makes code high quality?
   - What are the acceptance criteria?
   - What standards should be applied?

2. Review Checklist:
   - Functionality correctness
   - Code structure and organization
   - Error handling
   - Performance considerations
   - Security concerns
   - Documentation quality
   - Test coverage

3. Testing Strategy:
   - What tests should be run?
   - What edge cases to check?
   - How to validate behavior?

Output your review plan as JSON:
{{
  "review_aspects": ["aspect1", "aspect2", ...],
  "test_cases": ["test1", "test2", ...],
  "security_checks": ["check1", "check2", ...],
  "quality_metrics": ["metric1", "metric2", ...]
}}
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        thought = self.llm_client.chat(messages, temperature=0.2)

        if self.memory:
            self.memory.add_message(
                role="agent",
                content=f"[{self.name}] Review plan: {thought}",
                metadata={"task_id": task.task_id}
            )

        return thought

    def act(self, task: Task, thought: str) -> AgentResponse:
        """Perform code review.

        Args:
            task: Review task
            thought: Review plan

        Returns:
            AgentResponse with review results
        """
        console.print(f"[yellow]{self.name}: Performing review...[/yellow]")

        try:
            # Extract review plan
            review_plan = self._extract_review_plan(thought)

            # Get artifacts to review
            artifacts = task.metadata.get("artifacts", []) if task.metadata else []

            review_results = {
                "artifacts_reviewed": [],
                "issues": [],
                "suggestions": [],
                "quality_score": 0.0,
                "passed": False
            }

            total_score = 0.0
            num_reviews = 0

            for artifact_path in artifacts:
                # Review each artifact
                result = self._review_artifact(artifact_path, review_plan)
                review_results["artifacts_reviewed"].append(result)

                total_score += result["score"]
                num_reviews += 1

                review_results["issues"].extend(result.get("issues", []))
                review_results["suggestions"].extend(result.get("suggestions", []))

            # Calculate overall score
            if num_reviews > 0:
                review_results["quality_score"] = total_score / num_reviews
                review_results["passed"] = review_results["quality_score"] >= 0.7

            # Display results
            self._display_review_results(review_results)

            if self.memory:
                self.memory.add_message(
                    role="agent",
                    content=f"[{self.name}] Review complete. Score: {review_results['quality_score']:.2f}",
                    metadata={"task_id": task.task_id, "results": review_results}
                )

            return AgentResponse(
                success=review_results["passed"],
                data=review_results,
                message=f"Review complete. Quality score: {review_results['quality_score']:.2f}/1.0"
            )

        except Exception as e:
            console.print(f"[red]{self.name}: Error performing review: {e}[/red]")
            return AgentResponse(
                success=False,
                data={},
                message=f"Error performing review: {str(e)}"
            )

    def _extract_review_plan(self, thought: str) -> Dict[str, Any]:
        """Extract review plan from thought.

        Args:
            thought: Thought text

        Returns:
            Review plan dictionary
        """
        try:
            start_idx = thought.find("{")
            end_idx = thought.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = thought[start_idx:end_idx]
                plan = json.loads(json_str)
                return plan

        except json.JSONDecodeError:
            pass

        # Default plan
        return {
            "review_aspects": ["code_quality", "functionality", "documentation"],
            "test_cases": [],
            "security_checks": ["input_validation", "error_handling"],
            "quality_metrics": ["readability", "maintainability"]
        }

    def _review_artifact(self, artifact_path: str, review_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Review a single artifact.

        Args:
            artifact_path: Path to artifact
            review_plan: Review plan

        Returns:
            Review results for artifact
        """
        console.print(f"[blue]{self.name}: Reviewing {artifact_path}...[/blue]")

        try:
            # Read artifact
            if "read_file" in self.tools:
                content = self.use_tool("read_file", filepath=artifact_path)
            elif self.memory:
                artifact = self.memory.get_artifact(artifact_path)
                content = artifact.content if artifact else ""
            else:
                content = ""

            if not content:
                return {
                    "path": artifact_path,
                    "score": 0.0,
                    "issues": ["Could not read artifact"],
                    "suggestions": []
                }

            # Perform review
            prompt = f"""
Review the following code:

File: {artifact_path}
Review Aspects: {', '.join(review_plan.get('review_aspects', []))}

Code:
```
{content[:3000]}  # Limit for context
```

Provide a detailed review including:
1. Issues found (bugs, anti-patterns, security concerns)
2. Suggestions for improvement
3. Quality score (0.0-1.0)

Output as JSON:
{{
  "score": 0.85,
  "issues": [
    {{"severity": "high|medium|low", "description": "...", "line": 10}}
  ],
  "suggestions": [
    {{"type": "improvement|optimization|style", "description": "..."}}
  ],
  "strengths": ["strength1", "strength2"],
  "summary": "Overall assessment"
}}
"""

            messages = [
                Message(role="system", content=self.get_system_prompt()),
                Message(role="user", content=prompt)
            ]

            review = self.llm_client.chat(messages, temperature=0.2)

            # Parse review
            review_data = self._parse_review(review)
            review_data["path"] = artifact_path

            return review_data

        except Exception as e:
            console.print(f"[red]Error reviewing {artifact_path}: {e}[/red]")
            return {
                "path": artifact_path,
                "score": 0.0,
                "issues": [{"severity": "high", "description": f"Review error: {e}"}],
                "suggestions": []
            }

    def _parse_review(self, review_text: str) -> Dict[str, Any]:
        """Parse review from LLM response.

        Args:
            review_text: Review text

        Returns:
            Parsed review dictionary
        """
        try:
            start_idx = review_text.find("{")
            end_idx = review_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = review_text[start_idx:end_idx]
                review = json.loads(json_str)
                return review

        except json.JSONDecodeError:
            pass

        # Extract score from text if JSON parsing fails
        import re
        score_match = re.search(r'score["\s:]+([0-9.]+)', review_text.lower())
        score = float(score_match.group(1)) if score_match else 0.5

        return {
            "score": score,
            "issues": [],
            "suggestions": [],
            "strengths": [],
            "summary": review_text[:200]
        }

    def _display_review_results(self, results: Dict[str, Any]) -> None:
        """Display review results in a formatted table.

        Args:
            results: Review results
        """
        table = Table(title="Code Review Results", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Quality Score", f"{results['quality_score']:.2f}/1.0")
        table.add_row("Status", "PASSED" if results["passed"] else "FAILED")
        table.add_row("Artifacts Reviewed", str(len(results["artifacts_reviewed"])))
        table.add_row("Issues Found", str(len(results["issues"])))
        table.add_row("Suggestions", str(len(results["suggestions"])))

        console.print(table)

        # Display issues
        if results["issues"]:
            console.print("\n[bold red]Issues Found:[/bold red]")
            for i, issue in enumerate(results["issues"][:10], 1):  # Limit to 10
                severity = issue.get("severity", "medium")
                desc = issue.get("description", str(issue))
                console.print(f"  {i}. [{severity.upper()}] {desc}")

        # Display suggestions
        if results["suggestions"]:
            console.print("\n[bold blue]Suggestions:[/bold blue]")
            for i, suggestion in enumerate(results["suggestions"][:5], 1):  # Limit to 5
                desc = suggestion.get("description", str(suggestion))
                console.print(f"  {i}. {desc}")

    def run_tests(self, test_files: List[str]) -> Dict[str, Any]:
        """Run test files and collect results.

        Args:
            test_files: List of test file paths

        Returns:
            Test results dictionary
        """
        console.print(f"[blue]{self.name}: Running tests...[/blue]")

        results = {
            "total": len(test_files),
            "passed": 0,
            "failed": 0,
            "errors": []
        }

        for test_file in test_files:
            try:
                if "execute_python" in self.tools:
                    # Read test file
                    if "read_file" in self.tools:
                        test_code = self.use_tool("read_file", filepath=test_file)

                        # Execute test
                        exec_result = self.use_tool("execute_python", code=test_code, timeout=30)

                        if exec_result["status"] == "success" and exec_result["return_code"] == 0:
                            results["passed"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append({
                                "file": test_file,
                                "error": exec_result.get("stderr", "Unknown error")
                            })

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": test_file, "error": str(e)})

        console.print(f"[green]Tests: {results['passed']} passed, {results['failed']} failed[/green]")
        return results

    async def review(self, objective: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Review generated artifacts for quality.

        Args:
            objective: Original objective
            artifacts: Dictionary from CoderAgent with generated_files

        Returns:
            Dictionary with:
                - quality_score: Score from 0-100
                - suggestions: List of improvement suggestions
                - issues: List of issues found
                - passed: Boolean indicating if quality threshold met
        """
        console.print(f"[yellow]{self.name}: Reviewing artifacts for: {objective}[/yellow]")

        generated_files = artifacts.get("generated_files", [])

        if not generated_files:
            return {
                "quality_score": 0,
                "suggestions": ["No files were generated"],
                "issues": ["No artifacts to review"],
                "passed": False
            }

        all_issues = []
        all_suggestions = []
        file_scores = []

        for filepath in generated_files:
            try:
                # Read file content
                file_path = Path(filepath)
                if not file_path.exists():
                    console.print(f"[red]File not found: {filepath}[/red]")
                    continue

                content = file_path.read_text(encoding='utf-8')
                console.print(f"[blue]Reviewing {file_path.name}...[/blue]")

                # Review this file
                file_review = await self._review_single_file(
                    filepath=file_path.name,
                    content=content,
                    objective=objective
                )

                file_scores.append(file_review["score"])
                all_issues.extend(file_review.get("issues", []))
                all_suggestions.extend(file_review.get("suggestions", []))

            except Exception as e:
                console.print(f"[red]Error reviewing {filepath}: {e}[/red]")
                file_scores.append(50)  # Default mediocre score
                all_issues.append(f"Could not fully review {Path(filepath).name}: {e}")

        # Calculate overall quality score
        if file_scores:
            quality_score = int(sum(file_scores) / len(file_scores))
        else:
            quality_score = 0

        passed = quality_score >= 60  # Threshold for passing

        result = {
            "quality_score": quality_score,
            "suggestions": all_suggestions[:5],  # Limit to top 5
            "issues": all_issues[:10],  # Limit to top 10
            "passed": passed,
            "files_reviewed": len(generated_files)
        }

        # Display summary
        console.print(f"\n[bold]Review Summary:[/bold]")
        console.print(f"  Quality Score: {quality_score}/100")
        console.print(f"  Files Reviewed: {len(generated_files)}")
        console.print(f"  Issues Found: {len(all_issues)}")
        console.print(f"  Status: {'PASSED' if passed else 'NEEDS IMPROVEMENT'}")

        if self.memory:
            self.memory.add_message(
                role="agent",
                content=f"[{self.name}] Review complete. Score: {quality_score}/100",
                metadata={"objective": objective, "review": result}
            )

        return result

    async def _review_single_file(self, filepath: str, content: str, objective: str) -> Dict[str, Any]:
        """Review a single file.

        Args:
            filepath: Name of the file
            content: File content
            objective: Original objective

        Returns:
            Dictionary with score, issues, suggestions
        """
        # Limit content length for API
        content_preview = content[:2000] if len(content) > 2000 else content

        prompt = f"""
Review the following code file for quality:

Objective: {objective}
Filename: {filepath}

Code:
```
{content_preview}
```

Evaluate the code on:
1. **Functionality**: Does it accomplish the objective?
2. **Code Quality**: Is it well-structured and readable?
3. **Best Practices**: Does it follow language conventions?
4. **Completeness**: Are there TODOs or missing parts?
5. **Error Handling**: Does it handle edge cases?

Provide your review in EXACTLY this JSON format:

{{
    "score": 85,
    "issues": ["Issue description 1", "Issue description 2"],
    "suggestions": ["Suggestion 1", "Suggestion 2"],
    "summary": "Brief overall assessment"
}}

Score should be 0-100 where:
- 90-100: Excellent, production-ready
- 70-89: Good, minor improvements needed
- 50-69: Acceptable, several improvements needed
- 0-49: Needs significant work

Output ONLY the JSON, no other text.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        try:
            response = self.llm_client.chat(messages, temperature=0.2)

            # Parse JSON
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                review = json.loads(json_str)

                return {
                    "score": review.get("score", 70),
                    "issues": review.get("issues", []),
                    "suggestions": review.get("suggestions", []),
                    "summary": review.get("summary", "Review complete")
                }
            else:
                raise ValueError("No JSON in response")

        except Exception as e:
            console.print(f"[yellow]Warning: Could not parse review for {filepath}: {e}[/yellow]")
            # Return a default review
            return {
                "score": 70,
                "issues": [],
                "suggestions": ["Manual review recommended"],
                "summary": "Automated review encountered issues"
            }
