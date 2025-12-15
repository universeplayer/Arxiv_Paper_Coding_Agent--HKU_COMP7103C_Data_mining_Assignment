"""Code execution tools with sandboxing and timeout handling."""

import subprocess
import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console

console = Console()


class ExecutionError(Exception):
    """Exception raised for code execution errors."""

    pass


def execute_python(
    code: str,
    timeout: int = 30,
    capture_output: bool = True,
    working_dir: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Execute Python code in a subprocess.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
        capture_output: Whether to capture stdout/stderr
        working_dir: Working directory for execution
        env_vars: Additional environment variables

    Returns:
        Dictionary with status, output, and errors
    """
    try:
        console.print("[blue]Executing Python code...[/blue]")

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Execute code
            result = subprocess.run(
                [sys.executable, temp_file],
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                cwd=working_dir,
                env=env
            )

            output = {
                "status": "success" if result.returncode == 0 else "error",
                "return_code": result.returncode,
                "stdout": result.stdout if capture_output else "",
                "stderr": result.stderr if capture_output else "",
            }

            if result.returncode == 0:
                console.print("[green]Python code executed successfully[/green]")
            else:
                console.print(f"[yellow]Python code failed with code {result.returncode}[/yellow]")

            return output

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    except subprocess.TimeoutExpired:
        console.print(f"[red]Python execution timed out after {timeout}s[/red]")
        return {
            "status": "timeout",
            "error": f"Execution timed out after {timeout} seconds"
        }
    except Exception as e:
        console.print(f"[red]Error executing Python code: {e}[/red]")
        return {
            "status": "error",
            "error": str(e)
        }


def execute_shell(
    command: str,
    timeout: int = 30,
    shell: bool = True,
    capture_output: bool = True,
    working_dir: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    safe_mode: bool = True
) -> Dict[str, Any]:
    """Execute shell command.

    Args:
        command: Shell command to execute
        timeout: Execution timeout in seconds
        shell: Whether to execute in shell
        capture_output: Whether to capture stdout/stderr
        working_dir: Working directory for execution
        env_vars: Additional environment variables
        safe_mode: If True, block dangerous commands

    Returns:
        Dictionary with status, output, and errors
    """
    try:
        # Safety check for dangerous commands
        if safe_mode:
            dangerous_patterns = ["rm -rf", "mkfs", "dd if=", "> /dev/", ":(){ :|:& }"]
            for pattern in dangerous_patterns:
                if pattern in command:
                    console.print(f"[red]Blocked dangerous command: {command}[/red]")
                    return {
                        "status": "blocked",
                        "error": f"Command blocked for safety: contains '{pattern}'"
                    }

        console.print(f"[blue]Executing shell command: {command}[/blue]")

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Execute command
        result = subprocess.run(
            command,
            shell=shell,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            cwd=working_dir,
            env=env
        )

        output = {
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "stdout": result.stdout if capture_output else "",
            "stderr": result.stderr if capture_output else "",
            "command": command
        }

        if result.returncode == 0:
            console.print("[green]Command executed successfully[/green]")
        else:
            console.print(f"[yellow]Command failed with code {result.returncode}[/yellow]")

        return output

    except subprocess.TimeoutExpired:
        console.print(f"[red]Command timed out after {timeout}s[/red]")
        return {
            "status": "timeout",
            "error": f"Command timed out after {timeout} seconds",
            "command": command
        }
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")
        return {
            "status": "error",
            "error": str(e),
            "command": command
        }


def execute_script(
    filepath: str,
    interpreter: str = "python",
    args: Optional[List[str]] = None,
    timeout: int = 60,
    capture_output: bool = True,
    working_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a script file.

    Args:
        filepath: Path to script file
        interpreter: Interpreter to use (python, bash, node, etc.)
        args: Command-line arguments
        timeout: Execution timeout
        capture_output: Whether to capture output
        working_dir: Working directory

    Returns:
        Dictionary with status, output, and errors
    """
    try:
        script_path = Path(filepath)
        if not script_path.exists():
            return {
                "status": "error",
                "error": f"Script file {filepath} not found"
            }

        console.print(f"[blue]Executing script: {filepath}[/blue]")

        # Build command
        command = [interpreter, str(script_path)]
        if args:
            command.extend(args)

        # Execute
        result = subprocess.run(
            command,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            cwd=working_dir or script_path.parent
        )

        output = {
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "stdout": result.stdout if capture_output else "",
            "stderr": result.stderr if capture_output else "",
            "script": filepath
        }

        if result.returncode == 0:
            console.print(f"[green]Script {filepath} executed successfully[/green]")
        else:
            console.print(f"[yellow]Script failed with code {result.returncode}[/yellow]")

        return output

    except subprocess.TimeoutExpired:
        console.print(f"[red]Script timed out after {timeout}s[/red]")
        return {
            "status": "timeout",
            "error": f"Script timed out after {timeout} seconds",
            "script": filepath
        }
    except Exception as e:
        console.print(f"[red]Error executing script: {e}[/red]")
        return {
            "status": "error",
            "error": str(e),
            "script": filepath
        }


def validate_python_syntax(code: str) -> Dict[str, Any]:
    """Validate Python code syntax without executing.

    Args:
        code: Python code to validate

    Returns:
        Dictionary with validation status and errors
    """
    try:
        compile(code, "<string>", "exec")
        console.print("[green]Python syntax valid[/green]")
        return {"status": "valid", "errors": []}
    except SyntaxError as e:
        console.print(f"[red]Syntax error: {e}[/red]")
        return {
            "status": "invalid",
            "errors": [
                {
                    "type": "SyntaxError",
                    "message": str(e),
                    "line": e.lineno,
                    "offset": e.offset
                }
            ]
        }
    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        return {
            "status": "error",
            "errors": [{"type": type(e).__name__, "message": str(e)}]
        }
