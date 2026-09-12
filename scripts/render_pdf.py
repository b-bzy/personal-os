#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_pdf.py · 读 snapshot JSON + Claude 写的总评/建议，生成 PDF 复盘报告。

字段：id / date / category / context / problem / experience

snapshot 里若带 `report_type: "daily"` 则按日报排版；否则按周报排版（默认）。

用法：
    python render_pdf.py \
        --snapshot /tmp/snap.json \
        --summary-md "本周……" \
        --actions-md "1. xxx\n2. xxx" \
        --out report.pdf

依赖：weasyprint
"""

from __future__ import annotations
import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path

CATEGORY_ZH = {
    "decision": "决策判断",
    "execution": "执行落地",
    "communication": "沟通协作",
    "self-mgmt": "自我管理",
    "cognition": "认知盲区",
}
_LIST_PREFIX_RE = re.compile(r"^(?:\d+[.)、]|[-—·*])\s*")

# 按 report_type 切换文案。weekly 是默认（向后兼容）。
LABELS = {
    "weekly": {
        "title_suffix": "周复盘",
        "section_overview": "本周概览",
        "section_distribution": "分类分布",
        "section_entries": "本周条目",
        "section_actions": "下周可执行建议",
        "stat_card_total_label": "本周记录",
        "stat_card_top_label": "最高频分类",
        "stat_card_touched_label": "触及分类",
        "category_table_header": "本周",
        "empty_note": "本周暂无记录。",
        "summary_empty": "（本周未生成总评）",
        "actions_empty": "下周无具体建议。",
    },
    "daily": {
        "title_suffix": "日报",
        "section_overview": "今日概览",
        "section_distribution": "分类分布",
        "section_entries": "今日条目",
        "section_actions": "明日可执行建议",
        "stat_card_total_label": "今日记录",
        "stat_card_top_label": "最高频分类",
        "stat_card_touched_label": "触及分类",
        "category_table_header": "今日",
        "empty_note": "今日暂无记录。",
        "summary_empty": "（今日未生成总评）",
        "actions_empty": "明日无具体建议。",
    },
}


def _labels_for(snap: dict) -> dict:
    return LABELS.get(snap.get("report_type", "weekly"), LABELS["weekly"])


def find_default_css() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "pdf-style.css"


def render_stat_row(snap: dict) -> str:
    L = _labels_for(snap)
    total = snap["total"]
    by_cat = snap["by_category"]
    if total == 0:
        top_label, top_pct = "—", "—"
    else:
        top_cat = max(by_cat, key=by_cat.get)
        top_label = CATEGORY_ZH[top_cat]
        top_pct = f"{by_cat[top_cat] / total * 100:.0f}%"
    n_cats = sum(1 for v in by_cat.values() if v > 0)
    return f"""
    <div class="stat-row">
      <div class="stat-card">
        <div class="label">{L['stat_card_total_label']}</div>
        <div class="value">{total}</div>
        <div class="sub">条</div>
      </div>
      <div class="stat-card">
        <div class="label">{L['stat_card_top_label']}</div>
        <div class="value" style="font-size:14pt">{top_label}</div>
        <div class="sub">占比 {top_pct}</div>
      </div>
      <div class="stat-card">
        <div class="label">{L['stat_card_touched_label']}</div>
        <div class="value">{n_cats}</div>
        <div class="sub">/ 5 类</div>
      </div>
    </div>
    """


def render_category_table(snap: dict) -> str:
    L = _labels_for(snap)
    by_cat = snap["by_category"]
    is_daily = snap.get("report_type", "weekly") == "daily"
    rows = []
    for c, zh in CATEGORY_ZH.items():
        n = by_cat.get(c, 0)
        # 日报：跳过 0 行，避免大量空行
        if is_daily and n == 0:
            continue
        rows.append(f"<tr><td>{zh}</td><td class='num'>{n}</td></tr>")
    if not rows:
        return ""
    return f"""
    <table class="category">
      <thead><tr><th>分类</th><th class='num'>{L['category_table_header']}</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def _format_multiline(text: str) -> str:
    """把含 ① ② ③ 或换行的文本格式化成 HTML（每条换行）。"""
    if not text:
        return "—"
    text = html.escape(text)
    # 把 \n 换成 <br>
    text = text.replace("\n", "<br>")
    # 让 ① ② ③ ④ 之前自动换行（如果它不在开头）
    text = re.sub(r"(?<!^)(?<!<br>)([①-⑳])", r"<br>\1", text)
    return text


def render_entries(snap: dict) -> str:
    L = _labels_for(snap)
    entries = snap.get("entries", [])
    if not entries:
        return f'<div class="empty-note">{L["empty_note"]}</div>'

    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORY_ZH}
    for e in entries:
        by_cat.setdefault(e["category"], []).append(e)

    out = []
    for cat, zh in CATEGORY_ZH.items():
        items = by_cat.get(cat, [])
        if not items:
            continue
        out.append(f"<h3>{zh}（{len(items)} 条）</h3>")
        for e in items:
            meta = f"{e['id']} · {zh} · {e['date']}"
            ctx_html = _format_multiline(e.get("context", ""))
            prob_html = _format_multiline(e.get("problem", ""))
            exp_html = _format_multiline(e.get("experience", ""))
            out.append(f"""
            <div class="entry medium">
              <div class="meta">{html.escape(meta)}</div>
              <div class="field"><b>背景</b>{ctx_html}</div>
              <div class="field"><b>问题</b>{prob_html}</div>
              <div class="field"><b>经验</b>{exp_html}</div>
            </div>
            """)
    return "\n".join(out)


def md_lines_to_ol(actions_md: str, snap: dict | None = None) -> str:
    L = _labels_for(snap) if snap is not None else LABELS["weekly"]
    txt = actions_md.replace("\\n", "\n")
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    items = []
    for ln in lines:
        cleaned = _LIST_PREFIX_RE.sub("", ln, count=1).strip()
        if cleaned:
            items.append(f"<li>{html.escape(cleaned)}</li>")
    if not items:
        return f'<div class="empty-note">{L["actions_empty"]}</div>'
    return f"<ol class='actions'>{''.join(items)}</ol>"


def build_html(snap: dict, summary_md: str, actions_md: str, css_path: Path) -> str:
    L = _labels_for(snap)
    week = snap["week"]
    s, e = snap["date_range"]
    title = f"个人成长 · {week} {L['title_suffix']}"
    if snap.get("report_type", "weekly") == "daily":
        # 日报：标题已有日期，副标题不再重复
        subtitle = f"记录 {snap['total']} 条　·　生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    else:
        subtitle = f"{s} → {e}　·　共记录 {snap['total']} 条　·　生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    css_text = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    summary_html = html.escape(summary_md) if summary_md else L["summary_empty"]
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{css_text}</style></head>
<body>
<h1>{html.escape(title)}</h1>
<div class="subtitle">{html.escape(subtitle)}</div>

<h2>{L['section_overview']}</h2>
{render_stat_row(snap)}
<div class="summary">{summary_html}</div>

<h2>{L['section_distribution']}</h2>
{render_category_table(snap)}

<h2>{L['section_entries']}</h2>
{render_entries(snap)}

<h2>{L['section_actions']}</h2>
{md_lines_to_ol(actions_md, snap)}

</body></html>
"""


def to_pdf(html_str: str, out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from weasyprint import HTML  # type: ignore
        HTML(string=html_str).write_pdf(str(out_path))
        return "weasyprint"
    except ImportError:
        pass
    tmp_html = out_path.with_suffix(".html")
    tmp_html.write_text(html_str, encoding="utf-8")
    raise SystemExit(f"[render_pdf] 缺少 weasyprint。已写出 HTML 到 {tmp_html}，请安装：pip install weasyprint --break-system-packages")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--summary-md", default="")
    ap.add_argument("--actions-md", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--css", default=str(find_default_css()))
    args = ap.parse_args()

    snap = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    html_str = build_html(snap, args.summary_md, args.actions_md, Path(args.css))
    backend = to_pdf(html_str, Path(args.out))
    print(json.dumps({"ok": True, "out": args.out, "backend": backend}, ensure_ascii=False))


if __name__ == "__main__":
    main()
