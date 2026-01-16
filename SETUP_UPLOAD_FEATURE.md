# 上传功能设置指南

本指南将帮助你配置和部署 Santi League 的用户上传功能。

## 📋 功能概述

添加上传功能后，用户可以：
- ✅ 通过 Google 账户登录
- ✅ 上传麻将牌谱 JSON 文件
- ✅ 自动验证和处理文件
- ✅ 查看上传历史和状态

系统会自动：
- ✅ 验证上传的 JSON 格式
- ✅ 存储文件到 Firebase Storage
- ✅ 记录上传元数据到 Firestore
- ✅ 标记文件为待处理状态

## 🚀 完整设置步骤

### 步骤 1: 创建 Firebase 项目

1. 访问 [Firebase Console](https://console.firebase.google.com/)
2. 点击"添加项目"
3. 输入项目名称（例如：`santi-league`）
4. 选择是否启用 Google Analytics（推荐启用）
5. 完成项目创建

### 步骤 2: 启用必要的 Firebase 服务

在 Firebase Console 中启用以下服务：

#### 2.1 启用 Authentication（认证）

1. 在左侧菜单选择 **Authentication**
2. 点击"开始使用"
3. 选择"Sign-in method"标签页
4. 启用 **Google** 登录提供商
5. 输入项目支持电子邮件
6. 点击"保存"

#### 2.2 启用 Firestore Database（数据库）

1. 在左侧菜单选择 **Firestore Database**
2. 点击"创建数据库"
3. 选择"生产模式"（我们将使用自定义规则）
4. 选择数据库位置（推荐选择离你最近的地区）
5. 点击"启用"

#### 2.3 启用 Storage（文件存储）

1. 在左侧菜单选择 **Storage**
2. 点击"开始使用"
3. 接受默认安全规则（我们将稍后覆盖）
4. 选择存储位置（与 Firestore 相同地区）
5. 点击"完成"

#### 2.4 启用 Functions（云函数）

Functions 会在后续步骤中通过 CLI 部署时自动启用。

### 步骤 3: 获取 Firebase 配置

1. 在 Firebase Console，点击左上角的齿轮图标 ⚙️
2. 选择"项目设置"
3. 向下滚动到"您的应用"部分
4. 点击 **</>**（Web 应用）图标
5. 输入应用昵称（例如：`Santi League Web`）
6. **不要**选中"同时设置 Firebase Hosting"（我们已经配置好了）
7. 点击"注册应用"
8. 复制 Firebase SDK 配置代码，看起来像这样：

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  authDomain: "your-project-id.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project-id.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef123456"
};
```

### 步骤 4: 配置 Web 应用

#### 4.1 更新 upload.html

编辑 `docs/upload.html` 文件，找到这一行：

```javascript
// TODO: 替换为你的 Firebase 配置
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
};
```

将其替换为步骤 3 中获取的实际配置。

#### 4.2 更新 .firebaserc

编辑项目根目录下的 `.firebaserc` 文件：

```json
{
  "projects": {
    "default": "your-actual-project-id"
  }
}
```

将 `your-actual-project-id` 替换为你的实际 Firebase 项目 ID。

### 步骤 5: 安装 Cloud Functions 依赖

在项目根目录运行：

```bash
cd functions
npm install
cd ..
```

### 步骤 6: 登录 Firebase CLI

```bash
firebase login
```

这会打开浏览器窗口，用你的 Google 账户登录。

### 步骤 7: 部署所有服务

#### 7.1 部署 Storage 规则

```bash
firebase deploy --only storage
```

#### 7.2 部署 Firestore 规则

```bash
firebase deploy --only firestore:rules
```

#### 7.3 部署 Cloud Functions

```bash
firebase deploy --only functions
```

这可能需要几分钟时间。首次部署时，Firebase 可能会要求你升级到 Blaze（按量计费）计划，但**仍然有免费额度**，不会产生费用（除非超出额度）。

#### 7.4 部署网站

```bash
firebase deploy --only hosting
```

#### 7.5 一次性部署所有服务

你也可以一次性部署所有服务：

```bash
firebase deploy
```

### 步骤 8: 验证部署

部署完成后，访问你的网站：

```
https://your-project-id.web.app
```

1. 点击"上传牌谱"卡片
2. 使用 Google 账户登录
3. 选择联赛类型
4. 上传一个测试 JSON 文件
5. 检查上传是否成功

### 步骤 9: 验证 Cloud Functions

在 Firebase Console 中：

1. 选择左侧菜单的 **Functions**
2. 确认以下函数已部署：
   - `onFileUploaded` - 自动验证上传的文件
   - `scheduledRegenerateSite` - 定期检查新文件
   - `triggerRegenerate` - 手动触发重新生成
   - `getUploadStats` - 获取上传统计

### 步骤 10: 验证数据

在 Firebase Console 中：

1. 选择 **Firestore Database**
2. 应该看到 `game-logs` 集合
3. 查看上传的文件元数据

## 📁 项目文件结构

```
santi-league.github.io/
├── docs/                       # 网站文件
│   ├── index.html             # 主页（已添加上传链接）
│   ├── index-en.html          # 英文主页（已添加上传链接）
│   ├── upload.html            # 上传页面 ⭐ 新增
│   └── ...
├── functions/                  # Cloud Functions ⭐ 新增
│   ├── index.js               # 函数代码
│   └── package.json           # 依赖配置
├── src/                        # Python 脚本
│   └── generate_website.py    # 生成网站脚本
├── firebase.json               # Firebase 配置
├── .firebaserc                 # Firebase 项目配置
├── storage.rules               # Storage 安全规则 ⭐ 新增
├── firestore.rules             # Firestore 安全规则 ⭐ 新增
└── SETUP_UPLOAD_FEATURE.md     # 本文件
```

## 🔧 自定义配置

### 限制上传文件大小

编辑 `storage.rules` 文件：

```javascript
// 当前限制：5 MB
request.resource.size < 5 * 1024 * 1024

// 改为 10 MB：
request.resource.size < 10 * 1024 * 1024
```

重新部署：
```bash
firebase deploy --only storage
```

### 限制上传频率

编辑 `firestore.rules` 文件，添加速率限制（需要额外逻辑）。

### 只允许特定用户上传

编辑 `storage.rules` 文件：

```javascript
// 只允许特定电子邮件上传
allow write: if request.auth != null
             && request.auth.token.email in ['user1@example.com', 'user2@example.com']
```

## 🔄 处理上传的文件

目前，上传的文件会被验证并存储，但不会自动更新网站统计。有几种方式处理：

### 方案 A: 手动处理（简单）

1. 在 Firebase Console 中查看 Firestore 的 `game-logs` 集合
2. 手动下载新上传的文件
3. 将文件放到本地 `game-logs` 目录
4. 运行 `python src/generate_website.py`
5. 运行 `firebase deploy --only hosting`

### 方案 B: 使用 GitHub Actions（推荐）

创建一个 GitHub Actions 工作流：

1. 监听 Firestore 变化（通过 webhook）
2. 自动从 Storage 下载新文件
3. 运行 Python 脚本重新生成网站
4. 自动部署到 Firebase Hosting

（需要额外配置，可以另外提供详细指南）

### 方案 C: Cloud Functions 中运行 Python（高级）

在 Cloud Functions 中集成 Python 运行时：

1. 使用 Docker 容器运行 Python
2. 在 Functions 中触发 Python 脚本
3. 自动部署更新的 HTML

（需要自定义 Cloud Functions 运行时，较复杂）

## 💰 成本估算

基于免费套餐：

### 每天上传 10 个文件的情况：

**Storage:**
- 使用量：10 × 20 KB × 30 天 = 6 MB ✅
- 免费额度：5 GB（远远够用）

**Firestore:**
- 写入：10 × 2（文件元数据 + 验证状态更新）= 20 次/天
- 免费额度：20,000 次/天 ✅

**Functions:**
- 调用：10 次/天 = 300 次/月
- 免费额度：125,000 次/月 ✅

**结论：完全免费！** 🎉

### 超出免费额度的情况：

只有在以下情况下才会收费：
- 每天上传超过 1,000 个文件
- 存储超过 5 GB
- 每天 Firestore 操作超过 20,000 次

即使超出，费用也很低（Storage: $0.026/GB，Firestore: $0.06/100K 读取）

## 🐛 故障排除

### 上传失败："Permission denied"

**原因：** Storage 规则未正确部署

**解决：**
```bash
firebase deploy --only storage
```

### 无法登录："Popup blocked"

**原因：** 浏览器阻止弹出窗口

**解决：** 允许网站弹出窗口

### Functions 部署失败

**原因：** 需要升级到 Blaze 计划

**解决：**
1. 访问 Firebase Console
2. 选择左下角的"升级"
3. 选择 Blaze（按量计费）计划
4. 设置预算提醒（例如 $5/月）

注意：**不会立即收费**，免费额度仍然适用！

### 文件上传后没有出现在 Firestore

**原因：** Cloud Functions 未正确部署或执行失败

**检查：**
1. 访问 Firebase Console → Functions
2. 查看 `onFileUploaded` 的日志
3. 检查是否有错误消息

### 无法访问上传页面

**原因：** Hosting 未部署或 upload.html 未包含

**解决：**
```bash
firebase deploy --only hosting
```

## 📊 监控和管理

### 查看上传统计

访问 Cloud Function 提供的 API：

```
https://your-region-your-project.cloudfunctions.net/getUploadStats
```

### 查看 Functions 日志

```bash
firebase functions:log
```

或在 Firebase Console → Functions → 选择函数 → Logs

### 查看上传的文件

Firebase Console → Storage → `game-logs/`

### 查看文件元数据

Firebase Console → Firestore Database → `game-logs` 集合

## 🔐 安全建议

1. **定期检查 Storage** - 确保没有恶意文件上传
2. **监控 Firestore 使用量** - 设置预算提醒
3. **审查安全规则** - 根据需要调整访问权限
4. **备份数据** - 定期导出 Firestore 数据
5. **限制管理员权限** - 只给可信用户管理权限

## ✅ 完成检查清单

- [ ] Firebase 项目已创建
- [ ] Authentication（Google）已启用
- [ ] Firestore Database 已创建
- [ ] Storage 已启用
- [ ] Firebase 配置已复制到 upload.html
- [ ] .firebaserc 已更新项目 ID
- [ ] Functions 依赖已安装（npm install）
- [ ] 已登录 Firebase CLI
- [ ] Storage 规则已部署
- [ ] Firestore 规则已部署
- [ ] Cloud Functions 已部署
- [ ] Hosting 已部署
- [ ] 上传功能已测试
- [ ] 文件出现在 Firestore
- [ ] Functions 日志无错误

## 🎓 下一步

完成基本设置后，你可以：

1. **自动化处理** - 设置 GitHub Actions 自动处理上传的文件
2. **添加管理面板** - 创建管理员界面查看和管理上传
3. **优化 UI** - 改进上传页面的用户体验
4. **添加通知** - 上传成功后发送邮件或推送通知
5. **批量处理** - 允许一次上传多个文件

## 📞 获取帮助

如果遇到问题：

1. 检查 Firebase Console 中的日志
2. 运行 `firebase functions:log` 查看 Functions 日志
3. 查看浏览器控制台的错误信息
4. 参考 [Firebase 文档](https://firebase.google.com/docs)

## 📚 参考资源

- [Firebase Authentication 文档](https://firebase.google.com/docs/auth)
- [Cloud Firestore 文档](https://firebase.google.com/docs/firestore)
- [Cloud Storage 文档](https://firebase.google.com/docs/storage)
- [Cloud Functions 文档](https://firebase.google.com/docs/functions)
- [Firebase Security Rules](https://firebase.google.com/docs/rules)
