# Santi League 雀魂统计系统

雀魂麻将数据统计与展示系统

## 功能特性

- 📊 完整的对局数据统计
- 🎯 天凤R值计算系统
- 📈 手役统计分析
- 🌐 静态网页展示

## 使用方法

### 1. 统计数据分析

```bash
# 查看 M-League 统计（表格格式）
python player_stats.py game-logs/m-league -r --format table

# 导出为 JSON
python player_stats.py game-logs/m-league -r -o stats.json
```

### 2. 生成静态网站

```bash
python generate_website.py
```

生成的网站文件在 `docs/` 目录下：
- `index.html` - 首页
- `m-league.html` - M-League 统计页面
- `wrc.html` - WRC 统计页面（占位）

### 3. 部署到 GitHub Pages

1. 确保仓库设置中启用了 GitHub Pages
2. 设置源为 `docs` 文件夹
3. 推送代码：

```bash
git add docs/
git commit -m "Update statistics"
git push
```

## 统计项目

### 基础统计
- 对局数、小局数
- 天凤R值
- 总点数、平均顺位
- 名次分布（1/2/3/4位率）

### 和了统计
- 和了率、平均打点
- 立直和了（含一发率、里宝率）
- 副露和了
- 其他和了（门清荣和等）

### 立直 & 副露
- 立直率、副露率
- 立直后：和了率 / 流局率 / 放铳率 / 横移率
- 副露后：和了率 / 流局率 / 放铳率 / 横移率

### 放铳统计
- 放铳率、平均失点
- 放铳给各玩家的详细统计

### 手役统计
- 各种手役出现次数和比率
- 自动合并役牌（白/发/中/自风/场风）

### 流局统计
- 流局听牌率

## 文件说明

- `summarize_v23.py` - 牌谱解析核心
- `player_stats.py` - 统计计算与展示
- `generate_website.py` - 静态网站生成
- `batch_summarize_v23.py` - 批量处理工具
- `reverse_filenames.py` - 文件名倒序工具

## 天凤R值计算

采用天凤麻将的R值计算公式：

```
R值变动 = 试合数补正 × (对战结果 + 补正值) × スケーリング係数

- 对战结果: 1位+30, 2位+10, 3位-10, 4位-30
- 试合数补正: 400场以下 = 1 - 试合数×0.002, 400场以上 = 0.2
- 补正值: (桌平均R - 自己的R) / 40
- 初始R值: 1500
```

## 数据文件结构

```
game-logs/
  ├── m-league/
  │   ├── 10_1_2025_Tounament_South.json
  │   ├── 10_1_2025_Tounament_South (1).json
  │   └── ...
  └── wrc/
      └── ...
```

## License

MIT
