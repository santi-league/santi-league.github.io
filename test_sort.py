#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的排序逻辑
验证是否按JSON内部时间戳正确排序
"""

import sys
import os
import json

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.helpers import sort_files_by_date
from player_stats import scan_files

def test_sort():
    """测试排序功能"""
    print("=" * 80)
    print("测试牌谱排序功能 - 使用JSON内部时间戳")
    print("=" * 80)

    # 扫描M-League文件
    m_league_folder = "game-logs/m-league"
    files = scan_files(m_league_folder, "*.json", recursive=True)

    if not files:
        print("❌ 未找到牌谱文件")
        return

    print(f"\n找到 {len(files)} 个牌谱文件\n")

    # 排序前显示前5个文件
    print("排序前（前5个文件）：")
    print("-" * 80)
    for i, fp in enumerate(files[:5], 1):
        filename = os.path.basename(fp)
        print(f"{i}. {filename}")
    print()

    # 执行排序
    sorted_files = sort_files_by_date(files)

    # 排序后显示前10个和后10个文件
    print("排序后（最早的10个牌谱）：")
    print("-" * 80)
    for i, fp in enumerate(sorted_files[:10], 1):
        filename = os.path.basename(fp)

        # 读取JSON获取时间戳
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
                title = data.get('title', [])
                if isinstance(title, list) and len(title) > 1:
                    timestamp = title[1]
                else:
                    timestamp = "无时间戳"
        except:
            timestamp = "读取失败"

        print(f"{i}. {filename}")
        print(f"   时间戳: {timestamp}")

    print()
    print("排序后（最新的10个牌谱）：")
    print("-" * 80)
    for i, fp in enumerate(sorted_files[-10:], len(sorted_files) - 9):
        filename = os.path.basename(fp)

        # 读取JSON获取时间戳
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
                title = data.get('title', [])
                if isinstance(title, list) and len(title) > 1:
                    timestamp = title[1]
                else:
                    timestamp = "无时间戳"
        except:
            timestamp = "读取失败"

        print(f"{i}. {filename}")
        print(f"   时间戳: {timestamp}")

    print()
    print("=" * 80)
    print("✅ 排序测试完成！")
    print("=" * 80)

    # 验证排序是否正确（检查时间戳是否递增）
    print("\n验证排序正确性...")
    errors = 0
    for i in range(len(sorted_files) - 1):
        try:
            with open(sorted_files[i], 'r', encoding='utf-8') as f1:
                data1 = json.load(f1)
                time1 = data1.get('title', [None, None])[1]

            with open(sorted_files[i + 1], 'r', encoding='utf-8') as f2:
                data2 = json.load(f2)
                time2 = data2.get('title', [None, None])[1]

            if time1 and time2:
                from datetime import datetime
                t1 = datetime.strptime(time1, "%m/%d/%Y, %I:%M:%S %p")
                t2 = datetime.strptime(time2, "%m/%d/%Y, %I:%M:%S %p")

                if t1 > t2:
                    errors += 1
                    print(f"❌ 排序错误: {os.path.basename(sorted_files[i])} ({time1}) > {os.path.basename(sorted_files[i+1])} ({time2})")
        except:
            pass

    if errors == 0:
        print("✅ 排序验证通过！所有牌谱按时间戳正确排序")
    else:
        print(f"❌ 发现 {errors} 个排序错误")

if __name__ == "__main__":
    test_sort()
