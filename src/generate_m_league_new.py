#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立脚本 - 生成带标签页的M-League统计页面
"""

import os
import sys
import json
import html as html_module

# 导入现有功能
from player_stats import calculate_player_stats, scan_files, summarize_log, YAKU_TRANSLATION
from template_renderer import render_m_league_tabs
from generate_m_league_tabs import generate_ranking_content
from generate_website import (
    TRANSLATIONS,
    YAKU_TRANSLATION_EN,
    sort_files_by_date,
    extract_latest_date,
    extract_recent_games
)


def generate_recent_games_content(recent_games, stats_data, t, lang='zh'):
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
        player_tabs += f'<button class="player-filter-btn" data-player="{player["name"]}">{player["name"]} ({player["games"]}{t.get("games", "局")})</button>\n'

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
    <!-- Rating曲线图容器 -->
    <div id="ratingChartContainer" style="display: none; margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h3 id="chartPlayerName" style="text-align: center; color: #667eea; margin-bottom: 20px;"></h3>
        <canvas id="ratingChart" width="800" height="400"></canvas>
    </div>

    <!-- 玩家筛选选项卡 -->
    <div class="player-filter-tabs" style="margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 8px;">
        {player_tabs}
    </div>

    <!-- 牌谱表格 -->
    <div class="table-scroll">
        <table class="recent-games-table" id="gamesTable">
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


def generate_honor_games_content(honor_games, t, lang='zh'):
    """生成荣誉牌谱内容"""
    if not honor_games or len(honor_games) == 0:
        return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_honor_games', '暂无荣誉牌谱')}</p>"

    honor_cards = ""
    for game in honor_games:
        # 翻译役种，对宝牌保留飜数
        yaku_list = game.get('yaku_list', [])
        translated_yaku_parts = []
        total_han = 0  # 计算总番数

        for y in yaku_list:
            if '(' in y:
                yaku_name = y.split('(')[0]
                yaku_han = y.split('(')[1].rstrip(')')  # 提取飜数，如 "5飜"

                # 提取数字部分并累加
                han_num_str = yaku_han.replace('飜', '').replace('番', '').replace('役満', '')
                if han_num_str and han_num_str.isdigit():
                    total_han += int(han_num_str)

                # 对于宝牌类型，保留飜数显示
                if yaku_name in ['Dora', 'Ura Dora', 'Red Five']:
                    if lang == 'zh':
                        translated_name = YAKU_TRANSLATION.get(yaku_name, yaku_name)
                        # 提取数字部分
                        han_num = yaku_han.replace('飜', '').replace('番', '')
                        translated_yaku_parts.append(f"{translated_name}x{han_num}")
                    else:
                        translated_name = YAKU_TRANSLATION_EN.get(yaku_name, yaku_name)
                        han_num = yaku_han.replace('飜', '').replace('番', '')
                        translated_yaku_parts.append(f"{translated_name}x{han_num}")
                else:
                    # 其他役种不显示飜数
                    if lang == 'zh':
                        translated_yaku_parts.append(YAKU_TRANSLATION.get(yaku_name, yaku_name))
                    else:
                        translated_yaku_parts.append(YAKU_TRANSLATION_EN.get(yaku_name, yaku_name))
            else:
                # 没有飜数的役种
                if lang == 'zh':
                    translated_yaku_parts.append(YAKU_TRANSLATION.get(y, y))
                else:
                    translated_yaku_parts.append(YAKU_TRANSLATION_EN.get(y, y))

        # 添加总番数（如果有的话）
        if total_han > 0:
            han_text = f"{total_han}番" if lang == 'zh' else f"{total_han}han"
            translated_yaku = f"{han_text}: " + ', '.join(translated_yaku_parts)
        else:
            translated_yaku = ', '.join(translated_yaku_parts)

        # 处理 game_type，将 Kazoe Yakuman 视为三倍满
        point_desc = game.get('point_desc', '')
        game_type = game.get('type', 'yakuman')

        # 如果 point_desc 包含 "Kazoe Yakuman"，替换为三倍满
        if 'Kazoe Yakuman' in point_desc:
            game_type = 'sanbaiman'
            game_type_text = t['sanbaiman']  # "三倍满"
            game_type_class = 'sanbaiman'
        else:
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

    html_content = f"""
    <div class="honor-games-grid">
        {honor_cards}
    </div>
    """

    return html_content


def generate_player_details_html(name, data, t, lang='zh', league_avg=None):
    """生成单个玩家的详细数据HTML"""
    if league_avg is None:
        league_avg = {}

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
                yaku_name = YAKU_TRANSLATION.get(yaku, yaku)
            else:
                yaku_name = YAKU_TRANSLATION_EN.get(yaku, yaku)
            rate = data['yaku_rate'].get(yaku, 0)
            avg_rate = league_avg.get('yaku_rate', {}).get(yaku, 0) if league_avg else 0
            avg_text = f' <span class="league-avg">({t["average"]}{avg_rate}%)</span>' if avg_rate > 0 else ''
            yaku_html += f"<li>{yaku_name}: {count}{t['times']} ({rate}%){avg_text}</li>"

    # 对战情况表格
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
        vs_players_html += """
            </tbody>
        </table>
        """

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


def generate_m_league_tabs_page(lang='zh'):
    """生成M-League标签页页面"""
    print(f"正在生成 M-League 标签页 ({lang})...", file=sys.stderr)

    t = TRANSLATIONS[lang]

    # 加载M-League数据
    m_league_folder = "game-logs/m-league"
    files = scan_files(m_league_folder, "*.json", recursive=True)

    if not files:
        print("⚠ 未找到 M-League 数据文件", file=sys.stderr)
        return None

    # 按日期排序
    sorted_files = sort_files_by_date(files)

    # 处理所有游戏数据
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

    # 计算统计数据
    stats = calculate_player_stats(results, round_counts)
    stats_dict = dict(stats)

    # 提取league_average
    league_avg = stats_dict.pop("_league_average", {})

    # 提取最新日期
    latest_date = extract_latest_date(files)

    # 提取所有牌谱
    recent_games = extract_recent_games(sorted_files, results, count=len(sorted_files))

    # 加载荣誉牌谱
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

    # 生成各个标签页的内容
    recent_content = generate_recent_games_content(recent_games, stats_dict, t, lang)
    honor_content = generate_honor_games_content(honor_games, t, lang)
    ranking_content = generate_ranking_content(stats_dict, t, league_avg)

    # 生成玩家详情内容
    # 按对局数排序玩家
    sorted_players = sorted(stats_dict.items(), key=lambda x: (-x[1]["games"], x[0]))

    # 生成下拉选项
    player_options = ""
    for name, data in sorted_players:
        player_options += f'<option value="{name}">{name} ({data["games"]}局)</option>\n'

    # 生成每个玩家的详细HTML
    players_data = {}
    for name, data in sorted_players:
        player_html = generate_player_details_html(name, data, t, lang, league_avg)
        players_data[name] = player_html

    # 确定链接
    if lang == 'zh':
        other_stats_page = 'm-league-test-en.html'
        current_index = 'index.html'
        switch_lang_text = 'English'
        title = 'M-League 数据统计'
    else:
        other_stats_page = 'm-league-test.html'
        current_index = 'index-en.html'
        switch_lang_text = '中文'
        title = 'M-League Statistics'

    # 日期信息
    date_info = f"{t['data_updated']}: {latest_date}" if latest_date else ""

    # 标签文本
    tab_texts = {
        'recent': t['tab_recent'],
        'honor': t['tab_honor'],
        'ranking': t['tab_ranking'],
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
        player_options=player_options,
        players_data=players_data,
        select_player_label=t['select_player'],
        choose_player=t['choose_player'],
        select_player_prompt=t['select_player_prompt']
    )

    return html_content


def main():
    """主函数"""
    print("开始生成新版M-League页面...", file=sys.stderr)

    # 生成中文版
    html_zh = generate_m_league_tabs_page(lang='zh')
    if html_zh:
        output_path_zh = "docs/m-league-test.html"
        with open(output_path_zh, "w", encoding="utf-8") as f:
            f.write(html_zh)
        print(f"✓ 已生成 {output_path_zh}", file=sys.stderr)

    # 生成英文版
    html_en = generate_m_league_tabs_page(lang='en')
    if html_en:
        output_path_en = "docs/m-league-test-en.html"
        with open(output_path_en, "w", encoding="utf-8") as f:
            f.write(html_en)
        print(f"✓ 已生成 {output_path_en}", file=sys.stderr)

    print("✅ 新版M-League页面生成完成！", file=sys.stderr)
    print("   请在浏览器中打开 docs/m-league-test.html 查看效果", file=sys.stderr)


if __name__ == "__main__":
    main()
