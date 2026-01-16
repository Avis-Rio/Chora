# 飞书多维表格配置指南

## 应用配置

在飞书开放平台创建应用后，将以下信息填入 `config/feishu.yaml`：

```yaml
feishu:
  app_id: ""          # 飞书应用 App ID
  app_secret: ""      # 飞书应用 App Secret
  base_id: ""         # 多维表格 Base ID (从表格 URL 获取)
  table_id: ""        # 数据表 Table ID (从表格 URL 获取)
```

## 获取 Base ID 和 Table ID

1. 打开飞书多维表格
2. URL 格式: `https://xxx.feishu.cn/base/bascnXXXX?table=tblYYYY`
   - `bascnXXXX` = Base ID
   - `tblYYYY` = Table ID

## 推荐字段配置

请在飞书多维表格中创建以下字段：

| 字段名称 | 字段类型 | 备注 |
|----------|----------|------|
| 标题 | 文本 | 主键字段 |
| 原始链接 | 链接 | YouTube/小宇宙 URL |
| 平台 | 单选 | 选项: `YouTube`, `小宇宙` |
| 频道 | 文本 | 频道/播客名称 |
| 发布时间 | 日期 | 发布日期 |
| **封面** | **附件** | ⚠️ **必须是附件类型**，图片会上传到这里 |
| 正文 | 多行文本 | 完整改写内容 (Markdown 格式) |
| 阅读时长 | 数字 | 单位: 分钟 |
| 标签 | 多选 | 英文标签列表 |
| 金句 | 多行文本 | Markdown 引用格式 |
| 评分 | 数字 | 0-120 |
| 嘉宾 | 文本 | 嘉宾姓名与介绍 |
| 原文逐字稿 | 多行文本 | 原始转录文本 |
| 记录ID | 文本 | 唯一标识符，用于去重 |

## ⚠️ 重要：封面字段设置

**封面字段必须是"附件"类型**，不是"链接"类型！

设置方法：
1. 在多维表格中点击"封面"列标题
2. 选择"修改字段"
3. 字段类型选择"附件"
4. 保存

## 标签多选选项

在"标签"字段中添加以下英文标签选项：

**学科大类 (Academic Disciplines)**
- Philosophy, Sociology, Psychology, Anthropology, History
- Political Science, Economics, Technology, Medicine, Law

**研究领域 (Research Fields)**
- Gender Studies, Cultural Studies, Media Studies, Religious Studies
- Neuroscience, STS

**概念大类 (Conceptual Themes)**
- Power & Politics, Identity, Ethics, Capitalism, Modernity
- Relationships, Art & Aesthetics

**形式类 (Format)**
- Interview, Deep Dive

## 应用权限配置

在飞书开放平台 → 权限管理中开启以下权限：

### 必需权限

| 权限 | 说明 |
|------|------|
| `bitable:app` | 多维表格应用权限 |
| `bitable:record` | 读写多维表格记录 |
| `drive:drive` | 上传文件到云空间（封面上传需要） |

### 配置步骤

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 进入你的应用
3. 点击"权限管理"
4. 搜索并开启上述权限
5. 如需审核，提交审核申请

## 数据流架构

```
┌─────────────────────────────────────────────────────────────┐
│                        数据流向                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  本地处理 → 飞书多维表格（数据库）→ Vercel 前端（展示）       │
│                                                             │
│  1. 音视频 → 转录 → AI 改写 → export_to_json.py             │
│  2. feishu_service.py → 上传封面 + 创建/更新记录             │
│  3. （后续）前端调用飞书 API 读取数据并渲染                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 常见问题

### 封面上传失败

1. 检查"封面"字段是否为"附件"类型
2. 检查应用是否有 `drive:drive` 权限
3. 检查封面文件是否存在于 `content_archive/.../cover.png`

### 记录重复

系统通过"记录ID"字段判断是否重复。确保该字段存在且为文本类型。

### 标签无法选择

确保"标签"字段为"多选"类型，并预先添加了标签选项。
