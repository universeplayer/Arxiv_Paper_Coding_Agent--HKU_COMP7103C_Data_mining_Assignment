"""Coding agent for implementation tasks."""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.agents.base_agent import BaseAgent, Task, AgentResponse, Message
from src.core.memory import Artifact
from rich.console import Console

console = Console()


class CoderAgent(BaseAgent):
    """Agent responsible for code implementation."""

    def __init__(self, workspace: Optional[Path] = None, **kwargs):
        """Initialize coder agent."""
        super().__init__(name="CoderAgent", temperature=0.5, **kwargs)
        self.code_context: Dict[str, str] = {}
        self.workspace = workspace or Path("workspace")

    def get_system_prompt(self) -> str:
        """Get system prompt for coder."""
        return """You are an expert coding agent specialized in:
1. Writing clean, efficient, and well-documented code
2. Following best practices and design patterns
3. Implementing features based on specifications
4. Multi-language programming (Python, JavaScript, TypeScript, etc.)

Always:
- Write production-ready code with proper error handling
- Include docstrings and comments
- Follow language-specific conventions (PEP 8 for Python, etc.)
- Consider edge cases and validation
- Make code modular and maintainable"""

    def think(self, task: Task, context: Optional[str] = None) -> str:
        """Plan code implementation approach.

        Args:
            task: Task to implement
            context: Additional context

        Returns:
            Implementation plan
        """
        console.print(f"[yellow]{self.name}: Planning implementation...[/yellow]")

        prompt = f"""
Task: {task.description}

{f"Context: {context}" if context else ""}

Plan the implementation by considering:

1. Requirements Analysis:
   - What functionality is needed?
   - What are the inputs and outputs?
   - What edge cases exist?

2. Design Decisions:
   - What data structures are appropriate?
   - What algorithms or patterns should be used?
   - How to structure the code?

3. Implementation Strategy:
   - What files need to be created/modified?
   - What functions/classes are needed?
   - What dependencies are required?

4. Testing Approach:
   - What tests are needed?
   - How to validate correctness?

Provide your reasoning, then output a JSON implementation plan:
{{
  "files": [
    {{
      "path": "path/to/file.py",
      "purpose": "description",
      "components": ["function1", "class1", ...]
    }}
  ],
  "key_functions": ["func1", "func2", ...],
  "dependencies": ["package1", "package2", ...],
  "test_strategy": "description"
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
                content=f"[{self.name}] Implementation plan: {thought}",
                metadata={"task_id": task.task_id}
            )

        return thought

    def act(self, task: Task, thought: str) -> AgentResponse:
        """Implement code based on plan.

        Args:
            task: Task to implement
            thought: Implementation plan

        Returns:
            AgentResponse with implementation results
        """
        console.print(f"[yellow]{self.name}: Implementing code...[/yellow]")

        try:
            # Extract implementation plan
            impl_plan = self._extract_implementation_plan(thought)

            # Generate code for each file
            generated_files = []
            for file_spec in impl_plan.get("files", []):
                code = self._generate_code(
                    filepath=file_spec["path"],
                    purpose=file_spec["purpose"],
                    components=file_spec.get("components", []),
                    context=task.description
                )

                if code:
                    # Save code using tools (if available)
                    if "create_file" in self.tools:
                        self.use_tool(
                            "create_file",
                            filepath=file_spec["path"],
                            content=code,
                            overwrite=True
                        )

                    # Track artifact
                    if self.memory:
                        artifact = Artifact(
                            path=file_spec["path"],
                            content=code,
                            artifact_type="code",
                            metadata={
                                "purpose": file_spec["purpose"],
                                "task_id": task.task_id
                            }
                        )
                        self.memory.add_artifact(artifact)

                    generated_files.append(file_spec["path"])

            return AgentResponse(
                success=True,
                data={
                    "implementation_plan": impl_plan,
                    "generated_files": generated_files
                },
                message=f"Successfully implemented {len(generated_files)} files",
                artifacts=generated_files
            )

        except Exception as e:
            console.print(f"[red]{self.name}: Error implementing code: {e}[/red]")
            return AgentResponse(
                success=False,
                data={},
                message=f"Error implementing code: {str(e)}"
            )

    def _extract_implementation_plan(self, thought: str) -> Dict[str, Any]:
        """Extract implementation plan from thought.

        Args:
            thought: Thought text

        Returns:
            Implementation plan dictionary
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
            "files": [{"path": "output.py", "purpose": "Implementation", "components": []}],
            "key_functions": [],
            "dependencies": [],
            "test_strategy": "Manual testing"
        }

    def _generate_code(
        self,
        filepath: str,
        purpose: str,
        components: List[str],
        context: str
    ) -> str:
        """Generate code for a specific file.

        Args:
            filepath: Path to the file
            purpose: Purpose of the file
            components: List of components (functions, classes)
            context: Overall context

        Returns:
            Generated code as string
        """
        console.print(f"[blue]{self.name}: Generating code for {filepath}...[/blue]")

        file_ext = Path(filepath).suffix
        language = self._detect_language(file_ext)

        prompt = f"""
Generate complete, production-ready code for:

File: {filepath}
Language: {language}
Purpose: {purpose}
Required Components: {', '.join(components) if components else 'As needed'}

Context: {context}

Requirements:
1. Write complete, functional code (no TODOs or placeholders)
2. Include proper imports and dependencies
3. Add comprehensive docstrings/comments
4. Follow {language} best practices and conventions
5. Include error handling
6. Make code modular and maintainable

Output ONLY the code, no explanations before or after.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        code = self.llm_client.chat(messages, temperature=0.5)

        # Clean up code (remove markdown fences if present)
        code = self._clean_code(code, language)

        return code

    def _detect_language(self, file_ext: str) -> str:
        """Detect programming language from file extension.

        Args:
            file_ext: File extension

        Returns:
            Language name
        """
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".html": "HTML",
            ".css": "CSS",
            ".jsx": "React JSX",
            ".tsx": "React TSX",
        }
        return lang_map.get(file_ext, "Python")

    def _clean_code(self, code: str, language: str) -> str:
        """Clean generated code by removing markdown fences.

        Args:
            code: Raw code from LLM
            language: Programming language

        Returns:
            Cleaned code
        """
        # Remove markdown code fences
        lines = code.split("\n")
        cleaned_lines = []

        in_code_block = False
        for line in lines:
            stripped = line.strip()

            # Skip fence markers
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def modify_code(
        self,
        filepath: str,
        modification: str,
        reason: str
    ) -> Dict[str, Any]:
        """Modify existing code.

        Args:
            filepath: Path to file to modify
            modification: Description of modification
            reason: Reason for modification

        Returns:
            Dictionary with modification results
        """
        console.print(f"[blue]{self.name}: Modifying {filepath}...[/blue]")

        try:
            # Read existing code
            if "read_file" in self.tools:
                existing_code = self.use_tool("read_file", filepath=filepath)
            else:
                return {"status": "error", "message": "read_file tool not available"}

            # Generate modification
            prompt = f"""
Modify the following code:

File: {filepath}
Modification: {modification}
Reason: {reason}

Current Code:
```
{existing_code}
```

Provide the COMPLETE modified code (not just the changes).
Output ONLY the code, no explanations.
"""

            messages = [
                Message(role="system", content=self.get_system_prompt()),
                Message(role="user", content=prompt)
            ]

            modified_code = self.llm_client.chat(messages, temperature=0.3)
            modified_code = self._clean_code(modified_code, self._detect_language(Path(filepath).suffix))

            # Save modified code
            if "write_file" in self.tools:
                self.use_tool("write_file", filepath=filepath, content=modified_code)

            if self.memory:
                artifact = Artifact(
                    path=filepath,
                    content=modified_code,
                    artifact_type="code",
                    metadata={"modification": modification, "reason": reason}
                )
                self.memory.add_artifact(artifact)

            return {
                "status": "success",
                "filepath": filepath,
                "message": f"Modified {filepath}"
            }

        except Exception as e:
            console.print(f"[red]Error modifying code: {e}[/red]")
            return {"status": "error", "message": str(e)}

    async def implement(self, objective: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Implement code based on objective and plan.

        Args:
            objective: Natural language objective
            plan: Plan dictionary from PlannerAgent

        Returns:
            Dictionary with:
                - generated_files: List of file paths
                - workspace: Path to workspace directory
        """
        console.print(f"[yellow]{self.name}: Implementing: {objective}[/yellow]")

        # Ensure workspace exists
        self.workspace.mkdir(parents=True, exist_ok=True)

        generated_files = []
        files_to_generate = plan.get("architecture", {}).get("files", ["main.py"])

        for filepath in files_to_generate:
            try:
                # Determine file type and generate appropriate code
                file_path = Path(filepath)
                ext = file_path.suffix.lower()

                console.print(f"[blue]Generating {filepath}...[/blue]")

                if ext == ".html":
                    code = await self.generate_html(objective, plan, filepath)
                elif ext == ".py":
                    code = await self.generate_python(objective, plan, filepath)
                elif ext == ".js":
                    code = await self.generate_javascript(objective, plan, filepath)
                elif ext == ".css":
                    code = await self.generate_css(objective, plan, filepath)
                else:
                    # Generic code generation
                    code = await self._generate_generic_code(objective, plan, filepath)

                # Save to workspace
                full_path = self.workspace / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(code, encoding='utf-8')

                generated_files.append(str(full_path))
                console.print(f"[green]✓ Created {filepath}[/green]")

                # Track in memory
                if self.memory:
                    from src.core.memory import Artifact
                    artifact = Artifact(
                        path=str(full_path),
                        content=code,
                        artifact_type="code",
                        metadata={"filename": filepath, "objective": objective}
                    )
                    self.memory.add_artifact(artifact)

            except Exception as e:
                console.print(f"[red]Error generating {filepath}: {e}[/red]")
                continue

        return {
            "generated_files": generated_files,
            "workspace": str(self.workspace),
            "file_count": len(generated_files)
        }

    async def generate_html(self, objective: str, plan: Dict[str, Any], filename: str) -> str:
        """Generate HTML file.

        Args:
            objective: What to build
            plan: Full plan
            filename: Target filename

        Returns:
            HTML code as string
        """
        prompt = f"""
Generate a complete, working HTML file for the following:

Objective: {objective}
Filename: {filename}
Technologies: {', '.join(plan.get('technologies', []))}

Requirements:
1. Create a complete, valid HTML5 document
2. Include proper DOCTYPE, head, and body tags
3. Add meta tags for charset and viewport
4. Include inline CSS styles or link to external CSS if mentioned
5. Add JavaScript inline or link to external JS files if mentioned
6. Make it functional and well-structured
7. Include comments explaining key sections

Output ONLY the HTML code, no explanations.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        code = self.llm_client.chat(messages, temperature=0.5)
        return self._clean_code(code, "HTML")

    async def generate_python(self, objective: str, plan: Dict[str, Any], filename: str) -> str:
        """Generate Python file.

        Args:
            objective: What to build
            plan: Full plan
            filename: Target filename

        Returns:
            Python code as string
        """
        prompt = f"""
Generate a complete, working Python file for the following:

Objective: {objective}
Filename: {filename}
Technologies: {', '.join(plan.get('technologies', []))}

Requirements:
1. Include all necessary imports
2. Add proper docstrings
3. Follow PEP 8 conventions
4. Include error handling
5. Add a main block if appropriate
6. Make it fully functional (no TODOs)
7. Include comments for complex logic

Output ONLY the Python code, no explanations.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        code = self.llm_client.chat(messages, temperature=0.5)
        return self._clean_code(code, "Python")

    async def generate_javascript(self, objective: str, plan: Dict[str, Any], filename: str) -> str:
        """Generate JavaScript file.

        Args:
            objective: What to build
            plan: Full plan
            filename: Target filename

        Returns:
            JavaScript code as string
        """
        prompt = f"""
Generate a complete, working JavaScript file for the following:

Objective: {objective}
Filename: {filename}
Technologies: {', '.join(plan.get('technologies', []))}

Requirements:
1. Use modern JavaScript (ES6+)
2. Add proper error handling
3. Include JSDoc comments
4. Make it functional and production-ready
5. Use proper event handlers if needed
6. No TODOs or placeholders

Output ONLY the JavaScript code, no explanations.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        code = self.llm_client.chat(messages, temperature=0.5)
        return self._clean_code(code, "JavaScript")

    async def generate_css(self, objective: str, plan: Dict[str, Any], filename: str) -> str:
        """Generate CSS file.

        Args:
            objective: What to build
            plan: Full plan
            filename: Target filename

        Returns:
            CSS code as string
        """
        prompt = f"""
Generate a complete, working CSS file for the following:

Objective: {objective}
Filename: {filename}

Requirements:
1. Create modern, responsive styles
2. Use proper CSS organization
3. Include comments for sections
4. Add mobile-responsive design
5. Use proper color schemes
6. Make it visually appealing

Output ONLY the CSS code, no explanations.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        code = self.llm_client.chat(messages, temperature=0.5)
        return self._clean_code(code, "CSS")

    async def _generate_generic_code(self, objective: str, plan: Dict[str, Any], filename: str) -> str:
        """Generate generic code file.

        Args:
            objective: What to build
            plan: Full plan
            filename: Target filename

        Returns:
            Code as string
        """
        file_ext = Path(filename).suffix
        prompt = f"""
Generate a complete, working code file for the following:

Objective: {objective}
Filename: {filename}
File Type: {file_ext}
Technologies: {', '.join(plan.get('technologies', []))}

Requirements:
1. Create complete, functional code
2. Include proper comments
3. Follow best practices for this file type
4. Make it production-ready
5. No TODOs or placeholders

Output ONLY the code, no explanations.
"""

        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=prompt)
        ]

        code = self.llm_client.chat(messages, temperature=0.5)
        language = self._detect_language(file_ext)
        return self._clean_code(code, language)
