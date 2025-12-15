"""File I/O operations with safe path handling."""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console

console = Console()


class FileOperationError(Exception):
    """Exception raised for file operation errors."""

    pass


def _safe_path(path: str, base_dir: Optional[str] = None) -> Path:
    """Validate and resolve path safely.

    Args:
        path: File or directory path
        base_dir: Optional base directory to restrict operations

    Returns:
        Resolved Path object

    Raises:
        FileOperationError: If path is unsafe
    """
    try:
        resolved_path = Path(path).resolve()

        if base_dir:
            base = Path(base_dir).resolve()
            if not str(resolved_path).startswith(str(base)):
                raise FileOperationError(
                    f"Path {path} is outside base directory {base_dir}"
                )

        return resolved_path
    except Exception as e:
        raise FileOperationError(f"Invalid path {path}: {e}")


def create_file(
    filepath: str,
    content: str = "",
    overwrite: bool = False,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new file with content.

    Args:
        filepath: Path to the file
        content: Initial content
        overwrite: Whether to overwrite existing file
        base_dir: Optional base directory restriction

    Returns:
        Dictionary with status and message

    Raises:
        FileOperationError: If file creation fails
    """
    try:
        path = _safe_path(filepath, base_dir)

        if path.exists() and not overwrite:
            raise FileOperationError(f"File {filepath} already exists")

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        path.write_text(content, encoding="utf-8")

        console.print(f"[green]Created file: {filepath}[/green]")
        return {"status": "success", "path": str(path), "message": "File created"}

    except Exception as e:
        console.print(f"[red]Error creating file {filepath}: {e}[/red]")
        raise FileOperationError(f"Failed to create file: {e}")


def read_file(filepath: str, base_dir: Optional[str] = None) -> str:
    """Read file content.

    Args:
        filepath: Path to the file
        base_dir: Optional base directory restriction

    Returns:
        File content as string

    Raises:
        FileOperationError: If file reading fails
    """
    try:
        path = _safe_path(filepath, base_dir)

        if not path.exists():
            raise FileOperationError(f"File {filepath} does not exist")

        if not path.is_file():
            raise FileOperationError(f"{filepath} is not a file")

        content = path.read_text(encoding="utf-8")
        console.print(f"[blue]Read file: {filepath} ({len(content)} chars)[/blue]")
        return content

    except Exception as e:
        console.print(f"[red]Error reading file {filepath}: {e}[/red]")
        raise FileOperationError(f"Failed to read file: {e}")


def write_file(
    filepath: str,
    content: str,
    append: bool = False,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Write content to file.

    Args:
        filepath: Path to the file
        content: Content to write
        append: Whether to append or overwrite
        base_dir: Optional base directory restriction

    Returns:
        Dictionary with status and message

    Raises:
        FileOperationError: If writing fails
    """
    try:
        path = _safe_path(filepath, base_dir)

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        if append:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            action = "Appended to"
        else:
            path.write_text(content, encoding="utf-8")
            action = "Wrote to"

        console.print(f"[green]{action} file: {filepath}[/green]")
        return {"status": "success", "path": str(path), "message": f"{action} file"}

    except Exception as e:
        console.print(f"[red]Error writing file {filepath}: {e}[/red]")
        raise FileOperationError(f"Failed to write file: {e}")


def delete_file(filepath: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Delete a file.

    Args:
        filepath: Path to the file
        base_dir: Optional base directory restriction

    Returns:
        Dictionary with status and message

    Raises:
        FileOperationError: If deletion fails
    """
    try:
        path = _safe_path(filepath, base_dir)

        if not path.exists():
            raise FileOperationError(f"File {filepath} does not exist")

        if path.is_file():
            path.unlink()
            console.print(f"[yellow]Deleted file: {filepath}[/yellow]")
            return {"status": "success", "path": str(path), "message": "File deleted"}
        else:
            raise FileOperationError(f"{filepath} is not a file")

    except Exception as e:
        console.print(f"[red]Error deleting file {filepath}: {e}[/red]")
        raise FileOperationError(f"Failed to delete file: {e}")


def list_directory(
    dirpath: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    base_dir: Optional[str] = None
) -> List[str]:
    """List files in directory.

    Args:
        dirpath: Directory path
        pattern: Glob pattern for filtering
        recursive: Whether to search recursively
        base_dir: Optional base directory restriction

    Returns:
        List of file paths

    Raises:
        FileOperationError: If listing fails
    """
    try:
        path = _safe_path(dirpath, base_dir)

        if not path.exists():
            raise FileOperationError(f"Directory {dirpath} does not exist")

        if not path.is_dir():
            raise FileOperationError(f"{dirpath} is not a directory")

        if recursive:
            files = [str(p) for p in path.rglob(pattern) if p.is_file()]
        else:
            files = [str(p) for p in path.glob(pattern) if p.is_file()]

        console.print(f"[blue]Listed {len(files)} files in {dirpath}[/blue]")
        return sorted(files)

    except Exception as e:
        console.print(f"[red]Error listing directory {dirpath}: {e}[/red]")
        raise FileOperationError(f"Failed to list directory: {e}")


def create_directory(
    dirpath: str,
    parents: bool = True,
    exist_ok: bool = True,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Create a directory.

    Args:
        dirpath: Directory path
        parents: Create parent directories
        exist_ok: Don't error if directory exists
        base_dir: Optional base directory restriction

    Returns:
        Dictionary with status and message

    Raises:
        FileOperationError: If creation fails
    """
    try:
        path = _safe_path(dirpath, base_dir)

        if path.exists() and not exist_ok:
            raise FileOperationError(f"Directory {dirpath} already exists")

        path.mkdir(parents=parents, exist_ok=exist_ok)

        console.print(f"[green]Created directory: {dirpath}[/green]")
        return {"status": "success", "path": str(path), "message": "Directory created"}

    except Exception as e:
        console.print(f"[red]Error creating directory {dirpath}: {e}[/red]")
        raise FileOperationError(f"Failed to create directory: {e}")


def copy_file(
    src: str,
    dst: str,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Copy a file.

    Args:
        src: Source file path
        dst: Destination file path
        base_dir: Optional base directory restriction

    Returns:
        Dictionary with status and message

    Raises:
        FileOperationError: If copying fails
    """
    try:
        src_path = _safe_path(src, base_dir)
        dst_path = _safe_path(dst, base_dir)

        if not src_path.exists():
            raise FileOperationError(f"Source file {src} does not exist")

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)

        console.print(f"[green]Copied {src} to {dst}[/green]")
        return {"status": "success", "src": str(src_path), "dst": str(dst_path)}

    except Exception as e:
        console.print(f"[red]Error copying file: {e}[/red]")
        raise FileOperationError(f"Failed to copy file: {e}")
