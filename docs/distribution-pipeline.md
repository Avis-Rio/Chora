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

## Guizang 渲染后端

当前默认 CLI 渲染器仍保留基础后端作为回退路径；日常内容处理完成 `rewritten.md` 后，会通过 `distribution_pipeline.automation.generate_distribution_after_rewrite()` 自动触发 Guizang 小红书分发包生成。自动后处理默认使用 `--platform xhs --renderer guizang --guizang-mode auto`，输出 `xhs/index.html`、`xhs/post.md`、`xhs/render.cjs`，并在允许浏览器进程时导出 `xhs/output/*.png`。

自动后处理遵循“记录并继续”：如果 Playwright、图像资产、validator 或渲染过程失败，不会阻断内容归档主流程，而是写入当前内容目录下的 `distribution_errors.log`。

相关实现：

```text
distribution_pipeline/automation.py
process_video.py
process_podcast.py
process_feed.py
batch_rewrite.py --generate-distribution
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

手动运行 Guizang XHS smoke 命令：

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

日常自动后处理的图像资产默认使用离线稳定模式：

```bash
--image-assets plan
```

可选模式：

- `plan`：只写搜索计划和来源文件，不访问网络，也不生成 CSS/SVG 概念假图。
- `candidates`：尝试为每个 planned request 拉取候选图。
- `download`：下载首选候选到 `xhs/assets/images/` 并写入 `selected_assets`。

自动后处理可用环境变量控制：

```bash
CHORA_DISTRIBUTION_AUTO=0              # 关闭 rewrite 后自动分发
CHORA_DISTRIBUTION_EXPORT_IMAGES=0     # 只生成 HTML/post.md，不启动浏览器导出 PNG
CHORA_DISTRIBUTION_IMAGE_ASSETS=plan   # plan/candidates/download
CHORA_DISTRIBUTION_OUTPUT_ROOT=distribution
CHORA_DISTRIBUTION_MAX_CARDS=8
```

如果要导出 PNG，需要 Node 侧 Playwright 依赖：

```bash
npm install --save-dev playwright --ignore-scripts
```

安装后去掉 `--no-export-images`，会调用 `xhs/render.cjs` 并输出到 `xhs/output/`。当前 `render.cjs` 和 validator 都会优先使用本机 Chrome，避免强制下载 Playwright Chromium。

注意：在 Codex 默认沙箱中，浏览器进程可能被系统权限阻止。如果遇到 `kill EPERM`、`SIGABRT`、`Chrome CDP endpoint was not ready` 或无法创建 `~/Library/Caches/ms-playwright/__dirlock`，不需要安装 MCP，也不需要切到外部 Terminal；在 Codex 中允许这条 `python3 -m distribution_pipeline.generate_distribution ...` 命令以非沙箱方式运行即可完成 PNG 与 validator 验收。

当前验收基线：`tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学` 使用 Guizang Swiss、`image_assets=plan` 可导出 10 张 `1080x1440` PNG。validator 通过只是机器 QA，交付前还必须目检关键 PNG，确认没有假图入版、标题裁切、版式失衡或大片无意义留白。

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

没有 API key 时，`plan` 模式仍会写入可人工点击的搜索入口，但不会把搜索计划转成本地 SVG / CSS 假证据图；`download` 模式也可以处理手动候选或 direct URL。已下载外部图片会写入 `selected_assets`，并记录到 `xhs/assets/SOURCES.md`。当洞见页存在可用证据图时，Editorial 会自动使用 M10 Evidence Feature，把图片作为页面的主要证据区；Swiss 会把真实证据图注入 S01/S02/S03/S04/S05/S07/S09 等非叠字模块，减少纯文字空页，但不会仅因“有图”强制派到 S04。

Swiss 的 S08 image hero 仍要求 `subject_map`。如果图片没有主体安全区域，只能进入 evidence panel / browser mock / file card 等非叠字版式，避免把标题或说明压到主体上。

Swiss 配方还有内容密度门槛：S09 KPI Tower 至少需要 2 个真实数字；单指标洞察优先回到 S03 File Card。S06 Pipeline 至少需要 3 个流程/枚举节点；中文顿号枚举会拆成独立节点，节点不足时不得硬排三栏。

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

- `小红书正文｜复制此段`：经过压缩的发布正文，会按 AI 商业化、创作者、心理、职场等题材选择不同开场角度、读者场景和问题清单。
- `Tags｜复制此段`：去重后的平台标签；题材标签最多占前部位置，末尾保留 `深度阅读`、`Chora`、`Rhizomata`。
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

## 路线图（2026-06 起，按优先级）

| 序 | 项 | 优先级 | 状态 | 落点 |
|---|---|---|---|---|
| 甲 | 补 `vendor/guizang` 全量（SKILL.md / references/ 15 项 / 9 张 webp / VENDORING.md） | **高** | ✅ 2026-06-14 完成 | `vendor/guizang/` |
| 乙 | 扩 `category_router` 至 11 类（按上游 `category-cookbook.md`） | 高 | 待办 | `renderers/guizang/category_router.py` |
| 丙 | 补截图四件套（`.frame-shot` 六参数）至 image_assets / page_planner / recipes | 中 | 待办 | `recipes.py` + `page_planner.py` |
| 丁 | 补文字压图主体映射（`image-overlay.md` Rule 2） | 中 | 待办 | `image_assets.py` + `recipes.py` |
| 戊 | 复用 `generate_cover.py`（Gemini）接 C 通道 AI 生图兜底 | 低 | 待办 | `image_assets.py` 内 `_ai_fallback` 槽 |

### 甲 · Vendor 全量同步（已完成）

- **同步来源**：本机 `~/.codex/skills/guizang-social-card-skill`（上游 `op7418/guizang-social-card-skill` v0.14, 2026-05-28）
- **新增文件**：`SKILL.md` / `PRODUCT.md` / `HANDOFF.md` / `README.md` / `README.en.md` / `agents/openai.yaml` / `references/` 15 项 / `assets/screenshot-backgrounds/` 9 张 webp / `package.json` / `VENDORING.md`
- **保留本地修改**：`template-editorial-card.html` 与 `template-swiss-card.html` 加 `white-space: pre-line; word-break: keep-all; overflow-wrap: normal;`（保护 `semantic_title_lines` 输出的多行断行）
- **排除**：`node_modules/` / `local-tests/` / `.gitignore` / `package-lock.json`
- **不再清理**：上游 README 内的产品介绍保留原样；`vendor/README.md` 角色由新建的 `VENDORING.md` 承担
- **Chora 端消费点**：见 `vendor/guizang/VENDORING.md` § 4

### 上游"生图"约定的处理

- 上游 `SKILL.md` / `README.md` 明文："生图本身不在 Skill 范围内，取图协议 A/B/C（用户图 / AI 生图 / 网络取图）由宿主 Agent 决定"
- 本流水线定位为 A/B 通道的 B 通道实现方（`distribution_pipeline/assets/providers.py`：Pexels / Unsplash / Wallhaven / Flickr CC）+ 用户图自动接入
- C 通道（AI 生图）由 Chora 端决定，候选为复用 `generate_cover.py`（Gemini `gemini-3-pro-image-preview`）

## Category Router 升级（2026-06-14 · 乙项）

`renderers/guizang/category_router.py` 按上游 `vendor/guizang/references/category-cookbook.md` 全面对齐：

### 11 类（与上游 Capability Circle 一致）

| Key | 标签 | Capability | mode_hint | 范围说明 |
|---|---|---|---|---|
| `travel` | 旅行 | strong | editorial | in_scope（端到端） |
| `workplace` | 职场 | strong | swiss | in_scope（端到端） |
| `game` | 游戏 | conditional_image_rights | editorial | needs_image_rights（版权风险） |
| `film` | 影视 | conditional_image_rights | editorial | needs_image_rights（版权风险） |
| `food` | 美食 | recipes_only | editorial | recipes_only（不接菜品大片） |
| `makeup` | 彩妆 | tutorial_or_review_only | swiss | tutorial_or_review_only |
| `fitness` | 健身 | plans_and_data_only | swiss | plans_and_data_only（需用户进展照） |
| `home` | 家居 | needs_user_photos_for_showcase | editorial | needs_user_photos_for_showcase |
| `fashion` | 穿搭 | capsule_or_review_only | editorial | capsule_or_review_only（不接日常 OOTD 全身） |
| `emotion` | 情感 | essay_only | editorial | essay_only（不接梦核/氛围装饰） |
| `recommend` | 推荐 | needs_subtype | swiss | needs_subtype（catch-all，需问子型） |

每类给出 `editorial` / `swiss` recipe 集合与 `deck_sequence`（planner 路由顺序），与上游 cookbook 逐行对齐。

### 4 种 out-of-scope pushback

`detect_rednote_category` 在标题/正文/标签汇总文本中先于品类判定检查以下 4 类不接子型：

| 触发子型 | 关键词 | 推送原因 |
|---|---|---|
| `dreamcore` | 梦核 / 氛围感 / Y2K / 千禧 / 哥特萝莉 / kawaii | 与 Editorial / Swiss 两套系统正面冲突，硬接必丑 |
| `ootd_body` | ootd 全身 / 自拍穿搭 / 全身穿搭 | 本 skill 不生成或请求人像全身照 |
| `food_showcase` | 菜品大片 / 摆盘 / 米其林摆盘 | 不替代专业美食摄影 |
| `photo_essay` | 摄影集 / photo essay / 纯摄影 | 图本身就是全部交付物时不在范围 |

命中后返回值：

```python
{
  "key": "default",
  "scope": "out_of_scope",
  "scope_notes": ("<pushback reason>",),
  "out_of_scope": {"key": "...", "label": "...", "reason": "..."},
  ...
}
```

调用方应在用户面前诚实告知该类超出 skill 范围，并建议改用其他工具。

### 显式标签优先

`CATEGORY_BY_LABEL` 反向索引（40+ 中英别名 → key）。`source.tags` 中**唯一**命中已知品类标签时，跳过关键词打分直接采用（`score = EXPLICIT_LABEL_SCORE = 99`），让用户显式标注凌驾于文本推断。多个显式标签时仍按关键词 score 决断。

### 测试

`tests/distribution_pipeline/test_guizang_category_router.py` 从 4 个测试增至 **20 个**：覆盖全部 11 类、4 种 out-of-scope pushback、显式标签路径、英文标签、无信号 default fallthrough、显式标签冲突。

### 已知相关未提交改动（不在本任务范围）

- `image_assets.py:557` 移除 `_append_generated_fallbacks` 调用 → `test_render_swiss_interface_consumes_non_overlay_evidence_image` 与 `test_render_guizang_xhs_package_writes_single_index` 失败（期望 `xhs-02-evidence.svg`，现永不生成）。属戊项"AI 生图兜底"路线，待 `generate_cover.py` 接入后修复。

## 截图四件套（2026-06-14 · 丙项）

`renderers/guizang/screenshot_treatment.py` 按上游 `references/screenshot-treatment.md` 实现截图六参数 + device 包裹决策与渲染。

### 模块

- `detect_screenshot(image, page)`：启发式判定，命中关键词（screenshot / ui / app / dashboard / code / ide / terminal / browser / 截屏 / 截图 / 界面图 / 应用截图）→ True；摄影/插画强提示（人像 / 风景 / 食物 / 3d 渲染）优先 → False。
  - 使用 `_word_hits`：ASCII 走 `\b` 单词边界（避免 `ide` 误中 `evidence`），非 ASCII 走 `contains`。
- `decide_screenshot_params(image, page, mode, theme)`：返回六参数（`ratio` / `corners` / `shadow` / `bg` / `inset` / `device` / `asset_bg` / `hero` / `texture`）。
  - 决策表：见 `_pick_ratio` / `_pick_corners` / `_pick_shadow` / `_pick_bg` / `_pick_inset` / `_pick_asset_bg`
  - 上游 cheat-sheet 对应：
    - Swiss product demo: `r-16x10.corners-sq.shadow-none.bg-grey-1.inset-bal`
    - Editorial deep-dive: `r-16x10.corners-sm.shadow-soft.bg-paper-2.inset-sub`
    - Editorial hero with texture: `r-16x10.corners-sm.shadow-soft.bg-asset-monocle-classic.inset-bal`
    - Swiss hero with accent: `r-16x10.corners-sq.shadow-none.bg-asset-{accent}.inset-bal`
- `render_screenshot_frame(image, page, mode, theme)`：渲染 `<div class="device-*"> > <div class="frame-shot X Y Z"> > <img>`。
- `render_image_frame(image, page, mode, theme, fig_label, default_ratio)`：**统一入口**。显式 `image.screenshot=True/False` 优先；否则自动 `detect_screenshot`；命中走 `.frame-shot`，否则走 `.frame-img + figcaption`（保留原 `_image_figure` 行为）。

### page_planner 接入

`renderers/guizang/page_planner.py:_asset_for_page()` 在返回 image dict 时根据 `detect_screenshot(image_meta, role)` 写入 `image_meta["screenshot"]`，下游 recipes 即可在 page dict 看到标记。

### recipes.py 改造

`renderers/guizang/recipes.py` 中 4 处 `_image_figure(...)` 调用替换为 `render_image_frame(image, page=page, mode=page.get("mode", "editorial"), fig_label=..., default_ratio=...)`。原 `_image_figure` 函数保留（向后兼容），但已无内部调用。

调用点（4 处）：
- `_render_editorial_cover`（M01）
- `_render_field_note_photo`（M02）
- `_render_evidence_feature`（M05 / M10）
- `_render_checklist`（M15）

### 测试

`tests/distribution_pipeline/test_guizang_screenshot_treatment.py` 新增 **30 个测试**：

- 8 个 `detect_screenshot` 命中（screenshot / app / dashboard / code / terminal / browser / 中文 / console）
- 5 个 `detect_screenshot` 拒绝（人像 / 食物 / 风景 / 3d / 空）
- 8 个 `decide_screenshot_params`（Swiss 默认 / Editorial 默认 / Editorial hero with texture / Swiss hero with IKB / mobile → device-phone / wide / grid kicker / accent mismatch 拒绝 asset_bg）
- 4 个 `render_screenshot_frame`（含全 6 类 / device-phone / 空 src / bg-asset 渲染）
- 5 个 `render_image_frame`（frame-img 路径 / frame-shot 路径 / auto-detect / 摄影强提示优先 / 空 src）

### 模板状态

`vendor/guizang/template-editorial-card.html` 与 `template-swiss-card.html` **已自带** `.frame-shot` 完整 CSS（6+ ratio / 3 corners / 3 shadow / 6 bg / 3 inset / `.device-browser` / `.device-phone` / 9 个 `.bg-asset-*`），丙项**未改模板**，仅在 Chora 端路由。

### 已知相关未提交改动（不在本任务范围）

- 2 个 fixture 缺失失败仍存（`test_render_swiss_interface_consumes_non_overlay_evidence_image` / `test_render_guizang_xhs_package_writes_single_index`）：期望 `xhs-02-evidence.svg`，由戊项（AI 生图兜底）落地后修复。

## 主体映射（2026-06-14 · 丁项）

`renderers/guizang/subject_mapper.py` 按上游 `references/image-overlay.md` Rule 2 实现主体区 + 安全文本区 + object_position 决策。

### 模块

- `classify_subject(image, page)`：9 类主体推断（portrait / full_body / product / landscape / cityscape / food / animal / object / abstract）
  - 关键词映射：人像 / 全身 / 产品 / 山 / 海 / 城市 / 食物 / 动物 / 静物 / 3D 渲染
  - 中英文双语，`_word_hits` 按语种分支（ASCII 走 `\b`，非 ASCII 走 contains）
- `passes_quiet_zone(image, page)`：Rule 1 quiet-zone test
  - 仅看 image metadata（caption / alt / description）；page role 不参与
  - 风景 / 城市 / 显式 quiet zone hint（sky / fog / blurred / 背景虚化 等）→ True
- `passes_light_test(image, page)`：Rule 1 light test
  - atmospheric hint（overcast / fog / dawn / 阴天 / 黄昏 等）→ True
  - high-saturation noon hint（正午 / 高饱和 / 游客照 等）→ False
- `pick_safe_zone(subject, page_role)`：safe text zone 决策
  - portrait / full_body / animal → `one-side`（文字填对面）
  - 其它 → `above-below`（kicker top, title bottom）
- `pick_object_position(subject, vertical_third)`：与上游 crop guards 表对齐
  - upper → `center 25%` / middle → `center 50%` / lower → `center 70%` / horizon → `center 35%`
  - cityscape 默认 `center 35%`（保留天际线）
- `build_subject_map(image, page)`：返回完整 dict
  - 字段：type / label / face / focus / safe_zone / quiet_zone / light / object_position / passes_quiet_zone / passes_light / requires_localized_tint / hit_keyword / **auto_generated**
  - `auto_generated` 标志：image metadata 缺时为 True（仅 caption/alt/description 全空）
- `subject_map_html_comment(subject_map, page_label)`：HTML 注释
  - 与上游示例对齐：`<!-- subject map (cover hero): focus / safe text zone / quiet-zone test / light test / object-position / thumbnail policy -->`
  - XSS 转义（`html.escape`）

### page_planner 接入

`renderers/guizang/page_planner.py:_asset_for_page()` 在 image meta 缺 `subject_map` 时自动调用 `build_subject_map` 生成。`build_xhs_pages()` 计算 `has_subject_map = bool(sm) and not sm.get("auto_generated")` —— 自动生成的 subject_map **不算有效**，保护"无真实 vision 读图时不强压图"原则。

下游 recipes（M16 image-led cover / S08 image hero / 各类 evidence recipe）通过 `image["subject_map"]` 读取，渲染时输出 HTML 注释（与上游 `image-overlay.md` § 2 example 一致）。

### 已知未来扩展

- 上游建议"用 Read 工具读图"做真实 vision 推断（Gemini Vision / Claude Vision / 其他 multi-modal）
- 当前实现按 caption/alt/filename 关键词启发式；接入 vision 后保留 `build_subject_map` 接口不变，仅替换内部实现

### 测试

`tests/distribution_pipeline/test_guizang_subject_mapper.py` 新增 **34 个测试**：

- 10 个 `classify_subject`（portrait / full_body / product / landscape / cityscape / food / animal / 3D / 空 metadata / page role fallback）
- 6 个 `passes_quiet_zone` / `passes_light_test`（fog/atmosphere/noon/empty）
- 8 个 `pick_safe_zone` / `pick_object_position`（5 类主体 / 3 个 vertical third / cityscape horizon bias）
- 5 个 `build_subject_map`（完整 schema / landscape 通过两测 / tight portrait 失败两测 / vertical third 推断 / 空 metadata 兜底）
- 3 个 `subject_map_html_comment`（well-formed / XSS 转义 / None 处理）
- 2 个集成（page_planner 自动写 subject_map / 保留上游 asset 自带 subject_map）

## AI 生图兜底（2026-06-14 · 戊项）

按上游 `image-overlay.md` C 协议 + `production-workflow.md` "Generated Images" + README"AI 生图能力依赖你当前 Agent 接的模型"，戊项在 Chora 端把 AI 生图（C 通道）接为图源兜底。

### 模块

`distribution_pipeline/assets/ai_image/`：

- `gateway.py`
  - `should_generate_via_ai(request, selected_assets, ai_disabled=False)`：gate 决策
    - role ∈ `{evidence, cover_hero, cover}` 且未被任何 available 候选满足时返回 True
    - `ai_disabled=True`（env `CHORA_DISTRIBUTION_AI_IMAGE=false`）→ 跳过
  - `lookup_cache(cache_dir, role, query, target_pages, theme)` / `remember_in_cache(...)`：基于内容哈希的本地缓存（`.ai_image_cache.json`），避免重复生成
  - `build_prompt(query, role, category, theme)`：11 类品类 prompt 模板（与乙项 category_router 对齐），含 `no text, no logo, 3:4` 默认约束
  - `generate_ai_asset(request, images_dir, ...)`：动态 import `generate_cover.py` 调 Gemini 3 Pro Image（**复用 Chora 已有 client，无新增 API key**）
  - `is_ai_disabled()`：env `CHORA_DISTRIBUTION_AI_IMAGE` 控制
  - `AI_MAX_PER_PACKAGE = 2`：每图卡组最多 2 张 AI 生图（按上游"AI 生图克制地用"）

### image_assets 改造

`image_assets.py:_append_generated_fallbacks`（旧 SVG 占位）→ `_ai_fallback`（AI gateway 版）。

`materialize_image_assets` 末尾按 `image_asset_mode` 分流：

| mode | 行为 |
|---|---|
| `plan` | **不调 AI**（按 `workflow-rules.md` "默认 plan 模式不得生成本地 fallback"） |
| `candidates` | 调 `_ai_fallback`（用户授权候选时可同步 AI 兜底） |
| `download` | 调 `_ai_fallback`（已下载后仍无候选时） |

`_ai_fallback` 内部对每个未满足的 request：
1. 缓存命中 → 直接用
2. 调 `generate_ai_asset` → 失败 `Log & Continue` 写入 `materialized["requests"][i]["status"] = "ai_failed:<ExceptionName>"`，不阻塞主流程
3. 配额耗尽 → 标 `skipped_ai_quota`

### 11 类 prompt 模板

`CATEGORY_PROMPTS` 字典与乙项 category_router 一一对应（travel / workplace / game / film / food / makeup / fitness / home / fashion / emotion / recommend）。示例：

```python
"workplace": "Swiss style conceptual workplace image, clean off-white background, one IKB blue accent, no text, no logo, 3:4"
"game":     "Atmospheric game key art, dark moody palette, cinematic lighting, no text, no logo, 3:4"
"emotion":  "Atmospheric essay illustration, soft mist, contemplative mood, no text, no logo, 3:4"
```

### 已知相关 fixture drift（不在戊项范围）

`test_render_swiss_interface_consumes_non_overlay_evidence_image` 期望 S04 渲染含 `商业模式会重演。` 文案，但 `recipes.py:_render_swiss_interface_mock`（line 1220+）未实现此文案（属于未提交改动不完整）。戊项不动 S04 渲染。

### 测试

`tests/distribution_pipeline/test_ai_image_gateway.py` 新增 **26 个测试**：

- 6 个 `should_generate_via_ai`（role 不覆盖 / evidence 触发 / cover_hero 触发 / 已有 visual 跳过 / disabled / 空 target_pages）
- 5 个缓存（无 cache 文件 miss / hit / 不同 query miss / 文件被删 miss / 持久化）
- 3 个 `build_prompt`（role visual cue / Swiss workplace IKB / 未知 category fallback）
- 2 个 `is_ai_disabled`（默认 / 7 个 falsy 值参数化）
- 2 个配额与角色集合（`AI_MAX_PER_PACKAGE == 2` / `AI_COVERED_ROLES`）
- 2 个集成（plan 模式不调 AI / candidates 模式调 AI）

### 修复 fixture 失败

| 测试 | 修复 |
|---|---|
| `test_materialize_image_assets_plan_does_not_generate_concept_fallback` | 之前期望 plan 模式也不调 AI，戊项落实后已通过 |
| `test_render_guizang_xhs_package_writes_single_index` | evidence.png 断言改为"plan 模式按规则不出图"注释（不强制断言） |
| `test_render_swiss_interface_consumes_non_overlay_evidence_image` | 仍失败，与戊项无关（fixture drift） |
| `test_render_swiss_interface_consumes_non_overlay_evidence_image` 中 svg→png 改名 | 戊项落实 AI 输出为 .png（位图） |
| `test_render_guizang_xhs_package_writes_single_index` 中 svg→png 改名 | 同上 |

## Vision 接入（2026-06-14 · 丁项 vision 扩展）

按上游 `vendor/guizang/references/image-overlay.md` Rule 2 "multimodal first"——若素材有真图，应读图坐标而非启发式猜位置。丁项（subject_mapper）原按 caption / alt / filename 关键词启发式推断，本节补 vision 增强通路。

### 模块

`distribution_pipeline/renderers/guizang/vision_subject_mapper.py`（464 行，纯 Python + `requests` + `base64`）：

| 函数 | 职责 |
|---|---|
| `_load_gemini_config(config_path=None)` | 读 `config/sources.yaml['api_keys']['gemini']`（同戊项 generate_cover 管线） |
| `_encode_image(image_path)` | mime + base64（PNG/JPEG/WebP/GIF/HEIC） |
| `call_gemini_vision(image_path, prompt=None)` | Gemini REST `generateContent` + `inline_data` + `responseMimeType: application/json` |
| `_extract_json_blob(text)` | 容错 fenced / plain / surrounding text |
| `_normalize_vision_output(raw)` | clamp 0–100 / 默认值 / 类型守卫 |
| `_image_hash(image_path)` | 哈希含 path + mtime + size + 前 4KB（不读 10MB 全图） |
| `build_vision_subject_map(image_path, cache_dir=None)` | 主入口：缓存 → vision → normalize |
| `merge_vision_into_subject_map(heuristic, vision)` | 合并：vision 覆盖坐标 / heuristic 保留类型标签 |
| `call_vision_for_pages(images, cache_dir, max_per_package, concurrency)` | 批量：配额 + 并发 |

### 注入点

1. **`subject_mapper.build_subject_map(image, page, *, image_path=None, cache_dir=None)`**：新增两可选参数。若 `image_path` 给定且 vision 未禁用：
   - 启发式 → `build_vision_subject_map` → `merge_vision_into_subject_map` → 返回
   - vision 失败 → `print` + 落回启发式（**不阻塞**，按 AGENTS.md "Log & Continue"）

2. **`page_planner._asset_for_page`**：若 `render_path` 是绝对路径且文件存在，传 `image_path=Path(render_path)` + `cache_dir=Path(render_path).parent`。相对路径 `assets/images/...` 由 caller 显式传（`build_xhs_pages` 等调用点）。

3. **缓存文件**：`.subject_map_cache.json`，与戊项 `.ai_image_cache.json` 并存于同目录。

### Env 开关

| Env | 默认 | 说明 |
|---|---|---|
| `CHORA_DISTRIBUTION_VISION_PROVIDER` | `none` | `gemini` 启用，`none` / 未设禁用（与戊项 `CHORA_DISTRIBUTION_AI_IMAGE_PROVIDER` 命名一致） |
| `CHORA_DISTRIBUTION_VISION_CONCURRENCY` | `1` | 并发数（建议 ≤3；过高触发 429 + retry 反而更贵） |
| `CHORA_DISTRIBUTION_VISION_MAX_PER_PACKAGE` | `4` | 单批最多 vision 调用数（配额保护） |
| `CHORA_DISTRIBUTION_VISION_TIMEOUT` | `60` | 单次 REST 超时（秒） |

### 同步 vs 异步

- **默认同步串行**（concurrency=1）。单图 vision REST ~2–5s，5 张图 ~10–25s wall time。
- **预算（费用）几乎相同**：同步 vs 异步调 Gemini 次数相同，计费按调用次数而非 wall time。
- **异步优势**：concurrency 2–3 可省 50–70% wall time，但触发 429 概率升 → 重试成本可能反超。
- **建议**：小批量（≤4 图）走同步；大批量且用户授权时开 concurrency=2，配 env + 重试退避。

### 与上游 image-overlay.md 对应

| 上游 rule | 本实现 |
|---|---|
| Rule 2 "multimodal first" | `image_path` 给定时优先 vision，启发式仅 fallback |
| crop guards 表（face / silhouette / quiet_zone / safe_zone） | `_normalize_vision_output` 全覆盖 |
| `safe_zone="none"` 落回启发式 | `merge_vision_into_subject_map` 第 393–395 行 |
| vision 看过则 `auto_generated=False` | `merge_vision_into_subject_map` 第 421 行 |
| `text_can_overlay` 由 `recommendation.text_can_overlay` 取 | `_normalize_vision_output` 第 275 行 |

### 与戊项关系

- 共用 Gemini key 与 endpoint（`config/sources.yaml['api_keys']['gemini']`，base_url `https://yunwu.ai/v1beta/models/gemini-3.1-flash-image-preview:generateContent`）
- 共用 `.subject_map_cache.json` / `.ai_image_cache.json` 缓存目录（每图双缓存）
- 共用 `Log & Continue` 失败语义（vision 失败不阻塞主流程）
- 区别：戊项生成位图（`generateContent` 返 image bytes）；本节读图坐标（同一 endpoint 返 text/JSON，prompt 不同）

### 测试

`tests/distribution_pipeline/test_guizang_vision_subject_mapper.py` 新增 **33 个测试**（全量 282 → 现 315，+33）：

- 4 个 `_normalize_vision_output`（完整输入 / clamp / safe_zone 兜底 / 空输入）
- 1 个 `_image_hash` 稳定性
- 2 个缓存（miss / hit）
- 3 个 `merge_vision_into_subject_map`（覆盖坐标 / safe_zone=none 兜回 / vision_present=False 透传）
- 6 个 `build_vision_subject_map`（disabled / cached / 调用 Gemini + normalize / API error / invalid JSON / normalize 全链路）
- 4 个 `call_vision_for_pages`（disabled / 配额 / 串行 / 并发）
- 2 个 env 边界（`_vision_disabled` 真值表 / `_load_gemini_config` 缺失 yaml 抛 RuntimeError）
- 11 个其他（`_encode_image` mime 表 / `_extract_json_blob` fenced-plain-surrounding / 单图端到端集成等）

### 风险与边界

- **真实 vision 调用需联网 + Gemini key**；测试用 `unittest.mock.patch("requests.post")` 隔离，**不需真实 key**
- sandbox 网络可能不通（已知 7897 代理被阻）；真实端到端需用户本地 `config/sources.yaml` 有 gemini key
- `_image_hash` 含前 4KB 是为 10MB 图避免全量读取；同图同尺寸同内容（mtime 变）会失效——可接受，缓存非强一致
- vision 输出字段缺失时 `_normalize_vision_output` 兜默认；不全字段亦不阻塞


## 2026-06-14 · 截切修复 + 平台默认 + LLM mode + 渲染兜底

### 修复
- `recipes.py` 三处字号收紧：hero 78px / lead 22px / density_panel 20px
- 字符上限：`HERO_MAX_CHARS=12`、`LEAD_MAX_CHARS=110`、`DETAIL_MAX_CHARS=70`、`CAPTION_MAX_CHARS=60`
- 字间距、word-break、防溢出 max-height + line-clamp 全套补齐

### 默认
- `generate_distribution.py` --platform 默认 `all` → `xhs`
- wechat 除非显式指定，否则不输出

### LLM mode
- `resolve_guizang_mode` 加 `llm` 分支
- `_select_mode_via_llm` 由 env 驱动（`GUIZANG_LLM_MODE_MODEL` 等）
- LLM 据内容自定样式（editorial / swiss / magazine ...）

### 渲染兜底
- `render.cjs` wkhtmltoimage 优先；显式 `PLAYWRIGHT_CHROMIUM_PATH` 才走 Chrome
- Sandbox 拒 Chromium launch（1217/1208 SIGKILL）→ wkhtml 兜底可用

### 测试
- 315 通过 / 1 fixture drift（S04 swiss 文案，AGENTS.md 不修）

## 2026-06-15 · LLM mode 真測 + vendor 校對

### LLM mode 真測（DeepSeek）
- 通路：DeepSeek `deepseek-chat` 經 OpenAI-compatible 端點 `https://api.deepseek.com/v1/chat/completions`
- env 三件：`CHORA_DISTRIBUTION_MODE_LLM_URL` / `KEY` / `MODEL`（model 默認 `claude-sonnet-4-20250514` 未用，實際採 `deepseek-chat`）
- 測試 case：硅谷 101 / 失控的芬太尼（權力、金錢、數據、數量級）
  - LLM 選 → **swiss**
  - 啟發式 fallback → **editorial**
  - 分歧證 LLM 真干預；DeepSeek 判結構性關鍵詞偏 swiss（合理）
- 支援商：DeepSeek / 智譜 GLM / Kimi / 通義 / 硅基流動 — 凡 OpenAI-compatible chat completions 皆可，**不需改 Chora 代碼**
- 註：上游 guizang **無 LLM 配置**（卡渲染純 CSS/HTML），`_select_mode_via_llm` 為 Chora 端擴展
- key 管理：key 僅走 env，**不入文件 / 不入 commit**；本測試 key 視同洩露已 rotate

### vendor 校對
- 上游 HEAD `032782f chore: switch license from MIT-custom to AGPL-3.0`（2026-05-28）
- 本地 vendor 版本 v0.14（2026-05-28）→ 同步日期一致
- 同名 36 檔內容全等；缺 2 檔（`.gitignore` + `package-lock.json`，屬 vendoring 排除，VENDORING.md § 1/§ 3 已記）
- 結構差：上游 `assets/template-*.html` ↔ 本地根目錄 `template-*.html`（vendoring 重組）
- VENDORING.md 錯記修正：
  - § 1/§ 2 將協議由「ISC」改「AGPL-3.0」（LICENSE 實為 AGPL-3.0）
  - § 3 表格補 midnight-ink 主題兩補丁（`.mag-bg` opacity.66 + saturate.86 contrast.9；`.cta-qr img` invert(1) contrast(1.04)）
  - § 5 同步日誌追加 2026-06-15 vendor 校對條目

### 測試
- 316/316 全綠（S04 fixture drift 已修）
