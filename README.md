# 知识蒸馏工坊

把文件或书籍**蒸馏**成核心本质知识，**按需提炼**针对具体问题的知识，并把知识**生产成可复用的 Claude 技能**。

## 用法

1. 把资料放进 `inbox/`（支持 PDF、EPUB、DOCX、TXT、MD、HTML），或直接在对话里上传。
2. 告诉 Claude 你要什么：

| 你说 | 做什么 | 产出 |
|---|---|---|
| `/distill inbox/穷查理宝典.epub` 或"蒸馏这本书" | 通读全书，提取本质、核心模型、方法 | `knowledge/<slug>/core.md` |
| `/extract 我要准备一次薪资谈判` | 带着问题，从已有资料里定向提取 | `knowledge/_needs/<主题>.md` |
| `/forge-skill <slug>` 或"把它做成技能" | 把知识变成指导行动的技能 | `skills/<name>/SKILL.md` |

只丢文件、不说要做什么时，默认执行蒸馏。

## 生产出的技能在哪里调用

| 在哪里用 | 怎么安装 | 覆盖范围 |
|---|---|---|
| **claude.ai 账号（推荐）** | 运行 `python3 tools/pack_skills.py` 生成 `dist/<技能名>.zip`，然后在 claude.ai 或桌面 App 中打开 **Customize → Skills → + → Create skill → Upload a skill**，逐个上传 | 网页版、桌面 App、Cowork、云端 Claude Code 会话；已用 claude.ai 账号登录的终端 Claude Code 也会自动同步。需要在设置里开启"代码执行与文件创建" |
| **本仓库** | 已通过符号链接放进 `.claude/skills/`，不需要安装 | 在本仓库打开 Claude Code（包括云端会话）时直接可用 |
| **其他某个项目** | 复制 `skills/<名>/` 到该项目的 `.claude/skills/` | 只在那个项目里可用 |
| **本机所有项目** | 复制到 `~/.claude/skills/` | 本机终端里的 Claude Code |

调用方式：输入 `/<技能名>`（例如 `/salon-kaizen-card`），或者直接描述问题（例如"我的沙龙新客留不住"），Claude 会自动选择合适的技能。

打包时，技能之间引用的共享文件（例如 `reference.md`）会被复制进每个包，所以每个 ZIP 都可以单独上传。

## 已生产的技能

来源：丰田 CI × 丹纳赫 DBS 沙龙经营模型（`knowledge/shiny-ci-dbs-v1/`）。五个技能要**一起复制**，因为专项技能会引用 `salon-strategy-advisor/reference.md`。

| 技能 | 用途 | 模型 |
|---|---|---|
| `salon-strategy-advisor` | 综合咨询：问题分层、证据门槛、按 8 项模板出方案 | 两者 |
| `salon-kaizen-card` | 给单个问题开改善问题卡、设计试点 | 丰田 CI |
| `salon-pilot-review` | 复盘试点：继续、调整、停止还是固化 | 丰田 CI |
| `salon-policy-deployment` | 年度或季度方针展开，只定 1–3 个突破目标 | 丹纳赫 DBS |
| `salon-expansion-check` | 开店、收购、升级、关店评估 | 丹纳赫 DBS |

完整示例：[examples/demo-salon/](examples/demo-salon/)。这是一个虚构两店沙龙的完整经营周期，包含模拟数据、脚本算出的基线报告，以及 5 个技能各自的产出。

## 结构

```
inbox/          原始资料
knowledge/      蒸馏成品（core.md）+ 中间产物（_text/ 分块文本，_notes/ 精读笔记）
knowledge/_needs/  按需提炼结果
skills/         生产出的技能
templates/      知识卡与技能模板
tools/to_text.py  格式转换与分块（纯标准库；PDF 需 pdftotext 或 pypdf）
tools/salon_metrics.py  沙龙经营基线与试点指标计算（纯标准库，数据格式见 examples/demo-salon/data/数据字典.md）
examples/       完整示例
stores/         放你自己门店的数据与报告（stores/*/data/ 不提交到 git）
.claude/skills/ 本工坊的三个工作流技能：distill / extract / forge-skill
```

规则与质量底线见 [CLAUDE.md](CLAUDE.md)。
