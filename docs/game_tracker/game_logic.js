// Game State
const WINDS = ['東', '南', '西', '北'];
const INITIAL_POINTS = 25000;
const FU_VALUES = [20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110];

let players = [];
let currentDealer = 0;
let windRound = 0;
let roundNumber = 1;
let honba = 0;
let riichiSticks = 0;
let history = [];

// Current round state
let currentOutcome = null; // 'ron', 'tsumo', 'draw', 'nagashi'
let selectedWinners = []; // Support multiple winners for multi-ron
let selectedLoser = null;
let riichiPlayers = [];
let tenpaiPlayers = []; // For draw - who is tenpai

// Hand selection state
let selectedYaku = [];
let doraCount = 0;
let currentFuIndex = 2; // 30 fu
let isOpenHand = false;

// Yaku definitions
const YAKU_LIST = [
    // 1 han
    { id: 'riichi', name: '立直 Riichi', menzen: 1, open: 0, yakuman: false },
    { id: 'ippatsu', name: '一発 Ippatsu', menzen: 1, open: 0, yakuman: false },
    { id: 'tsumo', name: '門前清自摸和 Tsumo', menzen: 1, open: 0, yakuman: false },
    { id: 'pinfu', name: '平和 Pinfu', menzen: 1, open: 0, yakuman: false },
    { id: 'tanyao', name: '断幺九 Tanyao', menzen: 1, open: 1, yakuman: false },
    { id: 'iipeikou', name: '一盃口 Iipeikou', menzen: 1, open: 0, yakuman: false },
    { id: 'yakuhai1', name: '役牌 Yakuhai', menzen: 1, open: 1, yakuman: false },
    { id: 'yakuhai2', name: '役牌2 Yakuhai x2', menzen: 1, open: 1, yakuman: false },
    { id: 'yakuhai3', name: '役牌3 Yakuhai x3', menzen: 1, open: 1, yakuman: false },
    { id: 'yakuhai4', name: '役牌4 Yakuhai x4', menzen: 1, open: 1, yakuman: false },
    { id: 'haitei', name: '海底摸月 Haitei', menzen: 1, open: 1, yakuman: false },
    { id: 'houtei', name: '河底撈魚 Houtei', menzen: 1, open: 1, yakuman: false },
    { id: 'rinshan', name: '嶺上開花 Rinshan', menzen: 1, open: 1, yakuman: false },
    { id: 'chankan', name: '搶槓 Chankan', menzen: 1, open: 1, yakuman: false },
    // 2 han
    { id: 'double_riichi', name: '両立直 Double Riichi', menzen: 2, open: 0, yakuman: false },
    { id: 'chiitoitsu', name: '七対子 Chiitoitsu', menzen: 2, open: 0, yakuman: false },
    { id: 'sanshoku', name: '三色同順 Sanshoku', menzen: 2, open: 1, yakuman: false },
    { id: 'ittsu', name: '一気通貫 Ittsu', menzen: 2, open: 1, yakuman: false },
    { id: 'toitoi', name: '対々和 Toitoi', menzen: 2, open: 2, yakuman: false },
    { id: 'sanankou', name: '三暗刻 Sanankou', menzen: 2, open: 2, yakuman: false },
    { id: 'sankantsu', name: '三槓子 Sankantsu', menzen: 2, open: 2, yakuman: false },
    { id: 'sanshoku_doukou', name: '三色同刻 Sanshoku Doukou', menzen: 2, open: 2, yakuman: false },
    { id: 'chanta', name: '混全帯幺九 Chanta', menzen: 2, open: 1, yakuman: false },
    { id: 'honroto', name: '混老頭 Honroto', menzen: 2, open: 2, yakuman: false },
    { id: 'shousangen', name: '小三元 Shousangen', menzen: 2, open: 2, yakuman: false },
    // 3 han
    { id: 'ryanpeikou', name: '二盃口 Ryanpeikou', menzen: 3, open: 0, yakuman: false },
    { id: 'honitsu', name: '混一色 Honitsu', menzen: 3, open: 2, yakuman: false },
    { id: 'junchan', name: '純全帯幺九 Junchan', menzen: 3, open: 2, yakuman: false },
    // 6 han
    { id: 'chinitsu', name: '清一色 Chinitsu', menzen: 6, open: 5, yakuman: false },
    // Yakuman
    { id: 'kokushi', name: '国士無双 Kokushi', menzen: 13, open: 0, yakuman: true },
    { id: 'suuankou', name: '四暗刻 Suuankou', menzen: 13, open: 0, yakuman: true },
    { id: 'daisangen', name: '大三元 Daisangen', menzen: 13, open: 13, yakuman: true },
    { id: 'shousuushii', name: '小四喜 Shousuushii', menzen: 13, open: 13, yakuman: true },
    { id: 'daisuushii', name: '大四喜 Daisuushii', menzen: 26, open: 26, yakuman: true },
    { id: 'tsuuiisou', name: '字一色 Tsuuiisou', menzen: 13, open: 13, yakuman: true },
    { id: 'chinroto', name: '清老頭 Chinroto', menzen: 13, open: 13, yakuman: true },
    { id: 'ryuuiisou', name: '緑一色 Ryuuiisou', menzen: 13, open: 13, yakuman: true },
    { id: 'chuurenpoutou', name: '九蓮宝燈 Chuurenpoutou', menzen: 13, open: 0, yakuman: true },
    { id: 'suukantsu', name: '四槓子 Suukantsu', menzen: 13, open: 13, yakuman: true },
    { id: 'tenhou', name: '天和 Tenhou', menzen: 13, open: 0, yakuman: true },
    { id: 'chiihou', name: '地和 Chiihou', menzen: 13, open: 0, yakuman: true },
];

// Initialize game
function init() {
    const saved = localStorage.getItem('tyr_session');
    if (saved) {
        const data = JSON.parse(saved);
        if (confirm('检测到未完成的对局，是否继续？')) {
            players = data.players;
            currentDealer = data.currentDealer;
            windRound = data.windRound;
            roundNumber = data.roundNumber;
            honba = data.honba;
            riichiSticks = data.riichiSticks;
            history = data.history || [];
            updateMainDisplay();
            return;
        }
    }

    const names = prompt('输入四位玩家名字（用逗号分隔）', '東家,南家,西家,北家');
    if (!names) {
        init();
        return;
    }

    const nameList = names.split(/[,，、]/);
    if (nameList.length !== 4) {
        alert('请输入4位玩家！');
        init();
        return;
    }

    players = nameList.map((name, idx) => ({
        name: name.trim(),
        points: INITIAL_POINTS,
        wind: idx,
        isDealer: idx === 0
    }));

    updateMainDisplay();
    saveState();
}

function updateMainDisplay(showRoleButtons = false) {
    players.forEach((player, idx) => {
        const elem = document.getElementById(`player${idx}`);
        const windClass = ['wind-east', 'wind-south', 'wind-west', 'wind-north'][player.wind];
        const windName = WINDS[player.wind];

        let pointsClass = '';
        const delta = player.points - INITIAL_POINTS;
        if (delta > 0) pointsClass = 'positive';
        else if (delta < 0) pointsClass = 'negative';
        if (player.isDealer) pointsClass = 'active';

        let roleButtons = '';
        if (showRoleButtons) {
            const isWinner = selectedWinners.includes(idx);
            const isTenpai = tenpaiPlayers.includes(idx);

            if (currentOutcome === 'draw') {
                // For draw, show tenpai selection
                roleButtons = `
                    <div class="player-role-buttons show">
                        <button class="inline-role-btn ${isTenpai ? 'selected' : ''}" onclick="toggleTenpaiInline(${idx})">聴</button>
                    </div>
                `;
            } else {
                // For ron/tsumo/nagashi
                roleButtons = `
                    <div class="player-role-buttons show">
                        <button class="inline-role-btn ${isWinner ? 'selected' : ''}" onclick="selectWinnerInline(${idx})">+</button>
                        ${currentOutcome === 'ron' ? `<button class="inline-role-btn ${selectedLoser === idx ? 'selected' : ''}" onclick="selectLoserInline(${idx})">−</button>` : ''}
                        <button class="inline-role-btn riichi ${riichiPlayers.includes(idx) ? 'selected' : ''}" onclick="toggleRiichiInline(${idx})">🀫</button>
                    </div>
                `;
            }
        }

        elem.innerHTML = `
            ${roleButtons}
            <div class="player-name">
                ${player.name}
                <span class="wind-indicator ${windClass}">${windName}</span>
            </div>
            <div class="player-points ${pointsClass}">${player.points.toLocaleString()}</div>
        `;
    });

    document.getElementById('roundIndex').textContent = `${WINDS[windRound]}${roundNumber}`;
    document.getElementById('honbaCount').textContent = honba;
    document.getElementById('riichiCount').textContent = riichiSticks;

    saveState();
}

function saveState() {
    localStorage.setItem('tyr_session', JSON.stringify({
        players,
        currentDealer,
        windRound,
        roundNumber,
        honba,
        riichiSticks,
        history
    }));
}

// View switching
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

function showOutcomeSelection() {
    showView('outcomeView');
}

function backToMain() {
    currentOutcome = null;
    selectedWinners = [];
    selectedLoser = null;
    riichiPlayers = [];
    tenpaiPlayers = [];

    // Reset bottom panel to initial state
    document.getElementById('mainButtons').style.display = 'flex';
    document.getElementById('continueButtons').style.display = 'none';
    document.getElementById('outcomeHint').classList.remove('show');

    updateMainDisplay(false);
    showView('mainView');
}

function backToOutcome() {
    selectedWinners = [];
    selectedLoser = null;
    riichiPlayers = [];
    tenpaiPlayers = [];
    showView('outcomeView');
}

function backToRoleSelection() {
    selectedYaku = [];
    doraCount = 0;
    currentFuIndex = 2;
    isOpenHand = false;
    showView('roleView');
}

// Outcome selection
function selectOutcomeType(type) {
    currentOutcome = type;

    // Show inline role buttons on main display
    updateMainDisplay(true);

    // Update bottom panel
    document.getElementById('mainButtons').style.display = 'none';
    document.getElementById('continueButtons').style.display = 'flex';

    // Show hint
    const hint = document.getElementById('outcomeHint');
    if (type === 'ron') {
        hint.textContent = '点击 + 选择和了者（可多选），− 选择放铳者，🀫 选择立直者';
    } else if (type === 'tsumo') {
        hint.textContent = '点击 + 选择和了者，🀫 选择立直者';
    } else if (type === 'nagashi') {
        hint.textContent = '点击 + 选择流满者';
    } else if (type === 'draw') {
        hint.textContent = '点击 聴 选择听牌者（可多选或不选）';
    }
    hint.classList.add('show');

    // Update continue button state
    updateContinueButtonState();

    // Stay on main view
    showView('mainView');
}

function showRoleSelection() {
    const roleList = document.getElementById('roleList');
    const roleHint = document.getElementById('roleHint');

    if (currentOutcome === 'ron') {
        roleHint.textContent = '点击 + 选择和了者，- 选择放铳者，🀫 选择立直者';
    } else if (currentOutcome === 'tsumo') {
        roleHint.textContent = '点击 + 选择和了者，🀫 选择立直者';
    } else if (currentOutcome === 'nagashi') {
        roleHint.textContent = '点击 + 选择流满者';
    }

    roleList.innerHTML = '';
    players.forEach((player, idx) => {
        const item = document.createElement('div');
        item.className = 'player-role-item';

        const name = document.createElement('div');
        name.className = 'player-role-name';
        name.textContent = player.name;

        item.appendChild(name);

        // Winner button (+)
        const winnerBtn = document.createElement('button');
        winnerBtn.className = 'role-btn';
        winnerBtn.textContent = '+';
        winnerBtn.onclick = () => selectWinner(idx);
        if (selectedWinners.includes(idx)) winnerBtn.classList.add('selected');
        item.appendChild(winnerBtn);

        // Loser button (-) for ron only
        if (currentOutcome === 'ron') {
            const loserBtn = document.createElement('button');
            loserBtn.className = 'role-btn';
            loserBtn.textContent = '−';
            loserBtn.onclick = () => selectLoser(idx);
            if (selectedLoser === idx) loserBtn.classList.add('selected');
            item.appendChild(loserBtn);
        }

        // Riichi button
        const riichiBtn = document.createElement('button');
        riichiBtn.className = 'role-btn riichi';
        riichiBtn.textContent = '🀫';
        riichiBtn.onclick = () => toggleRiichi(idx);
        if (riichiPlayers.includes(idx)) riichiBtn.classList.add('selected');
        item.appendChild(riichiBtn);

        roleList.appendChild(item);
    });

    updateContinueButton();
    showView('roleView');
}

function selectWinner(idx) {
    // Old function - kept for compatibility but not used with inline buttons
    selectedWinners = [idx];
    showRoleSelection();
}

function selectLoser(idx) {
    selectedLoser = idx;
    showRoleSelection();
}

function toggleRiichi(idx) {
    const index = riichiPlayers.indexOf(idx);
    if (index > -1) {
        riichiPlayers.splice(index, 1);
    } else {
        riichiPlayers.push(idx);
    }
    showRoleSelection();
}

function updateContinueButton() {
    // Old function for separate role view - kept for compatibility
    const btn = document.getElementById('continueBtn');
    if (!btn) return;

    let canContinue = false;

    if (currentOutcome === 'ron') {
        canContinue = selectedWinners.length > 0 && selectedLoser !== null;
    } else if (currentOutcome === 'tsumo' || currentOutcome === 'nagashi') {
        canContinue = selectedWinners.length === 1;
    }

    btn.disabled = !canContinue;
}

// Inline role button functions
function selectWinnerInline(idx) {
    if (currentOutcome === 'ron') {
        // Ron: allow multiple winners
        const index = selectedWinners.indexOf(idx);
        if (index > -1) {
            selectedWinners.splice(index, 1);
        } else {
            selectedWinners.push(idx);
        }
    } else {
        // Tsumo/Nagashi: only one winner
        selectedWinners = [idx];
    }
    updateMainDisplay(true);
    updateContinueButtonState();
}

function selectLoserInline(idx) {
    selectedLoser = idx;
    updateMainDisplay(true);
    updateContinueButtonState();
}

function toggleRiichiInline(idx) {
    const index = riichiPlayers.indexOf(idx);
    if (index > -1) {
        riichiPlayers.splice(index, 1);
    } else {
        riichiPlayers.push(idx);
    }
    updateMainDisplay(true);
}

function toggleTenpaiInline(idx) {
    const index = tenpaiPlayers.indexOf(idx);
    if (index > -1) {
        tenpaiPlayers.splice(index, 1);
    } else {
        tenpaiPlayers.push(idx);
    }
    updateMainDisplay(true);
    updateContinueButtonState();
}

function cancelRoleSelection() {
    currentOutcome = null;
    selectedWinners = [];
    selectedLoser = null;
    riichiPlayers = [];
    tenpaiPlayers = [];
    updateMainDisplay(false);
    document.getElementById('mainButtons').style.display = 'flex';
    document.getElementById('continueButtons').style.display = 'none';
    document.getElementById('outcomeHint').classList.remove('show');
}

function updateContinueButtonState() {
    const btn = document.getElementById('continueToHandBtn');
    let canContinue = false;

    if (currentOutcome === 'ron') {
        canContinue = selectedWinners.length > 0 && selectedLoser !== null;
    } else if (currentOutcome === 'tsumo' || currentOutcome === 'nagashi') {
        canContinue = selectedWinners.length === 1;
    } else if (currentOutcome === 'draw') {
        canContinue = true; // Always can continue for draw (even with 0 tenpai)
    }

    btn.disabled = !canContinue;
}

function continueToHandSelection() {
    if (currentOutcome === 'draw') {
        // Handle draw with tenpai
        handleDraw();
        return;
    }

    if (currentOutcome === 'nagashi') {
        // Nagashi doesn't need hand selection
        const winnerIdx = selectedWinners[0];
        const isDealer = players[winnerIdx].isDealer;
        if (isDealer) {
            players[winnerIdx].points += 12000;
            players.forEach((p, idx) => {
                if (idx !== winnerIdx) p.points -= 4000;
            });
        } else {
            players[winnerIdx].points += 8000;
            players.forEach((p, idx) => {
                if (idx !== winnerIdx) {
                    p.points -= p.isDealer ? 4000 : 2000;
                }
            });
        }

        advanceRound(isDealer);
        backToMain();
        return;
    }

    // For ron/tsumo, go to hand selection
    // TODO: For multi-ron, we'd need to collect yaku for each winner
    // For now, we'll handle the first winner
    // Reset hand selection state
    selectedYaku = [];
    doraCount = 0;
    currentFuIndex = 2;
    isOpenHand = false;

    renderYaku();
    updateStats();
    showView('handView');
}

function handleDraw() {
    const tenpaiCount = tenpaiPlayers.length;
    const notenCount = 4 - tenpaiCount;

    // Calculate tenpai payments
    if (tenpaiCount > 0 && tenpaiCount < 4) {
        // Total 3000 points distributed
        // Each tenpai player receives 3000 / tenpaiCount
        // Each noten player pays 3000 / notenCount
        const receivePerTenpai = Math.floor(3000 / tenpaiCount / 100) * 100;
        const payPerNoten = Math.floor(3000 / notenCount / 100) * 100;

        players.forEach((p, idx) => {
            if (tenpaiPlayers.includes(idx)) {
                p.points += receivePerTenpai;
            } else {
                p.points -= payPerNoten;
            }
        });
    }

    // Check if dealer is tenpai to determine if renchan
    const dealerIsTenpai = tenpaiPlayers.includes(players.findIndex(p => p.isDealer));
    advanceRound(dealerIsTenpai);
    backToMain();
}

// Hand selection (Yaku)
function toggleOpenHand() {
    isOpenHand = !isOpenHand;
    document.getElementById('openHandText').textContent = isOpenHand ? '副露 (Open Hand)' : '門前 (Menzen)';
    document.getElementById('openHandToggle').classList.toggle('active', isOpenHand);
    renderYaku();
    updateStats();
}

function renderYaku() {
    const list = document.getElementById('yakuList');
    list.innerHTML = '';

    YAKU_LIST.forEach(yaku => {
        const han = isOpenHand ? yaku.open : yaku.menzen;
        const disabled = han === 0;
        const isSelected = selectedYaku.includes(yaku.id);

        const btn = document.createElement('div');
        btn.className = 'yaku-toggle' +
            (isSelected ? ' selected' : '') +
            (disabled ? ' disabled' : '');
        btn.textContent = yaku.name;

        if (!disabled) {
            btn.onclick = () => toggleYaku(yaku.id);
        }

        list.appendChild(btn);
    });
}

function toggleYaku(yakuId) {
    const index = selectedYaku.indexOf(yakuId);
    if (index > -1) {
        selectedYaku.splice(index, 1);
    } else {
        selectedYaku.push(yakuId);
    }
    renderYaku();
    updateStats();
}

function changeDora(delta) {
    doraCount = Math.max(0, Math.min(20, doraCount + delta));
    document.getElementById('doraValue').textContent = `Dora ${doraCount}`;
    updateStats();
}

function changeFu(delta) {
    currentFuIndex = Math.max(0, Math.min(FU_VALUES.length - 1, currentFuIndex + delta));
    const fu = FU_VALUES[currentFuIndex];
    document.getElementById('fuValue').textContent = `${fu} 符`;
    updateStats();
}

function updateStats() {
    let totalHan = doraCount;
    let yakumanCount = 0;
    let hasYakuman = false;

    selectedYaku.forEach(yakuId => {
        const yaku = YAKU_LIST.find(y => y.id === yakuId);
        if (yaku) {
            const han = isOpenHand ? yaku.open : yaku.menzen;
            if (yaku.yakuman) {
                hasYakuman = true;
                yakumanCount += han / 13;
            } else {
                totalHan += han;
            }
        }
    });

    const hasPinfu = selectedYaku.includes('pinfu');
    const hasChiitoitsu = selectedYaku.includes('chiitoitsu');
    const needFu = !hasYakuman && !hasPinfu && !hasChiitoitsu && totalHan > 0 && totalHan < 5;

    const fuSelector = document.getElementById('fuSelector');
    if (needFu) {
        fuSelector.classList.remove('disabled');
    } else {
        fuSelector.classList.add('disabled');
    }

    const fu = FU_VALUES[currentFuIndex];
    let statsText = '';

    if (hasYakuman) {
        statsText = yakumanCount === 1 ? '役満 Yakuman' : `役満 x${yakumanCount}`;
    } else if (totalHan >= 13) {
        statsText = '数え役満 Kazoe Yakuman';
    } else if (totalHan >= 11) {
        statsText = '三倍満 Sanbaiman';
    } else if (totalHan >= 8) {
        statsText = '倍満 Baiman';
    } else if (totalHan >= 6) {
        statsText = '跳満 Haneman';
    } else if (totalHan >= 5) {
        statsText = '満貫 Mangan';
    } else if (totalHan > 0) {
        statsText = needFu ? `${totalHan} han ${fu} fu` : `${totalHan} han`;
    } else {
        statsText = '0 han';
    }

    document.getElementById('statsDisplay').textContent = statsText;

    const submitBtn = document.getElementById('submitHandBtn');
    submitBtn.disabled = totalHan === 0 && !hasYakuman;
}

function handleScroll() {
    const yakuList = document.getElementById('yakuList');
    const topShadow = document.getElementById('topShadow');
    const bottomSection = document.getElementById('bottomSection');

    if (yakuList.scrollTop < 4) {
        topShadow.classList.add('no-shadow');
    } else {
        topShadow.classList.remove('no-shadow');
    }

    const isAtBottom = Math.abs(
        yakuList.scrollTop - (yakuList.scrollHeight - yakuList.clientHeight)
    ) < 4;

    if (isAtBottom) {
        bottomSection.classList.add('no-shadow');
    } else {
        bottomSection.classList.remove('no-shadow');
    }
}

function submitHand() {
    // For multi-ron, apply points for each winner
    // For now, we assume all winners have the same yaku (simplified)
    if (currentOutcome === 'ron' && selectedWinners.length > 1) {
        // Multi-ron: all winners win with the same hand
        const closestWinner = findClosestWinner();

        selectedWinners.forEach(winnerIdx => {
            const points = calculatePoints(winnerIdx);
            if (points) {
                applyPointsForWinner(points, winnerIdx);
                // Only closest winner gets honba
                if (winnerIdx === closestWinner) {
                    players[winnerIdx].points += honba * 300;
                    players[selectedLoser].points -= honba * 300;
                }
            }
        });

        // Add riichi sticks to the closest winner (upstream of loser)
        players[closestWinner].points += riichiSticks * 1000;
        riichiSticks = 0;

        // Add riichi sticks for this round
        riichiSticks += riichiPlayers.length;

        // Check if any winner is dealer
        const anyDealerWon = selectedWinners.some(idx => players[idx].isDealer);
        advanceRound(anyDealerWon);
        backToMain();
        return;
    }

    // Single winner (ron/tsumo)
    const points = calculatePoints(selectedWinners[0]);
    if (!points) {
        alert('无法计算点数');
        return;
    }

    applyPoints(points);

    // Add riichi sticks
    riichiSticks += riichiPlayers.length;

    advanceRound(players[selectedWinners[0]].isDealer);
    backToMain();
}

function findClosestWinner() {
    // Find the winner upstream (counterclockwise) from the loser
    if (selectedWinners.length === 0) return 0;
    if (selectedWinners.length === 1) return selectedWinners[0];

    // Find closest winner upstream from loser
    let closest = selectedWinners[0];
    let minDistance = 4;

    selectedWinners.forEach(winnerIdx => {
        const distance = (selectedLoser - winnerIdx + 4) % 4;
        if (distance > 0 && distance < minDistance) {
            minDistance = distance;
            closest = winnerIdx;
        }
    });

    return closest;
}

function calculatePoints(winnerIdx) {
    let totalHan = doraCount;
    let yakumanCount = 0;
    let hasYakuman = false;

    selectedYaku.forEach(yakuId => {
        const yaku = YAKU_LIST.find(y => y.id === yakuId);
        if (yaku) {
            const han = isOpenHand ? yaku.open : yaku.menzen;
            if (yaku.yakuman) {
                hasYakuman = true;
                yakumanCount += han / 13;
            } else {
                totalHan += han;
            }
        }
    });

    if (totalHan === 0 && !hasYakuman) return null;

    const fu = FU_VALUES[currentFuIndex];
    const isDealer = players[winnerIdx].isDealer;

    // Simplified point calculation
    let basePoints;

    if (hasYakuman) {
        basePoints = 8000 * yakumanCount;
    } else if (totalHan >= 13) {
        basePoints = 8000;
    } else if (totalHan >= 11) {
        basePoints = 6000;
    } else if (totalHan >= 8) {
        basePoints = 4000;
    } else if (totalHan >= 6) {
        basePoints = 3000;
    } else if (totalHan >= 5) {
        basePoints = 2000;
    } else {
        basePoints = fu * Math.pow(2, 2 + totalHan);
        if (basePoints > 2000) basePoints = 2000; // Cap at mangan
    }

    if (currentOutcome === 'ron') {
        const points = isDealer ? basePoints * 6 : basePoints * 4;
        return { type: 'ron', points: Math.ceil(points / 100) * 100 };
    } else if (currentOutcome === 'tsumo') {
        if (isDealer) {
            const each = Math.ceil(basePoints * 2 / 100) * 100;
            return { type: 'tsumo', dealer: true, each };
        } else {
            const dealerPays = Math.ceil(basePoints * 2 / 100) * 100;
            const otherPays = Math.ceil(basePoints / 100) * 100;
            return { type: 'tsumo', dealer: false, dealerPays, otherPays };
        }
    }

    return null;
}

function applyPoints(pointsData) {
    const winnerIdx = selectedWinners[0];
    if (pointsData.type === 'ron') {
        players[winnerIdx].points += pointsData.points + honba * 300 + riichiSticks * 1000;
        players[selectedLoser].points -= pointsData.points + honba * 300;
        riichiSticks = 0;
    } else if (pointsData.type === 'tsumo') {
        if (pointsData.dealer) {
            players[winnerIdx].points += pointsData.each * 3 + honba * 300 + riichiSticks * 1000;
            players.forEach((p, idx) => {
                if (idx !== winnerIdx) p.points -= pointsData.each + honba * 100;
            });
        } else {
            players[winnerIdx].points += pointsData.dealerPays + pointsData.otherPays * 2 + honba * 300 + riichiSticks * 1000;
            players.forEach((p, idx) => {
                if (idx !== winnerIdx) {
                    p.points -= (p.isDealer ? pointsData.dealerPays : pointsData.otherPays) + honba * 100;
                }
            });
        }
        riichiSticks = 0;
    }
}

function applyPointsForWinner(pointsData, winnerIdx) {
    // For multi-ron: each winner gets their points from the loser
    // No honba/riichi sticks here (handled separately)
    if (pointsData.type === 'ron') {
        players[winnerIdx].points += pointsData.points;
        players[selectedLoser].points -= pointsData.points;
    }
}

function advanceRound(dealerWon) {
    if (dealerWon) {
        honba++;
    } else {
        honba = 0;
        currentDealer = (currentDealer + 1) % 4;
        roundNumber++;

        if (roundNumber > 4) {
            roundNumber = 1;
            windRound++;
        }

        players.forEach((p, idx) => {
            p.wind = (idx - currentDealer + 4) % 4;
            p.isDealer = p.wind === 0;
        });
    }
}

function resetGame() {
    if (!confirm('确定要重置对局吗？所有数据将丢失。')) return;
    localStorage.removeItem('tyr_session');
    location.reload();
}

// Fix mobile vh issue (address bar)
function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Initialize on load
setVH();
window.addEventListener('resize', setVH);
window.addEventListener('orientationchange', setVH);

init();
