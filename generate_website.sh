#!/bin/bash
# 生成网站统计页面的启动脚本

cd "$(dirname "$0")"

# 第一步：整理牌谱文件，按日期归档到子文件夹
echo "=========================================="
echo "步骤 1/3: 整理牌谱文件"
echo "=========================================="
python3 src/organize_logs.py
if [ $? -ne 0 ]; then
    echo "❌ 牌谱整理失败"
    exit 1
fi
echo ""

# 第二步：提取荣誉牌谱
echo "=========================================="
echo "步骤 2/3: 提取荣誉牌谱"
echo "=========================================="
python3 src/extract_honor_games.py game-logs/m-league -o docs/honor_games.json
if [ $? -ne 0 ]; then
    echo "❌ 荣誉牌谱提取失败"
    exit 1
fi
echo ""

# 第三步：生成网站
echo "=========================================="
echo "步骤 3/3: 生成网站页面"
echo "=========================================="
python3 src/generate_website.py "$@"
