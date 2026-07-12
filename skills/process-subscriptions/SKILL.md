---
name: process-subscriptions
description: 批量处理订阅源中的所有新内容，支持 YouTube 频道和小宇宙播客
license: MIT
---

# /process-subscriptions 工作流

> **本 SKILL 是入口，不重复工作流细节**。完整工作流（步骤 0-7、元数据获取、AI 改写、Quiet Mode 协议）定义在 [`content-feed-summarizer/SKILL.md`](../content-feed-summarizer/SKILL.md)，本文件**只声明此入口特有的规则 + 扫描步骤**。
>
> 编排权威：`skills/ARCHITECTURE.md`

## 使用方式

```
/process-subscriptions
```

## 此入口与单 URL 的核心差异

| 差异 | process-url | **process-subscriptions** |
|------|-------------|---------------------------|
| 用户确认 | 无 | **必须先列清单 + 用户确认** |
| 扫描步骤 | 无 | `fetch_feed.py` 扫描所有订阅源 |
| 完整性自动修复 | 内嵌重试 5 次 | 步骤 4 调 `utils/content_validator.py --fix` |
| 状态更新 | 自动 | 自动（每个 process_video/podcast 内部已写入） |

完整对比见 `skills/ARCHITECTURE.md` §4。

## 执行步骤

### 步骤 0：前置检查

1. 验证 `config/sources.yaml` 存在（不存在则提示从 `config/sources.example.yaml` 复制）
2. 验证 API 密钥不是占位符（`your_xxx`）

### 步骤 1：扫描订阅源

```bash
python3 fetch_feed.py
```

按以下规则过滤：

| 规则 | 来源 |
|------|------|
| 关键词过滤（include_keywords） | `config/sources.yaml` |
| 已处理 ID 去重 | `config/state.yaml` 的 `processed_ids` |
| 文件夹去重 | `content_archive/` |
| 时间范围（默认 7 天） | `config.sources.yaml` → `settings.date_range_days` |
| 时长过滤（默认 30 分钟） | `config.sources.yaml` → `settings.min_duration_minutes` |

### 步骤 2：生成待处理清单（**必须用户确认**）

扫描完成后，**必须列出清单并请求用户确认**：

```
📋 待处理内容清单 (共 X 条):

YouTube:
1. [频道] 标题 (发布日期) - 时长
2. ...

小宇宙:
1. [播客] 标题 (发布日期) - 时长
2. ...

共 X 条新内容，是否开始处理？
```

**关键**：使用 `mcp__ask-user__ask_user` 工具（不是文字询问）。等待回复后再继续。

### 步骤 3：批量处理（用户确认后执行）

对清单内每条 URL，按平台调用：

```bash
# YouTube
python3 process_video.py "<VIDEO_URL>"

# 小宇宙
python3 process_podcast.py "<EPISODE_URL>"
```

每个项目的工作流由对应脚本负责（不重复定义）。

### 步骤 4：完整性检查（**此入口特有**）

批量处理完成后，自动修复缺失的 `rewritten.md`：

```bash
python3 utils/content_validator.py --fix
```

### 步骤 5：同步至飞书

```bash
python3 feishu_service.py sync
```

导出最新数据：
```bash
python3 export_to_json.py --all
python3 generate_frontend_data.py   # 同步 frontend/data
```

> 若 `FEISHU_*` 环境变量未配置，sync 安全跳过。

## Quiet Mode 规则

- 一旦用户确认清单 + 开始处理，**绝不再询问**
- 每条失败记录到 `processing_errors.log`，**继续处理下一条**
- 不因单条失败而中断批量

## 输出

每条内容落在：

```
content_archive/{YYYY-MM-DD}/{youtube|xiaoyuzhou}_{channel}_{title}/
├── metadata.md
├── transcript.md
├── rewritten.md
├── cover.jpg/png
└── audio.m4a       ← 仅小宇宙
```

下游数据流（不在本 SKILL 控制）：

```
content_archive/ → export_to_json.py → content_export.json
                → generate_frontend_data.py → frontend/data/ + frontend/public/data/
                → feishu_service.py sync → 飞书多维表格
```

详见 `skills/ARCHITECTURE.md` §3.5。

## 注意事项

- 批量模式**必须先列清单 + 用户确认后才开始**
- 错误日志写 `processing_errors.log`，不阻塞流程
- 已废弃：`python3 process_feed.py --update-state`（该命令从未实现，2026-07-11 起脚本已删除；状态更新由 process_video/podcast 内部完成）
