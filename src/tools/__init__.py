"""Tools for agent system."""

from src.tools.fileio import (
    create_file,
    read_file,
    write_file,
    delete_file,
    list_directory,
    create_directory,
)
from src.tools.web import web_search, fetch_url
from src.tools.executor import execute_python, execute_shell
from src.tools.arxiv import fetch_papers, search_arxiv, parse_paper_metadata

__all__ = [
    # File operations
    "create_file",
    "read_file",
    "write_file",
    "delete_file",
    "list_directory",
    "create_directory",
    # Web operations
    "web_search",
    "fetch_url",
    # Code execution
    "execute_python",
    "execute_shell",
    # arXiv
    "fetch_papers",
    "search_arxiv",
    "parse_paper_metadata",
]
