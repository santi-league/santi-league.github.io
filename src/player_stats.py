# -*- coding: utf-8 -*-
"""
玩家数据统计分析工具

基于 batch_summarize_v23.py 的输出，计算每个玩家的：
- 和牌率（自摸率、荣和率）
- 放铳率
- 副露率
- 立直率
- 平均打点
- 平均顺位
- 一发率、里宝率
- 副露后和牌率/放铳率
- 立直后放铳率

用法：
  python player_stats.py game-logs/m-league -r
  python player_stats.py game-logs/m-league -r -o stats.json
  python player_stats.py game-logs/m-league -r --format table
"""

import os
import sys
import json
import argparse
from collections import defaultdict
from typing import Dict, List, Any

# 导入别名处理函数
try:
    from summarize_v23 import load_player_aliases, normalize_player_name
except ImportError:
    # 如果导入失败，使用空的别名映射
    def load_player_aliases():
        return {}
    def normalize_player_name(name, alias_map):
        return name

# 手役英文到中文的映射
YAKU_TRANSLATION = {
    # 1番役
    "Riichi": "立直",
    "Ippatsu": "一发",
    "Fully Concealed Hand": "门前清自摸和",
    "Pinfu": "平和",
    "Pure Double Sequence": "一杯口",
    "White Dragon": "白",
    "Green Dragon": "发",
    "Red Dragon": "中",
    "Seat Wind": "自风",
    "Prevailing Wind": "场风",
    "Prevalent Wind": "场风",
    "All Simples": "断幺九",
    "Robbing a Kan": "抢杠",
    "After a Kan": "岭上开花",
    "Under the Sea": "海底捞月",
    "Under the River": "河底捞鱼",

    # 2番役
    "Double Riichi": "两立直",
    "Seven Pairs": "七对子",
    "All Triplets": "对对和",
    "Three Concealed Triplets": "三暗刻",
    "Three Color Triplets": "三色同刻",
    "Three Kans": "三杠子",
    "All Terminals and Honors": "混老头",
    "Little Three Dragons": "小三元",
    "Half Flush": "混一色",
    "Pure Straight": "一气通贯",
    "Three Color Straight": "三色同顺",

    # 3番役
    "Twice Pure Double Sequence": "两杯口",
    "Half Outside Hand": "混全带幺九",
    "Mixed Triple Sequence": "三色同顺",

    # 6番役
    "Full Flush": "清一色",
    "Pure Outside Hand": "纯全带幺九",

    # 役满
    "Four Concealed Triplets": "四暗刻",
    "Big Three Dragons": "大三元",
    "Little Four Winds": "小四喜",
    "Big Four Winds": "大四喜",
    "All Honors": "字一色",
    "All Terminals": "清老头",
    "All Green": "绿一色",
    "Nine Gates": "九莲宝灯",
    "Thirteen Orphans": "国士无双",
    "Four Kans": "四杠子",
    "Heavenly Hand": "天和",
    "Hand of Earth": "地和",
    "Hand of Man": "人和",
    "Blessing of Heaven": "天和",
    "Blessing of Earth": "地和",

    # 宝牌相关（虽然不会统计，但以防万一）
    "Dora": "宝牌",
    "Ura Dora": "里宝牌",
    "Red Five": "赤宝牌",
    "Akadora": "赤宝牌",

    # 三麻特有
    "Kita": "拔北",

    # 其他可能的英文名
    "One Shot": "一发",
    "Tanyao": "断幺九",
    "Iipeiko": "一杯口",
    "Chanta": "混全带幺九",
    "Junchan": "纯全带幺九",
    "Ryanpeikou": "两杯口",
    "Chitoitsu": "七对子",
    "Toitoi": "对对和",
    "Sanankou": "三暗刻",
    "Sanshoku Dokou": "三色同刻",
    "Sankantsu": "三杠子",
    "Honroutou": "混老头",
    "Shousangen": "小三元",
    "Honitsu": "混一色",
    "Chinitsu": "清一色",
    "Itsu": "一气通贯",
    "Ittsu": "一气通贯",
    "Sanshoku": "三色同顺",
    "Sanshoku Doujun": "三色同顺",
}

try:
    from batch_summarize_v23 import scan_files
    from summarize_v23 import summarize_log
except ImportError as e:
    print("无法导入必要模块，请确认 batch_summarize_v23.py 和 summarize_v23.py 在同目录下。", file=sys.stderr)
    raise


def calculate_tenhou_r_value(rank: int, games_played: int, player_r: float, table_avg_r: float, final_points: int, uma_config=None, origin_points=25000, avg_uma=None) -> float:
    """
    计算天凤R值变动

    参数:
    - rank: 名次 (1-4)
    - games_played: 已进行的游戏数
    - player_r: 玩家当前R值
    - table_avg_r: 桌平均R值
    - final_points: 最终素点
    - uma_config: Uma配置字典，默认为M-League规则 {1: 45000, 2: 5000, 3: -15000, 4: -35000}
    - origin_points: 起始分数/返点，M-League为25000，EMA为30000
    - avg_uma: 平均uma值（用于同分情况），如果提供则优先使用

    返回: R值变动量

    计算公式：
    R值变动 = 试合数补正 × ((Uma + 素点差)/1000 + (桌平均R - 自己R)/40)
    """
    # Uma（单位：点）
    if avg_uma is not None:
        # 如果提供了平均uma，使用它（同分平分uma的情况）
        uma = avg_uma
    elif uma_config is None:
        # 默认M-League Uma
        uma_points = {1: 45000, 2: 5000, 3: -15000, 4: -35000}
        uma = uma_points.get(rank, 0)
    else:
        uma = uma_config.get(rank, 0)

    # 素点差（单位：点）
    score_diff = final_points - origin_points

    # 合计点数变化（转换为千点单位）
    total_change = (uma + score_diff) / 1000.0

    # 桌平均R补正：(桌平均R - 自己的R) / 40
    r_correction = (table_avg_r - player_r) / 40.0

    # 试合数补正
    if games_played < 400:
        games_correction = 1 - games_played * 0.002
    else:
        games_correction = 0.2

    # R值变动 = 试合数补正 × (点数变化 + R值补正)
    r_change = games_correction * (total_change + r_correction)

    # 小数第3位以下切り上げ（向上取整到小数点后2位）
    import math
    r_change = math.ceil(r_change * 100) / 100

    return r_change


def calculate_player_stats(batch_results: List[Dict[str, Any]], round_counts: List[int], uma_config=None, origin_points=25000) -> Dict[str, Dict[str, Any]]:
    """
    基于批量统计结果，计算每个玩家的综合数据

    参数:
    - uma_config: Uma配置字典，默认为M-League规则 {1: 45000, 2: 5000, 3: -15000, 4: -35000}
    - origin_points: 起始分数/返点，M-League为25000，EMA为30000

    返回格式：
    {
        "玩家名": {
            "games": 总局数,
            "win_rate": 和牌率,
            "tsumo_rate": 自摸率,
            "ron_rate": 荣和率,
            "deal_in_rate": 放铳率,
            "riichi_rate": 立直率,
            "furo_rate": 副露率,
            "avg_win_points": 平均和牌打点,
            "avg_deal_in_points": 平均放铳失点,
            "avg_rank": 平均顺位,
            "avg_final_points": 平均终局点数,
            "ippatsu_rate": 一发率(占和牌数),
            "ura_rate": 里宝率(占和牌数),
            "furo_then_win_rate": 副露后和牌率(占副露数),
            "furo_then_deal_in_rate": 副露后放铳率(占副露数),
            "riichi_then_deal_in_rate": 立直后放铳率(占立直数),
            "deal_in_targets": 放铳给各玩家的次数统计,
            ...原始统计数据
        }
    }
    """
    # 加载玩家别名配置
    alias_map = load_player_aliases()
    # 跟踪每个主ID使用过的所有原始名称
    name_aliases_used = defaultdict(set)

    player_data = defaultdict(lambda: {
        "games": 0,          # 游戏场数（半庄数）
        "total_rounds": 0,   # 总小局数
        "furo_hands": 0,
        "riichi_hands": 0,
        "win_hands": 0,
        "riichi_win_hands": 0,  # 立直后和牌次数
        "win_points_sum": 0,
        "riichi_win_points_sum": 0,  # 立直和牌打点总和
        "furo_win_points_sum": 0,    # 副露和牌打点总和
        "dama_win_hands": 0,         # 默听和牌次数
        "dama_win_points_sum": 0,    # 默听和牌打点总和
        "tsumo_only_win_hands": 0,   # 仅自摸和牌次数
        "tsumo_only_win_points_sum": 0,  # 仅自摸和牌打点总和
        "deal_in_hands": 0,
        "deal_in_points_sum": 0,
        "furo_then_win_hands": 0,
        "furo_then_deal_in_hands": 0,
        "riichi_then_deal_in_hands": 0,
        "ippatsu_hands": 0,
        "ura_hands": 0,
        "rank_sum": 0,
        "final_points_sum": 0,
        "deal_in_targets": defaultdict(int),
        # 新增：总点数和名次统计
        "total_score": 0,    # 总点数（含马点）
        "rank_1": 0,         # 第1名次数
        "rank_2": 0,         # 第2名次数
        "rank_3": 0,         # 第3名次数
        "rank_4": 0,         # 第4名次数
        # 新增：流局听牌统计
        "ryuukyoku_hands": 0,  # 流局总次数
        "ryuukyoku_tenpai": 0, # 流局听牌次数
        "riichi_ryuukyoku": 0, # 立直后流局次数
        "furo_ryuukyoku": 0,   # 副露后流局次数
        # 新增：对每个玩家的放铳详细点数
        "deal_in_points_to_players": defaultdict(list),  # {玩家名: [点数列表]}
        # 新增：手役统计
        "yaku_count": defaultdict(int),  # {手役名: 次数}
        # 新增：天凤R值
        "current_r": 1500.0,  # 当前R值
        "total_rank": 0,      # 用于计算平均顺位
        # 新增：默听状态统计（基于手牌追踪）
        "dama_state_hands": 0,      # 进入默听状态的次数
        "dama_state_win": 0,        # 默听状态下和了
        "dama_state_deal_in": 0,    # 默听状态下放铳
        "dama_state_draw": 0,       # 默听状态下流局
        "dama_state_pass": 0,       # 默听状态下横移
        # 新增：对战统计
        "vs_players": defaultdict(lambda: {
            "games": 0,           # 对战场数
            "wins": 0,            # 胜利次数（顺位更高）
            "win_points": 0,      # 从对方和了获得的点数
            "lose_points": 0,     # 放铳给对方的点数
            "score_diff": 0,      # 总得点差值（自己-对方，含马点）
        }),
    })

    # 设置默认UMA配置（M-League）
    if uma_config is None:
        uma_config = {1: 45000, 2: 5000, 3: -15000, 4: -35000}

    # 天凤R值追踪：{玩家名: 当前R值}
    player_r_values = defaultdict(lambda: 1500.0)

    # 汇总所有对局数据
    for idx, result in enumerate(batch_results):
        summary = result.get("summary", [])
        # 获取这场游戏的小局数
        rounds_in_game = round_counts[idx] if idx < len(round_counts) else 0

        # 计算这一局的桌平均R值（在游戏开始前）
        # 使用归一化后的玩家名
        raw_table_players = [p.get("name", "") for p in summary if p.get("name")]
        table_players = [normalize_player_name(name, alias_map) for name in raw_table_players]
        table_avg_r = sum(player_r_values[name] for name in table_players) / len(table_players) if table_players else 1500.0

        # 构建本局玩家名次映射（使用归一化后的名字）
        player_ranks = {normalize_player_name(p.get("name"), alias_map): p.get("rank", 4) for p in summary if p.get("name")}

        for player_stat in summary:
            raw_name = player_stat.get("name", "")
            if not raw_name:
                continue

            # 归一化玩家名到主ID
            name = normalize_player_name(raw_name, alias_map)
            # 跟踪这个主ID使用过的原始名称
            name_aliases_used[name].add(raw_name)

            pd = player_data[name]

            # 天凤R值计算：先获取进行这局游戏前的游戏数
            games_before = pd["games"]

            # 然后再累加统计数据
            pd["games"] += 1
            pd["total_rounds"] += rounds_in_game
            pd["furo_hands"] += player_stat.get("furo_hands", 0)
            pd["riichi_hands"] += player_stat.get("riichi_hands", 0)
            pd["win_hands"] += player_stat.get("win_hands", 0)
            pd["riichi_win_hands"] += player_stat.get("riichi_win_hands", 0)
            pd["win_points_sum"] += player_stat.get("win_points_sum", 0)
            pd["riichi_win_points_sum"] += player_stat.get("riichi_win_points_sum", 0)
            pd["furo_win_points_sum"] += player_stat.get("furo_win_points_sum", 0)
            pd["dama_win_hands"] += player_stat.get("dama_win_hands", 0)
            pd["dama_win_points_sum"] += player_stat.get("dama_win_points_sum", 0)
            pd["tsumo_only_win_hands"] += player_stat.get("tsumo_only_win_hands", 0)
            pd["tsumo_only_win_points_sum"] += player_stat.get("tsumo_only_win_points_sum", 0)
            pd["deal_in_hands"] += player_stat.get("deal_in_hands", 0)
            pd["deal_in_points_sum"] += player_stat.get("deal_in_points_sum", 0)
            pd["furo_then_win_hands"] += player_stat.get("furo_then_win_hands", 0)
            pd["furo_then_deal_in_hands"] += player_stat.get("furo_then_deal_in_hands", 0)
            pd["riichi_then_deal_in_hands"] += player_stat.get("riichi_then_deal_in_hands", 0)
            pd["ippatsu_hands"] += player_stat.get("ippatsu_hands", 0)
            pd["ura_hands"] += player_stat.get("ura_hands", 0)
            pd["rank_sum"] += player_stat.get("rank", 0)
            pd["final_points_sum"] += player_stat.get("final_points", 0)

            # 计算总点数：(终局点数 - origin_points) + 马点
            final_points = player_stat.get("final_points", origin_points)
            rank = player_stat.get("rank", 4)

            # 使用传入的uma_config
            score = (final_points - origin_points) + uma_config.get(rank, 0)
            pd["total_score"] += score

            # 名次统计
            if rank == 1:
                pd["rank_1"] += 1
            elif rank == 2:
                pd["rank_2"] += 1
            elif rank == 3:
                pd["rank_3"] += 1
            elif rank == 4:
                pd["rank_4"] += 1

            # 使用之前获取的 games_before 计算R值（传入uma_config和origin_points）
            current_r = player_r_values[name]
            r_change = calculate_tenhou_r_value(rank, games_before, current_r, table_avg_r, final_points, uma_config, origin_points)
            player_r_values[name] += r_change
            pd["current_r"] = player_r_values[name]

            # 累加顺位用于计算平均
            pd["total_rank"] += rank

            # 流局听牌统计
            pd["ryuukyoku_hands"] += player_stat.get("ryuukyoku_hands", 0)
            pd["ryuukyoku_tenpai"] += player_stat.get("ryuukyoku_tenpai", 0)
            pd["riichi_ryuukyoku"] += player_stat.get("riichi_ryuukyoku", 0)
            pd["furo_ryuukyoku"] += player_stat.get("furo_ryuukyoku", 0)

            # 放铳目标统计（归一化目标玩家名）
            targets = player_stat.get("deal_in_targets", {})
            for target, count in targets.items():
                if count > 0:
                    normalized_target = normalize_player_name(target, alias_map)
                    pd["deal_in_targets"][normalized_target] += count

            # 放铳详细点数统计（归一化目标玩家名）
            deal_in_detail = player_stat.get("deal_in_points_detail", {})
            for target, points_list in deal_in_detail.items():
                if points_list:
                    normalized_target = normalize_player_name(target, alias_map)
                    pd["deal_in_points_to_players"][normalized_target].extend(points_list)

            # 手役统计（合并役牌）
            yaku_count = player_stat.get("yaku_count", {})
            yakuhai_types = {"White Dragon", "Green Dragon", "Red Dragon", "Seat Wind", "Prevailing Wind", "Prevalent Wind"}
            for yaku, count in yaku_count.items():
                if yaku in yakuhai_types:
                    pd["yaku_count"]["役牌"] += count
                else:
                    pd["yaku_count"][yaku] += count

            # 默听状态统计
            pd["dama_state_hands"] += player_stat.get("dama_state_hands", 0)
            pd["dama_state_win"] += player_stat.get("dama_state_win", 0)
            pd["dama_state_deal_in"] += player_stat.get("dama_state_deal_in", 0)
            pd["dama_state_draw"] += player_stat.get("dama_state_draw", 0)
            pd["dama_state_pass"] += player_stat.get("dama_state_pass", 0)

            # 对战统计：计算与其他玩家的对战情况
            my_rank = player_stat.get("rank", 4)
            my_final_points = player_stat.get("final_points", origin_points)
            my_score = (my_final_points - origin_points) + uma_config.get(my_rank, 0)

            for other_player in summary:
                other_raw_name = other_player.get("name", "")
                if not other_raw_name:
                    continue

                # 归一化对手玩家名
                other_name = normalize_player_name(other_raw_name, alias_map)
                # 跳过与自己的对战（比较归一化后的名字）
                if other_name == name:
                    continue

                other_rank = other_player.get("rank", 4)
                other_final_points = other_player.get("final_points", origin_points)
                other_score = (other_final_points - origin_points) + uma_config.get(other_rank, 0)

                vs_stat = pd["vs_players"][other_name]
                vs_stat["games"] += 1

                # 胜负判定：自己顺位更高（数字更小）为胜
                if my_rank < other_rank:
                    vs_stat["wins"] += 1

                # 从对方和了获得的点数（对方放铳给自己）
                # 需要检查对方的deal_in_points_detail中是否有归一化后的自己名字
                other_deal_in_detail = other_player.get("deal_in_points_detail", {})
                # 遍历所有放铳目标，归一化后与自己比较
                for target, points in other_deal_in_detail.items():
                    if normalize_player_name(target, alias_map) == name:
                        vs_stat["win_points"] += sum(points)

                # 放铳给对方的点数
                # 需要检查自己的deal_in_points_detail中是否有归一化后的对方名字
                my_deal_in_detail = player_stat.get("deal_in_points_detail", {})
                for target, points in my_deal_in_detail.items():
                    if normalize_player_name(target, alias_map) == other_name:
                        vs_stat["lose_points"] += sum(points)

                # 总得点差值（自己的得分 - 对方的得分）
                vs_stat["score_diff"] += (my_score - other_score)

    # 计算百分比和平均值
    stats = {}
    for name, pd in player_data.items():
        games = pd["games"]
        total_rounds = pd["total_rounds"]
        if games == 0:
            continue

        # 构建显示名称：主ID + 所有使用过的别名
        aliases_used = name_aliases_used.get(name, {name})
        if len(aliases_used) > 1:
            # 多个别名：显示为 "主ID (别名1, 别名2, ...)"
            # 排除主ID本身，只显示其他别名
            other_aliases = sorted(aliases_used - {name})
            display_name = f"{name} ({', '.join(other_aliases)})"
        else:
            # 只有一个名字，直接显示
            display_name = name

        win_hands = pd["win_hands"]
        riichi_win_hands = pd["riichi_win_hands"]
        deal_in_hands = pd["deal_in_hands"]
        furo_hands = pd["furo_hands"]
        riichi_hands = pd["riichi_hands"]

        stats[display_name] = {
            # 保存主ID用于内部引用
            "main_id": name,
            # 基础数据
            "games": games,
            "total_rounds": total_rounds,
            "furo_hands": furo_hands,
            "riichi_hands": riichi_hands,
            "win_hands": win_hands,
            "riichi_win_hands": riichi_win_hands,
            "deal_in_hands": deal_in_hands,
            "ippatsu_hands": pd["ippatsu_hands"],
            "ura_hands": pd["ura_hands"],

            # 天凤R值
            "tenhou_r": round(pd["current_r"], 2),

            # 百分比（相对于总小局数）
            "win_rate": round(win_hands / total_rounds * 100, 2) if total_rounds > 0 else 0,
            "deal_in_rate": round(deal_in_hands / total_rounds * 100, 2) if total_rounds > 0 else 0,
            "riichi_rate": round(riichi_hands / total_rounds * 100, 2) if total_rounds > 0 else 0,
            "furo_rate": round(furo_hands / total_rounds * 100, 2) if total_rounds > 0 else 0,

            # 和牌相关百分比（一发和里宝基于立直后和牌）
            "ippatsu_rate": round(pd["ippatsu_hands"] / riichi_win_hands * 100, 2) if riichi_win_hands > 0 else 0,
            "ura_rate": round(pd["ura_hands"] / riichi_win_hands * 100, 2) if riichi_win_hands > 0 else 0,

            # 副露相关
            "furo_then_win_hands": pd["furo_then_win_hands"],
            "furo_then_win_rate": round(pd["furo_then_win_hands"] / furo_hands * 100, 2) if furo_hands > 0 else 0,
            "furo_then_deal_in_rate": round(pd["furo_then_deal_in_hands"] / furo_hands * 100, 2) if furo_hands > 0 else 0,
            "furo_ryuukyoku": pd["furo_ryuukyoku"],
            "furo_ryuukyoku_rate": round(pd["furo_ryuukyoku"] / furo_hands * 100, 2) if furo_hands > 0 else 0,
            "furo_pass_rate": round((furo_hands - pd["furo_then_win_hands"] - pd["furo_then_deal_in_hands"] - pd["furo_ryuukyoku"]) / furo_hands * 100, 2) if furo_hands > 0 else 0,

            # 立直相关
            "riichi_win_rate": round(riichi_win_hands / riichi_hands * 100, 2) if riichi_hands > 0 else 0,
            "riichi_ryuukyoku_rate": round(pd["riichi_ryuukyoku"] / riichi_hands * 100, 2) if riichi_hands > 0 else 0,
            "riichi_then_deal_in_rate": round(pd["riichi_then_deal_in_hands"] / riichi_hands * 100, 2) if riichi_hands > 0 else 0,
            "riichi_pass_rate": round((riichi_hands - riichi_win_hands - pd["riichi_then_deal_in_hands"] - pd["riichi_ryuukyoku"]) / riichi_hands * 100, 2) if riichi_hands > 0 else 0,

            # 平均值
            "avg_win_points": round(pd["win_points_sum"] / win_hands, 0) if win_hands > 0 else 0,
            "avg_riichi_win_points": round(pd["riichi_win_points_sum"] / riichi_win_hands, 0) if riichi_win_hands > 0 else 0,
            "avg_furo_win_points": round(pd["furo_win_points_sum"] / pd["furo_then_win_hands"], 0) if pd["furo_then_win_hands"] > 0 else 0,
            "dama_win_hands": pd["dama_win_hands"],
            "avg_dama_win_points": round(pd["dama_win_points_sum"] / pd["dama_win_hands"], 0) if pd["dama_win_hands"] > 0 else 0,
            "tsumo_only_win_hands": pd["tsumo_only_win_hands"],
            "avg_tsumo_only_win_points": round(pd["tsumo_only_win_points_sum"] / pd["tsumo_only_win_hands"], 0) if pd["tsumo_only_win_hands"] > 0 else 0,
            "avg_deal_in_points": round(pd["deal_in_points_sum"] / deal_in_hands, 0) if deal_in_hands > 0 else 0,
            "avg_rank": round(pd["rank_sum"] / games, 2) if games > 0 else 0,
            "avg_final_points": round(pd["final_points_sum"] / games, 0) if games > 0 else 0,

            # 新增：总点数和名次统计
            "total_score": pd["total_score"],
            "rank_1": pd["rank_1"],
            "rank_2": pd["rank_2"],
            "rank_3": pd["rank_3"],
            "rank_4": pd["rank_4"],
            "rank_1_rate": round(pd["rank_1"] / games * 100, 2) if games > 0 else 0,
            "rank_2_rate": round(pd["rank_2"] / games * 100, 2) if games > 0 else 0,
            "rank_3_rate": round(pd["rank_3"] / games * 100, 2) if games > 0 else 0,
            "rank_4_rate": round(pd["rank_4"] / games * 100, 2) if games > 0 else 0,

            # 流局听牌
            "ryuukyoku_hands": pd["ryuukyoku_hands"],
            "ryuukyoku_tenpai": pd["ryuukyoku_tenpai"],
            "tenpai_rate": round(pd["ryuukyoku_tenpai"] / pd["ryuukyoku_hands"] * 100, 2) if pd["ryuukyoku_hands"] > 0 else 0,

            # 默听状态统计
            "dama_state_hands": pd["dama_state_hands"],
            "dama_state_win": pd["dama_state_win"],
            "dama_state_deal_in": pd["dama_state_deal_in"],
            "dama_state_draw": pd["dama_state_draw"],
            "dama_state_pass": pd["dama_state_pass"],
            "dama_state_win_rate": round(pd["dama_state_win"] / pd["dama_state_hands"] * 100, 2) if pd["dama_state_hands"] > 0 else 0,
            "dama_state_deal_in_rate": round(pd["dama_state_deal_in"] / pd["dama_state_hands"] * 100, 2) if pd["dama_state_hands"] > 0 else 0,
            "dama_state_draw_rate": round(pd["dama_state_draw"] / pd["dama_state_hands"] * 100, 2) if pd["dama_state_hands"] > 0 else 0,
            "dama_state_pass_rate": round(pd["dama_state_pass"] / pd["dama_state_hands"] * 100, 2) if pd["dama_state_hands"] > 0 else 0,

            # 放铳目标
            "deal_in_targets": dict(pd["deal_in_targets"]),

            # 对每个玩家的平均放铳点数
            "deal_in_avg_points_to_players": {
                target: round(sum(points) / len(points), 0) if points else 0
                for target, points in pd["deal_in_points_to_players"].items()
            },

            # 手役统计
            "yaku_count": dict(pd["yaku_count"]),
            "yaku_rate": {
                yaku: round(count / win_hands * 100, 2) if win_hands > 0 else 0
                for yaku, count in pd["yaku_count"].items()
            },

            # 对战统计
            "vs_players": {
                opponent: {
                    "games": vs_data["games"],
                    "wins": vs_data["wins"],
                    "win_rate": round(vs_data["wins"] / vs_data["games"] * 100, 2) if vs_data["games"] > 0 else 0,
                    "win_points": vs_data["win_points"],
                    "lose_points": vs_data["lose_points"],
                    "net_points": vs_data["win_points"] - vs_data["lose_points"],
                    "score_diff": vs_data["score_diff"],
                }
                for opponent, vs_data in pd["vs_players"].items()
            },
        }

    # 计算所有半庄数超过10的玩家的平均值
    qualified_players = [data for data in stats.values() if data["games"] > 10]

    if qualified_players:
        num_qualified = len(qualified_players)

        # 收集所有手役以计算平均率
        all_yaku = set()
        for player_data in qualified_players:
            all_yaku.update(player_data["yaku_rate"].keys())

        league_average = {
            "win_rate": round(sum(p["win_rate"] for p in qualified_players) / num_qualified, 2),
            "deal_in_rate": round(sum(p["deal_in_rate"] for p in qualified_players) / num_qualified, 2),
            "riichi_rate": round(sum(p["riichi_rate"] for p in qualified_players) / num_qualified, 2),
            "furo_rate": round(sum(p["furo_rate"] for p in qualified_players) / num_qualified, 2),
            "avg_win_points": round(sum(p["avg_win_points"] for p in qualified_players) / num_qualified, 0),
            "avg_deal_in_points": round(sum(p["avg_deal_in_points"] for p in qualified_players) / num_qualified, 0),
            "avg_rank": round(sum(p["avg_rank"] for p in qualified_players) / num_qualified, 2),
            "rank_1_rate": round(sum(p["rank_1_rate"] for p in qualified_players) / num_qualified, 2),
            "rank_2_rate": round(sum(p["rank_2_rate"] for p in qualified_players) / num_qualified, 2),
            "rank_3_rate": round(sum(p["rank_3_rate"] for p in qualified_players) / num_qualified, 2),
            "rank_4_rate": round(sum(p["rank_4_rate"] for p in qualified_players) / num_qualified, 2),
            "tenpai_rate": round(sum(p["tenpai_rate"] for p in qualified_players if p["ryuukyoku_hands"] > 0) /
                                 sum(1 for p in qualified_players if p["ryuukyoku_hands"] > 0), 2) if any(p["ryuukyoku_hands"] > 0 for p in qualified_players) else 0,
            "ippatsu_rate": round(sum(p["ippatsu_rate"] for p in qualified_players if p["riichi_win_hands"] > 0) /
                                  sum(1 for p in qualified_players if p["riichi_win_hands"] > 0), 2) if any(p["riichi_win_hands"] > 0 for p in qualified_players) else 0,
            "ura_rate": round(sum(p["ura_rate"] for p in qualified_players if p["riichi_win_hands"] > 0) /
                             sum(1 for p in qualified_players if p["riichi_win_hands"] > 0), 2) if any(p["riichi_win_hands"] > 0 for p in qualified_players) else 0,
            "riichi_win_rate": round(sum(p["riichi_win_rate"] for p in qualified_players if p["riichi_hands"] > 0) /
                                     sum(1 for p in qualified_players if p["riichi_hands"] > 0), 2) if any(p["riichi_hands"] > 0 for p in qualified_players) else 0,
            "riichi_then_deal_in_rate": round(sum(p["riichi_then_deal_in_rate"] for p in qualified_players if p["riichi_hands"] > 0) /
                                              sum(1 for p in qualified_players if p["riichi_hands"] > 0), 2) if any(p["riichi_hands"] > 0 for p in qualified_players) else 0,
            "furo_then_win_rate": round(sum(p["furo_then_win_rate"] for p in qualified_players if p["furo_hands"] > 0) /
                                        sum(1 for p in qualified_players if p["furo_hands"] > 0), 2) if any(p["furo_hands"] > 0 for p in qualified_players) else 0,
            "furo_then_deal_in_rate": round(sum(p["furo_then_deal_in_rate"] for p in qualified_players if p["furo_hands"] > 0) /
                                            sum(1 for p in qualified_players if p["furo_hands"] > 0), 2) if any(p["furo_hands"] > 0 for p in qualified_players) else 0,
            "avg_riichi_win_points": round(sum(p["avg_riichi_win_points"] for p in qualified_players if p["riichi_win_hands"] > 0) /
                                           sum(1 for p in qualified_players if p["riichi_win_hands"] > 0), 0) if any(p["riichi_win_hands"] > 0 for p in qualified_players) else 0,
            "avg_furo_win_points": round(sum(p["avg_furo_win_points"] for p in qualified_players if p["furo_then_win_hands"] > 0) /
                                         sum(1 for p in qualified_players if p["furo_then_win_hands"] > 0), 0) if any(p["furo_then_win_hands"] > 0 for p in qualified_players) else 0,
            "avg_dama_win_points": round(sum(p["avg_dama_win_points"] for p in qualified_players if p["dama_win_hands"] > 0) /
                                         sum(1 for p in qualified_players if p["dama_win_hands"] > 0), 0) if any(p["dama_win_hands"] > 0 for p in qualified_players) else 0,
            "avg_tsumo_only_win_points": round(sum(p["avg_tsumo_only_win_points"] for p in qualified_players if p["tsumo_only_win_hands"] > 0) /
                                                sum(1 for p in qualified_players if p["tsumo_only_win_hands"] > 0), 0) if any(p["tsumo_only_win_hands"] > 0 for p in qualified_players) else 0,
            # 手役平均率
            "yaku_rate": {
                yaku: round(sum(p["yaku_rate"].get(yaku, 0) for p in qualified_players if p["win_hands"] > 0) /
                           sum(1 for p in qualified_players if p["win_hands"] > 0 and yaku in p["yaku_rate"]), 2)
                if sum(1 for p in qualified_players if p["win_hands"] > 0 and yaku in p["yaku_rate"]) > 0 else 0
                for yaku in all_yaku
            }
        }

        stats["_league_average"] = league_average

    return stats


def format_as_table(stats: Dict[str, Dict[str, Any]]) -> str:
    """将统计数据格式化为表格"""
    if not stats:
        return "没有数据"

    # 按对局数降序排序
    sorted_players = sorted(stats.items(), key=lambda x: (-x[1]["games"], x[0]))

    lines = []
    lines.append("=" * 170)
    lines.append(f"{'玩家':<12} {'半庄':<6} {'小局':<6} {'R值':<8} {'总点数':<12} {'和牌率':<8} {'放铳率':<8} {'立直率':<8} {'副露率':<8} {'平均顺位':<10} {'1位率':<8}")
    lines.append("=" * 170)

    for name, data in sorted_players:
        lines.append(
            f"{name:<12} "
            f"{data['games']:<6} "
            f"{data['total_rounds']:<6} "
            f"{data['tenhou_r']:<8.2f} "
            f"{data['total_score']:<12} "
            f"{data['win_rate']:<7.2f}% "
            f"{data['deal_in_rate']:<7.2f}% "
            f"{data['riichi_rate']:<7.2f}% "
            f"{data['furo_rate']:<7.2f}% "
            f"{data['avg_rank']:<10.2f} "
            f"{data['rank_1_rate']:<7.2f}%"
        )

    lines.append("=" * 120)
    lines.append("")
    lines.append("详细统计:")
    lines.append("-" * 120)

    for name, data in sorted_players:
        lines.append(f"\n【{name}】（{data['games']} 半庄 / {data['total_rounds']} 小局）")
        lines.append(f"  天凤R值: {data['tenhou_r']:.2f}")
        lines.append(f"  总点数: {data['total_score']:+} (平均 {data['total_score']/data['games']:+.0f}/半庄), 平均顺位: {data['avg_rank']:.2f}")
        lines.append(f"  名次分布: 1位 {data['rank_1']}次({data['rank_1_rate']}%), 2位 {data['rank_2']}次({data['rank_2_rate']}%), 3位 {data['rank_3']}次({data['rank_3_rate']}%), 4位 {data['rank_4']}次({data['rank_4_rate']}%)")
        # 计算和牌类型数据
        riichi_win_hands = data['riichi_win_hands']
        furo_then_win_hands = data['furo_then_win_hands']
        dama_win_hands = data['dama_win_hands']
        tsumo_only_win_hands = data['tsumo_only_win_hands']

        lines.append(f"  和了: {data['win_hands']} 局 ({data['win_rate']}%), 平均打点: {data['avg_win_points']:.0f}")
        lines.append(f"    立直和了: {riichi_win_hands} 局 (平均{data['avg_riichi_win_points']:.0f}点), 一发: {data['ippatsu_hands']} 局 ({data['ippatsu_rate']}%), 里宝: {data['ura_hands']} 局 ({data['ura_rate']}%)")
        lines.append(f"    副露和了: {furo_then_win_hands} 局 (平均{data['avg_furo_win_points']:.0f}点)")
        if dama_win_hands > 0:
            lines.append(f"    默听和了: {dama_win_hands} 局 (平均{data['avg_dama_win_points']:.0f}点)")
        if tsumo_only_win_hands > 0:
            lines.append(f"    仅自摸和了: {tsumo_only_win_hands} 局 (平均{data['avg_tsumo_only_win_points']:.0f}点)")
        lines.append(f"  放铳: {data['deal_in_hands']} 局 ({data['deal_in_rate']}%), 平均失点: {data['avg_deal_in_points']:.0f}")
        lines.append(f"  立直: {data['riichi_hands']} 局 ({data['riichi_rate']}%), 立直后: 和了{data['riichi_win_rate']}% / 流局{data['riichi_ryuukyoku_rate']}% / 放铳{data['riichi_then_deal_in_rate']}% / 横移{data['riichi_pass_rate']}%")
        lines.append(f"  副露: {data['furo_hands']} 局 ({data['furo_rate']}%), 副露后: 和了{data['furo_then_win_rate']}% / 流局{data['furo_ryuukyoku_rate']}% / 放铳{data['furo_then_deal_in_rate']}% / 横移{data['furo_pass_rate']}%")

        # 流局听牌率
        if data['ryuukyoku_hands'] > 0:
            lines.append(f"  流局: {data['ryuukyoku_hands']} 次, 听牌 {data['ryuukyoku_tenpai']} 次 ({data['tenpai_rate']}%)")

        # 显示放铳给各玩家的详细统计（前8名）
        if data['deal_in_targets']:
            targets_sorted = sorted(data['deal_in_targets'].items(), key=lambda x: -x[1])
            top_targets = targets_sorted[:8]
            avg_points_map = data['deal_in_avg_points_to_players']
            lines.append(f"  放铳统计 (前{min(8, len(top_targets))}名):")
            for idx, (target, count) in enumerate(top_targets, 1):
                avg_pts = avg_points_map.get(target, 0)
                lines.append(f"    {idx}. {target}: {count}次, 平均{avg_pts:.0f}点")

        # 显示手役统计（按出现次数排序，只显示前10名）
        if data['yaku_count']:
            yaku_sorted = sorted(data['yaku_count'].items(), key=lambda x: -x[1])
            top_yaku = yaku_sorted[:10]
            lines.append(f"  手役统计 (前{min(10, len(top_yaku))}名, 共{len(yaku_sorted)}种):")
            for yaku, count in top_yaku:
                yaku_cn = YAKU_TRANSLATION.get(yaku, yaku)  # 如果没有翻译，保留原文
                rate = data['yaku_rate'].get(yaku, 0)
                lines.append(f"    {yaku_cn}: {count}次 ({rate}%)")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="统计雀魂牌谱中每个玩家的和牌率、放铳率等数据")
    ap.add_argument("folder", help="包含牌谱 JSON 的文件夹路径")
    ap.add_argument("-p", "--pattern", default="*.json", help="文件匹配模式（默认 *.json）")
    ap.add_argument("-r", "--recursive", action="store_true", help="是否递归子目录")
    ap.add_argument("-o", "--output", default=None, help="输出结果到文件（不指定则打印到 stdout）")
    ap.add_argument("-f", "--format", default="json", choices=["json", "table"],
                    help="输出格式: json 或 table（默认 json）")
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    files = scan_files(folder, args.pattern, args.recursive)

    if not files:
        print(f"在 {folder} 中未找到匹配 {args.pattern} 的文件", file=sys.stderr)
        return

    print(f"正在处理 {len(files)} 个文件...", file=sys.stderr)

    # 处理所有文件
    results = []
    round_counts = []  # 记录每场游戏的小局数
    errors = []

    for fp in sorted(files):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            summary = summarize_log(data)
            results.append(summary)
            # 记录这场游戏的小局数
            round_counts.append(len(data.get("log", [])))
        except Exception as ex:
            errors.append({"file": fp, "error": str(ex)})
            print(f"处理失败: {fp} - {ex}", file=sys.stderr)

    print(f"成功处理 {len(results)} 个文件，失败 {len(errors)} 个", file=sys.stderr)

    # 计算玩家统计
    stats = calculate_player_stats(results, round_counts)
    ls = list(stats.items())
    print(ls)

    # 输出结果
    if args.format == "table":
        output_text = format_as_table(stats)
    else:
        # 按对局数降序排序
        sorted_stats = dict(sorted(stats.items(), key=lambda x: (-x[1]["games"], x[0]) if x[0] != '_league_average' else (0, '_league_average')))
        output_text = json.dumps({
            "folder": folder,
            "files_processed": len(files),
            "files_succeeded": len(results),
            "files_failed": len(errors),
            "player_stats": sorted_stats,
        }, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"已写入：{os.path.abspath(args.output)}", file=sys.stderr)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
