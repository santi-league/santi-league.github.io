# -*- coding: utf-8 -*-
"""
S-League 配置文件

定义赛季信息、规则配置等
"""

# S-League赛季配置
SEASONS = {
    's0': {
        'name_zh': 'S0赛季',
        'name_en': 'Season 0',
        'description_zh': '测试用',
        'description_en': 'For Testing',
        'start_date_zh': '测试牌谱区间：2026年5月22日 - 2026年7月22日',
        'start_date_en': 'Test data range: May 22 - Jul 22, 2026',
        'rule_type': 'm-league',  # 使用M-League规则
        'data_folder': 'game-logs/s-league/s0',
        'finals_folder': 'game-logs/s-league/s0-finals',  # 最高位决定战牌谱（独立于常规赛数据）
        'enabled': True,
        'color': '#95a5a6'  # 赛季主题色（灰色，标识为测试赛季）
    },
    's1': {
        'name_zh': 'S1赛季',
        'name_en': 'Season 1',
        'description_zh': 'S-League首届最高位战',
        'description_en': 'S-League Inaugural Top Player Championship',
        'start_date_zh': '2026年7月23日 0点起',
        'start_date_en': 'Starting July 23, 2026 00:00',
        'rule_type': 'm-league',  # 使用M-League规则
        'data_folder': 'game-logs/s-league/s1',
        'finals_folder': 'game-logs/s-league/s1-finals',  # 最高位决定战牌谱（独立于常规赛数据）
        'enabled': True,
        'color': '#c15b42'  # 赛季主题色（红色）
    },
    # 未来赛季可以继续添加
    # 's2': {
    #     'name_zh': 'S2赛季',
    #     'name_en': 'Season 2',
    #     'description_zh': 'S-League第三赛季',
    #     'description_en': 'S-League Season 2',
    #     'start_date_zh': '2027年1月',
    #     'start_date_en': 'January 2027',
    #     'rule_type': 'm-league',
    #     'data_folder': 'game-logs/s-league/s2',
    #     'enabled': False,  # 未开始
    #     'color': '#3498db'  # 蓝色
    # }
}

# S-League专用规则配置（目前使用M-League规则）
RULE_CONFIG = {
    'origin_points': 25000,
    'uma_config': {1: 45000, 2: 5000, 3: -15000, 4: -35000},
    'total_points': 100000
}

# 页面配置
PAGE_CONFIG = {
    'title_zh': 'S-League 最高位战',
    'title_en': 'S-League Top Player Championship',
    'subtitle_zh': '最强雀士的巅峰对决',
    'subtitle_en': 'The Ultimate Mahjong Battle',
    'gradient_color_1': '#c15b42',  # 主题渐变色1
    'gradient_color_2': '#9c4732',  # 主题渐变色2
}

def get_enabled_seasons():
    """获取所有启用的赛季"""
    return {k: v for k, v in SEASONS.items() if v['enabled']}

def get_season_by_id(season_id):
    """根据ID获取赛季信息"""
    return SEASONS.get(season_id)
