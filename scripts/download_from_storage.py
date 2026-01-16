#!/usr/bin/env python3
"""
从 Firebase Storage 下载游戏日志文件
使用 Firebase Admin SDK
"""

import os
import sys
import json
from pathlib import Path

try:
    from google.cloud import storage
except ImportError:
    print("错误：需要安装 google-cloud-storage")
    print("运行: pip install google-cloud-storage")
    sys.exit(1)

PROJECT_ID = "santi-league"
BUCKET_NAME = "santi-league.firebasestorage.app"
LOCAL_BASE_DIR = "game-logs"

def download_files():
    """从 Firebase Storage 下载所有游戏日志文件"""

    # 初始化 Storage 客户端
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)

    # 列出所有 game-logs/ 下的文件
    blobs = bucket.list_blobs(prefix="game-logs/")

    downloaded_count = 0
    skipped_count = 0

    for blob in blobs:
        # 跳过目录标记
        if blob.name.endswith('/'):
            continue

        # 只处理 JSON 文件
        if not blob.name.endswith('.json'):
            continue

        # 构建本地路径
        # blob.name 格式: game-logs/m-league/timestamp_file.json
        local_path = Path(blob.name)
        local_file = Path(local_path)

        # 创建目录
        local_file.parent.mkdir(parents=True, exist_ok=True)

        # 检查文件是否已存在
        if local_file.exists():
            # 比较大小，如果相同则跳过
            if local_file.stat().st_size == blob.size:
                skipped_count += 1
                continue

        # 下载文件
        print(f"下载: {blob.name}")
        blob.download_to_filename(str(local_file))
        downloaded_count += 1

    print(f"\n下载完成:")
    print(f"  新下载: {downloaded_count} 个文件")
    print(f"  已跳过: {skipped_count} 个文件")

    return downloaded_count

if __name__ == "__main__":
    try:
        download_files()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
