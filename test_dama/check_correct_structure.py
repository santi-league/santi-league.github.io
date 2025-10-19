# -*- coding: utf-8 -*-
"""
使用正确的数据结构检查第一条记录

数据结构：
- [0] 局信息
- [1] 分数
- [2] 宝牌指示牌
- [3] 里宝牌指示牌
- [4-6] 玩家0的三个列表
- [7-9] 玩家1的三个列表
- [10-12] 玩家2的三个列表
- [13-15] 玩家3的三个列表
- [16+] 和了信息等
"""

import json
import os

# 读取第一个默听和了
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

with open(os.path.join(script_dir, 'santi_dama_wins.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

first_win = data['wins'][0]
print(f"文件: {first_win['filename']}")
print(f"局索引: {first_win['round_idx']}")
print()

# 读取原始游戏数据
filepath = os.path.join(project_dir, 'game-logs/m-league', first_win['filename'])
with open(filepath, 'r', encoding='utf-8') as f:
    game_data = json.load(f)

players = game_data['name']
player_idx = players.index('santi')

print(f'玩家: santi (索引 {player_idx})')
print(f'所有玩家: {players}')
print()

# 获取该局数据
round_data = game_data['log'][first_win['round_idx']]

# 使用正确的数据结构：每个玩家占3个列表
META_COUNT = 4  # [0-3] 是元数据
PLAYER_BLOCK_SIZE = 3  # 每个玩家3个列表

# 计算santi的数据范围
player_start_idx = META_COUNT + player_idx * PLAYER_BLOCK_SIZE
player_list_0 = round_data[player_start_idx] if player_start_idx < len(round_data) else []
player_list_1 = round_data[player_start_idx + 1] if player_start_idx + 1 < len(round_data) else []
player_list_2 = round_data[player_start_idx + 2] if player_start_idx + 2 < len(round_data) else []

print(f'santi的数据索引范围: [{player_start_idx}, {player_start_idx+2}]')
print()

print(f'列表0 (初始手牌): {player_list_0}')
print(f'列表1 (打牌动作1): {player_list_1}')
print(f'列表2 (打牌动作2): {player_list_2}')
print()

# 检查所有三个列表中的副露和立直标记
print('检查副露和立直标记:')
all_lists = [player_list_0, player_list_1, player_list_2]
has_furo = False
has_riichi = False

for list_idx, player_list in enumerate(all_lists):
    for item_idx, item in enumerate(player_list):
        if isinstance(item, str):
            # 检查副露标记
            if any(c in item for c in ['c', 'p', 'k', 'm']) and any(d.isdigit() for d in item):
                print(f'  列表{list_idx}[{item_idx}]: {item} <- 副露标记')
                has_furo = True
            # 检查立直标记
            if item.startswith('r'):
                print(f'  列表{list_idx}[{item_idx}]: {item} <- 立直标记')
                has_riichi = True

print()
if has_furo:
    print('✗ 这局有副露！不应该被判断为默听')
elif has_riichi:
    print('✗ 这局有立直！不应该被判断为默听')
else:
    print('✓ 这局没有副露也没有立直，可能是默听')
