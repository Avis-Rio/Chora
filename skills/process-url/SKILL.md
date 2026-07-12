---
name: process-url
description: 处理单个 YouTube 视频或小宇宙播客 URL，自动执行完整工作流
license: MIT
---

# /process-url 工作流

> **本 SKILL 是入口，不重复工作流细节**。完整工作流（步骤 0-7、元数据获取、AI 改写、Quiet Mode 协议）定义在 [`content-feed-summarizer/SKILL.md`](../content-feed-summarizer/SKILL.md)，本文件**只声明此入口特有的规则**。
>
> 编排权威：`skills/ARCHITECTURE.md`

## 使用方式

```
/process-url <URL>
```

## 支持的 URL 格式

| 平台 | URL 格式 | 示例 |
|------|----------|------|
| **YouTube** | `https://www.youtube.com/watch?v=VIDEO_ID` | `https://youtube.com/watch?v=abc123` |
| **YouTube** | `https://youtu.be/VIDEO_ID` | `https://youtu.be/abc123` |
| **小宇宙** | `https://www.xiaoyuzhoufm.com/episode/ID` | `https://xiaoyuzhoufm.com/episode/5e4ee557...` |

## 执行步骤

### 步骤 1：识别 URL 类型

根据 host 自动判断：`youtube.com` / `youtu.be` → YouTube；`xiaoyuzhoufm.com` → 小宇宙。

### 步骤 2：调用对应处理脚本

| 平台 | 命令 |
|------|------|
| YouTube | `python3 process_video.py "<URL>"` |
| 小宇宙 | `python3 process_podcast.py "<URL>"` |

脚本内部完成完整工作流（元数据 / 封面 / 转录 / AI 改写 / 归档）。

### 步骤 3：完整性验证（**此入口特有**）

必须验证 `rewritten.md` 成功生成：

| 条件 | 失败处理 |
|------|----------|
| 文件存在 | 重试（最多 5 次，间隔 5 秒） |
| 文件 > 100 字节 | 同上 |
| 仍然失败 | 记录到 `processing_errors.log`，继续（不抛错） |

### 步骤 4：同步至飞书

```bash
python3 feishu_service.py sync
```

> 若环境变量 `FEISHU_*` 未配置，该命令会安全跳过（不报错）。

## 此入口的 Quiet Mode 规则

- **URL 模式无需确认**——给定 URL 即开始
- 数据缺失用 `"Unknown"` 兜底，不停下询问
- 错误重试 3 次后写入 `processing_errors.log`，继续
- 一旦开始处理，绝不暂停请求"是否继续？"

## 输出

每条内容落在：

```
content_archive/{YYYY-MM-DD}/{youtube|xiaoyuzhou}_{channel}_{title}/
├── metadata.md
├── transcript.md
├── rewritten.md    ← 必须验证存在且 > 100 字节
├── cover.jpg/png
└── audio.m4a       ← 仅小宇宙
```

详细字段约定见 `content-feed-summarizer/SKILL.md` §3（AI 改写输出结构）。

## 与 process-subscriptions 的区别

| 场景 | 用 process-url | 用 process-subscriptions |
|------|----------------|--------------------------|
| 用户给了单个 URL | ✅ | ❌ |
| 批量扫描订阅源 | ❌ | ✅ |
| 需要用户先确认 | 否 | **是** |
| 自动完整性修复 | 内嵌重试 5 次 | `utils/content_validator.py --fix` |

详细对比见 `skills/ARCHITECTURE.md` §4。
