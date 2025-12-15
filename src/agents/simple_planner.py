"""简化的规划智能体 - 用于交互式代码生成"""

import json
from typing import Dict, Any
from pathlib import Path

from src.core.api_pool import ParallelLLMManager
from src.core.config import get_settings


class SimplePlannerAgent:
    """规划智能体 - 使用 Chain-of-Thought 分解任务"""

    def __init__(self, api_manager: ParallelLLMManager):
        self.settings = get_settings()
        self.api_manager = api_manager
    
    async def plan(self, objective: str) -> Dict[str, Any]:
        """制定任务执行计划
        
        Args:
            objective: 用户的自然语言需求
            
        Returns:
            包含计划的字典
        """
        system_prompt = """你是一个专业的软件架构师和规划专家。
你的任务是理解用户需求，使用 Chain-of-Thought 推理将其分解为具体可执行的任务。

请以 JSON 格式输出，包含：
1. plan_summary: 任务的简要总结（1-2句话）
2. tasks: 子任务列表，每个任务有 description
3. architecture: 建议的文件结构
4. technologies: 需要的技术栈

示例输出：
{
  "plan_summary": "创建一个展示 arXiv 论文的网页应用",
  "tasks": [
    {"id": 1, "description": "设计网页HTML结构"},
    {"id": 2, "description": "编写JavaScript获取arXiv数据"},
    {"id": 3, "description": "添加CSS样式美化页面"}
  ],
  "architecture": {
    "files": ["index.html", "script.js", "style.css"]
  },
  "technologies": ["HTML5", "JavaScript", "CSS3", "arXiv API"]
}"""

        user_prompt = f"""用户需求：{objective}

请使用 Chain-of-Thought 推理：
1. 理解需求的核心目标
2. 识别需要实现的功能
3. 分解为具体的开发任务
4. 设计合理的文件结构

请直接返回 JSON，不要其他文字。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        results = await self.api_manager.call_parallel(
            messages=messages,
            model="gpt-4o-mini",
            n_parallel=1,
            temperature=0.3,
            max_tokens=1500
        )
        
        content = results[0]["content"].strip()
        
        # 提取 JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
        
        try:
            plan = json.loads(json_str)
            return plan
        except json.JSONDecodeError:
            # 如果解析失败，返回基本计划
            return {
                "plan_summary": objective,
                "tasks": [{"id": 1, "description": objective}],
                "architecture": {"files": ["index.html"]},
                "technologies": ["HTML", "JavaScript"]
            }

    async def plan_revision(self, readme_path: Path) -> Dict[str, Any]:
        """根据 README 中的审查报告制定修改计划
        
        Args:
            readme_path: README 文件路径
            
        Returns:
            包含修改计划的字典
        """
        if not readme_path.exists():
            return {
                "error": "README not found",
                "tasks": []
            }
        
        # 读取 README 内容
        readme_content = readme_path.read_text(encoding="utf-8")
        
        # 检查是否有审查报告
        if "## 审查报告" not in readme_content:
            return {
                "error": "No review report found in README",
                "tasks": []
            }
        
        # 提取审查报告部分
        review_section = readme_content.split("## 审查报告")[1]
        if "##" in review_section:
            review_section = review_section.split("##")[0]
        
        system_prompt = """你是一个专业的软件工程师，擅长根据代码审查报告制定改进计划。

你的任务是：
1. 分析审查报告中发现的问题
2. 按优先级排序问题
3. 制定具体的修改任务计划

输出 JSON 格式：
{
  "plan_summary": "修改计划总结",
  "priority": "high|medium|low",
  "tasks": [
    {
      "id": 1,
      "description": "具体的修改任务描述",
      "priority": "critical|warning|info",
      "target_file": "需要修改的文件名",
      "estimated_effort": "low|medium|high"
    }
  ],
  "expected_improvements": ["改进点1", "改进点2"]
}"""

        user_prompt = f"""以下是 README 中的审查报告：

{review_section}

请根据审查报告中发现的问题制定修改计划。重点关注：
1. 严重问题（critical）必须优先处理
2. 警告问题（warning）应该处理
3. 改进建议可以选择性实现

请直接返回 JSON，不要其他文字。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        results = await self.api_manager.call_parallel(
            messages=messages,
            model="gpt-4o-mini",
            n_parallel=1,
            temperature=0.3,
            max_tokens=2000
        )
        
        content = results[0]["content"].strip()
        
        # 提取 JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
        
        try:
            plan = json.loads(json_str)
            return plan
        except json.JSONDecodeError:
            # 如果解析失败，返回基本计划
            return {
                "plan_summary": "根据审查报告进行代码改进",
                "priority": "medium",
                "tasks": [{"id": 1, "description": "修复审查中发现的问题"}],
                "expected_improvements": ["提高代码质量"]
            }
