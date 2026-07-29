# Santi League 开发笔记

## 最新更新 (2026-07-30)

本轮更新围绕 S-League 展开，核心思路是**让 S-League 彻底独立于 M-League 的渲染逻辑**（配色、标签页结构、Rating概念都不同），同时保留对底层数据处理基础设施（player_stats、summarize_v23、extract_honor_games）的复用。

### 1. S-League 专属内容生成器

新增 `src/s_league/content.py`，S-League 页面不再调用 `generate_m_league_tabs.py` / `generators/content_generators.py` 里 M-League 共用的排名和牌谱历史生成函数，而是有一套自己的实现：

- `generate_recent_games_content_s_league()` — 牌谱历史表格
- `generate_ranking_content_s_league()` — 总排名
- `generate_top5_leaderboards_content_s_league()` — 排行榜
- `generate_finals_content_s_league()` — 决定战

**原因**：M-League 的这些函数里大量硬编码了 Rating(R值) 相关的列和蓝紫配色 `#667eea`/`#764ba2`，直接复用会把 R值概念和配色一起带进来，还会因为共享同一份函数而牵连到 M-League（改坏一处两边都炸）。拆成独立文件后两边可以完全独立演化。

配套新增模板文件：`src/templates/html/s_league.html`、`src/templates/css/s_league.css`（从 `m_league.html`/`.css` 复制后精简/改色，而非直接引用）。页面生成入口：`generators/page_generators.py` 中的 `generate_s_league_page()`。

### 2. 移除 Rating(R值) 概念，改用纯总分体系

S-League 不使用 M-League 的 Tenhou-R 算法，牌谱历史/总排名/排行榜/决定战全部改成基于实际得点（pt）：

- 牌谱历史表格列：`玩家 | 局前总分 | 最终得分 | 点数变化(pt) | 局后总分`（局前/局后总分是把每局的 pt 变化按别名合并累加得到的，逻辑在 `content.py` 的 `_compute_running_score_totals()`）
- 点击某个玩家可以看到他的「总分变化曲线」（复用 Chart.js，逻辑同原来的 Rating 曲线，只是把 y 轴换成总分）
- 总排名按「总点数」（`stats_dict[name]['total_score']`）排名，不再有按 Rating/总得分切换的选项
- **注意换算**：总排名里的总分要 `/1000` 显示才能和牌谱历史的 pt 单位对齐（`content.py` 的 `_format_total_score()`），因为 `player_stats.py` 里 `total_score` 字段本身是没除以1000的原始点数

### 3. 决定战 & 排行榜 两个新标签页

**决定战**（`generate_finals_content_s_league`）：一张表，每行一个进决定战的选手，每个半庄对应"名次+分数"两列，最右侧总分（未除以1000，是直接的原始得点总和），按总分降序排列。数据源独立于常规赛：赛季配置新增 `finals_folder` 字段（如 `game-logs/s-league/s1-finals`），和 `data_folder` 完全分开，避免决定战牌谱被算进常规赛统计。处理逻辑在 `data_processor.py` 的 `process_finals_data()`。没有数据时显示"决定战尚未开始，敬请期待"。

**排行榜**（`generate_top5_leaderboards_content_s_league`）：4个 Top5 小榜单——1位率、避四率（=100%-4位率）、出勤半庄数、最高得点。1位率/避四率仅统计 ≥10半庄的正式排名玩家（避免小样本失真），出勤半庄数和最高得点不设门槛（这两个本身就是"打得多/单局爆发力强"的直接体现，不需要过滤）。

总排名页顶部加了一行提示："前四名（正式排名，≥10半庄）将进入S-League最高位决定战"，呼应决定战规则。

### 4. 配色调整

S-League 主题色从高饱和度的 `#e74c3c`/`#c0392b` 换成了低饱和度的陶土红 `#c15b42`/`#9c4732`（用户从5个降饱和度方案里选的）。改色时用 `sed` 在 `config.py`、`templates.py`、`content.py`、`s_league.css` 四个文件里统一替换，含 RGB 形式的 `231, 76, 60`（用于 `rgba()`）也一并换成 `193, 91, 66`。

### 5. 赛季状态管理与自动同步

**赛季语义调整**：S0 从"首届"改成了纯测试赛季（`description: '测试用'`，不再写虚构的"2026年1月"开始时间，改成注明测试用的是哪段真实牌谱：2026年5月22日-7月22日）。真正的首届最高位战是新建的 **S1 赛季**（`src/s_league/config.py`），时间窗口 2026年7月23日0点 - 8月23日0点。

**赛季卡片状态**从原来单纯看 `file_count > 0` 判断"进行中/即将开始"，改成赛季配置里显式的 `status` 字段（`ended`/`ongoing`/`upcoming`），卡片文案变成「已结束 · 101半庄」「进行中 · 2半庄」这种"状态+局数"组合展示（`templates.py` 的 `generate_index_template()`，新增 CSS class `.status-ended`）。

**自动同步牌谱**（`data_processor.py` 的 `sync_season_data()`）：赛季配置里新增 `start_time`/`end_time`（如 `'2026-07-23 00:00:00'`），`generate_all_s_league_pages()` 每次运行时会先扫描 `game-logs/m-league/` 全部牌谱，把真实时间戳（读JSON `title[1]`，按UTC+2显示时间）落在赛季窗口内、且还没同步过的文件复制进赛季的 `data_folder`，按文件名去重，天然幂等。只有配置了 `start_time` 的赛季才会自动同步（S0 没配置，保持手工维护的测试快照不被后续新牌谱污染）。

**副作用**：为了让 `sync_season_data()` 复用日期解析逻辑，把 `extract_latest_date()` 里内联的时间戳解析代码抽成了共享的 `_read_display_timestamp()` 私有函数。

### 6. 顺带修复的Bug：日期解析用了过时的文件名格式

`src/extract_honor_games.py` 的 `extract_date_from_filename()` 和 `s_league/data_processor.py` 原来的 `extract_latest_date()` 都用正则 `(\d+)_(\d+)_(\d+)` 匹配文件名里的日期，这是旧的 `MM_DD_YYYY...` 命名格式；但现在牌谱文件名是 `YYYY-MM-DD_HHMMSS_name.json`，正则完全不匹配，导致荣誉牌谱卡片的日期和赛季页头的"数据更新至"日期都显示不出来（要么是原始文件名，要么是空）。

**修复**：改成直接读 JSON 内的 `title[1]` 时间戳（和 `utils/helpers.py` 的 `sort_files_by_date()`、`generate_website.py` 的 `extract_recent_games()` 用的是同一个可靠数据源），并统一做 UTC+2 时区调整。**这个 bug 同时影响 M-League 的荣誉牌谱页面**（`docs/honor_games.json` 是用同一个 `extract_honor_games.py` 生成的），修复后如果重新跑一遍 M-League 的荣誉牌谱生成，日期显示也会一并修好。

---

## S-League 初版搭建 (2026-07-21)

### 1. 时区显示调整

**问题**: 牌谱文件时间戳为UTC+0，但网页需要显示UTC+2时间

**解决方案**:
- 修改 `src/generate_website.py`
- 导入 `timedelta` 模块
- 在显示时间前加2小时：`display_timestamp = timestamp + timedelta(hours=2)`

**代码位置**: `src/generate_website.py:271-276`
```python
# 调整时区：UTC+0 -> UTC+2
display_timestamp = timestamp + timedelta(hours=2)

all_game_details.append({
    'date': display_timestamp.strftime("%Y年%m月%d日 %H:%M"),
    'date_en': display_timestamp.strftime("%Y-%m-%d %H:%M"),
    ...
})
```

**影响范围**: 所有联赛（M-League、EMA、S-League）的最近牌谱时间显示

---

### 2. S-League 最高位战功能

**功能描述**: 新增S-League最高位战系统，支持多赛季管理

**赛制规则**:
- 采用M-League规则（25000起始分，uma: 45/5/-15/-35）
- 每赛季2个月常规赛
- 前4名（至少10场）进入最高位决定战
- 决定战5个半庄，最高分获胜

**模块结构**:
```
src/s_league/
├── __init__.py           # 模块导出
├── config.py             # 赛季配置
├── data_processor.py     # 数据处理
├── page_generator.py     # 页面生成
└── templates.py          # HTML模板

game-logs/s-league/
└── s0/                   # S0赛季数据

docs/s-league/
├── index.html           # 赛季选择页（中文）
├── index-en.html        # 赛季选择页（英文）
├── s0.html              # S0赛季统计（中文）
└── s0-en.html           # S0赛季统计（英文）
```

**集成点**:
- `src/generate_website.py:1699-1708` - S-League页面生成调用
- `src/config/translations.py:24-25, 138-139` - 翻译文本
- `src/templates/html/index.html:38-42` - 首页导航卡片
- `src/generators/page_generators.py:52-54` - 首页链接参数

---

### 3. Bug修复

#### Bug #1: update_all.sh 不会跑完
**原因**:
1. 空 `links.txt` 导致 `download_paipu.sh` 挂起
2. `organize_logs.py` 移动重复文件到errors时返回exit code 1
3. `update_all.sh` 的 `set -e` 导致遇到非零退出码就停止

**修复**:
- `download_paipu.sh:65-70` - 检测空链接并跳过
- `src/organize_logs.py:537-543` - 注释掉错误退出码检查

#### Bug #2: 牌谱重复计算
**原因**: `auto_classify_files()` 扫描了 `s-league` 文件夹，将其中的文件移到了 `m-league`

**修复**: `src/organize_logs.py:432-434` - 跳过 `s-league` 文件夹
```python
# 跳过 errors、sanma 和 s-league 文件夹
if 'errors' in root or 'sanma' in root or 's-league' in root:
    continue
```

#### Bug #3: M-League 重复文件
**原因**: 98个文件同时存在于根目录和日期文件夹

**修复**: 删除根目录中的重复文件，保留日期文件夹中的版本

---

### 4. UI调整

- 隐藏上传按钮：`src/templates/html/index.html:44-50` 注释掉上传功能卡片
- S-League介绍文本：从"关于S-League"改为"S-League赛制"
- 添加M-League规则说明到赛制介绍中

---

## 当前文件统计

- **M-League**: 615个牌谱文件
- **EMA**: 20个牌谱文件
- **S-League**: 0个文件（已恢复到git存档点）
- **Errors**: 3个文件

---

## Git状态

已修改但未提交的文件：
- 代码文件：
  - `src/generate_website.py` - 时区调整
  - `src/organize_logs.py` - 跳过s-league文件夹
  - `src/config/translations.py` - S-League翻译
  - `src/generators/page_generators.py` - S-League链接
  - `src/templates/html/index.html` - 隐藏上传按钮
  - `download_paipu.sh` - 空链接检查

- 新增文件：
  - `src/s_league/` - S-League模块
  - `docs/s-league/` - S-League页面

- game-logs已恢复到HEAD

---

## 待办事项

- [ ] 为S0赛季准备测试数据（复制过去2个月M-League牌谱）
- [ ] 测试S-League页面生成
- [ ] 提交代码到git
- [ ] 部署到GitHub Pages

---

## 技术要点

### 时间处理
- 牌谱文件时间戳存储为UTC+0
- 网页显示时调整为UTC+2
- 不修改原始文件，仅在显示层调整

### S-League数据隔离
- S-League文件夹独立管理，不参与自动分类
- 使用M-League规则但数据完全隔离
- 支持多赛季独立统计

### 模块化设计
- 配置、数据处理、页面生成、模板分离
- 复用现有基础设施（player_stats, template renderers）
- 最小化对现有代码的影响
