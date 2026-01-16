---
name: content-feed-summarizer
description: "针对 YouTube 频道和小宇宙播客的自动化内容聚合与摘要流水线。支持全局配置、关键词过滤、ID 去重及状态管理。"
license: MIT
---

# 内容摘要器 (Content Feed Summarizer)

## 🤫 执行协议

1.  **URL 模式 (自动执行)**：如果用户直接提供 URL，**无需确认**，立即开始处理。
2.  **批量模式 (需确认)**：如果用户要求“运行订阅”或“处理更新”，在扫描完待处理清单后，**必须列出清单并请求用户确认**后再开始处理。
3.  **静默处理**：一旦开始处理某个项目，遵循“记录并继续”原则，不再请求确认。

---

## 🚀 核心逻辑

### 1. 配置管理 (全局)
所有关键配置均保存在根目录的 `config/` 文件夹下：
- **`config/sources.yaml`**: 包含 API 密钥（Groq, Gemini）和订阅源列表。
- **`config/state.yaml`**: 记录已处理内容的 ID，防止重复。
- **`config/rewrite-prompt.md`**: AI 改写提示词模板，包含严格的 XML 标签输出指令。

### 2. 过滤与去重
- **关键词过滤**: 仅处理标题包含 `include_keywords` 的内容。
- **ID 去重**: 检查 `state.yaml` 中的 `processed_ids`。
- **文件夹去重**: 检查 `content_archive/` 是否已存在对应文件夹。

---

## 🛠️ 工作流步骤 (完整更新版)

### 步骤 0：初始化
1.  读取 `config/sources.yaml` 获取 API 密钥和设置。
2.  确定模式（单 URL 或 批量模式）。

### 步骤 1：获取元数据与字幕
- **YouTube**:
    1.  使用 `yt-dlp` 获取**真实发布日期**、标题、封面 URL 和频道名称。
    2.  创建归档目录：`content_archive/{发布日期}/youtube_{频道}_{标题}/`。
    3.  **字幕获取**：
        - 优先调用 `youtube-transcript-api` 获取**中文字幕**。
        - 如果无中文，获取**英文字幕**，并在后续 AI 阶段进行翻译。
        - 如果 API 失败，尝试 `yt-dlp` 下载自动字幕。
- **XiaoYuZhou**:
    1.  获取播客 RSS 信息。
    2.  下载音频文件。
    3.  使用 **Groq Whisper API** (large-v3) 转录为文本。
- **输出**: 保存为 `transcript.md` 和初始 `metadata.md` (仅包含标题)。

### 步骤 2：生成封面图
- **YouTube**: 优先使用 `yt-dlp` 下载原始高清封面缩略图。
- **XiaoYuZhou (小宇宙)**:
    - 播客**无原始封面**，必须调用 **Gemini 3 Pro Image** 生成。
    - **风格要求**:
        - **必须包含中文标题文字**
        - **字体风格 (汇文明朝体 Huiwen Mincho)**:
            - 字体类别：繁體明體 / 宋體 (Traditional Chinese Mingti/Songti)
            - 视觉风格：復古 (Vintage)、懷舊 (Retro)、木版印刷風格 (Woodblock print)
            - 细节特征：微損 (Slightly distressed)、墨暈感 (Ink bleed)
            - 笔画特征：橫細豎粗對比明顯 (High contrast strokes)、Sharp serifs
            - 整体气质：儒雅書卷氣 (Elegant and scholarly)
        - 根据内容主题生成艺术性插画（非固定播客对话风格）
        - **禁止**频道名、播客名、作者名、水印
        - 高端杂志封面/书籍封面品质
        - 16:9 比例
    - **命令**: `python3 generate_cover.py --regenerate-all` 可批量补生成缺失封面
- **Fallback (通用)**: 若封面获取失败，自动调用 Gemini 生成备用封面。

### 步骤 3：AI 深度改写 (Streaming & 分离输出)
- **输入**: 读取 `transcript.md` 和 `config/rewrite-prompt.md`。
- **模型**: 调用 Gemini 3 Pro (通过云雾 API)。
- **关键处理**:
    1.  **流式传输 (Streaming)**: 使用 `streamGenerateContent` 接口以防止长文本超时。
    2.  **语言强制**: Prompt 包含指令 "若为英文，先理解再用简体中文创作"。
    3.  **输出分离**: 要求 AI 使用 XML 标签严格区分两部分内容：
        - **`<METADATA_SECTION>`**: 包含来源、发布时间、嘉宾、金句。
        - **`<REWRITE_SECTION>`**: 包含创作说明、深度改写（2000-2500字）、核心洞察、哲思结语、推荐书单。
    4.  **过滤**: 自动过滤 Gemini 的思考过程 (`thought: true`)。

### 步骤 4：文件归档与后处理
1.  **解析 AI 输出**:
    - 提取 `<METADATA_SECTION>` → 合并至 `metadata.md`（**始终保留原始标题**，AI 只补充来源、发布时间、嘉宾、金句）。
    - 提取 `<REWRITE_SECTION>` → 保存至 `rewritten.md`。
2.  **字数统计**: 运行 `utils/word_count.py` 更新 `rewritten.md` 中的字数信息。
3.  **清理**: 删除临时文件。

### 步骤 5：状态更新
- 将该内容的 ID 写入 `config/state.yaml` 的 `processed_ids` 列表中。

---

## ⚠️ 常见问题处理

| 场景 | 处理方式 |
| :--- | :--- |
| **字幕为英文** | Prompt 包含强制翻译指令，最终输出为简体中文。 |
| **API 超时/断开** | 使用 **流式 API (Streaming)** + SSE 解析，确保长内容生成稳定。 |
| **元数据缺失** | `rewrite_service.py` 会尝试从 AI 输出中提取，如失败则保留默认值。 |
| **XML 标签缺失** | 若 AI 未生成标签，系统会尝试自动清洗并保存全量输出，同时保留基本元数据。 |
| **重复运行** | 脚本通过 ID 和文件夹双重检查跳过。 |
