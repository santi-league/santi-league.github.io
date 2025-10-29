#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查文件处理顺序"""

import os
import re
from datetime import datetime
from player_stats import scan_files

# 扫描 M-League 文件
m_league_folder = "game-logs/m-league"
files = scan_files(m_league_folder, "*.json", recursive=True)

print("="*80)
print("sorted(files) 的顺序（前10个）:")
print("="*80)

for i, fp in enumerate(sorted(files)[:10], 1):
    filename = os.path.basename(fp)
    print(f"{i}. {filename}")

print("\n" + "="*80)
print("按时间戳排序的顺序（前10个）:")
print("="*80)

# 按文件名中的日期排序
file_with_dates = []
for fp in files:
    filename = os.path.basename(fp)
    match = re.match(r'(\d+)_(\d+)_(\d+)', filename)
    number_match = re.search(r'\((\d+)\)', filename)
    file_number = int(number_match.group(1)) if number_match else 0

    if match:
        month, day, year = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            file_with_dates.append((date_obj, file_number, filename))
        except:
            pass

file_with_dates.sort(key=lambda x: (x[0], x[1]))

for i, (date, num, filename) in enumerate(file_with_dates[:10], 1):
    print(f"{i}. {filename} ({date.strftime('%Y-%m-%d')})")

print("\n问题：sorted(files) 是按文件名字符串排序，不是按日期排序！")
print("="*80)
