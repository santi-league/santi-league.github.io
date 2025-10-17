# -*- coding: utf-8 -*-
"""
麻将手牌分析模块
提供手牌追踪、向听数计算、听牌判断和手役检测功能
"""

from typing import List, Tuple, Optional, Set, Dict, Any
from collections import Counter


# ==================== 牌编码解码 ====================

def decode_tile(tile_num: int) -> Tuple[str, int]:
    """
    将牌谱中的数字编码转换为麻将牌
    编码规则：
    - 11-19: 1-9万 (m)
    - 21-29: 1-9条 (p)
    - 31-39: 1-9筒 (s)
    - 41-47: 东南西北白发中 (z1-z7)

    返回: (suit, rank)
    - suit: 'm'(万), 'p'(条), 's'(筒), 'z'(字牌)
    - rank: 1-9 (数牌) 或 1-7 (字牌)
    """
    if tile_num == 0 or tile_num >= 60:
        return ('unknown', 0)

    tens = tile_num // 10
    ones = tile_num % 10

    if tens == 1 and 1 <= ones <= 9:
        return ('m', ones)
    elif tens == 2 and 1 <= ones <= 9:
        return ('p', ones)
    elif tens == 3 and 1 <= ones <= 9:
        return ('s', ones)
    elif tens == 4 and 1 <= ones <= 7:
        return ('z', ones)
    else:
        return ('unknown', 0)


def encode_tile(suit: str, rank: int) -> int:
    """将麻将牌转换回数字编码"""
    suit_map = {'m': 10, 'p': 20, 's': 30, 'z': 40}
    if suit in suit_map:
        return suit_map[suit] + rank
    return 0


def tiles_to_string(tiles: List[int]) -> str:
    """将牌列表转换为可读字符串，用于调试"""
    decoded = [decode_tile(t) for t in tiles]
    result = []
    for suit_name, suit_char in [('m', '万'), ('p', '条'), ('s', '筒'), ('z', '字')]:
        suit_tiles = sorted([rank for s, rank in decoded if s == suit_name])
        if suit_tiles:
            result.append(''.join(map(str, suit_tiles)) + suit_char)
    return ' '.join(result)


# ==================== 向听数计算 ====================

def calculate_shanten(tiles: List[int]) -> int:
    """
    计算向听数（距离听牌还差几张）
    返回: -1=和了, 0=听牌, 1=一向听, 2=二向听, ...
    """
    if len(tiles) not in [13, 14]:
        return 99  # 非法手牌

    # 解码牌
    decoded = [decode_tile(t) for t in tiles]

    # 过滤掉unknown牌
    decoded = [(s, r) for s, r in decoded if s != 'unknown']

    if len(decoded) not in [13, 14]:
        return 99

    # 转换为34牌编码（0-33）
    tiles_34 = _convert_to_34_array(decoded)

    # 尝试标准型（4面子1雀头）
    standard_shanten = _calculate_standard_shanten_34(tiles_34)

    # 尝试七对子型
    pairs_shanten = _calculate_pairs_shanten_34(tiles_34)

    # 尝试国士无双型
    kokushi_shanten = _calculate_kokushi_shanten_34(tiles_34)

    return min(standard_shanten, pairs_shanten, kokushi_shanten)


def _convert_to_34_array(decoded: List[Tuple[str, int]]) -> List[int]:
    """
    将牌转换为34种类编码数组
    0-8: 1-9万, 9-17: 1-9条, 18-26: 1-9筒, 27-33: 东南西北白发中
    返回长度为34的数组，每个元素表示该种牌有几张
    """
    tiles_34 = [0] * 34

    for suit, rank in decoded:
        if suit == 'm':
            tiles_34[rank - 1] += 1
        elif suit == 'p':
            tiles_34[9 + rank - 1] += 1
        elif suit == 's':
            tiles_34[18 + rank - 1] += 1
        elif suit == 'z':
            tiles_34[27 + rank - 1] += 1

    return tiles_34


def _calculate_standard_shanten_34(tiles_34: List[int]) -> int:
    """
    计算标准型向听数（4面子1雀头）
    使用递归算法，参考天凤向听数计算
    """
    def remove_mentsu(tiles: List[int]) -> Tuple[int, int, int]:
        """移除所有面子，返回(面子数, 搭子数, 对子数)"""
        mentsu_count = 0
        tatsu_count = 0
        pair_count = 0

        result = _remove_mentsu_recursive(tiles[:], 0, mentsu_count, tatsu_count, pair_count)
        return result

    def _remove_mentsu_recursive(tiles: List[int], pos: int, mentsu: int, tatsu: int, pair: int) -> Tuple[int, int, int]:
        """递归移除面子"""
        # 跳过数量为0的牌
        while pos < 34 and tiles[pos] == 0:
            pos += 1

        if pos >= 34:
            return (mentsu, tatsu, pair)

        results = []
        current = tiles[pos]

        # 尝试不取任何组合，直接跳过
        results.append(_remove_mentsu_recursive(tiles, pos + 1, mentsu, tatsu, pair))

        # 尝试取刻子
        if current >= 3:
            tiles[pos] -= 3
            results.append(_remove_mentsu_recursive(tiles, pos, mentsu + 1, tatsu, pair))
            tiles[pos] += 3

        # 尝试取顺子（只能是数牌：0-8, 9-17, 18-26）
        if pos % 9 <= 6 and pos < 27:  # 不能是字牌，且不能是8、9（无法组成顺子）
            if tiles[pos] >= 1 and tiles[pos + 1] >= 1 and tiles[pos + 2] >= 1:
                tiles[pos] -= 1
                tiles[pos + 1] -= 1
                tiles[pos + 2] -= 1
                results.append(_remove_mentsu_recursive(tiles, pos, mentsu + 1, tatsu, pair))
                tiles[pos] += 1
                tiles[pos + 1] += 1
                tiles[pos + 2] += 1

        # 尝试取对子
        if current >= 2:
            tiles[pos] -= 2
            results.append(_remove_mentsu_recursive(tiles, pos + 1, mentsu, tatsu, pair + 1))
            tiles[pos] += 2

        # 尝试取搭子（两张的组合）
        # 对子搭子
        if current >= 2:
            tiles[pos] -= 2
            results.append(_remove_mentsu_recursive(tiles, pos + 1, mentsu, tatsu + 1, pair))
            tiles[pos] += 2

        # 两面/嵌张搭子（只能是数牌）
        if pos % 9 <= 7 and pos < 27:
            if tiles[pos] >= 1 and tiles[pos + 1] >= 1:
                tiles[pos] -= 1
                tiles[pos + 1] -= 1
                results.append(_remove_mentsu_recursive(tiles, pos, mentsu, tatsu + 1, pair))
                tiles[pos] += 1
                tiles[pos + 1] += 1

        if pos % 9 <= 6 and pos < 27:
            if tiles[pos] >= 1 and tiles[pos + 2] >= 1:
                tiles[pos] -= 1
                tiles[pos + 2] -= 1
                results.append(_remove_mentsu_recursive(tiles, pos, mentsu, tatsu + 1, pair))
                tiles[pos] += 1
                tiles[pos + 2] += 1

        # 返回最优结果（面子数最多，搭子数次之，对子数再次）
        return max(results, key=lambda x: (x[0], x[1], x[2]))

    # 计算最优组合
    best_mentsu, best_tatsu, best_pair = remove_mentsu(tiles_34)

    # 计算向听数
    # 有雀头的情况
    if best_pair > 0:
        shanten_with_pair = 8 - best_mentsu * 2 - best_tatsu - 1
    else:
        shanten_with_pair = 99

    # 无雀头的情况
    shanten_no_pair = 8 - best_mentsu * 2 - best_tatsu

    return min(shanten_with_pair, shanten_no_pair)


def _calculate_pairs_shanten_34(tiles_34: List[int]) -> int:
    """计算七对子向听数"""
    pairs = 0
    kinds = 0

    for count in tiles_34:
        if count >= 2:
            pairs += 1
            kinds += 1
        elif count == 1:
            kinds += 1

    # 七对子向听数 = 6 - 对子数
    shanten = 6 - pairs

    # 如果不同种类的牌少于7种，无法组成七对子
    if kinds < 7:
        return 99  # 不可能

    return shanten


def _calculate_kokushi_shanten_34(tiles_34: List[int]) -> int:
    """计算国士无双向听数"""
    # 国士牌: 0,8(1m,9m), 9,17(1p,9p), 18,26(1s,9s), 27-33(东南西北白发中)
    yaochu_indices = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]

    yaochu_kinds = 0
    has_pair = False

    for idx in yaochu_indices:
        if tiles_34[idx] >= 1:
            yaochu_kinds += 1
        if tiles_34[idx] >= 2:
            has_pair = True

    # 国士向听数 = 13 - 幺九种类数 - (是否有对子)
    shanten = 13 - yaochu_kinds - (1 if has_pair else 0)

    return shanten


def is_tenpai(tiles: List[int]) -> bool:
    """判断是否听牌"""
    return calculate_shanten(tiles) == 0


# ==================== 手役检测 ====================

def detect_yaku(tiles: List[int], furo_groups: List = None, is_riichi: bool = False,
                seat_wind: int = 1, prevalent_wind: int = 1) -> List[str]:
    """
    检测手牌中可能的手役（不考虑宝牌、一发、里宝等）

    参数:
    - tiles: 手牌（13张）
    - furo_groups: 副露组（如果有）
    - is_riichi: 是否立直
    - seat_wind: 自风 (1=东, 2=南, 3=西, 4=北)
    - prevalent_wind: 场风 (1=东, 2=南, 3=西, 4=北)

    返回: 可能的手役名称列表

    注意：这个函数检测的是在听牌状态下，如果和牌可能拥有的役
    不包括：立直、一发、里宝、宝牌、岭上开花、抢杠、海底等和牌时才能确定的役

    这里只检测"确定的役"，即无论听什么牌和了都一定有的役
    """
    if furo_groups is None:
        furo_groups = []

    yaku_list = []

    # 如果有副露，不能是门清役
    is_menzen = len(furo_groups) == 0

    # 转换为34编码
    decoded = [decode_tile(t) for t in tiles if decode_tile(t)[0] != 'unknown']
    tiles_34 = _convert_to_34_array(decoded)

    # 统计各花色
    m_tiles = [i for i in range(0, 9) if tiles_34[i] > 0]
    p_tiles = [i for i in range(9, 18) if tiles_34[i] > 0]
    s_tiles = [i for i in range(18, 27) if tiles_34[i] > 0]
    z_tiles = [i for i in range(27, 34) if tiles_34[i] > 0]

    has_m = len(m_tiles) > 0
    has_p = len(p_tiles) > 0
    has_s = len(s_tiles) > 0
    has_z = len(z_tiles) > 0

    num_suits = sum([has_m, has_p, has_s])
    total_tiles = sum(tiles_34)

    # === 检测确定的役种 ===

    # 七对子（听牌时就能确定）
    pairs = sum(1 for count in tiles_34 if count >= 2)
    if pairs == 6 and total_tiles == 13:
        # 如果已经有6对，那就是七对子听牌
        yaku_list.append("Seven Pairs")
        return yaku_list  # 七对子不能和其他役复合

    # 清一色/混一色
    if num_suits == 1 and (has_m or has_p or has_s):
        if not has_z:
            yaku_list.append("Full Flush")  # 清一色
        else:
            yaku_list.append("Half Flush")  # 混一色

    # 断幺九（全是2-8的数牌）
    if not has_z:
        all_simples = True
        for i in range(0, 9):
            if tiles_34[i] > 0 and i in [0, 8]:  # 1万或9万
                all_simples = False
        for i in range(9, 18):
            if tiles_34[i] > 0 and i in [9, 17]:  # 1条或9条
                all_simples = False
        for i in range(18, 27):
            if tiles_34[i] > 0 and i in [18, 26]:  # 1筒或9筒
                all_simples = False

        if all_simples and total_tiles == 13:
            yaku_list.append("All Simples")

    # 役牌：白发中
    if tiles_34[31] >= 3:  # 白 (z5)
        yaku_list.append("White Dragon")
    if tiles_34[32] >= 3:  # 发 (z6)
        yaku_list.append("Green Dragon")
    if tiles_34[33] >= 3:  # 中 (z7)
        yaku_list.append("Red Dragon")

    # 役牌：自风
    if seat_wind >= 1 and seat_wind <= 4:
        wind_idx = 27 + seat_wind - 1
        if tiles_34[wind_idx] >= 3:
            yaku_list.append("Seat Wind")

    # 役牌：场风
    if prevalent_wind >= 1 and prevalent_wind <= 4:
        wind_idx = 27 + prevalent_wind - 1
        if tiles_34[wind_idx] >= 3:
            yaku_list.append("Prevalent Wind")

    # 对对和（4个刻子+1个雀头，听牌时刻子数>=3）
    triplets = sum(1 for count in tiles_34 if count >= 3)
    if triplets >= 3:
        yaku_list.append("All Triplets")

    # 三暗刻（门清时，已有3个暗刻）
    if is_menzen and triplets >= 3:
        yaku_list.append("Three Concealed Triplets")

    # 混全带幺九（每个面子和雀头都有幺九牌）
    # 简化检测：略

    # 纯全带幺九（每个面子和雀头都有19，没有字牌）
    # 简化检测：略

    # 混老头（只有幺九牌，有字牌）
    # 简化检测：略

    # 清老头（只有19牌，没有字牌）
    # 简化检测：略

    # 三色同顺/三色同刻
    # 简化检测：略（需要和牌后才能确定具体面子）

    # 一气通贯
    # 简化检测：略

    return yaku_list


def has_yaku_for_dama(tiles: List[int],
                      furo_groups: List = None,
                      seat_wind: int = 1,
                      prevalent_wind: int = 1) -> bool:
    """
    判断手牌是否有役（用于默听判断）
    只要有任何确定的役（除了门前清自摸和），就返回True
    """
    yaku = detect_yaku(
        tiles,
        furo_groups,
        seat_wind=seat_wind,
        prevalent_wind=prevalent_wind
    )
    return len(yaku) > 0


# ==================== 手牌状态追踪器 ====================

class HandTracker:
    """追踪一个玩家在一局中的手牌状态"""

    def __init__(self,
                 seat: int,
                 initial_hand: List[int],
                 seat_wind: int = 1,
                 prevalent_wind: int = 1,
                 debug: bool = False):
        self.seat = seat
        self.seat_wind = seat_wind
        self.prevalent_wind = prevalent_wind
        self.debug = debug
        # 过滤掉非整数、60和0
        self.hand = sorted([t for t in initial_hand if isinstance(t, int) and 0 < t < 60])
        self.furo_groups = []  # 副露组
        self.riichi_declared = False

        # 默听状态追踪
        self.dama_state = False  # 当前是否处于默听状态
        self.dama_turns_count = 0  # 总共经历默听的次数

        # 默听结果统计
        self.dama_hands = 0  # 进入默听的局数
        self.dama_win = 0  # 默听后和了
        self.dama_deal_in = 0  # 默听后放铳
        self.dama_draw = 0  # 默听后流局
        self.dama_pass = 0  # 默听后横移（别人和了）
        self.debug_log: List[Dict[str, Any]] = []

        self._record_snapshot("init")

    def process_action_pair(self, draw_tile: int, discard_tile: int):
        """
        处理一次摸打
        draw_tile: 摸的牌（60表示没有摸牌）
        discard_tile: 打的牌（60表示没有打牌，可能是副露或立直）
        """
        # 摸牌
        if draw_tile > 0 and draw_tile < 60:
            self.hand.append(draw_tile)
            self.hand.sort()

        # 打牌
        if discard_tile > 0 and discard_tile < 60:
            if discard_tile in self.hand:
                self.hand.remove(discard_tile)
            self.hand.sort()

        # 每次摸打后检查默听状态
        if len(self.hand) == 13:
            self._check_dama_state()

        self._record_snapshot(
            "action_pair",
            {
                "draw": draw_tile,
                "discard": discard_tile
            }
        )

    def process_special_action(self, action_str: str):
        """
        处理特殊操作（立直、副露等）
        action_str: 如 'r29', 'c171618', 'p131313' 等
        """
        if not isinstance(action_str, str):
            return

        if action_str.startswith('r'):
            # 立直：r后面跟打出的牌
            self.riichi_declared = True
            discard = int(action_str[1:]) if len(action_str) > 1 else 0
            if discard > 0 and discard < 60 and discard in self.hand:
                self.hand.remove(discard)
                self.hand.sort()
            # 立直后不再是默听
            self.dama_state = False
            return

        furo_info = self._parse_furo_string(action_str)
        if furo_info is not None:
            # 副露
            furo_type, tiles = furo_info
            self._process_furo(furo_type, tiles)
            # 副露后不再是默听
            self.dama_state = False

        self._record_snapshot("special_action", {"action": action_str})

    def _parse_furo_string(self, action_str: str) -> Optional[Tuple[str, List[int]]]:
        """从操作字符串中解析副露信息，返回(类型, 牌列表)"""
        if not action_str or not isinstance(action_str, str):
            return None
        if action_str == 'Ryuukyoku':
            return None

        furo_type = None
        for ch in action_str:
            if ch in ('c', 'p', 'k', 'm'):
                furo_type = ch
                break
        if furo_type is None:
            return None

        digits = ''.join(ch for ch in action_str if ch.isdigit())
        if len(digits) < 2:
            return None

        tiles = []
        for i in range(0, len(digits) - 1, 2):
            tile_str = digits[i:i+2]
            if len(tile_str) == 2:
                tiles.append(int(tile_str))

        if not tiles:
            return None

        return furo_type, tiles

    def _process_furo(self, furo_type: str, tiles: List[int]):
        """处理副露"""
        if not tiles:
            return

        # 从手牌中移除副露用到的牌（吃/碰是从手里拿2张，从别人那里拿1张）
        # 杠是从手里拿3张或4张
        for tile in tiles:
            if tile in self.hand:
                self.hand.remove(tile)

        self.furo_groups.append({
            'type': furo_type,
            'tiles': tiles
        })
        self.hand.sort()

    def _check_dama_state(self):
        """
        检查当前是否处于默听状态
        条件：
        1. 没有立直
        2. 没有副露（门清）
        3. 手牌听牌（向听数=0）
        4. 有役（除了门前清自摸和）
        """
        # 如果已经立直或有副露，不可能是默听
        if self.riichi_declared or len(self.furo_groups) > 0:
            if self.dama_state:
                # 退出默听状态
                self.dama_state = False
                self._record_snapshot("exit_dama_state", {"detail": "riichi_or_furo"})
            return

        # 检查是否听牌
        if len(self.hand) != 13:
            if self.dama_state:
                self.dama_state = False
                self._record_snapshot("exit_dama_state", {"detail": "tile_count"})
            return

        if not is_tenpai(self.hand):
            if self.dama_state:
                self.dama_state = False
                self._record_snapshot("exit_dama_state", {"detail": "not_tenpai"})
            return

        # 检查是否有役（用于默听）
        if has_yaku_for_dama(
            self.hand,
            self.furo_groups,
            seat_wind=self.seat_wind,
            prevalent_wind=self.prevalent_wind
        ):
            if not self.dama_state:
                # 刚进入默听状态
                self.dama_state = True
                self.dama_hands += 1
                self._record_snapshot("enter_dama_state")
        else:
            if self.dama_state:
                self.dama_state = False
                self._record_snapshot("exit_dama_state", {"detail": "no_yaku"})

    def record_win(self):
        """记录和了"""
        if self.dama_state:
            self.dama_win += 1
            self.dama_state = False
        self._record_snapshot("record_win")

    def record_deal_in(self):
        """记录放铳"""
        if self.dama_state:
            self.dama_deal_in += 1
            self.dama_state = False
        self._record_snapshot("record_deal_in")

    def record_draw(self):
        """记录流局"""
        if self.dama_state:
            self.dama_draw += 1
            self.dama_state = False
        self._record_snapshot("record_draw")

    def record_pass(self):
        """记录横移（别人和了，自己既没和也没放铳）"""
        if self.dama_state:
            self.dama_pass += 1
            self.dama_state = False
        self._record_snapshot("record_pass")

    def is_dama(self) -> bool:
        """返回当前是否处于默听状态"""
        return self.dama_state

    def get_hand_string(self) -> str:
        """获取手牌的可读字符串"""
        return tiles_to_string(self.hand)

    def get_stats(self) -> Dict:
        """返回默听统计数据"""
        return {
            'dama_hands': self.dama_hands,
            'dama_win': self.dama_win,
            'dama_deal_in': self.dama_deal_in,
            'dama_draw': self.dama_draw,
            'dama_pass': self.dama_pass
        }

    def get_debug_log(self) -> List[Dict[str, Any]]:
        """获取调试日志"""
        return self.debug_log

    def _record_snapshot(self, reason: str, extra: Optional[Dict[str, Any]] = None):
        if not self.debug:
            return

        snapshot: Dict[str, Any] = {
            'reason': reason,
            'hand': self.hand.copy(),
            'hand_str': tiles_to_string(self.hand),
            'tile_count': len(self.hand),
            'dama_state': self.dama_state,
            'riichi_declared': self.riichi_declared,
            'furo_groups': list(self.furo_groups),
        }

        tenpai = len(self.hand) == 13 and is_tenpai(self.hand)
        snapshot['tenpai'] = tenpai
        if tenpai:
            snapshot['yaku'] = detect_yaku(
                self.hand,
                self.furo_groups,
                seat_wind=self.seat_wind,
                prevalent_wind=self.prevalent_wind
            )
        else:
            snapshot['yaku'] = []

        if extra:
            snapshot.update(extra)

        self.debug_log.append(snapshot)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试编码解码
    print("=== 测试编码解码 ===")
    test_tiles = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43, 45]
    print(f"牌编码: {test_tiles}")
    print(f"牌面: {tiles_to_string(test_tiles)}")

    # 测试向听数计算
    print("\n=== 测试向听数计算 ===")
    # 一个典型的听牌手牌
    tenpai_hand = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 41, 45, 45]
    print(f"手牌: {tiles_to_string(tenpai_hand)}")
    print(f"向听数: {calculate_shanten(tenpai_hand)}")
    print(f"是否听牌: {is_tenpai(tenpai_hand)}")

    # 测试手役检测
    print("\n=== 测试手役检测 ===")
    print(f"检测到的役: {detect_yaku(tenpai_hand)}")

    # 测试清一色听牌
    print("\n=== 测试清一色听牌 ===")
    honitsu_hand = [11, 12, 13, 14, 15, 16, 17, 18, 19, 11, 12, 13, 14]
    print(f"手牌: {tiles_to_string(honitsu_hand)}")
    print(f"向听数: {calculate_shanten(honitsu_hand)}")
    print(f"检测到的役: {detect_yaku(honitsu_hand)}")
    print(f"是否有役（用于默听）: {has_yaku_for_dama(honitsu_hand)}")

    # 测试HandTracker
    print("\n=== 测试HandTracker ===")
    initial = [14, 47, 13, 19, 15, 46, 31, 34, 16, 47, 22, 13, 38]
    tracker = HandTracker(0, initial)
    print(f"初始手牌: {tracker.get_hand_string()}")
    print(f"是否默听: {tracker.is_dama()}")

    # 模拟摸打几次
    tracker.process_action_pair(34, 47)
    print(f"\n摸34打47后: {tracker.get_hand_string()}")
    print(f"是否默听: {tracker.is_dama()}")

    print(f"\n默听统计: {tracker.get_stats()}")
