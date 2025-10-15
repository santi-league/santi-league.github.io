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


def calculate_tenhou_r_value(rank: int, games_played: int, player_r: float, table_avg_r: float) -> float:
    """
    计算天凤R值变动

    参数:
    - rank: 名次 (1-4)
    - games_played: 已进行的游戏数
    - player_r: 玩家当前R值
    - table_avg_r: 桌平均R值

    返回: R值变动量
    """
    # 对战结果（段位戦4人打ち）
    rank_points = {1: 30, 2: 10, 3: -10, 4: -30}
    result = rank_points.get(rank, 0)

    # 试合数补正
    if games_played < 400:
        games_correction = 1 - games_played * 0.002
    else:
        games_correction = 0.2

    # 补正值：(桌平均R - 自己的R) / 40
    # 桌平均R如果低于1500则按1500计算
    table_avg_r_corrected = max(table_avg_r, 1500)
    correction_value = (table_avg_r_corrected - player_r) / 40

    # スケーリング係数（段位戦）
    scaling = 1.0

    # R值变动 = 试合数补正 × (对战结果 + 补正值) × スケーリング係数
    r_change = games_correction * (result + correction_value) * scaling

    # 小数第3位以下切り上げ（向上取整到小数点后2位）
    import math
    r_change = math.ceil(r_change * 100) / 100

    return r_change


def calculate_player_stats(batch_results: List[Dict[str, Any]], round_counts: List[int]) -> Dict[str, Dict[str, Any]]:
    """
    基于批量统计结果，计算每个玩家的综合数据

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
        "other_win_points_sum": 0,   # 其他和牌打点总和（门清荣和等）
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
    })

    # 天凤R值追踪：{玩家名: 当前R值}
    player_r_values = defaultdict(lambda: 1500.0)

    # 汇总所有对局数据
    for idx, result in enumerate(batch_results):
        summary = result.get("summary", [])
        # 获取这场游戏的小局数
        rounds_in_game = round_counts[idx] if idx < len(round_counts) else 0

        # 计算这一局的桌平均R值（在游戏开始前）
        table_players = [p.get("name", "") for p in summary if p.get("name")]
        table_avg_r = sum(player_r_values[name] for name in table_players) / len(table_players) if table_players else 1500.0

        for player_stat in summary:
            name = player_stat.get("name", "")
            if not name:
                continue

            pd = player_data[name]
            pd["games"] += 1
            pd["total_rounds"] += rounds_in_game
            pd["furo_hands"] += player_stat.get("furo_hands", 0)
            pd["riichi_hands"] += player_stat.get("riichi_hands", 0)
            pd["win_hands"] += player_stat.get("win_hands", 0)
            pd["riichi_win_hands"] += player_stat.get("riichi_win_hands", 0)
            pd["win_points_sum"] += player_stat.get("win_points_sum", 0)
            pd["riichi_win_points_sum"] += player_stat.get("riichi_win_points_sum", 0)
            pd["furo_win_points_sum"] += player_stat.get("furo_win_points_sum", 0)
            pd["other_win_points_sum"] += player_stat.get("other_win_points_sum", 0)
            pd["deal_in_hands"] += player_stat.get("deal_in_hands", 0)
            pd["deal_in_points_sum"] += player_stat.get("deal_in_points_sum", 0)
            pd["furo_then_win_hands"] += player_stat.get("furo_then_win_hands", 0)
            pd["furo_then_deal_in_hands"] += player_stat.get("furo_then_deal_in_hands", 0)
            pd["riichi_then_deal_in_hands"] += player_stat.get("riichi_then_deal_in_hands", 0)
            pd["ippatsu_hands"] += player_stat.get("ippatsu_hands", 0)
            pd["ura_hands"] += player_stat.get("ura_hands", 0)
            pd["rank_sum"] += player_stat.get("rank", 0)
            pd["final_points_sum"] += player_stat.get("final_points", 0)

            # 计算总点数：(终局点数 - 25000) + 马点
            final_points = player_stat.get("final_points", 25000)
            rank = player_stat.get("rank", 4)

            # 马点：1位+45000, 2位+5000, 3位-15000, 4位-35000
            uma_points = {1: 45000, 2: 5000, 3: -15000, 4: -35000}
            score = (final_points - 25000) + uma_points.get(rank, 0)
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

            # 天凤R值计算
            games_before = pd["games"]  # 这是进行这局游戏前的游戏数
            current_r = player_r_values[name]
            r_change = calculate_tenhou_r_value(rank, games_before, current_r, table_avg_r)
            player_r_values[name] += r_change
            pd["current_r"] = player_r_values[name]

            # 累加顺位用于计算平均
            pd["total_rank"] += rank

            # 流局听牌统计
            pd["ryuukyoku_hands"] += player_stat.get("ryuukyoku_hands", 0)
            pd["ryuukyoku_tenpai"] += player_stat.get("ryuukyoku_tenpai", 0)
            pd["riichi_ryuukyoku"] += player_stat.get("riichi_ryuukyoku", 0)
            pd["furo_ryuukyoku"] += player_stat.get("furo_ryuukyoku", 0)

            # 放铳目标统计
            targets = player_stat.get("deal_in_targets", {})
            for target, count in targets.items():
                if count > 0:
                    pd["deal_in_targets"][target] += count

            # 放铳详细点数统计
            deal_in_detail = player_stat.get("deal_in_points_detail", {})
            for target, points_list in deal_in_detail.items():
                if points_list:
                    pd["deal_in_points_to_players"][target].extend(points_list)

            # 手役统计（合并役牌）
            yaku_count = player_stat.get("yaku_count", {})
            yakuhai_types = {"White Dragon", "Green Dragon", "Red Dragon", "Seat Wind", "Prevailing Wind", "Prevalent Wind"}
            for yaku, count in yaku_count.items():
                if yaku in yakuhai_types:
                    pd["yaku_count"]["役牌"] += count
                else:
                    pd["yaku_count"][yaku] += count

    # 计算百分比和平均值
    stats = {}
    for name, pd in player_data.items():
        games = pd["games"]
        total_rounds = pd["total_rounds"]
        if games == 0:
            continue

        win_hands = pd["win_hands"]
        riichi_win_hands = pd["riichi_win_hands"]
        deal_in_hands = pd["deal_in_hands"]
        furo_hands = pd["furo_hands"]
        riichi_hands = pd["riichi_hands"]

        stats[name] = {
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
            "other_win_hands": win_hands - riichi_win_hands - pd["furo_then_win_hands"],
            "avg_other_win_points": round(pd["other_win_points_sum"] / (win_hands - riichi_win_hands - pd["furo_then_win_hands"]), 0) if (win_hands - riichi_win_hands - pd["furo_then_win_hands"]) > 0 else 0,
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
        }

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
        # 计算其他和牌数据（门清荣和等）
        riichi_win_hands = data['riichi_win_hands']
        furo_then_win_hands = data['furo_then_win_hands']
        other_win_hands = data['other_win_hands']

        lines.append(f"  和了: {data['win_hands']} 局 ({data['win_rate']}%), 平均打点: {data['avg_win_points']:.0f}")
        lines.append(f"    立直和了: {riichi_win_hands} 局 (平均{data['avg_riichi_win_points']:.0f}点), 一发: {data['ippatsu_hands']} 局 ({data['ippatsu_rate']}%), 里宝: {data['ura_hands']} 局 ({data['ura_rate']}%)")
        lines.append(f"    副露和了: {furo_then_win_hands} 局 (平均{data['avg_furo_win_points']:.0f}点)")
        if other_win_hands > 0:
            lines.append(f"    其他和了: {other_win_hands} 局 (平均{data['avg_other_win_points']:.0f}点)")
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

    # 输出结果
    if args.format == "table":
        output_text = format_as_table(stats)
    else:
        # 按对局数降序排序
        sorted_stats = dict(sorted(stats.items(), key=lambda x: (-x[1]["games"], x[0])))
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
