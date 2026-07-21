# Santi League 开发笔记

## 最新更新 (2026-07-21)

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
