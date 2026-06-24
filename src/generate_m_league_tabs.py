#!/usr/bin/env python3
"""
生成带标签页的M-League统计页面
这个脚本使用新的模板系统生成M-League页面
"""

def generate_ranking_content(stats_data, t, league_avg):
    """
    生成总排名内容 - 支持按R值和总得分排名切换

    将玩家分为两组：
    1. 10个半庄以上：按R值或总得分从高到低排列
    2. 10个半庄以下：按半庄数排列
    """
    import json

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

    # 构建玩家数据JSON（供JavaScript使用）
    players_json_data = []
    for player_name, data in qualified_players:
        players_json_data.append({
            'name': player_name,
            'tenhou_r': data['tenhou_r'],
            'total_score': data['total_score'],
            'games': data['games'],
            'total_rounds': data['total_rounds'],
            'avg_rank': data['avg_rank'],
            'rank_1_rate': data['rank_1_rate'],
            'win_rate': data['win_rate']
        })

    players_json = json.dumps(players_json_data, ensure_ascii=False)

    # 生成HTML
    html = f"""
    <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <h2 style="color: #667eea; margin: 0;">{t.get('qualified_players', '正式排名')} (≥10{t.get('games', '半庄')})</h2>
        <div style="display: flex; align-items: center; gap: 10px;">
            <label style="font-weight: 600; color: #555;">{t.get('sort_by', '排序方式')}:</label>
            <select id="rankingMode" style="padding: 8px 16px; border: 2px solid #667eea; border-radius: 4px; font-size: 14px; cursor: pointer; background: white;">
                <option value="rating">{t.get('by_rating', '按Rating排名')}</option>
                <option value="score">{t.get('by_total_score', '按总得分排名')}</option>
            </select>
        </div>
    </div>

    <div style="margin-bottom: 40px;">
        <div style="overflow-x: auto;">
            <table id="rankingTable" style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background: #667eea; color: white;">
                        <th style="padding: 12px; text-align: center;">{t.get('rank', '排名')}</th>
                        <th style="padding: 12px;">{t['player']}</th>
                        <th id="sortColumn" style="padding: 12px; text-align: center;">{t['r_value']}</th>
                        <th style="padding: 12px; text-align: center;">{t['games']}</th>
                        <th style="padding: 12px; text-align: center;">{t['rounds']}</th>
                        <th style="padding: 12px; text-align: center;">{t['avg_rank']}</th>
                        <th style="padding: 12px; text-align: center;">{t.get('rank_1_rate', '一位率')}</th>
                        <th style="padding: 12px; text-align: center;">{t.get('win_rate', '和牌率')}</th>
                    </tr>
                </thead>
                <tbody id="rankingTableBody">
                </tbody>
            </table>
        </div>
    </div>
    """

    # 未达标玩家
    if unqualified_players:
        # 按半庄数降序排序
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
                            <th style="padding: 12px; text-align: center;">{t['r_value']}</th>
                            <th style="padding: 12px; text-align: center;">{t['total_score']}</th>
                            <th style="padding: 12px; text-align: center;">{t['avg_rank']}</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for player_name, data in unqualified_players:
            total_score_display = f"{data['total_score']:+}" if data['total_score'] != 0 else "0"
            html += f"""
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 12px; font-weight: 600;">{player_name}</td>
                            <td style="padding: 12px; text-align: center; font-weight: bold;">{data['games']}</td>
                            <td style="padding: 12px; text-align: center;">{data['total_rounds']}</td>
                            <td style="padding: 12px; text-align: center;">{data['tenhou_r']:.2f}</td>
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

    # 添加JavaScript代码
    html += f"""
    <script>
        (function() {{
            const playersData = {players_json};
            const rankEmojis = ['🥇', '🥈', '🥉'];

            function renderRanking(mode) {{
                const tbody = document.getElementById('rankingTableBody');
                const sortColumn = document.getElementById('sortColumn');

                // 更新表头
                if (mode === 'rating') {{
                    sortColumn.textContent = '{t['r_value']}';
                }} else {{
                    sortColumn.textContent = '{t['total_score']}';
                }}

                // 排序数据
                const sorted = [...playersData].sort((a, b) => {{
                    if (mode === 'rating') {{
                        return b.tenhou_r - a.tenhou_r;
                    }} else {{
                        return b.total_score - a.total_score;
                    }}
                }});

                // 渲染表格
                tbody.innerHTML = '';
                sorted.forEach((player, idx) => {{
                    const rank = idx + 1;
                    const rankEmoji = rank <= 3 ? rankEmojis[rank - 1] + ' ' : '';
                    const rowBg = idx % 2 === 0 ? 'white' : '#f8f9fa';

                    const sortValue = mode === 'rating'
                        ? player.tenhou_r.toFixed(2)
                        : (player.total_score >= 0 ? '+' : '') + player.total_score;

                    const sortValueColor = mode === 'rating' ? '#667eea' : (player.total_score >= 0 ? '#28a745' : '#dc3545');

                    const row = document.createElement('tr');
                    row.style.background = rowBg;
                    row.innerHTML = `
                        <td style="padding: 12px; text-align: center; font-weight: bold; font-size: 18px;">${{rankEmoji}}${{rank}}</td>
                        <td style="padding: 12px; font-weight: 600;">${{player.name}}</td>
                        <td style="padding: 12px; text-align: center; color: ${{sortValueColor}}; font-weight: bold;">${{sortValue}}</td>
                        <td style="padding: 12px; text-align: center;">${{player.games}}</td>
                        <td style="padding: 12px; text-align: center;">${{player.total_rounds}}</td>
                        <td style="padding: 12px; text-align: center;">${{player.avg_rank.toFixed(2)}}</td>
                        <td style="padding: 12px; text-align: center;">${{player.rank_1_rate.toFixed(1)}}%</td>
                        <td style="padding: 12px; text-align: center;">${{player.win_rate.toFixed(1)}}%</td>
                    `;
                    tbody.appendChild(row);
                }});
            }}

            // 监听切换事件
            document.getElementById('rankingMode').addEventListener('change', function() {{
                renderRanking(this.value);
            }});

            // 初始渲染（按R值排名）
            renderRanking('rating');
        }})();
    </script>
    """

    return html


def main():
    """主函数 - 目前仅用于测试"""
    print("M-League标签页生成器已加载")
    print("此模块将被generate_website.py调用")

if __name__ == '__main__':
    main()
