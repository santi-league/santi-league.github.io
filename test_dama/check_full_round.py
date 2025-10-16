# -*- coding: utf-8 -*-
"""检查完整的round数据结构"""

import json
import os

# 读取第一个默听和了
with open('test_dama/santi_dama_wins.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

first_win = data['wins'][0]
print(f"文件: {first_win['filename']}")
print(f"局索引: {first_win['round_idx']}")
print()

# 读取原始游戏数据
filepath = os.path.join('game-logs/m-league', first_win['filename'])
with open(filepath, 'r', encoding='utf-8') as f:
    game_data = json.load(f)

players = game_data['name']
player_idx = players.index('santi')

print(f'玩家: santi (索引 {player_idx})')
print(f'所有玩家: {players}')
print()

# 获取该局数据
round_data = game_data['log'][first_win['round_idx']]

print(f'round_data 结构:')
print(f'  元素数量: {len(round_data)}')
print()

for i, element in enumerate(round_data):
    if i == 0:
        print(f'[{i}] 局信息: {element}')
    elif i == 1:
        print(f'[{i}] 分数: {element}')
    elif i == 2:
        print(f'[{i}] 宝牌指示牌?: {element}')
    elif i == 3:
        print(f'[{i}] 里宝牌指示牌?: {element}')
    elif i >= 4 and i <= 7:
        print(f'[{i}] 玩家{i-4} ({players[i-4]}) 手牌历史:')
        player_moves = element
        print(f'     总共 {len(player_moves)} 个动作')
        # 打印所有动作
        for j, move in enumerate(player_moves):
            print(f'     [{j}] {move}')
    else:
        print(f'[{i}] {type(element).__name__}: {element}')

print()
print('=' * 80)
print('查找所有字符串类型的动作（可能是副露/立直标记）：')
for i in range(4, min(8, len(round_data))):
    player_moves = round_data[i]
    player_name = players[i-4]
    for j, move in enumerate(player_moves):
        if isinstance(move, str):
            print(f'  玩家{i-4} ({player_name}) 动作[{j}]: {move}')
