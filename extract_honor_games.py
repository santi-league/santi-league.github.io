# -*- coding: utf-8 -*-
"""
提取荣誉牌谱（役满和三倍满）

用法：
  python extract_honor_games.py game-logs/m-league -o honor_games.json
"""

import os
import sys
import json
import argparse
import re
from urllib.parse import quote
from datetime import datetime

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
    # 匹配格式：月_日_年
    match = re.match(r'(\d+)_(\d+)_(\d+)', filename)
    if match:
        month, day, year = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%Y年%m月%d日")
        except ValueError:
            return filename
    return filename

def generate_tenhou_url(game_data):
    """生成天凤牌谱再生URL"""
    # 天凤牌谱再生URL格式：https://tenhou.net/5/?log=<json_data>
    json_str = json.dumps(game_data, ensure_ascii=False, separators=(',', ':'))
    encoded = quote(json_str)
    return f"https://tenhou.net/5/?log={encoded}"

def extract_honor_games(folder, recursive=True):
    """提取所有役满和三倍满的牌谱"""
    honor_games = []

    # 扫描所有JSON文件
    if recursive:
        files = []
        for root, dirs, filenames in os.walk(folder):
            for filename in filenames:
                if filename.endswith('.json'):
                    files.append(os.path.join(root, filename))
    else:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.json')]

    print(f"正在扫描 {len(files)} 个文件...", file=sys.stderr)

    for filepath in sorted(files):
        filename = os.path.basename(filepath)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
        except Exception as e:
            print(f"读取文件失败: {filepath} - {e}", file=sys.stderr)
            continue

        players = game_data.get('name', [])
        date_str = extract_date_from_filename(filename)

        for round_idx, round_data in enumerate(game_data['log']):
            # 获取局数信息
            round_info = round_data[0]
            round_name = parse_round_name(round_info)

            # 检查最后一个元素是否是和了
            last_element = round_data[-1]
            if isinstance(last_element, list) and len(last_element) > 0:
                if last_element[0] == '和了':
                    win_info = last_element[2]
                    point_desc = win_info[3] if len(win_info) > 3 else ''

                    # 检查是否是役满或三倍满
                    if '役満' in point_desc or 'Yakuman' in point_desc or 'Sanbaiman' in point_desc:
                        winner_idx = win_info[0]
                        winner = players[winner_idx] if winner_idx < len(players) else 'Unknown'

                        # 提取役种
                        yaku_list = win_info[4:] if len(win_info) > 4 else []
                        yaku_str = ', '.join(yaku_list)

                        # 生成天凤URL
                        tenhou_url = generate_tenhou_url(game_data)

                        honor_game = {
                            'date': date_str,
                            'filename': filename,
                            'round': round_name,
                            'round_idx': round_idx,
                            'winner': winner,
                            'point_desc': point_desc,
                            'yaku': yaku_str,
                            'yaku_list': yaku_list,
                            'tenhou_url': tenhou_url,
                            'type': 'yakuman' if ('役満' in point_desc or 'Yakuman' in point_desc) else 'sanbaiman'
                        }

                        honor_games.append(honor_game)
                        print(f"✓ {date_str} {round_name} {winner} - {point_desc}", file=sys.stderr)

    # 按日期排序（最新的在前）
    honor_games.sort(key=lambda x: x['date'], reverse=True)

    return honor_games

def main():
    ap = argparse.ArgumentParser(description="提取役满和三倍满的牌谱")
    ap.add_argument("folder", help="包含牌谱 JSON 的文件夹路径")
    ap.add_argument("-o", "--output", default="honor_games.json", help="输出文件路径")
    ap.add_argument("--no-recursive", action="store_true", help="不递归扫描子目录")
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    honor_games = extract_honor_games(folder, recursive=not args.no_recursive)

    print(f"\n找到 {len(honor_games)} 个荣誉牌谱", file=sys.stderr)
    print(f"- 役满: {sum(1 for g in honor_games if g['type'] == 'yakuman')} 个", file=sys.stderr)
    print(f"- 三倍满: {sum(1 for g in honor_games if g['type'] == 'sanbaiman')} 个", file=sys.stderr)

    # 保存结果
    output = {
        'total': len(honor_games),
        'yakuman_count': sum(1 for g in honor_games if g['type'] == 'yakuman'),
        'sanbaiman_count': sum(1 for g in honor_games if g['type'] == 'sanbaiman'),
        'games': honor_games
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 已保存到 {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
