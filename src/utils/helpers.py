# -*- coding: utf-8 -*-
"""
辅助函数模块
"""

import os
import re
from datetime import datetime


def sort_files_by_date(files):
    """
    按日期和文件编号排序文件
    返回按时间顺序排序的文件列表（从旧到新）
    """
    file_with_dates = []
    for fp in files:
        filename = os.path.basename(fp)
        match = re.match(r'(\d+)_(\d+)_(\d+)', filename)
        number_match = re.search(r'\((\d+)\)', filename)

        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            year = int(match.group(3))
            number = int(number_match.group(1)) if number_match else 0

            try:
                date_obj = datetime(year, month, day)
                file_with_dates.append((fp, date_obj, number))
            except ValueError:
                continue

    # 按日期和编号排序（从旧到新）
    file_with_dates.sort(key=lambda x: (x[1], x[2]))
    return [fp for fp, _, _ in file_with_dates]


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
