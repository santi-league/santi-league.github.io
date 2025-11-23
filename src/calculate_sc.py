#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算并验证牌谱中的sc字段

流程：
1. 重新模拟log累计素点、立直棒，计算应有的sc
2. 将结果与牌谱内现有sc逐项对比（素点必须完全一致，R值允许0.01误差）
3. 若缺少sc字段，则报错并把牌谱移到error文件夹
"""

import os
import json
import glob
import shutil

ERROR_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'error'))

def move_file_to_error(filepath, reason):
    """将问题牌谱移动到error文件夹"""
    os.makedirs(ERROR_FOLDER, exist_ok=True)
    filename = os.path.basename(filepath)
    target_path = os.path.join(ERROR_FOLDER, filename)

    if os.path.abspath(filepath) == os.path.abspath(target_path):
        # 已经在error目录中
        return

    name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(target_path):
        target_path = os.path.join(ERROR_FOLDER, f"{name}_{counter}{ext}")
        counter += 1

    shutil.move(filepath, target_path)
    rel_target = os.path.relpath(target_path)
    print(f"   → 已移动到 {rel_target}")

def calculate_sc_from_log(log_data):
    """
    从log数据计算sc字段

    参数:
        log_data: 包含log的JSON数据

    返回:
        sc数组，格式：[玩家0分数, 玩家0R值, 玩家1分数, 玩家1R值, ...]
        如果无法计算则返回None
    """
    if 'log' not in log_data:
        return None

    # 初始分数
    scores = [25000, 25000, 25000, 25000]

    # 统计每个玩家的立直次数
    riichi_count = [0, 0, 0, 0]

    # 玩家动作序列的元素索引范围（根据log结构推断）
    # 玩家0: 元素[5, 6], 玩家1: 元素[8, 9], 玩家2: 元素[11, 12], 玩家3: 元素[14, 15]
    action_ranges = [
        (5, 6),   # 玩家0
        (8, 9),   # 玩家1
        (11, 12), # 玩家2
        (14, 15), # 玩家3
    ]

    # 遍历每一局
    for kyoku in log_data['log']:
        # 1. 统计立直次数
        for player_id, (start, end) in enumerate(action_ranges):
            for action_idx in range(start, end + 1):
                if action_idx < len(kyoku):
                    elem = kyoku[action_idx]
                    if isinstance(elem, list):
                        # 查找r开头的字符串（立直）
                        riichi_actions = [x for x in elem if isinstance(x, str) and x.startswith('r')]
                        if riichi_actions:
                            riichi_count[player_id] += 1

        # 2. 累加分数变动
        result = kyoku[-1]
        if isinstance(result, list) and len(result) >= 2:
            delta = result[1]  # 分数变动
            if isinstance(delta, list) and len(delta) == 4:
                for i in range(4):
                    scores[i] += delta[i]

    # 3. 扣除立直支付的1000点
    for i in range(4):
        scores[i] -= riichi_count[i] * 1000

    # 4. 处理剩余立直棒（归第一名所有）
    total = sum(scores)
    expected_total = 25000 * 4  # 100000
    total_riichi = sum(riichi_count)

    print(f"  立直次数: {riichi_count} (总计: {total_riichi}次)")
    print(f"  累加后分数: {scores}")
    print(f"  分数总和: {total} (预期: {expected_total}, 差值: {total - expected_total})")

    if total != expected_total:
        # 有剩余立直棒，归第一名所有
        riichi_sticks_value = total - expected_total

        # 找到第一名（分数最高的玩家）
        first_place_idx = scores.index(max(scores))
        scores[first_place_idx] += riichi_sticks_value

        print(f"  场上剩余立直棒价值: {riichi_sticks_value}点，归第一名 (玩家{first_place_idx})")
        print(f"  调整后分数: {scores}")

    # 5. 计算R值变化
    # R值 = (分数 - 25000) / 1000 + 马点
    uma_config = {1: 45, 2: 5, 3: -15, 4: -35}

    # 按分数排序，计算名次
    score_rank_pairs = [(scores[i], i) for i in range(4)]
    score_rank_pairs.sort(key=lambda x: -x[0])  # 按分数从高到低排序

    # 计算每个玩家的名次（处理同分情况）
    ranks = [0] * 4
    prev_score = None
    current_rank = 0

    for pos, (score, idx) in enumerate(score_rank_pairs):
        if prev_score is None or score < prev_score:
            current_rank = pos + 1
            prev_score = score
        ranks[idx] = current_rank

    # 找出同分组，计算平均马点
    score_groups = {}  # {分数: [玩家索引列表]}
    for i in range(4):
        score = scores[i]
        if score not in score_groups:
            score_groups[score] = []
        score_groups[score].append(i)

    # 计算每个玩家的马点（同分平分）
    uma_values = [0.0] * 4

    for score, group in score_groups.items():
        if len(group) == 1:
            # 单独一人，直接按名次拿马点
            i = group[0]
            rank = ranks[i]
            uma_values[i] = uma_config.get(rank, 0)
        else:
            # 多人同分，平分这些名次对应的马点
            group_ranks = [ranks[i] for i in group]
            min_rank = min(group_ranks)
            max_rank = min_rank + len(group) - 1

            # 计算这几个名次的马点总和
            total_uma = sum(uma_config.get(r, 0) for r in range(min_rank, max_rank + 1))
            avg_uma = total_uma / len(group)

            # 分配给每个人
            for i in group:
                uma_values[i] = avg_uma

    # 计算R值变化
    r_values = []
    for i in range(4):
        base_r = (scores[i] - 25000) / 1000.0
        r_change = base_r + uma_values[i]
        r_values.append(r_change)

    print(f"  名次: {ranks}")
    print(f"  马点: {uma_values}")
    print(f"  R值变化: {r_values}")

    # sc格式：[分数, R值变化, 分数, R值变化, ...]
    sc = []
    for i in range(4):
        sc.append(scores[i])
        sc.append(r_values[i])

    return sc


def process_file(filepath):
    """处理单个文件，计算并验证sc字段"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    filename = os.path.basename(filepath)

    print(f"\n处理: {filename}")

    if 'sc' not in data:
        print(f"❌ {filename}: 缺少 sc 字段，移动到 error 文件夹")
        move_file_to_error(filepath, "missing sc")
        return False

    # 计算sc
    calculated_sc = calculate_sc_from_log(data)

    if calculated_sc is None:
        print(f"❌ 无法计算sc字段")
        return False

    # 检查是否已有sc字段
    if 'sc' in data:
        original_sc = data['sc']

        # 比较是否一致（允许小误差）
        if len(original_sc) != len(calculated_sc):
            print(f"❌ 错误：sc字段长度不匹配！原={len(original_sc)}, 计算={len(calculated_sc)}")
            print(f"   原sc: {original_sc}")
            print(f"   计算sc: {calculated_sc}")
            return False

        # 比较每个值（分数必须完全相同，R值允许0.01的误差）
        mismatch = False
        for i in range(len(original_sc)):
            if i % 2 == 0:
                # 分数，必须完全相同
                if original_sc[i] != calculated_sc[i]:
                    mismatch = True
                    print(f"❌ 错误：玩家{i//2}分数不匹配！原={original_sc[i]}, 计算={calculated_sc[i]}")
            else:
                # R值，允许小误差
                if abs(original_sc[i] - calculated_sc[i]) > 0.01:
                    mismatch = True
                    print(f"❌ 错误：玩家{i//2}R值不匹配！原={original_sc[i]}, 计算={calculated_sc[i]}")

        if mismatch:
            print(f"   原sc: {original_sc}")
            print(f"   计算sc: {calculated_sc}")
            return False
        else:
            print(f"✓ sc字段验证通过，无需更新")
            return True

    return True


def main():
    """主函数"""
    print("计算和验证所有牌谱的sc字段...")
    print("="*80)

    # 扫描所有牌谱文件
    folders = ['game-logs/m-league', 'game-logs/ema']

    total_verified = 0  # 验证通过
    total_errors = 0    # 计算错误或不匹配

    for folder in folders:
        if not os.path.exists(folder):
            continue

        print(f"\n检查文件夹: {folder}")
        print("="*80)

        # 递归查找所有JSON文件
        json_files = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.endswith('.json'):
                    json_files.append(os.path.join(root, f))

        # 处理每个文件
        folder_verified = 0
        folder_errors = 0

        for filepath in json_files:
            result = process_file(filepath)

            if result:
                folder_verified += 1
                total_verified += 1
            else:
                folder_errors += 1
                total_errors += 1

        print(f"\n{folder} 统计:")
        print(f"  验证通过: {folder_verified} 个文件")
        print(f"  错误: {folder_errors} 个文件")

    print(f"\n{'='*80}")
    print(f"总计统计:")
    print(f"{'='*80}")
    print(f"  验证通过（无需更新）: {total_verified} 个文件")
    print(f"  错误: {total_errors} 个文件")
    print(f"{'='*80}")

    # 如果有错误，返回非零退出码
    if total_errors > 0:
        print(f"\n⚠️  发现 {total_errors} 个文件存在错误，请检查！")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
