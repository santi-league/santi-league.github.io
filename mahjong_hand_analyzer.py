# -*- coding: utf-8 -*-
"""
麻将手牌分析模块
提供手牌追踪、向听数计算、听牌判断和手役检测功能
"""

from typing import List, Tuple, Optional, Set, Dict
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

    这是简化版本，只计算标准型向听数（不包括七对子和国士无双）
    """
    if len(tiles) not in [13, 14]:
        return 99  # 非法手牌

    # 解码牌
    decoded = [decode_tile(t) for t in tiles]

    # 统计各花色的牌
    suits = {'m': [], 'p': [], 's': [], 'z': []}
    for suit, rank in decoded:
        if suit in suits:
            suits[suit].append(rank)

    # 尝试标准型（4面子1雀头）
    standard_shanten = _calculate_standard_shanten(suits)

    # 尝试七对子型
    pairs_shanten = _calculate_pairs_shanten(tiles)

    # 尝试国士无双型（只对13张牌）
    kokushi_shanten = 99
    if len(tiles) == 13:
        kokushi_shanten = _calculate_kokushi_shanten(decoded)

    return min(standard_shanten, pairs_shanten, kokushi_shanten)


def _calculate_standard_shanten(suits: Dict[str, List[int]]) -> int:
    """计算标准型向听数（4面子1雀头）"""
    total_tiles = sum(len(tiles) for tiles in suits.values())

    # 递归计算所有可能的面子组合
    best_shanten = 99

    def search(suit_idx: int, mentsu: int, jantou: int, remaining: Dict[str, List[int]]):
        nonlocal best_shanten

        suit_names = ['m', 'p', 's', 'z']

        # 所有花色都处理完了
        if suit_idx >= len(suit_names):
            # 计算向听数: 8 - 面子*2 - 雀头 - (还需要的搭子数)
            tatsu = 0  # 搭子数
            isolated = 0  # 孤立牌数

            for suit_name in suit_names:
                tiles = sorted(remaining[suit_name])
                if not tiles:
                    continue
                counter = Counter(tiles)

                # 简单估算搭子
                for rank in sorted(counter.keys()):
                    if counter[rank] >= 2:
                        tatsu += 1
                        counter[rank] -= 2
                    elif counter[rank] == 1:
                        # 检查是否能形成顺子搭子
                        if rank + 1 in counter or rank + 2 in counter:
                            tatsu += 1
                            counter[rank] -= 1
                        else:
                            isolated += 1

            # 计算向听数
            need_groups = 4 - mentsu
            tatsu = min(tatsu, need_groups)
            shanten = need_groups - tatsu + (1 if jantou == 0 else 0) - 1
            best_shanten = min(best_shanten, max(-1, shanten))
            return

        suit_name = suit_names[suit_idx]
        tiles = remaining[suit_name]

        if not tiles:
            search(suit_idx + 1, mentsu, jantou, remaining)
            return

        counter = Counter(tiles)

        # 尝试不取任何面子/雀头，直接跳到下一花色
        search(suit_idx + 1, mentsu, jantou, remaining)

        # 尝试取刻子
        for rank in sorted(counter.keys()):
            if counter[rank] >= 3 and mentsu < 4:
                new_remaining = {k: v[:] for k, v in remaining.items()}
                for _ in range(3):
                    new_remaining[suit_name].remove(rank)
                search(suit_idx, mentsu + 1, jantou, new_remaining)

        # 尝试取顺子（仅数牌）
        if suit_name in ['m', 'p', 's']:
            for rank in sorted(counter.keys()):
                if rank <= 7 and rank + 1 in counter and rank + 2 in counter and mentsu < 4:
                    new_remaining = {k: v[:] for k, v in remaining.items()}
                    new_remaining[suit_name].remove(rank)
                    new_remaining[suit_name].remove(rank + 1)
                    new_remaining[suit_name].remove(rank + 2)
                    search(suit_idx, mentsu + 1, jantou, new_remaining)

        # 尝试取雀头
        for rank in sorted(counter.keys()):
            if counter[rank] >= 2 and jantou == 0:
                new_remaining = {k: v[:] for k, v in remaining.items()}
                for _ in range(2):
                    new_remaining[suit_name].remove(rank)
                search(suit_idx, mentsu, 1, new_remaining)

    search(0, 0, 0, suits)
    return best_shanten


def _calculate_pairs_shanten(tiles: List[int]) -> int:
    """计算七对子向听数"""
    counter = Counter(tiles)
    pairs = sum(1 for count in counter.values() if count >= 2)
    singles = sum(1 for count in counter.values() if count == 1)

    # 七对子向听数 = 6 - 对子数
    # 但如果有4张一样的牌，算作两对
    shanten = 6 - pairs

    # 如果不同种类的牌少于7种，无法组成七对子
    if len(counter) < 7:
        shanten = max(shanten, 7 - len(counter))

    return shanten


def _calculate_kokushi_shanten(decoded: List[Tuple[str, int]]) -> int:
    """计算国士无双向听数"""
    # 国士牌: 1m, 9m, 1p, 9p, 1s, 9s, z1-z7 (共13种)
    yaochu = set()
    yaochu_tiles = []

    for suit, rank in decoded:
        if suit in ['m', 'p', 's'] and rank in [1, 9]:
            yaochu.add((suit, rank))
            yaochu_tiles.append((suit, rank))
        elif suit == 'z':
            yaochu.add((suit, rank))
            yaochu_tiles.append((suit, rank))

    # 国士向听数 = 13 - 幺九种类数 - (是否有对子)
    has_pair = len(yaochu_tiles) > len(yaochu)
    shanten = 13 - len(yaochu) - (1 if has_pair else 0)

    return shanten


def is_tenpai(tiles: List[int]) -> bool:
    """判断是否听牌"""
    return calculate_shanten(tiles) == 0


# ==================== 手役检测 ====================

def detect_yaku(tiles: List[int], furo_groups: List = None, is_riichi: bool = False) -> List[str]:
    """
    检测手牌中可能的手役（不考虑宝牌、一发、里宝等）

    参数:
    - tiles: 手牌（13张）
    - furo_groups: 副露组（如果有）
    - is_riichi: 是否立直

    返回: 可能的手役名称列表

    注意：这个函数检测的是在听牌状态下，如果和牌可能拥有的役
    不包括：立直、一发、里宝、宝牌、岭上开花、抢杠、海底等和牌时才能确定的役
    """
    if furo_groups is None:
        furo_groups = []

    yaku_list = []

    # 如果有副露，不能是门清役
    is_menzen = len(furo_groups) == 0

    decoded = [decode_tile(t) for t in tiles]
    suits = {'m': [], 'p': [], 's': []}
    honors = []

    for suit, rank in decoded:
        if suit in suits:
            suits[suit].append(rank)
        elif suit == 'z':
            honors.append(rank)

    # 统计各花色牌数
    m_count = len(suits['m'])
    p_count = len(suits['p'])
    s_count = len(suits['s'])
    z_count = len(honors)

    # === 检测基本役种 ===

    # 断幺九（全是2-8的数牌，没有字牌和1,9）
    if z_count == 0:
        all_simples = True
        for suit_name in ['m', 'p', 's']:
            if any(rank in [1, 9] for rank in suits[suit_name]):
                all_simples = False
                break
        if all_simples and (m_count + p_count + s_count) == len(tiles):
            yaku_list.append("All Simples")

    # 清一色/混一色（只有一种花色+字牌）
    num_suits = sum(1 for suit_name in ['m', 'p', 's'] if len(suits[suit_name]) > 0)
    if num_suits == 1:
        if z_count == 0:
            yaku_list.append("Full Flush")  # 清一色
        else:
            yaku_list.append("Half Flush")  # 混一色

    # 对对和（七对子在这里检测）
    counter = Counter(tiles)
    if all(count >= 2 for count in counter.values()) and len(counter) == 7:
        yaku_list.append("Seven Pairs")  # 七对子

    # 字牌役（役牌：白发中、自风、场风）
    # 注意：这里简化处理，不考虑自风场风的具体判断
    honor_counter = Counter(honors)
    if honor_counter.get(5, 0) >= 3:  # 白
        yaku_list.append("White Dragon")
    if honor_counter.get(6, 0) >= 3:  # 发
        yaku_list.append("Green Dragon")
    if honor_counter.get(7, 0) >= 3:  # 中
        yaku_list.append("Red Dragon")

    # 平和（门清且没有字牌，4个顺子+1个雀头）
    # 简化检测：如果是门清、没有字牌、没有刻子，可能是平和
    if is_menzen and z_count == 0:
        # 这里需要更复杂的逻辑来准确判断，暂时简化
        has_triplet = any(count >= 3 for count in Counter(tiles).values())
        if not has_triplet:
            yaku_list.append("Pinfu")

    # 一杯口/二杯口（门清，有重复的顺子）
    if is_menzen:
        # 简化检测：检查是否有相同的顺子
        # 实际需要解析面子后判断
        pass

    # 三色同顺（三种花色的同数字顺子）
    # 简化检测：检查三种花色是否都有连续数字
    if m_count > 0 and p_count > 0 and s_count > 0:
        for num in range(1, 8):
            if (all((num in suits['m'], num+1 in suits['m'], num+2 in suits['m']) and
                    (num in suits['p'], num+1 in suits['p'], num+2 in suits['p']) and
                    (num in suits['s'], num+1 in suits['s'], num+2 in suits['s']))):
                yaku_list.append("Mixed Triple Sequence")
                break

    # 三色同刻（三种花色的同数字刻子）
    if m_count > 0 and p_count > 0 and s_count > 0:
        m_counter = Counter(suits['m'])
        p_counter = Counter(suits['p'])
        s_counter = Counter(suits['s'])
        for num in range(1, 10):
            if m_counter.get(num, 0) >= 3 and p_counter.get(num, 0) >= 3 and s_counter.get(num, 0) >= 3:
                yaku_list.append("Triple Triplets")
                break

    return yaku_list


# ==================== 手牌状态追踪器 ====================

class HandTracker:
    """追踪一个玩家在一局中的手牌状态"""

    def __init__(self, seat: int, initial_hand: List[int]):
        self.seat = seat
        self.hand = sorted([t for t in initial_hand if t < 60])  # 过滤掉60
        self.draws = []  # 摸牌序列
        self.discards = []  # 打牌序列
        self.furo_groups = []  # 副露组
        self.riichi_declared = False
        self.current_turn = 0

        # 默听状态追踪
        self.dama_state = False  # 当前是否处于默听状态
        self.dama_turns = 0  # 默听持续回合数

    def process_turn(self, actions: List):
        """
        处理一个回合的动作
        actions: 牌谱中一个玩家的回合数据，可能包含数字（摸/打）和字符串（副露/立直标记）
        """
        for action in actions:
            if isinstance(action, int):
                if action < 60:
                    # 摸牌
                    self.hand.append(action)
                    self.hand.sort()
                    self.draws.append(action)
                # 60 表示跳过或占位
            elif isinstance(action, str):
                # 处理特殊操作
                if action.startswith('r'):
                    # 立直：r后面跟打出的牌
                    self.riichi_declared = True
                    discard = int(action[1:]) if len(action) > 1 else 0
                    if discard in self.hand:
                        self.hand.remove(discard)
                        self.discards.append(discard)
                elif action.startswith('c'):
                    # 吃：c后面跟三张牌
                    self._process_furo(action, 'chi')
                elif action.startswith('p'):
                    # 碰：p后面跟三张牌
                    self._process_furo(action, 'pon')
                elif action.startswith('k'):
                    # 杠
                    self._process_furo(action, 'kan')

        # 检查默听状态
        self._check_dama_state()
        self.current_turn += 1

    def process_discard(self, tile: int):
        """处理打牌"""
        if tile in self.hand:
            self.hand.remove(tile)
            self.discards.append(tile)
            self.hand.sort()

    def _process_furo(self, furo_str: str, furo_type: str):
        """处理副露"""
        # 提取副露的牌
        tiles_str = furo_str[1:]
        tiles = []
        i = 0
        while i < len(tiles_str):
            if i + 1 < len(tiles_str):
                tile = int(tiles_str[i:i+2])
                tiles.append(tile)
                i += 2
            else:
                break

        # 从手牌中移除副露的牌（除了从别人那里获得的那张）
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
            self.dama_state = False
            return

        # 检查是否听牌
        if len(self.hand) != 13:
            self.dama_state = False
            return

        if not is_tenpai(self.hand):
            self.dama_state = False
            return

        # 检查是否有役（不包括门前清自摸和）
        yaku_list = detect_yaku(self.hand, self.furo_groups, False)

        # 如果有任何役（除了仅自摸），就是默听
        if len(yaku_list) > 0:
            if not self.dama_state:
                # 刚进入默听状态
                self.dama_state = True
                self.dama_turns = 1
            else:
                self.dama_turns += 1
        else:
            self.dama_state = False
            self.dama_turns = 0

    def is_dama(self) -> bool:
        """返回当前是否处于默听状态"""
        return self.dama_state

    def get_hand_string(self) -> str:
        """获取手牌的可读字符串"""
        return tiles_to_string(self.hand)


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
