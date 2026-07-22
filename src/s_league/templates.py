# -*- coding: utf-8 -*-
"""
S-League HTML模板生成器

负责生成S-League相关的HTML页面
"""

import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.translations import TRANSLATIONS
from .config import SEASONS, PAGE_CONFIG


def generate_index_template(seasons_summary, lang='zh'):
    """
    生成S-League主页（赛季选择页面）

    参数:
        seasons_summary: 赛季摘要列表
        lang: 语言 ('zh' 或 'en')

    返回:
        str: HTML内容
    """
    t = TRANSLATIONS[lang]
    lang_code = 'zh-CN' if lang == 'zh' else 'en'
    other_lang = 'en' if lang == 'zh' else 'zh'
    other_page = 'index-en.html' if lang == 'zh' else 'index.html'
    home_page = '../index.html' if lang == 'zh' else '../index-en.html'

    title = PAGE_CONFIG['title_zh'] if lang == 'zh' else PAGE_CONFIG['title_en']
    subtitle = PAGE_CONFIG['subtitle_zh'] if lang == 'zh' else PAGE_CONFIG['subtitle_en']

    # 生成赛季卡片
    season_cards = ""
    for summary in seasons_summary:
        season_id = summary['season_id']
        season_info = summary['season_info']
        file_count = summary['file_count']
        has_data = summary['has_data']

        season_name = season_info['name_zh'] if lang == 'zh' else season_info['name_en']
        season_desc = season_info['description_zh'] if lang == 'zh' else season_info['description_en']
        season_date = season_info['start_date_zh'] if lang == 'zh' else season_info['start_date_en']
        season_color = season_info.get('color', '#667eea')

        # 赛季页面链接
        season_page = f"{season_id}.html" if lang == 'zh' else f"{season_id}-en.html"

        # 状态标签（按赛季配置的status字段：ended/ongoing/upcoming）
        season_status = season_info.get('status', 'ongoing' if has_data else 'upcoming')
        games_count_text = f"{file_count} {t['games']}" if lang == 'zh' else f"{file_count} games"

        if season_status == 'ended':
            status_label = f"{'已结束' if lang == 'zh' else 'Ended'} · {games_count_text}"
            status_class = "status-ended"
        elif season_status == 'ongoing':
            status_label = f"{'进行中' if lang == 'zh' else 'Ongoing'} · {games_count_text}"
            status_class = "status-active"
        else:
            status_label = "即将开始" if lang == 'zh' else "Coming Soon"
            status_class = "status-upcoming"

        season_cards += f"""
        <a href="{season_page}" class="season-card" style="--season-color: {season_color}">
            <div class="season-header">
                <h2>{season_name}</h2>
                <span class="season-status {status_class}">{status_label}</span>
            </div>
            <p class="season-description">{season_desc}</p>
            <p class="season-date">{season_date}</p>
            <div class="season-arrow">→</div>
        </a>
        """

    html = f"""<!DOCTYPE html>
<html lang="{lang_code}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: #f5f5f5;
            color: #333;
        }}

        .header {{
            background: linear-gradient(135deg, {PAGE_CONFIG['gradient_color_1']} 0%, {PAGE_CONFIG['gradient_color_2']} 100%);
            color: white;
            padding: 50px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
        }}

        .header h1 {{
            font-size: 48px;
            margin-bottom: 10px;
            font-weight: bold;
        }}

        .header .subtitle {{
            font-size: 20px;
            opacity: 0.95;
            margin-bottom: 20px;
        }}

        .lang-switch {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.2);
            padding: 10px 20px;
            border-radius: 20px;
            text-decoration: none;
            color: white;
            font-size: 14px;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}

        .lang-switch:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }}

        .back-link {{
            display: inline-block;
            margin-top: 15px;
            color: white;
            text-decoration: none;
            opacity: 0.9;
            font-size: 16px;
        }}

        .back-link:hover {{
            opacity: 1;
            text-decoration: underline;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        .intro {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .intro h2 {{
            color: {PAGE_CONFIG['gradient_color_1']};
            margin-bottom: 15px;
            font-size: 28px;
        }}

        .intro p {{
            font-size: 16px;
            line-height: 1.8;
            color: #666;
        }}

        .seasons-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}

        .season-card {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
            display: block;
            position: relative;
            overflow: hidden;
            border-left: 5px solid var(--season-color, #667eea);
        }}

        .season-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}

        .season-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, var(--season-color, #667eea) 0%, transparent 100%);
            opacity: 0.05;
            pointer-events: none;
        }}

        .season-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .season-header h2 {{
            font-size: 28px;
            color: var(--season-color, #667eea);
        }}

        .season-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }}

        .status-active {{
            background: #27ae60;
            color: white;
        }}

        .status-upcoming {{
            background: #95a5a6;
            color: white;
        }}

        .status-ended {{
            background: #7f8c8d;
            color: white;
        }}

        .season-description {{
            font-size: 16px;
            color: #555;
            margin-bottom: 10px;
            line-height: 1.6;
        }}

        .season-date {{
            font-size: 14px;
            color: #999;
            margin-bottom: 15px;
        }}

        .season-arrow {{
            text-align: right;
            font-size: 24px;
            color: var(--season-color, #667eea);
            font-weight: bold;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 36px;
            }}

            .seasons-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <a href="{other_page}" class="lang-switch">🌐 {t['switch_to_' + other_lang]}</a>
        <h1>{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <a href="{home_page}" class="back-link">← {t['back_home']}</a>
    </div>

    <div class="container">
        <div class="intro">
            <h2>{"S-League赛制" if lang == 'zh' else "S-League Rules"}</h2>
            <p>
                {"比赛采用M-League规则。每个赛季包含两个月的常规赛季，在常规赛季中成绩前四名的人可以进入最高位决定战（只对至少打了10个半庄的人计算位次），然后进行五个半庄的决定战，最高分获得者获得当赛季的S-League最高位头衔。" if lang == 'zh' else "Games follow M-League rules. Each season consists of a two-month regular season. The top four players (with at least 10 games played) advance to the Championship Finals, where they compete in five games. The player with the highest score wins the S-League Championship title for that season."}
            </p>
        </div>

        <div class="seasons-grid">
            {season_cards}
        </div>
    </div>
</body>
</html>
"""
    return html


def generate_season_page_template(season_data, lang='zh'):
    """
    生成单个赛季的统计页面

    参数:
        season_data: 赛季数据（from data_processor.process_season_data）
        lang: 语言

    返回:
        str: HTML内容
    """
    # S-League专用内容生成器（不含Rating/R值概念）
    from .content import (
        generate_recent_games_content_s_league,
        generate_ranking_content_s_league,
        generate_top5_leaderboards_content_s_league,
        generate_finals_content_s_league
    )
    from .data_processor import process_finals_data
    from generators.content_generators import generate_honor_games_content_for_tabs
    from extract_honor_games import extract_honor_games

    t = TRANSLATIONS[lang]
    season_info = season_data['season_info']
    stats_dict = season_data['stats_dict']
    league_avg = season_data['league_avg']
    recent_games = season_data['recent_games']
    latest_date = season_data['latest_date']

    season_id = [k for k, v in SEASONS.items() if v == season_info][0]
    season_name = season_info['name_zh'] if lang == 'zh' else season_info['name_en']

    # 生成各个标签页的内容
    recent_content = generate_recent_games_content_s_league(recent_games, stats_dict, t, lang)
    ranking_content = generate_ranking_content_s_league(stats_dict, t, league_avg, lang)
    leaderboard_content = generate_top5_leaderboards_content_s_league(stats_dict, t, lang)

    finals_data = process_finals_data(season_id)
    finals_content = generate_finals_content_s_league(finals_data, t, lang)

    honor_games_raw = extract_honor_games(season_info['data_folder'])
    honor_games = {
        'yakuman_sanbaiman_games': honor_games_raw.get('yakuman_sanbaiman', []),
        'rare_yaku_games': honor_games_raw.get('rare_yaku', [])
    }
    honor_content = generate_honor_games_content_for_tabs(honor_games, t, lang)

    # 荣誉牌谱内容复用M-League生成器，将其蓝紫配色替换为S-League的红色主题
    honor_content = _apply_red_theme(honor_content)

    # 页面链接
    other_lang = 'en' if lang == 'zh' else 'zh'
    other_page = f"{season_id}-en.html" if lang == 'zh' else f"{season_id}.html"
    index_page = "index.html" if lang == 'zh' else "index-en.html"

    # 日期信息
    date_info = f"{t['data_updated']}: {latest_date}" if latest_date else ""

    # 使用S-League专用模板（红色主题，仅牌谱历史/荣誉牌谱/总排名三个标签页）
    from generators.page_generators import generate_s_league_page

    html_content = generate_s_league_page(
        lang=lang,
        title=f"{season_name} - S-League",
        date_info=date_info,
        other_stats_page=other_page,
        current_index=index_page,
        switch_lang_text='English' if lang == 'zh' else '中文',
        back_home_text=t['back_home'],
        tab_texts={
            'recent': t['tab_recent'],
            'honor': t['tab_honor'],
            'ranking': t['tab_ranking'],
            'leaderboard': t['tab_leaderboard'],
            'finals': t['tab_finals']
        },
        recent_content=recent_content,
        honor_content=honor_content,
        ranking_content=ranking_content,
        leaderboard_content=leaderboard_content,
        finals_content=finals_content
    )

    return html_content


def _apply_red_theme(html_content):
    """将内容HTML中内联的M-League蓝紫配色替换为S-League红色主题"""
    return (
        html_content
        .replace('#667eea', '#c15b42')
        .replace('#764ba2', '#9c4732')
        .replace('102, 126, 234', '193, 91, 66')
    )
