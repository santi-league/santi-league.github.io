#!/usr/bin/env python3
"""
Indian Poker 实时多人服务器
使用 Flask + SocketIO 实现实时同步
"""

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import hashlib
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'indian-poker-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 卡片池定义
CARD_POOL = [
    {'name': '立直', 'count': 2},
    {'name': '役牌', 'count': 2},
    {'name': '默听', 'count': 2},
    {'name': '附露', 'count': 2},
    {'name': '平和', 'count': 1},
    {'name': '断幺', 'count': 1},
    {'name': '奇数番', 'count': 1},
    {'name': '偶数番', 'count': 1},
    {'name': '自摸', 'count': 1},
    {'name': '荣', 'count': 1},
    {'name': '跳满', 'count': 1},
    {'name': '倍满', 'count': 1}
]

ROUNDS = ['东1局', '东2局', '东3局', '东4局', '南1局', '南2局', '南3局', '南4局']
INITIAL_SCORE = 100000

# 游戏状态存储
game_state = {
    'players': [],  # [{'name': 'xxx', 'sid': 'xxx', 'role_index': None}, ...]
    'game_started': False,
    'current_round': None,
    'cards': {},  # {'东1局': ['卡1', '卡2', '卡3', '卡4'], ...}
    'scores': {},  # {'玩家名': 分数, ...}
    'field_pot': 0,
    'all_cards_generated': False
}

def build_deck():
    """构建完整的卡牌堆"""
    deck = []
    for card in CARD_POOL:
        for _ in range(card['count']):
            deck.append(card['name'])
    return deck

def generate_all_cards():
    """生成8局的所有卡片"""
    cards = {}
    for round_name in ROUNDS:
        deck = build_deck()
        random.shuffle(deck)
        cards[round_name] = [deck.pop() for _ in range(4)]
    return cards

def get_game_hash():
    """生成游戏唯一标识"""
    data = {
        'players': [p['name'] for p in game_state['players']],
        'cards': game_state['cards']
    }
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()[:8]

@app.route('/')
def index():
    """主页面"""
    html_path = Path(__file__).parent / 'docs' / 'indian_realtime.html'

    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <h1>错误</h1>
        <p>找不到 indian_realtime.html 模板文件</p>
        <p>路径: {}</p>
        """.format(html_path)

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f'客户端连接: {request.sid}')
    # 发送当前游戏状态
    emit('game_state_update', {
        'players': game_state['players'],
        'game_started': game_state['game_started'],
        'current_round': game_state['current_round'],
        'scores': game_state['scores'],
        'field_pot': game_state['field_pot']
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    print(f'客户端断开: {request.sid}')
    # 移除该客户端对应的玩家
    for player in game_state['players']:
        if player['sid'] == request.sid:
            game_state['players'].remove(player)
            # 广播玩家列表更新
            socketio.emit('players_update', {
                'players': game_state['players']
            })
            break

@socketio.on('join_game')
def handle_join_game(data):
    """玩家加入游戏"""
    player_name = data.get('name', '').strip()

    if not player_name:
        emit('error', {'message': '请输入姓名'})
        return

    # 检查是否已满4人
    if len(game_state['players']) >= 4:
        emit('error', {'message': '游戏已满4人'})
        return

    # 检查姓名是否重复
    if any(p['name'] == player_name for p in game_state['players']):
        emit('error', {'message': '姓名已被使用'})
        return

    # 添加玩家
    player = {
        'name': player_name,
        'sid': request.sid,
        'role_index': None
    }
    game_state['players'].append(player)

    print(f'玩家加入: {player_name} ({request.sid})')

    # 广播玩家列表更新
    socketio.emit('players_update', {
        'players': game_state['players']
    })

@socketio.on('select_role')
def handle_select_role(data):
    """玩家选择角色"""
    role_index = data.get('role_index')

    # 查找该客户端对应的玩家
    player = next((p for p in game_state['players'] if p['sid'] == request.sid), None)
    if not player:
        emit('error', {'message': '请先输入姓名'})
        return

    # 检查角色是否已被选择
    if any(p['role_index'] == role_index and p['sid'] != request.sid for p in game_state['players']):
        emit('error', {'message': '该角色已被选择'})
        return

    # 设置角色
    player['role_index'] = role_index

    print(f'玩家选择角色: {player["name"]} -> 角色{role_index}')

    # 广播角色选择更新
    socketio.emit('players_update', {
        'players': game_state['players']
    })

    # 检查是否所有玩家都已选择角色
    if len(game_state['players']) == 4 and all(p['role_index'] is not None for p in game_state['players']):
        # 生成卡片
        if not game_state['all_cards_generated']:
            game_state['cards'] = generate_all_cards()
            game_state['all_cards_generated'] = True
            print('已生成8局卡片')

        # 初始化分数
        for player in game_state['players']:
            game_state['scores'][player['name']] = INITIAL_SCORE

        # 通知所有客户端可以开始游戏
        socketio.emit('ready_to_start', {
            'message': '所有玩家已准备完毕，请选择局数开始游戏'
        })

@socketio.on('start_round')
def handle_start_round(data):
    """开始某一局"""
    round_name = data.get('round')

    if round_name not in ROUNDS:
        emit('error', {'message': '无效的局数'})
        return

    game_state['game_started'] = True
    game_state['current_round'] = round_name

    # 按照 role_index 排序玩家
    sorted_players = sorted(game_state['players'], key=lambda p: p['role_index'])

    # 获取该局的卡片
    round_cards = game_state['cards'][round_name]

    print(f'开始游戏: {round_name}')

    # 广播游戏开始
    socketio.emit('game_started', {
        'round': round_name,
        'players': sorted_players,
        'cards': round_cards,
        'scores': game_state['scores'],
        'field_pot': game_state['field_pot'],
        'game_hash': get_game_hash()
    })

@socketio.on('update_scores')
def handle_update_scores(data):
    """更新分数"""
    adjustments = data.get('adjustments', {})

    # 验证总和为0
    total = sum(adjustments.values())
    if total != 0:
        emit('error', {'message': f'点数变动总和必须为0，当前为{total}'})
        return

    # 应用分数变动
    for player_name, adjustment in adjustments.items():
        if player_name == 'field_pot':
            game_state['field_pot'] += adjustment
        elif player_name in game_state['scores']:
            game_state['scores'][player_name] += adjustment

    print(f'分数更新: {adjustments}')

    # 广播分数更新
    socketio.emit('scores_update', {
        'scores': game_state['scores'],
        'field_pot': game_state['field_pot']
    })

@socketio.on('reset_game')
def handle_reset_game():
    """重置游戏"""
    game_state['players'] = []
    game_state['game_started'] = False
    game_state['current_round'] = None
    game_state['cards'] = {}
    game_state['scores'] = {}
    game_state['field_pot'] = 0
    game_state['all_cards_generated'] = False

    print('游戏已重置')

    # 广播重置
    socketio.emit('game_reset', {})

if __name__ == '__main__':
    print('=' * 60)
    print('🎴 Indian Poker 实时多人服务器')
    print('=' * 60)
    print('服务器启动中...')
    print('访问地址: http://localhost:5000')
    print('按 Ctrl+C 停止服务器')
    print('=' * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
