# 上传功能快速开始指南

## 🚀 3 分钟快速部署（无需登录）

### 前置要求
- ✅ Firebase CLI 已安装（已完成）
- ✅ Google 账户

### 1. 创建 Firebase 项目（2 分钟）

访问 https://console.firebase.google.com/

1. 点击"添加项目"
2. 输入项目名称：`santi-league`
3. 完成创建

### 2. 启用服务（1 分钟）

在 Firebase Console 中：

**Firestore:**
1. 左侧菜单 → Firestore Database → Create Database
2. 选择"生产模式" → 选择地区 → 启用

**Storage:**
1. 左侧菜单 → Storage → Get Started
2. 接受规则 → 选择地区 → 完成

> ⚠️ **注意**：无需启用 Authentication，本项目支持匿名上传！

### 3. 获取配置（1 分钟）

1. Firebase Console → ⚙️ 项目设置
2. 滚动到"您的应用"
3. 点击 **</>**（Web 图标）
4. 输入应用名称 → 注册应用
5. **复制** `firebaseConfig` 代码

### 4. 配置本地文件（1 分钟）

**编辑 `docs/upload.html`** 第 346 行：

```javascript
const firebaseConfig = {
    // 粘贴你复制的配置
};
```

**编辑 `.firebaserc`：**

```json
{
  "projects": {
    "default": "你的项目ID"
  }
}
```

### 5. 部署（2 分钟）

```bash
# 安装 Functions 依赖
cd functions && npm install && cd ..

# 登录 Firebase
firebase login

# 部署所有服务
firebase deploy
```

### 6. 测试

访问：`https://你的项目ID.web.app/upload.html`

1. ✅ 无需登录，页面显示今日剩余配额
2. ✅ 选择联赛并上传 JSON 文件
3. ✅ 完成！配额自动更新

## 特性

- ✅ **无需登录** - 任何人都可以直接上传
- ✅ **简单快速** - 3 分钟完成部署
- ✅ **每日限额** - 每天最多上传 50 个文件
- ✅ **完全免费** - Firebase 免费套餐完全够用
- ✅ **安全限制** - 文件大小和类型限制
- ✅ **可选昵称** - 上传者可以留下昵称（可选）

## 安全说明

虽然允许匿名上传，但仍有以下安全措施：

1. ✅ **每日限额** - 每天最多 50 个文件（UTC 时区）
2. ✅ 只允许 JSON 格式
3. ✅ 文件大小限制 5 MB
4. ✅ 自动验证文件格式
5. ✅ 防止恶意文件上传
6. ✅ 可追踪上传者昵称（可选）

## 防滥用建议（可选）

如果担心滥用，可以添加：

1. **App Check** - Firebase 的应用验证
2. **reCAPTCHA** - 人机验证
3. **IP 限制** - 限制单个 IP 上传频率
4. **文件审核** - 管理员审核后才显示

详细指南请查看：`SETUP_UPLOAD_FEATURE.md`

## 常见问题

**Q: Functions 部署失败？**
A: 需要升级到 Blaze 计划（仍有免费额度，不会收费）

**Q: 上传失败？**
A: 确保已部署 Storage 规则：`firebase deploy --only storage`

**Q: 是否安全？**
A: 有基本安全限制（文件类型、大小），足够社群使用

**Q: 如何防止滥用？**
A: 已内置每日 50 个文件的限制。如需更严格控制，可添加 Firebase App Check 或 reCAPTCHA（见详细文档）

**Q: 每日配额何时重置？**
A: 每天 UTC 00:00 自动重置。修改配额限制请查看 `SETUP_UPLOAD_ANONYMOUS.md`

## 下一步

详细设置指南请查看：`SETUP_UPLOAD_FEATURE.md`
