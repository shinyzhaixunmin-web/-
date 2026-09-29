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

## 生产出的技能怎么用

把 `skills/<name>/` 复制到任意项目的 `.claude/skills/` 下（或 `~/.claude/skills/` 全局可用），然后用 `/<name>` 调用，Claude 也会在合适的场景自动触发。

## 结构

```
inbox/          原始资料
knowledge/      蒸馏成品（core.md）+ 中间产物（_text/ 分块文本，_notes/ 精读笔记）
knowledge/_needs/  按需提炼结果
skills/         生产出的技能
templates/      知识卡与技能模板
tools/to_text.py  格式转换与分块（纯标准库；PDF 需 pdftotext 或 pypdf）
.claude/skills/ 本工坊的三个工作流技能：distill / extract / forge-skill
```

规则与质量底线见 [CLAUDE.md](CLAUDE.md)。
