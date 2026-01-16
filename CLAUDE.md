# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此存储库中工作时提供指导。

## 语言与沟通规范
- **全程使用中文**：请务必全程使用中文与我对话。
- **文档编写**：所有新创建或修改的文档类文件（如 README、技术文档、注释等）均需使用中文编写。

## 项目概览

**Chora** 是一个自动化的内容聚合与处理流水线。它从 YouTube 和小宇宙 (XiaoYuZhou) 播客获取内容，进行音视频转录，生成 AI 驱动的结构化摘要，并将其存档在本地，同时支持可选的飞书 (Feishu) 集成。

### 核心工作流
1. 从 YouTube 频道或小宇宙播客获取内容（通过配置文件或直接 URL）。
2. 提取/生成转录文本（使用 YouTube 字幕 API 或 Groq Whisper 处理音频）。
3. 下载或使用 AI 生成封面图（使用 Gemini API）。
4. 使用可自定义的提示词 (Prompts) 将内容 AI 改写为结构化摘要。
5. 存档至本地文件夹，包含元数据、转录文本、摘要和封面图。
6. （可选）将元数据同步至飞书多维表格。

## 命令

### 运行内容摘要器 (Content Feed Summarizer)
主要工作流作为 Claude Code Skill 实现。触发方式：
```bash
# 处理单个 URL
"处理这个视频：https://youtube.com/watch?v=VIDEO_ID"

# 从配置进行批量处理
"运行我的内容摘要器 (Run my content feed summarizer)"
```

### 转录 (Transcription)
```bash
# 使用 Groq Whisper 转录播客音频
python transcribe_podcast.py <audio_file_path>

# 使用 yt-dlp 获取 YouTube 转录
python youtube_service.py  # 硬编码视频 ID 的测试模式
```

### 封面图生成
```bash
# 使用 Gemini API 生成封面图
python generate_cover.py "<prompt>" <output_path>
```

### 小宇宙音频下载
```bash
# 从小宇宙节目下载音频
python download_xyz.py <episode_url>
```

## 架构

### Skill 系统
项目使用 **Claude Code Skills**（而非独立脚本）作为主要接口。Skills 位于 `skills/` 目录下：

- **`content-feed-summarizer/`**：编排完整流水线的主要 Skill。
  - `SKILL.md`：Skill 定义，包含用于零干扰自动化的“静默模式协议 (Quiet Mode Protocol)”。
  - `prompt.md`：可自定义的 AI 改写模板（中文格式，结构化）。
  - `config-example.yaml`：批量处理的示例配置。

- **`podcast-cover-generator/`**：封面图生成配置。
  - `sources.yaml`：Gemini API 凭据和各平台的默认提示词。
  - `state.yaml`：处理状态跟踪。

### Python 工具脚本
独立脚本提供了被 Skill 调用的构建块：

- **`youtube_service.py`**：通过 yt-dlp 获取 YouTube 转录（VTT 解析、去重）。
- **`transcribe_podcast.py`**：使用 Groq Whisper API 进行音频转录。
  - 必要时将音频切分为 10 分钟的片段。
  - 使用 `whisper-large-v3` 模型。
  - 需要 `GROQ_API_KEY` 环境变量。
- **`generate_cover.py`**：基于 Gemini 的图像生成。
  - 从 `skills/podcast-cover-generator/sources.yaml` 读取 API 配置。
  - 模型：`gemini-3-pro-image-preview`。
- **`download_xyz.py`**：小宇宙音频爬取工具。

### 输出结构
内容存档在 `content_archive/` 目录下，结构如下：
```
content_archive/
└── {date}_{platform}_{channel}_{title}/
    ├── metadata.md       # YAML frontmatter + 嘉宾 + 金句
    ├── transcript.md     # 原始转录文本
    ├── rewritten.md      # AI 生成的结构化摘要
    ├── cover.jpg/webp    # 封面图（下载或 AI 生成）
    └── audio.m4a         # 原始音频（针对播客）
```

**文件夹命名规则**：`YYYY-MM-DD_{youtube|xiaoyuzhou}_{channel_name}_{title}`

### 错误处理哲学
Skill 遵循 **“记录并继续 (Log & Continue)”** 策略：
- 缺失转录：跳过该项，记录到 `processing_errors.log`。
- 封面下载失败：使用 Gemini 自动生成。
- 网络超时：重试 3 次（间隔 5 秒），然后跳过。
- 重复内容：如果输出文件夹已存在则跳过。
- 输出过长：自动切分为 `rewritten_part1.md`、`rewritten_part2.md` 等。
- 缺失元数据：默认使用 `"Unknown"`。
- **关键**：缺失 `prompt.md` → 报错并强制停止。

### API 依赖
- **Groq API**：Whisper 转录（`GROQ_API_KEY` 环境变量）。
- **Gemini API**：图像生成（在 `skills/podcast-cover-generator/sources.yaml` 中配置）。
- **飞书 API**（可选）：表格同步（`FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_TABLE_ID`）。

### 内容过滤
- **时长过滤**：默认最小 30 分钟（在 YAML 中配置）。
- **日期范围**：批量模式下默认为最近 7 天。
- **去重**：处理前检查是否存在已有的输出文件夹。

## 关键实现细节

### 转录生成策略
**YouTube**:
1. 首次尝试：`youtube-transcript-api`（如果可用）。
2. 备选方案：带有 VTT 解析的 `yt-dlp --write-auto-sub`。
3. VTT 解析器处理滚动字幕、去重和标签剥离。

**小宇宙**:
1. 通过爬取下载音频（无官方 API）。
2. 如果文件 > 25MB：使用 `pydub` 切分为 10 分钟片段。
3. 发送至 Groq Whisper API（并行或顺序）。
4. 合并结果。

### AI 摘要格式
`prompt.md` 模板强制执行以下结构（简体中文）：
- **执行摘要 (📌)**：150 字概览。
- **核心洞察与金句 (🔥)**：3-5 条原话引用。
- **核心概念 (💡)**：3-5 个主题章节。
- **批判性讨论 (🗣️)**：争议点或辩论。
- **行动指南 (✅)**：实用的要点建议。

### 静默模式协议 (Quiet Mode Protocol)
Skill **从不请求确认**。它：
- 原子化执行（获取 → 转录 → 摘要 → 保存）。
- 数据缺失时使用默认值。
- 记录错误并继续处理下一项。
- 自动切分长输出。
- 绝不停下来询问“我是否应该继续？”。

## 配置文件

### `skills/content-feed-summarizer/config-example.yaml`
```yaml
filter:
  min_duration_minutes: 30    # 跳过短于此时间的项
  date_range_days: 7          # 批量模式：获取最近 N 天的内容

output_dir: "./content_archive"

sources:
  youtube:
    - channel_id: "UCxxxxxx"
      name: "硅谷101"
  xiaoyuzhou:
    - podcast_id: "abc123456"
      name: "商业就是这样"
```

### `skills/podcast-cover-generator/sources.yaml`
包含 Gemini API 凭据和平台特定的默认提示词。**请勿提交真实的 API 密钥。**

## 开发笔记

### 添加新内容源
1. 将解析逻辑添加到相应的工具脚本。
2. 更新 `SKILL.md` 第 1 步（获取内容与元数据）。
3. 确保元数据提取返回：标题、上传日期、时长、缩略图、频道名称。
4. 将源添加到 `config-example.yaml`。

### 修改摘要结构
编辑 `skills/content-feed-summarizer/prompt.md`。模板使用 `{{variable}}` 占位符：
- `{{title}}`：内容标题
- `{{source}}`：平台名称 (youtube/xiaoyuzhou)
- `{{channel_name}}`：频道/播客名称
- `{{transcript_text}}`：原始转录文本

### 环境变量
完整功能所需：
```bash
GROQ_API_KEY=<your_groq_key>           # 用于音频转录
FEISHU_APP_ID=<optional>               # 用于飞书同步
FEISHU_APP_SECRET=<optional>
FEISHU_TABLE_ID=<optional>
```

### Python 依赖
关键库（按需安装）：
- `yt-dlp`：YouTube 元数据和字幕下载
- `groq`：Groq API 客户端 (Whisper)
- `pydub`：音频切分与处理
- `requests`：HTTP 请求
- `pyyaml`：YAML 配置解析
- `ffmpeg`：pydub 所需（系统依赖）
