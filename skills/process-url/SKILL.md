---
name: process-url
description: 处理单个 YouTube 视频或小宇宙播客 URL，自动执行完整工作流
---

# /process-url 工作流

处理单个内容 URL，自动识别类型并执行完整工作流。

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

### 步骤 1: 识别 URL 类型

自动检测 URL 是 YouTube 还是小宇宙播客。

### 步骤 2: 执行对应处理脚本

**如果是 YouTube 视频:**
```bash
python3 process_video.py "<URL>"
```

**如果是小宇宙播客:**
```bash
python3 process_podcast.py "<URL>"
```

### 步骤 3: 处理流程 (自动执行，无需确认)

| 阶段 | YouTube | 小宇宙 |
|------|---------|--------|
| 元数据 | yt-dlp 获取标题、频道、日期 | RSS 解析 |
| 封面 | 下载高清缩略图 | Gemini 生成艺术封面 |
| 内容 | youtube-transcript-api 获取字幕 | Groq Whisper 转录音频 |
| AI 改写 | Claude Sonnet 4 流式生成 | Claude Sonnet 4 流式生成 |

### 步骤 4: 完整性验证 ⚠️

**重要**: AI 改写完成后，**必须验证** `rewritten.md` 是否成功生成：
- 检查文件是否存在
- 检查文件大小 > 100 字节
- 如验证失败，立即重试（最多 5 次）

### 步骤 5: 同步至飞书

处理完成后，同步至飞书多维表格：
```bash
python3 feishu_service.py sync
```

## 输出文件

处理完成后，在 `content_archive/{日期}/{平台}_{频道}_{标题}/` 目录下生成：

```
├── metadata.md      # 元数据 (来源、发布时间、嘉宾、金句)
├── transcript.md    # 原始转录/字幕
├── rewritten.md     # 深度改写内容 (2000-3000字)
├── cover.jpg/png    # 封面图
└── audio.m4a       # (仅小宇宙) 原始音频
```

## AI 改写输出结构

`rewritten.md` 包含以下部分：

```
## 1. 创作说明
- 选题方向、评分、字数、核心价值

## 2. 深度改写 (2000-2500字)
核心论点深度展开

## 3. 核心洞察
5-10 条穿透力洞察

## 4. 哲思结语
思想家风格的金句总结

## 5. 推荐书单
3-5 本延伸阅读书籍

## 6. 内容标签
Tags: Philosophy, Technology, ...
```

## 注意事项

- URL 模式**无需确认**，直接开始处理
- 如果目录已存在，会跳过已完成的步骤
- 处理过程中遇到错误会记录并继续
- 封面生成失败会自动调用 Gemini 兜底