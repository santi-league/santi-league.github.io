#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确对比两个HTML文件中的对局，忽略日期格式差异
"""

import re
import json

# 读取两个HTML文件
with open('debug/m-league-before-changes.html', 'r', encoding='utf-8') as f:
    before_html = f.read()

with open('debug/m-league-after-changes.html', 'r', encoding='utf-8') as f:
    after_html = f.read()

def extract_all_games(html):
    """提取所有对局的完整信息"""
    # 找到gamesData变量
    games_match = re.search(r'const gamesData\s*=\s*(\[.*?\]);', html, re.DOTALL)
    if not games_match:
        print("未找到gamesData变量")
        return []

    games_str = games_match.group(1)

    # 尝试解析为JSON数组
    try:
        games = json.loads(games_str)
        return games
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        # 打印前1000个字符用于调试
        print(f"前1000字符: {games_str[:1000]}")
        return []

def normalize_game(game):
    """标准化对局信息，移除日期格式差异"""
    # 创建一个基于玩家信息的唯一标识
    players = game.get('players', [])

    # 按名字排序玩家（因为顺序可能不同）
    players_sorted = sorted(players, key=lambda p: p['name'])

    # 创建标识符：所有玩家的(名字,排名,分数)组合
    player_signature = tuple(
        (p['name'], p['rank'], p['final_points'])
        for p in players_sorted
    )

    # 提取日期（只保留年月日部分，忽略时间）
    date = game.get('date', '')
    # 移除时间部分，只保留日期
    date_only = re.sub(r'\s+\d+:\d+$', '', date)

    return {
        'date_only': date_only,
        'full_date': date,
        'player_signature': player_signature,
        'raw_game': game
    }

def find_santi_games(games):
    """找出包含santi的对局"""
    santi_games = []
    for game in games:
        players = game.get('players', [])
        for player in players:
            if player['name'] == 'santi':
                santi_games.append(game)
                break
    return santi_games

print('提取对局数据...')
before_games = extract_all_games(before_html)
after_games = extract_all_games(after_html)

print(f'修改前总对局数: {len(before_games)}')
print(f'修改后总对局数: {len(after_games)}')
print()

# 找出santi的对局
before_santi = find_santi_games(before_games)
after_santi = find_santi_games(after_games)

print(f'修改前santi对局数: {len(before_santi)}')
print(f'修改后santi对局数: {len(after_santi)}')
print()

# 标准化对局
before_normalized = [normalize_game(g) for g in before_santi]
after_normalized = [normalize_game(g) for g in after_santi]

# 创建签名集合
before_signatures = {g['player_signature']: g for g in before_normalized}
after_signatures = {g['player_signature']: g for g in after_normalized}

# 找出真正的差异
added_signatures = set(after_signatures.keys()) - set(before_signatures.keys())
removed_signatures = set(before_signatures.keys()) - set(after_signatures.keys())

print('='*80)
print('真正新增的santi对局:')
print('='*80)
if added_signatures:
    for sig in sorted(added_signatures, key=lambda s: after_signatures[s]['full_date'], reverse=True):
        game = after_signatures[sig]['raw_game']
        santi_player = [p for p in game['players'] if p['name'] == 'santi'][0]
        print(f"{game['date']}")
        print(f"  排名: 第{santi_player['rank']}名")
        print(f"  分数: {santi_player['final_points']}点")
        print(f"  R值变化: {santi_player.get('r_change', 'N/A')}")
        print(f"  玩家: {', '.join([p['name'] for p in game['players']])}")
        print()
else:
    print('无新增对局')
    print()

print('='*80)
print('真正删除的santi对局:')
print('='*80)
if removed_signatures:
    for sig in sorted(removed_signatures, key=lambda s: before_signatures[s]['full_date'], reverse=True):
        game = before_signatures[sig]['raw_game']
        santi_player = [p for p in game['players'] if p['name'] == 'santi'][0]
        print(f"{game['date']}")
        print(f"  排名: 第{santi_player['rank']}名")
        print(f"  分数: {santi_player['final_points']}点")
        print(f"  R值变化: {santi_player.get('r_change', 'N/A')}")
        print(f"  玩家: {', '.join([p['name'] for p in game['players']])}")
        print()
else:
    print('无删除对局')
    print()

# 分析R值变化的差异
print('='*80)
print('同一对局R值变化差异分析:')
print('='*80)
common_signatures = set(before_signatures.keys()) & set(after_signatures.keys())
r_value_changes = []

for sig in common_signatures:
    before_game = before_signatures[sig]['raw_game']
    after_game = after_signatures[sig]['raw_game']

    before_santi = [p for p in before_game['players'] if p['name'] == 'santi'][0]
    after_santi = [p for p in after_game['players'] if p['name'] == 'santi'][0]

    before_r = before_santi.get('r_change', 0)
    after_r = after_santi.get('r_change', 0)

    if abs(before_r - after_r) > 0.01:  # 有差异
        r_value_changes.append({
            'date': after_game['date'],
            'before_r': before_r,
            'after_r': after_r,
            'diff': after_r - before_r,
            'rank': after_santi['rank'],
            'points': after_santi['final_points']
        })

if r_value_changes:
    # 按日期排序
    r_value_changes.sort(key=lambda x: x['date'], reverse=True)

    print(f'发现 {len(r_value_changes)} 场对局的R值发生了变化:')
    print()

    total_diff = 0
    for change in r_value_changes[:20]:  # 显示前20个
        print(f"{change['date']}")
        print(f"  排名: 第{change['rank']}名, 分数: {change['points']}点")
        print(f"  修改前R值变化: {change['before_r']:+.1f}")
        print(f"  修改后R值变化: {change['after_r']:+.1f}")
        print(f"  差异: {change['diff']:+.1f}")
        print()
        total_diff += change['diff']

    if len(r_value_changes) > 20:
        print(f'... 还有 {len(r_value_changes) - 20} 场对局的R值也发生了变化')
        for change in r_value_changes[20:]:
            total_diff += change['diff']
        print()

    print(f'所有R值变化总和: {total_diff:+.1f}')
else:
    print('所有对局的R值都没有变化')
