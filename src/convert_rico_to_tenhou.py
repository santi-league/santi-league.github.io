#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 ricochet.cn API 下载的牌谱格式转换为标准天凤格式
"""

import json
import sys
import os
from pathlib import Path
from urllib.parse import unquote
import re
from datetime import datetime


def convert_timestamp_format(timestamp_str):
    """
    转换时间戳格式
    从: Sat, 23 May 2026 17:40:50 GMT (RFC 2822)
    到: 5/23/2026, 5:40:50 PM
    """
    if not timestamp_str:
        return timestamp_str

    try:
        # 解析 RFC 2822 格式
        dt = datetime.strptime(timestamp_str, '%a, %d %b %Y %H:%M:%S %Z')
        # 转换为目标格式
        # 使用 %-m 和 %-d 去掉前导零 (Linux/Mac)
        # Windows 上使用 %#m 和 %#d
        try:
            formatted = dt.strftime('%-m/%-d/%Y, %-I:%M:%S %p')
        except:
            # Windows 兼容
            formatted = dt.strftime('%#m/%#d/%Y, %#I:%M:%S %p')
        return formatted
    except Exception as e:
        # 如果解析失败，返回原始字符串
        print(f"Warning: Failed to convert timestamp '{timestamp_str}': {e}", file=sys.stderr)
        return timestamp_str


def extract_tenhou_json_from_url(text):
    """从天凤 URL 中提取 JSON 数据"""
    # text 格式: https://tenhou.net/6/#json={...}
    if not text or not isinstance(text, str):
        return None

    # 提取 json= 后面的部分
    match = re.search(r'#json=(.+)$', text)
    if not match:
        return None

    json_str = match.group(1)
    # URL 解码
    json_str = unquote(json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON: {e}", file=sys.stderr)
        return None


# 规则配置
RULE_CONFIGS = {
    'm-league': {
        'name': 'M-League',
        'origin_points': 25000,
        'uma_points': [45, 5, -15, -35],  # 千分
        'total_points': 100000
    },
    'ema': {
        'name': 'EMA',
        'origin_points': 30000,
        'uma_points': [15, 5, -5, -15],  # 千分
        'total_points': 120000
    }
}


def convert_rico_format_to_tenhou(rico_data, paipu_id=None, rule_type='m-league'):
    """
    将 ricochet.cn 格式转换为天凤格式

    Args:
        rico_data: list, ricochet.cn API 返回的数据
        paipu_id: str, 牌谱ID (可选，用于 ref 字段)
        rule_type: str, 规则类型 ('m-league' 或 'ema')

    Returns:
        dict: 标准天凤格式的数据
    """
    # 获取规则配置
    if rule_type not in RULE_CONFIGS:
        raise ValueError(f"Unknown rule type: {rule_type}. Available: {list(RULE_CONFIGS.keys())}")

    rule_config = RULE_CONFIGS[rule_type]
    if not isinstance(rico_data, list) or len(rico_data) == 0:
        raise ValueError("Input data must be a non-empty list")

    # 从第一局提取基本信息
    first_round = rico_data[0]
    tenhou_data = extract_tenhou_json_from_url(first_round.get('text', ''))

    if not tenhou_data:
        raise ValueError("Failed to extract tenhou data from first round")

    # tenhou_data 已经是完整的天凤格式
    # 但是它只包含第一局的数据，我们需要合并所有局

    # 重新构建 log 字段，包含所有局
    all_logs = []
    for round_data in rico_data:
        round_tenhou = extract_tenhou_json_from_url(round_data.get('text', ''))
        if round_tenhou and 'log' in round_tenhou:
            # 每局的 log 是一个列表，包含该局的所有数据
            all_logs.extend(round_tenhou['log'])

    # 使用第一局的基本信息，但替换 log
    result = tenhou_data.copy()
    result['log'] = all_logs

    # 转换时间戳格式
    if 'title' in result and isinstance(result['title'], list) and len(result['title']) > 1:
        result['title'][1] = convert_timestamp_format(result['title'][1])

    # 补充标准字段
    # ref: 牌谱ID (从文件名或参数提取)
    if paipu_id:
        result['ref'] = paipu_id

    # ver: 版本号 (固定为 2.3)
    result['ver'] = 2.3

    # lobby: 大厅 (固定为 0)
    result['lobby'] = 0

    # ratingc: 房间类型 (PF4 = 四人普通, PF3 = 三人普通)
    num_players = len(result.get('name', []))
    result['ratingc'] = 'PF3' if num_players == 3 else 'PF4'

    # dan: 段位 (从牌谱无法获取，填充默认值)
    result['dan'] = [''] * num_players

    # rate: R值 (从牌谱无法获取，填充默认值)
    result['rate'] = [0] * num_players

    # sx: 性别 (从牌谱无法获取，填充默认值 C=Computer)
    result['sx'] = ['C'] * num_players

    # sc: 最终分数 (从最后一局计算)
    if all_logs and len(all_logs) > 0:
        last_log = all_logs[-1]

        # last_log[1] 是最后一局开始前的分数
        # last_log[-1] 是最后一局的结算信息
        if len(last_log) > 1 and isinstance(last_log[1], list):
            scores_before_last = last_log[1]

            # 查找最后一局的得失分
            # 结算信息通常在 last_log 的最后一个元素
            # 格式: ['和了'/'流局'/..., [得失分数组], ...]
            score_changes = None
            last_element = last_log[-1]

            if isinstance(last_element, list) and len(last_element) >= 2:
                if isinstance(last_element[1], list):
                    score_changes = last_element[1]

            # 计算真正的最终分数
            if score_changes and len(score_changes) == len(scores_before_last):
                scores = [scores_before_last[i] + score_changes[i] for i in range(len(scores_before_last))]
            else:
                # 如果没有找到得失分，使用最后一局开始前的分数（兜底）
                scores = scores_before_last

            # 检查最后一局是否有人立直未被收回（立直棒）
            # 从整个 log 中查找立直标记 'rXX'
            # 立直标记可能在手牌列表或打牌列表中
            riichi_players = []

            # 遍历所有玩家的数据
            # log[0-3]是额外信息，log[4]开始是玩家数据
            # 每个玩家有3个数组: [初始手牌, 摸到的牌, 操作]
            # 玩家0: log[4-6], 玩家1: log[7-9], 玩家2: log[10-12], 玩家3: log[13-15]
            for idx in range(4, len(last_log) - 1):  # 排除最后一个结算信息
                if isinstance(last_log[idx], list):
                    for item in last_log[idx]:
                        if isinstance(item, str) and item.startswith('r'):
                            # 找到立直标记，判断是哪个玩家
                            # 玩家索引 = (idx - 4) // 3
                            player_idx = (idx - 4) // 3
                            if player_idx < len(scores) and player_idx not in riichi_players:
                                riichi_players.append(player_idx)
                            break

            # 扣除立直棒（每个立直玩家扣1000点）
            for player_idx in riichi_players:
                scores[player_idx] -= 1000

            # sc 格式：[score1, 千分点1, score2, 千分点2, ...]
            # 千分点计算公式：(最终分 - 起始分 + 马点) / 1000

            # 获取起始分（从第一局）
            first_log = all_logs[0]
            origin_points = first_log[1][0] if len(first_log) > 1 and isinstance(first_log[1], list) else rule_config['origin_points']

            # 使用规则配置的马点（千分）
            uma_points = rule_config['uma_points']

            # 计算排名（按分数从高到低）
            score_with_idx = [(s, i) for i, s in enumerate(scores)]
            score_with_idx.sort(key=lambda x: x[0], reverse=True)
            ranks = [0] * len(scores)
            for rank, (_, idx) in enumerate(score_with_idx):
                ranks[idx] = rank

            # 校验：分数总和必须小于等于规则配置的总分
            expected_total = rule_config['total_points']
            total_score = sum(scores)
            if total_score > expected_total:
                raise ValueError(f"分数校验失败：sc字段中分数总和为 {total_score}，应为 {expected_total}。分数={scores}")
            elif total_score < expected_total:
                scores[score_with_idx[0][1]] += expected_total - total_score
                print(f"调整分数: {total_score} -> {expected_total}, 第一名分数: {scores[score_with_idx[0][1]]}")

            # 组装 sc 数组
            sc = []
            for i, score in enumerate(scores):
                sc.append(score)
                # 千分点 = (最终分 - 起始分 + 马点*1000) / 1000
                relative_score = score - origin_points
                uma = uma_points[ranks[i]] * 1000
                pt = (relative_score + uma) / 1000
                sc.append(pt)
            result['sc'] = sc
        else:
            result['sc'] = [0] * (num_players * 2)
    else:
        result['sc'] = [0] * (num_players * 2)

    return result


def process_file(input_path, output_path, paipu_id=None, rule_type='m-league'):
    """
    处理单个文件

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        paipu_id: 牌谱ID (可选，如果不提供则从输出文件名提取)
        rule_type: 规则类型 ('m-league' 或 'ema')
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        rico_data = json.load(f)

    # 如果没有提供牌谱ID，从输出文件名提取
    if not paipu_id:
        paipu_id = Path(output_path).stem

    tenhou_data = convert_rico_format_to_tenhou(rico_data, paipu_id=paipu_id, rule_type=rule_type)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tenhou_data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"✓ Converted: {input_path} -> {output_path}")
    return tenhou_data


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python3 convert_rico_to_tenhou.py <input_file> [output_file] [--rule RULE]")
        print("   or: python3 convert_rico_to_tenhou.py <input_dir> <output_dir> [--rule RULE]")
        print("")
        print("Options:")
        print("  --rule RULE    Specify rule type: m-league (default) or ema")
        sys.exit(1)

    # 解析参数
    args = sys.argv[1:]
    rule_type = 'm-league'  # 默认规则

    # 查找 --rule 参数
    if '--rule' in args:
        rule_idx = args.index('--rule')
        if rule_idx + 1 < len(args):
            rule_type = args[rule_idx + 1]
            # 移除 --rule 和它的值
            args.pop(rule_idx)
            args.pop(rule_idx)
        else:
            print("Error: --rule requires a value")
            sys.exit(1)

    if len(args) < 1:
        print("Error: Input path required")
        sys.exit(1)

    input_path = Path(args[0])

    if input_path.is_file():
        # 单文件模式
        if len(args) >= 2:
            output_path = Path(args[1])
        else:
            output_path = input_path.parent / f"{input_path.stem}_tenhou.json"

        process_file(input_path, output_path, rule_type=rule_type)

    elif input_path.is_dir():
        # 目录模式
        if len(args) < 2:
            print("Error: Output directory required for directory mode")
            sys.exit(1)

        output_dir = Path(args[1])
        output_dir.mkdir(parents=True, exist_ok=True)

        json_files = list(input_path.glob("*.json"))
        if not json_files:
            print(f"No JSON files found in {input_path}")
            sys.exit(1)

        print(f"Found {len(json_files)} files to convert")
        print(f"Using rule: {rule_type}")
        print()

        success = 0
        failed = 0

        for json_file in json_files:
            output_file = output_dir / json_file.name
            try:
                process_file(json_file, output_file, rule_type=rule_type)
                success += 1
            except Exception as e:
                print(f"✗ Failed: {json_file} - {e}", file=sys.stderr)
                failed += 1

        print()
        print(f"Conversion complete: {success} success, {failed} failed")

    else:
        print(f"Error: {input_path} is not a file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
