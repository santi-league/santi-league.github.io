#!/usr/bin/env python3
"""
模板渲染器 - 用于加载和渲染HTML模板
"""
import json
from pathlib import Path

def load_template(template_name):
    """加载模板文件"""
    template_path = Path(__file__).parent.parent / 'templates' / template_name
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

def render_m_league_tabs(
    lang='zh',
    title='',
    date_info='',
    other_stats_page='',
    current_index='',
    switch_lang_text='',
    back_home_text='',
    tab_texts={},
    recent_content='',
    honor_content='',
    ranking_content='',
    player_options='',
    players_data={},
    select_player_label='',
    choose_player='',
    select_player_prompt='',
    additional_styles='',
    additional_scripts=''
):
    """
    渲染M-League标签页模板

    Args:
        lang: 语言代码 (zh/en)
        title: 页面标题
        date_info: 日期信息HTML
        other_stats_page: 语言切换链接
        current_index: 返回首页链接
        switch_lang_text: 切换语言文本
        back_home_text: 返回首页文本
        tab_texts: 标签页文本字典 {recent, honor, ranking, players}
        recent_content: 最近牌谱内容HTML
        honor_content: 荣誉牌谱内容HTML
        ranking_content: 总排名内容HTML
        player_options: 玩家选择器选项HTML
        players_data: 玩家详情数据字典
        select_player_label: "选择玩家"标签文本
        choose_player: "请选择"文本
        select_player_prompt: "请选择玩家查看详细数据"提示文本
        additional_styles: 额外的CSS样式
        additional_scripts: 额外的JavaScript代码
    """
    template = load_template('m_league_tabs.html')

    lang_code = 'zh-CN' if lang == 'zh' else 'en'

    # 将玩家数据转换为JSON
    players_data_json = json.dumps(players_data, ensure_ascii=False)

    # 渲染模板
    html = template.format(
        lang_code=lang_code,
        title=title,
        date_info=date_info,
        other_stats_page=other_stats_page,
        current_index=current_index,
        switch_lang_text=switch_lang_text,
        back_home_text=back_home_text,
        tab_recent=tab_texts.get('recent', '最近牌谱'),
        tab_honor=tab_texts.get('honor', '荣誉牌谱'),
        tab_ranking=tab_texts.get('ranking', '总排名'),
        tab_players=tab_texts.get('players', '玩家详情'),
        recent_content=recent_content,
        honor_content=honor_content,
        ranking_content=ranking_content,
        player_options=player_options,
        players_data_json=players_data_json,
        select_player_label=select_player_label,
        choose_player=choose_player,
        select_player_prompt=select_player_prompt,
        additional_styles=additional_styles,
        additional_scripts=additional_scripts
    )

    return html
