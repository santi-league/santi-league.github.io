# -*- coding: utf-8 -*-
"""
S-League 页面生成器

负责生成所有S-League相关的HTML页面
"""

import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .data_processor import process_season_data, get_all_seasons_summary
from .templates import generate_index_template, generate_season_page_template
from .config import SEASONS


def generate_all_s_league_pages():
    """
    生成所有S-League页面

    包括：
    - S-League主页（赛季选择）
    - 各个赛季的统计页面
    """
    print("\n正在生成 S-League 页面...", file=sys.stderr)

    # 创建输出目录
    output_dir = "docs/s-league"
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成主页（赛季选择页面）
    print("  生成 S-League 主页...", file=sys.stderr)
    seasons_summary = get_all_seasons_summary()

    # 中文主页
    index_html_zh = generate_index_template(seasons_summary, lang='zh')
    with open(f"{output_dir}/index.html", "w", encoding="utf-8") as f:
        f.write(index_html_zh)
    print(f"  ✓ 已生成 {output_dir}/index.html (中文)", file=sys.stderr)

    # 英文主页
    index_html_en = generate_index_template(seasons_summary, lang='en')
    with open(f"{output_dir}/index-en.html", "w", encoding="utf-8") as f:
        f.write(index_html_en)
    print(f"  ✓ 已生成 {output_dir}/index-en.html (英文)", file=sys.stderr)

    # 2. 生成各个赛季的页面
    for season_id, season_info in SEASONS.items():
        if not season_info['enabled']:
            continue

        print(f"  处理 {season_info['name_zh']} 数据...", file=sys.stderr)

        try:
            # 处理赛季数据
            season_data = process_season_data(season_id)

            if season_data['file_count'] == 0:
                print(f"    ⚠ {season_id} 没有数据，跳过", file=sys.stderr)
                continue

            # 生成中文页面
            season_html_zh = generate_season_page_template(season_data, lang='zh')
            with open(f"{output_dir}/{season_id}.html", "w", encoding="utf-8") as f:
                f.write(season_html_zh)
            print(f"  ✓ 已生成 {output_dir}/{season_id}.html (中文, {season_data['file_count']} 个文件)", file=sys.stderr)

            # 生成英文页面
            season_html_en = generate_season_page_template(season_data, lang='en')
            with open(f"{output_dir}/{season_id}-en.html", "w", encoding="utf-8") as f:
                f.write(season_html_en)
            print(f"  ✓ 已生成 {output_dir}/{season_id}-en.html (英文, {season_data['file_count']} 个文件)", file=sys.stderr)

        except Exception as e:
            print(f"  ✗ 生成 {season_id} 页面失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    print("✓ S-League 页面生成完成\n", file=sys.stderr)


def generate_season_page(season_id, lang='zh'):
    """
    生成单个赛季的页面

    参数:
        season_id: 赛季ID
        lang: 语言

    返回:
        str: HTML内容
    """
    season_data = process_season_data(season_id)
    return generate_season_page_template(season_data, lang=lang)


if __name__ == "__main__":
    # 允许直接运行此脚本来生成S-League页面
    generate_all_s_league_pages()
