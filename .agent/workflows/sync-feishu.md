---
description: 导出归档内容并同步到飞书多维表格（数据库模式）
---

# /sync-feishu 工作流

将本地归档内容导出为 JSON 并智能同步到飞书多维表格。

## 核心特性

- **智能同步**：自动跳过已完整的记录，仅处理新增或不完整的内容
- **自动补全**：检测缺失字段（如封面、标签），自动补全数据
- **封面上传**：封面图片直接上传到飞书作为附件存储
- **网络容错**：因网络问题失败的记录，再次运行会自动修复

## 使用方式

```
/sync-feishu
```

## 前置条件

1. 已在飞书开放平台创建应用并获取 app_id/app_secret
2. 已创建多维表格并配置好字段（参见 `config/feishu-setup.md`）
3. 已填写 `config/feishu.yaml` 配置文件
4. **确保飞书应用权限**：
   - `bitable:app` - 多维表格读写
   - `drive:drive` - 云空间上传（封面附件）

## 执行步骤

### 1. 导出内容到 JSON
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 export_to_json.py --all
```

### 2. 智能同步到飞书
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 feishu_service.py sync
```

## 智能同步逻辑

```
┌─────────────────────────────────────────────────────────────┐
│                     同步决策流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  对于每条本地内容：                                          │
│                                                             │
│  1. 检查飞书是否已有该记录（通过记录ID匹配）                   │
│                                                             │
│  2. 如果不存在 → ➕ 创建新记录 + 上传封面                     │
│                                                             │
│  3. 如果已存在：                                             │
│     - 检查必填字段是否完整                                   │
│     - 完整 → ⏭️ 跳过                                        │
│     - 不完整 → 🔧 补全缺失字段 + 重新上传封面                 │
│                                                             │
│  必填字段：标题、正文、封面、标签、发布时间、记录ID            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 可选命令

### 检查记录完整性
```bash
python3 feishu_service.py check
```
显示每条记录的完整性状态和缺失字段。

### 强制更新所有记录
```bash
python3 feishu_service.py sync --force
```
忽略完整性检查，强制更新所有记录（包括重新上传封面）。

## 输出示例

```
🔍 Checking table fields...
   Found fields: 标题, 正文, 封面, 标签, ...
📥 Fetching existing records...
   Found 9 existing records

📦 Processing 9 items...
⏭️  Skip (complete): 脑机接口大盘点...
⏭️  Skip (complete): How To Grow An Audience...
🔧 Updating (missing: 封面): 午后偏见043...
   📷 Uploaded: cover.png...
✅ Updated record: 午后偏见043...

==================================================
✅ Sync complete:
   ➕ Created: 0
   🔧 Updated: 1
   ⏭️  Skipped: 8
   ❌ Failed: 0
```

## 数据流向

```
本地归档 (content_archive/)
    ↓
export_to_json.py → content_export.json
    ↓
feishu_service.py sync (智能同步)
    ↓
┌───────────────────────────────────────┐
│  飞书多维表格 (数据库)                 │
│  - 文本内容：直接存储                 │
│  - 封面图片：上传为附件               │
│  - 标签：英文标签多选                 │
└───────────────────────────────────────┘
    ↓ (后续)
Vercel 前端 → 调用飞书 API → 渲染展示
```

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 认证失败 | 检查 `config/feishu.yaml` 中的 app_id/app_secret |
| 表格不存在 | 检查 base_id 和 table_id 是否正确 |
| 字段缺失 | 按 `config/feishu-setup.md` 创建缺失字段 |
| 封面上传失败 | 1. 检查 `drive:drive` 权限 2. 再次运行 sync 自动重试 |
| 附件字段报错 | 确保"封面"字段类型为"附件"而非"链接" |
| 网络超时 | 再次运行 sync，会自动补全之前失败的记录 |

## 字段类型要求

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 标题 | 文本 | 内容标题 |
| 记录ID | 文本 | 唯一标识符（用于去重） |
| 封面 | **附件** | ⚠️ 必须是附件类型 |
| 正文 | 多行文本 | AI 改写内容 |
| 标签 | 多选 | 英文标签列表 |
| 发布时间 | 日期 | 原始发布日期 |
| 原始链接 | 链接 | YouTube/小宇宙 URL |
| 平台 | 单选 | YouTube / 小宇宙 |
| 评分 | 数字 | 0-120 评分 |
