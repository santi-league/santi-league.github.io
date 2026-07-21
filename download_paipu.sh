#!/bin/bash
# 从 links.txt 批量下载雀魂牌谱
# 使用 ricochet.cn API

set -e

# 配置
LINKS_FILE="links.txt"
OUTPUT_DIR="game-logs"
USERNAME="地鼠"
PASSWORD="2n26uexJ4UVSj7h"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 links.txt 是否存在
if [ ! -f "$LINKS_FILE" ]; then
    echo -e "${RED}错误: 找不到 $LINKS_FILE 文件${NC}"
    echo "请创建 $LINKS_FILE 文件，每行一个牌谱链接"
    echo "示例:"
    echo "  https://game.maj-soul.com/1/?paipu=260527-xxx_axxx"
    echo "  https://game.maj-soul.com/1/?paipu=260524-xxx_axxx"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 读取文件内容并处理成数组
# 支持：1) 每行一个链接  2) 没有换行符，所有链接连在一起
file_content=$(cat "$LINKS_FILE")

# 将文件内容按 "雀魂牌譜:" 或 "雀魂牌谱:" 分割，提取所有URL
urls=()
while [[ "$file_content" =~ (https://game\.maj-soul\.com/1/\?paipu=[^雀]*) ]]; do
    url="${BASH_REMATCH[1]}"
    # 移除已匹配的部分
    file_content="${file_content#*$url}"

    # 清理URL末尾可能的多余字符
    url=$(echo "$url" | grep -oE 'https://game\.maj-soul\.com/1/\?paipu=[0-9a-f_-]+')

    if [[ -n "$url" ]]; then
        urls+=("$url")
    fi
done

total_links=${#urls[@]}
current=0
success=0
failed=0

echo "=========================================="
echo "批量下载雀魂牌谱"
echo "=========================================="
echo "链接文件: $LINKS_FILE"
echo "输出目录: $OUTPUT_DIR"
echo "总计链接: $total_links"
echo "=========================================="
echo ""

# 如果没有链接，直接退出
if [ "$total_links" -eq 0 ]; then
    echo -e "${YELLOW}没有需要下载的链接，跳过下载步骤${NC}"
    echo ""
    exit 0
fi

# 使用Python脚本批量下载所有牌谱（只登录一次）
python3 << PYTHON_SCRIPT
from src.download_paipu.rico import RicochetDownloader
import os
import sys

username = '''$USERNAME'''
password = '''$PASSWORD'''
output_dir = '''$OUTPUT_DIR'''

# URL列表
urls = [
$(for url in "${urls[@]}"; do echo "    '''$url''',"; done)
]

# 登录一次
print("正在登录...")
try:
    downloader = RicochetDownloader()
    downloader.login(username, password)
    print("✓ 登录成功")
except Exception as e:
    print(f"✗ 登录失败: {e}")
    sys.exit(1)

# 下载所有牌谱
current = 0
success = 0
failed = 0

for url in urls:
    current += 1

    # 提取UUID
    import re
    match = re.search(r'paipu=(\d{6}-[a-f0-9-]+)', url)
    if not match:
        print(f"[{current}/{len(urls)}] 跳过: 无法解析UUID")
        continue

    uuid = match.group(1)

    # 提取日期
    match2 = re.match(r'(\d{2})(\d{2})(\d{2})-', uuid)
    if not match2:
        print(f"[{current}/{len(urls)}] 跳过: 无法解析日期")
        continue

    temp_file = f"downloaded_paipu/{uuid}.json"

    # 检查是否已存在
    if os.path.exists(temp_file):
        print(f"[{current}/{len(urls)}] 已存在: {uuid}")
        success += 1
        continue

    print(f"[{current}/{len(urls)}] 下载中: {uuid}")

    # 下载
    try:
        os.makedirs("downloaded_paipu", exist_ok=True)

        downloader.download_to_file(url, temp_file)
        print(f"  ✓ 下载成功: {temp_file}")
        success += 1
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        failed += 1

    # 避免请求过快
    import time
    time.sleep(0.5)
    print()

# 关闭连接
downloader.close()

# 输出统计
print("=" * 42)
print("下载完成")
print("=" * 42)
print(f"总计: {len(urls)}")
print(f"成功: {success}")
print(f"失败: {failed}")
print(f"输出目录: downloaded_paipu")
print("=" * 42)

sys.exit(0 if failed == 0 else 1)
PYTHON_SCRIPT

exit_code=$?

# 根据Python脚本的退出码设置shell退出码
exit $exit_code
