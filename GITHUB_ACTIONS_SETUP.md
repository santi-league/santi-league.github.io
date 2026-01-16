# GitHub Actions 自动化配置指南

本文档说明如何配置 GitHub Actions，实现自动从 Firebase Storage 下载新的牌谱文件，并重新生成网站。

## 📋 前置要求

- GitHub 仓库已创建
- Firebase 项目已配置
- 本地已通过 `firebase login` 登录

## 🔧 配置步骤

### 1. 生成 Firebase Service Account 密钥

1. 访问 [Firebase Console](https://console.firebase.google.com/)
2. 选择你的项目 `santi-league`
3. 点击左侧菜单的 ⚙️ **Settings** → **Project settings**
4. 切换到 **Service accounts** 标签页
5. 点击 **Generate new private key**
6. 下载 JSON 密钥文件（**注意：妥善保管，不要泄露**）

### 2. 生成 Firebase CI Token

在本地终端运行：

```bash
firebase login:ci
```

这会生成一个 token，复制保存备用。

### 3. 配置 GitHub Secrets

1. 打开你的 GitHub 仓库页面
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，添加以下两个 secrets：

#### Secret 1: `FIREBASE_SERVICE_ACCOUNT`
- **Name**: `FIREBASE_SERVICE_ACCOUNT`
- **Value**: 粘贴步骤 1 下载的 JSON 文件的**完整内容**

#### Secret 2: `FIREBASE_TOKEN`
- **Name**: `FIREBASE_TOKEN`
- **Value**: 粘贴步骤 2 生成的 token

### 4. 启用 GitHub Actions

1. 在仓库页面点击 **Actions** 标签
2. 如果 Actions 被禁用，点击 **I understand my workflows, go ahead and enable them**

## 🚀 使用方式

### 自动运行

GitHub Actions 会自动在以下时间运行：
- ⏰ 每 6 小时运行一次（UTC 时间 00:00, 06:00, 12:00, 18:00）

### 手动触发

1. 打开仓库的 **Actions** 标签
2. 点击左侧的 **Process Game Logs and Update Website**
3. 点击右侧的 **Run workflow** 按钮
4. 选择分支（通常是 `main`）
5. 点击绿色的 **Run workflow** 按钮

## 📊 工作流程说明

当 workflow 运行时，会执行以下步骤：

1. **Checkout repository** - 检出代码
2. **Setup Python** - 安装 Python 3.11
3. **Install dependencies** - 安装所需的 Python 包
4. **Setup Node.js** - 安装 Node.js
5. **Install Firebase CLI** - 安装 Firebase 命令行工具
6. **Authenticate** - 使用 service account 认证
7. **Download files** - 从 Firebase Storage 下载新文件
8. **Generate website** - 运行 `generate_website.sh`
9. **Deploy** - 部署到 Firebase Hosting
10. **Commit changes** - 提交更改回仓库

## 🔍 查看运行结果

1. 打开 **Actions** 标签
2. 点击最近的 workflow run
3. 查看各个步骤的日志

## ⚠️ 常见问题

### 问题：认证失败

**解决方法**：
- 检查 `FIREBASE_SERVICE_ACCOUNT` secret 是否正确粘贴了完整的 JSON 内容
- 确保 JSON 格式正确，没有多余的空格或换行

### 问题：下载失败

**解决方法**：
- 确保 Service Account 有 Storage Object Viewer 权限
- 检查 bucket 名称是否正确

### 问题：部署失败

**解决方法**：
- 检查 `FIREBASE_TOKEN` 是否正确
- 尝试重新生成 token：`firebase login:ci`

## 🔒 安全建议

- ✅ 永远不要将 service account JSON 文件提交到代码仓库
- ✅ 不要在代码中硬编码 token
- ✅ 定期轮换 service account 密钥
- ✅ 使用最小权限原则，只授予必要的权限

## 📝 自定义配置

如果需要修改运行频率，编辑 `.github/workflows/process-game-logs.yml`：

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 每6小时
    # 修改为 '0 */1 * * *' 则为每小时
    # 修改为 '0 0 * * *' 则为每天凌晨
```

## 🎯 验证配置

配置完成后，可以手动触发一次 workflow 进行测试：

1. 上传一个测试文件到 Firebase Storage
2. 手动运行 GitHub Actions workflow
3. 检查是否成功下载、处理并部署

---

**配置完成！** 🎉

现在你的网站会自动处理新上传的牌谱文件了。
