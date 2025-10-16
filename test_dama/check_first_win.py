# -*- coding: utf-8 -*-
"""检查第一条默听和了记录的详细数据"""

import json
import os

# 读取第一个默听和了
with open('test_dama/santi_dama_wins.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

first_win = data['wins'][0]
print('第一条记录：')
print(f"日期: {first_win['date']}")
print(f"局数: {first_win['round']}")
print(f"文件: {first_win['filename']}")
print(f"局索引: {first_win['round_idx']}")
print()

# 读取原始游戏数据
filepath = os.path.join('game-logs/m-league', first_win['filename'])
with open(filepath, 'r', encoding='utf-8') as f:
    game_data = json.load(f)

players = game_data['name']
player_idx = players.index('santi')

print(f'玩家索引: {player_idx}')
print(f'玩家列表: {players}')
print()

# 获取该局数据
round_data = game_data['log'][first_win['round_idx']]
player_moves = round_data[player_idx + 4]

print('santi的手牌历史:')
for i, move in enumerate(player_moves):
    print(f'{i}: {move}')

print()
print('检查副露标记:')
has_furo = []
for i, move in enumerate(player_moves):
    if isinstance(move, str) and (move.startswith('p') or move.startswith('c') or move.startswith('k')):
        has_furo.append((i, move))
        print(f'  位置 {i}: {move}')

if has_furo:
    print(f'\n✗ 这局有副露！找到 {len(has_furo)} 个副露标记')
else:
    print('\n✓ 这局没有副露标记')
