#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_daily.py · 读 mistakes.md，提取「指定那一天」的条目，做机械统计

字段：id / date / category / context / problem / experience

用法：
    python analyze_daily.py                          # 今天
    python analyze_daily.py --date 2026-06-02
    python analyze_daily.py --json-out /tmp/snap.json

输出 snapshot 与 analyze_weekly.py 结构兼容，并多一个 `report_type: "daily"` 字段，
render_pdf.py 据此切换日报排版。
"""

from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

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


def resolve_date(args) -> date:
    if args.date:
        return datetime.strptime(args.date, "%Y-%m-%d").date()
    return date.today()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="例如 2026-06-02；默认今天")
    ap.add_argument("--data-file", default=str(find_default_mistakes_md()))
    ap.add_argument("--json-out", help="写入 JSON 路径；不指定则只打印到 stdout")
    args = ap.parse_args()

    target = resolve_date(args)
    target_str = target.isoformat()
    rows = parse_all(Path(args.data_file))
    cur = [r for r in rows if r["date"] == target_str]
    by_cat = Counter(r["category"] for r in cur)

    snap = {
        "report_type": "daily",
        "week": target_str,            # 复用 week 字段位置存放日期标签
        "date_range": [target_str, target_str],
        "total": len(cur),
        "by_category": {c: by_cat.get(c, 0) for c in CATEGORIES},
        "entries": cur,
    }
    out = json.dumps(snap, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(out, encoding="utf-8")
        print(json.dumps({"ok": True, "json": args.json_out, "date": target_str, "total": snap["total"]},
                         ensure_ascii=False))
    else:
        print(out)


if __name__ == "__main__":
    main()
