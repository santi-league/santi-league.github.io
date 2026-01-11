# -*- coding: utf-8 -*-
"""
页面生成器模块 - 包含各种页面的生成逻辑
"""

import sys
import os
import re
import json
import html as html_module

# 添加父目录到路径以便导入其他模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.translations import TRANSLATIONS, YAKU_TRANSLATION, YAKU_TRANSLATION_EN
from templates.template_loader import load_html_template, load_css


def generate_index_page(lang='zh'):
    """
    生成首页

    Args:
        lang: 语言 ('zh' 或 'en')

    Returns:
        str: 渲染后的HTML
    """
    t = TRANSLATIONS[lang]
    lang_code = 'zh-CN' if lang == 'zh' else 'en'
    other_lang = 'en' if lang == 'zh' else 'zh'
    other_index = 'index-en.html' if lang == 'zh' else 'index.html'

    html_template = load_html_template('index.html')
    css_content = load_css('index.css')

    return html_template.format(
        lang_code=lang_code,
        title=t['title'],
        subtitle=t['subtitle'],
        other_index=other_index,
        switch_lang=t['switch_to_' + other_lang],
        m_league_link='m-league-en.html' if lang == 'en' else 'm-league.html',
        m_league=t['m_league'],
        view_m_league=t['view_m_league'],
        ema_link='ema-en.html' if lang == 'en' else 'ema.html',
        ema=t['ema'],
        view_ema=t['view_ema'],
        sanma_honor_link='sanma-honor-en.html' if lang == 'en' else 'sanma-honor.html',
        sanma_honor=t['sanma_honor'],
        view_sanma_honor=t['view_sanma_honor'],
        generated_by=t['generated_by'],
        css_content=css_content
    )


def generate_ema_page(lang='zh'):
    """
    生成EMA页面

    Args:
        lang: 语言 ('zh' 或 'en')

    Returns:
        str: 渲染后的HTML
    """
    t = TRANSLATIONS[lang]
    lang_code = 'zh-CN' if lang == 'zh' else 'en'
    other_page = 'ema-en.html' if lang == 'zh' else 'ema.html'
    home_page = 'index.html' if lang == 'zh' else 'index-en.html'
    other_lang = 'en' if lang == 'zh' else 'zh'

    html_template = load_html_template('ema.html')
    css_content = load_css('ema.css')

    return html_template.format(
        lang_code=lang_code,
        other_page=other_page,
        switch_lang=t['switch_to_' + other_lang],
        coming_soon=t['coming_soon'],
        home_page=home_page,
        back_home=t['back_home'],
        css_content=css_content
    )


def generate_sanma_honor_page(yakuman_games, lang='zh'):
    """
    生成三麻荣誉牌谱页面

    Args:
        yakuman_games: 役满游戏列表
        lang: 语言 ('zh' 或 'en')

    Returns:
        str: 渲染后的HTML
    """
    t = TRANSLATIONS[lang]
    lang_code = 'zh-CN' if lang == 'zh' else 'en'
    other_lang = 'en' if lang == 'zh' else 'zh'
    other_page = 'sanma-honor-en.html' if lang == 'zh' else 'sanma-honor.html'
    home_page = 'index.html' if lang == 'zh' else 'index-en.html'

    title = "三麻荣誉牌谱" if lang == 'zh' else "Sanma Honor Games"

    # 生成荣誉牌谱卡片
    honor_cards = ""
    if yakuman_games and len(yakuman_games) > 0:
        for game in yakuman_games:
            # 检查是否是累计役满
            fan_info = game.get('fan_info', '')
            is_kazoe = 'Kazoe Yakuman' in str(fan_info) or '数え役満' in str(fan_info)

            # 翻译役种
            yaku_list = game.get('yaku_list', [])
            if lang == 'zh':
                # 翻译并替换Kita为拔北，保留番数
                translated_yaku_list = []
                for y in yaku_list:
                    yaku_str = str(y)
                    # 提取番数（如果有）
                    fan_match = re.search(r'\((\d+)飜\)', yaku_str)
                    fan_num = fan_match.group(1) if fan_match else None

                    # 获取役种名称（去掉番数部分）
                    yaku_name = yaku_str.split('(')[0]

                    if 'Kita' in yaku_str:
                        translated_name = '拔北'
                    else:
                        translated_name = YAKU_TRANSLATION.get(yaku_name, yaku_name)

                    # 添加番数
                    if fan_num:
                        translated_yaku_list.append(f'{translated_name}{fan_num}番')
                    else:
                        translated_yaku_list.append(translated_name)

                # 如果是累计役满，格式化为"累计役满（役种1 役种2 ...）"
                if is_kazoe:
                    yaku_part = ' '.join(translated_yaku_list)  # 用空格连接
                    translated_yaku = f'累计役满（{yaku_part}）'
                else:
                    translated_yaku = ', '.join(translated_yaku_list)
            else:
                # English version - extract fan numbers
                translated_yaku_list = []
                for y in yaku_list:
                    yaku_str = str(y)
                    # Extract fan number (if present)
                    fan_match = re.search(r'\((\d+)飜\)', yaku_str)
                    fan_num = fan_match.group(1) if fan_match else None

                    # Get yaku name (remove fan part)
                    yaku_name = yaku_str.split('(')[0]
                    translated_name = YAKU_TRANSLATION_EN.get(yaku_name, yaku_name)

                    # Add fan number
                    if fan_num:
                        translated_yaku_list.append(f'{translated_name} ({fan_num} han)')
                    else:
                        translated_yaku_list.append(translated_name)

                # English version kazoe yakuman format
                if is_kazoe:
                    yaku_part = ', '.join(translated_yaku_list)
                    translated_yaku = f'Kazoe Yakuman ({yaku_part})'
                else:
                    translated_yaku = ', '.join(translated_yaku_list)

            date_str = game['date'] if lang == 'zh' else game['date_en']
            escaped_url = html_module.escape(game['tenhou_url'], quote=True)

            # 役满类型显示
            yakuman_type_text = "累计役满" if (is_kazoe and lang == 'zh') else ("Kazoe Yakuman" if (is_kazoe and lang == 'en') else "役満")

            honor_cards += f"""
            <div class="honor-card yakuman">
                <div class="honor-type">{yakuman_type_text}</div>
                <div class="honor-info">
                    <div class="honor-date">{date_str}</div>
                    <div class="honor-round">{game['round']}</div>
                    <div class="honor-winner">{game['winner']}</div>
                    <div class="honor-yaku">{translated_yaku}</div>
                </div>
                <a href="{escaped_url}" target="_blank" class="honor-replay-btn">{t.get('view_replay', '查看牌谱')}</a>
            </div>
            """
    else:
        honor_cards = f"<p style='text-align: center; color: #999; padding: 40px;'>{'暂无役满牌谱' if lang == 'zh' else 'No yakuman games yet'}</p>"

    # 创建一个简化的 render_template 函数调用
    html_template = load_html_template('sanma_honor.html')
    css_content = load_css('sanma_honor.css')

    return html_template.format(
        lang_code=lang_code,
        title=title,
        other_page=other_page,
        switch_lang=t['switch_to_' + other_lang],
        home_page=home_page,
        back_home=t['back_home'],
        honor_cards=honor_cards,
        css_content=css_content
    )


def generate_m_league_page(
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
    leaderboard_content='',
    player_options='',
    players_data={},
    select_player_label='',
    choose_player='',
    select_player_prompt=''
):
    """
    生成M-League标签页页面

    Args:
        lang: 语言代码 (zh/en)
        title: 页面标题
        date_info: 日期信息HTML
        other_stats_page: 语言切换链接
        current_index: 返回首页链接
        switch_lang_text: 切换语言文本
        back_home_text: 返回首页文本
        tab_texts: 标签页文本字典 {recent, honor, ranking, leaderboard, players}
        recent_content: 最近牌谱内容HTML
        honor_content: 荣誉牌谱内容HTML
        ranking_content: 总排名内容HTML
        leaderboard_content: 排行榜内容HTML
        player_options: 玩家选择器选项HTML
        players_data: 玩家详情数据字典
        select_player_label: "选择玩家"标签文本
        choose_player: "请选择"文本
        select_player_prompt: "请选择玩家查看详细数据"提示文本

    Returns:
        str: 渲染后的HTML
    """
    # 加载模板和CSS
    html_template = load_html_template('m_league.html')
    css_content = load_css('m_league.css')

    # 语言代码
    lang_code = 'zh-CN' if lang == 'zh' else 'en'

    # 将玩家数据转换为JSON
    players_data_json = json.dumps(players_data, ensure_ascii=False)

    # 渲染模板
    html = html_template.format(
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
        tab_leaderboard=tab_texts.get('leaderboard', '排行榜' if lang == 'zh' else 'Leaderboard'),
        tab_players=tab_texts.get('players', '玩家详情'),
        recent_content=recent_content,
        honor_content=honor_content,
        ranking_content=ranking_content,
        leaderboard_content=leaderboard_content,
        player_options=player_options,
        players_data_json=players_data_json,
        select_player_label=select_player_label,
        choose_player=choose_player,
        select_player_prompt=select_player_prompt,
        css_content=css_content
    )

    return html
