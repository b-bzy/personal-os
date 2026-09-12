#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_weekly.py · 读 mistakes.md，提取「本周」条目，做机械统计

字段：id / date / category / context / problem / experience

用法（按推荐顺序）：
    python analyze_weekly.py                       # 本周（默认 Dubai Week，以今天为准）
    python analyze_weekly.py --dubai-week 8        # DW8（推荐：跟 SKILL.md 0.3 节命名一致）
    python analyze_weekly.py --range 2026-05-11:2026-05-17
    python analyze_weekly.py --week 2026-W20       # 旧 ISO 周接口，保留只为向后兼容
    python analyze_weekly.py --json-out /tmp/snap.json

锚点：DW1 起点 = 2026-04-19（周日），每 7 天一周（周日 → 周六）。
"""

from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

# Dubai Week 工具来自 lib_dates（共享给 personal-os 所有脚本）
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from lib_dates import dubai_week_of, dubai_week_range


ROW_RE = re.compile(
    r"^\|\s*(?P<id>\d{8}-\d{3})\s*"
    r"\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*"
    r"\|\s*(?P<category>[a-z\-]+)\s*"
    r"\|\s*(?P<context>[^|]*?)\s*"
    r"\|\s*(?P<problem>[^|]*?)\s*"
    r"\|\s*(?P<experience>[^|]*?)\s*\|\s*$",
    re.M,
)

CATEGORIES = ["decision", "execution", "communication", "self-mgmt", "cognition"]


def find_default_mistakes_md() -> Path:
    """默认指向「工作报告/个人成长/犯错总账.md」（兼容真机和沙盒）。"""
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


def parse_all(path: Path) -> list[dict]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    rows = []
    for m in ROW_RE.finditer(content):
        d = m.groupdict()
        for k in ("context", "problem", "experience"):
            d[k] = d[k].replace("<br>", "\n")
        rows.append(d)
    return rows


def iso_week_range(year: int, week: int) -> tuple[date, date]:
    monday = datetime.fromisocalendar(year, week, 1).date()
    return monday, monday + timedelta(days=6)


def resolve_range(args) -> tuple[date, date, str]:
    # --dubai-week N (推荐)
    if args.dubai_week is not None:
        n = int(args.dubai_week)
        s, e = dubai_week_range(n)
        return s, e, f"DW{n}"
    # --range YYYY-MM-DD:YYYY-MM-DD
    if args.range:
        a, b = args.range.split(":")
        start = datetime.strptime(a, "%Y-%m-%d").date()
        end = datetime.strptime(b, "%Y-%m-%d").date()
        # 用 Dubai Week 作 label（基于 start 日期归属）
        return start, end, f"DW{dubai_week_of(start)}"
    # --week 2026-Wxx (旧 ISO 接口，保留兼容)
    if args.week:
        m = re.match(r"(\d{4})-W(\d{1,2})", args.week)
        if not m:
            raise SystemExit("--week 格式为 YYYY-Www，例如 2026-W20")
        y, w = int(m.group(1)), int(m.group(2))
        s, e = iso_week_range(y, w)
        return s, e, f"{y}-W{w:02d}"
    # 默认：今天所在的 Dubai Week
    today = date.today()
    n = dubai_week_of(today)
    s, e = dubai_week_range(n)
    return s, e, f"DW{n}"


def in_range(d_str: str, start: date, end: date) -> bool:
    try:
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    return start <= d <= end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dubai-week", type=int, help="推荐，例如 --dubai-week 8 取 DW8")
    ap.add_argument("--week", help="旧 ISO 周接口，例如 2026-W20；建议改用 --dubai-week")
    ap.add_argument("--range", help="例如 2026-05-11:2026-05-17；优先级高于 --week，但低于 --dubai-week")
    ap.add_argument("--data-file", default=str(find_default_mistakes_md()))
    ap.add_argument("--json-out", help="写入 JSON 路径；不指定则只打印到 stdout")
    args = ap.parse_args()

    start, end, label = resolve_range(args)
    rows = parse_all(Path(args.data_file))
    cur = [r for r in rows if in_range(r["date"], start, end)]
    by_cat = Counter(r["category"] for r in cur)

    snap = {
        "week": label,
        "date_range": [start.isoformat(), end.isoformat()],
        "total": len(cur),
        "by_category": {c: by_cat.get(c, 0) for c in CATEGORIES},
        "entries": cur,
    }
    out = json.dumps(snap, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(out, encoding="utf-8")
        print(json.dumps({"ok": True, "json": args.json_out, "label": label, "total": snap["total"]},
                         ensure_ascii=False))
    else:
        print(out)


if __name__ == "__main__":
    main()
