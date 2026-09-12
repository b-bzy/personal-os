---
name: personal-os
description: 个人反思操作系统 skill。用户描述"今天做错了一件事 / 记一笔 / 这事我又干砸了"时，结构化入库到长期总账 犯错总账.md；用户说"出日报 / 今日复盘"时，生成当日反思日报 PDF；用户说"出周报 / 出反思周报 / 出复盘周报"时，按 Dubai Week 提取本周条目、找出反复犯错的通性，生成反思周报 PDF。哪怕用户没明说"用 personal-os skill"，只要场景是「日常错误记录 + 周期性反思复盘」，都用这个 skill。
---

# personal-os · 个人反思操作系统

> 把日常失误结构化沉淀成长期总账，再按日 / 周把它折叠成一份能看出模式的 PDF。

---

## § 零、日期与周次约定（**最高优先级 · 强制 4 步 · 不可绕过**）

> ⚠️ **这一节是硬性流程，不是建议。** Claude 在本 skill 的**任何**流程（入库 / 出日报 / 出周报 / 任何用到"今天"或"本周"的地方）开头，**必须依次跑完下面 4 步**。
>
> **跳过任何一步 = 违反本 skill 协议。**
> 哪怕用户上一句话刚说"今天是 X"、哪怕 `<env>` 顶部明显写着 Today's date、哪怕你"非常确定"——**都不能跳过 Step 0.1 的 bash 校验**。

### Step 0.1 · 现场采集今天的真实日期（bash，强制）

```bash
TZ='Asia/Dubai' date +"%Y-%m-%d %A"
```

把它存为本次流程的 `$TODAY` 和 `$DOW`。

**禁止做的事情**：
- ❌ 不跑 bash，直接读 `<env>` 顶部的 Today's date
- ❌ 引用对话历史里 `system-reminder: The date has changed. Today's date is now ...` 的旧值
- ❌ 凭"上次说今天是 X"做心算
- ❌ 把对话开头第一次校验的 `$TODAY` 一直缓存到对话结束

### Step 0.2 · 交叉校验

把 Step 0.1 输出和 `<env>` 顶部 Today's date 对比，不一致以 bash 为准并提示用户 env 已过期。

### Step 0.3 · 用 lib_dates 算 Dubai Week

```bash
python3 .../scripts/lib_dates.py
```

输出包含 `$DW`、`$DW_START`、`$DW_END`、`$DUBAI_DAY`。

锚点：DW1 = 2026-04-19（周日）；每 7 天一周（周日 → 周六）。

### Step 0.4 · 锁定本次流程的"时间快照"

完成 0.1-0.3 后，**把 `$TODAY` / `$DOW` / `$DW` / `$DW_START` / `$DW_END` 视为本次流程的"事实"，不再二次修改**。后续任何用到「今天 / 本周 / 这周 / 周报范围 / 入库默认日期」的地方都直接引用，不重新计算。

### 0.5 命名约定

- 周次：**Dubai Week**（`DW1` `DW2` ... `DW{N}`），不再用 ISO 周或月内周
- 周报 PDF：`周报/DW{N}-反思-周报.pdf`
- 日报 PDF：`日报/YYYY-MM-DD-反思日报.pdf`

### 0.6 用户给相对日期时的处理

| 用户说 | 处理 |
|---|---|
| "今天" / 没给日期 | 用 `$TODAY` |
| "昨天" | Python `timedelta(-1)` 算 |
| "上周" 出周报 | `$DW - 1` |
| "上上周" 出周报 | `$DW - 2` |
| "DW7" / "DW9 周报" | 直接用 7 / 9 |
| "0613" / "6/13" | 按用户原值 |

---

## § 一、触发词路由表（Claude 进来第一件事 = 看这表）

| 用户说 | 走哪个流程 | 调用脚本 |
|---|---|---|
| "记一笔" / "今天做错了" / 描述失误 | **A · 反思入库** | `scripts/append_entry.py` |
| "出日报" / "今日复盘" | **B · 反思日报** | `analyze_daily.py` + `render_pdf.py` |
| "出周报" / "出反思周报" / "出复盘周报" | **C · 反思周报** | `analyze_weekly.py` + `render_pdf.py` |

**模糊触发的处理**：用户描述既像入库又像出报告时，用 AskUserQuestion 二次确认。

---

## § 二、数据存储位置

```
~/Desktop/工作报告/个人成长/
├── 犯错总账.md              ← 全部反思条目（长期追加）
├── 日报/
│   └── YYYY-MM-DD-反思日报.pdf
└── 周报/
    └── DW{N}-反思-周报.pdf
```

实际路径按以下顺序解析：环境变量 `PG_TOTAL_LEDGER` > `~/Desktop/` 下的默认路径 > skill 内部 `data/`。

数据格式细节：反思条目 5 分类见 `references/categories.md`。

---

## § 三、主流程 A · 反思入库

### A1 · 识别输入形态
文字 / 截图 / PDF。图片用 `Read` 工具直接读，不要跑 OCR。

### A2 · 结构化抽取（4 用户字段 + 2 自动字段）

| 字段 | 来源 | 说明 |
|------|------|------|
| `date` | 用户 / `$TODAY` | YYYY-MM-DD |
| `context` | 用户 | 背景描述 |
| `problem` | 用户 | 问题清单 ① ② ③ |
| `experience` | 用户 | 经验清单 ① ② ③ |
| `id` | 脚本自动 | YYYYMMDD-NNN |
| `category` | Claude | 5 选 1（见 `references/categories.md`）|

### A2.5 · 润色（默认开启）
- ✅ 改错字病句、口语化→准确词、序号统一 ① ② ③、把两层意思拆开
- ❌ 不合并/拆分用户分点数、不增加用户没写的内容、不脑补根因

### A3 · 分类不明时 AskUserQuestion 二次确认
否则按 `cognition > self-mgmt > decision > communication > execution` 归类。

### A4 · 入库

```bash
python3 .../scripts/append_entry.py --json '<JSON>'
```

### A5 · 回执 + 既往展示 + 询问周报
1. 回执（含 id + 润色版）
2. `analyze_weekly.py --dubai-week $DW` 展示本周累计列表
3. AskUserQuestion 问是否出周报（出 / 不出）

---

## § 四、主流程 B · 反思日报

```bash
python3 .../scripts/analyze_daily.py --date $TODAY --json-out /tmp/snap_daily.json
# Claude 写 summary + actions（≤3 条，今晚/明天可验证）
python3 .../scripts/render_pdf.py --snapshot /tmp/snap_daily.json \
  --summary-md "..." --actions-md "1. xxx\n2. xxx" \
  --out "$HOME/Desktop/工作报告/个人成长/日报/$TODAY-反思日报.pdf"
```

snapshot 里 `report_type: "daily"` 让 `render_pdf.py` 自动切日报排版。

---

## § 五、主流程 C · 反思周报

```bash
python3 .../scripts/analyze_weekly.py --dubai-week $DW --json-out /tmp/ref_snap.json
# Claude 写 summary + actions
python3 .../scripts/render_pdf.py --snapshot /tmp/ref_snap.json \
  --summary-md "..." --actions-md "1. xxx\n2. xxx" \
  --out "$HOME/Desktop/工作报告/个人成长/周报/DW${DW}-反思-周报.pdf"
```

范围默认 `$DW`，"上周"用 `$DW-1`。

**总评要点**：找首要主题、不带情绪不喊鸡汤；**明确区分"实际失误"vs"方法吸收"**——这是反思板块特有信号。

**行动要点**：≤3 条，每条必须「一周内能验证做没做到」。

---

## § 六、关键约束

1. **§ 零节是硬规则**，所有流程开头都必须跑 4 步。
2. **不脑补**：用户没写的根因、没给的数据，一律不补。缺失就留空。
