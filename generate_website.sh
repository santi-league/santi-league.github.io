#!/bin/bash
# 生成网站统计页面的启动脚本

cd "$(dirname "$0")"
python3 src/extract_honor_games.py game-logs/m-league -o docs/honor_games.json
python3 src/generate_website.py "$@"
