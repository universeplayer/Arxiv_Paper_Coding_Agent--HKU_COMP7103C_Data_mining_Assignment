# System Architecture

## Overview

The Advanced Agent System is a production-ready multi-agent framework for autonomous code generation and task execution. It implements the ReACT (Reasoning + Acting) pattern with support for Chain-of-Thought reasoning and self-reflection.

## Core Components

### 1. LLM Client (`src/core/llm_client.py`)

**Purpose**: Unified interface for multiple LLM providers with robust error handling.

**Features**:
- Multi-provider support (OpenAI, DeepSeek, Qwen)
- Exponential backoff retry logic using `tenacity`
- Parallel API calls for ensemble voting
- Usage tracking and cost monitoring
- ReACT pattern implementation

**Key Classes**:
- `LLMClient`: Main client class
- `UsageStats`: Token and cost tracking
- `Message`: Chat message structure
- `ReACTStep`: Single reasoning-action step

### 2. Memory System (`src/core/memory.py`)

**Purpose**: Maintain project-wide context, conversation history, and artifacts.

**Features**:
- Conversation history with automatic context windowing
- Task execution tracking
- Artifact management (files, documents, code)
- Context compression for long conversations
- Persistent storage (JSON serialization)

**Key Classes**:
- `ProjectMemory`: Main memory container
- `Artifact`: Represents generated files/code
- `TaskExecution`: Task execution record
- `ConversationMessage`: Single message

### 3. Configuration (`src/core/config.py`)

**Purpose**: Centralized configuration using Pydantic settings.

**Features**:
- Environment variable support via `.env`
- Type validation and coercion
- Directory auto-creation
- Provider-specific settings
- Runtime configuration reloading

**Key Class**:
- `Settings`: Pydantic settings model

### 4. Orchestrator (`src/core/orchestrator.py`)

**Purpose**: Coordinate multiple agents and manage task execution.

**Features**:
- Dependency graph construction using NetworkX
- Topological task sorting
- Parallel execution support
- Error recovery mechanisms
- Progress tracking with Rich

**Key Class**:
- `Orchestrator`: Main orchestration engine

## Agent System

### Base Agent (`src/agents/base_agent.py`)

**Abstract base class** providing common functionality:

**Core Methods**:
- `think(task, context)`: Generate reasoning/plan
- `act(task, thought)`: Execute action based on reasoning
- `reflect(task, result)`: Reflect on results
- `execute(task, context)`: Full think-act-reflect cycle

**Tool System**:
- `register_tool(name, func)`: Register callable tools
- `use_tool(name, **kwargs)`: Execute tools

### Planning Agent (`src/agents/planner.py`)

**Purpose**: Task decomposition and dependency analysis.

**Features**:
- Chain-of-Thought task breakdown
- Dependency graph construction
- Execution schedule generation
- Complexity estimation

**Output**: Structured plan with subtasks, dependencies, and execution order.

### Coding Agent (`src/agents/coder.py`)

**Purpose**: Code implementation and generation.

**Features**:
- Multi-language support (Python, JS, TypeScript, etc.)
- Context-aware code generation
- Production-ready code (no TODOs/placeholders)
- Automatic documentation and error handling
- Code modification capabilities

**Output**: Complete, functional code files.

### Review Agent (`src/agents/reviewer.py`)

**Purpose**: Quality assessment and testing.

**Features**:
- Code quality analysis
- Security vulnerability detection
- Performance review
- Test execution
- Actionable feedback generation

**Output**: Quality scores, issues, and improvement suggestions.

## Tool System

### File Operations (`src/tools/fileio.py`)

Safe file I/O with path validation:
- `create_file()`, `read_file()`, `write_file()`, `delete_file()`
- `list_directory()`, `create_directory()`
- Base directory restriction for security

### Web Operations (`src/tools/web.py`)

Web search and URL fetching:
- `web_search()`: Simulate Brave Search API
- `fetch_url()`: Download and extract content
- `extract_links()`: Parse HTML links

### Code Execution (`src/tools/executor.py`)

Sandboxed code execution:
- `execute_python()`: Run Python code in subprocess
- `execute_shell()`: Execute shell commands (with safety checks)
- `execute_script()`: Run script files
- `validate_python_syntax()`: Syntax checking

### arXiv Integration (`src/tools/arxiv.py`)

Academic paper fetching:
- `fetch_papers()`: Get papers by category
- `search_arxiv()`: Keyword search
- `categorize_papers()`: Group by category
- `estimate_difficulty()`: Heuristic difficulty estimation
- `get_daily_papers()`: Fetch recent papers

### Template System (`src/tools/templates.py`)

Jinja2-based HTML generation:
- `TemplateRenderer`: Main rendering class
- `render_arxiv_page()`: Generate complete arXiv webpage
- `render_paper_detail()`: Individual paper pages

## Frontend Templates

### Modern arXiv Interface

**Files**:
- `modern_arxiv.html`: Main HTML template
- `style.css`: Glassmorphism styling with CSS variables
- `script.js`: Three.js background + interactivity

**Features**:
- 3D particle background (Three.js)
- Dark/Light theme toggle
- Real-time search and filtering
- Responsive design
- Smooth animations
- Keyboard shortcuts

## Data Flow

```
User Request
    ↓
Orchestrator
    ↓
Planning Agent → Task Decomposition → Dependency Graph
    ↓
Coding Agent → Code Generation → Artifacts
    ↓
Review Agent → Quality Check → Feedback
    ↓
Memory System → Persistence
    ↓
Results + Artifacts
```

## Design Patterns

### 1. ReACT (Reasoning + Acting)

Each agent follows:
1. **Reasoning**: Think about the task
2. **Acting**: Execute based on reasoning
3. **Reflection**: Learn from results

### 2. Chain-of-Thought

Complex tasks are broken down step-by-step:
- Understand requirements
- Identify subtasks
- Create execution plan
- Estimate complexity

### 3. Dependency Management

Tasks are organized as DAG (Directed Acyclic Graph):
- NetworkX for graph operations
- Topological sorting for execution order
- Parallel execution of independent tasks

### 4. Tool-Augmented Agents

Agents access external tools:
- File system operations
- Web APIs
- Code execution
- Data processing

## Error Handling

### Retry Logic

- Exponential backoff for API calls
- Maximum retry attempts (configurable)
- Timeout handling

### Validation

- Path safety checks
- Circular dependency detection
- Syntax validation
- Input sanitization

### Recovery

- Graceful degradation
- Error logging
- Task status tracking
- Rollback capabilities

## Performance Optimization

### Parallel Execution

- AsyncIO for concurrent API calls
- Parallel task execution (when dependencies allow)
- Thread pool for blocking operations

### Caching

- Conversation context compression
- Memory windowing (fixed-size deque)
- Lazy loading for large datasets

### Resource Management

- Token usage tracking
- Rate limiting
- Memory cleanup
- File handle management

## Security Considerations

### Code Execution

- Subprocess isolation
- Command sanitization (dangerous patterns blocked)
- Timeout enforcement
- Safe mode by default

### File Operations

- Path traversal prevention
- Base directory restriction
- Existence validation
- Permission checks

### API Security

- API key management via environment variables
- No hardcoded credentials
- HTTPS enforcement
- Request signing (provider-dependent)

## Extensibility

### Adding New Agents

1. Inherit from `BaseAgent`
2. Implement `think()`, `act()`, `reflect()`
3. Register tools as needed
4. Add to orchestrator

### Adding New Tools

1. Create function with clear signature
2. Add error handling
3. Register with agents
4. Document usage

### Adding New Templates

1. Create Jinja2 template
2. Place in `src/templates/`
3. Add rendering logic to `TemplateRenderer`
4. Test with sample data

## Testing Strategy

### Unit Tests

- Individual agent methods
- Tool functions
- Memory operations
- Configuration validation

### Integration Tests

- Multi-agent workflows
- End-to-end task execution
- Template rendering
- API interactions (mocked)

### System Tests

- Complete project execution
- arXiv daily generation
- Performance benchmarks
- Error recovery scenarios
