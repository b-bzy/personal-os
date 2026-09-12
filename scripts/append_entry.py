#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
append_entry.py · 把一条犯错记录追加到 data/mistakes.md

新字段（4 个用户字段 + 2 个自动字段）：
    用户填：date / context / problem / experience
    自动填：id（脚本生成）/ category（Claude 判后传入）

用法：
    python append_entry.py --json '{
      "date": "2026-05-13",
      "category": "cognition",
      "context": "今天叫拿 10 个阿联酋号码……",
      "problem": "①没问 10 的来源……②……",
      "experience": "①量化任务问数值依据……②……"
    }'

总账位置默认：脚本所在 skill 的 data/mistakes.md。可用 --data-file 覆盖。
"""

from __future__ import annotations
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

CATEGORIES = {"decision", "execution", "communication", "self-mgmt", "cognition"}

TABLE_HEADER_RE = re.compile(r"^\|\s*id\s*\|", re.M)


def escape_cell(s) -> str:
    """表格单元格的危险字符转义。"""
    if s is None:
        return ""
    s = str(s)
    return s.replace("|", "｜").replace("\r\n", "\n").replace("\n", "<br>").strip()


def next_id(content: str, date: str) -> str:
    day_key = date.replace("-", "")
    pattern = re.compile(rf"^\|\s*({day_key})-(\d{{3}})\s*\|", re.M)
    nums = [int(m.group(2)) for m in pattern.finditer(content)]
    seq = (max(nums) + 1) if nums else 1
    return f"{day_key}-{seq:03d}"


def find_default_mistakes_md() -> Path:
    """默认指向「工作报告/个人成长/犯错总账.md」。
    检测顺序：环境变量 PG_TOTAL_LEDGER > 用户真机路径 > 沙盒路径 > skill 内部 data/"""
    import os
    env = os.environ.get("PG_TOTAL_LEDGER")
    if env:
        return Path(env)
    candidates = [
        Path.home() / "Desktop/工作报告/个人成长/犯错总账.md",
        Path("/sessions/brave-dreamy-meitner/mnt/工作报告/个人成长/犯错总账.md"),
    ]
    for p in candidates:
        if p.parent.exists() or p.parent.parent.exists():
            return p
    return Path(__file__).resolve().parent.parent / "data" / "mistakes.md"


def ensure_initialized(path: Path) -> None:
    """若 mistakes.md 不存在或缺骨架，初始化它。"""
    if path.exists() and TABLE_HEADER_RE.search(path.read_text(encoding="utf-8")):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    template = (
        "# 个人成长 · 犯错总账\n\n"
        "> 这份文档由 personal-os skill 自动维护。每条犯错都会追加到下方表格。\n"
        ">\n"
        "> **不要**手动删除/重排已有行（会破坏 id 顺序和周报统计）。\n"
        "> 修改某条：直接改这一行的字段即可。\n"
        "> 想补一条历史犯错：在末尾追加，`date` 字段写真实发生日期即可。\n\n"
        "| id | date | category | context | problem | experience |\n"
        "|----|------|----------|---------|---------|------------|\n"
    )
    path.write_text(template, encoding="utf-8")


def append_row(path: Path, row: dict) -> str:
    ensure_initialized(path)
    content = path.read_text(encoding="utf-8")

    row_id = row.get("id") or next_id(content, row["date"])
    row["id"] = row_id

    cells = [
        row_id,
        row["date"],
        row["category"],
        escape_cell(row["context"]),
        escape_cell(row["problem"]),
        escape_cell(row["experience"]),
    ]
    new_line = "| " + " | ".join(cells) + " |\n"
    content = content.rstrip("\n") + "\n" + new_line
    path.write_text(content, encoding="utf-8")
    return row_id


def validate(row: dict) -> None:
    for k in ("date", "category", "context", "problem", "experience"):
        if not row.get(k):
            raise SystemExit(f"[append_entry] 缺必填字段: {k}")
    if row["category"] not in CATEGORIES:
        raise SystemExit(f"[append_entry] category 必须是 {sorted(CATEGORIES)}, 收到: {row['category']}")
    try:
        datetime.strptime(row["date"], "%Y-%m-%d")
    except ValueError:
        raise SystemExit(f"[append_entry] date 必须是 YYYY-MM-DD, 收到: {row['date']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=False, help='JSON 字符串，键为字段名')
    ap.add_argument("--date")
    ap.add_argument("--category", choices=sorted(CATEGORIES))
    ap.add_argument("--context")
    ap.add_argument("--problem")
    ap.add_argument("--experience")
    ap.add_argument("--data-file", default=str(find_default_mistakes_md()))
    args = ap.parse_args()

    if args.json:
        row = json.loads(args.json)
    else:
        row = {
            "date": args.date,
            "category": args.category,
            "context": args.context,
            "problem": args.problem,
            "experience": args.experience,
        }

    validate(row)
    path = Path(args.data_file)
    row_id = append_row(path, row)
    print(json.dumps({"ok": True, "id": row_id, "path": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
