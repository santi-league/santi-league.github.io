#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""比较两种R值计算的差异"""

import json
from generate_website import extract_recent_games, sort_files_by_date
from player_stats import calculate_player_stats, scan_files
from summarize_v23 import summarize_log

# 扫描 M-League 文件
m_league_folder = "game-logs/m-league"
files = scan_files(m_league_folder, "*.json", recursive=True)

# 使用日期排序而不是字符串排序
sorted_files = sort_files_by_date(files)

# 处理文件
results = []
round_counts = []
for fp in sorted_files:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        summary = summarize_log(data)
        results.append(summary)
        round_counts.append(len(data.get("log", [])))
    except Exception as ex:
        pass

print("="*80)
print("比较两种R值计算方法")
print("="*80)

# 方法1: extract_recent_games 计算的R值
recent_games = extract_recent_games(sorted_files, results, count=1)
if recent_games:
    print("\n【方法1】extract_recent_games 计算的最新一场R值:")
    print(f"日期: {recent_games[0]['date']}")
    for p in recent_games[0]['players_detail']:
        print(f"  {p['name']}: 局后R = {p['r_after']}")

# 方法2: calculate_player_stats 计算的R值
stats = calculate_player_stats(results, round_counts)
print("\n【方法2】calculate_player_stats 计算的当前R值:")
for name, data in sorted(stats.items(), key=lambda x: x[0]):
    if name == '_league_average':
        continue
    if name in ['santi', 'RinshanNomi', '小地鼠爱点炮', 'Samuel122']:
        print(f"  {name}: R = {data['tenhou_r']}")

print("\n分析:")
print("如果两个方法的R值不同，可能的原因:")
print("1. 文件处理顺序不同")
print("2. 某些游戏被跳过或处理方式不同")
print("="*80)
