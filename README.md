# 🚀 Advanced Multi-Agent Code Generation System

<div align="center">

**A Production-Ready Multi-Agent Framework for Autonomous Code Generation and Research Automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Developed by Yufeng HE and collaborators for advanced AI agent research*

</div>

---

## 🌟 Overview

The **Advanced Agent System** is a state-of-the-art multi-agent framework that implements cutting-edge AI agent patterns including **ReACT** (Reasoning + Acting), **Chain-of-Thought**, and **Self-Reflection**. It autonomously generates complete, production-ready software projects from natural language descriptions.

### 🎯 Key Highlights

- **🧠 Intelligent Multi-Agent Architecture**: Specialized agents (Planner, Coder, Reviewer) collaborating seamlessly
- **🔄 ReACT Pattern**: Think-Act-Reflect cycle for robust decision-making
- **🛠️ Rich Tool Ecosystem**: 20+ tools including file ops, web search, code execution, arXiv integration
- **💎 Stunning Frontend**: 3D particle effects (Three.js), glassmorphism design, dark/light themes
- **🔐 Production-Ready**: Exponential backoff, retry logic, comprehensive error handling
- **⚡ High Performance**: Parallel execution, async API calls, intelligent caching
- **📊 Memory System**: Context management, artifact tracking, conversation history
- **🎓 arXiv Specialization**: Academic paper aggregation with beautiful visualization

### 🏆 Academic Foundation

This system incorporates research from:
- **ReACT**: Reasoning and Acting in Language Models (Yao et al., 2022)
- **Chain-of-Thought**: Prompting for Complex Reasoning (Wei et al., 2022)
- **Self-Reflection**: Teaching Language Models to Self-Improve (Huang et al., 2022)

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Orchestrator (Core Engine)                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Task Scheduler │ Memory Manager │ Dependency Resolver     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐     ┌───────▼────────┐     ┌───────▼────────┐
│ Planning Agent │     │  Coding Agent  │     │  Review Agent  │
│                │     │                │     │                │
│ • Task Decomp  │     │ • Code Gen     │     │ • Quality QA   │
│ • Chain-of-    │     │ • Multi-Lang   │     │ • Security     │
│   Thought      │────▶│ • Tool Calling │────▶│ • Testing      │
│ • Dependency   │     │ • Artifact Mgmt│     │ • Feedback     │
│   Graph (DAG)  │     │                │     │                │
└────────────────┘     └────────────────┘     └────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────▼────────────────────────┐
        │            Tool System (20+ Tools)             │
        │  • File I/O        • Code Execution            │
        │  • Web Search      • arXiv API                 │
        │  • Templates       • Git Operations            │
        └────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 📦 Installation

```bash
# Navigate to project directory
cd advanced_agent_system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your OpenAI API key
```

### ⚡ Quick Demo

```bash
# Generate stunning arXiv daily webpage
python examples/arxiv_daily.py

# Output: ./outputs/arxiv_daily_YYYYMMDD/index.html
# Open in browser to see 3D effects and modern UI!
```

### 🧭 Usage Guide (CLI)

- Interactive mode (default model = deepseek):
    - `python run_agent.py`
- Direct mode with prompt:
    - `python run_agent.py --prompt "生成 arXiv 论文展示网页"`
- Switch global model (deepseek/openai/qwen by name):
    - `python run_agent.py --prompt "构建待办应用" --model gpt-4o`
    - `python run_agent.py --prompt "构建待办应用" --model qwen-plus`
- Choose reviewer implementation:
    - Default (同学版): `--reviewer simple`
    - Legacy tool-style reviewer: `--reviewer legacy`

环境变量可在 `.env` / `env.example` 配置（MODEL、各 provider API_KEY/Base URL），CLI 参数优先级高于环境变量。

### 💻 Programmatic Usage

```python
from src.core.orchestrator import Orchestrator

# Initialize orchestrator
orchestrator = Orchestrator(project_name="my_project")

# Define objective
objective = """
Create a web application that:
1. Fetches data from an API
2. Processes and analyzes the data
3. Displays results in an interactive dashboard
"""

# Execute project
results = orchestrator.execute_project(objective=objective)

# Check results
if results['success']:
    print(f"✓ Generated {len(results['artifacts'])} files")
    print(f"Quality score: {results['review']['quality_score']:.2f}")
```

## 📚 Documentation

### Core Documentation

- **[Quick Start Guide](docs/quickstart.md)** - Get started in 5 minutes
- **[Architecture Overview](docs/architecture.md)** - Deep dive into system design

### Component Guides

- **Agents**: Planning, Coding, and Review agent specifications
- **Tools**: File I/O, web search, code execution, arXiv integration
- **Templates**: Jinja2 templates for beautiful webpage generation
- **Memory**: Context management and artifact tracking

## 🎨 Features Showcase

### 🌐 arXiv Daily Generator

Generate beautiful, interactive webpages from arXiv papers with:
- 3D particle background (Three.js)
- Glassmorphism design
- Dark/Light theme toggle
- Real-time search and filtering
- Responsive mobile layout
- Keyboard shortcuts

### 🤖 Multi-Agent Collaboration

1. **Planner Agent**: Decomposes tasks using Chain-of-Thought
2. **Coder Agent**: Implements solutions with tool calling
3. **Review Agent**: Quality assurance and testing
4. **Orchestrator**: Coordinates execution

## 🔬 Technical Highlights

### ReACT Pattern

```python
def execute(task):
    thought = think(task)      # Reasoning
    result = act(task, thought)  # Action
    reflection = reflect(result) # Learning
    return result
```

### Tool System (20+ Tools)

- **File Operations**: create_file, read_file, write_file, delete_file
- **Web Operations**: web_search, fetch_url
- **Code Execution**: execute_python, execute_shell, validate_syntax
- **arXiv Integration**: fetch_papers, search_arxiv, categorize_papers
- **Templates**: Jinja2-based HTML generation

## 📧 Contact

**Yufeng HE**
- Research Focus: Trustworthy AI, Multi-Agent Systems

---

<div align="center">

**Built with passion for AI agent research**

</div>
