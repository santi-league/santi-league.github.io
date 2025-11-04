# 🎴 印第安麻将 - 实时多人游戏服务器

## 📖 简介

这是一个基于 Flask + SocketIO 的实时多人 Indian Poker 游戏系统。所有访问同一服务器的玩家可以实时同步游戏状态。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_indian.txt
```

### 2. 启动服务器

```bash
python3 indian_server.py
```

服务器将在 `http://localhost:5000` 启动。

### 3. 访问游戏

在浏览器中打开 `http://localhost:5000`

如果在服务器上运行，替换 `localhost` 为服务器IP地址。

## 🎮 游戏流程

### 阶段 1: 玩家加入
1. 每个玩家打开网页
2. 输入自己的姓名并点击"确定"
3. 等待其他玩家加入（最多4人）

### 阶段 2: 角色选择
1. 每个玩家点击"选择我的角色"
2. 选择自己的位置（1-4号位）
3. 等待所有玩家都选择完角色

### 阶段 3: 开始游戏
1. 当4位玩家都选择完角色后，自动显示"选择局数"选项
2. 任意玩家选择局数并点击"开始游戏"
3. 所有玩家同时看到游戏开始

### 阶段 4: 查看卡片
- 每个玩家可以看到其他3位玩家的NG卡片
- 自己的卡片显示为 "???"

### 阶段 5: 点数追踪
1. 所有玩家共享同一个点数记录
2. 任意玩家可以输入点数变动
3. 点数变动总和必须为 0 才能应用
4. 应用后，所有玩家的屏幕实时同步更新

## 🔧 技术架构

### 后端
- **Flask**: Web 服务器框架
- **Flask-SocketIO**: WebSocket 实时通信
- **Python**: 服务端逻辑

### 前端
- **Socket.IO Client**: WebSocket 客户端
- **原生 JavaScript**: 前端交互
- **HTML/CSS**: 界面设计

### 实时同步事件

| 事件名 | 方向 | 说明 |
|--------|------|------|
| `connect` | Client → Server | 客户端连接 |
| `join_game` | Client → Server | 玩家加入游戏 |
| `select_role` | Client → Server | 玩家选择角色 |
| `start_round` | Client → Server | 开始某一局 |
| `update_scores` | Client → Server | 更新分数 |
| `players_update` | Server → All Clients | 广播玩家列表更新 |
| `ready_to_start` | Server → All Clients | 通知可以开始游戏 |
| `game_started` | Server → All Clients | 广播游戏开始 |
| `scores_update` | Server → All Clients | 广播分数更新 |

## 📊 游戏状态管理

服务器维护全局游戏状态：

```python
game_state = {
    'players': [],        # 玩家列表
    'game_started': False,# 游戏是否开始
    'current_round': None,# 当前局数
    'cards': {},          # 8局卡片数据
    'scores': {},         # 玩家分数
    'field_pot': 0,       # 场供
}
```

## 🎴 卡片池

```python
CARD_POOL = [
    立直 (x2), 役牌 (x2), 默听 (x2), 附露 (x2),
    平和 (x1), 断幺 (x1), 奇数番 (x1), 偶数番 (x1),
    自摸 (x1), 荣 (x1), 跳满 (x1), 倍满 (x1)
]
```

共16张卡片，每局为4位玩家各分配1张。

## 🌐 服务器部署

### 本地测试
```bash
python3 indian_server.py
```

### 局域网访问
1. 找到服务器IP地址（例如：`192.168.1.100`）
2. 确保防火墙允许端口 5000
3. 其他设备访问 `http://192.168.1.100:5000`

### 云服务器部署
1. 上传文件到服务器
2. 安装依赖
3. 配置防火墙规则（开放端口 5000）
4. 使用 `gunicorn` 或 `supervisor` 保持服务运行

```bash
# 使用 gunicorn (生产环境推荐)
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 indian_server:app
```

## 🔒 注意事项

1. **安全性**: 当前版本没有身份验证，适合局域网或私密场合使用
2. **并发**: 目前设计为单个游戏房间，所有连接的客户端共享同一个游戏状态
3. **断线重连**: 如果玩家断线，需要刷新页面重新加入

## 🐛 常见问题

### Q: 端口 5000 被占用
**A**: 修改 `indian_server.py` 最后一行的端口号：
```python
socketio.run(app, host='0.0.0.0', port=8080, debug=True)
```

### Q: 无法从其他设备访问
**A**:
1. 检查防火墙设置
2. 确认服务器IP地址正确
3. 使用 `0.0.0.0` 而不是 `localhost` 作为 host

### Q: 卡片没有随机
**A**: 每次有4个玩家都选择完角色后，服务器会自动生成新的8局卡片数据

## 📝 更新日志

### v1.0.0 (2025-01-04)
- ✅ 实时多人游戏
- ✅ 玩家加入和角色选择
- ✅ 自动发牌系统
- ✅ 实时点数同步
- ✅ Indian 模式（看不到自己的卡片）

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！
