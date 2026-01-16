# Vercel 部署指南

## 🔐 环境变量配置

在 Vercel 项目设置 (Settings → Environment Variables) 中添加以下变量：

| 变量名 | 值 | 来源 |
|--------|-----|------|
| `FEISHU_APP_ID` | `cli_a9d4c8d410f89bc7` | 飞书开放平台 |
| `FEISHU_APP_SECRET` | `pxgy2wigikb4FSlLcmlSshzwwx0rpHsa` | 飞书开放平台 |
| `FEISHU_BASE_ID` | `JRJAbum6yaS1SDsYMYPcTvJQn1b` | 多维表格 URL |
| `FEISHU_TABLE_ID` | `tblvdORsM2Sd9upd` | 多维表格 URL |

> ⚠️ **安全提醒**：以上值仅供参考，请在 Vercel 后台直接配置，不要提交到 Git。

---

## 📦 部署步骤

### 1. 推送代码到 GitHub
```bash
git add .
git commit -m "Add Feishu API integration"
git push
```

### 2. 连接 Vercel
1. 访问 [vercel.com](https://vercel.com)
2. Import Git Repository
3. 选择 `Chora` 仓库
4. **Root Directory**: `frontend`
5. 点击 Deploy

### 3. 配置环境变量
1. 进入 Project Settings
2. 选择 Environment Variables
3. 添加上述 4 个变量
4. 重新部署 (Deployments → Redeploy)

---

## 🧪 本地测试

本地开发时，API 路由不可用，会自动回退到静态 JSON：

```bash
cd frontend/public
python3 -m http.server 8081
```

如需本地测试 API，可安装 Vercel CLI：

```bash
npm i -g vercel
cd frontend
vercel dev
```

---

## 📁 项目结构

```
frontend/
├── api/
│   └── content.js     # ← Serverless Function (调用飞书 API)
├── public/
│   ├── index.html
│   ├── app.js         # ← 前端 (优先调用 /api/content)
│   ├── styles.css
│   └── data/
│       └── content.json  # ← 静态备份 (本地开发用)
├── vercel.json
└── package.json
```

---

## 🔄 数据流

```
飞书多维表格
     ↓
Vercel API (/api/content)  ← 密钥安全存储在环境变量
     ↓
前端渲染
```

**实时同步**：飞书数据更新后，前端自动获取最新内容（缓存 5 分钟）。
