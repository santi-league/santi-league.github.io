// pending-games.js - 显示未处理的牌谱
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { getFirestore, collection, query, where, onSnapshot, orderBy } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js';

// Firebase 配置
const firebaseConfig = {
    apiKey: "AIzaSyASDebG89ESWOtChoVZVA4vH4iPRNMZqGA",
    authDomain: "santi-league.firebaseapp.com",
    projectId: "santi-league",
    storagePath: "santi-league.firebasestorage.app",
    messagingSenderId: "266841538242",
    appId: "1:266841538242:web:91a27bb48c047bec2a055b",
    measurementId: "G-GN3PMKX4GP"
};

// 初始化 Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// 获取当前页面的联赛类型
function getCurrentLeague() {
    const path = window.location.pathname;
    if (path.includes('m-league')) return 'm-league';
    if (path.includes('ema')) return 'ema';
    if (path.includes('sanma')) return 'sanma';
    return 'm-league'; // 默认
}

// 格式化时间戳为显示格式
function formatTimestamp(timestamp) {
    if (!timestamp) return '未知时间';

    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}年${month}月${day}日 ${hours}:${minutes}`;
}

// 加载未处理的牌谱
export function loadPendingGames() {
    const league = getCurrentLeague();
    const tableBody = document.getElementById('gamesTableBody');

    if (!tableBody) {
        console.log('Table body not found, pending games feature disabled');
        return;
    }

    // 创建查询：未处理的牌谱
    const q = query(
        collection(db, 'game-logs'),
        where('league', '==', league),
        where('processed', '==', false),
        orderBy('uploadedAt', 'desc')
    );

    // 实时监听
    onSnapshot(q, (snapshot) => {
        // 移除旧的未处理行
        document.querySelectorAll('.pending-game-row').forEach(row => row.remove());

        // 添加新的未处理行
        snapshot.docs.forEach(doc => {
            const data = doc.data();
            const row = createPendingRow(data);
            // 插入到表格最前面
            tableBody.insertBefore(row, tableBody.firstChild);
        });
    }, (error) => {
        console.error('Error loading pending games:', error);
    });
}

// 创建未处理牌谱的表格行
function createPendingRow(data) {
    const tr = document.createElement('tr');
    tr.className = 'pending-game-row';
    tr.style.backgroundColor = '#fff3cd'; // 浅黄色背景
    tr.style.borderLeft = '4px solid #ffc107'; // 黄色边框

    // 日期时间列
    const dateCell = document.createElement('td');
    dateCell.className = 'game-date';
    dateCell.textContent = formatTimestamp(data.uploadedAt);
    tr.appendChild(dateCell);

    // 桌平均R列
    const avgRCell = document.createElement('td');
    avgRCell.className = 'table-avg-r';
    avgRCell.textContent = '-';
    tr.appendChild(avgRCell);

    // 未处理状态列 - 跨越所有玩家列（4个玩家 x 9列 = 36列）
    const statusCell = document.createElement('td');
    statusCell.colSpan = 36;
    statusCell.style.textAlign = 'center';
    statusCell.style.fontWeight = '600';
    statusCell.style.color = '#856404';
    statusCell.style.fontSize = '16px';
    statusCell.innerHTML = '⏳ 未处理 - 等待系统处理中...';
    tr.appendChild(statusCell);

    return tr;
}

// 页面加载时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadPendingGames);
} else {
    loadPendingGames();
}
