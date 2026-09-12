#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lib_dates.py · personal-os 共用日期 / Dubai Week 工具库

锚点：DW1 第 1 天 = 2026-04-19（周日 · 用户抵达迪拜起算）
周边界：周日 → 周六
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# ===== 锚点 =====
ANCHOR = date(2026, 4, 19)       # DW1 day 1
USER_TZ = "Asia/Dubai"           # 用户时区


# ===== "今天" =====
def today() -> date:
    """以用户时区为准取今天日期。

    禁止用 `date.today()`——那个走的是沙盒 locale（UTC），跨日界会偏 1 天。
    """
    return datetime.now(ZoneInfo(USER_TZ)).date()


# ===== Dubai Week =====
def dubai_week_of(d: date) -> int:
    """给定日期 d，返回它属于第几个 Dubai Week（1, 2, ...）。"""
    return (d - ANCHOR).days // 7 + 1


def dubai_week_range(n: int) -> tuple[date, date]:
    """给定 Dubai Week 编号 n，返回 (start, end) 日期范围（周日 → 周六）。"""
    start = ANCHOR + timedelta(days=(n - 1) * 7)
    return start, start + timedelta(days=6)


def dubai_day_of(d: date) -> int:
    """给定日期 d，返回它是迪拜第几天（1-based，4/19 = day 1）。"""
    return (d - ANCHOR).days + 1


# ===== 月份 / 月度 =====
def month_of(d: date) -> str:
    """格式化为 YYYY-MM。"""
    return d.strftime("%Y-%m")


def dubai_weeks_in_month(year: int, month: int) -> list[int]:
    """给定年月，返回该月覆盖的 Dubai Week 编号列表。

    一个月通常覆盖 4-5 个 DW。
    """
    from calendar import monthrange
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return list(range(dubai_week_of(first), dubai_week_of(last) + 1))


# ===== CLI 自检（直接跑这个脚本看输出）=====
if __name__ == "__main__":
    import sys, json
    t = today()
    dw = dubai_week_of(t)
    s, e = dubai_week_range(dw)
    info = {
        "today": t.isoformat(),
        "dow": t.strftime("%A"),
        "dubai_day": dubai_day_of(t),
        "dubai_week": dw,
        "dw_range": [s.isoformat(), e.isoformat()],
        "tz": USER_TZ,
        "anchor": ANCHOR.isoformat(),
    }
    if "--json" in sys.argv:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(f"今天      : {info['today']} {info['dow']}")
        print(f"迪拜第   : day {info['dubai_day']}")
        print(f"本周     : DW{dw} ({s} → {e})")
