#!/usr/bin/env python3
"""
交互式多智能体代码生成系统
从自然语言描述到可运行代码的完整流程
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_settings
from src.core.api_pool import ParallelLLMManager
from src.agents.enhanced_planner import EnhancedPlannerAgent
from src.agents.simple_coder import SimpleCoderAgent
from src.agents.simple_reviewer import SimpleReviewerAgent

console = Console()


def print_welcome():
    """显示欢迎信息"""
    welcome_text = """
# 🤖 高级多智能体代码生成系统

这是一个智能代码生成系统，可以根据您的自然语言描述自动生成完整的、可运行的代码。

## 工作流程：

1. **规划智能体** - 理解需求，分解任务
2. **编码智能体** - 编写代码，创建文件
3. **审查智能体** - 检查质量，提出改进

## 示例任务：

- "生成一个解析 arXiv 每日论文并在网页展示摘要的代码"
- "创建一个简单的待办事项管理器网页应用"
- "开发一个数据可视化仪表板"
- "制作一个 Markdown 转 HTML 的转换工具"

输入 'quit' 或 'exit' 退出系统。
"""
    console.print(Panel(Markdown(welcome_text), border_style="cyan", title="欢迎"))


async def execute_task(user_prompt: str, output_dir: Path):
    """执行用户任务"""

    console.print(f"\n[bold green]► 收到任务：[/bold green]{user_prompt}\n")

    # 初始化系统
    settings = get_settings()
    api_manager = ParallelLLMManager(settings)

    # 创建智能体
    planner = EnhancedPlannerAgent(api_manager)
    coder = SimpleCoderAgent(api_manager)
    reviewer = SimpleReviewerAgent(api_manager)
    # 统一走标准 Planner + Coder 流程，不再使用模板捷径

    try:
        # Step 1: 规划阶段
        console.print("[bold cyan]━━━ 步骤 1/3: 规划智能体正在分析任务 ━━━[/bold cyan]\n")

        plan_result = await planner.plan(user_prompt)

        console.print(Panel(
            plan_result.get('plan_summary', '任务已分解'),
            title="📋 任务规划",
            border_style="blue"
        ))

        # 显示任务列表
        tasks = plan_result.get('tasks', [])
        if tasks:
            console.print("\n[bold]子任务列表：[/bold]")
            for i, task in enumerate(tasks, 1):
                task_desc = task.get('description', task) if isinstance(task, dict) else str(task)
                console.print(f"  {i}. {task_desc}")

        # 显示架构
        architecture = plan_result.get('architecture', {})
        if architecture:
            console.print("\n[bold]文件架构：[/bold]")
            for file_path in architecture.keys():
                console.print(f"  📄 {file_path}")

        # Step 2: 编码阶段
        console.print("\n[bold cyan]━━━ 步骤 2/3: 编码智能体正在实现功能 ━━━[/bold cyan]\n")

        # 使用标准 Coder 实现计划
        code_result = await coder.implement(
            objective=user_prompt,
            plan=plan_result,
            workspace=output_dir
        )

        # 显示生成的文件
        generated_files = code_result.get('files', [])
        if generated_files:
            file_list = []
            for f in generated_files:
                if isinstance(f, dict):
                    path = f.get('path', 'unknown')
                    size = f.get('size', 0)
                    file_list.append(f"✓ {path} ({size} chars)")
                else:
                    file_list.append(f"✓ {f}")

            console.print(Panel(
                "\n".join(file_list),
                title=f"📁 生成的文件 (共 {len(generated_files)} 个)",
                border_style="green"
            ))

        # Step 3: 审查阶段
        console.print("\n[bold cyan]━━━ 步骤 3/3: 审查智能体正在检查质量 ━━━[/bold cyan]\n")

        # 所有任务都进行真实审查（包括 arXiv），以便将发现写入 README
        # 添加 output_dir 到 code_result 以便 reviewer 可以更新 README
        code_result_with_dir = code_result.copy()
        code_result_with_dir['output_dir'] = output_dir
        
        review_result = await reviewer.review(
            objective=user_prompt,
            implementation=code_result_with_dir
        )

        quality_score = review_result.get('quality_score', 0.5) * 100  # Convert to 0-100 scale
        assessment = review_result.get('assessment', '')
        issues = review_result.get('issues', [])

        # 显示审查结果
        if quality_score >= 80:
            status = "[green]✓ 优秀[/green]"
        elif quality_score >= 70:
            status = "[yellow]△ 良好[/yellow]"
        else:
            status = "[red]✗ 需改进[/red]"

        review_text = f"质量评分: {quality_score:.1f}/100 {status}\n\n"
        review_text += assessment

        if issues:
            review_text += "\n\n主要问题:\n"
            for issue in issues[:5]:  # Show top 5 issues
                severity = issue.get('severity', 'info')
                message = issue.get('message', '')
                review_text += f"• [{severity}] {message}\n"

        console.print(Panel(
            review_text,
            title="📊 审查报告",
            border_style="magenta"
        ))

        # 总结
        console.print(f"\n[bold green]✓ 任务完成！[/bold green]")
        console.print(f"\n输出目录: [cyan]{output_dir}[/cyan]")

        # 查找主入口文件
        main_files = list(output_dir.glob("index.html")) + list(output_dir.glob("*.html")) + list(output_dir.glob("main.py"))
        if main_files:
            main_file = main_files[0]
            console.print(f"主文件: [cyan]{main_file.name}[/cyan]")

            # 尝试自动打开
            if main_file.suffix == '.html':
                console.print(f"\n[bold]正在浏览器中打开...[/bold]")
                import subprocess
                import platform
                
                try:
                    system = platform.system()
                    if system == 'Windows':
                        # Windows: 使用 start 命令
                        subprocess.run(['cmd', '/c', 'start', '', str(main_file)], check=False)
                    elif system == 'Darwin':
                        # macOS: 使用 open 命令
                        subprocess.run(['open', str(main_file)], check=False)
                    else:
                        # Linux: 使用 xdg-open 命令
                        subprocess.run(['xdg-open', str(main_file)], check=False)
                except Exception as e:
                    console.print(f"[yellow]⚠ 无法自动打开浏览器: {e}[/yellow]")
                    console.print(f"[yellow]请手动打开: {main_file}[/yellow]")

        return {
            'success': True,
            'output_dir': str(output_dir),
            'files': [f.get('path') if isinstance(f, dict) else f for f in generated_files],
            'quality_score': quality_score
        }

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {e}[/bold red]")
        import traceback
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        return {'success': False, 'error': str(e)}


async def interactive_mode():
    """交互模式"""
    print_welcome()
    
    base_output = Path("outputs/generated_projects")
    base_output.mkdir(parents=True, exist_ok=True)
    
    task_count = 0
    
    while True:
        console.print("\n" + "─" * 70)
        user_input = Prompt.ask(
            "\n[bold cyan]请输入您的任务描述[/bold cyan]",
            default=""
        )
        
        if not user_input or user_input.strip() == "":
            continue
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            console.print("\n[bold]再见！[/bold] 👋\n")
            break
        
        task_count += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = base_output / f"task_{task_count}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        await execute_task(user_input, output_dir)


async def direct_mode(prompt: str):
    """直接模式（命令行参数）"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f"outputs/generated_projects/task_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result = await execute_task(prompt, output_dir)
    return result


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="交互式多智能体代码生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 交互模式
  python run_agent.py
  
  # 直接指定任务
  python run_agent.py --prompt "生成 arXiv 论文展示网页"
  
  # 指定输出目录
  python run_agent.py --prompt "创建待办事项应用" --output ./my_project
        """
    )
    
    parser.add_argument(
        '--prompt', '-p',
        type=str,
        help='直接指定任务描述（不进入交互模式）'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='输出目录'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='强制进入交互模式'
    )
    
    args = parser.parse_args()
    
    if args.prompt and not args.interactive:
        # 直接模式
        output = args.output or Path(f"outputs/generated_projects/task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        output.mkdir(parents=True, exist_ok=True)
        asyncio.run(execute_task(args.prompt, output))
    else:
        # 交互模式
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
