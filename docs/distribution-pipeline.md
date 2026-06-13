# Chora 分发素材生成流水线

## 定位

分发素材生成流水线负责把 `content_archive/` 中已经完成 AI 改写的文章，转化为适合微信公众号和小红书使用的视觉素材包。它是内容处理主流程之后的独立后处理层，不负责下载、转录、AI 改写、飞书同步或前端展示。

## 输入要求

输入目录必须是单篇内容归档目录，至少包含：

```text
metadata.md
rewritten.md
transcript.md
cover.jpg/png/webp
```

其中 `metadata.md` 提供标题、来源、发布时间、嘉宾和金句；`rewritten.md` 提供核心洞察与标签。

## 输出结构

默认输出到 `distribution/{内容目录名}/`：

```text
source.json
insights.json
visual_system.json
visual_briefs.json
xhs/
  post.md
  cards/
    01-cover.html
    02-insight.html
wechat/
  hero.html
  inline_01.html
  appendix.md
manifest.json
```

如果启用图片导出，每个 HTML 文件会生成同名 PNG。

## 使用方式

只生成 HTML 和文案：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-13/youtube_硅谷101_Token经济学：AI时代的新货币战争" \
  --platform all \
  --style chora-editorial \
  --cards 8 \
  --no-export-images
```

生成 HTML 并导出图片：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-13/youtube_硅谷101_Token经济学：AI时代的新货币战争" \
  --platform all \
  --style chora-editorial \
  --cards 8
```

图片导出依赖 Playwright。如环境缺少浏览器运行时，按提示执行：

```bash
python3 -m playwright install chromium
```

## Guizang 渲染后端计划

当前默认渲染器仍是基础后端，输出一张卡一个 HTML。CLI 已新增可选的 `--renderer guizang`、`--guizang-mode` 和 `--guizang-theme` 参数；Guizang 后端目前已支持小红书 `xhs/index.html` 单文件多画板 HTML 输出。PNG 导出、validator 和微信公众号封面对会在后续阶段接入。

实施计划见：

```text
docs/plans/2026-05-31-guizang-renderer-integration.md
```

目标命令形态：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform all \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8
```

该后端会复用现有 `source.json`、`insights.json`、`visual_system.json` 和 `visual_briefs.json`，只替换平台生图环节。基础后端会保留为回退路径。

当前可用的 Guizang XHS smoke 命令：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform xhs \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --no-export-images
```

图像资产默认使用离线稳定模式：

```bash
--image-assets plan
```

可选模式：

- `plan`：只写搜索计划和来源文件，不访问网络。
- `candidates`：尝试为每个 planned request 拉取候选图。
- `download`：下载首选候选到 `xhs/assets/images/` 并写入 `selected_assets`。

如果要导出 PNG，需要 Node 侧 Playwright 依赖：

```bash
npm install --save-dev playwright --ignore-scripts
```

安装后去掉 `--no-export-images`，会调用 `xhs/render.cjs` 并输出到 `xhs/output/`。当前 `render.cjs` 和 validator 都会优先使用本机 Chrome，避免强制下载 Playwright Chromium。

注意：在 Codex 默认沙箱中，浏览器进程可能被系统权限阻止。如果遇到 `kill EPERM`、`SIGABRT`、`Chrome CDP endpoint was not ready` 或无法创建 `~/Library/Caches/ms-playwright/__dirlock`，不需要安装 MCP，也不需要切到外部 Terminal；在 Codex 中允许这条 `python3 -m distribution_pipeline.generate_distribution ...` 命令以非沙箱方式运行即可完成 PNG 与 validator 验收。

### 图像证据层

Guizang 后端会为每个包生成 `image_assets.json`。它记录：

- 本地可用素材，例如归档目录中的 `cover.jpg/png/webp`。
- 每张卡片建议使用的图像角色：`hero`、`evidence` 等。
- 外部搜索词与搜索入口：Pexels、Unsplash、Wallhaven、Flickr CC。
- 版权状态，默认外部图均为 `unverified`，使用前需人工判断。

XHS 渲染侧会同步写入：

```text
xhs/assets/image_assets.json
xhs/assets/SOURCES.md
xhs/assets/images/
```

若本地存在 `cover.*`，封面页会自动引用复制后的 `xhs/assets/images/source-cover.*`，形成图文封面。

外部图片已支持候选与下载链路。Pexels 与 Unsplash 官方 API 需要环境变量：

```bash
PEXELS_API_KEY=<your_key>
UNSPLASH_ACCESS_KEY=<your_key>
```

没有 API key 时，`plan` 模式仍会写入可人工点击的搜索入口；`download` 模式也可以处理手动候选或 direct URL。已下载外部图片会写入 `selected_assets`，并记录到 `xhs/assets/SOURCES.md`。当洞见页存在可用证据图时，Guizang 会自动使用 M10 Evidence Feature，把图片作为页面的主要证据区。

外部图片版权不会被自动判定为可商用。`SOURCES.md` 会保存图源、作者、原始 URL 与版权状态，发布前仍需人工确认。

## 数据中间层

`source.json` 保存来源文章信息：

- 标题
- 平台
- 频道
- 原始链接
- 发布时间
- 嘉宾
- 金句
- 标签

`insights.json` 保存核心洞见列表：

- 序号
- 洞见标题
- 洞见正文
- 一句话摘要
- 关键词占位

`visual_system.json` 保存整篇文章的视觉母题系统，包括视觉母题、材质语言、构图规则和禁忌。

`visual_briefs.json` 保存每条洞见的视觉导演稿，包括视觉隐喻、构图、情绪、材质和禁止使用的陈词滥调。

## 小红书策略

小红书素材采用竖版 `1080x1440` 卡片组，默认包括：

- 封面卡
- 若干洞见卡
- 可选概念图卡
- 结尾导流卡

`xhs/post.md` 会生成可直接复用的平台发布稿，包括：

- `小红书正文｜复制此段`：经过压缩的发布正文。
- `Tags｜复制此段`：去重后的平台标签。
- `首评｜可选`：Chora / Rhizomata 导流首评。
- `发布清单`：图片上传顺序与图源记录位置。
- `全部洞察备份`：保留完整洞察，供人工二次编辑。

Guizang 小红书末卡会使用低调 CTA 条。若项目内存在透明背景 PNG 形式的 `frontend/assets/rhizomata-qr.png`，会复制到 `xhs/assets/brand/rhizomata-qr.png` 并渲染在末卡；否则仅显示 Chora 链接与公众号名称，不阻塞导出。

## 微信公众号策略

公众号素材更克制，默认生成：

- `hero.html`：文章首图，`1200x675`
- `inline_*.html`：文中洞见贴图，`900x500`
- `appendix.md`：文章末尾导流文案

公众号贴图不追求小红书式强钩子，而更强调杂志内页感、留白和长期品牌识别。

## 风格语法

风格定义位于 `distribution_pipeline/styles/`，当前包含：

- `chora-editorial`
- `techno-critical`
- `literary-poster`

风格 YAML 不是固定模板，而是审美规则：字体、色彩、布局倾向、材质和禁忌。渲染器会将这些规则注入安全版式骨架，保持稳定的同时允许后续扩展陌生化视觉。

## 自动审稿

当前 MVP 包含两类审稿：

- 文本密度审稿：检查标题和正文是否过长、是否为空。
- 重复构图审稿：检查连续卡片是否重复使用同一视觉隐喻或构图位置。

审稿结果会写入 `manifest.json`。

## 故障排查

### 找不到核心洞察

检查 `rewritten.md` 是否包含：

```markdown
## 3. 核心洞察
```

当前解析器优先支持 `1. **标题**：正文` 和 `- **标题**：正文` 格式。

### 图片导出失败

确认已安装 Playwright Chromium：

```bash
python3 -m playwright install chromium
```

### 样式不存在

确认 `--style` 参数对应 `distribution_pipeline/styles/{style}.yaml`。

### 平台参数错误

当前支持：

- `all`
- `xhs`
- `wechat`

## 边界约束

该流水线不会修改 `content_archive/` 原始归档内容，也不会修改飞书同步和前端展示逻辑。分发状态如未来需要管理，建议新建独立分发表或 manifest 索引，不复用现有内容展示表。
