# -*- coding: utf-8 -*-
"""
调试工具：跟踪指定小局中某位玩家的听牌与有役状态

用法示例：
  python test_dama/debug_tenpai_states.py \\
      --file game-logs/m-league/10_10_2025_Tounament_South\\ \\(1\\).json \\
      --player santi \\
      --round 1
"""

import argparse
import json
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mahjong_hand_analyzer import HandTracker, decode_tile, _convert_to_34_array, _calculate_standard_shanten_34, _calculate_pairs_shanten_34, _calculate_kokushi_shanten_34  # noqa: E402
from mahjong_hand_analyzer import tiles_to_string as base_tiles_to_string  # noqa: E402
from extract_honor_games import convert_round_to_tenhou  # noqa: E402

META_LIST_COUNT = 4
PLAYER_BLOCK_SIZE = 3


def tiles_to_string_human(tiles: List[int]) -> str:
    text = base_tiles_to_string(tiles)
    mapping = {'万': '万', '条': '条', '筒': '筒'}
    honor_map = {
        '1': '东',
        '2': '南',
        '3': '西',
        '4': '北',
        '5': '白',
        '6': '发',
        '7': '中',
    }

    parts = []
    for part in text.split():
        if part.endswith('字'):
            numbers = part[:-1]
            honors = ''.join(honor_map.get(ch, ch) for ch in numbers)
            parts.append(honors)
        else:
            parts.append(part)
    return ' '.join(parts)


def tile_to_human(tile: int) -> str:
    if not isinstance(tile, int) or tile <= 0 or tile >= 60:
        return "-"

    # 红宝牌特殊处理
    if tile == 51:
        return "红5万"
    if tile == 52:
        return "红5筒"  # 52是红5p，对应21-29的筒
    if tile == 53:
        return "红5条"  # 53是红5s，对应31-39的条

    # 实际编码：21-29是筒(s)，31-39是条(p)
    tens = tile // 10
    ones = tile % 10

    if tens == 1 and 1 <= ones <= 9:
        return f"{ones}万"
    elif tens == 2 and 1 <= ones <= 9:
        return f"{ones}筒"  # 21-29是筒
    elif tens == 3 and 1 <= ones <= 9:
        return f"{ones}条"  # 31-39是条
    elif tens == 4 and 1 <= ones <= 7:
        honor_map = {
            1: "东",
            2: "南",
            3: "西",
            4: "北",
            5: "白",
            6: "发",
            7: "中",
        }
        return honor_map.get(ones, f"字{ones}")

    return str(tile)


def calculate_shanten_breakdown(hand: List[int]) -> Dict[str, int]:
    if not hand:
        return {"standard": 99, "pairs": 99, "kokushi": 99}

    decoded = [decode_tile(t) for t in hand if decode_tile(t)[0] != "unknown"]
    if not decoded:
        return {"standard": 99, "pairs": 99, "kokushi": 99}

    tiles_34 = _convert_to_34_array(decoded)

    standard = _calculate_standard_shanten_34(tiles_34[:])
    pairs = _calculate_pairs_shanten_34(tiles_34[:])
    kokushi = _calculate_kokushi_shanten_34(tiles_34[:])

    return {
        "standard": standard,
        "pairs": pairs,
        "kokushi": kokushi,
    }


def extract_player_block(round_data: List, player_idx: int) -> List[List[int]]:
    """按照 3 段结构提取指定玩家的牌谱块"""
    block = []
    block_start = META_LIST_COUNT + player_idx * PLAYER_BLOCK_SIZE

    for offset in range(PLAYER_BLOCK_SIZE):
        idx = block_start + offset
        if idx >= len(round_data) - 1:
            block.append([])
            continue
        item = round_data[idx]
        block.append(item if isinstance(item, list) else [])

    return block


def process_draw_and_discard_lists(tracker: HandTracker, draw_list: List, discard_list: List):
    """
    处理摸牌列表和打牌列表

    draw_list: 每轮摸到的牌
    discard_list: 每轮打出的牌（60表示摸切，'rXX'表示立直打XX）
    """
    if not isinstance(draw_list, list) or not isinstance(discard_list, list):
        return

    # 过滤出数字牌
    draws = [t for t in draw_list if isinstance(t, int)]

    # 处理打牌列表：将立直标记'rXX'转换为对应的牌和立直标记
    discards = []
    riichi_turns = set()
    for i, item in enumerate(discard_list):
        if isinstance(item, str) and item.startswith('r'):
            # 立直标记，例如'r44'表示立直打44
            tile_str = item[1:]
            if tile_str.isdigit():
                discards.append(int(tile_str))
                riichi_turns.add(i)
            else:
                discards.append(60)
        elif isinstance(item, int):
            discards.append(item)
        else:
            discards.append(60)

    # 处理每一轮的摸打
    for i in range(max(len(draws), len(discards))):
        draw_tile = draws[i] if i < len(draws) else 60
        discard_tile = discards[i] if i < len(discards) else 60

        # 如果打出的是60（摸切），则打出摸到的牌
        if discard_tile == 60:
            discard_tile = draw_tile

        tracker.process_action_pair(draw_tile, discard_tile)

        # 如果这一巡是立直，只设置立直标志（牌已经在process_action_pair中打出了）
        if i in riichi_turns:
            tracker.riichi_declared = True
            tracker.dama_state = False

    # 处理其他特殊动作（副露等）
    for item in discard_list:
        if isinstance(item, str) and not item.startswith('r'):
            tracker.process_special_action(item)


def main():
    parser = argparse.ArgumentParser(description="调试玩家在某小局的听牌与有役状态")
    parser.add_argument("--file", required=True, help="牌谱 JSON 文件路径")
    parser.add_argument("--player", required=True, help="玩家名称")
    parser.add_argument("--round", type=int, default=0, help="小局索引（从 0 起）")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        game = json.load(f)

    names = game.get("name", [])
    if args.player not in names:
        raise SystemExit(f"玩家 {args.player} 不在牌谱中：{args.file}")

    player_idx = names.index(args.player)

    rounds = game.get("log", [])
    if args.round < 0 or args.round >= len(rounds):
        raise SystemExit(f"小局索引超出范围：0 ~ {len(rounds) - 1}")

    round_data = rounds[args.round]
    if not round_data:
        raise SystemExit("该小局数据为空")

    header = round_data[0] if isinstance(round_data[0], list) else [0, 0, 0]
    round_raw = header[0] if header else 0
    east_player = round_raw % 4
    prevalent_wind = min(round_raw // 4 + 1, 4)

    block = extract_player_block(round_data, player_idx)
    initial_hand = [t for t in block[0] if isinstance(t, int)]

    if not initial_hand:
        raise SystemExit("无法解析初始手牌（可能未记录或格式不同）")

    # 输出原始三行数据
    print(f"\n==== {args.player} 的原始三行数据 ====")
    for list_idx, data_list in enumerate(block):
        print(f"\n列表{list_idx}:")
        print("原始编码:", data_list)
        # 转换为麻将牌格式
        converted = []
        for item in data_list:
            if isinstance(item, int):
                if item == 60:
                    converted.append("摸切")
                else:
                    converted.append(tile_to_human(item))
            else:
                converted.append(str(item))
        print("麻将牌:", " ".join(converted))

    print()

    seat_wind = ((player_idx - east_player) % 4) + 1

    tracker = HandTracker(
        player_idx,
        initial_hand,
        seat_wind=seat_wind,
        prevalent_wind=prevalent_wind,
        debug=True
    )

    # block[1] 是摸牌列表，block[2] 是打牌列表
    draw_list = block[1] if len(block) > 1 else []
    discard_list = block[2] if len(block) > 2 else []

    process_draw_and_discard_lists(tracker, draw_list, discard_list)

    debug_log = tracker.get_debug_log()

    tenhou_data = convert_round_to_tenhou(round_data, game)
    tenhou_url = f"https://tenhou.net/5/#json={json.dumps(tenhou_data, ensure_ascii=False, separators=(',', ':'))}"

    print(f"牌谱: {args.file}")
    print(f"玩家: {args.player} (索引 {player_idx})")
    print(f"小局索引: {args.round}")
    print(f"初始手牌: {tiles_to_string_human(initial_hand)}")
    print(f"座风: {seat_wind}, 场风: {prevalent_wind}")
    print(f"天凤链接: {tenhou_url}")
    # 检测打牌列表中的立直标记
    riichi_turn_info = {}  # {turn_index: riichi_tile}
    for i, item in enumerate(discard_list):
        if isinstance(item, str) and item.startswith('r'):
            # 解析立直打出的牌，例如 'r44' -> 44
            riichi_tile_str = item[1:]
            if riichi_tile_str.isdigit():
                riichi_tile = int(riichi_tile_str)
                riichi_turn_info[i] = riichi_tile

    print("\n==== 摸打过程 ====")
    step = 0
    riichi_declared = False
    for idx, entry in enumerate(debug_log, 1):
        # 只显示摸打动作
        if entry['reason'] == 'action_pair':
            draw_tile = entry.get('draw', 60)
            discard_tile = entry.get('discard', 60)

            draw_h = tile_to_human(draw_tile) if draw_tile < 60 else "-"

            # 检查是否在这一巡立直
            if step in riichi_turn_info:
                riichi_tile = riichi_turn_info[step]
                discard_h = tile_to_human(riichi_tile)
                action_desc = f"摸{draw_h} 打{discard_h} [立直]"
                riichi_declared = True
            else:
                discard_h = tile_to_human(discard_tile) if discard_tile < 60 else "-"
                # 判断是否摸切
                is_tsumogiri = (draw_tile == discard_tile and draw_tile < 60)
                action_desc = f"摸{draw_h} 切{discard_h}" if is_tsumogiri else f"摸{draw_h} 打{discard_h}"

            step += 1

            hand_human = tiles_to_string_human(entry.get("hand", []))
            shanten_info = calculate_shanten_breakdown(entry.get("hand", []))
            shanten_str = f"标准{shanten_info['standard']} / 七对{shanten_info['pairs']} / 国士{shanten_info['kokushi']}"

            yaku_str = ", ".join(entry.get("yaku", [])) if entry.get("yaku") else "-"

            # 显示立直状态（立直之后的每一巡都标记）
            riichi_status = "✓ [已立直]" if riichi_declared else "✗"

            print(f"【第{step}巡】{action_desc}")
            print(f"  打后手牌: {hand_human} ({entry['tile_count']}张)")
            print(f"  向听数: {shanten_str}")
            print(f"  听牌: {'是' if entry['tenpai'] else '否'} | 役: {yaku_str}")
            print(f"  默听: {'✓' if entry['dama_state'] else '✗'} | 立直: {riichi_status}")
            print()
        elif entry['reason'] == 'special_action':
            action_str = entry.get('action', '')
            print(f"【特殊动作】{action_str}")
            if action_str.startswith('r'):
                print(f"  → 立直")
            elif 'c' in action_str or 'p' in action_str or 'k' in action_str:
                print(f"  → 副露")
            print()


if __name__ == "__main__":
    main()
