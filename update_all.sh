#!/bin/bash
# 自动下载、转换、整理牌谱并生成网站

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认规则类型
RULE_TYPE=""
RULE_FOLDER=""

# 解析参数
while getopts "me" opt; do
    case $opt in
        m)
            RULE_TYPE="m-league"
            RULE_FOLDER="m-league"
            ;;
        e)
            RULE_TYPE="ema"
            RULE_FOLDER="ema"
            ;;
        \?)
            echo "Usage: $0 [-m|-e]"
            echo "  -m    M-League 规则"
            echo "  -e    EMA 规则"
            exit 1
            ;;
    esac
done

echo ""
echo "========================================"
echo "自动更新牌谱网站"
if [ -n "$RULE_TYPE" ]; then
    echo "规则类型: $RULE_TYPE"
fi
echo "========================================"
echo ""

# 步骤 1: 下载牌谱
echo -e "${BLUE}[1/5] 下载牌谱...${NC}"
./download_paipu.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 下载失败${NC}"
    exit 1
fi
echo ""

# 步骤 1.5: 移动文件到对应的规则文件夹（如果指定了规则）
if [ -n "$RULE_FOLDER" ]; then
    echo -e "${BLUE}[2/5] 整理下载的牌谱到 $RULE_FOLDER 文件夹...${NC}"

    # 创建目标文件夹
    mkdir -p "downloaded_paipu/$RULE_FOLDER"

    # 统计根目录的 JSON 文件数
    file_count=$(ls downloaded_paipu/*.json 2>/dev/null | wc -l | xargs)

    if [ "$file_count" -gt 0 ]; then
        # 移动文件
        mv downloaded_paipu/*.json "downloaded_paipu/$RULE_FOLDER/"
        echo -e "${GREEN}✓ 已移动 $file_count 个文件到 downloaded_paipu/$RULE_FOLDER/${NC}"
    else
        echo -e "${YELLOW}没有需要移动的文件${NC}"
    fi
    echo ""
fi

# 步骤 2: 转换格式
echo -e "${BLUE}[$([ -n "$RULE_FOLDER" ] && echo "3/5" || echo "2/4")] 转换牌谱格式...${NC}"
./convert_paipu.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 转换失败${NC}"
    exit 1
fi
echo ""

# 步骤 3: 整理牌谱
echo -e "${BLUE}[$([ -n "$RULE_FOLDER" ] && echo "4/5" || echo "3/4")] 整理牌谱文件...${NC}"
python3 src/organize_logs.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 整理失败${NC}"
    exit 1
fi
echo ""

# 步骤 4: 生成网站
echo -e "${BLUE}[$([ -n "$RULE_FOLDER" ] && echo "5/5" || echo "4/4")] 生成网站...${NC}"
python3 src/generate_website.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 生成网站失败${NC}"
    exit 1
fi
echo ""

echo "========================================"
echo -e "${GREEN}✓ 全部完成！${NC}"
echo "========================================"
echo ""
echo "提示：如需提交到 git，请运行："
echo "  git add ."
echo "  git commit -m 'Update game logs'"
echo "  git push"
echo ""
