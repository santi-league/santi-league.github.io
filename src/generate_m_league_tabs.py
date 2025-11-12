#!/usr/bin/env python3
"""
生成带标签页的M-League统计页面
这个脚本使用新的模板系统生成M-League页面
"""

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


def main():
    """主函数 - 目前仅用于测试"""
    print("M-League标签页生成器已加载")
    print("此模块将被generate_website.py调用")

if __name__ == '__main__':
    main()
