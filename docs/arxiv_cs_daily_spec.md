# arXiv CS Daily · Flagship Spec

> 面向 coding agent 的**强约束指令**。禁止直接修改需生成的网页代码，只能通过 Planner → Coder → Reviewer 的链式协作，以本规范作为唯一蓝本，确保最终网页具备旗舰级视觉、智能增强、代码复现与图像展示能力。

---

## 1. 愿景与边界

1. **体验愿景**：打造“沉浸式论文探索工作台”，集成 3D Hero、即时过滤、动态分析、代码复现快照、关键图片画廊与审计追踪。
2. **内容范围**：覆盖 cs.AI / cs.CL / cs.CV / cs.TH / cs.SY 等子领域，抓取 6–20 篇当日新论文，保留可扩展能力。
3. **协作要求**：全流程 ≤8 步，由多智能体完成规划、开发、质检；任一步缺失即判失败。

---

## 2. 旗舰体验基线

- **Hero & Global Nav**：全屏渐层 + 粒子/three.js 背景，显示今日论文计数、领域覆盖、复现成功率；导航含 Tabs、暗/亮主题自动切换、⌘K 搜索、下载审计入口。
- **智能过滤 HUD**：右侧折叠面板，提供 tags / sliders / pill 组合，支持 `key_topics`、`methods`、`datasets`、`difficulty`、`impact_score`、`reproducibility_score`、`risk_flags`、`labels[]`，状态同步 URL，可复制筛选链接。
- **论文卡片**：玻璃拟态 + 3D hover，展示评分徽章、标签、复现状态（Code/Media badges），展开层含摘要、复制引用、收藏/置顶、跳转详情。
- **详情视图**：面包屑、主图画廊（lightbox + 下载 + 来源提示）、评分雷达图、标签云、代码折叠块（含语法高亮/复制/仓库跳转）、时间轴、相关文章推荐。
- **时间轴与审计页脚**：展示版本迭代、工具调用、生成耗时；页脚带 `run_id`、SHA256、重建命令、Audit 下载按钮。

更多视觉标准详见 `docs/ui_ux_guidelines.md`；Reviewer 将严格比对，缺少任一交互即判 `revise`。

---

## 3. 数据与智能增强管线

| 能力 | 产物 | 要点 |
| --- | --- | --- |
| **标签/评分生成** | `data/papers_list.json`、`tags.json` | 字段含 `key_topics`、`methods`、`datasets`、`difficulty`、`impact_score`、`reproducibility_score`、`novelty_score`、`risk_flags`、`rationale`。提供排序键、筛选映射。 |
| **代码复现情报** | `code_snapshots/<paper_id>.md`、`repos/<paper_id>/` | 抓取/克隆仓库，提取 README 摘要、Top-K `.py` 片段、依赖、运行命令、`difficulty`、`success_probability`。失败需写 degrade 建议。 |
| **关键图片提取** | `media/<paper_id>/fig_*.png`、`metadata.json` | 优先 PDF 内嵌 → 首页渲染 → AI 占位；记录 `source`、`caption`、`confidence_score`、`sha256`。 |
| **时间轴 & 审计** | `data/history.json`、`audit/audit.json`、`audit/tool_report.md` | 每篇论文包含版本列表（时间、差异摘要、来源链接）；审计记录工具链、耗时、失败原因、graceful degrade。 |

所有脚本、下载、写入必须记录到 `audit/io_log.json` 并附 SHA256。

---

## 4. 必备模块与交互

| 模块 | 描述 | 关键交互 |
| --- | --- | --- |
| Hero + Stats Dock | 3D 场景、运行概览、今日亮点按钮、主题切换 | 粘性导航、滚动提示、键盘快捷键、Lottie/GSAP 动画 |
| Filter & Insight Panel | HUD 样式过滤器 + 小型分析图 | 多选 Chips + 滑块，URL 同步，显示活跃标签数量 |
| Papers Grid / Masonry | 自适应卡片，含评分、标签、Code/Media 状态 | Hover 浮层、收藏、复制引用、快速跳详情 |
| Detail Drawer / Page | 图像画廊、代码折叠区、时间轴、相关文章 | Lightbox、代码复制、仓库跳转、时间轴节点对比 |
| Code & Media Hub | README 摘要、Top 片段、媒体画廊、风险提示 | 折叠/展开、复制命令、下载图片、占位提示 |
| Timeline + Audit Footer | 运行历史与审计入口 | 节点 tooltip、Diff 摘要、下载 audit JSON |

前端需拆分至 `web/components/`，遵守 `docs/ui_ux_guidelines.md` 的主题、字体、动画、可访问性要求。

---

## 5. 多智能体任务拆解（Planner 必须输出）

1. **plan-1 规格增强**：汇总本规范 + `docs/ui_ux_guidelines.md` + `docs/code_media_brief.md`，生成 `spec/enhanced_plan.json`（含任务图、里程碑、验收项）。
2. **plan-2 数据获取**：抓取 arXiv → 结构化存入 `data/raw_metadata.json`、`data/papers_list.json`、`tags.json`，附标签/评分 rationale。
3. **plan-3 代码 & 媒体脚本**：实现/调用 `scripts/code_media_extractor.py`，产出 `code_snapshots/`、`media/`、`repos/`、`audit/io_log.json`，并记录 degrade。
4. **plan-4 前端构建**：依据 UI 指南完成 Hero、Filters、Cards、Detail、Charts、Timeline、暗/亮主题、响应式、状态管理；输出 `workspace_runs/<run_id>/site/`。
5. **plan-5 审计复核**：生成 `audit/audit.json`、`audit/tool_report.md`、`review_report.json`、`run.sh` 或 README，验证可复现性。

缺少任一 plan 即判未达标。

---

## 6. 交付物与目录

```
workspace_runs/<run_id>/
├─ data/
│  ├─ raw_metadata.json
│  ├─ papers_list.json
│  └─ history.json
├─ code_snapshots/
│  └─ <paper_id>.md
├─ media/<paper_id>/
│  ├─ fig_*.png 或 placeholder
│  └─ metadata.json
├─ repos/<paper_id>/...
├─ site/ (最终网页静态资源，勿手改)
├─ scripts/
│  └─ code_media_extractor.py (+ 运行日志)
├─ audit/
│  ├─ audit.json
│  ├─ tool_report.md
│  └─ io_log.json
└─ metadata.json / run.sh / review_report.json
```

任何手动更改 `site/` 代码的行为均视为违规；修改需通过重新运行脚本或 write_file。

---

## 7. 全局约束

- 仅可调用 OpenAI `gpt-5-mini`；若需多样性，使用客户端并行采样，禁止设温度。
- 所有外部访问（下载、克隆、解析）必须由工具或生成脚本完成，并在 `audit/io_log.json` 中逐条记录。
- 执行步数 ≤8；若需求复杂，Planner 必须先扩展任务图再分派。
- 所有产物写入 `workspace_runs/{timestamp}`，并生成 `metadata.json`、`run_id`、`sha256`。

---

## 8. 验收清单

1. **视觉/交互**：双主题、渐层、3D、动画、HUD 过滤、图像画廊、雷达图全部落地；移动端/无障碍合格。
2. **数据完整**：每篇论文具备标签、评分、`rationale`、代码/媒体状态；时间戳 <24h。
3. **代码复现与媒体**：`code_snapshots/`、`repos/`、`media/`、`io_log.json` 齐备，失败含 degrade 策略。
4. **前端联动**：过滤、排序、标签、Code/Media 状态、时间轴、审计页脚均可正常交互。
5. **审计 & 复现**：`audit/audit.json`、`tool_report.md`、`run.sh`/README 完整；可按指令重新生成站点。

任一条未满足 → Reviewer 输出 `revise` 并写明缺陷原因。

---

## 9. 参考资料

- `docs/ui_ux_guidelines.md`：视觉/交互/性能规范
- `docs/code_media_brief.md`：代码复现与媒体提取流程
- `docs/agent_task_matrix.md`：多智能体职责
- `README.md`：运行命令、依赖、示例

> 在每次 Planner 输出中引用关键条款（模块/数据/验收），确保 coding agent 按照“更高级、直观、功能完整”的目标构建网页。

