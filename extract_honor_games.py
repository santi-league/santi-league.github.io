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
import copy
from urllib.parse import quote
from datetime import datetime

# 手役英文到日文的翻译
HAND_DICT = {
    "Mangan": "満貫",
    "Haneman": "跳満",
    "Baiman": "倍満",
    "Sanbaiman": "三倍満",
    "Yakuman": "役満",
    "Kazoeyakuman": "数え役満",
    "Kiriagemangan": "切り上げ満貫"
}

# 役种英文到日文的翻译
YAKU_DICT = {
    "White Dragon": "役牌 白",
    "Green Dragon": "役牌 發",
    "Red Dragon": "役牌 中",
    "Seat Wind": "自風 南",
    "Prevalent Wind": "場風 南",
    "Dora": "ドラ",
    "Ura Dora": "裏ドラ",
    "Red Five": "赤ドラ",
    "Riichi": "立直",
    "Double Riichi": "両立直",
    "Ippatsu": "一発",
    "Fully Concealed Hand": "門前清自摸和",
    "Mixed Triple Sequence": "三色同順",
    "Triple Triplets": "三色同刻",
    "Pure Double Sequence": "一盃口",
    "Twice Pure Double Sequence": "二盃口",
    "Pinfu": "平和",
    "All Simples": "断幺九",
    "Pure Straight": "一気通貫",
    "Seven Pairs": "七対子",
    "All Triplets": "対々和",
    "Half Outside Hand": "混全帯幺九",
    "Fully Outside Hand": "純全帯幺九",
    "After a Kan": "嶺上開花",
    "Under the Sea": "海底摸月",
    "Under the River": "河底撈魚",
    "Half Flush": "混一色",
    "Full Flush": "清一色",
    "Three Concealed Triplets": "三暗刻",
    "Thirteen Orphans": "国士無双",
    "Little Three Dragons": "小三元",
    "Three Kans": "三槓子",
    "All Terminals and Honors": "混老頭",
    "Blessing of Heaven": "天和",
    "Blessing of Earth": "地和",
    "Four Concealed Triplets": "四暗刻",
    "Big Three Dragons": "大三元",
    "All Honors": "字一色",
    "All Green": "緑一色",
    "All Terminals": "清老頭",
    "Nine Gates": "九蓮宝燈",
    "Four Winds": "四風連打",
    "Four Kans": "四槓子"
}

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

def convert_round_to_tenhou(round_data, game_data):
    """将单局数据转换为天凤格式"""
    # 翻译和了信息中的手役和役种
    if isinstance(round_data[-1], list) and len(round_data[-1]) > 0:
        if round_data[-1][0] == '和了':
            win_info = round_data[-1][2]

            # 翻译手役（如 "Yakuman 32000点∀" -> "役満32000点∀"）
            if len(win_info) > 3:
                point_desc = win_info[3]
                for en_hand, jp_hand in HAND_DICT.items():
                    if point_desc.startswith(en_hand):
                        point_desc = jp_hand + point_desc[len(en_hand):]
                        break
                win_info[3] = point_desc

            # 翻译役种列表（从第5个元素开始）
            new_yaku_list = win_info[:4]  # 前4个元素保持不变
            for i in range(4, len(win_info)):
                yaku_str = win_info[i]
                # 分离役种名和番数
                if '(' in yaku_str:
                    yaku_name = yaku_str.split('(')[0]
                    yaku_han = '(' + yaku_str.split('(')[1]
                    # 翻译役种名
                    if yaku_name in YAKU_DICT:
                        new_yaku_list.append(YAKU_DICT[yaku_name] + yaku_han)
                    else:
                        new_yaku_list.append(yaku_str)
                else:
                    new_yaku_list.append(yaku_str)

            round_data[-1][2] = new_yaku_list

    # 构建天凤格式的JSON（只包含单局）
    tenhou_data = {
        "title": ["Tournament", "M-League"],
        "name": game_data.get("name", []),
        "rule": game_data.get("rule", {}),
        "log": [round_data]
    }

    return tenhou_data

def generate_tenhou_url(round_data, game_data):
    """生成天凤牌谱再生URL"""
    # 转换为天凤格式
    tenhou_data = convert_round_to_tenhou(round_data, game_data)
    # 生成URL：https://tenhou.net/5/#json=<json_data>
    # 注意：直接拼接JSON字符串，不需要URL编码
    json_str = json.dumps(tenhou_data, ensure_ascii=False, separators=(',', ':'))
    return f"https://tenhou.net/5/#json={json_str}"

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

                        # 生成天凤URL（需要深拷贝以避免修改原始数据）
                        round_data_copy = copy.deepcopy(round_data)
                        tenhou_url = generate_tenhou_url(round_data_copy, game_data)

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
