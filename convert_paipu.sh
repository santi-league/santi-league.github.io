#!/bin/bash
# 批量转换 downloaded_paipu 中的牌谱到 game-logs

set -e

INPUT_DIR="downloaded_paipu"
OUTPUT_DIR="game-logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查输入目录是否存在
if [ ! -d "$INPUT_DIR" ]; then
    echo -e "${RED}错误: 找不到 $INPUT_DIR 目录${NC}"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 统计文件数
total_files=$(ls "$INPUT_DIR"/*.json 2>/dev/null | wc -l | xargs)

if [ "$total_files" -eq 0 ]; then
    echo -e "${YELLOW}没有需要转换的文件${NC}"
    exit 0
fi

echo "=========================================="
echo "批量转换牌谱"
echo "=========================================="
echo "输入目录: $INPUT_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "总计文件: $total_files"
echo "=========================================="
echo ""

# 调用 Python 脚本进行批量转换
python3 src/convert_rico_to_tenhou.py "$INPUT_DIR" "$OUTPUT_DIR"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 转换完成${NC}"
else
    echo ""
    echo -e "${RED}✗ 转换失败${NC}"
fi

exit $exit_code
