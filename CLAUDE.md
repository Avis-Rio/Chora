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
  - `setup.md`：环境安装与 API 密钥配置指南。
  - `examples/`：标准输出格式示例与反模式说明。

- **`process-subscriptions/`**：批量订阅处理 Skill。
  - `SKILL.md`：扫描 `config/sources.yaml` 中的所有订阅源并批量处理。

- **`process-url/`**：单 URL 处理 Skill。
  - `SKILL.md`：处理单个 YouTube 或小宇宙 URL。

### Python 工具脚本
独立脚本提供了被 Skill 调用的构建块：

- **`youtube_service.py`**：通过 yt-dlp 获取 YouTube 转录（VTT 解析、去重）。
- **`process_video.py`**：YouTube 视频完整处理流程（元数据 → 封面 → 字幕 → 改写 → 分发）。
- **`process_podcast.py`**：小宇宙播客完整处理流程（元数据 → 音频下载 → Groq Whisper 转录 → 改写 → 封面 → 分发）。
  - 必要时使用 ffmpeg 将音频切分为 5 分钟片段。
  - 使用 `whisper-large-v3` 模型。
  - 需要 `GROQ_API_KEY` 环境变量。
- **`generate_cover.py`**：基于 Gemini 的图像生成。
  - 从 `config/sources.yaml` 读取 API 配置（优先从 `.env` 环境变量读取）。
  - 模型：`gemini-3.1-flash-image-preview`（可在 `.env` 中覆盖）。
- **`fetch_feed.py`**：订阅源扫描与获取。
- ~~**`process_feed.py`**~~：批量处理入口。**2026-07-11 起废弃** ——与 `process-subscriptions` Skill 功能完全重叠，且 `--update-state` 子命令从未实现、文件本身依赖 Python 3.10+ 语法。状态更新已下沉到 `process_video.py` / `process_podcast.py` 内部。详见 `skills/ARCHITECTURE.md` §6。
- **`feishu_service.py`**：飞书多维表格同步服务。
- **`rewrite_service.py`**：AI 内容改写服务。
- **`config_loader.py`**：统一配置加载器，支持 `.env` 环境变量覆盖 YAML 配置。

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
- **Gemini API**：图像生成（`GEMINI_API_KEY` / `GEMINI_BASE_URL` / `GEMINI_MODEL` 环境变量，或 `config/sources.yaml`）。
- **LLM API**：内容改写（`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` 环境变量，或 `config/sources.yaml`）。
- **飞书 API**（可选）：表格同步（`FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_BASE_ID`, `FEISHU_TABLE_ID` 环境变量，或 `config/feishu.yaml`）。

**安全提示**：敏感信息优先使用 `.env` 文件配置，`config/sources.yaml` 与 `config/feishu.yaml` 中仅保留占位符。

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

### `config/sources.example.yaml`
全局配置模板，包含过滤规则、输出目录、订阅源列表示例。**API 密钥请通过 `.env` 环境变量配置，不要在此文件中填入真实密钥。**

### `.env.example`
环境变量配置模板，包含所有敏感信息（API keys、飞书凭证）。复制为 `.env` 并填入真实值。`.env` 已被 `.gitignore` 忽略，不会提交到 Git。

## 开发笔记

### 添加新内容源
1. 将解析逻辑添加到相应的工具脚本。
2. 更新 `SKILL.md` 第 1 步（获取内容与元数据）。
3. 确保元数据提取返回：标题、上传日期、时长、缩略图、频道名称。
4. 将源添加到 `config/sources.yaml` 或 `config/sources.example.yaml`。

### 修改摘要结构
编辑 `config/rewrite-prompt.md`。模板使用 `{{variable}}` 占位符：
- `{{title}}`：内容标题
- `{{source}}`：平台名称 (youtube/xiaoyuzhou)
- `{{channel_name}}`：频道/播客名称
- `{{transcript_text}}`：原始转录文本

### 环境变量
完整功能所需：
```bash
GROQ_API_KEY=<your_groq_key>               # 用于音频转录
GEMINI_API_KEY=<your_gemini_key>           # 用于封面生成
GEMINI_BASE_URL=<your_gemini_base_url>     # 可选，覆盖默认 Gemini endpoint
GEMINI_MODEL=<your_gemini_model>           # 可选，覆盖默认模型
LLM_API_KEY=<your_llm_key>                 # 用于内容改写
LLM_BASE_URL=<your_llm_base_url>           # 可选
LLM_MODEL=<your_llm_model>                 # 可选
FEISHU_APP_ID=<optional>                   # 用于飞书同步
FEISHU_APP_SECRET=<optional>
FEISHU_BASE_ID=<optional>
FEISHU_TABLE_ID=<optional>
```

### Python 依赖
使用 `requirements.txt` 安装：
```bash
pip install -r requirements.txt
```

关键库：
- `yt-dlp`：YouTube 元数据和字幕下载
- `youtube-transcript-api`：YouTube 字幕获取
- `groq`：Groq API 客户端 (Whisper)
- `requests`：HTTP 请求
- `PyYAML`：YAML 配置解析
- `python-dotenv`：自动加载 `.env` 环境变量
- `playwright`：分发流水线 PNG 导出
- `ffmpeg`：音频切分（系统依赖）

## 前端 Chóra

### 技术架构
- **部署**：Vercel Serverless Functions + 静态站点
- **数据源**：飞书多维表格 API（通过 `/api/content` 代理）
- **样式**：原生 CSS + 汇文明朝体自定义字体
- **交互**：原生 JavaScript（无框架）

### API 端点
- `/api/content`：从飞书获取文章列表
- `/api/image?token={token}`：代理飞书图片下载（处理认证）

### 已实现功能

#### 核心功能
- 文章卡片网格布局（响应式 3→2→1 列）
- 全文阅读器（侧边栏 TOC、进度条、返回顶部）
- 全局搜索（标题、频道、嘉宾、内容）
- 标签过滤系统

#### 交互增强
- **Logo 悬停动效**：旋转 180° + 橙色点亮
- **Keep in Touch 弹窗**：Rhizomata 公众号二维码
- **移动端卡片点亮**：Intersection Observer 实现滚动到中心自动高亮

### 移动端优化（2026-01-17）

#### 已修复问题
1. **封面模糊效果**：768px 减弱模糊，480px 完全移除
2. **内容溢出**：添加 `flex-direction: column` + `overflow-x: hidden`
3. **表格横向滚动**：使用 `.table-wrapper` 包装器 + `min-width: 500px`
4. **快读导航栏**：添加可折叠的移动端 TOC 按钮

#### 响应式断点
- **1024px**：2 列布局，隐藏桌面端 TOC
- **768px**：1 列布局，封面模糊减弱，搜索框堆叠
- **480px**：超小屏优化，完全移除模糊，字体缩小

### 环境变量（Vercel）
```bash
FEISHU_APP_ID=<app_id>
FEISHU_APP_SECRET=<app_secret>
FEISHU_BASE_ID=<base_id>
FEISHU_TABLE_ID=<table_id>
```

### 故障排除
详见 `frontend/DEPLOY.md`

### 内容管理

#### 发布控制
飞书多维表格中的「是否发布」复选框字段控制文章在前端的可见性：
- **勾选**：文章在前端显示
- **取消勾选**：文章从前端下架

**技术实现**：
- `api/content.js` 中通过 `filter()` 过滤 `是否发布 === true` 的记录
- CDN 缓存时间：30 秒（`s-maxage=30`）
- 更改后约 30 秒内生效，强制刷新可立即看到

#### 缓存策略
```
Cache-Control: s-maxage=30, stale-while-revalidate=15
```
- 边缘缓存 30 秒
- 过期后 15 秒内返回旧数据同时后台更新
