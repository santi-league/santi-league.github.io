# -*- coding: utf-8 -*-
"""
提取指定玩家的所有默听和了小局，生成天凤回放链接

用法：
  python test_dama/extract_dama_wins.py
"""

import os
import sys
import json
import copy

# 添加父目录到路径以导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extract_honor_games import convert_round_to_tenhou, HAND_DICT, YAKU_DICT

def parse_round_name(round_info):
    """解析局数信息"""
    ba_ju, honba, riichi_sticks = round_info

    # 0=东1, 1=东2, 2=东3, 3=东4, 4=南1, 5=南2, 6=南3, 7=南4
    ba_names = ['东一', '东二', '东三', '东四', '南一', '南二', '南三', '南四']
    round_name = ba_names[ba_ju] if ba_ju < len(ba_names) else f'局{ba_ju}'

    if honba > 0:
        return f'{round_name}局{honba}本场'
    else:
        return f'{round_name}局'

def extract_date_from_filename(filename):
    """从文件名提取日期"""
    import re
    from datetime import datetime

    match = re.match(r'(\d+)_(\d+)_(\d+)', filename)
    if match:
        month, day, year = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%Y年%m月%d日")
        except ValueError:
            return filename
    return filename

def generate_tenhou_url(round_data, game_data):
    """生成天凤牌谱再生URL"""
    # 转换为天凤格式
    tenhou_data = convert_round_to_tenhou(round_data, game_data)
    # 生成URL
    json_str = json.dumps(tenhou_data, ensure_ascii=False, separators=(',', ':'))
    return f"https://tenhou.net/5/#json={json_str}"

def is_dama_win(round_data, player_idx):
    """判断是否是默听和了"""
    # 检查最后一个元素是否是和了
    if not isinstance(round_data[-1], list) or len(round_data[-1]) < 3:
        return False

    if round_data[-1][0] != '和了':
        return False

    win_info = round_data[-1][2]
    if len(win_info) < 1 or win_info[0] != player_idx:
        return False

    # 检查玩家的手牌历史，判断是否有立直或副露
    player_hands = round_data[player_idx + 4]

    # 检查是否有立直标记 (r开头)
    has_riichi = any(isinstance(move, str) and move.startswith('r') for move in player_hands)

    # 检查是否有副露 (p开头或其他副露标记)
    has_furo = any(isinstance(move, str) and (move.startswith('p') or move.startswith('c') or move.startswith('k')) for move in player_hands)

    # 默听 = 没有立直 且 没有副露
    return not has_riichi and not has_furo

def extract_dama_wins_for_player(folder, player_name):
    """提取指定玩家的所有默听和了"""
    dama_wins = []

    # 扫描所有JSON文件
    files = []
    for root, dirs, filenames in os.walk(folder):
        for filename in filenames:
            if filename.endswith('.json'):
                files.append(os.path.join(root, filename))

    print(f"正在扫描 {len(files)} 个文件，查找 {player_name} 的默听和了...", file=sys.stderr)

    for filepath in sorted(files):
        filename = os.path.basename(filepath)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
        except Exception as e:
            print(f"读取文件失败: {filepath} - {e}", file=sys.stderr)
            continue

        players = game_data.get('name', [])

        # 检查玩家是否在这场游戏中
        if player_name not in players:
            continue

        player_idx = players.index(player_name)
        date_str = extract_date_from_filename(filename)

        for round_idx, round_data in enumerate(game_data['log']):
            if is_dama_win(round_data, player_idx):
                # 获取局数信息
                round_info = round_data[0]
                round_name = parse_round_name(round_info)

                # 获取和了信息
                win_info = round_data[-1][2]
                point_desc = win_info[3] if len(win_info) > 3 else ''
                yaku_list = win_info[4:] if len(win_info) > 4 else []
                yaku_str = ', '.join(yaku_list)

                # 生成天凤URL
                round_data_copy = copy.deepcopy(round_data)
                tenhou_url = generate_tenhou_url(round_data_copy, game_data)

                dama_win = {
                    'date': date_str,
                    'filename': filename,
                    'round': round_name,
                    'round_idx': round_idx,
                    'point_desc': point_desc,
                    'yaku': yaku_str,
                    'yaku_list': yaku_list,
                    'tenhou_url': tenhou_url,
                    'other_players': [p for i, p in enumerate(players) if i != player_idx]
                }

                dama_wins.append(dama_win)
                print(f"✓ {date_str} {round_name} - {point_desc}", file=sys.stderr)

    return dama_wins

def main():
    folder = "game-logs/m-league"
    player_name = "santi"

    dama_wins = extract_dama_wins_for_player(folder, player_name)

    print(f"\n找到 {player_name} 的 {len(dama_wins)} 个默听和了", file=sys.stderr)

    # 输出到文本文件
    output_file = "test_dama/santi_dama_wins.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"{player_name} 的默听和了小局列表\n")
        f.write("=" * 80 + "\n\n")

        for i, win in enumerate(dama_wins, 1):
            f.write(f"【{i}】{win['date']} {win['round']}\n")
            f.write(f"得分: {win['point_desc']}\n")
            f.write(f"役种: {win['yaku']}\n")
            f.write(f"对手: {', '.join(win['other_players'])}\n")
            f.write(f"天凤链接: {win['tenhou_url']}\n")
            f.write("\n" + "-" * 80 + "\n\n")

    print(f"✓ 已保存到 {output_file}", file=sys.stderr)

    # 同时保存JSON格式
    json_output = "test_dama/santi_dama_wins.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump({
            'player': player_name,
            'total': len(dama_wins),
            'wins': dama_wins
        }, f, ensure_ascii=False, indent=2)

    print(f"✓ 已保存JSON到 {json_output}", file=sys.stderr)

if __name__ == "__main__":
    main()
