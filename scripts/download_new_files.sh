#!/bin/bash
# 从 Firebase Storage 下载新的游戏日志文件

set -e

PROJECT_ID="santi-league"
BUCKET_NAME="santi-league.firebasestorage.app"

echo "=========================================="
echo "下载新文件从 Firebase Storage"
echo "=========================================="

# 检查 Service Account 认证
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "使用 Service Account 认证..."
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
    gcloud config set project santi-league
else
    echo "警告：未找到 Service Account 凭证"
fi

# 确保目录存在
mkdir -p game-logs/m-league
mkdir -p game-logs/ema
mkdir -p game-logs/sanma

# 使用 gsutil 或 Firebase CLI 下载文件
# 检查是否安装了 gsutil
if command -v gsutil &> /dev/null; then
    echo "使用 gsutil 下载文件..."

    # 同步 M-League 文件
    echo "同步 M-League 文件..."
    gsutil -m rsync -r "gs://${BUCKET_NAME}/game-logs/m-league" game-logs/m-league/ || true

    # 同步 EMA 文件
    echo "同步 EMA 文件..."
    gsutil -m rsync -r "gs://${BUCKET_NAME}/game-logs/ema" game-logs/ema/ || true

    # 同步 Sanma 文件
    echo "同步 Sanma 文件..."
    gsutil -m rsync -r "gs://${BUCKET_NAME}/game-logs/sanma" game-logs/sanma/ || true

else
    echo "gsutil 未安装，尝试使用 Python 脚本..."

    # 使用 Python 脚本下载（备用方案）
    if [ -f "scripts/download_from_storage.py" ]; then
        python3 scripts/download_from_storage.py
    else
        echo "错误：无法找到下载工具"
        exit 1
    fi
fi

# 统计下载的文件数量
total_files=$(find game-logs -name "*.json" -type f 2>/dev/null | wc -l)
echo ""
echo "下载完成！共 ${total_files} 个文件"
echo "=========================================="
