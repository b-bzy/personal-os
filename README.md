# personal-os · 个人反思操作系统

一个 [Claude Code](https://claude.com/claude-code) Skill：把日常失误结构化沉淀成一本长期总账，再按日 / 周把它折叠成一份能看出模式的 PDF。

重点不是"记下来"，而是**跨周期看重复**——同一类错犯到第三次时，它应该在报告里显形。

## 它能做什么

| 你说 | 它做 |
|---|---|
| 「今天做错了一件事 / 记一笔」 | 结构化抽取 + 分类，追加到长期总账 `犯错总账.md` |
| 「出日报 / 今日复盘」 | 生成当日反思日报 PDF |
| 「出周报 / 出反思周报」 | 按 Dubai Week 提取本周条目，找出反复犯错的通性，生成周报 PDF |

每条记录抽取 4 个字段（背景 / 问题 / 经验 / 日期），自动补 id 和分类。分类为 5 选 1，定义见 [`references/categories.md`](references/categories.md)。

入库时默认做**润色**：改错字病句、口语化转准确词、统一序号——但不合并或拆分你的分点，不增加你没写的内容，不脑补根因。

## 周次体系：Dubai Week

报告不用 ISO 周，也不用月内周，而是自定义的 **Dubai Week**（`DW1` `DW2` …）：以周日为一周起点，锚点 `DW1 = 2026-04-19`。日期计算统一收敛在 [`scripts/lib_dates.py`](scripts/lib_dates.py)，并强制以 `TZ='Asia/Dubai'` 现场采集当天日期，避免模型凭上下文里的过期日期做心算。

改锚点或改时区，只需要动 `lib_dates.py` 一处。

## 目录结构

```
personal-os/
├── SKILL.md                  # 主流程定义（触发词路由 + 流程 A/B/C）
├── scripts/
│   ├── lib_dates.py          # Dubai Week 共享日期工具
│   ├── append_entry.py       # 反思入库
│   ├── analyze_daily.py      # 当日条目聚合
│   ├── analyze_weekly.py     # 本周条目聚合
│   └── render_pdf.py         # 日报 / 周报 PDF 渲染
├── references/categories.md  # 反思 5 分类定义
├── assets/pdf-style.css      # 极简风 PDF 样式
└── data/                     # 占位目录（真实数据存在 skill 外部）
```

## 安装

把 `personal-os/` 放进 Claude Code 的 skills 目录：

```bash
git clone https://github.com/b-bzy/personal-os.git ~/.claude/skills/personal-os
```

PDF 渲染需要 weasyprint：

```bash
pip install weasyprint
```

其余脚本只用 Python 3 标准库（需要 3.9+，用到了 `zoneinfo`）。

## 数据存在哪

**真实数据不在这个仓库里。** 脚本按以下顺序定位总账文件：

1. 环境变量 `PG_TOTAL_LEDGER`（推荐显式设置）
2. `~/Desktop/工作报告/个人成长/犯错总账.md`
3. 都不存在时，回退到 skill 内部的 `data/mistakes.md`

```bash
export PG_TOTAL_LEDGER="$HOME/your/path/犯错总账.md"
```

仓库里的 `data/` 只有占位文件，不含任何真实记录。

## 定制

- **改分类**：[`references/categories.md`](references/categories.md)（5 分类的定义与归类优先级）
- **改样式**：[`assets/pdf-style.css`](assets/pdf-style.css)
- **改周次锚点 / 时区**：[`scripts/lib_dates.py`](scripts/lib_dates.py)
