# 封面图片静态托管部署指南

本指南介绍如何将封面图片部署到 Vercel，使飞书多维表格能够正常显示封面。

## 前提条件

1. 安装 Node.js 和 npm
2. 注册 Vercel 账号: https://vercel.com/signup

## 部署步骤

### 1. 安装 Vercel CLI

```bash
npm install -g vercel
```

### 2. 登录 Vercel

```bash
vercel login
```

按提示完成登录（选择邮箱或 GitHub 登录）。

### 3. 部署前端

```bash
cd frontend
vercel --prod
```

首次部署时会提示：
- `Set up and deploy?` → 选择 `Y`
- `Which scope?` → 选择你的账户
- `Link to existing project?` → 选择 `N`
- `What's your project's name?` → 输入 `chora-covers`（或自定义名称）
- `In which directory is your code located?` → 直接回车（使用当前目录）

### 4. 获取部署域名

部署成功后，会显示类似：
```
✅ Production: https://chora-covers.vercel.app
```

### 5. 更新配置

编辑 `config/vercel.yaml`，将 `domain` 设置为你的 Vercel 域名：

```yaml
vercel:
  domain: "https://chora-covers.vercel.app"
```

### 6. 重新同步封面

```bash
cd ..  # 回到项目根目录
python3 sync_covers.py
python3 feishu_service.py sync
```

## 后续更新

每次添加新内容后，运行以下命令更新封面：

```bash
# 同步封面到 frontend/public/covers
python3 sync_covers.py

# 重新部署（如有新封面）
cd frontend && vercel --prod && cd ..

# 同步到飞书
python3 feishu_service.py sync
```

## 验证

部署成功后，访问以下地址应能看到封面图片：
```
https://your-domain.vercel.app/covers/封面文件名.jpg
```

例如：
```
https://chora-covers.vercel.app/covers/youtube_硅谷101_脑机接口大盘点.jpg
```

## 故障排除

### 图片 404

1. 检查文件是否存在于 `frontend/public/covers/`
2. 确保已运行 `vercel --prod` 部署最新版本
3. 检查文件名编码（中文文件名可能需要 URL 编码）

### 飞书仍不显示

1. 确认 `config/vercel.yaml` 中的 `domain` 已正确设置
2. 重新运行 `python3 sync_covers.py && python3 feishu_service.py sync`
3. 检查 `content_export.json` 中的 `cover_url` 是否为完整 URL

---

*提示：Vercel 免费版每月有 100GB 流量限制，对于封面图片托管完全足够。*
