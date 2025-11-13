# -*- coding: utf-8 -*-
"""
模板加载器 - 用于加载HTML模板和CSS文件
"""

import os

# 模板和CSS文件的基础路径
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(TEMPLATE_DIR, 'html')
CSS_DIR = os.path.join(TEMPLATE_DIR, 'css')


def load_html_template(template_name):
    """
    加载HTML模板文件

    Args:
        template_name: 模板文件名 (如 'index.html')

    Returns:
        str: 模板内容
    """
    template_path = os.path.join(HTML_DIR, template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"模板文件不存在: {template_path}")


def load_css(css_name):
    """
    加载CSS文件

    Args:
        css_name: CSS文件名 (如 'index.css')

    Returns:
        str: CSS内容
    """
    css_path = os.path.join(CSS_DIR, css_name)
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"CSS文件不存在: {css_path}")


def render_template(template_name, css_name=None, **kwargs):
    """
    渲染模板

    Args:
        template_name: HTML模板文件名
        css_name: CSS文件名 (可选,如果指定则会加载CSS并注入到模板中)
        **kwargs: 模板变量

    Returns:
        str: 渲染后的HTML
    """
    # 加载HTML模板
    html_template = load_html_template(template_name)

    # 如果指定了CSS文件,加载CSS内容
    if css_name:
        css_content = load_css(css_name)
        kwargs['css_content'] = css_content

    # 渲染模板
    return html_template.format(**kwargs)
