#!/bin/bash
# 启动印第安麻将实时多人服务器

echo "=========================================="
echo "🎴 印第安麻将服务器启动脚本"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python 3.7+"
    exit 1
fi

echo "✅ Python3 已安装"
echo ""

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 正在安装依赖..."
    pip3 install -r requirements_indian.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
else
    echo "✅ 依赖已安装"
fi

echo ""
echo "=========================================="
echo "🚀 启动服务器..."
echo "=========================================="
echo ""
echo "访问地址: http://localhost:5000"
echo "或者从其他设备访问: http://[你的IP]:5000"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""
echo "=========================================="
echo ""

# 启动服务器
python3 src/indian_server.py
