# -*- coding: utf-8 -*-
"""
Mahjong Soul v2.3 牌谱 → 对局总结 JSON

统计项目（按玩家）：
- furo_hands, riichi_hands, win_hands, win_points_sum(含本场/供托),
- deal_in_targets, furo_then_win_hands, furo_then_deal_in_hands,
- rank, final_points, deal_in_hands, deal_in_points_sum,
- riichi_then_deal_in_hands, ippatsu_hands, ura_hands

用法：
  python summarize_v23.py path/to/v23.json
  # 或
  cat v23.json | python summarize_v23.py
"""

import sys
import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

# 导入手牌分析模块
from mahjong_hand_analyzer import HandTracker

# ---------- 役/点数解析 ----------
YAKU_LINE   = re.compile(r'^\d+符\d+飜')
RE_DORA     = re.compile(r'Dora\((\d+)飜\)')
RE_URADORA  = re.compile(r'Ura Dora\((\d+)飜\)')
RE_REDFIVE  = re.compile(r'Red Five\((\d+)飜\)')
PTS_RE      = re.compile(r'(\d+)(?:-(\d+))?点')  # "18000点" or "700-1300点"

IPPATSU_KEYWORDS = ("Ippatsu", "One Shot", "一发")

def extract_yaku_names(info_list: List[Any]) -> List[str]:
    """提取所有役名（包括宝牌、一发等）"""
    names = []
    for x in info_list:
        if not isinstance(x, str):
            continue
        if YAKU_LINE.match(x) or x.endswith('点'):
            continue
        names.append(re.sub(r'\(\d+飜\)$', '', x))
    return names

def extract_hand_yaku(info_list: List[Any]) -> List[str]:
    """提取手役（排除宝牌、一发、里宝、点数等级）"""
    yaku_names = extract_yaku_names(info_list)
    # 排除：宝牌、一发、里宝、以及点数等级（满贯、跳满等）
    excluded = {'Dora', 'Ura Dora', 'Red Five', 'Ippatsu', 'One Shot', '一发'}
    # 过滤掉包含点数等级关键词的项
    point_levels = ['Mangan', 'Haneman', 'Baiman', 'Sanbaiman', 'Yakuman',
                   '满贯', '跳满', '倍满', '三倍满', '役满']

    result = []
    for yaku in yaku_names:
        if yaku in excluded:
            continue
        # 检查是否包含点数等级关键词
        if any(level in yaku for level in point_levels):
            continue
        result.append(yaku)
    return result

def ura_han_total(info_list: List[Any]) -> int:
    total = 0
    for s in info_list:
        if isinstance(s, str):
            m = RE_URADORA.search(s)
            if m:
                total += int(m.group(1))
    return total

def has_ippatsu(info_list: List[Any]) -> bool:
    for s in info_list:
        if isinstance(s, str) and any(k in s for k in IPPATSU_KEYWORDS):
            return True
    return False

def parse_win_points_total(info_list: List[Any], is_tsumo: bool, winner_is_dealer: bool) -> int:
    """
    基于役行里的“...点”解析和牌基本打点（不含本场/供托）：
      - "a-b点"（常见于非庄自摸） → 2*a + b
      - 单值 "x点"：自摸（通常庄）按 3*x；荣和按 x
    未解析则返回 0（不从分差逆推，避免混入本场/供托/包牌等）。
    """
    m = None
    for s in info_list:
        if isinstance(s, str):
            m = PTS_RE.search(s)
            if m:
                break
    if not m:
        return 0
    a = int(m.group(1))
    b = m.group(2)
    if b is not None:
        return 2 * a + int(b)
    return 3 * a if is_tsumo else a

# ---------- c/p/k/r 记号 ----------
def _extract_furo_tag(token: str) -> Optional[str]:
    """识别副露标记字符，忽略如 Ryuukyoku 等非副露字符串"""
    if not isinstance(token, str):
        return None
    if token == 'Ryuukyoku':
        return None
    if not any(ch.isdigit() for ch in token):
        return None
    for ch in token:
        if ch in ('c', 'p', 'k', 'm'):
            return ch
    return None


def count_cpk_r(mark_array: List[Any]) -> Tuple[int, int, int, int]:
    c = p = k = r = 0
    for x in mark_array:
        if not isinstance(x, str):
            continue
        tag = _extract_furo_tag(x)
        if tag == 'c':
            c += 1
        elif tag == 'p':
            p += 1
        elif tag in ('k', 'm'):
            k += 1
        if x.startswith('r'):
            r += 1
    return c, p, k, r

# ---------- 本场/供托分配 ----------
def assign_pots_to_winners(
    winners: List[int],
    east_seat: int,
    losers: List[int],
    honba: int,
    kyotaku: int,
    policy: str = "first_from_loser",  # or "even"
) -> Dict[int, Tuple[int, int]]:
    """
    返回 {winner_seat: (kyotaku_pts, honba_pts)}
    - 供托：1000 * kyotaku
    - 本场：300  * honba
    策略：
      * "first_from_loser": 荣和且有放铳者时，把全部本场/供托给“从放铳者起逆时针最近”的赢家
      * "even": 在所有赢家间均分，余数从（有放铳者则自放铳者，否则自东）起顺序 +1
    """
    res = {w: (0, 0) for w in winners}
    if not winners:
        return res

    total_ky = 1000 * int(kyotaku or 0)
    total_hn = 300  * int(honba or 0)

    if policy == "first_from_loser" and len(losers) == 1 and winners:
        L = losers[0]
        order = sorted(winners, key=lambda w: (w - L) % 4)
        res[order[0]] = (total_ky, total_hn)
        return res

    n = len(winners)
    base_ky, rem_ky = divmod(total_ky, n)
    base_hn, rem_hn = divmod(total_hn, n)
    start = losers[0] if losers else east_seat
    order = sorted(winners, key=lambda w: (w - start) % 4)
    for i, w in enumerate(order):
        res[w] = (base_ky + (1 if i < rem_ky else 0),
                  base_hn + (1 if i < rem_hn else 0))
    return res

# ---------- 主统计 ----------
def summarize_log(v23: Dict[str, Any]) -> Dict[str, Any]:
    names = v23.get("name", ["P0","P1","P2","P3"])
    N = 4

    per = []
    for i in range(N):
        per.append({
            "name": names[i] if i < len(names) else f"P{i}",
            # —— 附露/立直/和牌/点棒 ——
            "furo_hands": 0,
            "riichi_hands": 0,
            "win_hands": 0,
            "win_points_sum": 0,
            "riichi_win_hands": 0,  # 新增：立直后和牌次数
            "riichi_win_points_sum": 0,  # 新增：立直和牌打点总和
            "furo_win_points_sum": 0,    # 新增：副露和牌打点总和
            "dama_win_hands": 0,         # 新增：默听和牌次数（门清荣和）
            "dama_win_points_sum": 0,    # 新增：默听和牌打点总和
            "tsumo_only_win_hands": 0,   # 新增：仅自摸和牌次数
            "tsumo_only_win_points_sum": 0,  # 新增：仅自摸和牌打点总和
            "deal_in_targets": { n: 0 for n in names },
            "deal_in_points_detail": { n: [] for n in names },  # 新增：记录每次放铳的点数
            "furo_then_win_hands": 0,
            "furo_then_deal_in_hands": 0,
            # —— 新增：顺位/素点 与 放铳扩展 ——
            "rank": None,
            "final_points": 0,
            "deal_in_hands": 0,
            "deal_in_points_sum": 0,
            "riichi_then_deal_in_hands": 0,
            "ippatsu_hands": 0,
            "ura_hands": 0,
            # —— 新增：流局听牌统计 ——
            "ryuukyoku_hands": 0,        # 流局总次数
            "ryuukyoku_tenpai": 0,       # 流局听牌次数
            "riichi_ryuukyoku": 0,       # 立直后流局次数
            "furo_ryuukyoku": 0,         # 副露后流局次数
            # —— 新增：手役统计 ——
            "yaku_count": {},            # 各种手役的出现次数
            # —— 新增：默听状态统计（基于手牌追踪）——
            "dama_state_hands": 0,       # 进入默听状态的次数
            "dama_state_win": 0,         # 默听状态下和了
            "dama_state_deal_in": 0,     # 默听状态下放铳
            "dama_state_draw": 0,        # 默听状态下流局
            "dama_state_pass": 0,        # 默听状态下横移（别人和了）
        })

    for hand in v23.get("log", []):
        if not hand:
            continue

        # 当局东家 + 本场/供托
        header   = hand[0] if isinstance(hand[0], list) else [0,0,0]
        round_idx= int(header[0]) if header else 0
        east     = round_idx % 4
        honba    = int(header[1]) if len(header) > 1 else 0
        kyotaku  = int(header[2]) if len(header) > 2 else 0

        # 局内标记
        furo_flag   = [False]*N
        riichi_flag = [False]*N

        META_LIST_COUNT = 4
        PLAYER_BLOCK_SIZE = 3
        prevalent_wind = min(round_idx // 4 + 1, 4)

        player_blocks = []
        hand_trackers = [None] * N

        for seat in range(N):
            block = []
            block_start = META_LIST_COUNT + seat * PLAYER_BLOCK_SIZE
            for offset in range(PLAYER_BLOCK_SIZE):
                idx = block_start + offset
                if idx >= len(hand) - 1:
                    block.append([])
                    continue
                item = hand[idx]
                block.append(item if isinstance(item, list) else [])
            player_blocks.append(block)

            initial_hand_raw = block[0] if block else []
            initial_hand = [t for t in initial_hand_raw if isinstance(t, int)]
            if initial_hand:
                seat_wind = ((seat - east) % 4) + 1
                hand_trackers[seat] = HandTracker(
                    seat,
                    initial_hand,
                    seat_wind=seat_wind,
                    prevalent_wind=prevalent_wind
                )

        for seat in range(N):
            block = player_blocks[seat]
            tracker = hand_trackers[seat]

            # block[0] = initial hand (already processed)
            # block[1] = draw list (tiles drawn each turn)
            # block[2] = discard list (tiles discarded each turn, 60 = tsumogiri)
            draw_list = block[1] if len(block) > 1 else []
            discard_list = block[2] if len(block) > 2 else []

            # 处理手牌追踪
            if tracker is not None and isinstance(draw_list, list) and isinstance(discard_list, list):
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

            # 检查副露和立直标记（需要检查所有三个列表）
            for arr in block:
                if isinstance(arr, list):
                    c, p, k, r = count_cpk_r(arr)
                    if (c + p + k) > 0:
                        furo_flag[seat] = True
                    if r > 0:
                        riichi_flag[seat] = True

        # 结算
        result = hand[-1]
        if not (isinstance(result, list) and result):
            continue

        tag = result[0]
        deltas = result[1] if len(result) > 1 else None
        info_list = result[2] if len(result) > 2 else []

        winners: List[int] = []
        losers:  List[int] = []
        if isinstance(deltas, list) and len(deltas) == N:
            for i, dv in enumerate(deltas):
                if dv is None:
                    continue
                winners.append(i) if dv > 0 else None
                losers.append(i)  if dv < 0 else None

        if tag == "和了":
            is_tsumo = (len(winners) == 1 and len(losers) == 3)

            # ==== 新增：记录默听状态下的和了 ====
            for w in winners:
                if hand_trackers[w] is not None:
                    hand_trackers[w].record_win()

            # ==== 新增：记录默听状态下的放铳 ====
            for L in losers:
                if hand_trackers[L] is not None:
                    hand_trackers[L].record_deal_in()

            # ==== 新增：记录默听状态下的横移 ====
            for i in range(N):
                if i not in winners and i not in losers:
                    if hand_trackers[i] is not None:
                        hand_trackers[i].record_pass()

            # 若赢家役中出现 Riichi，也视为其本局立直
            yaku_names = extract_yaku_names(info_list)
            # if any("Riichi" in s for s in info_list) or ("Riichi" in yaku_names):
            if "Riichi" in yaku_names:
                for w in winners:
                    riichi_flag[w] = True

            # 一发/里宝（整局一次计入）
            _ipp = has_ippatsu(info_list)
            _ura = ura_han_total(info_list)

            # 分配本场/供托并累加赢家打点
            pots = assign_pots_to_winners(
                winners=winners,
                east_seat=east,
                losers=losers if not is_tsumo else [],
                honba=honba,
                kyotaku=kyotaku,
                policy="first_from_loser"  # 改为 "even" 可均分
            )

            # 提取手役（排除宝牌、一发、里宝）
            hand_yaku_list = extract_hand_yaku(info_list)

            for w in winners:
                per[w]["win_hands"] += 1
                base_pts = parse_win_points_total(info_list, is_tsumo, winner_is_dealer=(w==east))
                add_ky, add_hn = pots.get(w, (0,0))
                total_pts = base_pts + add_ky + add_hn
                per[w]["win_points_sum"] += total_pts

                # 判断和牌类型（互斥分类）：优先级：立直 > 副露 > 默听/仅自摸
                is_riichi_win = riichi_flag[w]
                is_furo_win = furo_flag[w]

                # 立直后和牌统计（一发和里宝只在立直和牌时可能出现）
                # 优先级最高：如果立直了，无论是否副露，都算立直和了
                if is_riichi_win:
                    per[w]["riichi_win_hands"] += 1
                    per[w]["riichi_win_points_sum"] += total_pts
                    if _ipp:
                        per[w]["ippatsu_hands"] += 1
                    if _ura > 0:
                        per[w]["ura_hands"] += 1
                # 副露和牌统计（没有立直的情况下）
                elif is_furo_win:
                    per[w]["furo_then_win_hands"] += 1
                    per[w]["furo_win_points_sum"] += total_pts
                # 门清和牌（既没有立直也没有副露）
                else:
                    # 检查手役中是否有除了"门前清自摸和"之外的其他役
                    # 手役已经排除了宝牌、一发、里宝
                    non_tsumo_yaku = [y for y in hand_yaku_list if y not in ['Fully Concealed Hand', '门前清自摸和', '门清自摸']]

                    if non_tsumo_yaku:
                        # 默听：有其他役，可以荣和或自摸
                        per[w]["dama_win_hands"] += 1
                        per[w]["dama_win_points_sum"] += total_pts
                    else:
                        # 仅自摸：只有门前清自摸和这个役
                        per[w]["tsumo_only_win_hands"] += 1
                        per[w]["tsumo_only_win_points_sum"] += total_pts

                # 记录手役
                for yaku in hand_yaku_list:
                    if yaku not in per[w]["yaku_count"]:
                        per[w]["yaku_count"][yaku] = 0
                    per[w]["yaku_count"][yaku] += 1

            # 放铳者：目标统计 + 放铳局数/总失点 + 立直后放铳 + 副露后放铳 + 详细点数
            if not is_tsumo and losers:
                for L in losers:
                    loss_points = 0
                    if isinstance(deltas, list) and deltas[L] < 0:
                        loss_points = -int(deltas[L])
                        per[L]["deal_in_hands"] += 1
                        per[L]["deal_in_points_sum"] += loss_points
                    for W in winners:
                        if W == L:
                            continue
                        tgt = per[W]["name"]
                        per[L]["deal_in_targets"][tgt] += 1
                        # 记录放铳给该玩家的详细点数
                        per[L]["deal_in_points_detail"][tgt].append(loss_points)
                    if riichi_flag[L]:
                        per[L]["riichi_then_deal_in_hands"] += 1
                    if furo_flag[L]:
                        per[L]["furo_then_deal_in_hands"] += 1

        # 流局听牌统计
        if tag == "Ryuukyoku" or tag == "流局":
            # ==== 新增：记录默听状态下的流局 ====
            for i in range(N):
                if hand_trackers[i] is not None:
                    hand_trackers[i].record_draw()

            # deltas 中正数表示听牌收入，负数表示不听罚符
            if isinstance(deltas, list) and len(deltas) == N:
                for i, dv in enumerate(deltas):
                    per[i]["ryuukyoku_hands"] += 1
                    if dv is not None and dv >= 0:  # 听牌（包括0点的情况）
                        per[i]["ryuukyoku_tenpai"] += 1
                    # 立直后流局统计
                    if riichi_flag[i]:
                        per[i]["riichi_ryuukyoku"] += 1
                    # 副露后流局统计
                    if furo_flag[i]:
                        per[i]["furo_ryuukyoku"] += 1

        # 本局是否计入"附露局/立直局"
        for i in range(N):
            if furo_flag[i]:
                per[i]["furo_hands"] += 1
            if riichi_flag[i]:
                per[i]["riichi_hands"] += 1

        # ==== 新增：汇总本局的默听状态统计 ====
        for i in range(N):
            if hand_trackers[i] is not None:
                stats = hand_trackers[i].get_stats()
                per[i]["dama_state_hands"] += stats['dama_hands']
                per[i]["dama_state_win"] += stats['dama_win']
                per[i]["dama_state_deal_in"] += stats['dama_deal_in']
                per[i]["dama_state_draw"] += stats['dama_draw']
                per[i]["dama_state_pass"] += stats['dama_pass']

    # 写入素点与顺位
    sc = v23.get("sc", [])
    finals = [int(sc[2*i]) for i in range(N)] if isinstance(sc, list) and len(sc) >= 2*N else [0]*N
    for i in range(N):
        per[i]["final_points"] = finals[i]

    # 计算名次和平均马点
    order = sorted(range(N), key=lambda i: (-finals[i], i))
    prev = None
    current_rank = 0

    # 先计算每个人的名次
    for pos, i in enumerate(order):
        if prev is None or finals[i] < prev:
            current_rank = pos + 1
            prev = finals[i]
        per[i]["rank"] = current_rank

    # 计算平均马点（M-League uma配置）
    uma_config = {1: 45000, 2: 5000, 3: -15000, 4: -35000}

    # 找出同分组，计算平均uma
    score_groups = {}  # {分数: [玩家索引列表]}
    for i in range(N):
        score = finals[i]
        if score not in score_groups:
            score_groups[score] = []
        score_groups[score].append(i)

    # 为每个同分组计算平均uma
    for score, group in score_groups.items():
        if len(group) == 1:
            # 单独一人，直接按名次拿uma
            i = group[0]
            rank = per[i]["rank"]
            per[i]["avg_uma"] = uma_config.get(rank, 0)
        else:
            # 多人同分，平分这些名次对应的uma
            ranks = [per[i]["rank"] for i in group]
            min_rank = min(ranks)
            max_rank = min_rank + len(group) - 1

            # 计算这几个名次的uma总和
            total_uma = sum(uma_config.get(r, 0) for r in range(min_rank, max_rank + 1))
            avg_uma = total_uma / len(group)

            # 分配给每个人
            for i in group:
                per[i]["avg_uma"] = avg_uma

    return {
        "ref": v23.get("ref"),
        "title": v23.get("title", ["",""])[0],
        "start_time": v23.get("title", ["",""])[1],
        "players": names,
        "summary": per
    }

# ---------- CLI ----------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("-","--"):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = summarize_log(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
