# UI/UX 指南

此文档定义 coding agent 输出网页时必须遵循的视觉/交互标准。禁止生成基础模板或“仅 Bootstrap”风格，所有组件需呈现旗舰级沉浸体验。

---

## 1. 视觉语言

1. **主题双态**：深浅主题 + `prefers-color-scheme` 自动切换，提供显式切换开关，状态保存到 `localStorage`。
2. **色彩体系**：主色 `#7C3AED` 与 `#22D3EE` 渐层，暗色背景 `#050A1F`，浅色背景 `#F5F7FB`，辅以霓虹高亮与柔和灰。
3. **排版**：`Space Grotesk`（标题）+ `Inter`（正文）+ `Space Mono`（数字/代码），标题字重 600+，行高 ≥1.7。
4. **玻璃拟态 + 3D**：卡片使用 `backdrop-filter: blur(20px)`、渐层描边、柔和阴影、20px 圆角；Hero 文案可使用 3D 透视（CSS/three.js）。
5. **动画**：滚动触发淡入、Parallax、粒子漂浮；关键交互使用 `GSAP`/`Framer Motion` 或 IntersectionObserver；Hover 具备光晕/微缩放。

---

## 2. 布局与组件

| 区块 | 高级要求 |
| --- | --- |
| Hero | 全屏渐层 + 粒子/three.js 背景；包含搜索、分类 Tabs、运行统计、主题切换；支持滚动提示。 |
| 导航 | 粘性/自动隐藏导航，含过滤入口、下载按钮、回到顶部快捷；移动端折叠为 FAB。 |
| 智能过滤面板 | 右侧 HUD 弹层（含多选 chips/滑块/checkbox），实时更新 URL Query，展示活跃标签数量。 |
| 论文卡片 | 3D hover、玻璃式卡片，展示标签、评分、代码/媒体状态图标；展开区域含摘要、操作按钮。 |
| 数据可视化 | 首页包含 sparkline/柱状图（每日新增、复现率、领域分布），详情页展示雷达图/仪表盘（impact/reproducibility）。 |
| 详情页 | 面包屑、主图画廊（lightbox）、评分徽章、标签云、代码折叠、媒体画廊、时间轴、相关文章推荐。 |

---

## 3. 交互细节

1. 搜索支持模糊匹配、快捷键提示（⌘K / Ctrl+K），输入时展示即时建议。
2. 标签 chips 可多选，状态同步至 URL（如 `?topics=vision,llm&difficulty=hard`），提供“一键清空”与“复制筛选链接”。
3. 代码块采用语法高亮 + 折叠（Accordion），具备复制按钮与“跳转仓库”链接。
4. 图片画廊支持 lightbox、缩略图、左右切换、下载、来源信息；占位图需注明 “AI-generated placeholder…”。
5. 评分徽章颜色随分值渐变，并可显示 tooltip 解释评分依据。
6. 页脚展示 run_id、生成时间、工具版本、重建命令，并提供“下载 audit”按钮。

---

## 4. 访问性与性能

- 所有可点击元素添加 `aria-label`，键盘可操作，焦点状态清晰；对比度满足 WCAG AA。
- 图片 `alt` 描述不可缺失；AI 占位图需告知限制。
- 组件模块化（Hero、FilterPanel、Card、TagBar、Timeline、DetailSection 等）并拆分到 `web/components/`。
- CSS 变量集中定义于 `:root` / `[data-theme="dark"]`，便于主题切换；可使用 Tailwind/原子化工具但需自定义主题。
- 懒加载图片、代码块与重型组件；使用 IntersectionObserver 触发动画；首页 LCP < 2.5s。

---

## 5. 可扩展性

1. 组件存放在 `web/components/`；布局样式独立文件，避免内联大段 CSS。
2. 配置放入 `config/ui_theme.json`、`config/tag_dictionary.json`，可被脚本读取。
3. 暴露 `window.CS_DAILY_STATE = { filters, tags, scores, theme, build_meta }`，供后续脚本/插件使用。
4. 提供构建脚本（如 `scripts/build_site.py` 或 npm script）输出 `site/` 静态资源。

---

> **Review 提醒**：ReviewAgent 会检查是否实现上述视觉/交互/无障碍/性能要求；若未达到，例如仍为基础模板、无动画、无双主题，将直接判定 `revise`。所有 UI 代码必须通过工具（write_file）生成，不得手动修改已有文件。

