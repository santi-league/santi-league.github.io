#!/bin/bash
# 生成网站统计页面的启动脚本

cd "$(dirname "$0")"
python3 src/generate_website.py "$@"
