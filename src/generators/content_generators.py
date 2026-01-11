# -*- coding: utf-8 -*-
"""
内容块生成器模块 - 用于生成M-League页面的各种内容块
"""

import sys
import os
import json
import html as html_module

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.translations import YAKU_TRANSLATION, YAKU_TRANSLATION_EN

# 导入别名处理函数
try:
    from summarize_v23 import load_player_aliases, normalize_player_name
except ImportError:
    # 如果导入失败，使用空的别名映射
    def load_player_aliases():
        return {}
    def normalize_player_name(name, alias_map=None):
        return name


# ============================================================================
# 排名内容生成
# ============================================================================

def generate_ranking_content(stats_data, t, league_avg):
    """
    生成总排名内容

    将玩家分为两组：
    1. 10个半庄以上：按R值从高到低排列
    2. 10个半庄以下：按半庄数排列
    """
    # 分离玩家
    qualified_players = []  # >= 10个半庄
    unqualified_players = []  # < 10个半庄

    for player_name, data in stats_data.items():
        if player_name == "_league_average":
            continue
        if data['games'] >= 10:
            qualified_players.append((player_name, data))
        else:
            unqualified_players.append((player_name, data))

    # 排序
    qualified_players.sort(key=lambda x: -x[1]['tenhou_r'])  # R值降序
    unqualified_players.sort(key=lambda x: -x[1]['games'])  # 半庄数降序

    # 生成HTML
    html = f"""
    <div style="margin-bottom: 40px;">
        <h2 style="color: #667eea; margin-bottom: 20px;">{t.get('qualified_players', '正式排名')} (≥10{t.get('games', '半庄')})</h2>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background: #667eea; color: white;">
                        <th style="padding: 12px; text-align: center;">排名</th>
                        <th style="padding: 12px;">{t['player']}</th>
                        <th style="padding: 12px; text-align: center;">{t['r_value']}</th>
                        <th style="padding: 12px; text-align: center;">{t['games']}</th>
                        <th style="padding: 12px; text-align: center;">{t['rounds']}</th>
                        <th style="padding: 12px; text-align: center;">{t['avg_rank']}</th>
                        <th style="padding: 12px; text-align: center;">{t.get('rank_1_rate', '一位率')}</th>
                        <th style="padding: 12px; text-align: center;">{t.get('win_rate', '和牌率')}</th>
                    </tr>
                </thead>
                <tbody>
    """

    rank_emojis = ['🥇', '🥈', '🥉']
    for idx, (player_name, data) in enumerate(qualified_players, 1):
        rank_emoji = rank_emojis[idx - 1] if idx <= 3 else ''
        row_bg = '#f8f9fa' if idx % 2 == 0 else 'white'

        html += f"""
                    <tr style="background: {row_bg};">
                        <td style="padding: 12px; text-align: center; font-weight: bold; font-size: 18px;">{rank_emoji} {idx}</td>
                        <td style="padding: 12px; font-weight: 600;">{player_name}</td>
                        <td style="padding: 12px; text-align: center; color: #667eea; font-weight: bold;">{data['tenhou_r']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{data['games']}</td>
                        <td style="padding: 12px; text-align: center;">{data['total_rounds']}</td>
                        <td style="padding: 12px; text-align: center;">{data['avg_rank']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{data['rank_1_rate']:.1f}%</td>
                        <td style="padding: 12px; text-align: center;">{data['win_rate']:.1f}%</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>
    </div>
    """

    # 未达标玩家
    if unqualified_players:
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
                            <th style="padding: 12px; text-align: center;">{t['r_value']}</th>
                            <th style="padding: 12px; text-align: center;">{t['avg_rank']}</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for player_name, data in unqualified_players:
            html += f"""
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 12px; font-weight: 600;">{player_name}</td>
                            <td style="padding: 12px; text-align: center; font-weight: bold;">{data['games']}</td>
                            <td style="padding: 12px; text-align: center;">{data['total_rounds']}</td>
                            <td style="padding: 12px; text-align: center;">{data['tenhou_r']:.2f}</td>
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


# ============================================================================
# 最近牌谱内容生成
# ============================================================================

def generate_recent_games_content_for_tabs(recent_games, stats_data, t, lang='zh', alias_map=None):
    """生成最近牌谱内容 - 带玩家筛选和Rating曲线图"""
    if not recent_games or len(recent_games) == 0:
        return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_recent_games', '暂无最近牌谱')}</p>"

    # 加载别名映射（如果没有传入）
    if alias_map is None:
        alias_map = load_player_aliases()

    # 收集所有玩家信息并按半庄数排序
    player_list = []
    for player_name, data in stats_data.items():
        if player_name == "_league_average":
            continue
        # 从stats_data中提取main_id（如果有的话）
        main_id = data.get('main_id', player_name)
        player_list.append({
            'name': player_name,  # 显示名称（带别名）
            'main_id': main_id,   # 主ID（用于数据筛选）
            'games': data['games']
        })
    player_list.sort(key=lambda x: -x['games'])

    # 构建玩家选项卡
    player_tabs = ""
    all_text = t.get('all_players', '所有玩家')
    player_tabs += f'<button class="player-filter-btn active" data-player="all">{all_text}</button>\n'
    for player in player_list:
        games_text = t.get('games', '局')
        # 使用main_id作为data-player属性，显示名称作为按钮文本
        player_tabs += f'<button class="player-filter-btn" data-player="{player["main_id"]}">{player["name"]} ({player["games"]}{games_text})</button>\n'

    # 构建游戏数据（JSON格式，供JavaScript使用）
    games_data = []
    player_rating_history = {}  # 每个玩家的rating历史（按主ID存储）

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
            # 获取原始玩家名并归一化为主ID
            original_name = p['name']
            main_id = normalize_player_name(original_name, alias_map)

            player_info = {
                'name': main_id,  # 使用主ID，确保JavaScript可以正确匹配
                'original_name': original_name,  # 保留原始名称用于显示
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

            # 记录玩家的rating历史（使用主ID作为key）
            if main_id not in player_rating_history:
                player_rating_history[main_id] = []
            player_rating_history[main_id].append({
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

    <!-- Rating计算公式说明 -->
    <div class="rating-formula-section" style="margin-bottom: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
        <div style="display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="toggleFormula()">
            <h3 style="color: white; margin: 0; font-size: 18px; font-weight: 600;">
                <span style="margin-right: 10px;">📊</span>Rating值计算公式
            </h3>
            <span id="formulaToggle" style="color: white; font-size: 20px; transition: transform 0.3s;">▼</span>
        </div>

        <div id="formulaContent" style="display: none; margin-top: 20px; background: white; padding: 20px; border-radius: 8px;">
            <!-- 主公式 -->
            <div style="background: #f8f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; margin-bottom: 20px;">
                <h4 style="color: #667eea; margin: 0 0 10px 0; font-size: 16px;">主公式</h4>
                <div style="font-family: 'Courier New', monospace; font-size: 15px; color: #333; background: white; padding: 12px; border-radius: 6px; text-align: center;">
                    <strong style="color: #764ba2;">Rating变动</strong> = <strong style="color: #667eea;">试合数补正</strong> × (<strong style="color: #f093fb;">得点变化</strong> + <strong style="color: #4facfe;">Rating补正</strong>)
                </div>
            </div>

            <!-- 详细步骤 -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
                <!-- 步骤1 -->
                <div style="background: #fff5f5; padding: 15px; border-radius: 8px; border-left: 4px solid #f093fb;">
                    <h5 style="color: #f093fb; margin: 0 0 8px 0; font-size: 14px;">① 得点变化（千点单位）</h5>
                    <div style="font-size: 13px; color: #555; line-height: 1.6;">
                        <code style="background: white; padding: 4px 8px; border-radius: 4px; display: block; margin-bottom: 8px;">
                            (Uma + 素点差) / 1000
                        </code>
                        <div style="margin-top: 8px; font-size: 12px; color: #666;">
                            <strong>Uma：</strong><br>
                            • M-League: 1位=+45k, 2位=+5k, 3位=-15k, 4位=-35k<br>
                            • EMA: 1位=+15k, 2位=+5k, 3位=-5k, 4位=-15k<br>
                            <strong>素点差：</strong>最终点数 - 起始点数
                        </div>
                    </div>
                </div>

                <!-- 步骤2 -->
                <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #4facfe;">
                    <h5 style="color: #4facfe; margin: 0 0 8px 0; font-size: 14px;">② Rating补正</h5>
                    <div style="font-size: 13px; color: #555; line-height: 1.6;">
                        <code style="background: white; padding: 4px 8px; border-radius: 4px; display: block; margin-bottom: 8px;">
                            (桌平均Rating - 自己的Rating) / 40
                        </code>
                        <div style="margin-top: 8px; font-size: 12px; color: #666;">
                            • 对手强：补正为正<br>
                            • 对手弱：补正为负<br>
                            <em>→ 强者输少赢多，弱者输多赢少</em>
                        </div>
                    </div>
                </div>

                <!-- 步骤3 -->
                <div style="background: #f5f3ff; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea;">
                    <h5 style="color: #667eea; margin: 0 0 8px 0; font-size: 14px;">③ 试合数补正</h5>
                    <div style="font-size: 13px; color: #555; line-height: 1.6;">
                        <code style="background: white; padding: 4px 8px; border-radius: 4px; display: block; margin-bottom: 8px;">
                            试合数 < 400: 1 - 试合数 × 0.002<br>
                            试合数 ≥ 400: 0.2
                        </code>
                        <div style="margin-top: 8px; font-size: 12px; color: #666;">
                            • 初期：Rating波动大<br>
                            • 后期：Rating稳定（固定0.2）
                        </div>
                    </div>
                </div>
            </div>

            <!-- 示例 -->
            <div style="margin-top: 20px; background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); padding: 15px; border-radius: 8px;">
                <h5 style="color: #d35400; margin: 0 0 10px 0; font-size: 14px;">💡 计算示例</h5>
                <div style="font-size: 12px; color: #555; line-height: 1.8; background: white; padding: 12px; border-radius: 6px;">
                    <strong>条件：</strong>第1名，终局38000点，当前Rating=1650，桌平均Rating=1600，已打50场<br>
                    <strong>计算：</strong><br>
                    • 得点变化 = (45000 + 13000) / 1000 = 58<br>
                    • Rating补正 = (1600 - 1650) / 40 = -1.25<br>
                    • 试合数补正 = 1 - 50 × 0.002 = 0.9<br>
                    • Rating变动 = 0.9 × (58 - 1.25) = <strong style="color: #d35400;">+51.08</strong><br>
                    <strong style="color: #27ae60;">→ 新Rating：1701.08</strong>
                </div>
            </div>
        </div>
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

        // 切换公式显示/隐藏
        function toggleFormula() {{
            const content = document.getElementById('formulaContent');
            const toggle = document.getElementById('formulaToggle');

            if (content.style.display === 'none') {{
                content.style.display = 'block';
                toggle.style.transform = 'rotate(180deg)';
            }} else {{
                content.style.display = 'none';
                toggle.style.transform = 'rotate(0deg)';
            }}
        }}

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
                    // 显示原始玩家名（保持牌谱历史的真实性）
                    const displayName = p.original_name || p.name;
                    tr.innerHTML += `
                        <td class="player-name ${{rankClass}} ${{highlightClass}}">${{displayName}}</td>
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


# ============================================================================
# 荣誉牌谱内容生成
# ============================================================================

def _generate_honor_game_card(game, t, lang='zh'):
    """生成单个荣誉牌谱卡片的HTML"""
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

    # 处理 game_type
    point_desc = game.get('point_desc', '')
    game_type = game.get('type', 'yakuman')

    # 稀有役种使用特殊样式
    if game_type == 'rare_yaku':
        # 获取稀有役种列表，显示具体的役种名称
        rare_yaku_list = game.get('rare_yaku', [])
        if rare_yaku_list:
            # 取第一个稀有役种作为标题
            main_rare_yaku = rare_yaku_list[0]
            if lang == 'zh':
                game_type_text = YAKU_TRANSLATION.get(main_rare_yaku, main_rare_yaku)
            else:
                game_type_text = main_rare_yaku
        else:
            # 兜底显示
            game_type_text = t.get('rare_yaku', '稀有役种') if lang == 'zh' else 'Rare Yaku'
        game_type_class = 'rare-yaku'
    # 如果 point_desc 包含 "Kazoe Yakuman"，替换为三倍满
    elif 'Kazoe Yakuman' in point_desc:
        game_type = 'sanbaiman'
        game_type_text = t['sanbaiman']  # "三倍满"
        game_type_class = 'sanbaiman'
    else:
        game_type_text = t['yakuman'] if game_type == 'yakuman' else t['sanbaiman']
        game_type_class = 'yakuman' if game_type == 'yakuman' else 'sanbaiman'

    escaped_url = html_module.escape(game['tenhou_url'], quote=True)

    return f"""
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


def generate_honor_games_content_for_tabs(honor_games_data, t, lang='zh'):
    """生成荣誉牌谱内容

    支持两种数据格式：
    1. 旧格式：直接传入游戏列表
    2. 新格式：字典包含 'yakuman_sanbaiman_games' 和 'rare_yaku_games'
    """
    # 检查是否为新格式（字典）
    if isinstance(honor_games_data, dict):
        yakuman_sanbaiman_games = honor_games_data.get('yakuman_sanbaiman_games', [])
        rare_yaku_games = honor_games_data.get('rare_yaku_games', [])

        if not yakuman_sanbaiman_games and not rare_yaku_games:
            return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_honor_games', '暂无荣誉牌谱')}</p>"

        html_parts = []

        # 役满和三倍满部分
        if yakuman_sanbaiman_games:
            section_title = "役满 & 三倍満" if lang == 'zh' else "Yakuman & Sanbaiman"
            cards_html = "".join([_generate_honor_game_card(game, t, lang) for game in yakuman_sanbaiman_games])
            html_parts.append(f"""
            <div class="honor-section">
                <h2 style="text-align: center; color: #667eea; margin: 20px 0;">{section_title}</h2>
                <div class="honor-games-grid">{cards_html}</div>
            </div>
            """)

        # 稀有役种部分
        if rare_yaku_games:
            section_title = "稀有役种" if lang == 'zh' else "Rare Yaku"
            cards_html = "".join([_generate_honor_game_card(game, t, lang) for game in rare_yaku_games])
            html_parts.append(f"""
            <div class="honor-section">
                <h2 style="text-align: center; color: #667eea; margin: 40px 0 20px 0;">{section_title}</h2>
                <div class="honor-games-grid">{cards_html}</div>
            </div>
            """)

        return "".join(html_parts)

    else:
        # 旧格式：直接是游戏列表
        honor_games = honor_games_data
        if not honor_games or len(honor_games) == 0:
            return f"<p style='text-align: center; color: #999; padding: 40px;'>{t.get('no_honor_games', '暂无荣誉牌谱')}</p>"

        cards_html = "".join([_generate_honor_game_card(game, t, lang) for game in honor_games])
        return f'<div class="honor-games-grid">{cards_html}</div>'


# ============================================================================
# 玩家详情内容生成
# ============================================================================

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


# ============================================================================
# 排行榜内容生成
# ============================================================================

def generate_leaderboard_content(stats_dict, sorted_files, t, lang='zh'):
    """生成排行榜内容 - 1番手牌频率排行"""
    # 加载别名映射
    alias_map = load_player_aliases()

    # 统计每个玩家的1番手牌次数和总小局数（使用主ID）
    one_han_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计1番手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表并归一化为主ID
            raw_names = data.get('name', [])
            main_ids = [normalize_player_name(name, alias_map) for name in raw_names]

            # 初始化这些玩家的计数器（使用主ID）
            for main_id in main_ids:
                if main_id not in total_rounds_played:
                    total_rounds_played[main_id] = 0
                if main_id not in one_han_counts:
                    one_han_counts[main_id] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1（使用主ID）
                for main_id in main_ids:
                    total_rounds_played[main_id] = total_rounds_played.get(main_id, 0) + 1

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
                            # 使用主ID统计
                            winner_main_id = main_ids[winner_seat] if winner_seat < len(main_ids) else None
                            if winner_main_id:
                                one_han_counts[winner_main_id] = one_han_counts.get(winner_main_id, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和1番手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        # 获取主ID用于匹配统计数据
        main_id = stats.get('main_id', name)
        total_rounds = total_rounds_played.get(main_id, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取1番手牌次数（使用主ID查询）
        one_han_count = one_han_counts.get(main_id, 0)
        one_han_rate = (one_han_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,  # 显示名称（带括号的完整格式）
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
        <h2>1番手牌频率</h2>
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
    # 加载别名映射
    alias_map = load_player_aliases()

    # 统计每个玩家的2番手牌次数和总小局数（使用主ID）
    two_han_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计2番手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表并归一化为主ID
            raw_names = data.get('name', [])
            main_ids = [normalize_player_name(name, alias_map) for name in raw_names]

            # 初始化这些玩家的计数器（使用主ID）
            for main_id in main_ids:
                if main_id not in total_rounds_played:
                    total_rounds_played[main_id] = 0
                if main_id not in two_han_counts:
                    two_han_counts[main_id] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1（使用主ID）
                for main_id in main_ids:
                    total_rounds_played[main_id] = total_rounds_played.get(main_id, 0) + 1

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
                            # 使用主ID统计
                            winner_main_id = main_ids[winner_seat] if winner_seat < len(main_ids) else None
                            if winner_main_id:
                                two_han_counts[winner_main_id] = two_han_counts.get(winner_main_id, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和2番手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        # 获取主ID用于匹配统计数据
        main_id = stats.get('main_id', name)
        total_rounds = total_rounds_played.get(main_id, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取2番手牌次数（使用主ID查询）
        two_han_count = two_han_counts.get(main_id, 0)
        two_han_rate = (two_han_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,  # 显示名称（带括号的完整格式）
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
        title = '2番手牌频率'
    else:
        header_name = 'Player'
        header_count = '2-Han Wins'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'
        title = '2-Han Win Rate'

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
    # 加载别名映射
    alias_map = load_player_aliases()

    # 统计每个玩家的3番以上不到满贯手牌次数和总小局数（使用主ID）
    three_han_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表并归一化为主ID
            raw_names = data.get('name', [])
            main_ids = [normalize_player_name(name, alias_map) for name in raw_names]

            # 初始化这些玩家的计数器（使用主ID）
            for main_id in main_ids:
                if main_id not in total_rounds_played:
                    total_rounds_played[main_id] = 0
                if main_id not in three_han_counts:
                    three_han_counts[main_id] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1（使用主ID）
                for main_id in main_ids:
                    total_rounds_played[main_id] = total_rounds_played.get(main_id, 0) + 1

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
                            # 使用主ID统计
                            winner_main_id = main_ids[winner_seat] if winner_seat < len(main_ids) else None
                            if winner_main_id:
                                three_han_counts[winner_main_id] = three_han_counts.get(winner_main_id, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和3番以上不到满贯手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        # 获取主ID用于匹配统计数据
        main_id = stats.get('main_id', name)
        total_rounds = total_rounds_played.get(main_id, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取手牌次数（使用主ID查询）
        three_han_count = three_han_counts.get(main_id, 0)
        three_han_rate = (three_han_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,  # 显示名称（带括号的完整格式）
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
        title = '3番以上不到满贯频率'
    else:
        header_name = 'Player'
        header_count = 'Count'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'
        title = '3+ Han (Below Mangan) Win Rate'

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
    # 加载别名映射
    alias_map = load_player_aliases()

    # 统计每个玩家的满贯以上手牌次数和总小局数（使用主ID）
    mangan_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计满贯以上手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表并归一化为主ID
            raw_names = data.get('name', [])
            main_ids = [normalize_player_name(name, alias_map) for name in raw_names]

            # 初始化这些玩家的计数器（使用主ID）
            for main_id in main_ids:
                if main_id not in total_rounds_played:
                    total_rounds_played[main_id] = 0
                if main_id not in mangan_counts:
                    mangan_counts[main_id] = 0

            # 遍历每个小局
            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1（使用主ID）
                for main_id in main_ids:
                    total_rounds_played[main_id] = total_rounds_played.get(main_id, 0) + 1

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
                            # 使用主ID统计
                            winner_main_id = main_ids[winner_seat] if winner_seat < len(main_ids) else None
                            if winner_main_id:
                                mangan_counts[winner_main_id] = mangan_counts.get(winner_main_id, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和满贯以上手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        # 获取主ID用于匹配统计数据
        main_id = stats.get('main_id', name)
        total_rounds = total_rounds_played.get(main_id, 0)

        # 只统计玩过超过100小局的玩家
        if total_rounds <= 100:
            continue

        # 获取满贯以上手牌次数（使用主ID查询）
        mangan_count = mangan_counts.get(main_id, 0)
        mangan_rate = (mangan_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,  # 显示名称（带括号的完整格式）
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
        title = '满贯以上手牌频率'
    else:
        header_name = 'Player'
        header_count = 'Mangan+ Wins'
        header_total = 'Total Rounds Played'
        header_rate = 'Rate'
        title = 'Mangan+ Hand Rate'

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
    # 加载别名映射
    alias_map = load_player_aliases()

    # 统计每个玩家的跳满以上手牌次数和总小局数（使用主ID）
    haneman_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计跳满以上手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表并归一化为主ID
            raw_names = data.get('name', [])
            main_ids = [normalize_player_name(name, alias_map) for name in raw_names]

            for main_id in main_ids:
                if main_id not in total_rounds_played:
                    total_rounds_played[main_id] = 0
                if main_id not in haneman_counts:
                    haneman_counts[main_id] = 0

            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                for main_id in main_ids:
                    total_rounds_played[main_id] = total_rounds_played.get(main_id, 0) + 1

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
                            # 使用主ID统计
                            winner_main_id = main_ids[winner_seat] if winner_seat < len(main_ids) else None
                            if winner_main_id:
                                haneman_counts[winner_main_id] = haneman_counts.get(winner_main_id, 0) + 1
        except Exception as e:
            continue

    # 计算频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        # 获取主ID用于匹配统计数据
        main_id = stats.get('main_id', name)
        total_rounds = total_rounds_played.get(main_id, 0)
        if total_rounds <= 100:
            continue

        haneman_count = haneman_counts.get(main_id, 0)  # 使用主ID查询
        haneman_rate = (haneman_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,
            'haneman_count': haneman_count,
            'total_rounds': total_rounds,
            'haneman_rate': haneman_rate
        })

    leaderboard_data.sort(key=lambda x: x['haneman_rate'], reverse=True)

    if lang == 'zh':
        title = '跳满以上手牌频率'
        header_count = '跳满以上次数'
    else:
        title = 'Haneman+ Hand Rate'
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
    # 加载别名映射
    alias_map = load_player_aliases()

    # 统计每个玩家的倍满以上手牌次数和总小局数（使用主ID）
    baiman_counts = {}
    total_rounds_played = {}

    # 遍历所有牌谱文件统计倍满以上手牌和小局数
    for filepath in sorted_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取玩家列表并归一化为主ID
            raw_names = data.get('name', [])
            main_ids = [normalize_player_name(name, alias_map) for name in raw_names]

            # 初始化这些玩家的计数器（使用主ID）
            for main_id in main_ids:
                if main_id not in total_rounds_played:
                    total_rounds_played[main_id] = 0
                if main_id not in baiman_counts:
                    baiman_counts[main_id] = 0

            for round_data in data.get('log', []):
                if not isinstance(round_data, list) or len(round_data) < 3:
                    continue

                # 每个小局，所有参与玩家的小局数都+1（使用主ID）
                for main_id in main_ids:
                    total_rounds_played[main_id] = total_rounds_played.get(main_id, 0) + 1

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
                            # 使用主ID统计
                            winner_main_id = main_ids[winner_seat] if winner_seat < len(main_ids) else None
                            if winner_main_id:
                                baiman_counts[winner_main_id] = baiman_counts.get(winner_main_id, 0) + 1
        except Exception as e:
            continue

    # 计算每个人和倍满以上手牌的频率
    leaderboard_data = []
    for name, stats in stats_dict.items():
        # 获取主ID用于匹配统计数据
        main_id = stats.get('main_id', name)
        total_rounds = total_rounds_played.get(main_id, 0)
        if total_rounds <= 100:
            continue

        # 获取倍满以上手牌次数（使用主ID查询）
        baiman_count = baiman_counts.get(main_id, 0)
        baiman_rate = (baiman_count / total_rounds) * 100 if total_rounds > 0 else 0

        leaderboard_data.append({
            'name': name,  # 显示名称（带括号的完整格式）
            'baiman_count': baiman_count,
            'total_rounds': total_rounds,
            'baiman_rate': baiman_rate
        })

    leaderboard_data.sort(key=lambda x: x['baiman_rate'], reverse=True)

    if lang == 'zh':
        title = '倍满以上手牌频率'
        header_count = '倍满以上次数'
    else:
        title = 'Baiman+ Hand Rate'
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


