#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
fillin.py
从 JSON 文件读取选手数据，写入 docs/players/<玩家名>.html 的关键指标位置。

支持的 JSON 字段：
- name           (str)     选手名
- totalKyoku     (int)     总局数
- points         (float)   总成绩（可正可负）
- rValue         (int)     R 值
- avgRank        (float)   平均顺位
- winRate        (float)   和了率（0~1）
- dealIn         (float)   放铳率（0~1）
- riichi         (float)   立直率（0~1）
- naki           (float)   副露率（0~1）
- rankDist       (list[float], len=4) 顺位分布(1~4位)，0~1

额外扩展：
- winIncome            (int|float) 每次和了平均得点（或周期总和，你来定义）
- dealInLoss           (int|float) 每次放铳平均失点
- ippatsu              (float)     一发率（0~1）
- dealInAfterRiichi    (float)     立直后放铳率（0~1）
- uradora              (float)     里宝平均（例如每次和了的平均里宝张数），保留 2 位小数

脚本会匹配并替换以下 HTML 元素 id：
- player-name, total-kyoku, avg-rank, win-rate, deal-in, riichi-rate, naki-rate,
  points-total, r-value, win-income, dealin-loss, ippatsu-rate, dealin-after-riichi, uradora-avg
以及“顺位分布”模块内的 4 条进度条与百分比（结构需与模板一致）。
"""

import argparse
import datetime as dt
import json
import re
from pathlib import Path
import shutil
import sys
from typing import List, Any

# ---------- 基础工具 ----------
def replace_inner_text_by_id(html: str, element_id: str, new_text: str) -> str:
    """
    将具有给定 id 的 HTML 元素的内部文本替换为 new_text。
    仅替换第一次出现。
    """
    pattern = re.compile(
        rf'(<[^>]*\bid="{re.escape(element_id)}"[^>]*>)(.*?)(</[^>]+>)',
        flags=re.DOTALL | re.IGNORECASE,
    )
    def _repl(m):
        return f"{m.group(1)}{new_text}{m.group(3)}"
    new_html, n = pattern.subn(_repl, html, count=1)
    if n == 0:
        print(f"[warn] 未找到 id=\"{element_id}\" 的元素，跳过。", file=sys.stderr)
    return new_html

def format_signed_number(x: float, digits: int = 0) -> str:
    """
    格式化带符号数字：千分位 + 固定小数位
    例：+1,240 / -6,400 / +1,234.5
    """
    sign = "+" if x >= 0 else "-"
    fmt = f"{{:,.{digits}f}}"
    return f"{sign}{fmt.format(abs(x))}"

def format_percent(p: float, digits: int = 1) -> str:
    """0.118 -> 11.8%"""
    return f"{p * 100:.{digits}f}%"

def update_last_updated_date(html: str) -> str:
    """把“最后更新：YYYY-MM-DD”替换为今天。"""
    today = dt.date.today().strftime("%Y-%m-%d")
    pattern = re.compile(r'最后更新：\d{4}-\d{2}-\d{2}')
    new_html, n = pattern.subn(r'最后更新：' + today, html, count=1)
    if n == 0:
        print("[info] 未找到“最后更新：YYYY-MM-DD”，跳过日期更新。", file=sys.stderr)
    return new_html

def update_rank_distribution(html: str, dist: List[float]) -> str:
    """
    dist: [p1,p2,p3,p4]，每项 0~1。
    更新“顺位分布”四条进度条 width 百分比与右侧数字。
    要求 HTML 结构顺序为 1位/2位/3位/4位，每条包含：
      <div class="fill" style="width:XX%"></div>
      <div class="pct">XX%</div>
    """
    if len(dist) != 4:
        print("[warn] rankDist 长度不是 4，忽略顺位分布更新。", file=sys.stderr)
        return html

    def replace_nth_fill_width(h: str, n_target: int, pct_str: str) -> str:
        patt = re.compile(r'(<div\s+class="fill"\s+style="width:)(\d+(?:\.\d+)?)%("\s*></div>)')
        count = 0
        def _repl(m):
            nonlocal count
            count += 1
            if count == n_target:
                return f'{m.group(1)}{pct_str}%{m.group(3)}'
            return m.group(0)
        return patt.sub(_repl, h, count=n_target)

    def replace_nth_pct_text(h: str, n_target: int, pct_str: str) -> str:
        patt = re.compile(r'(<div\s+class="pct">)(\d+(?:\.\d+)?)%(</div>)')
        count = 0
        def _repl(m):
            nonlocal count
            count += 1
            if count == n_target:
                return f"{m.group(1)}{pct_str}%{m.group(3)}"
            return m.group(0)
        return patt.sub(_repl, h, count=n_target)

    out = html
    for i, p in enumerate(dist, start=1):
        pct_str = f"{p * 100:.0f}"
        out = replace_nth_fill_width(out, i, pct_str)
        out = replace_nth_pct_text(out, i, pct_str)
    return out

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser(description="从 JSON 写入 docs/players/<玩家>.html 的关键数据")
    ap.add_argument("--data", required=True, help="JSON 数据文件路径，例如 ./data/dishu.json")
    ap.add_argument("--docs", default="docs", help="docs 根目录（默认 ./docs）")
    ap.add_argument("--player", default="地鼠", help="玩家文件名（不含扩展名），默认 地鼠")
    args = ap.parse_args()

    data_path = Path(args.data)
    docs_root = Path(args.docs)
    html_path = docs_root / "players" / f"{args.player}.html"

    if not data_path.exists():
        print(f"[error] 数据文件不存在：{data_path}", file=sys.stderr)
        sys.exit(1)
    if not html_path.exists():
        print(f"[error] HTML 文件不存在：{html_path}", file=sys.stderr)
        sys.exit(1)

    # 读 JSON
    with data_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    # 读 HTML
    html = html_path.read_text(encoding="utf-8")

    # 备份
    backup_path = html_path.with_suffix(".html.bak")
    shutil.copy2(html_path, backup_path)
    print(f"[info] 已备份原文件到：{backup_path}")

    # 便捷取值
    def get(k, default=None): return data.get(k, default)

    # 核心数值映射（确保你的 HTML 有对应 id）
    mappings: list[tuple[str, str | None]] = [
        ("player-name",   get("name")),
        ("total-kyoku",   f"{int(get('totalKyoku'))}" if get("totalKyoku") is not None else None),
        ("avg-rank",      f"{float(get('avgRank')):.2f}" if get("avgRank") is not None else None),

        # 百分比：0~1 -> 0~100%
        ("win-rate",      format_percent(float(get("winRate"))) if get("winRate") is not None else None),
        ("deal-in",       format_percent(float(get("dealIn")))  if get("dealIn")  is not None else None),
        ("riichi-rate",   format_percent(float(get("riichi")))  if get("riichi")  is not None else None),
        ("naki-rate",     format_percent(float(get("naki")))    if get("naki")    is not None else None),

        # 额外扩展
        ("points-total",  format_signed_number(float(get("points")), digits=1) if get("points") is not None else None),
        ("r-value",       f"{int(get('rValue'))}" if get("rValue") is not None else None),
        ("win-income",    format_signed_number(float(get("winIncome")), digits=0) if get("winIncome") is not None else None),
        ("dealin-loss",   format_signed_number(float(get("dealInLoss")), digits=0) if get("dealInLoss") is not None else None),
        ("ippatsu-rate",  format_percent(float(get("ippatsu"))) if get("ippatsu") is not None else None),
        ("dealin-after-riichi", format_percent(float(get("dealInAfterRiichi"))) if get("dealInAfterRiichi") is not None else None),
        ("uradora-avg",   f"{float(get('uradora')):.2f}" if get("uradora") is not None else None),
    ]

    #for element_id, text in mappings:
    #    if text is None:
    #        continue
    #    html = replace_inner_text_by_id(html, element_id, text)

    # 顺位分布
    #rd = get("rankDist")
    #if isinstance(rd, list):
    #    try:
    #        dist = [float(x) for x in rd]
    #        html = update_rank_distribution(html, dist)
    #    except Exception as e:
    #        print(f"[warn] 更新顺位分布失败：{e}", file=sys.stderr)

    # 更新“最后更新：YYYY-MM-DD”
    html = update_last_updated_date(html)

    # 写回
    html_path.write_text(html, encoding="utf-8")
    print(f"[ok] 已更新：{html_path}")

if __name__ == "__main__":
    main()
