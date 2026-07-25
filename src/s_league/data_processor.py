# -*- coding: utf-8 -*-
"""
S-League 数据处理器

负责处理S-League各赛季的牌谱数据
"""

import os
import sys
import json
import shutil

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from player_stats import calculate_player_stats, scan_files, summarize_log
from utils.helpers import sort_files_by_date
from .config import SEASONS, RULE_CONFIG
import re
from datetime import datetime, timedelta


def _read_display_timestamp(filepath):
    """
    从牌谱JSON读取真实时间戳（title[1]），并做时区调整 UTC+0 -> UTC+2
    （与网站其他日期显示保持一致）。读取/解析失败时返回None。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        title = data.get('title', [])
        if isinstance(title, list) and len(title) > 1:
            timestamp_str = title[1]
            if timestamp_str[-1] == 'M':
                timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
            else:
                timestamp = datetime.strptime(timestamp_str, "%d/%m/%Y, %H:%M:%S")
            return timestamp + timedelta(hours=2)
    except (json.JSONDecodeError, ValueError, IndexError, OSError):
        pass
    return None


def extract_latest_date(files):
    """从牌谱JSON内的时间戳（title[1]）中提取最新日期，时区调整UTC+0 -> UTC+2"""
    dates = [d for d in (_read_display_timestamp(fp) for fp in files) if d is not None]
    if dates:
        return max(dates).strftime("%Y年%m月%d日")
    return None


def sync_season_data(season_id):
    """
    从 game-logs/m-league/ 中扫描落在该赛季时间窗口 [start_time, end_time) 内的牌谱，
    复制到该赛季的 data_folder 中（已存在的文件名会跳过，不重复复制）。

    时间窗口按赛季配置的 start_time/end_time 字段判断（UTC+2显示时间），
    未配置 start_time 的赛季（如手工维护的测试赛季）不做自动同步。

    参数:
        season_id: 赛季ID (如 's0', 's1')

    返回:
        int: 本次新复制的文件数
    """
    if season_id not in SEASONS:
        raise ValueError(f"未知的赛季: {season_id}")

    season = SEASONS[season_id]
    start_time_str = season.get('start_time')

    if not start_time_str:
        return 0

    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_time_str = season.get('end_time')
    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S") if end_time_str else None

    data_folder = season['data_folder']
    os.makedirs(data_folder, exist_ok=True)

    existing_filenames = {os.path.basename(fp) for fp in scan_files(data_folder, "*.json", recursive=True)}

    copied = 0
    for fp in scan_files('game-logs/m-league', "*.json", recursive=True):
        filename = os.path.basename(fp)
        if filename in existing_filenames:
            continue

        display_timestamp = _read_display_timestamp(fp)
        if display_timestamp is None:
            continue
        if display_timestamp < start_time:
            continue
        if end_time is not None and display_timestamp >= end_time:
            continue

        shutil.copy2(fp, os.path.join(data_folder, filename))
        copied += 1

    return copied


def process_season_data(season_id):
    """
    处理指定赛季的数据

    参数:
        season_id: 赛季ID (如 's0', 's1')

    返回:
        dict: {
            'season_info': 赛季信息,
            'stats_dict': 玩家统计数据,
            'league_avg': 联盟平均数据,
            'recent_games': 最近对局,
            'sorted_files': 排序后的文件列表,
            'results': 处理结果列表,
            'latest_date': 最新日期
        }
    """
    if season_id not in SEASONS:
        raise ValueError(f"未知的赛季: {season_id}")

    season = SEASONS[season_id]
    data_folder = season['data_folder']

    # 扫描文件
    files = scan_files(data_folder, "*.json", recursive=True)

    if not files:
        return {
            'season_info': season,
            'stats_dict': {},
            'league_avg': {},
            'recent_games': [],
            'sorted_files': [],
            'results': [],
            'latest_date': None,
            'file_count': 0
        }

    # 按日期排序
    sorted_files = sort_files_by_date(files)

    # 处理每个文件
    results = []
    round_counts = []

    # 使用M-League规则的uma配置
    uma_config = RULE_CONFIG['uma_config']

    for fp in sorted_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 使用M-League规则处理
            summary = summarize_log(data, uma_config=uma_config)
            results.append(summary)
            round_counts.append(len(data.get("log", [])))
        except Exception as ex:
            print(f"  S-League处理失败: {fp} - {ex}", file=sys.stderr)

    # 提取最新日期
    latest_date = extract_latest_date(files)

    # 计算玩家统计
    if results:
        # 导入extract_recent_games
        from generate_website import extract_recent_games

        # 提取最近对局
        recent_games = extract_recent_games(
            sorted_files,
            results,
            count=len(sorted_files),
            uma_config=uma_config,
            origin_points=RULE_CONFIG['origin_points']
        )

        # 计算统计数据
        stats = calculate_player_stats(
            results,
            round_counts,
            uma_config=uma_config,
            origin_points=RULE_CONFIG['origin_points']
        )
        stats_dict = dict(stats)

        # 提取联盟平均
        league_avg = stats_dict.pop("_league_average", {})
    else:
        recent_games = []
        stats_dict = {}
        league_avg = {}

    return {
        'season_info': season,
        'stats_dict': stats_dict,
        'league_avg': league_avg,
        'recent_games': recent_games,
        'sorted_files': sorted_files,
        'results': results,
        'latest_date': latest_date,
        'file_count': len(files)
    }


def process_finals_data(season_id):
    """
    处理指定赛季的最高位决定战数据（与常规赛数据完全独立）

    参数:
        season_id: 赛季ID (如 's0', 's1')

    返回:
        dict: {
            'games': [每个半庄一个列表，元素为{'name','rank','final_points'}], ...],
            'dates': [每个半庄对应的日期字符串（已UTC+2调整）],
            'file_count': 牌谱文件数量
        }
    """
    if season_id not in SEASONS:
        raise ValueError(f"未知的赛季: {season_id}")

    season = SEASONS[season_id]
    finals_folder = season.get('finals_folder')

    if not finals_folder:
        return {'games': [], 'dates': [], 'file_count': 0}

    files = scan_files(finals_folder, "*.json", recursive=True)
    if not files:
        return {'games': [], 'dates': [], 'file_count': 0}

    sorted_files = sort_files_by_date(files)
    uma_config = RULE_CONFIG['uma_config']

    games = []
    dates = []

    for fp in sorted_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)

            result = summarize_log(data, uma_config=uma_config)
            summary = result.get('summary', [])
            games.append([
                {'name': p['name'], 'rank': p['rank'], 'final_points': p['final_points']}
                for p in summary
            ])

            title = data.get('title', [])
            date_str = None
            if isinstance(title, list) and len(title) > 1:
                timestamp_str = title[1]
                try:
                    if timestamp_str[-1] == 'M':
                        timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
                    else:
                        timestamp = datetime.strptime(timestamp_str, "%d/%m/%Y, %H:%M:%S")
                    date_str = (timestamp + timedelta(hours=2)).strftime("%Y年%m月%d日")
                except (ValueError, IndexError):
                    date_str = None
            dates.append(date_str)
        except Exception as ex:
            print(f"  S-League决定战处理失败: {fp} - {ex}", file=sys.stderr)

    return {'games': games, 'dates': dates, 'file_count': len(files)}


def get_all_seasons_summary():
    """
    获取所有赛季的摘要信息

    返回:
        list: 赛季摘要列表
    """
    summaries = []

    for season_id, season_info in SEASONS.items():
        if not season_info['enabled']:
            continue

        data_folder = season_info['data_folder']
        files = scan_files(data_folder, "*.json", recursive=True)

        summaries.append({
            'season_id': season_id,
            'season_info': season_info,
            'file_count': len(files) if files else 0,
            'has_data': len(files) > 0 if files else False
        })

    return summaries
