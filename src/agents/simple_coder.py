"""Simple Coder Agent for interactive code generation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from ..core.api_pool import ParallelLLMManager
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class SimpleCoderAgent:
    """Agent that generates actual code files from plans."""

    def __init__(self, api_manager: ParallelLLMManager):
        self.api_manager = api_manager
        self.settings = get_settings()

    async def implement(
        self,
        objective: str,
        plan: Dict[str, Any],
        workspace: Path
    ) -> Dict[str, Any]:
        """Generate code files based on plan.

        Args:
            objective: User's original request
            plan: Plan from SimplePlannerAgent
            workspace: Directory to write files

        Returns:
            Dictionary with generated files and metadata
        """
        logger.info("Starting code implementation phase")

        # Prepare workspace
        workspace.mkdir(parents=True, exist_ok=True)

        # Generate files based on plan's architecture
        architecture = plan.get("architecture", {})
        generated_files = []

        for file_path, file_description in architecture.items():
            logger.info(f"Generating {file_path}")

            # Generate file content
            file_content = await self._generate_file_content(
                objective=objective,
                plan=plan,
                file_path=file_path,
                file_description=file_description
            )

            # Write file to disk
            full_path = workspace / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            full_path.write_text(file_content, encoding="utf-8")
            generated_files.append({
                "path": str(file_path),
                "full_path": str(full_path),
                "description": file_description,
                "size": len(file_content)
            })

            logger.info(f"✓ Generated {file_path} ({len(file_content)} chars)")

        return {
            "success": True,
            "files": generated_files,
            "workspace": str(workspace),
            "total_files": len(generated_files)
        }

    async def _generate_file_content(
        self,
        objective: str,
        plan: Dict[str, Any],
        file_path: str,
        file_description: str
    ) -> str:
        """Generate content for a single file.

        Args:
            objective: User's original request
            plan: Complete plan from planner
            file_path: Path of file to generate
            file_description: Description of what this file should do

        Returns:
            Generated file content as string
        """
        # Determine file type
        file_ext = Path(file_path).suffix.lower()

        # Build system prompt based on file type and name
        file_name = Path(file_path).name.lower()

        if file_ext == ".html":
            system_prompt = self._get_html_system_prompt()
        elif file_ext == ".css":
            system_prompt = self._get_css_system_prompt()
        elif file_ext == ".js":
            # 区分前端 JS 和后端 Node.js
            if "server" in file_name or "app" in file_name or "api" in file_name:
                system_prompt = self._get_nodejs_backend_prompt()
            else:
                system_prompt = self._get_js_system_prompt()
        elif file_ext == ".py":
            # 区分后端 Python 和脚本
            if "server" in file_name or "app" in file_name or "api" in file_name:
                system_prompt = self._get_python_backend_prompt()
            else:
                system_prompt = self._get_python_system_prompt()
        elif file_ext == ".json" and file_name == "package.json":
            system_prompt = self._get_package_json_prompt()
        elif file_ext == ".txt" and "requirements" in file_name:
            system_prompt = self._get_requirements_txt_prompt()
        elif file_ext == ".sh":
            system_prompt = self._get_shell_script_prompt()
        else:
            system_prompt = "You are an expert programmer. Generate high-quality, production-ready code."

        # Build user prompt
        user_prompt = f"""请生成文件: {file_path}

任务描述: {objective}

文件说明: {file_description}

整体架构:
{json.dumps(plan.get('architecture', {}), ensure_ascii=False, indent=2)}

技术要求:
{json.dumps(plan.get('technologies', {}), ensure_ascii=False, indent=2)}

要求:
1. 生成完整的、可直接运行的代码
2. 代码质量高，有适当的注释
3. 遵循最佳实践和设计模式
4. 确保代码健壮性和错误处理
5. 只输出代码内容，不要有额外的解释

直接输出文件的完整内容:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Generate code using parallel API calls for robustness
        logger.info(f"Calling API with model: {self.settings.coder_model}")

        # Keep generations responsive: large token budgets + multiple parallel candidates easily hit timeouts,
        # especially on third-party OpenAI-compatible providers.
        model_lower = (self.settings.coder_model or "").lower()
        is_gpt5 = "gpt-5" in model_lower
        configured_max_tokens = int(getattr(self.settings, "max_tokens_per_request", 4000) or 4000)
        if is_gpt5:
            # gpt-5 系列需要更多 tokens（内部推理会消耗大量 tokens）
            max_tokens = max(8000, configured_max_tokens)
            reasoning_effort = "medium"  # 降低推理强度以留出输出空间
        else:
            # OpenRouter 等代理在大 token 输出时响应很慢，限制上限以减少超时
            max_tokens = min(configured_max_tokens, 3000)
            reasoning_effort = "high"

        results = await self.api_manager.call_parallel(
            messages=messages,
            model=self.settings.coder_model,
            n_parallel=1,  # Reduce latency and avoid waiting on multiple slow candidates
            provider="openai",
            reasoning_effort=reasoning_effort,
            max_tokens=max_tokens
        )

        if not results:
            raise RuntimeError(f"Failed to generate content for {file_path}")

        # Use the first successful result
        content = results[0]["content"].strip()
        logger.info(f"Received content length: {len(content)} chars")

        # 如果内容为空，记录详细信息
        if not content:
            logger.error(f"Empty content received for {file_path}")
            logger.error(f"Full result: {results[0]}")
            logger.error(f"Model: {self.settings.coder_model}")
            logger.error(f"Messages length: {len(messages)}")
            raise RuntimeError(f"API returned empty content for {file_path}")

        # Clean up markdown code blocks if present
        content = self._clean_code_content(content)

        return content

    def _get_html_system_prompt(self) -> str:
        """System prompt for HTML generation."""
        return """你是顶级的前端工程师，擅长实现“严格按需求”的静态网站。

    最重要规则（高优先级）：
    1. 用户在任务描述里给出的结构/文件名/设计 token/交互规则必须严格遵守。
    2. 不要擅自引入未要求的设计语言（例如玻璃态/3D 背景/主题切换），除非用户明确要求。
    3. 只输出该文件的完整代码内容，不要输出解释或 Markdown 围栏。

    默认原则（仅在用户未指定时才使用）：
    - 语义化结构、可访问性（aria）、响应式 meta

必须包含的HTML元素：
1. 完整的HTML5文档结构（<!DOCTYPE html>, <html lang="zh-CN">, <head>, <body>）
    2. **响应式viewport** - <meta name="viewport" content="width=device-width, initial-scale=1.0">
    3. 语义化标签（<header>, <main>, <section>, <footer>）
    4. 适当的 aria 标签提升可访问性

HTML结构模板：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[项目标题]</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>[项目标题]</h1>
    </header>
    <main>
        <!-- 项目具体内容 -->
    </main>
    <footer>
        <p>数据来源：arXiv</p>
    </footer>
    <script src="main.js"></script>
</body>
</html>
```

特殊项目要求：
- arXiv 论文展示：添加 Three.js CDN + Canvas 用于3D粒子背景
- 数据可视化：预留 canvas 或 svg 容器
- 待办事项/表单：使用卡片式布局，每个项目独立玻璃卡片

风格要求：
- 类名使用 BEM 命名规范或语义化命名
- 布局使用 flexbox 或 grid
- 所有交互元素添加 hover 和 focus 样式
- 颜色方案：深色主题为主，浅色主题为辅"""

    def _get_css_system_prompt(self) -> str:
        """System prompt for CSS generation."""
        return """你是顶级的CSS设计大师，专注于创造令人惊叹的视觉体验。你的作品必须媲美顶级设计网站。

核心要求 - 必须全部实现：

1. **CSS变量系统**（必须）
```css
:root {
    /* 深色主题（默认） */
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --accent-1: #6366f1;
    --accent-2: #8b5cf6;
    --accent-3: #ec4899;
    --glass-bg: rgba(255, 255, 255, 0.05);
    --glass-border: rgba(255, 255, 255, 0.1);
}

[data-theme="light"] {
    /* 浅色主题 */
    --bg-primary: #f8fafc;
    --bg-secondary: #f1f5f9;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --glass-bg: rgba(255, 255, 255, 0.7);
    --glass-border: rgba(148, 163, 184, 0.3);
}
```

2. **渐变背景动画**（必须）
```css
.background-gradient {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    background: linear-gradient(135deg,
        var(--bg-primary) 0%,
        var(--bg-secondary) 50%,
        var(--accent-1) 100%);
    animation: gradient-shift 15s ease infinite;
}

@keyframes gradient-shift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
```

3. **玻璃态卡片**（必须）
```css
.glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    transition: all 0.3s ease;
}

.glass-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}
```

4. **渐变文字**（必须）
```css
.gradient-text {
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2), var(--accent-3));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradient-shift 5s ease infinite;
}
```

5. **主题切换按钮**（必须）
```css
.theme-toggle {
    position: fixed;
    top: 2rem;
    right: 2rem;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: var(--glass-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--glass-border);
    cursor: pointer;
    transition: all 0.3s ease;
    z-index: 1000;
}

.theme-toggle:hover {
    transform: scale(1.1) rotate(15deg);
}
```

6. **流畅动画**（必须包含至少3种）
```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
```

7. **响应式设计**（必须）
```css
/* 移动端 */
@media (max-width: 768px) {
    .container { padding: 1rem; }
    .glass-card { padding: 1.5rem; }
    h1 { font-size: 2rem; }
}

/* 平板 */
@media (min-width: 769px) and (max-width: 1024px) {
    .container { padding: 2rem; }
}
```

8. **输入框/按钮样式**（必须）
```css
input, button {
    background: var(--glass-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 0.75rem 1.5rem;
    color: var(--text-primary);
    transition: all 0.3s ease;
}

input:focus, button:hover {
    border-color: var(--accent-1);
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
    outline: none;
}

button {
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    cursor: pointer;
    font-weight: 600;
}
```

性能优化（必须）：
- 使用 transform 和 opacity 做动画（GPU加速）
- 添加 will-change 属性给动画元素
- 避免频繁的 reflow 和 repaint

布局要求：
- 使用 flexbox 或 grid 实现响应式布局
- 所有间距使用 rem 单位
- 最大宽度限制（max-width: 1200px）+ 居中对齐

颜色方案（严格遵守）：
- 主色：深蓝紫渐变 (#6366f1 → #8b5cf6 → #ec4899)
- 背景：深色 #0f172a / 浅色 #f8fafc
- 玻璃效果：rgba(255, 255, 255, 0.05) + blur(20px)"""

    def _get_js_system_prompt(self) -> str:
        """System prompt for JavaScript generation."""
        return """你是顶级的JavaScript全栈工程师，编写优雅、高性能、现代化的JavaScript代码。

必须实现的核心功能（所有项目）：

1. **主题切换系统**（必须）
```javascript
// 初始化主题
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

// 切换主题
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

// 更新图标
function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-icon');
    icon.textContent = theme === 'dark' ? '🌙' : '☀️';
}

// 绑定事件
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
});
```

2. **流畅动画效果**（必须）
- 所有元素淡入效果（fadeIn）
- 交互反馈动画（点击、hover）
- 平滑滚动
- 加载状态动画

3. **localStorage持久化**（必须）
- 主题偏好保存
- 用户数据保存（待办事项、表单数据等）
- 错误处理（容量满、权限等）

4. **现代ES6+语法**（必须）
- const/let 而非 var
- 箭头函数
- 模板字符串
- 解构赋值
- async/await
- 可选链 ?.

5. **性能优化**（必须）
```javascript
// 防抖函数
function debounce(func, delay = 300) {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
}

// 使用示例
const searchInput = document.getElementById('search');
searchInput.addEventListener('input', debounce((e) => {
    performSearch(e.target.value);
}, 300));
```

6. **待办事项应用特定功能**（根据需求）
```javascript
// 待办事项管理
class TodoApp {
    constructor() {
        this.todos = this.loadTodos();
        this.init();
    }

    // 加载数据
    loadTodos() {
        const saved = localStorage.getItem('todos');
        return saved ? JSON.parse(saved) : [];
    }

    // 保存数据
    saveTodos() {
        localStorage.setItem('todos', JSON.stringify(this.todos));
    }

    // 添加待办
    addTodo(text) {
        const todo = {
            id: Date.now(),
            text,
            completed: false,
            createdAt: new Date().toISOString()
        };
        this.todos.push(todo);
        this.saveTodos();
        this.render();
    }

    // 切换完成状态
    toggleTodo(id) {
        const todo = this.todos.find(t => t.id === id);
        if (todo) {
            todo.completed = !todo.completed;
            this.saveTodos();
            this.render();
        }
    }

    // 删除待办
    deleteTodo(id) {
        this.todos = this.todos.filter(t => t.id !== id);
        this.saveTodos();
        this.render();
    }

    // 渲染界面
    render() {
        const container = document.getElementById('todoList');
        container.innerHTML = this.todos.map(todo => `
            <div class="todo-item glass-card ${todo.completed ? 'completed' : ''}" data-id="${todo.id}">
                <input type="checkbox" ${todo.completed ? 'checked' : ''}
                       onchange="app.toggleTodo(${todo.id})">
                <span class="todo-text">${todo.text}</span>
                <button onclick="app.deleteTodo(${todo.id})" class="delete-btn">🗑️</button>
            </div>
        `).join('');
    }

    init() {
        this.render();
        // 绑定添加按钮
        document.getElementById('addBtn').addEventListener('click', () => {
            const input = document.getElementById('todoInput');
            if (input.value.trim()) {
                this.addTodo(input.value.trim());
                input.value = '';
            }
        });
    }
}

// 初始化应用
const app = new TodoApp();
```

7. **错误处理和用户反馈**（必须）
```javascript
// 显示提示消息
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }, 10);
}

// 错误处理示例
try {
    localStorage.setItem('test', 'test');
} catch (e) {
    showToast('存储空间已满，请清理数据', 'error');
}
```

代码质量要求：
- 所有函数添加简洁注释
- 使用有意义的变量名
- 避免全局变量污染（使用 IIFE 或模块）
- 适当的空行和格式化
- 处理边界情况（空值、null、undefined）

性能优化：
- 使用事件委托减少事件监听器
- 使用 DocumentFragment 批量DOM操作
- 图片懒加载
- 防抖/节流处理高频事件"""

    def _get_python_system_prompt(self) -> str:
        """System prompt for Python generation."""
        return """你是专业的Python工程师，擅长编写高质量、功能完整的Python代码。

基本要求:
1. 遵循PEP 8代码规范
2. 使用类型注解（Type Hints）
3. 完善的错误处理和异常处理
4. 清晰的文档字符串
5. 模块化设计
6. 使用现代Python特性（Python 3.9+）
7. 性能优化和资源管理

对于arXiv论文获取脚本（fetch_arxiv.py），必须实现:

**核心功能:**
1. **arXiv API调用**:
   - 使用 requests 库调用 arXiv API
   - 构造正确的查询URL（http://export.arxiv.org/api/query）
   - 支持多个类别查询（cs.AI, cs.CL, cs.LG, cs.CV）
   - 支持日期范围过滤（获取最近1天的论文）

2. **XML解析**:
   - 使用 xml.etree.ElementTree 解析arXiv返回的XML
   - 提取论文信息：id, title, authors, summary, published, categories, pdf_url

3. **数据处理**:
   - 按日期过滤论文（只保留最近发布的）
   - 按类别分组
   - 去重（基于论文ID）
   - 排序（按发布时间降序）

4. **JSON输出**:
   - 将论文数据保存为 papers.json
   - 使用 indent=2 格式化输出
   - 包含完整的论文元数据

**代码结构建议:**
```python
import requests
import json
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from typing import List, Dict, Any

def fetch_arxiv_papers(
    categories: List[str] = ['cs.AI', 'cs.CL', 'cs.LG', 'cs.CV'],
    max_results: int = 50,
    days_back: int = 1
) -> List[Dict[str, Any]]:
    \"\"\"从arXiv获取论文\"\"\"
    # 构造查询
    # 调用API
    # 解析XML
    # 返回论文列表

def parse_arxiv_entry(entry: ET.Element) -> Dict[str, Any]:
    \"\"\"解析单个论文条目\"\"\"
    # 提取id, title, authors, summary等
    # 返回字典

def filter_by_date(papers: List[Dict], days: int) -> List[Dict]:
    \"\"\"按日期过滤论文\"\"\"
    # 计算截止日期
    # 过滤论文

def save_to_json(papers: List[Dict], filepath: str = 'papers.json'):
    \"\"\"保存到JSON文件\"\"\"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    papers = fetch_arxiv_papers()
    save_to_json(papers)
    print(f'Fetched {len(papers)} papers')
```

**重要细节:**
- arXiv API URL: `http://export.arxiv.org/api/query`
- 查询参数: `search_query=cat:cs.AI+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=50`
- XML命名空间: `{http://www.w3.org/2005/Atom}`
- 日期格式: ISO 8601 (2024-12-01T00:00:00Z)
- 错误处理: 网络错误、XML解析错误、文件写入错误

性能优化:
- 使用会话对象（requests.Session）
- 适当的超时设置
- 缓存机制（可选）"""

    def _clean_code_content(self, content: str) -> str:
        """Clean up code content by removing markdown code blocks.

        Args:
            content: Raw content from LLM

        Returns:
            Cleaned content
        """
        # Remove markdown code blocks if present
        lines = content.split("\n")

        # Check if first line is a code block marker
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        # Check if last line is a code block marker
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines)

    def _get_nodejs_backend_prompt(self) -> str:
        """System prompt for Node.js backend generation."""
        return """你是专业的 Node.js 后端工程师，擅长使用 Express 构建 RESTful API。

必须实现的功能（完整后端服务器）：

1. **Express 服务器设置**（必须）
```javascript
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static('public')); // 提供静态文件

// 路由
// ... API endpoints

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
```

2. **RESTful API 端点**（根据需求）
- GET /api/data - 获取数据列表
- POST /api/data - 创建新数据
- PUT /api/data/:id - 更新数据
- DELETE /api/data/:id - 删除数据

3. **数据存储**
- 使用文件系统（JSON文件）或内存数据库
- 简单项目使用 fs 模块读写 JSON
- 复杂项目使用 SQLite 或 MongoDB

4. **错误处理**（必须）
```javascript
// 全局错误处理
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// 404 处理
app.use((req, res) => {
    res.status(404).json({ error: 'Not found' });
});
```

5. **CORS 配置**（必须）
允许前端跨域访问

代码质量要求：
- 使用 async/await 处理异步操作
- 适当的错误处理和状态码
- 清晰的路由组织
- 输入验证
- 日志记录"""

    def _get_python_backend_prompt(self) -> str:
        """System prompt for Python backend generation."""
        return """你是专业的 Python 后端工程师，擅长使用 Flask/FastAPI 构建 API。

必须实现的功能（完整后端服务）：

1. **Flask 应用设置**（必须）
```python
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)  # 允许跨域

# 数据存储路径
DATA_FILE = Path('data.json')

@app.route('/')
def index():
    return 'API Server Running'

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

2. **RESTful API 端点**（根据需求）
```python
@app.route('/api/data', methods=['GET'])
def get_data():
    data = load_data()
    return jsonify(data)

@app.route('/api/data', methods=['POST'])
def create_data():
    new_item = request.json
    data = load_data()
    data.append(new_item)
    save_data(data)
    return jsonify(new_item), 201

@app.route('/api/data/<int:id>', methods=['DELETE'])
def delete_data(id):
    data = load_data()
    data = [item for item in data if item['id'] != id]
    save_data(data)
    return '', 204
```

3. **数据持久化**（必须）
```python
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
```

4. **错误处理**（必须）
```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
```

代码质量要求：
- 类型注解
- 错误处理
- 输入验证
- 适当的 HTTP 状态码
- JSON 响应格式"""

    def _get_package_json_prompt(self) -> str:
        """System prompt for package.json generation."""
        return """生成完整的 Node.js package.json 配置文件。

必须包含的内容：
1. 项目基本信息（name, version, description）
2. 启动脚本（scripts）
3. 所有必需的依赖（dependencies）
4. 开发依赖（devDependencies，可选）

常用依赖：
- express: Web 框架
- cors: 跨域支持
- body-parser: 请求体解析（Express 4.16+ 内置）
- dotenv: 环境变量
- nodemon: 开发时自动重启（devDependencies）

示例：
```json
{
  "name": "project-name",
  "version": "1.0.0",
  "description": "Project description",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
```"""

    def _get_requirements_txt_prompt(self) -> str:
        """System prompt for requirements.txt generation."""
        return """生成 Python requirements.txt 依赖文件。

常用依赖：
- Flask==2.3.0 - Web 框架
- Flask-CORS==4.0.0 - 跨域支持
- requests==2.31.0 - HTTP 客户端
- python-dotenv==1.0.0 - 环境变量

示例：
```
Flask==2.3.0
Flask-CORS==4.0.0
requests==2.31.0
```

只列出必需的依赖，使用固定版本号。"""

    def _get_shell_script_prompt(self) -> str:
        """System prompt for shell script generation."""
        return """生成启动脚本（start.sh），用于一键启动项目。

必须包含：
1. Shebang (#!/bin/bash)
2. 检查依赖是否安装
3. 安装依赖（如果需要）
4. 启动后端服务器
5. 打开浏览器（可选）
6. 清晰的输出信息

Node.js 项目示例：
```bash
#!/bin/bash

echo "🚀 启动项目..."

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 请先安装 Node.js"
    exit 1
fi

# 安装依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

# 启动服务器
echo "✅ 启动服务器..."
npm start
```

Python 项目示例：
```bash
#!/bin/bash

echo "🚀 启动项目..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装 Python 3"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务器
echo "✅ 启动服务器..."
python app.py
```"""
