# -*- coding: utf-8 -*-
"""
批量统计：读取文件夹内所有 v2.3 牌谱 JSON，调用 summarize_v23.summarize_log，
并统计每位玩家参与的对局数（跨文件合并）。

用法：
  python batch_summarize_v23.py /path/to/folder
  # 递归子目录
  python batch_summarize_v23.py /path/to/folder --recursive
  # 指定文件模式（默认 *.json）
  python batch_summarize_v23.py /path/to/folder -p "*.paipu.json"
  # 输出到文件
  python batch_summarize_v23.py /path/to/folder -o result.json
"""

import os
import sys
import json
import glob
import argparse

try:
    from summarize_v23 import summarize_log  # ← 需与本脚本同目录，或在 PYTHONPATH 中
except ImportError as e:
    print("无法导入 summarize_v23.summarize_log，请确认 summarize_v23.py 与本脚本同目录。", file=sys.stderr)
    raise

def scan_files(folder: str, pattern: str, recursive: bool):
    if recursive:
        pattern_path = os.path.join(folder, "**", pattern)
        return [p for p in glob.glob(pattern_path, recursive=True) if os.path.isfile(p)]
    else:
        pattern_path = os.path.join(folder, pattern)
        return [p for p in glob.glob(pattern_path) if os.path.isfile(p)]

def main():
    ap = argparse.ArgumentParser(description="批量统计 v2.3 牌谱并汇总玩家出场局数")
    ap.add_argument("folder", help="包含牌谱 JSON 的文件夹路径")
    ap.add_argument("-p", "--pattern", default="*.json", help="文件匹配模式（默认 *.json）")
    ap.add_argument("-r", "--recursive", action="store_true", help="是否递归子目录")
    ap.add_argument("-o", "--output", default=None, help="输出结果到文件（不指定则打印到 stdout）")
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    files = scan_files(folder, args.pattern, args.recursive)

    results = []
    player_total_games = {}  # {player_name: count}
    errors = []

    for fp in sorted(files):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            summary = summarize_log(data)  # 调用你之前的程序
            # 记录文件路径
            summary_out = {
                "file": os.path.relpath(fp, folder),
                **summary
            }
            results.append(summary_out)

            # 汇总“每个玩家一共玩了多少局游戏”
            # 每个文件视为一局（东南西北四人），对出现过的名字各+1
            for name in set(summary.get("players", [])):
                player_total_games[name] = player_total_games.get(name, 0) + 1

        except Exception as ex:
            errors.append({"file": fp, "error": str(ex)})

    # 排序玩家统计（按局数降序）
    player_total_games_sorted = dict(
        sorted(player_total_games.items(), key=lambda kv: (-kv[1], kv[0]))
    )

    out = {
        "folder": folder,
        "files_processed": len(files),
        "files_succeeded": len(results),
        "files_failed": len(errors),
        "player_total_games": player_total_games_sorted,
        "results": results,
        "errors": errors,
    }

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已写入：{os.path.abspath(args.output)}")
    else:
        print(text)

if __name__ == "__main__":
    main()

