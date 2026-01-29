# -*- coding: utf-8 -*-
"""
辅助函数模块
"""

import os
import re
import json
from datetime import datetime


def sort_files_by_date(files):
    """
    按JSON文件内部的时间戳排序文件
    返回按时间顺序排序的文件列表（从旧到新）

    时间戳位置：json['title'][1]
    格式："MM/DD/YYYY, HH:MM:SS AM/PM"
    例如："10/15/2025, 12:25:03 AM"

    如果有任何文件缺失时间戳，会抛出ValueError异常并列出所有缺失时间戳的文件
    """
    file_with_dates = []
    files_without_timestamp = []

    for fp in files:
        timestamp = None
        error_reason = None

        # 尝试从JSON文件中读取时间戳
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 获取 title[1] 中的时间戳
                title = data.get('title', [])
                if isinstance(title, list) and len(title) > 1:
                    timestamp_str = title[1]
                    # 解析时间戳："MM/DD/YYYY, HH:MM:SS AM/PM"
                    if timestamp_str[-1] == 'M':
                        timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
                    else:
                        timestamp = datetime.strptime(timestamp_str, "%d/%m/%Y, %H:%M:%S")
                else:
                    error_reason = "title字段不存在或格式错误"
        except json.JSONDecodeError as e:
            error_reason = f"JSON解析失败: {str(e)}"
        except ValueError as e:
            error_reason = f"时间戳格式错误: {str(e)}"
        except Exception as e:
            error_reason = f"读取失败: {str(e)}"

        # 如果无法从JSON获取时间戳，记录错误
        if timestamp is None:
            files_without_timestamp.append({
                'path': fp,
                'filename': os.path.basename(fp),
                'reason': error_reason or "未知原因"
            })
        else:
            file_with_dates.append((fp, timestamp))

    # 如果有文件缺失时间戳，抛出异常
    if files_without_timestamp:
        error_msg = f"\n{'='*80}\n❌ 错误：发现 {len(files_without_timestamp)} 个牌谱文件缺失时间戳\n{'='*80}\n"
        for i, file_info in enumerate(files_without_timestamp, 1):
            error_msg += f"\n{i}. 文件：{file_info['filename']}\n"
            error_msg += f"   路径：{file_info['path']}\n"
            error_msg += f"   原因：{file_info['reason']}\n"
        error_msg += f"\n{'='*80}\n"
        error_msg += "请确保所有牌谱JSON文件都包含有效的时间戳：json['title'][1]\n"
        error_msg += "格式：\"MM/DD/YYYY, HH:MM:SS AM/PM\"\n"
        error_msg += f"{'='*80}\n"
        raise ValueError(error_msg)

    # 按时间戳排序（从旧到新）
    file_with_dates.sort(key=lambda x: x[1])
    return [fp for fp, _ in file_with_dates]


def format_percentage(value, decimal_places=1):
    """
    格式化百分比

    Args:
        value: 小数值 (如 0.256)
        decimal_places: 小数位数

    Returns:
        str: 格式化的百分比字符串 (如 "25.6%")
    """
    if value is None:
        return "0.0%"
    return f"{value * 100:.{decimal_places}f}%"


def format_number(value, decimal_places=0):
    """
    格式化数字

    Args:
        value: 数值
        decimal_places: 小数位数

    Returns:
        str: 格式化的数字字符串
    """
    if value is None:
        return "0"
    if decimal_places == 0:
        return f"{int(value)}"
    return f"{value:.{decimal_places}f}"


def escape_html(text):
    """
    转义HTML特殊字符

    Args:
        text: 要转义的文本

    Returns:
        str: 转义后的文本
    """
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def get_latest_date_from_files(files):
    """
    从文件列表中获取最新日期

    Args:
        files: 文件路径列表

    Returns:
        str: 最新日期字符串 (格式: YYYY年MM月DD日)
    """
    if not files:
        return None

    sorted_files = sort_files_by_date(files)
    if not sorted_files:
        return None

    latest_file = sorted_files[-1]
    filename = os.path.basename(latest_file)
    match = re.match(r'(\d+)_(\d+)_(\d+)', filename)

    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        return f"{year}年{month}月{day}日"

    return None
