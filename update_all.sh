#!/bin/bash
# 自动下载、转换、整理牌谱并生成网站

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "自动更新牌谱网站"
echo "========================================"
echo ""

# 步骤 1: 下载牌谱
echo -e "${BLUE}[1/4] 下载牌谱...${NC}"
./download_paipu.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 下载失败${NC}"
    exit 1
fi
echo ""

# 步骤 2: 转换格式
echo -e "${BLUE}[2/4] 转换牌谱格式...${NC}"
./convert_paipu.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 转换失败${NC}"
    exit 1
fi
echo ""

# 步骤 3: 整理牌谱
echo -e "${BLUE}[3/4] 整理牌谱文件...${NC}"
python3 src/organize_logs.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 整理失败${NC}"
    exit 1
fi
echo ""

# 步骤 4: 生成网站
echo -e "${BLUE}[4/4] 生成网站...${NC}"
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
