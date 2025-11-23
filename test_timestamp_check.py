#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试时间戳检查功能
验证是否能正确检测缺失时间戳的文件
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.helpers import sort_files_by_date
from player_stats import scan_files

def test_timestamp_check():
    """测试时间戳检查功能"""
    print("=" * 80)
    print("测试时间戳检查功能")
    print("=" * 80)
    print()

    # 扫描M-League文件
    m_league_folder = "game-logs/m-league"
    files = scan_files(m_league_folder, "*.json", recursive=True)

    if not files:
        print("❌ 未找到牌谱文件")
        return

    print(f"找到 {len(files)} 个牌谱文件")
    print()

    # 尝试排序（如果有文件缺失时间戳会抛出异常）
    try:
        sorted_files = sort_files_by_date(files)
        print("✅ 所有牌谱文件都包含有效的时间戳！")
        print(f"✅ 成功排序 {len(sorted_files)} 个文件")
    except ValueError as e:
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    test_timestamp_check()
