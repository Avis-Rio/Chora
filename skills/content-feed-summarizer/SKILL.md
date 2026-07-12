---
name: content-feed-summarizer
description: "针对 YouTube 频道和小宇宙播客的自动化内容聚合与摘要流水线。支持全局配置、关键词过滤、ID 去重及状态管理。"
license: MIT
---

# 内容摘要器 (Content Feed Summarizer)

> **本 SKILL 是工作流权威定义**——完整 7 步工作流（步骤 0-5）在这里独有。共同契约（Quiet Mode、Log & Continue、飞书同步等）见 [`ARCHITECTURE.md` §3](../ARCHITECTURE.md)。两个薄入口 SKILL（`process-url` / `process-subscriptions`）通过引用本文件获得工作流细节。

**入口 SKILL 协同**：
| SKILL | 输入 | 用户交互 | 谁负责"工作流"细节 |
|---|---|---|---|
| 本文件（`content-feed-summarizer`）| 协议权威 | — | **是**（步骤 0-5 在 §下方） |
| [`process-url`](../process-url/SKILL.md) | 单 URL | 无确认 | 引用 ARCHITECTURE + 本文件 |
| [`process-subscriptions`](../process-subscriptions/SKILL.md) | 订阅源 + 扫描 | **必须确认** | 引用 ARCHITECTURE + 本文件 |

**Quiet Mode 协议**（3 规则）：见 [ARCHITECTURE.md §3.1](../ARCHITECTURE.md#31-quiet-mode-协议)。
**错误处理策略**：见 [ARCHITECTURE.md §3.3](../ARCHITECTURE.md#33-错误处理log--continue)。

---

## 🚀 核心逻辑

### 1. 配置管理 (全局)
所有关键配置均保存在根目录的 `config/` 文件夹下：
- **`config/sources.yaml`**: 包含 API 密钥（Groq, Gemini）和订阅源列表。
- **`config/state.yaml`**: 记录已处理内容的 ID，防止重复。
- **`config/rewrite-prompt.md`**: AI 改写提示词模板，包含严格的 XML 标签输出指令。

**安全提示**：API 密钥优先从环境变量读取（`.env` 文件）。请将真实密钥写入仓库根目录的 `.env` 文件（已被 `.gitignore` 忽略），并在 `config/sources.yaml` 中保留占位符。参见 `.env.example`。

### 2. 过滤与去重
- **关键词过滤**: 仅处理标题包含 `include_keywords` 的内容。
- **ID 去重**: 检查 `state.yaml` 中的 `processed_ids`。
- **文件夹去重**: 检查 `content_archive/` 是否已存在对应文件夹。

---

## 🛠️ 工作流步骤 (完整更新版)

### 步骤 0：初始化
1.  读取 `config/sources.yaml` 及环境变量（`.env`）获取 API 密钥和设置。
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
- **模型**: 调用 Claude Sonnet 4 (通过云雾 API)。
- **关键处理**:
    1.  **流式传输 (Streaming)**: 使用 `streamGenerateContent` 接口以防止长文本超时。
    2.  **语言强制**: Prompt 包含指令 "若为英文，先理解再用简体中文创作"。
    3.  **输出分离**: 要求 AI 使用 XML 标签严格区分两部分内容：
        - **`<METADATA_SECTION>`**: 包含来源、发布时间、嘉宾、金句。
        - **`<REWRITE_SECTION>`**: 包含创作说明、深度改写（2000-2500字）、核心洞察、哲思结语、推荐书单。
    4.  **过滤**: 自动过滤 Gemini 的思考过程 (`thought: true`)。
    5.  **完整性验证**: ⚠️ **重要** - AI 改写完成后，**必须检查** `rewritten.md` 是否成功生成且文件大小 > 100 字节。若生成失败或文件为空，立即重试（最多 5 次）。

### 步骤 4：文件归档与后处理
1.  **解析 AI 输出**:
    - 提取 `<METADATA_SECTION>` → 合并至 `metadata.md`（**始终保留原始标题**，AI 只补充来源、发布时间、嘉宾、金句）。
    - 提取 `<REWRITE_SECTION>` → 保存至 `rewritten.md`。
2.  **字数统计**: 运行 `utils/word_count.py` 更新 `rewritten.md` 中的字数信息。
3.  **Guizang 小红书分发包**: `rewritten.md` 成功后自动调用 `distribution_pipeline.automation.generate_distribution_after_rewrite()`，生成 `distribution/{内容目录名}/xhs/index.html`、`xhs/post.md`，并在浏览器环境可用时导出 `xhs/output/*.png`。
4.  **清理**: 删除临时文件。

分发后处理遵循“记录并继续”：如果 Guizang 渲染、PNG 导出或 validator 失败，不要中断主流程；错误写入内容目录下的 `distribution_errors.log`。

### 步骤 5：状态更新
- 将该内容的 ID 写入 `config/state.yaml` 的 `processed_ids` 列表中。

### 步骤 6：内容分发（可选）

**前置条件**: 步骤 5 完成，且 `distribution.enabled: true`

**配置文件**: `skills/content-feed-summarizer/distribution-config.yaml`

**流程**:

1. **读取配置**: 加载 `distribution-config.yaml`
2. **检查开关**: 确认各平台是否启用
3. **提取内容**: 从 `rewritten.md` 和 `metadata.md` 提取所需内容
4. **小红书分发**（如启用）:
   - 提取核心洞察 + 哲思结语
   - 根据内容标签自动选择风格
   - 调用 `/baoyu-xhs-images` 生成卡片
   - 输出到 `distribution/xhs/`
5. **微信公众号分发**（如启用）:
   - 提取深度改写 + 书单推荐
   - 生成 Markdown 文档
   - 添加回流链接和公众号引导
   - 输出到 `distribution/wechat/article.md`
6. **输出报告**: 显示生成的文件路径

**输出目录结构**:
```
content_archive/{article}/
└── distribution/
    ├── xhs/
    │   ├── 01-cover.png
    │   ├── 02-insight.png
    │   └── ...
    └── wechat/
        └── article.md
```

**错误处理**:
- 分发失败不阻塞主流程
- 记录错误到日志
- 继续处理下一个平台

**手动触发**:
```bash
# 单独运行内容分发
python3 -c "
import sys
sys.path.insert(0, 'skills/content-feed-summarizer/distribution')
from config_loader import load_config
from content_extractor import ContentExtractor
from xhs_generator import XHSGenerator
from wechat_generator import WeChatGenerator

config = load_config()
article_dir = 'content_archive/YYYY-MM-DD/xxx'

extractor = ContentExtractor(article_dir)
content = extractor.extract()

# 小红书
xhs = XHSGenerator(config, article_dir)
print(xhs.get_generation_prompt(content))

# 公众号
wc = WeChatGenerator(config, article_dir)
result = wc.generate(content)
print(f'公众号文章: {result.markdown_path}')
"
```

---

## 🔧 完整性验证与修复工具

为防止批量处理时因超时导致 `rewritten.md` 缺失，提供以下工具：

### 1. 完整性检查 (`utils/content_validator.py`)
```bash
# 检查最近 30 天的内容完整性
python3 utils/content_validator.py

# 检查所有内容
python3 utils/content_validator.py --days 0

# 只显示不完整的条目
python3 utils/content_validator.py --only-invalid

# 生成修复报告
python3 utils/content_validator.py --report
```

### 2. 批量重写 (`batch_rewrite.py`)
```bash
# 扫描并处理所有缺失 rewritten.md 的内容
python3 batch_rewrite.py

# 只处理大文件 (>40KB)
python3 batch_rewrite.py --large-only

# 预览模式（不执行）
python3 batch_rewrite.py --dry-run

# 处理最近 7 天的新内容
python3 batch_rewrite.py --days 7

# 补 rewrite 后同时生成 Guizang 小红书分发包
python3 batch_rewrite.py --generate-distribution
```

### 3. 飞书同步前验证
**重要**：每次同步飞书前，务必运行：
```bash
python3 utils/content_validator.py --fix
```
这会自动修复所有缺失的 `rewritten.md`。

---

## ⚠️ 常见问题处理

| 场景 | 处理方式 |
| :--- | :--- |
| **字幕为英文** | Prompt 包含强制翻译指令，最终输出为简体中文。 |
| **API 超时/断开** | 使用 **流式 API (Streaming)** + SSE 解析，确保长内容生成稳定。 |
| **元数据缺失** | `rewrite_service.py` 会尝试从 AI 输出中提取，如失败则保留默认值。 |
| **XML 标签缺失** | 若 AI 未生成标签，系统会尝试自动清洗并保存全量输出，同时保留基本元数据。 |
| **重复运行** | 脚本通过 ID 和文件夹双重检查跳过。 |
| **rewritten.md 缺失** | 运行 `python3 utils/content_validator.py --fix` 自动修复 |
