# API Reference

## Core Modules

### src.core.config

**Settings Class**

```python
from src.core.config import get_settings, Settings

# Get global settings instance
settings = get_settings()

# Access configuration
settings.default_model          # str: Default LLM model
settings.max_retries            # int: Max API retry attempts
settings.timeout_seconds        # int: Request timeout
settings.arxiv_max_results      # int: Max arXiv papers to fetch
settings.output_dir             # Path: Output directory

# Get provider-specific settings
api_key = settings.get_api_key("openai")
base_url = settings.get_base_url("openai")
```

### src.core.llm_client

**LLMClient Class**

```python
from src.core.llm_client import LLMClient, Message

# Initialize client
client = LLMClient(
    provider="openai",
    model="gpt-4-turbo-preview",
    temperature=0.7,
    max_tokens=4000
)

# Sync chat
messages = [
    Message(role="system", content="You are a helpful assistant"),
    Message(role="user", content="Hello!")
]
response = client.chat(messages)

# Async chat
response = await client.achat(messages)

# Parallel chat (ensemble voting)
best_response, all_responses = client.ensemble_vote(messages, n=3)

# Usage statistics
print(client.get_usage_report())
```

### src.core.memory

**ProjectMemory Class**

```python
from src.core.memory import ProjectMemory, Artifact, TaskExecution
from pathlib import Path

# Create memory
memory = ProjectMemory(project_name="demo", max_context_messages=100)

# Add conversation messages
memory.add_message("user", "Create a calculator")
memory.add_message("assistant", "I'll create that")

# Add artifacts
artifact = Artifact(
    path="calculator.py",
    content="# code here",
    artifact_type="code",
    metadata={"language": "python"}
)
memory.add_artifact(artifact)

# Track task execution
execution = TaskExecution(
    task_id="task_1",
    agent_type="CoderAgent",
    status="completed",
    input_data={"description": "Create calculator"},
    output_data={"files": ["calculator.py"]}
)
memory.add_task_execution(execution)

# Save/load
memory.save(Path("memory.json"))
loaded = ProjectMemory.load(Path("memory.json"))
```

### src.core.orchestrator

**Orchestrator Class**

```python
from src.core.orchestrator import Orchestrator

# Initialize
orchestrator = Orchestrator(
    project_name="my_project",
    enable_parallel=True
)

# Execute project
results = orchestrator.execute_project(
    objective="Create a web scraper",
    context="Focus on maintainability",
    max_iterations=10
)

# Check results
if results['success']:
    print(f"Tasks completed: {results['tasks_completed']}")
    print(f"Artifacts: {results['artifacts']}")

# Generate report
report = orchestrator.generate_report(results)
print(report)

# Save results
orchestrator.save_results(results, Path("results.json"))
```

## Agents

### src.agents.base_agent

**BaseAgent Class**

```python
from src.agents.base_agent import BaseAgent, Task, AgentResponse

# Create custom agent
class MyAgent(BaseAgent):
    def think(self, task, context=None):
        # Implement reasoning
        return "My thought process"

    def act(self, task, thought):
        # Implement action
        return AgentResponse(
            success=True,
            data={"result": "done"},
            message="Completed successfully"
        )

# Use agent
agent = MyAgent(name="MyAgent")
task = Task(
    task_id="task_1",
    description="Do something",
    dependencies=[],
    priority=1
)

# Execute full cycle (think-act-reflect)
result = agent.execute(task)

# Register tools
agent.register_tool("my_tool", my_function)
output = agent.use_tool("my_tool", arg1="value")
```

### src.agents.planner

**PlannerAgent Class**

```python
from src.agents.planner import PlannerAgent

planner = PlannerAgent()

task = Task(
    task_id="plan_project",
    description="Plan a web application",
    dependencies=[]
)

# Execute planning
result = planner.execute(task, context="Use modern stack")

# Access plan
plan_data = result.data['plan']
subtasks = plan_data['subtasks']
execution_order = planner.get_execution_order()
```

### src.agents.coder

**CoderAgent Class**

```python
from src.agents.coder import CoderAgent

coder = CoderAgent()

task = Task(
    task_id="implement_feature",
    description="Create a REST API endpoint",
    dependencies=[]
)

# Execute implementation
result = coder.execute(task)

# Check generated files
generated_files = result.artifacts
```

### src.agents.reviewer

**ReviewerAgent Class**

```python
from src.agents.reviewer import ReviewerAgent

reviewer = ReviewerAgent()

task = Task(
    task_id="review_code",
    description="Review generated code",
    dependencies=[],
    metadata={"artifacts": ["api.py", "tests.py"]}
)

# Execute review
result = reviewer.execute(task)

# Check quality
quality_score = result.data['quality_score']
issues = result.data['issues']
suggestions = result.data['suggestions']
```

## Tools

### src.tools.fileio

**File Operations**

```python
from src.tools.fileio import (
    create_file, read_file, write_file, delete_file,
    list_directory, create_directory
)

# Create file
result = create_file("output.txt", "Hello", overwrite=True)

# Read file
content = read_file("output.txt")

# Write/append
write_file("output.txt", "World", append=True)

# List directory
files = list_directory("./src", pattern="*.py", recursive=True)

# Create directory
create_directory("./outputs/data", parents=True)

# Delete
delete_file("output.txt")
```

### src.tools.executor

**Code Execution**

```python
from src.tools.executor import (
    execute_python, execute_shell, validate_python_syntax
)

# Validate syntax
code = "def hello(): print('hi')"
validation = validate_python_syntax(code)

if validation['status'] == 'valid':
    # Execute Python
    result = execute_python(code, timeout=30)
    print(result['stdout'])

# Execute shell
result = execute_shell("ls -la", timeout=10, safe_mode=True)
```

### src.tools.arxiv

**arXiv Integration**

```python
from src.tools.arxiv import (
    fetch_papers, search_arxiv, get_daily_papers,
    categorize_papers, estimate_difficulty
)

# Fetch by category
papers = fetch_papers(
    category="cs.AI",
    max_results=20,
    days_back=1  # Last 24 hours
)

# Search by keywords
papers = search_arxiv("large language models", max_results=10)

# Get daily papers from multiple categories
daily = get_daily_papers(
    categories=["cs.AI", "cs.CL", "cs.LG"],
    max_per_category=20
)

# Categorize
categorized = categorize_papers(papers)

# Estimate difficulty
for paper in papers:
    difficulty = estimate_difficulty(paper)
    print(f"{paper.title}: {difficulty}")
```

### src.tools.web

**Web Operations**

```python
from src.tools.web import web_search, fetch_url, extract_links

# Search (simulated)
results = web_search("Python tutorial", num_results=10)

# Fetch URL
result = fetch_url("https://example.com", extract_text=True)
html = result['raw_content']
text = result['text']

# Extract links
links = extract_links(html, base_url="https://example.com")
```

### src.tools.templates

**Template Rendering**

```python
from src.tools.templates import TemplateRenderer
from pathlib import Path

renderer = TemplateRenderer()

# Render arXiv page
papers_data = [...]  # List of paper dicts
index_path = renderer.render_arxiv_page(
    papers=papers_data,
    output_dir=Path("./output"),
    date="December 2, 2025"
)

# Render custom template
context = {"title": "My Page", "items": [1, 2, 3]}
html = renderer.render("my_template.html", context)
```

## Data Structures

### Task

```python
from src.agents.base_agent import Task

task = Task(
    task_id="unique_id",           # str
    description="Task description", # str
    dependencies=["task_1"],        # List[str]
    priority=5,                     # int
    metadata={"key": "value"}       # Dict[str, Any]
)
```

### AgentResponse

```python
from src.agents.base_agent import AgentResponse

response = AgentResponse(
    success=True,                     # bool
    data={"result": "value"},         # Dict[str, Any]
    message="Success message",        # str
    artifacts=["file1.py"]            # List[str]
)
```

### Artifact

```python
from src.core.memory import Artifact

artifact = Artifact(
    path="output.py",                 # str
    content="# code",                 # str
    artifact_type="code",             # str
    metadata={"lang": "python"}       # Dict[str, Any]
)
```

### PaperMetadata

```python
from src.tools.arxiv import PaperMetadata

paper = PaperMetadata(
    id="2401.12345v1",
    title="Paper Title",
    authors=["Author 1", "Author 2"],
    abstract="Abstract text...",
    categories=["cs.AI", "cs.LG"],
    primary_category="cs.AI",
    published="2024-01-15T10:00:00Z",
    updated="2024-01-16T10:00:00Z",
    pdf_url="https://arxiv.org/pdf/2401.12345",
    arxiv_url="https://arxiv.org/abs/2401.12345"
)
```

## Error Handling

All tools and agents use custom exceptions:

```python
from src.tools.fileio import FileOperationError
from src.tools.executor import ExecutionError

try:
    content = read_file("nonexistent.txt")
except FileOperationError as e:
    print(f"File error: {e}")

try:
    result = execute_python(bad_code)
except ExecutionError as e:
    print(f"Execution error: {e}")
```

## Type Hints

The codebase uses comprehensive type hints:

```python
from typing import Dict, List, Optional, Any
from pathlib import Path

def my_function(
    filepath: str,
    options: Optional[Dict[str, Any]] = None
) -> List[str]:
    ...
```

## Best Practices

1. **Always check return values**:
   ```python
   if result['success']:
       # Process data
   else:
       # Handle error
   ```

2. **Use context managers for resources**:
   ```python
   memory = ProjectMemory("project")
   try:
       # Work with memory
   finally:
       memory.save(Path("memory.json"))
   ```

3. **Handle exceptions appropriately**:
   ```python
   try:
       result = agent.execute(task)
   except Exception as e:
       console.print(f"[red]Error: {e}[/red]")
   ```

4. **Clean up resources**:
   ```python
   client.reset_usage_stats()
   memory.clear()
   ```
