# 代码重构文档 (Code Refactoring Documentation)

## 概述 (Overview)

对 `generate_website.py` 进行了模块化重构，将HTML模板、CSS样式、翻译数据和辅助函数分离到独立的模块中。

The `generate_website.py` has been refactored into a modular structure, separating HTML templates, CSS styles, translations, and helper functions into independent modules.

## 新的目录结构 (New Directory Structure)

```
src/
├── generate_website.py          # 主生成脚本 (保留了原有功能)
├── generate_website.py.backup   # 原始备份文件
├── config/                      # 配置模块
│   ├── __init__.py
│   └── translations.py          # 多语言翻译配置
├── templates/                   # 模板模块
│   ├── __init__.py
│   ├── template_loader.py       # 模板加载器
│   ├── html/                    # HTML模板
│   │   ├── index.html           # 首页模板
│   │   ├── ema.html             # EMA页面模板
│   │   └── sanma_honor.html     # 三麻荣誉牌谱模板
│   └── css/                     # CSS样式文件
│       ├── index.css            # 首页样式
│       ├── ema.css              # EMA页面样式
│       └── sanma_honor.css      # 三麻荣誉牌谱样式
├── generators/                  # 页面生成器
│   ├── __init__.py
│   └── page_generators.py       # 页面生成函数
└── utils/                       # 工具函数
    ├── __init__.py
    └── helpers.py               # 辅助函数
```

## 主要改动 (Key Changes)

### 1. 配置模块 (Configuration Module)

**src/config/translations.py**
- 包含所有多语言翻译字典
- 提供 `get_translation(lang)` 函数
- 包含役种翻译映射

### 2. 模板系统 (Template System)

**src/templates/template_loader.py**
- `load_html_template(name)` - 加载HTML模板
- `load_css(name)` - 加载CSS文件
- `render_template(template, css, **kwargs)` - 渲染模板

**HTML模板** (src/templates/html/)
- 使用 `{variable}` 占位符
- 分离了HTML结构和业务逻辑

**CSS文件** (src/templates/css/)
- 独立的CSS样式文件
- 更易于维护和修改

### 3. 页面生成器 (Page Generators)

**src/generators/page_generators.py**
- `generate_index_page(lang)` - 生成首页
- `generate_ema_page(lang)` - 生成EMA页面
- `generate_sanma_honor_page(yakuman_games, lang)` - 生成三麻荣誉牌谱页面

### 4. 工具函数 (Utility Functions)

**src/utils/helpers.py**
- `sort_files_by_date(files)` - 按日期排序文件
- `format_percentage(value)` - 格式化百分比
- `format_number(value)` - 格式化数字
- `escape_html(text)` - HTML转义
- `get_latest_date_from_files(files)` - 获取最新日期

### 5. 主文件更新 (Main File Updates)

**src/generate_website.py**
- 导入新模块: `from config.translations import TRANSLATIONS`
- 导入页面生成器: `from generators.page_generators import *`
- 导入工具函数: `from utils.helpers import sort_files_by_date`
- 简化了页面生成函数，调用模块化组件

## 优点 (Benefits)

1. **代码组织** (Code Organization)
   - 清晰的模块划分
   - 易于定位和修改代码

2. **可维护性** (Maintainability)
   - HTML/CSS分离，更易修改样式
   - 翻译集中管理，添加语言更方便

3. **可重用性** (Reusability)
   - 模板可以在多个页面中重用
   - 工具函数可以被其他脚本使用

4. **可测试性** (Testability)
   - 独立模块便于单元测试
   - 减少耦合度

5. **扩展性** (Extensibility)
   - 添加新页面只需创建新模板和生成器
   - 添加新样式只需新增CSS文件

## 向后兼容性 (Backward Compatibility)

- 保留了所有原有的函数接口
- `generate_index_html(lang)` 等函数仍然可以调用
- 原始代码备份在 `generate_website.py.backup`

## 使用方法 (Usage)

生成网站的方式保持不变:
```bash
python src/generate_website.py
```

或使用shell脚本:
```bash
./generate_website.sh
```

## 注意事项 (Notes)

1. 所有新模块都需要 `__init__.py` 文件以成为Python包
2. HTML模板使用 `str.format()` 语法: `{variable}`
3. CSS文件通过 `template_loader.py` 动态注入到HTML中
4. 翻译键值保持一致，确保所有语言版本同步

## 未来改进 (Future Improvements)

1. 可以考虑使用 Jinja2 等更强大的模板引擎
2. 可以添加模板缓存机制提高性能
3. 可以将M-League页面也重构为模块化结构
4. 可以添加配置文件支持 (YAML/JSON)

## 测试 (Testing)

重构后的代码已通过测试:
- ✅ 成功生成所有HTML页面
- ✅ 样式和功能与重构前一致
- ✅ 多语言支持正常工作
- ✅ 文件大小和内容保持一致
