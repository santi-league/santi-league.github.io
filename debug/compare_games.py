#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比两个HTML文件中的对局差异
"""

import re
from collections import Counter

# 读取两个HTML文件
with open('debug/m-league-before-changes.html', 'r', encoding='utf-8') as f:
    before_html = f.read()

with open('debug/m-league-after-changes.html', 'r', encoding='utf-8') as f:
    after_html = f.read()

# 提取所有对局的日期和时间
def extract_game_info(html):
    # 匹配 "date": "YYYY年MM月DD日 HH:MM" 或 "YYYY年MM月DD日"
    matches = re.findall(r'"date":\s*"([^"]+)"', html)
    return matches

before_games = extract_game_info(before_html)
after_games = extract_game_info(after_html)

print(f'修改前总对局数: {len(before_games)}')
print(f'修改后总对局数: {len(after_games)}')
print(f'差异: {len(after_games) - len(before_games)}')
print()

# 统计出现次数
before_counter = Counter(before_games)
after_counter = Counter(after_games)

# 找出差异
print('='*80)
print('日期/时间出现次数差异:')
print('='*80)
all_dates = sorted(set(before_games) | set(after_games), reverse=True)

differences = []
for date in all_dates[:30]:  # 只看最近30个
    before_count = before_counter.get(date, 0)
    after_count = after_counter.get(date, 0)
    if before_count != after_count:
        differences.append((date, before_count, after_count, after_count - before_count))

if differences:
    for date, before_count, after_count, diff in differences:
        print(f'{date}:')
        print(f'  修改前: {before_count}场')
        print(f'  修改后: {after_count}场')
        print(f'  差异: {diff:+d}')
        print()
else:
    print('前30个日期中没有发现差异')

# 专门查找包含santi的对局
print('='*80)
print('包含santi的对局分析:')
print('='*80)

def extract_santi_games_detail(html):
    """提取包含santi的对局详细信息"""
    # 找到所有对局数据块
    pattern = r'\{"date":\s*"([^"]+)".*?"players":\s*\[([^\]]+)\]'
    matches = re.findall(pattern, html)

    santi_games = []
    for date, players_str in matches:
        if 'santi' in players_str:
            # 提取santi的排名和分数
            # 查找 "name": "santi", "rank": X
            santi_match = re.search(r'"name":\s*"santi",\s*"rank":\s*(\d+)', players_str)
            if santi_match:
                rank = int(santi_match.group(1))
                # 查找final_points
                points_match = re.search(r'"name":\s*"santi".*?"final_points":\s*(-?\d+)', players_str)
                points = int(points_match.group(1)) if points_match else None
                santi_games.append((date, rank, points))

    return santi_games

before_santi = extract_santi_games_detail(before_html)
after_santi = extract_santi_games_detail(after_html)

print(f'修改前santi对局数: {len(before_santi)}')
print(f'修改后santi对局数: {len(after_santi)}')
print(f'差异: {len(after_santi) - len(before_santi)}')
print()

# 找出新增/删除的对局
before_dates = {g[0] for g in before_santi}
after_dates = {g[0] for g in after_santi}

added = after_dates - before_dates
removed = before_dates - after_dates

if added:
    print('新增的santi对局:')
    for date in sorted(added, reverse=True):
        game = [g for g in after_santi if g[0] == date][0]
        print(f'  {date}: 第{game[1]}名, {game[2]}点')

if removed:
    print('\n删除的santi对局:')
    for date in sorted(removed, reverse=True):
        game = [g for g in before_santi if g[0] == date][0]
        print(f'  {date}: 第{game[1]}名, {game[2]}点')
