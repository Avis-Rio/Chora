---
description: 处理单个 YouTube 视频或小宇宙播客 URL，执行完整的内容处理工作流
---

# /process-url 工作流

处理单个内容 URL，自动识别类型并执行完整工作流。

## 使用方式

```
/process-url <URL>
```

## 支持的 URL 格式

- **YouTube**: `https://www.youtube.com/watch?v=VIDEO_ID` 或 `https://youtu.be/VIDEO_ID`
- **小宇宙**: `https://www.xiaoyuzhoufm.com/episode/EPISODE_ID`

## 执行步骤

### 1. 识别 URL 类型
根据 URL 判断是 YouTube 视频还是小宇宙播客。

### 2. 执行对应处理脚本

**如果是 YouTube 视频:**
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 process_video.py "<URL>"
```

**如果是小宇宙播客:**
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 process_podcast.py "<URL>"
```

### 3. 处理流程 (自动执行，无需确认)

1. **获取元数据**: 标题、频道/播客名、发布日期
2. **创建归档目录**: `content_archive/{日期}/{平台}_{频道}_{标题}/`
3. **获取内容**:
   - YouTube: 下载封面 + 获取字幕
   - 小宇宙: 下载音频 + Groq Whisper 转录
4. **AI 深度改写**: Gemini 3 Pro 流式生成
5. **生成封面** (仅小宇宙): Gemini 3 Pro Image 生成汇文明朝体风格封面

### 4. 输出文件

处理完成后，在 `content_archive/` 目录下生成:
- `metadata.md` - 元数据 (来源、发布时间、嘉宾、金句)
- `transcript.md` - 原始转录/字幕
- `rewritten.md` - 深度改写内容
- `cover.jpg/png` - 封面图

## 注意事项

- URL 模式**无需确认**，直接开始处理
- 如果目录已存在，会跳过已完成的步骤
- 处理过程中遇到错误会记录并继续
