# 代码与媒体增强需求
本说明约束 coding agent 在“解析论文 → 复现代码 → 获取图片 → 生成标签/评分”全过程中的产物格式、日志记录与失败策略。所有逻辑必须由自动化脚本或工具完成，禁止直接手工修改生成代码。

---

## 1. 核心任务

### 1.1 代码复现情报

1. 扫描 `raw_metadata.json`、PDF 文本、评论、附加链接获取仓库/伪代码线索。  
2. 通过工具克隆仓库（或模拟下载），提取：
   - README 前 2000 字、关键命令、安装步骤；
   - Top-K `.py` 文件（按“函数 + 类”数量评分）并截取 4k 字符片段；
   - 依赖列表、推荐运行命令、复现难度（easy / medium / hard）、成功概率评估。
3. 写入 `code_snapshots/<paper_id>.md`，结构包含：
   ```
   # Repo Snapshot
   - repo_url
   - detected_branch / commit
   - dependencies
   - run_commands
   - difficulty / success_probability
   ## README snippet
   ...
   ## code/xxx.py
   ```  
4. 将状态（成功/失败/原因）记入 `io_log.json` 与 `audit/tool_report.md`。

### 1.2 关键图片 / Figure

1. 尝试从 PDF 中提取首图或嵌入图片；若失败则渲染首页，仍失败则生成 AI 描述占位符（无需真正调用图像模型，但需写入日志）。  
2. 输出到 `media/<paper_id>/fig_1.png` 等；同时创建 `media/<paper_id>/metadata.json`，包含：
   ```
   {
     "paper_id": "...",
     "source": "pdf-embedded" | "render-first-page" | "ai-placeholder",
     "caption": "...",
     "confidence_score": 0-1,
     "sha256": "...",
     "generated_at": "ISO time"
   }
   ```
3. 在 audit 中记录操作结果与 degrade 说明。

### 1.3 标签与评分

1. 生成结构化字段：`key_topics`、`methods`、`datasets`、`difficulty`、`impact_score (0-100)`、`reproducibility_score (0-100)`、`novelty_score`、`risk_flags`、`rationale`。  
2. 写入 `papers_list.json`，供前端过滤器使用；评分依据需写入 `audit/tool_report.md`（提示词或规则）。

---

## 2. 目录与文件

```
workspace_runs/<run_id>/
├─ data/
│  ├─ raw_metadata.json
│  └─ papers_list.json   # 包含 tags/scores/code/media 状态
├─ code_snapshots/
│  └─ <paper_id>.md
├─ media/
│  └─ <paper_id>/
│     ├─ fig_1.png (或 txt 占位符)
│     └─ metadata.json
├─ repos/
│  └─ <paper_id>/...     # 克隆仓库（可按需清理）
├─ audit/
│  ├─ audit.json
│  ├─ tool_report.md     # 子任务摘要、提示词、评分依据
│  └─ io_log.json        # 每次下载/写入记录
```

---

## 3. 审计要求

- **尝试记录**：每篇论文必须有代码/媒体尝试记录（成功/失败 + 原因），并写入 `io_log.json` 与 `audit/audit.json`。  
- **哈希与时间**：所有生成文件均计算 `sha256` 并记录 `generated_at`。  
- **degrade 策略**：无法获取文件时写明 `status=degraded`、错误信息、建议操作。  
- **评分解释**：`rationale` 必须存在，ReviewAgent 会比对摘要内容。

---

## 4. 前端联动

- 详情页“Code & Media”区需展示：
  - README 摘要 + 可折叠代码块 + 复制按钮 + 跳转仓库链接；
  - 图片画廊（lightbox、下载、来源提示、占位符说明）；
  - 标签徽章、雷达图/仪表盘、风险提示（如 Need GPU、Dataset private）。  
- 列表卡片显示 `code`/`media` 状态图标（✓ / ⚠️ / ✗），并展示评分徽章。

---

## 5. 失败策略

1. 代码下载失败 → 在 `code_snapshots/<paper_id>.md` 写入“已尝试链接 + 错误信息 + 建议”。  
2. 图片提取失败 → 写入 `media/<paper_id>/figure_placeholder.txt` + metadata，详情页展示占位提示。  
3. 若政策或权限限制，提供人工步骤并在 audit 中标记 `manual_step_required=true`。

> **提示**：所有脚本必须包含英文注释、异常处理、日志输出；若需要外部依赖（git、PyMuPDF、Pillow 等）需在 README 或脚本说明中提示，但不得手动修改已生成代码。

