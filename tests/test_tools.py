"""Tests for tool system."""

import pytest
import tempfile
from pathlib import Path

from src.tools.fileio import (
    create_file, read_file, write_file, delete_file,
    list_directory, create_directory, FileOperationError
)
from src.tools.executor import execute_python, execute_shell, validate_python_syntax
from src.tools.arxiv import estimate_difficulty


class TestFileOperations:
    """Test file I/O operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_create_and_read_file(self, temp_dir):
        """Test file creation and reading."""
        filepath = str(temp_dir / "test.txt")
        content = "Hello, World!"

        # Create file
        result = create_file(filepath, content)
        assert result["status"] == "success"

        # Read file
        read_content = read_file(filepath)
        assert read_content == content

    def test_write_file(self, temp_dir):
        """Test writing to file."""
        filepath = str(temp_dir / "write_test.txt")

        # Write
        result = write_file(filepath, "Line 1\n")
        assert result["status"] == "success"

        # Append
        write_file(filepath, "Line 2\n", append=True)

        content = read_file(filepath)
        assert "Line 1" in content
        assert "Line 2" in content

    def test_delete_file(self, temp_dir):
        """Test file deletion."""
        filepath = str(temp_dir / "delete_test.txt")

        create_file(filepath, "content")
        assert Path(filepath).exists()

        delete_file(filepath)
        assert not Path(filepath).exists()

    def test_list_directory(self, temp_dir):
        """Test directory listing."""
        # Create some files
        create_file(str(temp_dir / "file1.txt"), "")
        create_file(str(temp_dir / "file2.txt"), "")
        create_file(str(temp_dir / "file3.py"), "")

        # List all files
        files = list_directory(str(temp_dir))
        assert len(files) == 3

        # List with pattern
        txt_files = list_directory(str(temp_dir), pattern="*.txt")
        assert len(txt_files) == 2

    def test_create_directory(self, temp_dir):
        """Test directory creation."""
        dirpath = str(temp_dir / "subdir" / "nested")

        result = create_directory(dirpath, parents=True)
        assert result["status"] == "success"
        assert Path(dirpath).exists()
        assert Path(dirpath).is_dir()

    def test_safe_path_validation(self, temp_dir):
        """Test path safety validation."""
        # This should fail (path traversal attempt)
        with pytest.raises(FileOperationError):
            read_file("../../etc/passwd", base_dir=str(temp_dir))


class TestCodeExecution:
    """Test code execution tools."""

    def test_execute_valid_python(self):
        """Test executing valid Python code."""
        code = """
print("Hello, World!")
result = 2 + 2
print(f"Result: {result}")
"""
        result = execute_python(code, timeout=5)

        assert result["status"] == "success"
        assert result["return_code"] == 0
        assert "Hello, World!" in result["stdout"]
        assert "Result: 4" in result["stdout"]

    def test_execute_invalid_python(self):
        """Test executing invalid Python code."""
        code = "print('unclosed string"

        result = execute_python(code, timeout=5)
        assert result["status"] == "error"
        assert result["return_code"] != 0

    def test_python_timeout(self):
        """Test Python execution timeout."""
        code = """
import time
time.sleep(100)  # Sleep longer than timeout
"""
        result = execute_python(code, timeout=1)
        assert result["status"] == "timeout"

    def test_validate_python_syntax(self):
        """Test Python syntax validation."""
        # Valid code
        valid_code = "def hello():\n    print('Hello')"
        result = validate_python_syntax(valid_code)
        assert result["status"] == "valid"

        # Invalid code
        invalid_code = "def hello(\n    print('Hello')"
        result = validate_python_syntax(invalid_code)
        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0

    def test_execute_shell_safe(self):
        """Test safe shell command execution."""
        result = execute_shell("echo 'Hello'", timeout=5)
        assert result["status"] == "success"
        assert "Hello" in result["stdout"]

    def test_execute_shell_dangerous_blocked(self):
        """Test that dangerous commands are blocked."""
        result = execute_shell("rm -rf /", timeout=5, safe_mode=True)
        assert result["status"] == "blocked"


class TestArxivTools:
    """Test arXiv integration tools."""

    def test_estimate_difficulty(self):
        """Test paper difficulty estimation."""
        # Mock paper object
        class MockPaper:
            def __init__(self, abstract):
                self.abstract = abstract

        # Beginner paper
        beginner = MockPaper("This is an introductory survey on machine learning...")
        assert estimate_difficulty(beginner) == "beginner"

        # Advanced paper
        advanced = MockPaper(
            "We present a theoretical analysis with formal proof of convergence "
            "and asymptotic complexity bounds..."
        )
        assert estimate_difficulty(advanced) == "advanced"

        # Intermediate paper
        intermediate = MockPaper("We propose a new method for image classification...")
        assert estimate_difficulty(intermediate) == "intermediate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
