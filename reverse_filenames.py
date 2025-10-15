# -*- coding: utf-8 -*-
"""
将每天的牌谱文件编号倒序重命名

例如:
  10_1_2025_Tounament_South.json
  10_1_2025_Tounament_South (1).json
  10_1_2025_Tounament_South (2).json
  10_1_2025_Tounament_South (3).json

变成:
  10_1_2025_Tounament_South.json (原来的 (3))
  10_1_2025_Tounament_South (1).json (原来的 (2))
  10_1_2025_Tounament_South (2).json (原来的 (1))
  10_1_2025_Tounament_South (3).json (原来的无编号)

用法：
  python reverse_filenames.py game-logs/m-league
  python reverse_filenames.py game-logs/m-league --dry-run  # 预览不实际修改
"""

import os
import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path


def parse_filename(filename):
    """
    解析文件名，提取日期、基础名称和编号

    返回: (date_str, base_name, number)
    例如: "10_1_2025_Tounament_South (2).json" -> ("10_1_2025", "Tounament_South", 2)
          "10_1_2025_Tounament_South.json" -> ("10_1_2025", "Tounament_South", None)
    """
    # 匹配格式: MM_DD_YYYY_Name (N).json 或 MM_DD_YYYY_Name.json
    pattern = r'^(\d{1,2}_\d{1,2}_\d{4})_(.+?)(?: \((\d+)\))?\.json$'
    match = re.match(pattern, filename)

    if not match:
        return None, None, None

    date_str = match.group(1)
    base_name = match.group(2)
    number = int(match.group(3)) if match.group(3) else None

    return date_str, base_name, number


def reverse_rename_files(directory, dry_run=False):
    """
    将目录下的文件按日期分组，并将每组的编号倒序
    """
    directory = Path(directory)

    # 按日期和基础名分组
    file_groups = defaultdict(list)

    # 扫描所有JSON文件
    for file_path in directory.glob("*.json"):
        filename = file_path.name
        date_str, base_name, number = parse_filename(filename)

        if date_str and base_name:
            key = f"{date_str}_{base_name}"
            file_groups[key].append((filename, number if number is not None else -1))

    # 处理每个分组
    rename_operations = []

    for key, files in file_groups.items():
        if len(files) <= 1:
            # 只有一个文件，不需要重命名
            continue

        # 按编号排序 (无编号的-1排在最前面)
        files.sort(key=lambda x: x[1])

        # 倒序处理
        files_reversed = files[::-1]

        # 生成新的文件名
        date_base = key  # 例如 "10_1_2025_Tounament_South"

        for idx, (old_filename, old_number) in enumerate(files):
            new_number = files_reversed[idx][1]

            # 构造新文件名
            if new_number == -1:
                new_filename = f"{date_base}.json"
            else:
                new_filename = f"{date_base} ({new_number}).json"

            if old_filename != new_filename:
                rename_operations.append((old_filename, new_filename))

    # 执行重命名
    if not rename_operations:
        print("没有需要重命名的文件")
        return

    print(f"将要重命名 {len(rename_operations)} 个文件:\n")

    for old_name, new_name in rename_operations:
        print(f"  {old_name}")
        print(f"  -> {new_name}\n")

    if dry_run:
        print("【预览模式】以上是将要执行的重命名操作，没有实际修改文件。")
        print("如要实际执行，请去掉 --dry-run 参数。")
        return

    # 实际执行重命名 - 使用临时文件名避免冲突
    print("开始重命名...")

    # 第一步：将所有文件重命名为临时名称
    temp_names = []
    for old_name, new_name in rename_operations:
        old_path = directory / old_name
        temp_name = f"_temp_{old_name}"
        temp_path = directory / temp_name
        old_path.rename(temp_path)
        temp_names.append((temp_name, new_name))

    # 第二步：从临时名称重命名为最终名称
    for temp_name, new_name in temp_names:
        temp_path = directory / temp_name
        new_path = directory / new_name
        temp_path.rename(new_path)

    print(f"✓ 成功重命名 {len(rename_operations)} 个文件")


def main():
    parser = argparse.ArgumentParser(
        description="将每天的牌谱文件编号倒序重命名",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览将要进行的重命名操作
  python reverse_filenames.py game-logs/m-league --dry-run

  # 实际执行重命名
  python reverse_filenames.py game-logs/m-league
        """
    )

    parser.add_argument("directory", help="包含牌谱文件的目录")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际修改文件")

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"错误: 目录不存在: {args.directory}", file=sys.stderr)
        sys.exit(1)

    try:
        reverse_rename_files(args.directory, args.dry_run)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
