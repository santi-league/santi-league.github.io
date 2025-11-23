# -*- coding: utf-8 -*-
"""
生成静态网站

用法：
  python generate_website.py
"""

import os
import sys
import json
import re
import html as html_module
from datetime import datetime
from player_stats import calculate_player_stats, scan_files, summarize_log, YAKU_TRANSLATION
from template_renderer import render_m_league_tabs
from generate_m_league_tabs import generate_ranking_content

# 导入新的模块化组件
from config.translations import TRANSLATIONS, YAKU_TRANSLATION_EN
from generators.page_generators import generate_index_page, generate_ema_page, generate_sanma_honor_page
from utils.helpers import sort_files_by_date

# 为了向后兼容，保留原有的TRANSLATIONS变量
# TRANSLATIONS现在从config.translations导入


# sort_files_by_date现在从utils.helpers导入，但为了向后兼容保留原函数定义
def sort_files_by_date_old(files):
    """
    按日期和文件编号排序文件
    返回按时间顺序排序的文件列表（从旧到新）
    """
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
                file_with_dates.append((date_obj, file_number, fp))
            except ValueError:
                continue

    # 按日期和文件编号排序
    file_with_dates.sort(key=lambda x: (x[0], x[1]))
    return [fp for _, _, fp in file_with_dates]


def extract_latest_date(files):
    """从文件名列表中提取最新日期"""
    dates = []
    for fp in files:
        filename = os.path.basename(fp)
        # 匹配格式：月_日_年
        match = re.match(r'(\d+)_(\d+)_(\d+)', filename)
        if match:
            month, day, year = match.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                dates.append(date_obj)
            except ValueError:
                continue

    if dates:
        latest_date = max(dates)
        return latest_date.strftime("%Y年%m月%d日")
    return None


def extract_recent_games(files, results, count=5, all_results=None, uma_config=None, origin_points=25000):
    """
    提取最近的N个牌谱信息，包含R值计算详情

    参数:
    - uma_config: Uma配置字典，例如 {1: 15000, 2: 5000, 3: -5000, 4: -15000} (EMA)
                 默认为 {1: 45000, 2: 5000, 3: -15000, 4: -35000} (M-League)
    - origin_points: 起始分数/返点，M-League为25000，EMA为30000

    返回格式: [
        {
            'date': '2025年1月15日',
            'players_detail': [
                {
                    'name': '玩家名',
                    'rank': 1,
                    'final_points': 30000,
                    'r_before': 1500.0,
                    'games_before': 10,
                    'score_change': 50.0,  # (uma + 素点差) / 1000
                    'r_correction': 0.0,   # (桌平均R - 玩家R) / 40
                    'games_correction': 0.8,  # 试合数补正系数
                    'r_change': 40.0,
                    'r_after': 1540.0
                },
                ...
            ],
            'table_avg_r': 1500.0
        },
        ...
    ]
    """
    from collections import defaultdict
    from player_stats import calculate_tenhou_r_value

    # 设置默认UMA配置（M-League）
    if uma_config is None:
        uma_config = {1: 45000, 2: 5000, 3: -15000, 4: -35000}

    # 创建文件和结果的映射，按时间顺序排序
    file_result_pairs = []
    files_without_timestamp = []

    for fp, result in zip(files, results):
        # 尝试从JSON中读取完整的时间戳
        timestamp = None
        error_reason = None

        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
                title = data.get('title', [])
                if isinstance(title, list) and len(title) > 1:
                    timestamp_str = title[1]
                    # 解析时间戳："MM/DD/YYYY, HH:MM:SS AM/PM"
                    timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
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
            file_result_pairs.append((timestamp, fp, result))

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

    # 按时间升序排序（从旧到新）
    file_result_pairs.sort(key=lambda x: x[0])

    # 追踪所有玩家的R值和场数
    player_r_values = defaultdict(lambda: 1500.0)
    player_games = defaultdict(int)

    # 计算所有游戏的R值（为了得到最近几场的R值状态）
    all_game_details = []

    for timestamp, fp, result in file_result_pairs:
        summary = result.get('summary', [])

        # 计算这局的桌平均R值
        table_players = [p.get('name', '') for p in summary if p.get('name')]
        table_avg_r = sum(player_r_values[name] for name in table_players) / len(table_players) if table_players else 1500.0

        # 计算每个玩家的R值变化
        players_detail = []
        for player_stat in summary:
            name = player_stat.get('name', '')
            if not name:
                continue

            rank = player_stat.get('rank', 4)
            final_points = player_stat.get('final_points', 25000)
            games_before = player_games[name]
            r_before = player_r_values[name]

            # 使用平均uma（如果有的话），否则回退到按名次查表
            avg_uma = player_stat.get('avg_uma')
            if avg_uma is not None:
                uma = avg_uma
            else:
                # 回退方案：按名次查表
                uma = uma_config.get(rank, 0)

            score_diff = final_points - origin_points
            score_change = (uma + score_diff) / 1000.0

            # 计算R值补正
            r_correction = (table_avg_r - r_before) / 40.0

            # 计算试合数补正
            if games_before < 400:
                games_correction = 1 - games_before * 0.002
            else:
                games_correction = 0.2

            # 计算R值变动（传入uma_config、origin_points和avg_uma）
            r_change = calculate_tenhou_r_value(rank, games_before, r_before, table_avg_r, final_points, uma_config, origin_points, avg_uma=uma)
            r_after = r_before + r_change

            players_detail.append({
                'name': name,
                'rank': rank,
                'final_points': final_points,
                'r_before': round(r_before, 2),
                'games_before': games_before,
                'score_change': round(score_change, 1),
                'r_correction': round(r_correction, 2),
                'games_correction': round(games_correction, 3),
                'r_change': round(r_change, 2),
                'r_after': round(r_after, 2)
            })

            # 更新玩家R值和场数
            player_r_values[name] = r_after
            player_games[name] += 1

        # 按名次排序
        players_detail.sort(key=lambda x: x['rank'])

        all_game_details.append({
            'date': timestamp.strftime("%Y年%m月%d日 %H:%M"),
            'date_en': timestamp.strftime("%Y-%m-%d %H:%M"),
            'players_detail': players_detail,
            'table_avg_r': round(table_avg_r, 2)
        })

    # 返回最近的N场，反转顺序让最新的在前面
    recent = all_game_details[-count:] if len(all_game_details) >= count else all_game_details
    return list(reversed(recent))


def generate_index_html(lang='zh'):
    """生成首页 - 使用新的模块化生成器"""
    return generate_index_page(lang)


def generate_stats_html(title, stats_data, league_name, latest_date=None, lang='zh', honor_games=None, recent_games=None):
    """生成统计页面"""
    t = TRANSLATIONS[lang]
    lang_code = 'zh-CN' if lang == 'zh' else 'en'
    other_lang = 'en' if lang == 'zh' else 'zh'

    # 根据语言确定其他页面的链接
    if league_name == 'm-league':
        other_stats_page = 'm-league-en.html' if lang == 'zh' else 'm-league.html'
        other_index = 'index-en.html' if lang == 'zh' else 'index.html'  # 语言切换用
        current_index = 'index.html' if lang == 'zh' else 'index-en.html'  # 返回首页用
    else:  # ema
        other_stats_page = 'ema-en.html' if lang == 'zh' else 'ema.html'
        other_index = 'index-en.html' if lang == 'zh' else 'index.html'  # 语言切换用
        current_index = 'index.html' if lang == 'zh' else 'index-en.html'  # 返回首页用

    # 提取并移除league_average
    league_avg = stats_data.pop("_league_average", {})

    # 按对局数降序排序（排除_league_average）
    sorted_players = sorted(stats_data.items(), key=lambda x: (-x[1]["games"], x[0]))

    # 日期信息
    date_info = f"<p class='date-info'>{t['data_updated']}: {latest_date}</p>" if latest_date else ""

    # 最近牌谱部分 - 横向表格
    recent_section = ""
    if recent_games and len(recent_games) > 0:
        table_rows = ""
        for game_idx, game in enumerate(recent_games, 1):
            date_str = game['date'] if lang == 'zh' else game['date_en']
            table_avg_r = game.get('table_avg_r', 0)

            # 每一局占一行，包含日期、桌平均R和4个玩家的数据
            players_data = game.get('players_detail', [])

            # 构建玩家数据单元格
            player_cells = ""
            for p in players_data:
                rank_class = f"rank-{p['rank']}"
                player_cells += f"""
                    <td class="player-name {rank_class}">{p['name']}</td>
                    <td class="r-value">{p['r_before']}</td>
                    <td class="games-count">{p['games_before']}</td>
                    <td class="score-change">{p['score_change']:+.1f}</td>
                    <td class="r-correction">{p['r_correction']:+.2f}</td>
                    <td class="games-coef">{p['games_correction']:.3f}</td>
                    <td class="r-change">{p['r_change']:+.2f}</td>
                    <td class="r-value">{p['r_after']}</td>
                """

            table_rows += f"""
                <tr>
                    <td class="game-date">{date_str}</td>
                    <td class="table-avg-r">{table_avg_r:.2f}</td>
                    {player_cells}
                </tr>
            """

        recent_section = f"""
        <div class="recent-games-section">
            <h2>{t['recent_games']}</h2>
            <div class="table-scroll">
                <table class="recent-games-table">
                    <thead>
                        <tr>
                            <th rowspan="2">{t['game_date']}</th>
                            <th rowspan="2">{t['table_avg_r']}</th>
                            <th colspan="8">{t['player']}1</th>
                            <th colspan="8">{t['player']}2</th>
                            <th colspan="8">{t['player']}3</th>
                            <th colspan="8">{t['player']}4</th>
                        </tr>
                        <tr>
                            <th>{t['player']}</th>
                            <th>{t['r_before']}</th>
                            <th>{t['games_count']}</th>
                            <th>{t['score_change_pt']}</th>
                            <th>{t['r_correction']}</th>
                            <th>{t['games_coef']}</th>
                            <th>{t['r_change']}</th>
                            <th>{t['r_after']}</th>

                            <th>{t['player']}</th>
                            <th>{t['r_before']}</th>
                            <th>{t['games_count']}</th>
                            <th>{t['score_change_pt']}</th>
                            <th>{t['r_correction']}</th>
                            <th>{t['games_coef']}</th>
                            <th>{t['r_change']}</th>
                            <th>{t['r_after']}</th>

                            <th>{t['player']}</th>
                            <th>{t['r_before']}</th>
                            <th>{t['games_count']}</th>
                            <th>{t['score_change_pt']}</th>
                            <th>{t['r_correction']}</th>
                            <th>{t['games_coef']}</th>
                            <th>{t['r_change']}</th>
                            <th>{t['r_after']}</th>

                            <th>{t['player']}</th>
                            <th>{t['r_before']}</th>
                            <th>{t['games_count']}</th>
                            <th>{t['score_change_pt']}</th>
                            <th>{t['r_correction']}</th>
                            <th>{t['games_coef']}</th>
                            <th>{t['r_change']}</th>
                            <th>{t['r_after']}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        """

    # 荣誉牌谱部分
    honor_section = ""
    if honor_games and len(honor_games) > 0:
        honor_cards = ""
        for game in honor_games:
            # 翻译役种
            yaku_list = game.get('yaku_list', [])
            if lang == 'zh':
                translated_yaku = ', '.join([YAKU_TRANSLATION.get(y.split('(')[0], y) for y in yaku_list])
            else:
                translated_yaku = ', '.join([YAKU_TRANSLATION_EN.get(y.split('(')[0], y) if '(' in y else y for y in yaku_list])

            game_type = game.get('type', 'yakuman')
            game_type_text = t['yakuman'] if game_type == 'yakuman' else t['sanbaiman']
            game_type_class = 'yakuman' if game_type == 'yakuman' else 'sanbaiman'

            # HTML转义URL中的特殊字符
            escaped_url = html_module.escape(game['tenhou_url'], quote=True)

            honor_cards += f"""
            <div class="honor-card {game_type_class}">
                <div class="honor-type">{game_type_text}</div>
                <div class="honor-info">
                    <div class="honor-date">{game['date']}</div>
                    <div class="honor-round">{game['round']}</div>
                    <div class="honor-winner">{game['winner']}</div>
                    <div class="honor-yaku">{translated_yaku}</div>
                </div>
                <a href="{escaped_url}" target="_blank" class="honor-replay-btn">{t['view_replay']}</a>
            </div>
            """

        honor_section = f"""
        <div class="honor-games-section">
            <h2>{t['honor_games']}</h2>
            <div class="honor-games-grid">
                {honor_cards}
            </div>
        </div>
        """

    # 生成表格行
    table_rows = ""
    for name, data in sorted_players:
        # 使用锚点链接
        player_id = name.replace(" ", "_").replace("(", "").replace(")", "")
        table_rows += f"""
        <tr>
            <td class="player-name"><a href="#player-{player_id}" class="player-link">{name}</a></td>
            <td>{data['games']}</td>
            <td>{data['total_rounds']}</td>
            <td class="highlight">{data['tenhou_r']:.2f}</td>
            <td>{data['total_score']:+}</td>
            <td>{data['avg_rank']:.2f}</td>
            <td>{data['rank_1_rate']:.1f}%</td>
            <td>{data['win_rate']:.1f}%</td>
            <td>{data['deal_in_rate']:.1f}%</td>
            <td>{data['riichi_rate']:.1f}%</td>
            <td>{data['furo_rate']:.1f}%</td>
        </tr>
        """

    # 生成详细统计卡片
    detail_cards = ""
    for name, data in sorted_players:
        player_id = name.replace(" ", "_").replace("(", "").replace(")", "")
        riichi_win_hands = data['riichi_win_hands']
        furo_then_win_hands = data['furo_then_win_hands']
        dama_win_hands = data.get('dama_win_hands', 0)
        tsumo_only_win_hands = data.get('tsumo_only_win_hands', 0)

        # 手役统计（前10）
        yaku_html = ""
        if data.get('yaku_count'):
            yaku_sorted = sorted(data['yaku_count'].items(), key=lambda x: -x[1])[:10]
            for yaku, count in yaku_sorted:
                # 根据语言选择役种翻译
                if lang == 'zh':
                    # 如果是英文役种，翻译成中文；如果已经是中文，保持不变
                    yaku_name = YAKU_TRANSLATION.get(yaku, yaku)
                else:  # English
                    # 如果是中文役种，翻译回英文；如果已经是英文，保持不变
                    yaku_name = YAKU_TRANSLATION_EN.get(yaku, yaku)
                rate = data['yaku_rate'].get(yaku, 0)
                avg_rate = league_avg.get('yaku_rate', {}).get(yaku, 0) if league_avg else 0
                avg_text = f' <span class="league-avg">({t["average"]}{avg_rate}%)</span>' if avg_rate > 0 else ''
                yaku_html += f"<li>{yaku_name}: {count}{t['times']} ({rate}%){avg_text}</li>"

        # 对战情况表格
        vs_players_html = ""
        if data.get('vs_players'):
            # 按对战场数排序
            vs_sorted = sorted(data['vs_players'].items(), key=lambda x: -x[1]['games'])
            vs_players_html = f"""
            <table class="vs-table">
                <thead>
                    <tr>
                        <th>{t['opponent']}</th>
                        <th>{t['games_count']}</th>
                        <th>{t['win_rate_vs']}</th>
                        <th>{t['win_points']}</th>
                        <th>{t['lose_points']}</th>
                        <th>{t['net_points']}</th>
                        <th>{t['score_diff']}</th>
                    </tr>
                </thead>
                <tbody>
            """
            for opponent, vs_data in vs_sorted:
                net_points = vs_data['net_points']
                net_class = 'positive' if net_points > 0 else 'negative' if net_points < 0 else 'neutral'
                score_diff = vs_data['score_diff']
                score_diff_class = 'positive' if score_diff > 0 else 'negative' if score_diff < 0 else 'neutral'
                opponent_id = opponent.replace(" ", "_").replace("(", "").replace(")", "")
                vs_players_html += f"""
                    <tr>
                        <td class="opponent-name"><a href="#player-{opponent_id}" class="opponent-link">{opponent}</a></td>
                        <td>{vs_data['games']}</td>
                        <td>{vs_data['win_rate']:.1f}%</td>
                        <td class="positive">+{vs_data['win_points']}</td>
                        <td class="negative">-{vs_data['lose_points']}</td>
                        <td class="{net_class}">{net_points:+}</td>
                        <td class="{score_diff_class}">{score_diff:+}</td>
                    </tr>
                """
            vs_players_html += """
                </tbody>
            </table>
            """

        detail_cards += f"""
        <div class="player-card" id="player-{player_id}">
            <h3>{name}</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">{t['tenhou_r']}</div>
                    <div class="stat-value large">{data['tenhou_r']:.2f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">{t['total_score']}</div>
                    <div class="stat-value">{data['total_score']:+}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">{t['avg_rank']}</div>
                    <div class="stat-value">{data['avg_rank']:.2f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">{t['games_count']}</div>
                    <div class="stat-value">{data['games']} {t['games']}</div>
                </div>
            </div>

            <div class="section">
                <h4>{t['rank_distribution']}</h4>
                <div class="rank-bars">
                    <div class="rank-bar">
                        <span class="rank-label">{t['rank_1']}</span>
                        <div class="bar-container">
                            <div class="bar bar-1" style="width: {data['rank_1_rate']}%"></div>
                            <span class="bar-text">{data['rank_1']} {t['times']} ({data['rank_1_rate']:.1f}%)</span>
                        </div>
                    </div>
                    <div class="rank-bar">
                        <span class="rank-label">{t['rank_2']}</span>
                        <div class="bar-container">
                            <div class="bar bar-2" style="width: {data['rank_2_rate']}%"></div>
                            <span class="bar-text">{data['rank_2']} {t['times']} ({data['rank_2_rate']:.1f}%)</span>
                        </div>
                    </div>
                    <div class="rank-bar">
                        <span class="rank-label">{t['rank_3']}</span>
                        <div class="bar-container">
                            <div class="bar bar-3" style="width: {data['rank_3_rate']}%"></div>
                            <span class="bar-text">{data['rank_3']} {t['times']} ({data['rank_3_rate']:.1f}%)</span>
                        </div>
                    </div>
                    <div class="rank-bar">
                        <span class="rank-label">{t['rank_4']}</span>
                        <div class="bar-container">
                            <div class="bar bar-4" style="width: {data['rank_4_rate']}%"></div>
                            <span class="bar-text">{data['rank_4']} {t['times']} ({data['rank_4_rate']:.1f}%)</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h4>{t['win_stats']}</h4>
                <div class="summary-box">
                    <span class="summary-label">{t['total_wins']}:</span>
                    <span class="summary-value">{data['win_hands']} {t['rounds']} ({data['win_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('win_rate', 0):.1f}%)</span></span>
                    <span class="summary-label">{t['avg_points']}:</span>
                    <span class="summary-value">{data['avg_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_win_points', 0):.0f}{t['points']})</span></span>
                </div>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>{t['type']}</th>
                            <th>{t['count']}</th>
                            <th>{t['avg_points']}</th>
                            <th>{t['special_stats']}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="type-label">{t['riichi_win']}</td>
                            <td>{riichi_win_hands} {t['rounds']}</td>
                            <td class="points-value">{data['avg_riichi_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_riichi_win_points', 0):.0f})</span></td>
                            <td class="special-stats">{t['ippatsu']}: {data['ippatsu_hands']}{t['rounds']} ({data['ippatsu_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('ippatsu_rate', 0):.1f}%)</span> · {t['ura']}: {data['ura_hands']}{t['rounds']} ({data['ura_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('ura_rate', 0):.1f}%)</span></td>
                        </tr>
                        <tr>
                            <td class="type-label">{t['furo_win']}</td>
                            <td>{furo_then_win_hands} {t['rounds']}</td>
                            <td class="points-value">{data['avg_furo_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_furo_win_points', 0):.0f})</span></td>
                            <td class="special-stats">-</td>
                        </tr>
                        {f'''<tr>
                            <td class="type-label">{t['dama_win']}</td>
                            <td>{dama_win_hands} {t['rounds']}</td>
                            <td class="points-value">{data['avg_dama_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_dama_win_points', 0):.0f})</span></td>
                            <td class="special-stats">{t['has_yaku_menzen']}</td>
                        </tr>''' if dama_win_hands > 0 else ''}
                        {f'''<tr>
                            <td class="type-label">{t['tsumo_only_win']}</td>
                            <td>{tsumo_only_win_hands} {t['rounds']}</td>
                            <td class="points-value">{data['avg_tsumo_only_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_tsumo_only_win_points', 0):.0f})</span></td>
                            <td class="special-stats">{t['menzen_tsumo']}</td>
                        </tr>''' if tsumo_only_win_hands > 0 else ''}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h4>{t['riichi_furo']}</h4>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>{t['type']}</th>
                            <th>{t['count_rate']}</th>
                            <th>{t['win']}</th>
                            <th>{t['draw']}</th>
                            <th>{t['deal_in']}</th>
                            <th>{t['pass']}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="type-label">{t['riichi']}</td>
                            <td>{data['riichi_hands']} {t['rounds']} ({data['riichi_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('riichi_rate', 0):.1f}%)</span></td>
                            <td class="rate-good">{data['riichi_win_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('riichi_win_rate', 0):.1f}%)</span></td>
                            <td class="rate-neutral">{data['riichi_ryuukyoku_rate']:.1f}%</td>
                            <td class="rate-bad">{data['riichi_then_deal_in_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('riichi_then_deal_in_rate', 0):.1f}%)</span></td>
                            <td class="rate-neutral">{data['riichi_pass_rate']:.1f}%</td>
                        </tr>
                        <tr>
                            <td class="type-label">{t['furo']}</td>
                            <td>{data['furo_hands']} {t['rounds']} ({data['furo_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('furo_rate', 0):.1f}%)</span></td>
                            <td class="rate-good">{data['furo_then_win_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('furo_then_win_rate', 0):.1f}%)</span></td>
                            <td class="rate-neutral">{data['furo_ryuukyoku_rate']:.1f}%</td>
                            <td class="rate-bad">{data['furo_then_deal_in_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('furo_then_deal_in_rate', 0):.1f}%)</span></td>
                            <td class="rate-neutral">{data['furo_pass_rate']:.1f}%</td>
                        </tr>
                        {f'''<tr>
                            <td class="type-label">{t['dama']}</td>
                            <td>{data['dama_state_hands']} {t['times']}</td>
                            <td class="rate-good">{data['dama_state_win_rate']:.1f}%</td>
                            <td class="rate-neutral">{data['dama_state_draw_rate']:.1f}%</td>
                            <td class="rate-bad">{data['dama_state_deal_in_rate']:.1f}%</td>
                            <td class="rate-neutral">{data['dama_state_pass_rate']:.1f}%</td>
                        </tr>''' if data.get('dama_state_hands', 0) > 0 else ''}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h4>{t['deal_in_stats']}</h4>
                <div class="summary-box">
                    <span class="summary-label">{t['deal_in']}:</span>
                    <span class="summary-value">{data['deal_in_hands']} {t['rounds']} ({data['deal_in_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('deal_in_rate', 0):.1f}%)</span></span>
                    <span class="summary-label">{t['avg_deal_in_points']}:</span>
                    <span class="summary-value negative">{data['avg_deal_in_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_deal_in_points', 0):.0f}{t['points']})</span></span>
                </div>
            </div>

            {f'''<div class="section">
                <h4>{t['vs_stats']}</h4>
                {vs_players_html}
            </div>''' if vs_players_html else ''}

            {f'''<div class="section">
                <h4>{t['yaku_stats']}</h4>
                <ul class="yaku-list">
                    {yaku_html}
                </ul>
            </div>''' if yaku_html else ''}

            {f'''<div class="section">
                <h4>{t['draw_tenpai']}</h4>
                <p>{t['draw_count']}: {data['ryuukyoku_hands']} {t['times']}, {t['tenpai']} {data['ryuukyoku_tenpai']} {t['times']} ({data['tenpai_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('tenpai_rate', 0):.1f}%)</span></p>
            </div>''' if data['ryuukyoku_hands'] > 0 else ''}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="{lang_code}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Santi League</title>
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
        }}

        .header h1 {{
            font-size: 36px;
            margin-bottom: 10px;
        }}

        .date-info {{
            font-size: 16px;
            margin: 10px 0;
            opacity: 0.9;
        }}

        .back-link {{
            display: inline-block;
            margin-top: 10px;
            color: white;
            text-decoration: none;
            opacity: 0.9;
        }}

        .back-link:hover {{
            opacity: 1;
            text-decoration: underline;
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

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        .summary-table {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow-x: auto;
            margin-bottom: 30px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px 10px;
            text-align: center;
            font-weight: 600;
        }}

        td {{
            padding: 12px 10px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .player-name {{
            font-weight: bold;
        }}

        .player-link {{
            color: #667eea;
            text-decoration: none;
            transition: color 0.2s ease;
        }}

        .player-link:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}

        .highlight {{
            background: #fff3cd;
            font-weight: bold;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        h2 {{
            margin: 40px 0 20px 0;
            color: #667eea;
            font-size: 28px;
        }}

        .player-card {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .player-card h3 {{
            color: #667eea;
            font-size: 24px;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .stat-item {{
            text-align: center;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
        }}

        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}

        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-value.large {{
            font-size: 32px;
        }}

        .section {{
            margin-top: 25px;
        }}

        .section h4 {{
            color: #555;
            margin-bottom: 12px;
            font-size: 18px;
        }}

        .section p {{
            line-height: 1.8;
            color: #666;
        }}

        .section ul {{
            margin-left: 20px;
            line-height: 1.8;
            color: #666;
        }}

        .rank-bars {{
            margin-top: 10px;
        }}

        .rank-bar {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}

        .rank-label {{
            width: 50px;
            font-weight: bold;
        }}

        .bar-container {{
            flex: 1;
            position: relative;
            height: 30px;
            background: #f0f0f0;
            border-radius: 5px;
            overflow: hidden;
        }}

        .bar {{
            height: 100%;
            transition: width 0.3s ease;
            border-radius: 5px;
        }}

        .bar-1 {{ background: linear-gradient(90deg, #28a745, #5cb85c); }}
        .bar-2 {{ background: linear-gradient(90deg, #17a2b8, #5bc0de); }}
        .bar-3 {{ background: linear-gradient(90deg, #ffc107, #ffda6a); }}
        .bar-4 {{ background: linear-gradient(90deg, #dc3545, #e66a73); }}

        .bar-text {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 12px;
            font-weight: bold;
            color: #333;
        }}

        .yaku-list {{
            columns: 2;
            column-gap: 20px;
        }}

        .yaku-list li {{
            break-inside: avoid;
            margin-bottom: 5px;
        }}

        .vs-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 14px;
        }}

        .vs-table th {{
            background: #667eea;
            color: white;
            padding: 10px 8px;
            text-align: center;
            font-weight: 600;
        }}

        .vs-table td {{
            padding: 8px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}

        .vs-table tr:hover {{
            background: #f9f9f9;
        }}

        .vs-table .opponent-name {{
            font-weight: bold;
            text-align: left;
        }}

        .vs-table .opponent-link {{
            color: #667eea;
            text-decoration: none;
            transition: color 0.2s ease;
        }}

        .vs-table .opponent-link:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}

        .vs-table .positive {{
            color: #28a745;
            font-weight: bold;
        }}

        .vs-table .negative {{
            color: #dc3545;
            font-weight: bold;
        }}

        .vs-table .neutral {{
            color: #666;
        }}

        .summary-box {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
            border-left: 4px solid #667eea;
        }}

        .summary-label {{
            font-size: 14px;
            color: #666;
            font-weight: 500;
        }}

        .summary-value {{
            font-size: 18px;
            color: #333;
            font-weight: bold;
        }}

        .summary-value.negative {{
            color: #dc3545;
        }}

        .league-avg {{
            font-size: 13px;
            color: #888;
            margin-left: 8px;
            font-weight: normal;
        }}

        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}

        .stats-table thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}

        .stats-table th {{
            color: white;
            padding: 12px 10px;
            text-align: center;
            font-weight: 600;
            font-size: 14px;
        }}

        .stats-table td {{
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
            font-size: 16px;
        }}

        .stats-table tbody tr:hover {{
            background: #f8f9fa;
        }}

        .stats-table tbody tr:last-child td {{
            border-bottom: none;
        }}

        .stats-table .type-label {{
            font-weight: 600;
            color: #555;
            text-align: left;
        }}

        .stats-table .points-value {{
            color: #667eea;
            font-weight: 600;
            font-size: 18px;
        }}

        .stats-table .special-stats {{
            color: #666;
            font-size: 14px;
        }}

        .stats-table .rate-good {{
            color: #28a745;
            font-weight: 600;
            font-size: 17px;
        }}

        .stats-table .rate-bad {{
            color: #dc3545;
            font-weight: 600;
            font-size: 17px;
        }}

        .stats-table .rate-neutral {{
            color: #666;
            font-size: 16px;
        }}

        /* 最近牌谱样式 - 横向表格 */
        .recent-games-section {{
            margin-bottom: 30px;
        }}

        .recent-games-section h2 {{
            margin: 0 0 15px 0;
            color: #667eea;
            font-size: 24px;
        }}

        .table-scroll {{
            overflow-x: auto;
            margin-bottom: 20px;
        }}

        .recent-games-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }}

        .recent-games-table thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        .recent-games-table th {{
            padding: 8px 5px;
            text-align: center;
            font-weight: 600;
            font-size: 10px;
            border: 1px solid rgba(255,255,255,0.2);
            white-space: nowrap;
        }}

        .recent-games-table tbody tr {{
            transition: background-color 0.2s;
        }}

        .recent-games-table tbody tr:nth-child(even) {{
            background: #f8f9fa;
        }}

        .recent-games-table tbody tr:hover {{
            background: #e3f2fd;
        }}

        .recent-games-table td {{
            padding: 6px 4px;
            text-align: center;
            border: 1px solid #e0e0e0;
            font-size: 10px;
            white-space: nowrap;
        }}

        .recent-games-table .game-date {{
            font-weight: bold;
            color: #667eea;
            font-size: 11px;
        }}

        .recent-games-table .table-avg-r {{
            font-weight: 600;
            color: #764ba2;
        }}

        .recent-games-table .player-name {{
            font-weight: 500;
            color: #333;
            max-width: 100px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .recent-games-table .player-name.rank-1 {{
            color: #ffc107;
            font-weight: bold;
        }}

        .recent-games-table .player-name.rank-2 {{
            color: #666;
        }}

        .recent-games-table .player-name.rank-3 {{
            color: #999;
        }}

        .recent-games-table .player-name.rank-4 {{
            color: #ccc;
        }}

        .recent-games-table .r-value {{
            color: #667eea;
            font-weight: 500;
        }}

        .recent-games-table .games-count {{
            color: #888;
        }}

        .recent-games-table .score-change {{
            font-weight: 500;
        }}

        .recent-games-table .r-correction {{
            color: #764ba2;
        }}

        .recent-games-table .games-coef {{
            color: #888;
            font-size: 9px;
        }}

        .recent-games-table .r-change {{
            font-weight: bold;
        }}

        /* 荣誉牌谱样式 */
        .honor-games-section {{
            margin-bottom: 40px;
        }}

        .honor-games-section h2 {{
            margin: 0 0 20px 0;
            color: #667eea;
            font-size: 28px;
        }}

        .honor-games-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .honor-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid;
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .honor-card.yakuman {{
            border-left-color: #dc3545;
            background: linear-gradient(135deg, #fff 0%, #ffe6e6 100%);
        }}

        .honor-card.sanbaiman {{
            border-left-color: #ffc107;
            background: linear-gradient(135deg, #fff 0%, #fff9e6 100%);
        }}

        .honor-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}

        .honor-type {{
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
        }}

        .honor-card.yakuman .honor-type {{
            color: #dc3545;
        }}

        .honor-card.sanbaiman .honor-type {{
            color: #ffc107;
        }}

        .honor-info {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .honor-date {{
            font-size: 14px;
            color: #666;
        }}

        .honor-round {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }}

        .honor-winner {{
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
        }}

        .honor-yaku {{
            font-size: 13px;
            color: #555;
            line-height: 1.5;
        }}

        .honor-replay-btn {{
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            text-align: center;
            font-weight: 600;
            transition: background 0.2s;
        }}

        .honor-replay-btn:hover {{
            background: #764ba2;
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}

            .yaku-list {{
                columns: 1;
            }}

            .vs-table {{
                font-size: 12px;
            }}

            .vs-table th,
            .vs-table td {{
                padding: 6px 4px;
            }}

            .stats-table {{
                font-size: 12px;
            }}

            .stats-table th,
            .stats-table td {{
                padding: 8px 5px;
            }}

            .stats-table .special-stats {{
                font-size: 11px;
            }}

            .summary-box {{
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }}

            .recent-games-table {{
                font-size: 9px;
            }}

            .recent-games-table th {{
                padding: 6px 3px;
                font-size: 8px;
            }}

            .recent-games-table td {{
                padding: 4px 2px;
                font-size: 9px;
            }}

            .honor-games-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <a href="{other_stats_page}" class="lang-switch">🌐 {t['switch_to_' + other_lang]}</a>
        <h1>{title}</h1>
        {date_info}
        <a href="{current_index}" class="back-link">{t['back_home']}</a>
    </div>

    <div class="container">
        {recent_section}
        {honor_section}

        <div class="summary-table">
            <table>
                <thead>
                    <tr>
                        <th>{t['player']}</th>
                        <th>{t['games']}</th>
                        <th>{t['rounds']}</th>
                        <th>{t['r_value']}</th>
                        <th>{t['total_score']}</th>
                        <th>{t['avg_rank']}</th>
                        <th>{t['rank_1_rate']}</th>
                        <th>{t['win_rate']}</th>
                        <th>{t['deal_in_rate']}</th>
                        <th>{t['riichi_rate']}</th>
                        <th>{t['furo_rate']}</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        <h2>{t['detailed_stats']}</h2>
        {detail_cards}
    </div>
</body>
</html>
"""
    return html


def generate_recent_games_content_for_tabs(recent_games, stats_data, t, lang='zh'):
    """生成最近牌谱内容 - 带玩家筛选和Rating曲线图"""
    if not recent_games or len(recent_games) == 0:
        return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_recent_games', '暂无最近牌谱')}</p>"

    # 收集所有玩家信息并按半庄数排序
    player_list = []
    for player_name, data in stats_data.items():
        if player_name == "_league_average":
            continue
        player_list.append({
            'name': player_name,
            'games': data['games']
        })
    player_list.sort(key=lambda x: -x['games'])

    # 构建玩家选项卡
    player_tabs = ""
    all_text = t.get('all_players', '所有玩家')
    player_tabs += f'<button class="player-filter-btn active" data-player="all">{all_text}</button>\n'
    for player in player_list:
        games_text = t.get('games', '局')
        player_tabs += f'<button class="player-filter-btn" data-player="{player["name"]}">{player["name"]} ({player["games"]}{games_text})</button>\n'

    # 构建游戏数据（JSON格式，供JavaScript使用）
    games_data = []
    player_rating_history = {}  # 每个玩家的rating历史

    for game in recent_games:
        date_str = game['date'] if lang == 'zh' else game['date_en']
        table_avg_r = game.get('table_avg_r', 0)
        players_data = game.get('players_detail', [])

        game_data = {
            'date': date_str,
            'table_avg_r': table_avg_r,
            'players': []
        }

        for p in players_data:
            player_info = {
                'name': p['name'],
                'rank': p['rank'],
                'r_before': p['r_before'],
                'games_before': p['games_before'],
                'final_points': p['final_points'],
                'score_change': p['score_change'],
                'r_correction': p['r_correction'],
                'games_correction': p['games_correction'],
                'r_change': p['r_change'],
                'r_after': p['r_after']
            }
            game_data['players'].append(player_info)

            # 记录玩家的rating历史
            pname = p['name']
            if pname not in player_rating_history:
                player_rating_history[pname] = []
            player_rating_history[pname].append({
                'date': date_str,
                'games': p['games_before'],
                'r_value': p['r_after']
            })

        games_data.append(game_data)

    # 将数据转换为JSON
    games_json = json.dumps(games_data, ensure_ascii=False)
    rating_history_json = json.dumps(player_rating_history, ensure_ascii=False)

    html_content = f"""
    <!-- 玩家筛选选项卡 -->
    <div class="player-filter-tabs" style="margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 8px;">
        {player_tabs}
    </div>

    <!-- Rating曲线图容器 -->
    <div id="ratingChartContainer" style="display: none; margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h3 id="chartPlayerName" style="text-align: center; color: #667eea; margin-bottom: 20px;"></h3>
        <canvas id="ratingChart" width="800" height="400"></canvas>
    </div>

    <!-- 牌谱表格 -->
    <div class="table-scroll">
        <table class="recent-games-table" id="gamesTable">
            <thead>
                <tr>
                    <th rowspan="2">{t['game_date']}</th>
                    <th rowspan="2">{t['table_avg_r']}</th>
                    <th colspan="9">{t['player']}1</th>
                    <th colspan="9">{t['player']}2</th>
                    <th colspan="9">{t['player']}3</th>
                    <th colspan="9">{t['player']}4</th>
                </tr>
                <tr>
                    <th>{t['player']}</th>
                    <th>{t['r_before']}</th>
                    <th>{t['games_count']}</th>
                    <th>{t['final_points']}</th>
                    <th>{t['score_change_pt']}</th>
                    <th>{t['r_correction']}</th>
                    <th>{t['games_coef']}</th>
                    <th>{t['r_change']}</th>
                    <th>{t['r_after']}</th>

                    <th>{t['player']}</th>
                    <th>{t['r_before']}</th>
                    <th>{t['games_count']}</th>
                    <th>{t['final_points']}</th>
                    <th>{t['score_change_pt']}</th>
                    <th>{t['r_correction']}</th>
                    <th>{t['games_coef']}</th>
                    <th>{t['r_change']}</th>
                    <th>{t['r_after']}</th>

                    <th>{t['player']}</th>
                    <th>{t['r_before']}</th>
                    <th>{t['games_count']}</th>
                    <th>{t['final_points']}</th>
                    <th>{t['score_change_pt']}</th>
                    <th>{t['r_correction']}</th>
                    <th>{t['games_coef']}</th>
                    <th>{t['r_change']}</th>
                    <th>{t['r_after']}</th>

                    <th>{t['player']}</th>
                    <th>{t['r_before']}</th>
                    <th>{t['games_count']}</th>
                    <th>{t['final_points']}</th>
                    <th>{t['score_change_pt']}</th>
                    <th>{t['r_correction']}</th>
                    <th>{t['games_coef']}</th>
                    <th>{t['r_change']}</th>
                    <th>{t['r_after']}</th>
                </tr>
            </thead>
            <tbody id="gamesTableBody">
            </tbody>
        </table>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // 游戏数据
        const gamesData = {games_json};
        const ratingHistory = {rating_history_json};
        let currentChart = null;

        // 渲染表格
        function renderGamesTable(filterPlayer = 'all') {{
            const tbody = document.getElementById('gamesTableBody');
            tbody.innerHTML = '';

            const filteredGames = filterPlayer === 'all'
                ? gamesData
                : gamesData.filter(game => game.players.some(p => p.name === filterPlayer));

            filteredGames.forEach(game => {{
                const tr = document.createElement('tr');

                // 添加日期和桌平均R
                tr.innerHTML = `
                    <td class="game-date">${{game.date}}</td>
                    <td class="table-avg-r">${{game.table_avg_r.toFixed(2)}}</td>
                `;

                // 添加4个玩家的数据
                game.players.forEach(p => {{
                    const rankClass = `rank-${{p.rank}}`;
                    const highlightClass = (filterPlayer !== 'all' && p.name === filterPlayer) ? 'highlight-player' : '';
                    tr.innerHTML += `
                        <td class="player-name ${{rankClass}} ${{highlightClass}}">${{p.name}}</td>
                        <td class="r-value">${{p.r_before}}</td>
                        <td class="games-count">${{p.games_before}}</td>
                        <td class="final-points">${{p.final_points}}</td>
                        <td class="score-change">${{p.score_change >= 0 ? '+' : ''}}${{p.score_change.toFixed(1)}}</td>
                        <td class="r-correction">${{p.r_correction >= 0 ? '+' : ''}}${{p.r_correction.toFixed(2)}}</td>
                        <td class="games-coef">${{p.games_correction.toFixed(3)}}</td>
                        <td class="r-change">${{p.r_change >= 0 ? '+' : ''}}${{p.r_change.toFixed(2)}}</td>
                        <td class="r-value">${{p.r_after}}</td>
                    `;
                }});

                tbody.appendChild(tr);
            }});
        }}

        // 绘制Rating曲线图
        function drawRatingChart(playerName) {{
            const container = document.getElementById('ratingChartContainer');
            const chartTitle = document.getElementById('chartPlayerName');
            const ctx = document.getElementById('ratingChart').getContext('2d');

            if (!ratingHistory[playerName]) {{
                container.style.display = 'none';
                return;
            }}

            container.style.display = 'block';
            chartTitle.textContent = `${{playerName}} - Rating {t.get('change_curve', '变化曲线')}`;

            // 反转数据（从最早到最新）
            const data = [...ratingHistory[playerName]].reverse();

            // 准备图表数据
            const labels = data.map((d, idx) => `${{d.date}}\\n(${{d.games}}{t.get('games', '局')})`);
            const rValues = data.map(d => d.r_value);

            // 销毁旧图表
            if (currentChart) {{
                currentChart.destroy();
            }}

            // 创建新图表
            currentChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'Rating',
                        data: rValues,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: true,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                title: function(context) {{
                                    const idx = context[0].dataIndex;
                                    return `${{data[idx].date}} (${{data[idx].games}}{t.get('games', '局')})`;
                                }},
                                label: function(context) {{
                                    return `Rating: ${{context.parsed.y.toFixed(2)}}`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            title: {{
                                display: true,
                                text: 'Rating'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: '{t.get('date_and_games', '日期（半庄数）')}'
                            }},
                            ticks: {{
                                maxRotation: 45,
                                minRotation: 45,
                                autoSkip: false,
                                callback: function(value, index, ticks) {{
                                    // 根据数据点数量动态决定显示间隔
                                    const totalPoints = data.length;
                                    let skipInterval;

                                    if (totalPoints <= 20) {{
                                        skipInterval = 1; // 显示所有
                                    }} else if (totalPoints <= 40) {{
                                        skipInterval = 2; // 每2个显示1个
                                    }} else if (totalPoints <= 60) {{
                                        skipInterval = 3; // 每3个显示1个
                                    }} else if (totalPoints <= 80) {{
                                        skipInterval = 4; // 每4个显示1个
                                    }} else if (totalPoints <= 100) {{
                                        skipInterval = 5; // 每5个显示1个
                                    }} else if (totalPoints <= 120) {{
                                        skipInterval = 6; // 每6个显示1个
                                    }} else {{
                                        skipInterval = 8; // 每8个显示1个
                                    }}

                                    // 总是显示第一个和最后一个标签
                                    if (index === 0 || index === data.length - 1) {{
                                        return labels[index];
                                    }}

                                    // 按间隔显示
                                    if (index % skipInterval === 0) {{
                                        return labels[index];
                                    }}

                                    return '';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // 玩家筛选按钮点击事件
        document.querySelectorAll('.player-filter-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                // 更新按钮状态
                document.querySelectorAll('.player-filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const playerName = this.getAttribute('data-player');

                // 渲染表格
                renderGamesTable(playerName);

                // 绘制或隐藏图表
                if (playerName === 'all') {{
                    document.getElementById('ratingChartContainer').style.display = 'none';
                    if (currentChart) {{
                        currentChart.destroy();
                        currentChart = null;
                    }}
                }} else {{
                    drawRatingChart(playerName);
                }}
            }});
        }});

        // 初始化显示所有牌谱
        renderGamesTable('all');
    </script>

    <style>
        .player-filter-tabs {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .player-filter-btn {{
            padding: 8px 16px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }}

        .player-filter-btn:hover {{
            background: #f0f0f0;
        }}

        .player-filter-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}

        .highlight-player {{
            background-color: #fff3cd !important;
            font-weight: bold;
        }}
    </style>
    """

    return html_content


def generate_honor_games_content_for_tabs(honor_games, t, lang='zh'):
    """生成荣誉牌谱内容"""
    if not honor_games or len(honor_games) == 0:
        return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_honor_games', '暂无荣誉牌谱')}</p>"

    honor_cards = ""
    for game in honor_games:
        yaku_list = game.get('yaku_list', [])
        if lang == 'zh':
            translated_yaku = ', '.join([YAKU_TRANSLATION.get(y.split('(')[0], y) for y in yaku_list])
        else:
            translated_yaku = ', '.join([YAKU_TRANSLATION_EN.get(y.split('(')[0], y) if '(' in y else y for y in yaku_list])

        game_type = game.get('type', 'yakuman')
        game_type_text = t['yakuman'] if game_type == 'yakuman' else t['sanbaiman']
        game_type_class = 'yakuman' if game_type == 'yakuman' else 'sanbaiman'
        escaped_url = html_module.escape(game['tenhou_url'], quote=True)

        honor_cards += f"""
        <div class="honor-card {game_type_class}">
            <div class="honor-type">{game_type_text}</div>
            <div class="honor-info">
                <div class="honor-date">{game['date']}</div>
                <div class="honor-round">{game['round']}</div>
                <div class="honor-winner">{game['winner']}</div>
                <div class="honor-yaku">{translated_yaku}</div>
            </div>
            <a href="{escaped_url}" target="_blank" class="honor-replay-btn">{t['view_replay']}</a>
        </div>
        """

    return f'<div class="honor-games-grid">{honor_cards}</div>'


def generate_player_details_html_for_tabs(name, data, t, lang='zh', league_avg=None):
    """生成单个玩家的详细数据HTML（为标签页版本简化）"""
    if league_avg is None:
        league_avg = {}

    player_id = name.replace(" ", "_").replace("(", "").replace(")", "")
    riichi_win_hands = data['riichi_win_hands']
    furo_then_win_hands = data['furo_then_win_hands']
    dama_win_hands = data.get('dama_win_hands', 0)
    tsumo_only_win_hands = data.get('tsumo_only_win_hands', 0)

    yaku_html = ""
    if data.get('yaku_count'):
        yaku_sorted = sorted(data['yaku_count'].items(), key=lambda x: -x[1])[:10]
        for yaku, count in yaku_sorted:
            if lang == 'zh':
                yaku_name = YAKU_TRANSLATION.get(yaku, yaku)
            else:
                yaku_name = YAKU_TRANSLATION_EN.get(yaku, yaku)
            rate = data['yaku_rate'].get(yaku, 0)
            avg_rate = league_avg.get('yaku_rate', {}).get(yaku, 0) if league_avg else 0
            avg_text = f' <span class="league-avg">({t["average"]}{avg_rate}%)</span>' if avg_rate > 0 else ''
            yaku_html += f"<li>{yaku_name}: {count}{t['times']} ({rate}%){avg_text}</li>"

    vs_players_html = ""
    if data.get('vs_players'):
        vs_sorted = sorted(data['vs_players'].items(), key=lambda x: -x[1]['games'])
        vs_players_html = f"""
        <table class="vs-table">
            <thead>
                <tr>
                    <th>{t['opponent']}</th>
                    <th>{t['games_count']}</th>
                    <th>{t['win_rate_vs']}</th>
                    <th>{t['win_points']}</th>
                    <th>{t['lose_points']}</th>
                    <th>{t['net_points']}</th>
                    <th>{t['score_diff']}</th>
                </tr>
            </thead>
            <tbody>
        """

        for vs_player, vs_data in vs_sorted:
            vs_win_rate = vs_data['win_rate']
            win_rate_class = 'rate-good' if vs_win_rate > 25 else 'rate-bad' if vs_win_rate < 25 else ''
            net_points = vs_data['win_points'] - vs_data['lose_points']
            net_class = 'positive' if net_points > 0 else 'negative' if net_points < 0 else ''
            score_diff = vs_data['score_diff']
            score_diff_class = 'positive' if score_diff > 0 else 'negative' if score_diff < 0 else ''

            vs_players_html += f"""
                <tr>
                    <td>{vs_player}</td>
                    <td>{vs_data['games']}</td>
                    <td class="{win_rate_class}">{vs_win_rate:.1f}%</td>
                    <td class="positive">+{vs_data['win_points']}</td>
                    <td class="negative">-{vs_data['lose_points']}</td>
                    <td class="{net_class}">{net_points:+}</td>
                    <td class="{score_diff_class}">{score_diff:+}</td>
                </tr>
            """
        vs_players_html += "</tbody></table>"

    html = f"""
    <div class="player-card" id="player-{player_id}">
        <h3>{name}</h3>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">{t['tenhou_r']}</div>
                <div class="stat-value large">{data['tenhou_r']:.2f}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">{t['total_score']}</div>
                <div class="stat-value">{data['total_score']:+}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">{t['avg_rank']}</div>
                <div class="stat-value">{data['avg_rank']:.2f}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">{t['games_count']}</div>
                <div class="stat-value">{data['games']} {t['games']}</div>
            </div>
        </div>

        <div class="section">
            <h4>{t['rank_distribution']}</h4>
            <div class="rank-bars">
                <div class="rank-bar">
                    <span class="rank-label">{t['rank_1']}</span>
                    <div class="bar-container">
                        <div class="bar bar-1" style="width: {data['rank_1_rate']}%"></div>
                        <span class="bar-text">{data['rank_1']} {t['times']} ({data['rank_1_rate']:.1f}%)</span>
                    </div>
                </div>
                <div class="rank-bar">
                    <span class="rank-label">{t['rank_2']}</span>
                    <div class="bar-container">
                        <div class="bar bar-2" style="width: {data['rank_2_rate']}%"></div>
                        <span class="bar-text">{data['rank_2']} {t['times']} ({data['rank_2_rate']:.1f}%)</span>
                    </div>
                </div>
                <div class="rank-bar">
                    <span class="rank-label">{t['rank_3']}</span>
                    <div class="bar-container">
                        <div class="bar bar-3" style="width: {data['rank_3_rate']}%"></div>
                        <span class="bar-text">{data['rank_3']} {t['times']} ({data['rank_3_rate']:.1f}%)</span>
                    </div>
                </div>
                <div class="rank-bar">
                    <span class="rank-label">{t['rank_4']}</span>
                    <div class="bar-container">
                        <div class="bar bar-4" style="width: {data['rank_4_rate']}%"></div>
                        <span class="bar-text">{data['rank_4']} {t['times']} ({data['rank_4_rate']:.1f}%)</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <h4>{t['win_stats']}</h4>
            <div class="summary-box">
                <span class="summary-label">{t['total_wins']}:</span>
                <span class="summary-value">{data['win_hands']} {t['rounds']} ({data['win_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('win_rate', 0):.1f}%)</span></span>
                <span class="summary-label">{t['avg_points']}:</span>
                <span class="summary-value">{data['avg_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_win_points', 0):.0f}{t['points']})</span></span>
            </div>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>{t['type']}</th>
                        <th>{t['count']}</th>
                        <th>{t['avg_points']}</th>
                        <th>{t['special_stats']}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="type-label">{t['riichi_win']}</td>
                        <td>{riichi_win_hands} {t['rounds']}</td>
                        <td class="points-value">{data['avg_riichi_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_riichi_win_points', 0):.0f})</span></td>
                        <td class="special-stats">{t['ippatsu']}: {data['ippatsu_hands']}{t['rounds']} ({data['ippatsu_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('ippatsu_rate', 0):.1f}%)</span> · {t['ura']}: {data['ura_hands']}{t['rounds']} ({data['ura_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('ura_rate', 0):.1f}%)</span></td>
                    </tr>
                    <tr>
                        <td class="type-label">{t['furo_win']}</td>
                        <td>{furo_then_win_hands} {t['rounds']}</td>
                        <td class="points-value">{data['avg_furo_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_furo_win_points', 0):.0f})</span></td>
                        <td class="special-stats">-</td>
                    </tr>
                    {f'''<tr>
                        <td class="type-label">{t['dama_win']}</td>
                        <td>{dama_win_hands} {t['rounds']}</td>
                        <td class="points-value">{data['avg_dama_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_dama_win_points', 0):.0f})</span></td>
                        <td class="special-stats">{t['has_yaku_menzen']}</td>
                    </tr>''' if dama_win_hands > 0 else ''}
                    {f'''<tr>
                        <td class="type-label">{t['tsumo_only_win']}</td>
                        <td>{tsumo_only_win_hands} {t['rounds']}</td>
                        <td class="points-value">{data['avg_tsumo_only_win_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_tsumo_only_win_points', 0):.0f})</span></td>
                        <td class="special-stats">{t['menzen_tsumo']}</td>
                    </tr>''' if tsumo_only_win_hands > 0 else ''}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h4>{t['riichi_furo']}</h4>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>{t['type']}</th>
                        <th>{t['count_rate']}</th>
                        <th>{t['win']}</th>
                        <th>{t['draw']}</th>
                        <th>{t['deal_in']}</th>
                        <th>{t['pass']}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="type-label">{t['riichi']}</td>
                        <td>{data['riichi_hands']} {t['rounds']} ({data['riichi_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('riichi_rate', 0):.1f}%)</span></td>
                        <td class="rate-good">{data['riichi_win_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('riichi_win_rate', 0):.1f}%)</span></td>
                        <td class="rate-neutral">{data['riichi_ryuukyoku_rate']:.1f}%</td>
                        <td class="rate-bad">{data['riichi_then_deal_in_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('riichi_then_deal_in_rate', 0):.1f}%)</span></td>
                        <td class="rate-neutral">{data['riichi_pass_rate']:.1f}%</td>
                    </tr>
                    <tr>
                        <td class="type-label">{t['furo']}</td>
                        <td>{data['furo_hands']} {t['rounds']} ({data['furo_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('furo_rate', 0):.1f}%)</span></td>
                        <td class="rate-good">{data['furo_then_win_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('furo_then_win_rate', 0):.1f}%)</span></td>
                        <td class="rate-neutral">{data['furo_ryuukyoku_rate']:.1f}%</td>
                        <td class="rate-bad">{data['furo_then_deal_in_rate']:.1f}% <span class="league-avg">({t['average']}{league_avg.get('furo_then_deal_in_rate', 0):.1f}%)</span></td>
                        <td class="rate-neutral">{data['furo_pass_rate']:.1f}%</td>
                    </tr>
                    {f'''<tr>
                        <td class="type-label">{t['dama']}</td>
                        <td>{data['dama_state_hands']} {t['times']}</td>
                        <td class="rate-good">{data['dama_state_win_rate']:.1f}%</td>
                        <td class="rate-neutral">{data['dama_state_draw_rate']:.1f}%</td>
                        <td class="rate-bad">{data['dama_state_deal_in_rate']:.1f}%</td>
                        <td class="rate-neutral">{data['dama_state_pass_rate']:.1f}%</td>
                    </tr>''' if data.get('dama_state_hands', 0) > 0 else ''}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h4>{t['deal_in_stats']}</h4>
            <div class="summary-box">
                <span class="summary-label">{t['deal_in']}:</span>
                <span class="summary-value">{data['deal_in_hands']} {t['rounds']} ({data['deal_in_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('deal_in_rate', 0):.1f}%)</span></span>
                <span class="summary-label">{t['avg_deal_in_points']}:</span>
                <span class="summary-value negative">{data['avg_deal_in_points']:.0f}{t['points']} <span class="league-avg">({t['average']}{league_avg.get('avg_deal_in_points', 0):.0f}{t['points']})</span></span>
            </div>
        </div>

        {f'''<div class="section">
            <h4>{t['vs_stats']}</h4>
            {vs_players_html}
        </div>''' if vs_players_html else ''}

        {f'''<div class="section">
            <h4>{t['yaku_stats']}</h4>
            <ul class="yaku-list">
                {yaku_html}
            </ul>
        </div>''' if yaku_html else ''}

        {f'''<div class="section">
            <h4>{t['draw_tenpai']}</h4>
            <p>{t['draw_count']}: {data['ryuukyoku_hands']} {t['times']}, {t['tenpai']} {data['ryuukyoku_tenpai']} {t['times']} ({data['tenpai_rate']:.1f}%) <span class="league-avg">({t['average']}{league_avg.get('tenpai_rate', 0):.1f}%)</span></p>
        </div>''' if data['ryuukyoku_hands'] > 0 else ''}
    </div>
    """
    return html


def generate_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成排行榜内容 - 1番手牌频率排行"""
    # 统计每个玩家的1番手牌次数和总小局数
    one_han_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计1番手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表
            names = data.get('name', [])

            # 初始化这些玩家的计数器
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in one_han_counts:
                    one_han_counts[name] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1
                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                # 检查最后一个元素是否为和了
                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 5:
                        winner_seat = yaku_info[0]
                        fan_str = str(yaku_info[3])  # 番数信息
                        yaku_list = yaku_info[4:]    # 役种列表

                        # 检查是否是1番（不是役满）
                        is_yakuman = '役満' in fan_str or 'Yakuman' in fan_str
                        if not is_yakuman and ('1飜' in fan_str or '30符1飜' in fan_str or '40符1飜' in fan_str or '50符1飜' in fan_str):
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                one_han_counts[winner_name] = one_han_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和1番手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取1番手牌次数
        one_han_count = one_han_counts.get(name, 0)
        one_han_rate = (one_han_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'one_han_count': one_han_count,
            'total_rounds': total_rounds,
            'one_han_rate': one_han_rate
        })

    # 按照1番手牌频率从高到低排序
    leaderboard_data.sort(key=lambda x: x['one_han_rate'], reverse=True)

    # 生成HTML表格
    if lang == 'zh':
        header_name = '玩家'
        header_count = '1番手牌次数'
        header_total = '总小局数'
        header_rate = '频率'
    else:
        header_name = 'Player'
        header_count = '1-Han Wins'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'

    html = f'''
    <div class="leaderboard-section">
        <h2>1番手牌频率排行榜</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>{header_name}</th>
                        <th>{header_count}</th>
                        <th>{header_total}</th>
                        <th>{header_rate}</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['one_han_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['one_han_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_two_han_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成排行榜内容 - 2番手牌频率排行"""
    # 统计每个玩家的2番手牌次数和总小局数
    two_han_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计2番手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表
            names = data.get('name', [])

            # 初始化这些玩家的计数器
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in two_han_counts:
                    two_han_counts[name] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1
                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                # 检查最后一个元素是否为和了
                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 5:
                        winner_seat = yaku_info[0]
                        fan_str = str(yaku_info[3])  # 番数信息
                        yaku_list = yaku_info[4:]    # 役种列表

                        # 检查是否是2番（不是役满）
                        is_yakuman = '役満' in fan_str or 'Yakuman' in fan_str
                        if not is_yakuman and '2飜' in fan_str:
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                two_han_counts[winner_name] = two_han_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和2番手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取2番手牌次数
        two_han_count = two_han_counts.get(name, 0)
        two_han_rate = (two_han_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'two_han_count': two_han_count,
            'total_rounds': total_rounds,
            'two_han_rate': two_han_rate
        })

    # 按照2番手牌频率从高到低排序
    leaderboard_data.sort(key=lambda x: x['two_han_rate'], reverse=True)

    # 生成HTML表格
    if lang == 'zh':
        header_name = '玩家'
        header_count = '2番手牌次数'
        header_total = '总小局数'
        header_rate = '频率'
        title = '2番手牌频率排行榜'
    else:
        header_name = 'Player'
        header_count = '2-Han Wins'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'
        title = '2-Han Win Rate Leaderboard'

    html = f'''
    <div class="leaderboard-section">
        <h2>{title}</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>{header_name}</th>
                        <th>{header_count}</th>
                        <th>{header_total}</th>
                        <th>{header_rate}</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['two_han_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['two_han_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_three_han_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成排行榜内容 - 3番以上不到满贯（3番60以下 + 4番20）"""
    # 统计每个玩家的3番以上不到满贯手牌次数和总小局数
    three_han_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表
            names = data.get('name', [])

            # 初始化这些玩家的计数器
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in three_han_counts:
                    three_han_counts[name] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1
                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                # 检查最后一个元素是否为和了
                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 5:
                        winner_seat = yaku_info[0]
                        fan_str = str(yaku_info[3])  # 番数信息
                        yaku_list = yaku_info[4:]    # 役种列表

                        # 检查是否是役满或满贯以上
                        is_yakuman = '役満' in fan_str or 'Yakuman' in fan_str
                        is_mangan_plus = 'Mangan' in fan_str or 'Haneman' in fan_str or 'Baiman' in fan_str or 'Sanbaiman' in fan_str or '满贯' in fan_str or '跳满' in fan_str or '倍满' in fan_str or '三倍满' in fan_str

                        # 3番60以下（不到满贯）或 4番20（不到满贯）
                        if not is_yakuman and not is_mangan_plus and ('3飜' in fan_str or '4飜' in fan_str):
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                three_han_counts[winner_name] = three_han_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和3番以上不到满贯手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取手牌次数
        three_han_count = three_han_counts.get(name, 0)
        three_han_rate = (three_han_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'three_han_count': three_han_count,
            'total_rounds': total_rounds,
            'three_han_rate': three_han_rate
        })

    # 按照频率从高到低排序
    leaderboard_data.sort(key=lambda x: x['three_han_rate'], reverse=True)

    # 生成HTML表格
    if lang == 'zh':
        header_name = '玩家'
        header_count = '次数'
        header_total = '总小局数'
        header_rate = '频率'
        title = '3番以上不到满贯频率排行榜'
    else:
        header_name = 'Player'
        header_count = 'Count'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'
        title = '3+ Han (Below Mangan) Win Rate Leaderboard'

    html = f'''
    <div class="leaderboard-section">
        <h2>{title}</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>{header_name}</th>
                        <th>{header_count}</th>
                        <th>{header_total}</th>
                        <th>{header_rate}</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['three_han_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['three_han_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_mangan_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成满贯以上手牌频率排行榜"""
    # 统计每个玩家的满贯以上手牌次数和总小局数
    mangan_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计满贯以上手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表
            names = data.get('name', [])

            # 初始化这些玩家的计数器
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in mangan_counts:
                    mangan_counts[name] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1
                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                # 检查最后一个元素是否为和了
                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 4:
                        winner_seat = yaku_info[0]
                        fan_str = str(yaku_info[3])  # 番数信息

                        # 检查是否是满贯以上
                        # 满贯: 5番, 4番30符以上, 3番60符以上
                        # 跳满: 6-7番
                        # 倍满: 8-10番
                        # 三倍满: 11-12番
                        # 役满: 13番以上
                        is_mangan_plus = False

                        # 检查役满
                        if '役満' in fan_str or 'Yakuman' in fan_str:
                            is_mangan_plus = True
                        # 检查三倍满
                        elif '三倍満' in fan_str or 'Sanbaiman' in fan_str:
                            is_mangan_plus = True
                        # 检查倍满
                        elif '倍満' in fan_str or 'Baiman' in fan_str:
                            is_mangan_plus = True
                        # 检查跳满
                        elif '跳満' in fan_str or 'Haneman' in fan_str:
                            is_mangan_plus = True
                        # 检查满贯
                        elif '満貫' in fan_str or 'Mangan' in fan_str:
                            is_mangan_plus = True
                        # 检查4番30符、40符、50符、60符（都是满贯）
                        elif '4飜30符' in fan_str or '4飜40符' in fan_str or '4飜50符' in fan_str or '4飜60符' in fan_str:
                            is_mangan_plus = True
                        # 检查3番60符、70符（满贯）
                        elif '3飜60符' in fan_str or '3飜70符' in fan_str:
                            is_mangan_plus = True

                        if is_mangan_plus:
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                mangan_counts[winner_name] = mangan_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和满贯以上手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取满贯以上手牌次数
        mangan_count = mangan_counts.get(name, 0)
        mangan_rate = (mangan_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'mangan_count': mangan_count,
            'total_rounds': total_rounds,
            'mangan_rate': mangan_rate
        })

    # 按照满贯以上频率从高到低排序
    leaderboard_data.sort(key=lambda x: x['mangan_rate'], reverse=True)

    # 生成HTML表格
    if lang == 'zh':
        header_name = '玩家'
        header_count = '满贯以上次数'
        header_total = '总小局数'
        header_rate = '频率'
        title = '满贯以上手牌频率排行榜'
    else:
        header_name = 'Player'
        header_count = 'Mangan+ Wins'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'
        title = 'Mangan+ Hand Rate Leaderboard'

    html = f'''
    <div class="leaderboard-section">
        <h2>{title}</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>{header_name}</th>
                        <th>{header_count}</th>
                        <th>{header_total}</th>
                        <th>{header_rate}</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['mangan_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['mangan_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_haneman_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成跳满以上手牌频率排行榜（6番以上）"""
    # 统计每个玩家的跳满以上手牌次数和总小局数
    haneman_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计跳满以上手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            names = data.get('name', [])
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in haneman_counts:
                    haneman_counts[name] = 0

            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 4:
                        winner_seat = yaku_info[0]
                        fan_str = str(yaku_info[3])

                        # 检查是否是跳满以上（6番以上）
                        is_haneman_plus = False

                        if '役満' in fan_str or 'Yakuman' in fan_str:
                            is_haneman_plus = True
                        elif '三倍満' in fan_str or 'Sanbaiman' in fan_str:
                            is_haneman_plus = True
                        elif '倍満' in fan_str or 'Baiman' in fan_str:
                            is_haneman_plus = True
                        elif '跳満' in fan_str or 'Haneman' in fan_str:
                            is_haneman_plus = True

                        if is_haneman_plus:
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                haneman_counts[winner_name] = haneman_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)
        if total_rounds <= 100:
            continue

        haneman_count = haneman_counts.get(name, 0)
        haneman_rate = (haneman_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'haneman_count': haneman_count,
            'total_rounds': total_rounds,
            'haneman_rate': haneman_rate
        })

    leaderboard_data.sort(key=lambda x: x['haneman_rate'], reverse=True)

    if lang == 'zh':
        title = '跳满以上手牌频率排行榜'
        header_count = '跳满以上次数'
    else:
        title = 'Haneman+ Hand Rate Leaderboard'
        header_count = 'Haneman+ Wins'

    html = f'''
    <div class="leaderboard-section">
        <h2>{title}</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>玩家</th>
                        <th>{header_count}</th>
                        <th>总小局数</th>
                        <th>频率</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['haneman_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['haneman_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_baiman_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成倍满以上手牌频率排行榜（8番以上）"""
    # 统计每个玩家的倍满以上手牌次数和总小局数
    baiman_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计倍满以上手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            names = data.get('name', [])
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in baiman_counts:
                    baiman_counts[name] = 0

            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 4:
                        winner_seat = yaku_info[0]
                        fan_str = str(yaku_info[3])

                        # 检查是否是倍满以上（8番以上）
                        is_baiman_plus = False

                        if '役満' in fan_str or 'Yakuman' in fan_str:
                            is_baiman_plus = True
                        elif '三倍満' in fan_str or 'Sanbaiman' in fan_str:
                            is_baiman_plus = True
                        elif '倍満' in fan_str or 'Baiman' in fan_str:
                            is_baiman_plus = True

                        if is_baiman_plus:
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                baiman_counts[winner_name] = baiman_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)
        if total_rounds <= 100:
            continue

        baiman_count = baiman_counts.get(name, 0)
        baiman_rate = (baiman_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'baiman_count': baiman_count,
            'total_rounds': total_rounds,
            'baiman_rate': baiman_rate
        })

    leaderboard_data.sort(key=lambda x: x['baiman_rate'], reverse=True)

    if lang == 'zh':
        title = '倍满以上手牌频率排行榜'
        header_count = '倍满以上次数'
    else:
        title = 'Baiman+ Hand Rate Leaderboard'
        header_count = 'Baiman+ Wins'

    html = f'''
    <div class="leaderboard-section">
        <h2>{title}</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>玩家</th>
                        <th>{header_count}</th>
                        <th>总小局数</th>
                        <th>频率</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['baiman_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['baiman_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_flush_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成混一色/清一色频率排行榜"""
    # 统计每个玩家的混一色/清一色次数和总小局数
    flush_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计混一色/清一色和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            names = data.get('name', [])
            for name in names:
                if name not in total_rounds_played:
                    total_rounds_played[name] = 0
                if name not in flush_counts:
                    flush_counts[name] = 0

            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                for name in names:
                    total_rounds_played[name] = total_rounds_played.get(name, 0) + 1

                last_action = round_data[-1]
                if not isinstance(last_action, list) or len(last_action) < 3:
                    continue

                if last_action[0] == '和了':
                    yaku_info = last_action[2]
                    if len(yaku_info) >= 5:
                        winner_seat = yaku_info[0]
                        yaku_list = yaku_info[4:]  # 役种列表

                        # 检查是否包含混一色或清一色
                        has_flush = False
                        for yaku in yaku_list:
                            yaku_str = str(yaku)
                            # 检查混一色
                            if 'Half Flush' in yaku_str or '混一色' in yaku_str or '混全帯么九' in yaku_str:
                                has_flush = True
                                break
                            # 检查清一色
                            if 'Full Flush' in yaku_str or '清一色' in yaku_str:
                                has_flush = True
                                break

                        if has_flush:
                            winner_name = names[winner_seat] if winner_seat < len(names) else None
                            if winner_name:
                                flush_counts[winner_name] = flush_counts.get(winner_name, 0) + 1
        except Exception as e:
            continue

    # 计算频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        total_rounds = total_rounds_played.get(name, 0)
        if total_rounds <= 100:
            continue

        flush_count = flush_counts.get(name, 0)
        flush_rate = (flush_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'flush_count': flush_count,
            'total_rounds': total_rounds,
            'flush_rate': flush_rate
        })

    leaderboard_data.sort(key=lambda x: x['flush_rate'], reverse=True)

    if lang == 'zh':
        title = '混一色/清一色频率排行榜'
        header_count = '混/清一色次数'
    else:
        title = 'Half/Full Flush Rate Leaderboard'
        header_count = 'Flush Wins'

    html = f'''
    <div class="leaderboard-section">
        <h2>{title}</h2>
        <div class="table-scroll">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>玩家</th>
                        <th>{header_count}</th>
                        <th>总小局数</th>
                        <th>频率</th>
                    </tr>
                </thead>
                <tbody>
    '''

    for rank, data in enumerate(leaderboard_data, 1):
        html += f'''
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{data['name']}</strong></td>
                        <td>{data['flush_count']}</td>
                        <td>{data['total_rounds']}</td>
                        <td>{data['flush_rate']:.2f}%</td>
                    </tr>
        '''

    html += '''
                </tbody>
            </table>
        </div>
    </div>
    '''

    return html


def generate_league_tabs_page(stats_dict, league_avg, honor_games, recent_games, sorted_files, results, latest_date, lang='zh', league_name='m-league'):
    """
    生成联赛标签页页面（通用函数，支持M-League和EMA）

    参数:
    - league_name: 'm-league' 或 'ema'
    """
    t = TRANSLATIONS[lang]

    # 生成各个标签页的内容
    recent_content = generate_recent_games_content_for_tabs(recent_games, stats_dict, t, lang)
    honor_content = generate_honor_games_content_for_tabs(honor_games, t, lang)
    ranking_content = generate_ranking_content(stats_dict, t, league_avg)

    # 生成排行榜内容（包含6个排行榜）
    one_han_leaderboard = generate_leaderboard_content(stats_dict, sorted_files, t, lang)
    two_han_leaderboard = generate_two_han_leaderboard_content(stats_dict, sorted_files, t, lang)
    three_han_leaderboard = generate_three_han_leaderboard_content(stats_dict, sorted_files, t, lang)
    mangan_leaderboard = generate_mangan_leaderboard_content(stats_dict, sorted_files, t, lang)
    haneman_leaderboard = generate_haneman_leaderboard_content(stats_dict, sorted_files, t, lang)
    baiman_leaderboard = generate_baiman_leaderboard_content(stats_dict, sorted_files, t, lang)
    leaderboard_content = one_han_leaderboard + two_han_leaderboard + three_han_leaderboard + mangan_leaderboard + haneman_leaderboard + baiman_leaderboard

    # 生成玩家详情内容
    sorted_players = sorted(stats_dict.items(), key=lambda x: (-x[1]["games"], x[0]))

    # 生成下拉选项
    player_options = ""
    for name, data in sorted_players:
        player_options += f'<option value="{name}">{name} ({data["games"]}局)</option>\n'

    # 生成每个玩家的详细HTML
    players_data = {}
    for name, data in sorted_players:
        player_html = generate_player_details_html_for_tabs(name, data, t, lang, league_avg)
        players_data[name] = player_html

    # 根据联赛类型确定链接和标题
    if league_name == 'm-league':
        if lang == 'zh':
            other_stats_page = 'm-league-en.html'
            current_index = 'index.html'
            switch_lang_text = '🌐 English'
            title = 'M-League 数据统计'
        else:
            other_stats_page = 'm-league.html'
            current_index = 'index-en.html'
            switch_lang_text = '🌐 中文'
            title = 'M-League Statistics'
    else:  # ema
        if lang == 'zh':
            other_stats_page = 'ema-en.html'
            current_index = 'index.html'
            switch_lang_text = '🌐 English'
            title = 'EMA 数据统计'
        else:
            other_stats_page = 'ema.html'
            current_index = 'index-en.html'
            switch_lang_text = '🌐 中文'
            title = 'EMA Statistics'

    # 日期信息
    date_info = f"{t['data_updated']}: {latest_date}" if latest_date else ""

    # 标签文本
    tab_texts = {
        'recent': t['tab_recent'],
        'honor': t['tab_honor'],
        'ranking': t['tab_ranking'],
        'leaderboard': t.get('tab_leaderboard', '排行榜' if lang == 'zh' else 'Leaderboard'),
        'players': t['tab_players']
    }

    # 渲染模板
    html_content = render_m_league_tabs(
        lang=lang,
        title=title,
        date_info=date_info,
        other_stats_page=other_stats_page,
        current_index=current_index,
        switch_lang_text=switch_lang_text,
        back_home_text=t['back_home'],
        tab_texts=tab_texts,
        recent_content=recent_content,
        honor_content=honor_content,
        ranking_content=ranking_content,
        leaderboard_content=leaderboard_content,
        player_options=player_options,
        players_data=players_data,
        select_player_label=t['select_player'],
        choose_player=t['choose_player'],
        select_player_prompt=t['select_player_prompt']
    )

    return html_content


def generate_m_league_tabs_page(stats_dict, league_avg, honor_games, recent_games, sorted_files, results, latest_date, lang='zh'):
    """生成M-League标签页页面（向后兼容的包装函数）"""
    return generate_league_tabs_page(stats_dict, league_avg, honor_games, recent_games, sorted_files, results, latest_date, lang, league_name='m-league')


def extract_sanma_yakuman(sanma_folder):
    """从三麻文件夹中提取所有役满"""
    yakuman_games = []

    files = scan_files(sanma_folder, "*.json", recursive=True)
    if not files:
        return yakuman_games

    sorted_files = sort_files_by_date(files)

    for fp in sorted_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 提取文件名中的日期信息
            filename = os.path.basename(fp)
            date_match = re.match(r'(\d+)_(\d+)_(\d+)_(.+)\.json', filename)
            if date_match:
                month, day, year, event_type = date_match.groups()
                date_str_zh = f"{year}年{month}月{day}日"
                date_str_en = f"{year}-{month}-{day}"
            else:
                date_str_zh = filename
                date_str_en = filename

            # 遍历所有局
            for round_idx, round_data in enumerate(data.get("log", []), 1):
                if len(round_data) < 10:
                    continue

                result = round_data[-1]
                if not isinstance(result, list) or len(result) < 3:
                    continue

                # 检查是否是和了
                if result[0] != "和了":
                    continue

                # 获取役种列表
                yaku_info = result[2]
                if len(yaku_info) < 5:
                    continue

                yaku_list = yaku_info[4:]  # 役种从第5个元素开始
                fan_info = yaku_info[3] if len(yaku_info) > 3 else ""  # 先获取fan_info

                # 检查是否包含役满 (检查yaku_list和fan_info)
                has_yakuman = (any('役満' in str(yaku) or 'Yakuman' in str(yaku) for yaku in yaku_list) or
                              '役満' in str(fan_info) or 'Yakuman' in str(fan_info))

                if has_yakuman:
                    winner_seat = yaku_info[0]

                    # 获取玩家名字
                    name_list = data.get("name", [])
                    winner_name = name_list[winner_seat] if winner_seat < len(name_list) else f"玩家{winner_seat+1}"

                    # 确定场风和局数
                    round_info = round_data[0]
                    if len(round_info) >= 3:
                        wind = round_info[0]  # 0=东, 1=南
                        dealer = round_info[1]  # 庄家位置
                        honba = round_info[2]  # 本场数
                        wind_str = "东" if wind == 0 else "南"
                        round_str = f"{wind_str}{dealer+1}局{honba}本场"
                    else:
                        round_str = f"第{round_idx}局"

                    # 构建嵌入式JSON天凤URL
                    # 获取役种描述用于标题，翻译成中文
                    yaku_names = []
                    for y in yaku_list:
                        yaku_name_en = str(y).split('(')[0]
                        yaku_name_zh = YAKU_TRANSLATION.get(yaku_name_en, yaku_name_en)
                        yaku_names.append(yaku_name_zh)
                    yaku_desc = ', '.join(yaku_names)

                    # 构建JSON数据
                    json_data = {
                        "title": ["Santi League -- Sanma", f"{winner_name}的{yaku_desc}"],
                        "name": name_list,
                        "rule": {"disp": "三人麻雀"},
                        "log": [round_data]
                    }

                    # 转换为JSON字符串（不需要手动HTML转义，模板会自动处理）
                    json_str = json.dumps(json_data, ensure_ascii=False, separators=(',', ':'))
                    tenhou_url = f"https://tenhou.net/5/#json={json_str}"

                    yakuman_games.append({
                        'date': date_str_zh,
                        'date_en': date_str_en,
                        'round': round_str,
                        'winner': winner_name,
                        'yaku_list': yaku_list,
                        'fan_info': fan_info,
                        'tenhou_url': tenhou_url,
                        'type': 'yakuman'
                    })

        except Exception as ex:
            print(f"  处理三麻文件失败: {fp} - {ex}", file=sys.stderr)

    return yakuman_games


def generate_sanma_honor_html(yakuman_games, lang='zh'):
    """生成三麻荣誉牌谱页面 - 使用新的模块化生成器"""
    return generate_sanma_honor_page(yakuman_games, lang)


def main():
    print("开始生成静态网站...", file=sys.stderr)

    # 生成中文首页
    index_html_zh = generate_index_html(lang='zh')
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(index_html_zh)
    print("✓ 已生成 docs/index.html (中文)", file=sys.stderr)

    # 生成英文首页
    index_html_en = generate_index_html(lang='en')
    with open("docs/index-en.html", "w", encoding="utf-8") as f:
        f.write(index_html_en)
    print("✓ 已生成 docs/index-en.html (英文)", file=sys.stderr)

    # 加载荣誉牌谱数据
    honor_games = []
    honor_games_path = "docs/honor_games.json"
    if os.path.exists(honor_games_path):
        try:
            with open(honor_games_path, "r", encoding="utf-8") as f:
                honor_data = json.load(f)
                honor_games = honor_data.get('games', [])
            print(f"✓ 已加载 {len(honor_games)} 个荣誉牌谱", file=sys.stderr)
        except Exception as e:
            print(f"⚠ 加载荣誉牌谱失败: {e}", file=sys.stderr)

    # 生成 M-League 页面
    print("正在处理 M-League 数据...", file=sys.stderr)
    m_league_folder = "game-logs/m-league"
    files = scan_files(m_league_folder, "*.json", recursive=True)

    if files:
        # 按日期正确排序文件
        sorted_files = sort_files_by_date(files)

        results = []
        round_counts = []
        for fp in sorted_files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                summary = summarize_log(data)
                results.append(summary)
                round_counts.append(len(data.get("log", [])))
            except Exception as ex:
                print(f"  处理失败: {fp} - {ex}", file=sys.stderr)

        # 提取最新日期
        latest_date = extract_latest_date(files)

        # 提取所有牌谱（使用按日期排序的文件）
        recent_games = extract_recent_games(sorted_files, results, count=len(sorted_files))

        stats = calculate_player_stats(results, round_counts)
        stats_dict = dict(stats)

        # 提取league_average
        league_avg = stats_dict.pop("_league_average", {})

        # 生成中文版（使用新的标签页模板）
        m_league_html_zh = generate_m_league_tabs_page(
            stats_dict=stats_dict,
            league_avg=league_avg,
            honor_games=honor_games,
            recent_games=recent_games,
            sorted_files=sorted_files,
            results=results,
            latest_date=latest_date,
            lang='zh'
        )
        with open("docs/m-league.html", "w", encoding="utf-8") as f:
            f.write(m_league_html_zh)
        print(f"✓ 已生成 docs/m-league.html (中文, 处理了 {len(results)} 个文件)", file=sys.stderr)

        # 生成英文版（使用新的标签页模板）
        m_league_html_en = generate_m_league_tabs_page(
            stats_dict=stats_dict,
            league_avg=league_avg,
            honor_games=honor_games,
            recent_games=recent_games,
            sorted_files=sorted_files,
            results=results,
            latest_date=latest_date,
            lang='en'
        )
        with open("docs/m-league-en.html", "w", encoding="utf-8") as f:
            f.write(m_league_html_en)
        print(f"✓ 已生成 docs/m-league-en.html (英文, 处理了 {len(results)} 个文件)", file=sys.stderr)

        if latest_date:
            print(f"  最新牌谱日期: {latest_date}", file=sys.stderr)
    else:
        print("⚠ 未找到 M-League 数据文件", file=sys.stderr)

    # 生成 EMA 页面
    print("正在处理 EMA 数据...", file=sys.stderr)
    ema_folder = "game-logs/ema"
    ema_files = scan_files(ema_folder, "*.json", recursive=True)

    if ema_files:
        # EMA的Uma配置：15-5-5-15
        ema_uma_config = {1: 15000, 2: 5000, 3: -5000, 4: -15000}

        # 按日期正确排序文件
        sorted_ema_files = sort_files_by_date(ema_files)

        ema_results = []
        ema_round_counts = []
        for fp in sorted_ema_files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                summary = summarize_log(data)
                ema_results.append(summary)
                ema_round_counts.append(len(data.get("log", [])))
            except Exception as ex:
                print(f"  处理失败: {fp} - {ex}", file=sys.stderr)

        # 提取最新日期
        ema_latest_date = extract_latest_date(ema_files)

        # 提取所有牌谱（使用EMA的Uma配置和起始分数30000）
        ema_recent_games = extract_recent_games(sorted_ema_files, ema_results, count=len(sorted_ema_files), uma_config=ema_uma_config, origin_points=30000)

        # 计算玩家统计数据（使用EMA的Uma配置和起始分数30000）
        ema_stats = calculate_player_stats(ema_results, ema_round_counts, uma_config=ema_uma_config, origin_points=30000)
        ema_stats_dict = dict(ema_stats)

        # 提取league_average
        ema_league_avg = ema_stats_dict.pop("_league_average", {})

        # EMA暂时没有荣誉牌谱（可以后续添加）
        ema_honor_games = []

        # 生成中文版（使用通用的联赛标签页模板）
        ema_html_zh = generate_league_tabs_page(
            stats_dict=ema_stats_dict,
            league_avg=ema_league_avg,
            honor_games=ema_honor_games,
            recent_games=ema_recent_games,
            sorted_files=sorted_ema_files,
            results=ema_results,
            latest_date=ema_latest_date,
            lang='zh',
            league_name='ema'
        )
        with open("docs/ema.html", "w", encoding="utf-8") as f:
            f.write(ema_html_zh)
        print(f"✓ 已生成 docs/ema.html (中文, 处理了 {len(ema_results)} 个文件)", file=sys.stderr)

        # 生成英文版（使用通用的联赛标签页模板）
        ema_html_en = generate_league_tabs_page(
            stats_dict=ema_stats_dict,
            league_avg=ema_league_avg,
            honor_games=ema_honor_games,
            recent_games=ema_recent_games,
            sorted_files=sorted_ema_files,
            results=ema_results,
            latest_date=ema_latest_date,
            lang='en',
            league_name='ema'
        )
        with open("docs/ema-en.html", "w", encoding="utf-8") as f:
            f.write(ema_html_en)
        print(f"✓ 已生成 docs/ema-en.html (英文, 处理了 {len(ema_results)} 个文件)", file=sys.stderr)

        if ema_latest_date:
            print(f"  最新牌谱日期: {ema_latest_date}", file=sys.stderr)
    else:
        # 如果没有EMA数据，生成占位页面
        print("⚠ 未找到 EMA 数据文件，生成占位页面", file=sys.stderr)
        ema_html_zh = generate_ema_page(lang='zh')
        with open("docs/ema.html", "w", encoding="utf-8") as f:
            f.write(ema_html_zh)
        print("✓ 已生成 docs/ema.html (中文)", file=sys.stderr)

        ema_html_en = generate_ema_page(lang='en')
        with open("docs/ema-en.html", "w", encoding="utf-8") as f:
            f.write(ema_html_en)
        print("✓ 已生成 docs/ema-en.html (英文)", file=sys.stderr)

    # 生成三麻荣誉牌谱页面
    print("正在处理三麻数据...", file=sys.stderr)
    sanma_folder = "game-logs/sanma"
    if os.path.exists(sanma_folder):
        yakuman_games = extract_sanma_yakuman(sanma_folder)
        print(f"✓ 找到 {len(yakuman_games)} 个役满", file=sys.stderr)

        # 生成中文版
        sanma_html_zh = generate_sanma_honor_html(yakuman_games, lang='zh')
        with open("docs/sanma-honor.html", "w", encoding="utf-8") as f:
            f.write(sanma_html_zh)
        print("✓ 已生成 docs/sanma-honor.html (中文)", file=sys.stderr)

        # 生成英文版
        sanma_html_en = generate_sanma_honor_html(yakuman_games, lang='en')
        with open("docs/sanma-honor-en.html", "w", encoding="utf-8") as f:
            f.write(sanma_html_en)
        print("✓ 已生成 docs/sanma-honor-en.html (英文)", file=sys.stderr)
    else:
        print("⚠ 未找到三麻数据文件夹", file=sys.stderr)

    print("\n网站生成完成！", file=sys.stderr)
    print("请将 docs 文件夹的内容推送到 GitHub Pages", file=sys.stderr)


if __name__ == "__main__":
    # 确保 docs 目录存在
    os.makedirs("docs", exist_ok=True)
    main()
