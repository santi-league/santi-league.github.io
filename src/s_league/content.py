# -*- coding: utf-8 -*-
"""
S-League 内容生成器

S-League不使用Rating(R值)概念，牌谱历史和总排名只基于实际得点（总分）展示。
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from summarize_v23 import load_player_aliases, normalize_player_name


def _compute_running_score_totals(recent_games):
    """
    为每局比赛的每个玩家计算局前总分/局后总分（按别名合并统计）

    recent_games 为最新在前的列表；按时间正序（从旧到新）累加点数变化，
    然后把结果写回原有的players_detail字典中（原地修改）。
    """
    alias_map = load_player_aliases()
    running_totals = {}

    for game in reversed(recent_games):
        for p in game.get('players_detail', []):
            main_id = normalize_player_name(p['name'], alias_map)
            score_before = running_totals.get(main_id, 0.0)
            score_after = score_before + p['score_change']
            p['score_before'] = round(score_before, 1)
            p['score_after'] = round(score_after, 1)
            running_totals[main_id] = score_after

    return recent_games


def generate_recent_games_content_s_league(recent_games, stats_data, t, lang='zh'):
    """生成S-League牌谱历史内容（无Rating概念，仅展示分数变化）"""
    if not recent_games or len(recent_games) == 0:
        return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_recent_games', '暂无最近牌谱')}</p>"

    recent_games = _compute_running_score_totals(recent_games)

    alias_map = load_player_aliases()

    # 收集所有玩家信息并按半庄数排序（用于筛选选项卡）
    player_list = []
    for player_name, data in stats_data.items():
        if player_name == "_league_average":
            continue
        main_id = data.get('main_id', player_name)
        player_list.append({
            'name': player_name,
            'main_id': main_id,
            'games': data['games']
        })
    player_list.sort(key=lambda x: -x['games'])

    player_tabs = ""
    all_text = t.get('all_players', '所有玩家')
    player_tabs += f'<button class="player-filter-btn active" data-player="all">{all_text}</button>\n'
    for player in player_list:
        games_text = t.get('games', '局')
        player_tabs += f'<button class="player-filter-btn" data-player="{player["main_id"]}">{player["name"]} ({player["games"]}{games_text})</button>\n'

    # 构建游戏数据（JSON格式，供JavaScript使用），同时收集每个玩家的总分变化历史
    games_data = []
    player_score_history = {}  # 每个玩家的总分历史（按主ID存储，从最新到最旧）

    for game in recent_games:
        date_str = game['date'] if lang == 'zh' else game['date_en']
        players_data = game.get('players_detail', [])

        game_data = {
            'date': date_str,
            'players': []
        }

        for p in players_data:
            main_id = normalize_player_name(p['name'], alias_map)
            game_data['players'].append({
                'name': main_id,
                'original_name': p['name'],
                'rank': p['rank'],
                'score_before': p['score_before'],
                'final_points': p['final_points'],
                'score_change': p['score_change'],
                'score_after': p['score_after']
            })

            if main_id not in player_score_history:
                player_score_history[main_id] = []
            player_score_history[main_id].append({
                'date': date_str,
                'games': p.get('games_before', 0),
                'score': p['score_after']
            })

        games_data.append(game_data)

    games_json = json.dumps(games_data, ensure_ascii=False)
    score_history_json = json.dumps(player_score_history, ensure_ascii=False)

    player_label = t['player']
    score_before_label = t.get('score_before_total', '局前总分' if lang == 'zh' else 'Score Before')
    final_points_label = t['final_points']
    score_change_label = t['score_change_pt']
    score_after_label = t.get('score_after_total', '局后总分' if lang == 'zh' else 'Score After')

    header_cols = "".join(f"""
                    <th>{player_label}</th>
                    <th>{score_before_label}</th>
                    <th>{final_points_label}</th>
                    <th>{score_change_label}</th>
                    <th>{score_after_label}</th>""" for _ in range(4))

    html_content = f"""
    <!-- 玩家筛选选项卡 -->
    <div class="player-filter-tabs" style="margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 8px;">
        {player_tabs}
    </div>

    <!-- 总分曲线图容器 -->
    <div id="scoreChartContainer" style="display: none; margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h3 id="chartPlayerName" style="text-align: center; color: #c15b42; margin-bottom: 20px;"></h3>
        <canvas id="scoreChart" width="800" height="400"></canvas>
    </div>

    <!-- 牌谱表格 -->
    <div class="table-scroll">
        <table class="recent-games-table" id="gamesTable">
            <thead>
                <tr>
                    <th rowspan="2">{t['game_date']}</th>
                    <th colspan="5">{t['player']}1</th>
                    <th colspan="5">{t['player']}2</th>
                    <th colspan="5">{t['player']}3</th>
                    <th colspan="5">{t['player']}4</th>
                </tr>
                <tr>{header_cols}
                </tr>
            </thead>
            <tbody id="gamesTableBody">
            </tbody>
        </table>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const gamesData = {games_json};
        const scoreHistory = {score_history_json};
        let currentScoreChart = null;

        function renderGamesTable(filterPlayer = 'all') {{
            const tbody = document.getElementById('gamesTableBody');
            tbody.innerHTML = '';

            const filteredGames = filterPlayer === 'all'
                ? gamesData
                : gamesData.filter(game => game.players.some(p => p.name === filterPlayer));

            filteredGames.forEach(game => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `<td class="game-date">${{game.date}}</td>`;

                game.players.forEach(p => {{
                    const rankClass = `rank-${{p.rank}}`;
                    const highlightClass = (filterPlayer !== 'all' && p.name === filterPlayer) ? 'highlight-player' : '';
                    const displayName = p.original_name || p.name;
                    tr.innerHTML += `
                        <td class="player-name ${{rankClass}} ${{highlightClass}}">${{displayName}}</td>
                        <td class="r-value">${{p.score_before.toFixed(1)}}</td>
                        <td class="final-points">${{p.final_points}}</td>
                        <td class="score-change">${{p.score_change >= 0 ? '+' : ''}}${{p.score_change.toFixed(1)}}</td>
                        <td class="r-value">${{p.score_after.toFixed(1)}}</td>
                    `;
                }});

                tbody.appendChild(tr);
            }});
        }}

        // 绘制总分曲线图
        function drawScoreChart(playerName) {{
            const container = document.getElementById('scoreChartContainer');
            const chartTitle = document.getElementById('chartPlayerName');
            const ctx = document.getElementById('scoreChart').getContext('2d');

            if (!scoreHistory[playerName]) {{
                container.style.display = 'none';
                return;
            }}

            container.style.display = 'block';
            chartTitle.textContent = `${{playerName}} - {'Total Score' if lang == 'en' else '总分'}{t.get('change_curve', '变化曲线' if lang == 'zh' else '')}`;

            // 反转数据（从最早到最新）
            const data = [...scoreHistory[playerName]].reverse();

            const labels = data.map((d, idx) => `${{d.date}}\\n(${{d.games}}{t.get('games', '局')})`);
            const scoreValues = data.map(d => d.score);

            if (currentScoreChart) {{
                currentScoreChart.destroy();
            }}

            currentScoreChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: '{"Total Score" if lang == "en" else "总分"}',
                        data: scoreValues,
                        borderColor: '#c15b42',
                        backgroundColor: 'rgba(193, 91, 66, 0.1)',
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
                                    return `{"Total Score" if lang == "en" else "总分"}: ${{context.parsed.y.toFixed(1)}}`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            title: {{
                                display: true,
                                text: '{"Total Score" if lang == "en" else "总分"}'
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
                                    const totalPoints = data.length;
                                    let skipInterval;

                                    if (totalPoints <= 20) {{
                                        skipInterval = 1;
                                    }} else if (totalPoints <= 40) {{
                                        skipInterval = 2;
                                    }} else if (totalPoints <= 60) {{
                                        skipInterval = 3;
                                    }} else if (totalPoints <= 80) {{
                                        skipInterval = 4;
                                    }} else if (totalPoints <= 100) {{
                                        skipInterval = 5;
                                    }} else if (totalPoints <= 120) {{
                                        skipInterval = 6;
                                    }} else {{
                                        skipInterval = 8;
                                    }}

                                    if (index === 0 || index === data.length - 1) {{
                                        return labels[index];
                                    }}

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

        document.querySelectorAll('.player-filter-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                document.querySelectorAll('.player-filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const playerName = this.getAttribute('data-player');
                renderGamesTable(playerName);

                if (playerName === 'all') {{
                    document.getElementById('scoreChartContainer').style.display = 'none';
                    if (currentScoreChart) {{
                        currentScoreChart.destroy();
                        currentScoreChart = null;
                    }}
                }} else {{
                    drawScoreChart(playerName);
                }}
            }});
        }});

        renderGamesTable('all');
    </script>
    """

    return html_content


def _format_total_score(total_score):
    """总分统一按/1000显示（与牌谱历史的pt单位保持一致）"""
    scaled = total_score / 1000
    return f"{scaled:+.1f}" if scaled != 0 else "0"


def generate_ranking_content_s_league(stats_data, t, league_avg, lang='zh'):
    """生成S-League总排名内容（无Rating概念，按总得分排名）"""
    qualified_players = []
    unqualified_players = []

    for player_name, data in stats_data.items():
        if player_name == "_league_average":
            continue
        if data['games'] >= 10:
            qualified_players.append((player_name, data))
        else:
            unqualified_players.append((player_name, data))

    qualified_players.sort(key=lambda x: -x[1]['total_score'])

    rank_emojis = ['🥇', '🥈', '🥉']

    rows_html = ""
    for idx, (player_name, data) in enumerate(qualified_players):
        rank = idx + 1
        rank_emoji = rank_emojis[rank - 1] + ' ' if rank <= 3 else ''
        total_score_display = _format_total_score(data['total_score'])
        rows_html += f"""
                    <tr>
                        <td style="padding: 12px; text-align: center; font-weight: bold; font-size: 18px;">{rank_emoji}{rank}</td>
                        <td style="padding: 12px; font-weight: 600;">{player_name}</td>
                        <td style="padding: 12px; text-align: center; color: #c15b42; font-weight: bold;">{total_score_display}</td>
                        <td style="padding: 12px; text-align: center;">{data['games']}</td>
                        <td style="padding: 12px; text-align: center;">{data['total_rounds']}</td>
                        <td style="padding: 12px; text-align: center;">{data['avg_rank']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{data['rank_1_rate']:.1f}%</td>
                        <td style="padding: 12px; text-align: center;">{data['win_rate']:.1f}%</td>
                    </tr>"""

    finals_note = (
        '前四名（正式排名，≥10半庄）将进入S-League最高位决定战'
        if lang == 'zh' else
        'The top 4 players (official rankings, ≥10 games) advance to the S-League Championship Finals'
    )

    html = f"""
    <div style="margin-bottom: 20px;">
        <h2 style="color: #c15b42; margin: 0 0 10px 0;">{t.get('qualified_players', '正式排名')} (≥10{t.get('games', '半庄')})</h2>
        <div class="summary-box" style="border-left-color: #c15b42;">
            <span class="summary-label">🏆 {finals_note}</span>
        </div>
    </div>

    <div style="margin-bottom: 40px;">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background: #c15b42; color: white;">
                        <th style="padding: 12px; text-align: center;">{t.get('rank', '排名')}</th>
                        <th style="padding: 12px;">{t['player']}</th>
                        <th style="padding: 12px; text-align: center;">{t['total_score']}</th>
                        <th style="padding: 12px; text-align: center;">{t['games']}</th>
                        <th style="padding: 12px; text-align: center;">{t['rounds']}</th>
                        <th style="padding: 12px; text-align: center;">{t['avg_rank']}</th>
                        <th style="padding: 12px; text-align: center;">{t.get('rank_1_rate', '一位率')}</th>
                        <th style="padding: 12px; text-align: center;">{t.get('win_rate', '和牌率')}</th>
                    </tr>
                </thead>
                <tbody>{rows_html}
                </tbody>
            </table>
        </div>
    </div>
    """

    if unqualified_players:
        unqualified_players.sort(key=lambda x: -x[1]['games'])

        html += f"""
        <div>
            <h2 style="color: #999; margin-bottom: 20px;">{t.get('unqualified_players', '新人榜')} (<10{t.get('games', '半庄')})</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background: #999; color: white;">
                            <th style="padding: 12px;">{t['player']}</th>
                            <th style="padding: 12px; text-align: center;">{t['games']}</th>
                            <th style="padding: 12px; text-align: center;">{t['rounds']}</th>
                            <th style="padding: 12px; text-align: center;">{t['total_score']}</th>
                            <th style="padding: 12px; text-align: center;">{t['avg_rank']}</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for player_name, data in unqualified_players:
            total_score_display = _format_total_score(data['total_score'])
            html += f"""
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 12px; font-weight: 600;">{player_name}</td>
                            <td style="padding: 12px; text-align: center; font-weight: bold;">{data['games']}</td>
                            <td style="padding: 12px; text-align: center;">{data['total_rounds']}</td>
                            <td style="padding: 12px; text-align: center;">{total_score_display}</td>
                            <td style="padding: 12px; text-align: center;">{data['avg_rank']:.2f}</td>
                        </tr>
            """

        html += """
                    </tbody>
                </table>
            </div>
        </div>
        """

    return html


def _generate_top5_table(title, rows, value_label, t):
    """生成单个Top5排行榜小表格（rows为[(玩家名, 数值显示字符串), ...]，最多5条）"""
    rank_emojis = ['🥇', '🥈', '🥉']

    if not rows:
        body_html = """
                    <tr>
                        <td colspan="3" style="padding: 20px; text-align: center; color: #999;">-</td>
                    </tr>"""
    else:
        body_html = ""
        for idx, (player_name, value_display) in enumerate(rows):
            rank = idx + 1
            rank_emoji = rank_emojis[rank - 1] + ' ' if rank <= 3 else ''
            body_html += f"""
                    <tr>
                        <td style="padding: 10px; text-align: center; font-weight: bold;">{rank_emoji}{rank}</td>
                        <td style="padding: 10px; font-weight: 600;">{player_name}</td>
                        <td style="padding: 10px; text-align: center; color: #c15b42; font-weight: bold;">{value_display}</td>
                    </tr>"""

    return f"""
    <div style="background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
        <h3 style="margin: 0; padding: 16px 20px; background: #c15b42; color: white; font-size: 18px;">{title}</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f8f9fa;">
                    <th style="padding: 10px; text-align: center; color: #666; font-size: 13px;">#</th>
                    <th style="padding: 10px; text-align: center; color: #666; font-size: 13px;">{t['player']}</th>
                    <th style="padding: 10px; text-align: center; color: #666; font-size: 13px;">{value_label}</th>
                </tr>
            </thead>
            <tbody>{body_html}
            </tbody>
        </table>
    </div>
    """


def generate_top5_leaderboards_content_s_league(stats_data, t, lang='zh', min_games=10):
    """
    生成S-League排行榜内容：一位率/避四率/出勤半庄数，各取前5名

    一位率、避四率仅统计半庄数达标（默认>=10）的玩家，避免小样本失真；
    出勤半庄数按全部玩家统计。
    """
    players = [(name, data) for name, data in stats_data.items() if name != "_league_average"]
    qualified = [(name, data) for name, data in players if data['games'] >= min_games]

    rank_1_rows = sorted(qualified, key=lambda x: -x[1]['rank_1_rate'])[:5]
    rank_1_rows = [(name, f"{data['rank_1_rate']:.1f}%") for name, data in rank_1_rows]

    avoid_last_rows = sorted(qualified, key=lambda x: x[1]['rank_4_rate'])[:5]
    avoid_last_rows = [(name, f"{100 - data['rank_4_rate']:.1f}%") for name, data in avoid_last_rows]

    attendance_rows = sorted(players, key=lambda x: -x[1]['games'])[:5]
    games_label = t.get('games', '半庄')
    attendance_rows = [(name, f"{data['games']}{games_label}") for name, data in attendance_rows]

    top5_label = 'Top 5' if lang == 'en' else '前5名'
    qualify_note = f"({t.get('qualified_players', '正式排名')} ≥{min_games} {t.get('games', '半庄')})"

    rank_1_table = _generate_top5_table(
        f"{t.get('rank_1_rate', '1位率')} {top5_label} {qualify_note}",
        rank_1_rows, t.get('rank_1_rate', '1位率'), t
    )
    avoid_last_table = _generate_top5_table(
        f"{t.get('avoid_last_rate', '避四率')} {top5_label} {qualify_note}",
        avoid_last_rows, t.get('avoid_last_rate', '避四率'), t
    )
    attendance_table = _generate_top5_table(
        f"{t.get('attendance_games', '出勤半庄数')} {top5_label}",
        attendance_rows, t.get('attendance_games', '出勤半庄数'), t
    )

    return f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
        {rank_1_table}
        {avoid_last_table}
        {attendance_table}
    </div>
    """


def generate_finals_content_s_league(finals_data, t, lang='zh'):
    """
    生成S-League最高位决定战内容：一张表，每行一名选手，
    每个半庄对应"名次"+"分数"两列，最右侧为总分，按总分从高到低排序
    """
    games = finals_data.get('games', [])
    dates = finals_data.get('dates', [])

    if not games:
        msg = '决定战尚未开始，敬请期待' if lang == 'zh' else 'The Championship Finals have not started yet'
        return f"<p style='text-align: center; color: #999; padding: 40px;'>{msg}</p>"

    alias_map = load_player_aliases()

    player_order = []
    player_rounds = {}  # main_id -> [(rank, final_points) 或 None, ...]，与games等长

    for game_idx, game in enumerate(games):
        for p in game:
            main_id = normalize_player_name(p['name'], alias_map)
            if main_id not in player_rounds:
                player_rounds[main_id] = [None] * len(games)
                player_order.append(main_id)
            player_rounds[main_id][game_idx] = (p['rank'], p['final_points'])

    totals = {
        main_id: sum(r[1] for r in rounds if r is not None)
        for main_id, rounds in player_rounds.items()
    }

    ranked_players = sorted(player_order, key=lambda main_id: -totals[main_id])

    game_label = t.get('games', '半庄' if lang == 'zh' else 'Game')
    rank_label = '名次' if lang == 'zh' else 'Rank'
    score_label = '分数' if lang == 'zh' else 'Score'
    total_label = '总分' if lang == 'zh' else 'Total'

    header_row1 = f'<th rowspan="2" style="padding: 12px;">{t["player"]}</th>'
    header_row2 = ""
    for game_idx in range(len(games)):
        game_num_label = f"第{game_idx + 1}{game_label}" if lang == 'zh' else f"{game_label} {game_idx + 1}"
        date_str = dates[game_idx] if game_idx < len(dates) and dates[game_idx] else ""
        sub_label = f"{game_num_label}<br><span style=\"font-weight: normal; font-size: 11px; opacity: 0.85;\">{date_str}</span>" if date_str else game_num_label
        header_row1 += f'<th colspan="2" style="padding: 12px; text-align: center;">{sub_label}</th>'
        header_row2 += f'<th style="padding: 8px; text-align: center; font-size: 12px;">{rank_label}</th>'
        header_row2 += f'<th style="padding: 8px; text-align: center; font-size: 12px;">{score_label}</th>'
    header_row1 += f'<th rowspan="2" style="padding: 12px; text-align: center;">{total_label}</th>'

    rank_emojis = ['🥇', '🥈', '🥉']
    rows_html = ""
    for idx, main_id in enumerate(ranked_players):
        position = idx + 1
        position_emoji = rank_emojis[position - 1] + ' ' if position <= 3 else ''
        rounds = player_rounds[main_id]

        cells = ""
        for r in rounds:
            if r is None:
                cells += '<td style="padding: 10px; text-align: center; color: #ccc;">-</td>' * 2
            else:
                rank, final_points = r
                rank_color = '#c15b42' if rank == 1 else '#333'
                cells += f'<td style="padding: 10px; text-align: center; color: {rank_color}; font-weight: {"bold" if rank == 1 else "normal"};">{rank}</td>'
                cells += f'<td style="padding: 10px; text-align: center;">{final_points}</td>'

        total_display = f"{totals[main_id]:+}" if totals[main_id] != 0 else "0"

        rows_html += f"""
                    <tr>
                        <td style="padding: 12px; font-weight: bold;">{position_emoji}{main_id}</td>
                        {cells}
                        <td style="padding: 12px; text-align: center; color: #c15b42; font-weight: bold; font-size: 16px;">{total_display}</td>
                    </tr>"""

    return f"""
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background: #c15b42; color: white;">{header_row1}</tr>
                <tr style="background: #c15b42; color: white;">{header_row2}</tr>
            </thead>
            <tbody>{rows_html}
            </tbody>
        </table>
    </div>
    """
