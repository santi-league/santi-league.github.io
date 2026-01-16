#!/usr/bin/env python3
"""
标记已处理的牌谱文件
在 generate_website.sh 运行完成后，将 Firestore 中的牌谱记录标记为已处理
"""

import os
import sys
import json
from pathlib import Path

try:
    from google.cloud import firestore
    from google.oauth2 import service_account
except ImportError:
    print("错误: 请先安装 google-cloud-firestore")
    print("运行: pip install google-cloud-firestore")
    sys.exit(1)


def init_firestore():
    """初始化 Firestore 客户端"""
    # 从环境变量获取凭证
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        # GitHub Actions 环境
        db = firestore.Client()
    else:
        # 本地开发环境 - 需要设置环境变量
        print("提示: 请设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
        print("export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json")
        sys.exit(1)

    return db


def get_local_game_files():
    """获取本地所有牌谱文件"""
    game_logs_dir = Path('game-logs')

    if not game_logs_dir.exists():
        print(f"警告: game-logs 目录不存在")
        return []

    json_files = []
    for league_dir in ['m-league', 'ema', 'sanma']:
        league_path = game_logs_dir / league_dir
        if league_path.exists():
            for json_file in league_path.rglob('*.json'):
                # 获取相对于 game-logs 的路径
                rel_path = str(json_file.relative_to(game_logs_dir))
                json_files.append({
                    'fileName': json_file.name,
                    'storagePath': rel_path,
                    'league': league_dir
                })

    return json_files


def mark_processed_in_firestore(db, local_files):
    """在 Firestore 中标记已处理的文件"""
    marked_count = 0
    skipped_count = 0

    for file_info in local_files:
        try:
            # 查询 Firestore 中匹配的文档
            # 优先通过 storagePath 查找
            query = db.collection('game-logs').where('fileName', '==', file_info['fileName']).where('league', '==', file_info['league']).where('processed', '==', False)

            docs = query.stream()
            updated = False

            for doc in docs:
                # 更新为已处理
                doc.reference.update({
                    'processed': True,
                    'processedAt': firestore.SERVER_TIMESTAMP
                })
                marked_count += 1
                updated = True
                print(f"✓ 已标记: {file_info['fileName']} ({file_info['league']})")

            if not updated:
                skipped_count += 1

        except Exception as e:
            print(f"✗ 错误处理 {file_info['fileName']}: {e}")
            continue

    return marked_count, skipped_count


def main():
    """主函数"""
    print("========================================")
    print("标记已处理的牌谱文件")
    print("========================================")

    # 初始化 Firestore
    try:
        db = init_firestore()
        print("✓ Firestore 连接成功")
    except Exception as e:
        print(f"✗ Firestore 连接失败: {e}")
        sys.exit(1)

    # 获取本地文件列表
    local_files = get_local_game_files()
    print(f"\n找到 {len(local_files)} 个本地牌谱文件")

    if len(local_files) == 0:
        print("没有文件需要处理")
        return

    # 标记为已处理
    print("\n开始标记已处理文件...")
    marked, skipped = mark_processed_in_firestore(db, local_files)

    print("\n========================================")
    print(f"处理完成:")
    print(f"  - 已标记: {marked} 个文件")
    print(f"  - 已跳过: {skipped} 个文件")
    print("========================================")


if __name__ == '__main__':
    main()
