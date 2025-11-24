#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查被删除的11月19日文件
"""

import subprocess
import json

files = [
    "game-logs/m-league/11_19_2025_Tounament_South (2).json",
    "game-logs/m-league/11_19_2025_Tounament_South (3).json",
    "game-logs/m-league/11_19_2025_Tounament_South (4).json",
    "game-logs/m-league/11_19_2025_Tounament_South (5).json"
]

print("被删除的11月19日文件内容:")
print("="*80)

for file in files:
    try:
        result = subprocess.run(
            ['git', 'show', f'154b78f:{file}'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        players = list(data.get('name', []))
        date_info = data.get('title', [])[1] if len(data.get('title', [])) > 1 else 'N/A'

        print(f"\n文件: {file}")
        print(f"日期: {date_info}")
        print(f"玩家: {', '.join(players)}")
        print(f"包含santi: {'是' if 'santi' in players else '否'}")

    except Exception as e:
        print(f"\n文件: {file}")
        print(f"错误: {e}")
