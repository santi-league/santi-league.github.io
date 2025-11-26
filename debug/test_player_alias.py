#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试玩家别名功能
"""

import sys
import os
import json

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from summarize_v23 import load_player_aliases, normalize_player_name, PLAYER_ALIAS_MAP

def test_alias_loading():
    """测试别名配置加载"""
    print("="*80)
    print("测试1: 别名配置加载")
    print("="*80)

    alias_map = load_player_aliases()
    print(f"加载的别名映射: {json.dumps(alias_map, ensure_ascii=False, indent=2)}")
    print(f"映射数量: {len(alias_map)}")
    print()

    return alias_map

def test_name_normalization():
    """测试玩家名转换"""
    print("="*80)
    print("测试2: 玩家名转换")
    print("="*80)

    test_cases = [
        ("santi", "应该保持为主ID"),
        ("santi_alt", "应该转换为santi（如果配置了）"),
        ("RinshanNomi", "应该保持不变或转换"),
        ("UnknownPlayer", "未配置的玩家应该保持原名"),
    ]

    for name, description in test_cases:
        normalized = normalize_player_name(name, PLAYER_ALIAS_MAP)
        print(f"{name:20} -> {normalized:20} ({description})")
    print()

def test_with_mock_game():
    """测试使用模拟对局数据"""
    print("="*80)
    print("测试3: 模拟对局数据处理")
    print("="*80)

    # 创建一个模拟的对局数据
    mock_game = {
        "name": ["santi_alt", "Player2", "Player3", "Player4"],
        "log": []  # 简化，不包含实际对局数据
    }

    # 模拟别名转换
    raw_names = mock_game.get("name", [])
    normalized_names = [normalize_player_name(name, PLAYER_ALIAS_MAP) for name in raw_names]

    print("原始玩家名:", raw_names)
    print("转换后:", normalized_names)
    print()

    if "santi_alt" in raw_names and "santi" in normalized_names:
        print("✅ 别名转换成功：santi_alt -> santi")
    else:
        print("ℹ️  未配置 santi_alt 别名，或主ID不是 santi")
    print()

def test_multiple_aliases():
    """测试多个别名转换到同一主ID"""
    print("="*80)
    print("测试4: 多个别名合并")
    print("="*80)

    test_names = ["santi", "santi_alt", "圣地", "santi_test"]
    normalized = [normalize_player_name(name, PLAYER_ALIAS_MAP) for name in test_names]

    print("测试名称:", test_names)
    print("转换结果:", normalized)

    # 检查所有配置的别名是否都转换为同一主ID
    unique_results = set(normalized)
    if len(unique_results) == 1:
        print(f"✅ 所有别名都转换为同一主ID: {unique_results.pop()}")
    else:
        print(f"ℹ️  转换后有 {len(unique_results)} 个不同的ID: {unique_results}")
        print("   （这是正常的，如果某些名字没有配置为别名）")
    print()

if __name__ == "__main__":
    print("\n")
    print("*" * 80)
    print("玩家别名功能测试")
    print("*" * 80)
    print()

    # 运行测试
    test_alias_loading()
    test_name_normalization()
    test_with_mock_game()
    test_multiple_aliases()

    print("="*80)
    print("测试完成")
    print("="*80)
    print()
    print("说明：")
    print("- 如果配置文件为空或只有注释，所有玩家名都会保持原样")
    print("- 要启用别名合并，请编辑 src/player_aliases.json")
    print("- 示例配置：")
    print('  {')
    print('    "santi": ["santi", "santi_alt", "圣地"],')
    print('    "RinshanNomi": ["RinshanNomi", "Rinshan"]')
    print('  }')
    print()
