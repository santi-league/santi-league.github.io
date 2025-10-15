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
from typing import Any, Dict, List, Tuple

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
    """提取手役（排除宝牌、一发、里宝）"""
    yaku_names = extract_yaku_names(info_list)
    excluded = {'Dora', 'Ura Dora', 'Red Five', 'Ippatsu', 'One Shot', '一发'}
    return [y for y in yaku_names if y not in excluded]

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
def count_cpk_r(mark_array: List[Any]) -> Tuple[int, int, int, int]:
    c = p = k = r = 0
    for x in mark_array:
        if isinstance(x, str):
            c += x.count('c')
            p += x.count('p')
            k += x.count('k')
            r += x.count('r')
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
            "other_win_points_sum": 0,   # 新增：其他和牌打点总和
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

        # 从 hand[4] 到 hand[-2]（hand[-1] 为结算），按东→南→西→北轮转归属
        for idx in range(4, len(hand)-1):
            arr = hand[idx]
            if not isinstance(arr, list):
                continue
            seat = (east + (idx - 4)) % 4
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

                # 判断和牌类型（互斥分类）：优先级：立直 > 副露 > 其他
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
                # 其他和牌（既没有立直也没有副露，如门清荣和）
                else:
                    per[w]["other_win_points_sum"] += total_pts

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

    # 写入素点与顺位
    sc = v23.get("sc", [])
    finals = [int(sc[2*i]) for i in range(N)] if isinstance(sc, list) and len(sc) >= 2*N else [0]*N
    for i in range(N):
        per[i]["final_points"] = finals[i]

    order = sorted(range(N), key=lambda i: (-finals[i], i))
    prev = None
    current_rank = 0
    for pos, i in enumerate(order):
        if prev is None or finals[i] < prev:
            current_rank = pos + 1
            prev = finals[i]
        per[i]["rank"] = current_rank

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

