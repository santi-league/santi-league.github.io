# 玩家卡片生成器使用说明

## 概述

`player-card-generator.js` 提供了一套完整的JavaScript函数，用于根据JSON数据生成M-League玩家统计卡片的HTML模板。

## 主要功能

### 1. `createPlayerCard(playerData)`

主函数，生成完整的玩家卡片HTML。

**参数：**
```javascript
playerData = {
    playerName: string,           // 玩家名称
    basicStats: Object,           // 基本统计数据
    rankDistribution: Object,     // 名次分布
    winStats: Object,            // 和了统计
    riichiAndMeld: Object,       // 立直副露统计
    dealInStats: Object,         // 放铳统计
    matchups: Array,             // 对战情况列表
    yakuStats: Array,            // 手役统计列表
    exhaustiveDraw: Object       // 流局听牌统计
}
```

**返回值：** 完整的玩家卡片HTML字符串

**使用示例：**
```javascript
const playerHtml = createPlayerCard({
    playerName: "santi",
    basicStats: { /* ... */ },
    // ... 其他数据
});

// 将生成的HTML插入到页面中
document.getElementById('player-container').innerHTML = playerHtml;
```

---

### 2. `createStatsGrid(basicStats)`

生成基本统计网格（R值、总点数、平均顺位、场数）。

**参数：**
```javascript
basicStats = {
    rValue: number,        // R值
    totalPoints: number,   // 总点数（可以为负数）
    avgRank: number,       // 平均顺位
    gameCount: number      // 场数
}
```

**示例：**
```javascript
const statsHtml = createStatsGrid({
    rValue: 1561.16,
    totalPoints: 102300,
    avgRank: 2.46,
    gameCount: 185
});
```

**输出特性：**
- R值和平均顺位保留2位小数
- 总点数自动添加正负号
- 场数自动添加"半庄"单位

---

### 3. `createRankBars(rankDistribution)`

生成名次分布条形图。

**参数：**
```javascript
rankDistribution = {
    rank1: { count: number, percentage: number },
    rank2: { count: number, percentage: number },
    rank3: { count: number, percentage: number },
    rank4: { count: number, percentage: number }
}
```

**示例：**
```javascript
const rankBarsHtml = createRankBars({
    rank1: { count: 48, percentage: 25.95 },
    rank2: { count: 42, percentage: 22.7 },
    rank3: { count: 56, percentage: 30.27 },
    rank4: { count: 39, percentage: 21.08 }
});
```

**视觉效果：**
- 1位：绿色渐变条
- 2位：蓝色渐变条
- 3位：黄色渐变条
- 4位：红色渐变条

---

### 4. `createWinStatsSection(winStats)`

生成和了统计部分，包括总体和了、立直和了、副露和了、默听和了和可选的仅自摸和了。

**参数：**
```javascript
winStats = {
    overall: {
        count: number,              // 总和了次数
        rate: number,               // 总和了率
        avgPoints: number,          // 平均打点
        leagueAvgRate: number,      // 联盟平均和了率
        leagueAvgPoints: number     // 联盟平均打点
    },
    riichi: {
        count: number,
        avgPoints: number,
        leagueAvgPoints: number,
        ippatsu: {
            count: number,
            rate: number,
            leagueAvgRate: number
        },
        uraDora: {
            count: number,
            rate: number,
            leagueAvgRate: number
        }
    },
    meld: {
        count: number,
        avgPoints: number,
        leagueAvgPoints: number
    },
    damaten: {
        count: number,
        avgPoints: number,
        leagueAvgPoints: number
    },
    // 可选字段
    tsumoOnly: {
        count: number,
        avgPoints: number,
        leagueAvgPoints: number
    }
}
```

**特殊说明：**
- `tsumoOnly` 是可选字段，如果提供则会显示"仅自摸和了"行
- 联盟平均值会显示在灰色小字中

---

### 5. `createRiichiMeldSection(riichiAndMeld)`

生成立直副露统计表格。

**参数：**
```javascript
riichiAndMeld = {
    riichi: {
        count: number,
        rate: number,
        leagueAvgRate: number,
        winRate: number,
        drawRate: number,
        dealInRate: number,
        sideRate: number,
        leagueAvgWinRate: number,
        leagueAvgDealInRate: number
    },
    meld: {
        count: number,
        rate: number,
        leagueAvgRate: number,
        winRate: number,
        drawRate: number,
        dealInRate: number,
        sideRate: number,
        leagueAvgWinRate: number,
        leagueAvgDealInRate: number
    }
}
```

**自动样式规则：**
- 和了率 ≥ 40%：绿色（rate-good）
- 和了率 < 40%：灰色（rate-neutral）
- 放铳率 ≥ 15%：红色（rate-bad）
- 放铳率 < 15%：灰色（rate-neutral）

---

### 6. `createDealInSection(dealInStats)`

生成放铳统计部分。

**参数：**
```javascript
dealInStats = {
    count: number,              // 放铳次数
    rate: number,               // 放铳率
    avgPoints: number,          // 平均失点
    leagueAvgRate: number,      // 联盟平均放铳率
    leagueAvgPoints: number     // 联盟平均失点
}
```

**示例：**
```javascript
const dealInHtml = createDealInSection({
    count: 284,
    rate: 13.2,
    avgPoints: 5392,
    leagueAvgRate: 13.3,
    leagueAvgPoints: 5655
});
```

---

### 7. `createMatchupsTable(matchups)`

生成对战情况表格。

**参数：**
```javascript
matchups = [
    {
        opponent: string,           // 对手名称
        gameCount: number,          // 对战场数
        winRate: number,            // 胜率
        winPoints: number,          // 和了获点
        dealInPoints: number,       // 放铳失点
        netWinDealIn: number,       // 净和了放铳点数
        totalPointDiff: number,     // 总得点差
        hasLink: boolean           // 是否有链接（可选，默认false）
    },
    // ... 更多对手
]
```

**自动样式规则：**
- 胜率 ≥ 25%：绿色（rate-good）
- 胜率 < 25%：红色（rate-bad）
- 正点数：绿色（positive）
- 负点数：红色（negative）
- 零点数：灰色（neutral）

**链接功能：**
- 当 `hasLink: true` 时，对手名称会生成锚点链接 `#player-{对手名称}`

**示例：**
```javascript
const matchupsHtml = createMatchupsTable([
    {
        opponent: "姫野婭也",
        gameCount: 106,
        winRate: 56.6,
        winPoints: 369700,
        dealInPoints: 296000,
        netWinDealIn: 73700,
        totalPointDiff: 472100,
        hasLink: false
    },
    {
        opponent: "南美雀后",
        gameCount: 97,
        winRate: 51.5,
        winPoints: 311900,
        dealInPoints: 187900,
        netWinDealIn: 124000,
        totalPointDiff: 507800,
        hasLink: true  // 会生成链接
    }
]);
```

---

### 8. `createYakuList(yakuStats)`

生成手役统计列表（通常显示前10名）。

**参数：**
```javascript
yakuStats = [
    {
        name: string,              // 手役名称
        count: number,             // 出现次数
        rate: number,              // 出现率
        leagueAvgRate: number      // 联盟平均出现率
    },
    // ... 更多手役
]
```

**示例：**
```javascript
const yakuHtml = createYakuList([
    { name: "立直", count: 233, rate: 51.21, leagueAvgRate: 46.79 },
    { name: "役牌", count: 160, rate: 35.16, leagueAvgRate: 40.7 },
    { name: "断幺九", count: 101, rate: 22.2, leagueAvgRate: 20.12 }
]);
```

**布局特性：**
- 使用两列布局（CSS columns）
- 比率保留2位小数

---

### 9. `createExhaustiveDrawSection(exhaustiveDraw)`

生成流局听牌统计部分。

**参数：**
```javascript
exhaustiveDraw = {
    totalDraws: number,           // 总流局次数
    tenpaCount: number,           // 听牌次数
    tenpaRate: number,            // 听牌率
    leagueAvgTenpaRate: number    // 联盟平均听牌率
}
```

**示例：**
```javascript
const exhaustiveHtml = createExhaustiveDrawSection({
    totalDraws: 284,
    tenpaCount: 136,
    tenpaRate: 47.9,
    leagueAvgTenpaRate: 46.3
});
```

---

## 完整使用示例

### 示例1：生成单个玩家卡片

```javascript
// 准备完整的玩家数据
const playerData = {
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
            ippatsu: { count: 39, rate: 16.7, leagueAvgRate: 20.4 },
            uraDora: { count: 77, rate: 32.9, leagueAvgRate: 30.6 }
        },
        meld: { count: 177, avgPoints: 4633, leagueAvgPoints: 4640 },
        damaten: { count: 44, avgPoints: 7166, leagueAvgPoints: 6736 }
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
            totalPointDiff: 472100
        }
    ],
    yakuStats: [
        { name: "立直", count: 233, rate: 51.21, leagueAvgRate: 46.79 },
        { name: "役牌", count: 160, rate: 35.16, leagueAvgRate: 40.7 }
    ],
    exhaustiveDraw: {
        totalDraws: 284,
        tenpaCount: 136,
        tenpaRate: 47.9,
        leagueAvgTenpaRate: 46.3
    }
};

// 生成HTML
const html = createPlayerCard(playerData);

// 插入到页面
document.getElementById('player-container').innerHTML = html;
```

### 示例2：批量生成多个玩家卡片

```javascript
const playersData = [
    { playerName: "santi", /* ... */ },
    { playerName: "姫野婭也", /* ... */ },
    { playerName: "南美雀后", /* ... */ }
];

// 生成所有玩家卡片
const allPlayersHtml = playersData
    .map(player => createPlayerCard(player))
    .join('\n');

// 插入到页面
document.getElementById('all-players').innerHTML = allPlayersHtml;
```

### 示例3：仅生成特定部分

```javascript
// 仅生成名次分布图
const rankBarsHtml = createRankBars({
    rank1: { count: 48, percentage: 25.95 },
    rank2: { count: 42, percentage: 22.7 },
    rank3: { count: 56, percentage: 30.27 },
    rank4: { count: 39, percentage: 21.08 }
});

// 仅生成对战情况表格
const matchupsHtml = createMatchupsTable([
    { opponent: "姫野婭也", gameCount: 106, winRate: 56.6, /* ... */ }
]);
```

---

## 注意事项

1. **数据格式**：确保传入的数据格式与文档一致，特别注意数值类型
2. **可选字段**：`winStats.tsumoOnly` 和 `matchups[].hasLink` 是可选字段
3. **小数精度**：比率和平均值会自动格式化为适当的小数位数
4. **CSS依赖**：生成的HTML依赖现有的CSS样式类，确保CSS文件已正确加载
5. **联盟平均值**：所有联盟平均值都使用 `<span class="league-avg">` 包裹

---

## 样式类名参考

生成的HTML使用以下CSS类名：

- `.player-card` - 玩家卡片容器
- `.stats-grid` - 统计网格
- `.stat-item` - 单个统计项
- `.stat-label` - 统计标签
- `.stat-value` - 统计值
- `.rank-bars` - 名次条形图容器
- `.rank-bar` - 单个名次条
- `.bar-container` - 条形图容器
- `.bar` - 条形图主体
- `.bar-1`, `.bar-2`, `.bar-3`, `.bar-4` - 不同名次的颜色
- `.summary-box` - 摘要框
- `.stats-table` - 统计表格
- `.vs-table` - 对战表格
- `.yaku-list` - 手役列表
- `.league-avg` - 联盟平均值
- `.rate-good` - 良好比率（绿色）
- `.rate-bad` - 不良比率（红色）
- `.rate-neutral` - 中性比率（灰色）
- `.positive` - 正值（绿色）
- `.negative` - 负值（红色）
- `.neutral` - 零值（灰色）

---

## 兼容性

- 支持现代浏览器（Chrome, Firefox, Safari, Edge）
- 可在Node.js环境中使用（通过 `module.exports`）
- 不依赖第三方库

---

## 许可

本代码为M-League项目的一部分，遵循项目许可协议。
