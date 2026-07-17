#!/bin/bash
# 批量转换 downloaded_paipu 中的牌谱到 game-logs
# 支持子文件夹分类转换 (m-league, ema)

set -e

INPUT_DIR="downloaded_paipu"
OUTPUT_DIR="game-logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查输入目录是否存在
if [ ! -d "$INPUT_DIR" ]; then
    echo -e "${RED}错误: 找不到 $INPUT_DIR 目录${NC}"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "批量转换牌谱"
echo "=========================================="
echo ""

total_success=0
total_failed=0

# 定义要处理的子文件夹
SUBDIRS=("m-league" "ema")

for subdir in "${SUBDIRS[@]}"; do
    input_subdir="$INPUT_DIR/$subdir"
    output_subdir="$OUTPUT_DIR/$subdir"

    # 检查子文件夹是否存在
    if [ ! -d "$input_subdir" ]; then
        echo -e "${YELLOW}跳过: $input_subdir 不存在${NC}"
        echo ""
        continue
    fi

    # 统计该子文件夹中的文件数
    file_count=$(ls "$input_subdir"/*.json 2>/dev/null | wc -l | xargs)

    if [ "$file_count" -eq 0 ]; then
        echo -e "${YELLOW}跳过: $input_subdir 没有 JSON 文件${NC}"
        echo ""
        continue
    fi

    echo -e "${BLUE}[$subdir] 转换牌谱...${NC}"
    echo "输入目录: $input_subdir"
    echo "输出目录: $output_subdir"
    echo "文件数量: $file_count"
    echo ""

    # 创建输出子目录
    mkdir -p "$output_subdir"

    # 调用 Python 脚本进行批量转换，根据子文件夹名称传递规则参数
    if python3 src/convert_rico_to_tenhou.py "$input_subdir" "$output_subdir" --rule "$subdir"; then
        echo -e "${GREEN}✓ $subdir 转换完成${NC}"
        total_success=$((total_success + file_count))
    else
        echo -e "${RED}✗ $subdir 转换失败${NC}"
        total_failed=$((total_failed + file_count))
    fi
    echo ""
done

# 处理根目录中的文件（兼容旧的工作流程）
root_files=$(ls "$INPUT_DIR"/*.json 2>/dev/null | wc -l | xargs)

if [ "$root_files" -gt 0 ]; then
    echo -e "${BLUE}[根目录] 转换牌谱...${NC}"
    echo "输入目录: $INPUT_DIR (根目录)"
    echo "输出目录: $OUTPUT_DIR (根目录)"
    echo "文件数量: $root_files"
    echo ""
    echo -e "${YELLOW}提示: 建议将这些文件移动到 $INPUT_DIR/m-league 或 $INPUT_DIR/ema${NC}"
    echo ""

    # 转换根目录的文件到 game-logs 根目录
    if python3 src/convert_rico_to_tenhou.py "$INPUT_DIR" "$OUTPUT_DIR"; then
        echo -e "${GREEN}✓ 根目录转换完成${NC}"
        total_success=$((total_success + root_files))
    else
        echo -e "${RED}✗ 根目录转换失败${NC}"
        total_failed=$((total_failed + root_files))
    fi
    echo ""
fi

echo "=========================================="
if [ $total_failed -eq 0 ]; then
    echo -e "${GREEN}✓ 全部转换完成${NC}"
    echo "成功: $total_success 个文件"
else
    echo -e "${YELLOW}转换完成（部分失败）${NC}"
    echo "成功: $total_success 个文件"
    echo "失败: $total_failed 个文件"
fi
echo "=========================================="

exit $([ $total_failed -eq 0 ] && echo 0 || echo 1)
