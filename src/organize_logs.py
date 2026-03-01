#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
牌谱整理工具

功能：
- 遍历文件夹，找到所有非标准化文件名的文件
- 将这些文件移到根目录
- 对文件进行标准化重命名并去重
- 将文件移动到对应日期文件夹并去重

用法：
  python src/organize_logs.py
  python src/organize_logs.py --dry-run  # 仅预览，不实际移动
"""

import os
import sys
import json
import shutil
import re
from datetime import datetime
from collections import defaultdict

# 添加src目录到路径以导入summarize_log
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from summarize_v23 import summarize_log

ERROR_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'game-logs', 'errors'))

def detect_league_type(data):
    """
    检测牌谱类型（M-League 或 EMA）

    通过分析起始分数和马点来判断：
    - EMA: 起始30000, 马点 15/5/-5/-15 (千分)
    - M-League: 起始25000, 马点 45/5/-15/-35 (千分)

    公式：马点 = sc值 × 1000 - 相对分 + 起始分

    返回：'m-league', 'ema', 或 None（无法判断）
    """
    try:
        # 1. 获取起始分数
        if 'log' not in data or len(data['log']) == 0:
            return None

        first_round = data['log'][0]
        if len(first_round) < 2 or not isinstance(first_round[1], list):
            return None

        origin_points = first_round[1][0]  # 第一个玩家的起始分

        # 2. 获取sc字段
        if 'sc' not in data or len(data['sc']) < 8:
            return None

        sc = data['sc']

        # 3. 提取每个玩家的相对分和sc值
        players_data = []
        for i in range(4):
            relative_score = sc[i*2]      # 相对分（最终分 - 起始分）
            sc_value = sc[i*2 + 1]        # sc值（千分制）

            players_data.append({
                'relative_score': relative_score,
                'sc_value': sc_value
            })

        # 4. 按相对分排序得出名次（相对分大的名次靠前）
        sorted_players = sorted(players_data, key=lambda x: -x['relative_score'])

        # 5. 反推马点（千分制）
        # 公式：马点 = sc值 × 1000 - 相对分 + 起始分
        uma_list = []
        for p in sorted_players:
            uma_points = p['sc_value'] * 1000 - p['relative_score'] + origin_points
            uma_thousandths = round(uma_points / 1000)  # 转换为千分制
            uma_list.append(uma_thousandths)

        # 6. 判断类型
        # EMA配置：起始30000, 马点 [15, 5, -5, -15]
        # M-League配置：起始25000, 马点 [45, 5, -15, -35]

        ema_uma = [15, 5, -5, -15]
        mleague_uma = [45, 5, -15, -35]

        # 允许±1的误差（因为四舍五入）
        def uma_matches(uma_list, expected_uma):
            return all(abs(uma_list[i] - expected_uma[i]) <= 1 for i in range(4))

        if origin_points == 30000 and uma_matches(uma_list, ema_uma):
            return 'ema'
        elif origin_points == 25000 and uma_matches(uma_list, mleague_uma):
            return 'm-league'
        else:
            # 无法确定，输出调试信息
            print(f"    ⚠️  无法确定牌谱类型: 起始分={origin_points}, 马点(千分)={uma_list}")
            return None

    except Exception as e:
        # 检测失败，返回None
        return None

def move_to_error(filepath, reason=None):
    """将文件移动到game-logs/errors文件夹"""
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
        msg += f"（原因: {reason}）"
    print(msg)
    return target_path

def is_standard_filename(filename):
    """
    检查文件名是否符合标准格式
    标准格式：YYYY-MM-DD_HHMMSS_玩家名.json
    例如：2025-01-01_120000_santi.json
    """
    pattern = r'^\d{4}-\d{2}-\d{2}_\d{6}_[^/\\]+\.json$'
    return bool(re.match(pattern, filename))

def get_standard_filename(data):
    """
    根据牌谱数据生成标准文件名
    返回：(标准文件名, 日期文件夹名) 或 (None, None) 如果失败
    """
    try:
        # 获取时间戳
        title = data.get('title', [])
        print('title', title)
        if not isinstance(title, list) or len(title) < 2:
            return None, None

        timestamp_str = title[1]
        print('timestamp_str', timestamp_str)

        # 解析时间戳："MM/DD/YYYY, HH:MM:SS AM/PM"
        if timestamp_str[-1] == 'M':
            try:
                timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
            except ValueError:
                return None, None
        else:
            try:
                timestamp = datetime.strptime(timestamp_str, "%d/%m/%Y, %H:%M:%S")
            except ValueError:
                return None, None

        # 生成日期文件夹名：YYYY-MM-DD
        date_folder_name = timestamp.strftime("%Y-%m-%d")
        print('date_folder_name', date_folder_name)

        # 获取第一名玩家的名字
        try:
            result = summarize_log(data)
            first_place_players = [p for p in result['summary'] if p['rank'] == 1]
            if first_place_players:
                winner_name = first_place_players[0]['name']
            else:
                winner_name = 'NOWINNER'
        except Exception:
            winner_name = 'UNKNOWN'

        # 生成新文件名：日期_时间_第一名玩家.json
        time_str = timestamp.strftime("%H%M%S")
        new_filename = f"{date_folder_name}_{time_str}_{winner_name}.json"

        return new_filename, date_folder_name

    except Exception:
        return None, None

def organize_folder(folder_path, dry_run=False):
    """
    整理指定文件夹中的牌谱文件

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

    # ========== 阶段1：找到所有非标准化文件并移到根目录 ==========
    print("阶段 1/3: 扫描并移动非标准化文件到根目录\n")

    non_standard_files = []
    moved_to_root_count = 0

    # 递归扫描所有JSON文件
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if not f.endswith('.json'):
                continue

            file_path = os.path.join(root, f)

            # 检查是否在根目录
            is_in_root = (os.path.dirname(file_path) == folder_path)

            # 检查文件名是否标准化
            if not is_standard_filename(f):
                if is_in_root:
                    # 已经在根目录，直接记录
                    non_standard_files.append(file_path)
                else:
                    # 不在根目录，需要移动
                    target_path = os.path.join(folder_path, f)

                    if dry_run:
                        print(f"📋 预览移动到根目录: {os.path.relpath(file_path, folder_path)} -> {f}")
                        non_standard_files.append(file_path)  # 预览模式仍使用原路径
                        moved_to_root_count += 1
                    else:
                        # 检查目标是否已存在
                        if os.path.exists(target_path):
                            print(f"⚠️  {os.path.relpath(file_path, folder_path)}: 根目录已存在同名文件，移动到errors")
                            move_to_error(file_path, "move-to-root-conflict")
                        else:
                            shutil.move(file_path, target_path)
                            print(f"✓ 移动到根目录: {os.path.relpath(file_path, folder_path)} -> {f}")
                            non_standard_files.append(target_path)
                            moved_to_root_count += 1

    if not non_standard_files:
        print("✓ 没有需要整理的非标准化文件\n")
        return 0, 0

    print(f"\n阶段1完成：移动了 {moved_to_root_count} 个文件到根目录")
    print(f"找到 {len(non_standard_files)} 个非标准化文件需要重命名\n")

    # ========== 阶段2：标准化重命名并去重 ==========
    print("阶段 2/3: 标准化重命名并去重\n")

    file_info_list = []  # 存储文件信息：(当前路径, 标准文件名, 日期文件夹名, 内容hash)
    renamed_count = 0
    error_count = 0

    for file_path in non_standard_files:
        filename = os.path.basename(file_path)

        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取标准文件名
            new_filename, date_folder_name = get_standard_filename(data)

            if not new_filename or not date_folder_name:
                print(f"❌ {filename}: 无法生成标准文件名")
                if not dry_run:
                    move_to_error(file_path, "invalid-data")
                error_count += 1
                continue

            # 计算内容hash用于去重
            canonical_content = json.dumps(data, ensure_ascii=False, sort_keys=True)

            # 检查是否需要重命名
            if filename != new_filename:
                if not dry_run:
                    new_path_in_root = os.path.join(folder_path, new_filename)

                    # 检查目标文件名是否已存在
                    if os.path.exists(new_path_in_root):
                        print(f"⚠️  {filename}: 重命名目标 {new_filename} 已存在，移动到errors")
                        move_to_error(file_path, "rename-target-exists")
                        error_count += 1
                        continue
                    else:
                        shutil.move(file_path, new_path_in_root)
                        print(f"✏️  重命名: {filename} -> {new_filename}")
                        file_info_list.append((new_path_in_root, new_filename, date_folder_name, canonical_content))
                        renamed_count += 1
                else:
                    print(f"✏️  预览重命名: {filename} -> {new_filename}")
                    file_info_list.append((file_path, new_filename, date_folder_name, canonical_content))
                    renamed_count += 1
            else:
                file_info_list.append((file_path, filename, date_folder_name, canonical_content))

        except Exception as e:
            print(f"❌ {filename}: 处理失败 - {str(e)}")
            if not dry_run:
                move_to_error(file_path, "processing-error")
            error_count += 1

    print(f"\n阶段2完成：重命名了 {renamed_count} 个文件\n")

    # ========== 阶段3：移动到日期文件夹并去重 ==========
    print("阶段 3/3: 移动到日期文件夹并去重\n")

    target_records = {}  # 记录目标文件：{(日期, 文件名): {'content': ..., 'current_path': ...}}
    moved_count = 0
    duplicate_removed = 0
    duplicate_conflicts = 0
    date_groups = defaultdict(list)

    for current_path, filename, date_folder_name, canonical_content in file_info_list:
        # 检查文件是否还存在（可能在阶段2被移到errors）
        if not dry_run and not os.path.exists(current_path):
            continue

        date_folder_path = os.path.join(folder_path, date_folder_name)
        target_path = os.path.join(date_folder_path, filename)
        target_key = (date_folder_name, filename)

        existing_entry = target_records.get(target_key)

        if existing_entry:
            existing_rel = os.path.relpath(existing_entry['current_path'], folder_path)
            current_rel = filename if dry_run else os.path.relpath(current_path, folder_path)

            if canonical_content == existing_entry['content']:
                # 完全重复，移动到errors文件夹
                if dry_run:
                    print(f"🗑️  预览移动重复牌谱到errors: {current_rel}（与 {existing_rel} 完全相同）")
                else:
                    move_to_error(current_path, "duplicate")
                duplicate_removed += 1
                continue
            else:
                # 内容不同的重名牌谱 -> 全部移到errors
                print(f"⚠️  发现内容不同但命名相同的牌谱: {current_rel} 与 {existing_rel}")
                if dry_run:
                    print("   预览：两个文件都将被移动到 game-logs/errors/ 目录")
                else:
                    move_to_error(current_path, "duplicate-conflict")
                    move_to_error(existing_entry['current_path'], "duplicate-conflict")
                duplicate_conflicts += 1
                error_count += 2
                target_records.pop(target_key, None)
                continue

        # 记录这个文件
        target_records[target_key] = {
            'content': canonical_content,
            'current_path': current_path
        }

        # 移动到日期文件夹
        date_groups[date_folder_name].append(filename)

        if dry_run:
            print(f"📋 预览移动: {filename} -> {date_folder_name}/{filename}")
            moved_count += 1
        else:
            # 创建日期文件夹（如果不存在）
            if not os.path.exists(date_folder_path):
                os.makedirs(date_folder_path)
                print(f"📁 创建文件夹: {date_folder_name}/")

            # 移动文件
            shutil.move(current_path, target_path)
            print(f"✓ 移动: {filename} -> {date_folder_name}/{filename}")
            target_records[target_key]['current_path'] = target_path
            moved_count += 1

    # 打印统计信息
    print(f"\n{'-'*80}")
    print("整理完成统计：")
    print(f"{'-'*80}")
    if dry_run:
        print(f"  预览模式（未实际操作）")
    print(f"  总文件数: {len(non_standard_files)}")
    print(f"  {'将'if dry_run else '已'}移动到根目录: {moved_to_root_count} 个文件")
    print(f"  {'将'if dry_run else '已'}重命名: {renamed_count} 个文件")
    print(f"  {'将'if dry_run else '已'}移动到日期文件夹: {moved_count} 个文件")
    print(f"  错误: {error_count} 个文件")
    if duplicate_removed > 0:
        print(f"  {'将'if dry_run else ''}移动重复牌谱到errors: {duplicate_removed} 个")
    if duplicate_conflicts > 0:
        print(f"  重复冲突{'将'if dry_run else ''}移入errors: {duplicate_conflicts} 组")

    if date_groups:
        print(f"\n  按日期分组（{'将要'if dry_run else '已'}移动的文件）：")
        for date_name in sorted(date_groups.keys()):
            print(f"    {date_name}: {len(date_groups[date_name])} 个文件")

    print(f"{'-'*80}\n")

    return moved_to_root_count + renamed_count + moved_count, error_count


def auto_classify_files(dry_run=False):
    """
    自动检测并分类牌谱文件到正确的联赛文件夹

    返回：(分类成功数, 分类失败数)
    """
    print("\n" + "="*80)
    print("阶段 0: 自动检测并分类牌谱类型")
    print("="*80 + "\n")

    game_logs_root = "game-logs"
    m_league_folder = "game-logs/m-league"
    ema_folder = "game-logs/ema"

    # 确保目标文件夹存在
    os.makedirs(m_league_folder, exist_ok=True)
    os.makedirs(ema_folder, exist_ok=True)

    classified_count = 0
    error_count = 0

    # 扫描所有文件夹中的 JSON 文件
    all_json_files = []

    for root, dirs, files in os.walk(game_logs_root):
        # 跳过 errors 和 sanma 文件夹
        if 'errors' in root or 'sanma' in root:
            continue

        for f in files:
            if f.endswith('.json'):
                file_path = os.path.join(root, f)
                all_json_files.append(file_path)

    # 检测每个文件的类型
    for file_path in all_json_files:
        filename = os.path.basename(file_path)
        current_folder = os.path.dirname(file_path)

        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检测类型
            detected_type = detect_league_type(data)

            if detected_type is None:
                # 无法检测，跳过
                continue

            # 确定目标文件夹
            if detected_type == 'm-league':
                target_folder = m_league_folder
            elif detected_type == 'ema':
                target_folder = ema_folder
            else:
                continue

            # 检查文件是否已在正确的文件夹中
            if os.path.abspath(current_folder).startswith(os.path.abspath(target_folder)):
                # 已经在正确的文件夹中（包括子文件夹），跳过
                continue

            # 需要移动
            target_path = os.path.join(target_folder, filename)

            if dry_run:
                print(f"📋 预览分类: {os.path.relpath(file_path)} -> {detected_type}/{filename}")
                classified_count += 1
            else:
                # 检查目标是否已存在
                if os.path.exists(target_path):
                    print(f"⚠️  {filename}: 目标位置已存在同名文件，移动到errors")
                    move_to_error(file_path, "auto-classify-conflict")
                    error_count += 1
                else:
                    shutil.move(file_path, target_path)
                    print(f"✓ 自动分类: {filename} -> {detected_type}/")
                    classified_count += 1

        except Exception as e:
            print(f"❌ {filename}: 分类失败 - {str(e)}")
            error_count += 1

    if classified_count == 0 and error_count == 0:
        print("✓ 所有文件已在正确的位置\n")
    else:
        print(f"\n阶段0完成：{'将'if dry_run else '已'}分类 {classified_count} 个文件{', ' + str(error_count) + ' 个错误' if error_count > 0 else ''}\n")

    return classified_count, error_count

def main():
    """主函数"""
    # 检查是否为预览模式
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if dry_run:
        print("\n" + "="*80)
        print("🔍 预览模式 - 仅显示将要执行的操作，不会实际移动文件")
        print("="*80)

    # 阶段0：自动分类牌谱类型
    classified, classify_errors = auto_classify_files(dry_run)

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
        print(f"自动分类: 需要分类 {classified} 个文件{', ' + str(classify_errors) + ' 个错误' if classify_errors > 0 else ''}")
        print(f"M-League: 需要操作 {m_moved} 个文件{', ' + str(m_errors) + ' 个错误' if m_errors > 0 else ''}")
        print(f"EMA:      需要操作 {e_moved} 个文件{', ' + str(e_errors) + ' 个错误' if e_errors > 0 else ''}")
    else:
        print(f"自动分类: 已分类 {classified} 个文件{', ' + str(classify_errors) + ' 个错误' if classify_errors > 0 else ''}")
        print(f"M-League: 已操作 {m_moved} 个文件{', ' + str(m_errors) + ' 个错误' if m_errors > 0 else ''}")
        print(f"EMA:      已操作 {e_moved} 个文件{', ' + str(e_errors) + ' 个错误' if e_errors > 0 else ''}")
    print("="*80)

    if dry_run:
        print("\n提示：运行时不加 --dry-run 参数即可实际执行移动操作")

    # 如果有错误，返回非零退出码
    if classify_errors + m_errors + e_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
