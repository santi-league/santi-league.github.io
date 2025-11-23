#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
牌谱整理工具

功能：
- 遍历 game-logs/m-league 和 game-logs/ema 文件夹
- 根据牌谱JSON中的时间戳（title[1]），将牌谱移动到对应日期的子文件夹
- 文件名格式：日期_时间_第一名玩家id.json

用法：
  python src/organize_logs.py
  python src/organize_logs.py --dry-run  # 仅预览，不实际移动
"""

import os
import sys
import json
import shutil
from datetime import datetime
from collections import defaultdict

# 添加src目录到路径以导入summarize_log
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from summarize_v23 import summarize_log

ERROR_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'error'))

def move_to_error(filepath, reason=None):
    """将文件移动到error文件夹"""
    if not filepath or not os.path.exists(filepath):
        return

    os.makedirs(ERROR_FOLDER, exist_ok=True)
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    target_path = os.path.join(ERROR_FOLDER, filename)
    counter = 1
    while os.path.exists(target_path):
        target_path = os.path.join(ERROR_FOLDER, f"{name}_{counter}{ext}")
        counter += 1

    shutil.move(filepath, target_path)
    rel_src = os.path.relpath(filepath)
    rel_tgt = os.path.relpath(target_path)
    msg = f"⚠️  已将 {rel_src} 移动到 {rel_tgt}"
    if reason:
        msg += f"（{reason}）"
    print(msg)
    return target_path

def organize_folder(folder_path, dry_run=False):
    """
    整理指定文件夹中的牌谱文件（递归处理所有子文件夹）

    参数:
    - folder_path: 文件夹路径
    - dry_run: 如果为True，只显示将要执行的操作，不实际移动文件
    """
    if not os.path.exists(folder_path):
        print(f"⚠️  文件夹不存在: {folder_path}")
        return

    print(f"\n{'='*80}")
    print(f"整理文件夹: {folder_path}")
    print(f"{'='*80}\n")

    # 递归扫描所有JSON文件（包括子文件夹）
    json_files = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.endswith('.json'):
                json_files.append(os.path.join(root, f))

    if not json_files:
        print(f"✓ 没有需要整理的牌谱文件\n")
        return

    print(f"找到 {len(json_files)} 个牌谱文件（包括子文件夹）\n")

    # 统计信息
    moved_count = 0
    renamed_count = 0
    error_count = 0
    skipped_count = 0
    date_groups = defaultdict(list)

    target_records = {}
    duplicate_removed = 0
    duplicate_conflicts = 0

    for file_path in json_files:
        filename = os.path.basename(file_path)
        current_dir = os.path.dirname(file_path)

        try:
            # 读取JSON文件获取时间戳
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取时间戳
            title = data.get('title', [])
            if not isinstance(title, list) or len(title) < 2:
                print(f"❌ {filename}: 缺少时间戳（title[1]）")
                error_count += 1
                continue

            timestamp_str = title[1]

            # 解析时间戳："MM/DD/YYYY, HH:MM:SS AM/PM"
            try:
                timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
            except ValueError as e:
                print(f"❌ {filename}: 时间戳格式错误 '{timestamp_str}'")
                error_count += 1
                continue

            # 生成日期文件夹名：YYYY-MM-DD
            date_folder_name = timestamp.strftime("%Y-%m-%d")
            date_folder_path = os.path.join(folder_path, date_folder_name)

            # 获取第一名玩家的名字
            try:
                result = summarize_log(data)
                first_place_players = [p for p in result['summary'] if p['rank'] == 1]
                if first_place_players:
                    winner_name = first_place_players[0]['name']
                else:
                    winner_name = 'NOWINNER'
            except Exception as e:
                print(f"⚠️  {filename}: 无法获取第一名玩家信息 - {str(e)}")
                winner_name = 'UNKNOWN'

            # 生成新文件名：日期_时间_第一名玩家.json
            # 格式：2025-08-01_001520_santi.json（日期_时分秒_第一名玩家id）
            time_str = timestamp.strftime("%H%M%S")
            new_filename = f"{date_folder_name}_{time_str}_{winner_name}.json"

            # 目标文件路径
            target_path = os.path.join(date_folder_path, new_filename)
            target_key = (date_folder_name, new_filename)

            canonical_content = json.dumps(data, ensure_ascii=False, sort_keys=True)
            existing_entry = target_records.get(target_key)
            rel_path = os.path.relpath(file_path, folder_path)

            if existing_entry:
                existing_rel = os.path.relpath(existing_entry['current_path'], folder_path)

                if canonical_content == existing_entry['content']:
                    # 完全重复，删除其中一个
                    if dry_run:
                        print(f"🗑️  预览删除重复牌谱: {rel_path}（与 {existing_rel} 完全相同）")
                    else:
                        os.remove(file_path)
                        print(f"🗑️  删除重复牌谱: {rel_path}（保留 {existing_rel}）")
                    duplicate_removed += 1
                    continue
                else:
                    # 内容不同的重名牌谱 -> 全部移到error
                    print(f"⚠️  发现内容不同但命名相同的牌谱: {rel_path} 与 {existing_rel}")
                    if dry_run:
                        print("   预览：两个文件都将被移动到 error/ 目录")
                    else:
                        move_to_error(file_path, "duplicate-conflict")
                        move_to_error(existing_entry['current_path'], "duplicate-conflict")
                    duplicate_conflicts += 1
                    error_count += 2
                    target_records.pop(target_key, None)
                    continue
            else:
                target_records[target_key] = {
                    'content': canonical_content,
                    'current_path': file_path
                }

            # 检查是否需要移动或重命名
            needs_action = False
            action_type = ""

            # 获取当前文件的相对路径（相对于folder_path）
            current_relative_dir = os.path.relpath(current_dir, folder_path)

            # 检查位置是否正确
            wrong_location = current_relative_dir != date_folder_name

            # 检查文件名是否正确（完全匹配）
            wrong_filename = filename != new_filename

            if wrong_location:
                # 文件不在正确的日期文件夹中
                needs_action = True
                action_type = "移动"
            elif wrong_filename:
                # 文件在正确的文件夹中，但文件名不对
                # 这包括：格式错误、时间不对、或第一名玩家不对
                needs_action = True
                action_type = "重命名"

            if not needs_action:
                # 文件已经在正确的位置且文件名完全正确（包括第一名玩家）
                skipped_count += 1
                continue

            # 记录到日期组
            date_groups[date_folder_name].append(new_filename)

            if dry_run:
                if action_type == "移动":
                    print(f"📋 {action_type}: {os.path.relpath(file_path, folder_path)} -> {date_folder_name}/{new_filename}")
                    moved_count += 1
                else:
                    print(f"✏️  {action_type}: {os.path.relpath(file_path, folder_path)} -> {new_filename}")
                    renamed_count += 1
            else:
                # 创建日期文件夹（如果不存在）
                if not os.path.exists(date_folder_path):
                    os.makedirs(date_folder_path)
                    print(f"📁 创建文件夹: {date_folder_name}/")

                # 移动/重命名文件
                shutil.move(file_path, target_path)
                target_records[target_key]['current_path'] = target_path

                if action_type == "移动":
                    print(f"✓ {action_type}: {os.path.relpath(file_path, folder_path)} -> {date_folder_name}/{new_filename}")
                    moved_count += 1
                else:
                    print(f"✓ {action_type}: {filename} -> {new_filename}")
                    renamed_count += 1

        except Exception as e:
            print(f"❌ {filename}: 处理失败 - {str(e)}")
            error_count += 1

    # 打印统计信息
    print(f"\n{'-'*80}")
    print("整理完成统计：")
    print(f"{'-'*80}")
    if dry_run:
        print(f"  预览模式（未实际操作）")
    print(f"  总文件数: {len(json_files)}")
    print(f"  已正确: {skipped_count} 个文件（无需操作）")
    if not dry_run:
        print(f"  已移动: {moved_count} 个文件")
        print(f"  已重命名: {renamed_count} 个文件")
    else:
        actions_needed = len(json_files) - skipped_count - error_count
        print(f"  需要操作: {actions_needed} 个文件")
    print(f"  错误: {error_count} 个文件")
    if duplicate_removed > 0:
        print(f"  删除重复牌谱: {duplicate_removed} 个")
    if duplicate_conflicts > 0:
        print(f"  重复冲突移入error: {duplicate_conflicts} 组")

    if date_groups:
        print(f"\n  按日期分组（需要操作的文件）：")
        for date_name in sorted(date_groups.keys()):
            print(f"    {date_name}: {len(date_groups[date_name])} 个文件")

    print(f"{'-'*80}\n")

    return moved_count + renamed_count, error_count


def main():
    """主函数"""
    # 检查是否为预览模式
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if dry_run:
        print("\n" + "="*80)
        print("🔍 预览模式 - 仅显示将要执行的操作，不会实际移动文件")
        print("="*80)

    # 整理M-League文件夹
    m_league_folder = "game-logs/m-league"
    m_moved, m_errors = organize_folder(m_league_folder, dry_run) or (0, 0)

    # 整理EMA文件夹
    ema_folder = "game-logs/ema"
    e_moved, e_errors = organize_folder(ema_folder, dry_run) or (0, 0)

    # 总结
    print("="*80)
    print("牌谱整理总结")
    print("="*80)
    if dry_run:
        print(f"M-League: 需要操作 {m_moved} 个文件{', ' + str(m_errors) + ' 个错误' if m_errors > 0 else ''}")
        print(f"EMA:      需要操作 {e_moved} 个文件{', ' + str(e_errors) + ' 个错误' if e_errors > 0 else ''}")
    else:
        print(f"M-League: 已操作 {m_moved} 个文件{', ' + str(m_errors) + ' 个错误' if m_errors > 0 else ''}")
        print(f"EMA:      已操作 {e_moved} 个文件{', ' + str(e_errors) + ' 个错误' if e_errors > 0 else ''}")
    print("="*80)

    if dry_run:
        print("\n提示：运行时不加 --dry-run 参数即可实际执行移动操作")

    # 如果有错误，返回非零退出码
    if m_errors + e_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
