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

from mahjong_hand_analyzer import (  # noqa: E402
    HandTracker,
    tiles_to_string,
    decode_tile,
    _convert_to_34_array,
    _calculate_standard_shanten_34,
    _calculate_pairs_shanten_34,
    _calculate_kokushi_shanten_34,
)
from extract_honor_games import convert_round_to_tenhou  # noqa: E402

META_LIST_COUNT = 4
PLAYER_BLOCK_SIZE = 3


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


def process_action_list(tracker: HandTracker, action_list: List):
    """复用 summarize_v23 中的解析逻辑"""
    if not isinstance(action_list, list) or not action_list:
        return

    draw_tiles: List[int] = []
    discard_tiles: List[int] = []
    special_actions: List[str] = []

    for action in action_list:
        if isinstance(action, int):
            if action >= 60:
                draw_tiles.append(action)
            else:
                if len(draw_tiles) == len(discard_tiles):
                    draw_tiles.append(action)
                else:
                    discard_tiles.append(action)
        elif isinstance(action, str):
            special_actions.append(action)

    for draw, discard in zip(draw_tiles, discard_tiles):
        tracker.process_action_pair(draw, discard)

    for action_str in special_actions:
        tracker.process_special_action(action_str)


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

    seat_wind = ((player_idx - east_player) % 4) + 1

    tracker = HandTracker(
        player_idx,
        initial_hand,
        seat_wind=seat_wind,
        prevalent_wind=prevalent_wind,
        debug=True
    )

    for action_list in block[1:]:
        process_action_list(tracker, action_list)

    debug_log = tracker.get_debug_log()

    tenhou_data = convert_round_to_tenhou(round_data, game)
    tenhou_url = f"https://tenhou.net/5/#json={json.dumps(tenhou_data, ensure_ascii=False, separators=(',', ':'))}"

    print(f"牌谱: {args.file}")
    print(f"玩家: {args.player} (索引 {player_idx})")
    print(f"小局索引: {args.round}")
    print(f"初始手牌: {tiles_to_string(initial_hand)}")
    print(f"座风: {seat_wind}, 场风: {prevalent_wind}")
    print(f"天凤链接: {tenhou_url}")
    print("\n==== 调试日志 ====")
    for idx, entry in enumerate(debug_log, 1):
        yaku_str = ", ".join(entry.get("yaku", [])) if entry.get("yaku") else "-"
        shanten_info = calculate_shanten_breakdown(entry.get("hand", []))
        shanten_str = (
            f"标准{shanten_info['standard']} / 七对{shanten_info['pairs']} / 国士{shanten_info['kokushi']}"
        )
        print(f"[{idx:02d}] 理由: {entry['reason']}")
        print(f"     手牌: {entry['hand_str']} ({entry['tile_count']} 张)")
        print(f"     听牌: {'是' if entry['tenpai'] else '否'}; 役: {yaku_str}")
        print(f"     向听: {shanten_str}")
        print(f"     默听: {'是' if entry['dama_state'] else '否'}; 立直: {'是' if entry['riichi_declared'] else '否'}")
        if "draw" in entry or "discard" in entry:
            print(f"     摸: {entry.get('draw')}, 打: {entry.get('discard')}")
        if "action" in entry:
            print(f"     特殊操作: {entry['action']}")
        if entry['reason'].startswith("exit_dama_state"):
            print(f"     退出原因: {entry.get('detail', '-')}")
        print()


if __name__ == "__main__":
    main()
