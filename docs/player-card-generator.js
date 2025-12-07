/**
 * M-League 玩家卡片生成器
 * 用于根据JSON数据生成玩家统计卡片的HTML模板
 */

/**
 * 主函数：生成完整的玩家卡片HTML
 * @param {Object} playerData - 玩家完整数据对象
 * @param {string} playerData.playerName - 玩家名称
 * @param {Object} playerData.basicStats - 基本统计数据
 * @param {Object} playerData.rankDistribution - 名次分布
 * @param {Object} playerData.winStats - 和了统计
 * @param {Object} playerData.riichiAndMeld - 立直副露统计
 * @param {Object} playerData.dealInStats - 放铳统计
 * @param {Array} playerData.matchups - 对战情况列表
 * @param {Array} playerData.yakuStats - 手役统计列表
 * @param {Object} playerData.exhaustiveDraw - 流局听牌统计
 * @returns {string} 完整的玩家卡片HTML字符串
 */
function createPlayerCard(playerData) {
    const {
        playerName,
        basicStats,
        rankDistribution,
        winStats,
        riichiAndMeld,
        dealInStats,
        matchups,
        yakuStats,
        exhaustiveDraw
    } = playerData;

    return `
    <div class="player-card" id="player-${playerName}">
        <h3>${playerName}</h3>
        ${createStatsGrid(basicStats)}

        <div class="section">
            <h4>名次分布</h4>
            ${createRankBars(rankDistribution)}
        </div>

        ${createWinStatsSection(winStats)}

        ${createRiichiMeldSection(riichiAndMeld)}

        ${createDealInSection(dealInStats)}

        <div class="section">
            <h4>对战情况</h4>
            ${createMatchupsTable(matchups)}
        </div>

        <div class="section">
            <h4>手役统计 (前10名)</h4>
            ${createYakuList(yakuStats)}
        </div>

        ${createExhaustiveDrawSection(exhaustiveDraw)}
    </div>
    `;
}

/**
 * 生成基本统计网格
 * @param {Object} basicStats - 基本统计数据
 * @param {number} basicStats.rValue - R值
 * @param {number} basicStats.totalPoints - 总点数
 * @param {number} basicStats.avgRank - 平均顺位
 * @param {number} basicStats.gameCount - 场数
 * @returns {string} 统计网格HTML
 */
function createStatsGrid(basicStats) {
    const { rValue, totalPoints, avgRank, gameCount } = basicStats;

    // 格式化总点数（添加正负号）
    const formattedPoints = totalPoints >= 0 ? `+${totalPoints}` : `${totalPoints}`;

    return `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">R值</div>
                <div class="stat-value large">${rValue.toFixed(2)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">总点数</div>
                <div class="stat-value">${formattedPoints}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">平均顺位</div>
                <div class="stat-value">${avgRank.toFixed(2)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">场数</div>
                <div class="stat-value">${gameCount} 半庄</div>
            </div>
        </div>`;
}

/**
 * 生成名次分布条形图
 * @param {Object} rankDistribution - 名次分布数据
 * @param {Object} rankDistribution.rank1 - 1位统计 {count, percentage}
 * @param {Object} rankDistribution.rank2 - 2位统计 {count, percentage}
 * @param {Object} rankDistribution.rank3 - 3位统计 {count, percentage}
 * @param {Object} rankDistribution.rank4 - 4位统计 {count, percentage}
 * @returns {string} 名次分布条形图HTML
 */
function createRankBars(rankDistribution) {
    const ranks = [
        { label: '1位', data: rankDistribution.rank1, barClass: 'bar-1' },
        { label: '2位', data: rankDistribution.rank2, barClass: 'bar-2' },
        { label: '3位', data: rankDistribution.rank3, barClass: 'bar-3' },
        { label: '4位', data: rankDistribution.rank4, barClass: 'bar-4' }
    ];

    const barsHtml = ranks.map(rank => {
        const { count, percentage } = rank.data;
        return `
                <div class="rank-bar">
                    <span class="rank-label">${rank.label}</span>
                    <div class="bar-container">
                        <div class="bar ${rank.barClass}" style="width: ${percentage.toFixed(2)}%"></div>
                        <span class="bar-text">${count} 次 (${percentage.toFixed(1)}%)</span>
                    </div>
                </div>`;
    }).join('');

    return `
            <div class="rank-bars">${barsHtml}
            </div>`;
}

/**
 * 生成和了统计部分
 * @param {Object} winStats - 和了统计数据
 * @param {Object} winStats.overall - 总体和了统计 {count, rate, avgPoints, leagueAvgRate, leagueAvgPoints}
 * @param {Object} winStats.riichi - 立直和了统计 {count, avgPoints, leagueAvgPoints, ippatsu, uraDora}
 * @param {Object} winStats.meld - 副露和了统计 {count, avgPoints, leagueAvgPoints}
 * @param {Object} winStats.damaten - 默听和了统计 {count, avgPoints, leagueAvgPoints}
 * @param {Object} [winStats.tsumoOnly] - 仅自摸和了统计（可选） {count, avgPoints, leagueAvgPoints}
 * @returns {string} 和了统计部分HTML
 */
function createWinStatsSection(winStats) {
    const { overall, riichi, meld, damaten, tsumoOnly } = winStats;

    // 生成仅自摸和了行（如果存在）
    const tsumoOnlyRow = tsumoOnly ? `
                    <tr>
                        <td class="type-label">仅自摸和了</td>
                        <td>${tsumoOnly.count} 小局</td>
                        <td class="points-value">${tsumoOnly.avgPoints}点 <span class="league-avg">(平均${tsumoOnly.leagueAvgPoints})</span></td>
                        <td class="special-stats">门清自摸</td>
                    </tr>` : '';

    return `
        <div class="section">
            <h4>和了统计</h4>
            <div class="summary-box">
                <span class="summary-label">总和了:</span>
                <span class="summary-value">${overall.count} 小局 (${overall.rate.toFixed(1)}%) <span class="league-avg">(平均${overall.leagueAvgRate.toFixed(1)}%)</span></span>
                <span class="summary-label">平均打点:</span>
                <span class="summary-value">${overall.avgPoints}点 <span class="league-avg">(平均${overall.leagueAvgPoints}点)</span></span>
            </div>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>次数</th>
                        <th>平均打点</th>
                        <th>特殊统计</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="type-label">立直和了</td>
                        <td>${riichi.count} 小局</td>
                        <td class="points-value">${riichi.avgPoints}点 <span class="league-avg">(平均${riichi.leagueAvgPoints})</span></td>
                        <td class="special-stats">一发: ${riichi.ippatsu.count}小局 (${riichi.ippatsu.rate.toFixed(1)}%) <span class="league-avg">(平均${riichi.ippatsu.leagueAvgRate.toFixed(1)}%)</span> · 里宝: ${riichi.uraDora.count}小局 (${riichi.uraDora.rate.toFixed(1)}%) <span class="league-avg">(平均${riichi.uraDora.leagueAvgRate.toFixed(1)}%)</span></td>
                    </tr>
                    <tr>
                        <td class="type-label">副露和了</td>
                        <td>${meld.count} 小局</td>
                        <td class="points-value">${meld.avgPoints}点 <span class="league-avg">(平均${meld.leagueAvgPoints})</span></td>
                        <td class="special-stats">-</td>
                    </tr>
                    <tr>
                        <td class="type-label">默听和了</td>
                        <td>${damaten.count} 小局</td>
                        <td class="points-value">${damaten.avgPoints}点 <span class="league-avg">(平均${damaten.leagueAvgPoints})</span></td>
                        <td class="special-stats">有役门清</td>
                    </tr>
                    ${tsumoOnlyRow}
                </tbody>
            </table>
        </div>`;
}

/**
 * 生成立直副露部分
 * @param {Object} riichiAndMeld - 立直副露统计数据
 * @param {Object} riichiAndMeld.riichi - 立直统计 {count, rate, leagueAvgRate, winRate, drawRate, dealInRate, sideRate, leagueAvgWinRate, leagueAvgDealInRate}
 * @param {Object} riichiAndMeld.meld - 副露统计 {count, rate, leagueAvgRate, winRate, drawRate, dealInRate, sideRate, leagueAvgWinRate, leagueAvgDealInRate}
 * @returns {string} 立直副露部分HTML
 */
function createRiichiMeldSection(riichiAndMeld) {
    const { riichi, meld } = riichiAndMeld;

    /**
     * 辅助函数：根据比率值返回对应的CSS类名
     * @param {number} rate - 比率值
     * @param {string} type - 类型 ('win', 'dealIn')
     * @returns {string} CSS类名
     */
    const getRateClass = (rate, type) => {
        if (type === 'win') {
            return rate >= 40 ? 'rate-good' : 'rate-neutral';
        } else if (type === 'dealIn') {
            return rate >= 15 ? 'rate-bad' : 'rate-neutral';
        }
        return 'rate-neutral';
    };

    return `
        <div class="section">
            <h4>立直 & 副露</h4>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>次数/比率</th>
                        <th>和了</th>
                        <th>流局</th>
                        <th>放铳</th>
                        <th>横移动</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="type-label">立直</td>
                        <td>${riichi.count} 小局 (${riichi.rate.toFixed(1)}%) <span class="league-avg">(平均${riichi.leagueAvgRate.toFixed(1)}%)</span></td>
                        <td class="${getRateClass(riichi.winRate, 'win')}">${riichi.winRate.toFixed(1)}% <span class="league-avg">(平均${riichi.leagueAvgWinRate.toFixed(1)}%)</span></td>
                        <td class="rate-neutral">${riichi.drawRate.toFixed(1)}%</td>
                        <td class="${getRateClass(riichi.dealInRate, 'dealIn')}">${riichi.dealInRate.toFixed(1)}% <span class="league-avg">(平均${riichi.leagueAvgDealInRate.toFixed(1)}%)</span></td>
                        <td class="rate-neutral">${riichi.sideRate.toFixed(1)}%</td>
                    </tr>
                    <tr>
                        <td class="type-label">副露</td>
                        <td>${meld.count} 小局 (${meld.rate.toFixed(1)}%) <span class="league-avg">(平均${meld.leagueAvgRate.toFixed(1)}%)</span></td>
                        <td class="${getRateClass(meld.winRate, 'win')}">${meld.winRate.toFixed(1)}% <span class="league-avg">(平均${meld.leagueAvgWinRate.toFixed(1)}%)</span></td>
                        <td class="rate-neutral">${meld.drawRate.toFixed(1)}%</td>
                        <td class="${getRateClass(meld.dealInRate, 'dealIn')}">${meld.dealInRate.toFixed(1)}% <span class="league-avg">(平均${meld.leagueAvgDealInRate.toFixed(1)}%)</span></td>
                        <td class="rate-neutral">${meld.sideRate.toFixed(1)}%</td>
                    </tr>

                </tbody>
            </table>
        </div>`;
}

/**
 * 生成放铳统计部分
 * @param {Object} dealInStats - 放铳统计数据
 * @param {number} dealInStats.count - 放铳次数
 * @param {number} dealInStats.rate - 放铳率
 * @param {number} dealInStats.avgPoints - 平均失点
 * @param {number} dealInStats.leagueAvgRate - 联盟平均放铳率
 * @param {number} dealInStats.leagueAvgPoints - 联盟平均失点
 * @returns {string} 放铳统计部分HTML
 */
function createDealInSection(dealInStats) {
    const { count, rate, avgPoints, leagueAvgRate, leagueAvgPoints } = dealInStats;

    return `
        <div class="section">
            <h4>放铳统计</h4>
            <div class="summary-box">
                <span class="summary-label">放铳:</span>
                <span class="summary-value">${count} 小局 (${rate.toFixed(1)}%) <span class="league-avg">(平均${leagueAvgRate.toFixed(1)}%)</span></span>
                <span class="summary-label">平均失点:</span>
                <span class="summary-value negative">${avgPoints}点 <span class="league-avg">(平均${leagueAvgPoints}点)</span></span>
            </div>
        </div>`;
}

/**
 * 生成对战情况表格
 * @param {Array} matchups - 对战情况列表
 * @param {string} matchups[].opponent - 对手名称
 * @param {number} matchups[].gameCount - 对战场数
 * @param {number} matchups[].winRate - 胜率
 * @param {number} matchups[].winPoints - 和了获点
 * @param {number} matchups[].dealInPoints - 放铳失点
 * @param {number} matchups[].netWinDealIn - 净和了放铳点数
 * @param {number} matchups[].totalPointDiff - 总得点差
 * @param {boolean} [matchups[].hasLink] - 是否有链接（可选，默认false）
 * @returns {string} 对战情况表格HTML
 */
function createMatchupsTable(matchups) {
    /**
     * 辅助函数：根据数值返回对应的CSS类名
     * @param {number} value - 数值
     * @returns {string} CSS类名
     */
    const getValueClass = (value) => {
        if (value > 0) return 'positive';
        if (value < 0) return 'negative';
        return 'neutral';
    };

    /**
     * 辅助函数：根据胜率返回对应的CSS类名
     * @param {number} winRate - 胜率
     * @returns {string} CSS类名
     */
    const getWinRateClass = (winRate) => {
        return winRate >= 25 ? 'rate-good' : 'rate-bad';
    };

    /**
     * 辅助函数：格式化点数（添加正负号）
     * @param {number} points - 点数
     * @returns {string} 格式化后的点数字符串
     */
    const formatPoints = (points) => {
        if (points > 0) return `+${points}`;
        if (points < 0) return `${points}`;
        return `+${points}`;
    };

    const rowsHtml = matchups.map(matchup => {
        const opponentDisplay = matchup.hasLink
            ? `<a href="#player-${matchup.opponent}" class="opponent-link">${matchup.opponent}</a>`
            : matchup.opponent;

        return `
                <tr>
                    <td class="opponent-name">${opponentDisplay}</td>
                    <td>${matchup.gameCount}</td>
                    <td class="${getWinRateClass(matchup.winRate)}">${matchup.winRate.toFixed(1)}%</td>
                    <td class="${getValueClass(matchup.winPoints)}">${formatPoints(matchup.winPoints)}</td>
                    <td class="${getValueClass(-matchup.dealInPoints)}">${formatPoints(-matchup.dealInPoints)}</td>
                    <td class="${getValueClass(matchup.netWinDealIn)}">${formatPoints(matchup.netWinDealIn)}</td>
                    <td class="${getValueClass(matchup.totalPointDiff)}">${formatPoints(matchup.totalPointDiff)}</td>
                </tr>`;
    }).join('');

    return `
        <table class="vs-table">
            <thead>
                <tr>
                    <th>对手</th>
                    <th>场数</th>
                    <th>胜率</th>
                    <th>和了获点</th>
                    <th>放铳失点</th>
                    <th>净和了放铳点数</th>
                    <th>总得点差</th>
                </tr>
            </thead>
            <tbody>
        ${rowsHtml}
            </tbody>
        </table>`;
}

/**
 * 生成手役统计列表
 * @param {Array} yakuStats - 手役统计列表（通常前10名）
 * @param {string} yakuStats[].name - 手役名称
 * @param {number} yakuStats[].count - 出现次数
 * @param {number} yakuStats[].rate - 出现率
 * @param {number} yakuStats[].leagueAvgRate - 联盟平均出现率
 * @returns {string} 手役统计列表HTML
 */
function createYakuList(yakuStats) {
    const yakuItems = yakuStats.map(yaku =>
        `<li>${yaku.name}: ${yaku.count}次 (${yaku.rate.toFixed(2)}%) <span class="league-avg">(平均${yaku.leagueAvgRate.toFixed(2)}%)</span></li>`
    ).join('');

    return `
            <ul class="yaku-list">
                ${yakuItems}
            </ul>`;
}

/**
 * 生成流局听牌部分
 * @param {Object} exhaustiveDraw - 流局听牌统计数据
 * @param {number} exhaustiveDraw.totalDraws - 总流局次数
 * @param {number} exhaustiveDraw.tenpaCount - 听牌次数
 * @param {number} exhaustiveDraw.tenpaRate - 听牌率
 * @param {number} exhaustiveDraw.leagueAvgTenpaRate - 联盟平均听牌率
 * @returns {string} 流局听牌部分HTML
 */
function createExhaustiveDrawSection(exhaustiveDraw) {
    const { totalDraws, tenpaCount, tenpaRate, leagueAvgTenpaRate } = exhaustiveDraw;

    return `
        <div class="section">
            <h4>流局听牌</h4>
            <p>流局: ${totalDraws} 次, 听牌 ${tenpaCount} 次 (${tenpaRate.toFixed(1)}%) <span class="league-avg">(平均${leagueAvgTenpaRate.toFixed(1)}%)</span></p>
        </div>`;
}

// ==================== 使用示例 ====================

/**
 * 示例数据结构
 */
const examplePlayerData = {
    playerName: "santi",
    basicStats: {
        rValue: 1561.16,
        totalPoints: 102300,
        avgRank: 2.46,
        gameCount: 185
    },
    rankDistribution: {
        rank1: { count: 48, percentage: 25.95 },
        rank2: { count: 42, percentage: 22.7 },
        rank3: { count: 56, percentage: 30.27 },
        rank4: { count: 39, percentage: 21.08 }
    },
    winStats: {
        overall: {
            count: 455,
            rate: 21.2,
            avgPoints: 6355,
            leagueAvgRate: 21.4,
            leagueAvgPoints: 6298
        },
        riichi: {
            count: 234,
            avgPoints: 7505,
            leagueAvgPoints: 7706,
            ippatsu: {
                count: 39,
                rate: 16.7,
                leagueAvgRate: 20.4
            },
            uraDora: {
                count: 77,
                rate: 32.9,
                leagueAvgRate: 30.6
            }
        },
        meld: {
            count: 177,
            avgPoints: 4633,
            leagueAvgPoints: 4640
        },
        damaten: {
            count: 44,
            avgPoints: 7166,
            leagueAvgPoints: 6736
        }
        // tsumoOnly 为可选字段
        // tsumoOnly: {
        //     count: 3,
        //     avgPoints: 10300,
        //     leagueAvgPoints: 4890
        // }
    },
    riichiAndMeld: {
        riichi: {
            count: 488,
            rate: 22.8,
            leagueAvgRate: 21.8,
            winRate: 48.0,
            drawRate: 12.3,
            dealInRate: 15.8,
            sideRate: 24.0,
            leagueAvgWinRate: 46.3,
            leagueAvgDealInRate: 15.3
        },
        meld: {
            count: 689,
            rate: 32.1,
            leagueAvgRate: 31.7,
            winRate: 25.7,
            drawRate: 17.1,
            dealInRate: 13.9,
            sideRate: 43.2,
            leagueAvgWinRate: 29.2,
            leagueAvgDealInRate: 13.1
        }
    },
    dealInStats: {
        count: 284,
        rate: 13.2,
        avgPoints: 5392,
        leagueAvgRate: 13.3,
        leagueAvgPoints: 5655
    },
    matchups: [
        {
            opponent: "姫野婭也",
            gameCount: 106,
            winRate: 56.6,
            winPoints: 369700,
            dealInPoints: 296000,
            netWinDealIn: 73700,
            totalPointDiff: 472100,
            hasLink: false  // 可选，默认false
        },
        {
            opponent: "南美雀后",
            gameCount: 97,
            winRate: 51.5,
            winPoints: 311900,
            dealInPoints: 187900,
            netWinDealIn: 124000,
            totalPointDiff: 507800,
            hasLink: true
        }
        // ... 更多对手数据
    ],
    yakuStats: [
        { name: "立直", count: 233, rate: 51.21, leagueAvgRate: 46.79 },
        { name: "役牌", count: 160, rate: 35.16, leagueAvgRate: 40.7 },
        { name: "断幺九", count: 101, rate: 22.2, leagueAvgRate: 20.12 },
        { name: "门前清自摸和", count: 98, rate: 21.54, leagueAvgRate: 23.52 },
        { name: "平和", count: 95, rate: 20.88, leagueAvgRate: 21.3 },
        { name: "一杯口", count: 19, rate: 4.18, leagueAvgRate: 4.44 },
        { name: "七对子", count: 18, rate: 3.96, leagueAvgRate: 2.87 },
        { name: "混一色", count: 16, rate: 3.52, leagueAvgRate: 5.87 },
        { name: "三色同顺", count: 10, rate: 2.2, leagueAvgRate: 2.93 },
        { name: "对对和", count: 5, rate: 1.1, leagueAvgRate: 2.5 }
    ],
    exhaustiveDraw: {
        totalDraws: 284,
        tenpaCount: 136,
        tenpaRate: 47.9,
        leagueAvgTenpaRate: 46.3
    }
};

/**
 * 使用示例：
 *
 * // 生成单个玩家卡片
 * const playerCardHtml = createPlayerCard(examplePlayerData);
 * console.log(playerCardHtml);
 *
 * // 或者仅生成特定部分
 * const statsGridHtml = createStatsGrid(examplePlayerData.basicStats);
 * const rankBarsHtml = createRankBars(examplePlayerData.rankDistribution);
 * const winStatsHtml = createWinStatsSection(examplePlayerData.winStats);
 * // ...等等
 */

// 导出函数供外部使用（如果在模块环境中）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        createPlayerCard,
        createStatsGrid,
        createRankBars,
        createWinStatsSection,
        createRiichiMeldSection,
        createDealInSection,
        createMatchupsTable,
        createYakuList,
        createExhaustiveDrawSection
    };
}
