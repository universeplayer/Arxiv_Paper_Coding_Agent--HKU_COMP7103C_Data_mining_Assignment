# 多智能体任务矩阵

| 任务 ID | 负责人 | 目标 | 关键产物 | 应引用的文档 |
| --- | --- | --- | --- | --- |
| plan-1 | PlanningAgent | 将用户需求映射为 5 个任务，定义 schema、前端组件树、工具列表、审计策略。 | `spec/enhanced_plan.json`、`spec/ui_components.md` | `arxiv_cs_daily_spec.md`, `ui_ux_guidelines.md` |
| plan-2 | CodeAgent | 抓取 arXiv 数据、生成标签/评分、输出结构化 JSON。 | `data/raw_metadata.json`、`data/papers_list.json`、`tags.json` | `code_media_brief.md` |
| plan-3 | CodeAgent | 构建代码/媒体增强脚本并运行，产出 `code_snapshots/`、`media/`、`repos/`、`io_log.json`。 | `scripts/code_media_extractor.py`、快照/媒体文件 | `code_media_brief.md` |
| plan-4 | CodeAgent | 实现高级前端（Hero、Filters、Cards、Detail、Charts、Dark/Light、可访问性、响应式）。 | `web/` 组件、`site/` 构建产物、`static/` 资源 | `ui_ux_guidelines.md` |
| plan-5 | ReviewAgent | 审核 UI、数据增强、审计日志与可复现性，输出结论与修复建议。 | `audit/audit.json`、`review_report.json`、`run.sh` | 所有上游文档 |

> 在 Planner 输出中应直接引用上述矩阵，确保任务覆盖所有增强项。若任务数不足或缺少关键产物，ReviewAgent 必须要求返工。

