# Quick Start Guide

## Installation

### Prerequisites

- Python 3.10 or higher
- pip or conda package manager
- An OpenAI API key (or compatible provider)

### Step 1: Clone and Setup

```bash
# Clone or download the repository
cd advanced_agent_system

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

Required configuration:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

Optional (for other providers):
```bash
DEEPSEEK_API_KEY=sk-your-key-here
QWEN_API_KEY=sk-your-key-here
```

### Step 3: Verify Installation

```python
# Test import
python -c "from src.core.config import get_settings; print('✓ Installation successful!')"
```

## Basic Usage

### Example 1: Generate arXiv Daily Page

The simplest way to see the system in action:

```bash
python examples/arxiv_daily.py
```

This will:
1. Fetch latest papers from arXiv (cs.AI, cs.CL, cs.LG, cs.CV)
2. Process and categorize them
3. Generate a beautiful, interactive webpage
4. Create paper detail pages
5. Generate audit logs

**Output**: Check `outputs/arxiv_daily_YYYYMMDD/index.html`

### Example 2: Using Individual Agents

```python
from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.base_agent import Task

# Initialize agents
planner = PlannerAgent()
coder = CoderAgent()

# Create a task
task = Task(
    task_id="demo_task",
    description="Create a Python function to calculate Fibonacci numbers",
    dependencies=[]
)

# Plan the task
plan_result = planner.execute(task)
print(plan_result.data)

# Implement the task
code_result = coder.execute(task)
print(code_result.message)
```

### Example 3: Using the Orchestrator

```python
from src.core.orchestrator import Orchestrator

# Initialize orchestrator
orchestrator = Orchestrator(project_name="my_project")

# Define objective
objective = """
Create a web scraper that:
1. Fetches data from a target URL
2. Parses HTML content
3. Extracts specific information
4. Saves to JSON file
"""

# Execute
results = orchestrator.execute_project(
    objective=objective,
    context="Focus on clean, maintainable code"
)

# Check results
if results['success']:
    print(f"✓ Project completed!")
    print(f"Generated files: {results['artifacts']}")
else:
    print(f"✗ Failed: {results['error']}")
```

### Example 4: Custom Tool Usage

```python
from src.core.llm_client import LLMClient
from src.agents.base_agent import BaseAgent, Task, AgentResponse
from src.tools.fileio import create_file, read_file

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="CustomAgent")
        # Register tools
        self.register_tool("create_file", create_file)
        self.register_tool("read_file", read_file)

    def think(self, task, context=None):
        return f"I will work on: {task.description}"

    def act(self, task, thought):
        # Use tools
        self.use_tool("create_file",
                     filepath="output.txt",
                     content="Hello, World!")

        content = self.use_tool("read_file", filepath="output.txt")

        return AgentResponse(
            success=True,
            data={"content": content},
            message="File created and read successfully"
        )

# Use custom agent
agent = CustomAgent()
task = Task(task_id="test", description="Test file operations", dependencies=[])
result = agent.execute(task)
print(result.message)
```

## Configuration Options

### Environment Variables

All settings can be configured via `.env` file:

```bash
# LLM Settings
DEFAULT_MODEL=gpt-4-turbo-preview
PLANNER_MODEL=gpt-4-turbo-preview
CODER_MODEL=gpt-4-turbo-preview

# System Settings
MAX_RETRIES=3
TIMEOUT_SECONDS=60
LOG_LEVEL=INFO

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=50
MAX_TOKENS_PER_REQUEST=4000

# arXiv Settings
ARXIV_MAX_RESULTS=50
ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG,cs.CV

# Output Directories
OUTPUT_DIR=./outputs
LOGS_DIR=./logs
CACHE_DIR=./cache
```

### Programmatic Configuration

```python
from src.core.config import get_settings, reload_settings

# Get settings
settings = get_settings()
print(f"Current model: {settings.default_model}")

# Modify environment and reload
import os
os.environ["DEFAULT_MODEL"] = "gpt-3.5-turbo"
settings = reload_settings()
print(f"New model: {settings.default_model}")
```

## Common Tasks

### Task 1: Fetch arXiv Papers

```python
from src.tools.arxiv import fetch_papers, search_arxiv

# Fetch by category
papers = fetch_papers(category="cs.AI", max_results=20)

# Search by keywords
papers = search_arxiv(query="large language models", max_results=10)

# Print results
for paper in papers:
    print(f"{paper.title}")
    print(f"  Authors: {', '.join(paper.authors[:3])}")
    print(f"  URL: {paper.pdf_url}")
```

### Task 2: Generate Custom Webpage

```python
from src.tools.templates import TemplateRenderer
from pathlib import Path

renderer = TemplateRenderer()

# Prepare data
papers_data = [
    {
        'title': 'Paper Title',
        'authors': ['Author 1', 'Author 2'],
        'abstract': 'Abstract text...',
        'primary_category': 'cs.AI',
        'difficulty': 'intermediate',
        # ... other fields
    }
]

# Render
output_path = renderer.render_arxiv_page(
    papers=papers_data,
    output_dir=Path("./my_output"),
    date="December 2, 2025"
)

print(f"Generated: {output_path}")
```

### Task 3: Execute Python Code

```python
from src.tools.executor import execute_python, validate_python_syntax

# Validate syntax
code = """
def hello(name):
    return f"Hello, {name}!"

print(hello("World"))
"""

validation = validate_python_syntax(code)
if validation['status'] == 'valid':
    # Execute
    result = execute_python(code, timeout=10)
    print(result['stdout'])
else:
    print(f"Syntax error: {validation['errors']}")
```

### Task 4: Memory Management

```python
from src.core.memory import ProjectMemory, Artifact
from pathlib import Path

# Create memory
memory = ProjectMemory(project_name="my_project")

# Add messages
memory.add_message("user", "Create a calculator")
memory.add_message("assistant", "I'll create that for you")

# Add artifact
artifact = Artifact(
    path="calculator.py",
    content="# Calculator code...",
    artifact_type="code"
)
memory.add_artifact(artifact)

# Save
memory.save(Path("./outputs/memory.json"))

# Load
loaded_memory = ProjectMemory.load(Path("./outputs/memory.json"))
print(f"Loaded {len(loaded_memory.artifacts)} artifacts")
```

## Troubleshooting

### Issue: "No API key found"

**Solution**: Ensure `.env` file exists and contains valid API key:
```bash
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

### Issue: "Module not found"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "Permission denied" on file operations

**Solution**: Check file permissions and ensure output directories are writable:
```bash
chmod -R u+w outputs/
```

### Issue: "Rate limit exceeded"

**Solution**: Adjust rate limiting in `.env`:
```bash
MAX_REQUESTS_PER_MINUTE=20
```

### Issue: arXiv API timeout

**Solution**: Reduce number of papers fetched:
```bash
ARXIV_MAX_RESULTS=20
```

## Next Steps

1. **Read the Architecture docs**: Understand system design (`docs/architecture.md`)
2. **Explore API Reference**: Detailed API documentation (`docs/api.md`)
3. **Run tests**: `pytest tests/` (when implemented)
4. **Customize agents**: Create your own agent subclasses
5. **Build templates**: Design custom templates for your use case

## Getting Help

- Check documentation in `docs/`
- Review example scripts in `examples/`
- Examine source code (well-documented)
- Open issues on GitHub (if applicable)

## Tips for Success

1. **Start small**: Test with simple tasks before complex projects
2. **Monitor usage**: Check token usage via `llm_client.get_usage_report()`
3. **Use appropriate models**: GPT-4 for planning, GPT-3.5 for simple tasks
4. **Enable logging**: Set `LOG_LEVEL=DEBUG` for detailed output
5. **Validate outputs**: Always review generated code before execution
6. **Save memory**: Use `memory.save()` for long-running projects

Happy coding!
