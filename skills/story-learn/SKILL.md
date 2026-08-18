---
name: story-learn
version: 1.0.0
description: 中文小说自学习流水线。触发词："学习新语料""吸收范文""更新基线""语料进来自动分析""学一下这些文章"。当用户提供新的范文/语料目录（知乎盐选文章、签约作品集等）时：① 运行 analyze-corpus.py 统计分析（题材/导语/分节/结尾/母题）；② 运行 update-baselines.py 自动合并进 story-platform/references/genre-baselines.md 题材基线库与 tropes.md 套路母题库；③ 精读新语料提炼新技法更新 craft.md；④ 追加校准日志并输出学习报告。语料更新即可重学，基线永远保鲜。
metadata: {"openclaw":{"source":"https://github.com/wangliang01/oh-story"}}
---

# story-learn · 自学习流水线

把任何语料转化为 skill 知识资产的固定流程。**语料进 → 数据出 → 基线更新 → 学习报告**。

## 何时使用
- 用户提供新的范文/语料目录（"学一下这些文章""吸收这个仓库"）
- 现有语料更新了，需要重学（"重新分析"）
- 需要看看当前基线数据（"现在基线是什么"）

## 流程

### 第 1 步 · 确认语料
- 用户给了路径 → 用它；没给 → 搜索常见位置（项目 `corpus/`、`~/Downloads`、已 clone 的语料仓库目录），找不到就问。
- 语料通常是 markdown 集合（可能带 HTML 噪音，脚本会清洗）。

### 第 2 步 · 统计分析
运行（skill 同目录的脚本，语料目录传绝对路径）：
```
python <story-platform skill 目录>/scripts/analyze-corpus.py <语料目录> --json=corpus-stats.json
```
`<story-platform skill 目录>` 按「参考资料解析顺序」定位（story-conception 中有定义；通常为 `.claude/skills/story-platform/`、`.opencode/skills/story-platform/`、`skills/story-platform/` 之一）。
- **注意 `--json=` 必须带等号**（`--json <路径>` 不会被解析）。
- **Windows 路径坑**：Git Bash 的 `/tmp` 原生 Python 不认，语料目录与输出文件都用真实 Windows 路径（`C:\...`）或项目内相对路径；跑 Git Bash 的 shell 和原生 Python 解析路径的规则不一致。
- 语料巨大（数千篇）时加 `--limit=1500` 抽样，报告里注明是抽样（抽样已改为固定种子随机，可复现；不要用 9~11 节这种短问答规则覆盖签约文 15~21 节规则——update-baselines.py 已加保护，只降不升）。
- 读输出：题材分布、导语长度、分节、结尾类型、母题词频、各题材导语样本。

随后把 `corpus-stats.json` 传给 update-baselines.py（同一进程内路径规则一致，直接传相对路径即可）。

### 第 3 步 · 自动更新基线
运行：
```
python <story-platform skill 目录>/scripts/update-baselines.py <corpus-stats.json 路径>
```
脚本默认把基线文件写到同 skill 的 `references/` 下（`genre-baselines.md` / `tropes.md`），可用 `--dir <story-platform 目录>` 覆盖。
- 自动合并进 `story-platform/references/genre-baselines.md`（通用数据表 + 语料样本区）和 `story-platform/references/tropes.md`（母题词频）。
- curated 文本（变体/警报/技法）不会被覆盖——只更新数据。

### 第 4 步 · 精读提炼新技法（模型判断，脚本替代不了）
- 从本次语料中新出现的导语/结尾/开头样本里，找**现有 story-platform/references/craft.md / genre-baselines.md 没覆盖的模式**（新母题、新结尾类型、新细节手法）。
- 有 → 追加进 story-platform/references/craft.md 对应章节或 story-platform/references/genre-baselines.md 对应题材；无 → 跳过并说明"无新技法"。

### 第 5 步 · 校准日志 + 学习报告
- 在 `story-qualify/references/qualify-notes.md` 校准日志追加一条：日期、语料、样本量、更新了哪些资产、新发现。
- 向用户输出学习报告：
  - 学了什么（语料/样本量）
  - 更新了什么（基线/套路/技法，逐项）
  - 数据亮点（导语/结尾/母题的关键数字）
  - 新发现（值得注意的模式）

## 完成标准
- analyze + update 两个脚本都跑通，基线文件已更新
- 校准日志已追加
- 学习报告已输出（含数据亮点与更新清单）
