# -*- coding: utf-8 -*-
"""
S-League 最高位战模块

这个模块负责处理S-League赛季数据和页面生成
"""

from .config import SEASONS, RULE_CONFIG
from .page_generator import generate_all_s_league_pages

__all__ = ['SEASONS', 'RULE_CONFIG', 'generate_all_s_league_pages']
