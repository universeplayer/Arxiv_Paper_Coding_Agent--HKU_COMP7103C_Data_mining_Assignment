# Contributing

Thank you for your interest in contributing to the Arxiv Paper Coding Agent project!

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```
3. Copy `env.example` to `.env` and add your API keys.

## Development Workflow

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes, keeping commits small and focused.
3. Run linting and tests before committing:
   ```bash
   ruff check src/ tests/
   pytest tests/ -v
   ```
4. Push your branch and open a Pull Request against `main`.

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting.
- Follow PEP 8 conventions.
- Add docstrings to all public functions and classes.
- Use type hints where practical.

## Reporting Issues

- Use GitHub Issues to report bugs or request features.
- Include steps to reproduce, expected behavior, and actual behavior.

## Pull Request Guidelines

- Keep PRs focused on a single change.
- Include a clear description of what the PR does and why.
- Ensure CI checks pass before requesting review.
- Add or update tests for any new functionality.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
