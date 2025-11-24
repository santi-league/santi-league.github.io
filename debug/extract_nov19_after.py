#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取11月19日的所有对局（修改后）
"""

import re
import json

# 读取after HTML
with open('debug/m-league-after-changes.html', 'r', encoding='utf-8') as f:
    after_html = f.read()

# 提取gamesData
games_match = re.search(r'const gamesData\s*=\s*(\[.*?\]);', after_html, re.DOTALL)
if games_match:
    games = json.loads(games_match.group(1))

    print("修改后 - 2025年11月19日的所有对局:")
    print("="*80)

    nov19_games = [g for g in games if g['date'].startswith('2025年11月19日')]

    for i, game in enumerate(nov19_games, 1):
        print(f"\n对局 {i}: {game['date']}")
        print(f"平均R值: {game['table_avg_r']}")
        print("玩家信息:")
        for p in game['players']:
            marker = " ★" if p['name'] == 'santi' else ""
            print(f"  {p['rank']}. {p['name']}: {p['final_points']}点, R值变化: {p['r_change']:+.2f}{marker}")

    print(f"\n总计: {len(nov19_games)}场对局")
    print(f"包含santi的对局: {len([g for g in nov19_games if any(p['name']=='santi' for p in g['players'])])}场")
else:
    print("未找到gamesData")
