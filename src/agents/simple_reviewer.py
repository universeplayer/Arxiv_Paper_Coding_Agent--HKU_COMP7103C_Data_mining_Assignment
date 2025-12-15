"""Simple Reviewer Agent for code quality assessment."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from ..core.api_pool import ParallelLLMManager
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class SimpleReviewerAgent:
    """Agent that reviews generated code for quality and correctness."""

    def __init__(self, api_manager: ParallelLLMManager):
        self.api_manager = api_manager
        self.settings = get_settings()

    async def review(
        self,
        objective: str,
        implementation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Review generated code files.

        Args:
            objective: User's original request
            implementation: Result from SimpleCoderAgent

        Returns:
            Dictionary with review results and quality assessment
        """
        logger.info("Starting code review phase")

        files = implementation.get("files", [])
        if not files:
            return {
                "success": False,
                "error": "No files to review"
            }

        # Review each file
        file_reviews = []
        for file_info in files:
            logger.info(f"Reviewing {file_info['path']}")

            review = await self._review_file(
                objective=objective,
                file_info=file_info
            )

            file_reviews.append(review)
            logger.info(f"✓ Reviewed {file_info['path']} - Score: {review['score']:.2f}")

        # Calculate overall quality score
        avg_score = sum(r["score"] for r in file_reviews) / len(file_reviews)

        # Identify issues
        all_issues = []
        for review in file_reviews:
            all_issues.extend(review.get("issues", []))

        # Generate overall assessment
        overall_assessment = await self._generate_overall_assessment(
            objective=objective,
            file_reviews=file_reviews,
            avg_score=avg_score
        )

        # Update README with review findings
        output_dir = implementation.get("output_dir")
        if output_dir:
            await self._update_readme_with_findings(
                output_dir=output_dir,
                file_reviews=file_reviews,
                avg_score=avg_score,
                all_issues=all_issues,
                overall_assessment=overall_assessment
            )

        return {
            "success": True,
            "quality_score": avg_score,
            "file_reviews": file_reviews,
            "total_issues": len(all_issues),
            "issues": all_issues,
            "assessment": overall_assessment,
            "passed": avg_score >= 0.7  # 70% threshold
        }

    async def _review_file(
        self,
        objective: str,
        file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Review a single file.

        Args:
            objective: User's original request
            file_info: File metadata including path and content

        Returns:
            Review results for this file
        """
        # Read file content
        file_path = Path(file_info["full_path"])
        if not file_path.exists():
            return {
                "file": file_info["path"],
                "score": 0.0,
                "issues": [{"severity": "critical", "message": "File not found"}],
                "suggestions": []
            }

        content = file_path.read_text(encoding="utf-8")

        # Determine file type
        file_ext = file_path.suffix.lower()
        
        # 限制内容长度以避免超过 API 限制
        # Qwen 模型限制：30720 tokens，约等于 20000 字符（考虑中文）
        # 保守起见，限制在 25000 字符
        max_content_length = 25000
        is_truncated = False
        if len(content) > max_content_length:
            content = content[:max_content_length]
            is_truncated = True
            logger.warning(f"File {file_info['path']} truncated from {len(content)} to {max_content_length} chars")

        # Build review prompt
        system_prompt = self._get_reviewer_system_prompt(file_ext)
        
        truncation_note = "\n\n⚠️ 注意：文件内容过长，已截取前 25000 字符进行审查。" if is_truncated else ""

        user_prompt = f"""请评审以下代码文件:

文件名: {file_info['path']}
任务目标: {objective}
文件说明: {file_info.get('description', 'N/A')}{truncation_note}

代码内容:
```
{content}
```

请从以下维度评审:
1. **代码质量** (0-100分):
   - 可读性和代码风格
   - 结构和组织
   - 命名规范
   - 注释质量

2. **功能完整性** (0-100分):
   - 是否满足任务要求
   - 功能实现的完整性
   - 边界情况处理

3. **健壮性** (0-100分):
   - 错误处理
   - 输入验证
   - 异常处理

4. **性能和最佳实践** (0-100分):
   - 性能优化
   - 遵循最佳实践
   - 安全性考虑

输出要求（务必严格遵守）：
1. 只输出一个 ```json ... ``` 代码块，不要包含任何额外文本、注释或说明。
2. JSON 内全部使用英文标点（","、":"、"[]" 等），不要使用中文引号或顿号。
3. 字符串必须使用双引号，布尔/数字使用原生 JSON 语法。

JSON 模板如下，请直接填入实际数值：
```json
{{
    "scores": {{
        "quality": <0-100>,
        "completeness": <0-100>,
        "robustness": <0-100>,
        "performance": <0-100>
    }},
    "issues": [
        {{"severity": "critical|warning|info", "message": "问题描述", "line": <行号或 null>}}
    ],
    "suggestions": [
        "改进建议1",
        "改进建议2"
    ],
    "summary": "简要总结"
}}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Get review using parallel API calls
        # gpt-5 系列需要更多 tokens（内部推理会消耗大量 tokens）
        is_gpt5 = "gpt-5" in self.settings.reviewer_model.lower()
        max_tokens = 4000 if is_gpt5 else 2000

        results = await self.api_manager.call_parallel(
            messages=messages,
            model=self.settings.reviewer_model,
            n_parallel=2,
            provider="openai",
            reasoning_effort="medium",  # gpt-5 系列审查使用中等推理
            max_tokens=max_tokens
        )

        if not results:
            return {
                "file": file_info["path"],
                "score": 0.5,
                "issues": [{"severity": "warning", "message": "Review failed"}],
                "suggestions": []
            }

        # Parse review result
        try:
            review_data = self._parse_review_result(results[0]["content"])
        except Exception as e:
            logger.error(f"Failed to parse review result: {e}")
            return {
                "file": file_info["path"],
                "score": 0.5,
                "issues": [],
                "suggestions": [],
                "raw_review": results[0]["content"]
            }

        # Calculate overall score (0-1 scale)
        scores = review_data.get("scores", {})
        avg_score = (
            scores.get("quality", 50) +
            scores.get("completeness", 50) +
            scores.get("robustness", 50) +
            scores.get("performance", 50)
        ) / 400.0

        return {
            "file": file_info["path"],
            "score": avg_score,
            "scores": scores,
            "issues": review_data.get("issues", []),
            "suggestions": review_data.get("suggestions", []),
            "summary": review_data.get("summary", "")
        }

    def _get_reviewer_system_prompt(self, file_ext: str) -> str:
        """Get system prompt for file reviewer.

        Args:
            file_ext: File extension (e.g., '.py', '.html')

        Returns:
            System prompt string
        """
        base_prompt = """你是资深的代码审查专家，拥有丰富的软件工程经验。

你的职责是:
1. 仔细审查代码质量
2. 识别潜在问题和改进空间
3. 提供建设性的反馈
4. 确保代码满足最佳实践

审查标准:
- 代码可读性和可维护性
- 功能完整性和正确性
- 错误处理和健壮性
- 性能和安全性
- 遵循语言/框架最佳实践"""

        if file_ext == ".py":
            return base_prompt + """

Python 特定关注点:
- PEP 8 代码规范
- 类型注解使用
- 异常处理
- 文档字符串质量
- 性能优化（列表推导、生成器等）"""

        elif file_ext in [".html", ".css", ".js"]:
            return base_prompt + """

前端特定关注点:
- HTML语义化和可访问性
- CSS性能和浏览器兼容性
- JavaScript现代性和最佳实践
- 响应式设计
- 用户体验"""

        return base_prompt

    def _parse_review_result(self, content: str) -> Dict[str, Any]:
        """Parse LLM review output.

        Args:
            content: Raw review content from LLM

        Returns:
            Parsed review data
        """
        # Try to extract JSON from content
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to find JSON object in text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # If all else fails, return default structure
            return {
                "scores": {
                    "quality": 50,
                    "completeness": 50,
                    "robustness": 50,
                    "performance": 50
                },
                "issues": [],
                "suggestions": [],
                "summary": "Review parsing failed"
            }

    async def _generate_overall_assessment(
        self,
        objective: str,
        file_reviews: List[Dict[str, Any]],
        avg_score: float
    ) -> str:
        """Generate overall assessment of the project.

        Args:
            objective: User's original request
            file_reviews: Reviews of all files
            avg_score: Average quality score

        Returns:
            Overall assessment text
        """
        # Count issues by severity
        critical_count = 0
        warning_count = 0
        info_count = 0

        for review in file_reviews:
            for issue in review.get("issues", []):
                severity = issue.get("severity", "info")
                if severity == "critical":
                    critical_count += 1
                elif severity == "warning":
                    warning_count += 1
                else:
                    info_count += 1

        # Generate assessment
        if avg_score >= 0.9:
            quality_level = "优秀"
        elif avg_score >= 0.7:
            quality_level = "良好"
        elif avg_score >= 0.5:
            quality_level = "及格"
        else:
            quality_level = "需要改进"

        assessment = f"""
代码质量评估: {quality_level} ({avg_score * 100:.1f}/100)

文件审查数量: {len(file_reviews)}
严重问题: {critical_count}
警告: {warning_count}
提示: {info_count}

总体评价:
"""

        if avg_score >= 0.8:
            assessment += "代码质量很高，满足生产环境要求。"
        elif avg_score >= 0.6:
            assessment += "代码质量良好，建议根据反馈进行小幅优化。"
        else:
            assessment += "代码需要进一步改进，请关注严重问题和警告。"

        if critical_count > 0:
            assessment += f"\n\n⚠️ 发现 {critical_count} 个严重问题，需要立即修复。"

        return assessment.strip()

    async def _update_readme_with_findings(
        self,
        output_dir: Path,
        file_reviews: List[Dict[str, Any]],
        avg_score: float,
        all_issues: List[Dict[str, Any]],
        overall_assessment: str
    ) -> None:
        """Update README with review findings.

        Args:
            output_dir: Output directory path
            file_reviews: List of file review results
            avg_score: Average quality score
            all_issues: All issues found
            overall_assessment: Overall assessment text
        """
        readme_path = output_dir / "README.md"
        
        if not readme_path.exists():
            logger.warning(f"README not found at {readme_path}, skipping update")
            return

        try:
            # Read existing README
            existing_content = readme_path.read_text(encoding="utf-8")
            
            # Remove old review section if exists
            if "\n## 审查报告" in existing_content:
                existing_content = existing_content.split("\n## 审查报告")[0]
            
            # Build review section
            review_section = "\n\n## 审查报告\n\n"
            review_section += f"**审查时间**: {self._get_current_time()}\n\n"
            review_section += f"**质量评分**: {avg_score * 100:.1f}/100\n\n"
            review_section += f"### 总体评价\n\n{overall_assessment}\n\n"
            
            # Add file-specific findings
            if file_reviews:
                review_section += "### 文件审查详情\n\n"
                for review in file_reviews:
                    file_name = review.get("file", "unknown")
                    score = review.get("score", 0) * 100
                    review_section += f"#### {file_name} (评分: {score:.1f}/100)\n\n"
                    
                    # Issues
                    issues = review.get("issues", [])
                    if issues:
                        review_section += "**发现的问题**:\n\n"
                        for issue in issues:
                            severity = issue.get("severity", "info")
                            message = issue.get("message", "")
                            line = issue.get("line")
                            severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")
                            line_str = f" (行 {line})" if line else ""
                            review_section += f"- {severity_emoji} [{severity.upper()}]{line_str}: {message}\n"
                        review_section += "\n"
                    
                    # Suggestions
                    suggestions = review.get("suggestions", [])
                    if suggestions:
                        review_section += "**改进建议**:\n\n"
                        for suggestion in suggestions:
                            review_section += f"- 💡 {suggestion}\n"
                        review_section += "\n"
            
            # Add improvement plan section
            if avg_score < 0.9:  # Only add if not perfect
                review_section += "\n### 改进计划建议\n\n"
                review_section += "基于以上审查发现的问题，建议制定以下改进计划：\n\n"
                
                # Group issues by severity
                critical_issues = [i for i in all_issues if i.get("severity") == "critical"]
                warning_issues = [i for i in all_issues if i.get("severity") == "warning"]
                
                if critical_issues:
                    review_section += "**优先级 1 - 严重问题** (必须修复):\n\n"
                    for idx, issue in enumerate(critical_issues[:5], 1):
                        review_section += f"{idx}. {issue.get('message', '')}\n"
                    review_section += "\n"
                
                if warning_issues:
                    review_section += "**优先级 2 - 警告问题** (建议修复):\n\n"
                    for idx, issue in enumerate(warning_issues[:5], 1):
                        review_section += f"{idx}. {issue.get('message', '')}\n"
                    review_section += "\n"
                
                review_section += "**优先级 3 - 优化建议** (可选):\n\n"
                review_section += "- 代码注释和文档完善\n"
                review_section += "- 性能优化和代码重构\n"
                review_section += "- 添加更多测试用例\n\n"
            
            # Write updated README
            updated_content = existing_content.rstrip() + review_section
            readme_path.write_text(updated_content, encoding="utf-8")
            
            logger.info(f"✓ Updated README with review findings at {readme_path}")
            
        except Exception as e:
            logger.error(f"Failed to update README: {e}")
    
    def _get_current_time(self) -> str:
        """Get current time as formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
