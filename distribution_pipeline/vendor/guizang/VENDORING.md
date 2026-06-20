# Guizang Vendor 资产

> 本目录是上游 `op7418/guizang-social-card-skill` 在 Chora 分发流水线内的 **vendoring 副本**。本文件说明：**从哪里来、什么时候同步、复制了什么、排除/修改了什么、Chora 端如何消费**。
>
> 产品介绍参见同目录的 `README.md` / `README.en.md`（与上游一致）。设计哲学与原则参见 `PRODUCT.md` 与 `HANDOFF.md`。

---

## 1. 来源

| 项 | 值 |
|---|---|
| 上游仓库 | <https://github.com/op7418/guizang-social-card-skill> |
| 上游版本 | v0.14（2026-05-28） |
| 同步来源（首次） | 本机 `~/.codex/skills/guizang-social-card-skill` |
| 同步日期 | 2026-06-14 |
| 同步方式 | `rsync -a` 排除 `node_modules/` / `local-tests/` / `.gitignore` / 两个 `template-*.html` |

> 上游协议：AGPL-3.0（参见同目录 `LICENSE`）。本目录仅作 vendoring 用途，未做协议变更。

---

## 2. 目录现状（v0.14 同步后）

```text
vendor/guizang/
├── VENDORING.md                # 本文件：Chora 端的 vendoring 说明
├── README.md / README.en.md    # 上游产品介绍（中/英）
├── SKILL.md                    # 上游 7 步工作流入口
├── PRODUCT.md / HANDOFF.md     # 上游产品哲学与交付记录
├── LICENSE                     # 上游 AGPL-3.0 协议
├── package.json                # 上游：仅声明 playwright 依赖
├── validate-social-deck.mjs    # 上游：6 条规则渲染校验
├── agents/
│   └── openai.yaml             # 上游：备用子代理配置
├── assets/
│   ├── magazine-bg-webgl.js
│   └── screenshot-backgrounds/ # 9 张 .webp 截图舞台底
│       ├── style-a/            #   5 张 Editorial（dune / forest-ink / indigo-porcelain / kraft-paper / monocle-classic）
│       └── style-b/            #   4 张 Swiss（ikb-dot-gradient / lemon-green-dot-shadow / lemon-grid / safety-orange-halftone）
├── references/                 # 15 个子规范（按需读取）
│   ├── background-systems.md
│   ├── category-cookbook.md    # 11 品类版式路由
│   ├── components.md
│   ├── content-planning.md
│   ├── image-overlay.md        # 文字压图：选图 / 局部 tint / 主体映射
│   ├── layout-recipes.md       # 28 个版式骨架（M01-M16 + S01-S12）
│   ├── map-component.md        # Mapbox Static / OSM / schematic
│   ├── platform-specs.md
│   ├── portrait-fill.md
│   ├── production-workflow.md
│   ├── qa-checklist.md
│   ├── screenshot-treatment.md # 截图四件套
│   ├── style-system.md
│   ├── theme-presets.md        # 10 套 palette
│   └── title-shortener.md
├── template-editorial-card.html  # 杂志风种子（**保留 Chora 本地修改**）
└── template-swiss-card.html      # 瑞士风种子（**保留 Chora 本地修改**）
```

文件计数：根目录 11 + agents 1 + assets JS 1 + screenshot-backgrounds 9 + references 15 = **37**（含两个本地保留的 template HTML）。

---

## 3. 同步策略

### 复制（与上游一致）

- 所有 `.md` / `.yaml` / `.json` / `.webp` / `.mjs` / `.js`
- 不做内容改写，不二次翻译

### 排除

| 路径 | 原因 |
|---|---|
| `node_modules/` | 上游 `playwright` 由 Chora 宿主决定装在哪；vendor 不带入 node_modules |
| `local-tests/` | 上游 `.gitignore` 排除；含历史 demo / 用户上传，不分发 |
| `.gitignore` | 上游仓库治理规则，不属运行时资产 |
| `package-lock.json` | 锁定文件随 `playwright` 装包生成；vendor 不需 |

### 保留本地修改（不覆盖）

| 文件 | 本地修改 | 原因 |
|---|---|---|
| `template-editorial-card.html` | `.h-xl / .h-lg` 加 `white-space: pre-line; word-break: keep-all; overflow-wrap: normal;` | 让标题按 `semantic_title_lines` 输出的多行（`\n`）正确换行，避免中英文断词诡异 |
| `template-editorial-card.html` | `[data-theme="midnight-ink"] .mag-bg` 加 `opacity: .66; filter: saturate(.86) contrast(.9);` | midnight-ink 主题：背景降饱和+对比柔化，适配深色主题 |
| `template-editorial-card.html` | `[data-theme="midnight-ink"] .cta-qr img` 加 `filter: invert(1) contrast(1.04);` | midnight-ink 主题：QR 码图反色以保扫码对比度 |
| `template-swiss-card.html` | `.display / .display-sm / .display-md` 加同三行 | 同上 |

如需重新同步本目录，应**先**用 `git diff vendor/guizang/template-*.html` 备份本地修改；**后** rsync；**再**用 patch / apply_patch 恢复本地微调。

---

## 4. Chora 端如何消费

> 运行时请读取本目录中的固定资产，**不要**直接依赖用户本机 `~/.codex/skills/guizang-social-card-skill` 路径。这样可避免本机 skill 更新或缺失导致 Chora 输出漂移。

### 4.1 模板与样式

- 渲染入口 `distribution_pipeline/renderers/guizang/guizang_renderer.py` 复制本目录两个 `template-*.html` 至任务工作目录，再按 `page_planner` 规划的版式注入 `<!-- POSTERS_HERE -->`。
- `recipes.py` 实现 28 个版式骨架中**已实现子集**（M01-M16 杂志风 + S01-S13 瑞士风，含新增 S13 Map · Route）的渲染函数；尚未覆盖的版式在 `docs/guizang-recipe-coverage.md` 中标注。

### 4.2 子规范（references/）

| 子规范 | Chora 端消费点 |
|---|---|
| `category-cookbook.md` | `renderers/guizang/category_router.py`（已对齐 11 类 + 4 类 out-of-scope pushback，详见 `docs/distribution-pipeline.md`） |
| `image-overlay.md` | `renderers/guizang/subject_mapper.py` + `vision_subject_mapper.py`（启发式主体映射已接；vision 通道默认关闭，需环境变量启用；localized tint 仍待加深） |
| `screenshot-treatment.md` | `renderers/guizang/screenshot_treatment.py` + `recipes.py`（`.frame-shot` 六参数、device 包裹、截图检测已接；多截图墙与语义分配仍待补） |
| `map-component.md` | `renderers/guizang/page_planner.py` + `recipes.py` 新增 **S13 Map · Route**：基于文本中的地理/跨境/迁移关键词生成抽象路线卡片；不依赖 Mapbox Static token，使用 CSS/SVG 节点与连线 |
| `layout-recipes.md` | `renderers/guizang/recipes.py` + `page_planner.py` |
| `theme-presets.md` | `renderers/guizang/theme.py` |
| `style-system.md` | `renderers/guizang/recipes.py` 内的字体 / 卡片 / 间距 token |
| `portrait-fill.md` | `recipes.py` 内 `r-*` 比例类 |
| `qa-checklist.md` | `renderers/guizang/validator.py` + `validate-social-deck.mjs`（上游脚本） |
| `production-workflow.md` | `assets/ai_image/gateway.py` + `image_assets.py`（AI 生图兜底已接入 candidates/download；`plan` 默认不生图） |
| 其余 5 个 | 当前未直接消费，作为未来实现的参考 |

### 4.3 截图舞台底（9 张 .webp）

当前 `renderers/guizang/screenshot_treatment.py` 会在截图类素材命中时选择 `.bg-asset-*` / `.frame-shot` / device 包裹；多截图墙与更细的截图语义分配仍未完成。可用舞台底：

- Editorial → `style-a/*.webp`
- Swiss → `style-b/*.webp`

---

## 5. 同步日志

| 日期 | 上游版本 | 触发 | 操作者 | 备注 |
|---|---|---|---|---|
| 2026-06-14 | v0.14 | Chora distribution 接入补全 | Codex | 首版 vendoring：补 SKILL.md / PRODUCT.md / HANDOFF.md / README.{md,en.md} / agents/ / references/ 15 项 / assets/screenshot-backgrounds/ 9 张；保留本地两个 template HTML 白空间修复 |
| 2026-06-15 | v0.14 | vendor 校对 | Codex | LICENSE 实为 AGPL-3.0（§ 1/§ 2 原误记 ISC 已正）；template-editorial-card.html 增 midnight-ink 主题两补丁（`.mag-bg` opacity.66 + saturate.86 contrast.9；`.cta-qr img` invert(1) contrast(1.04)）未入 § 3 表格（待补） |
| 2026-06-17 | v0.14 | Chora 接入状态校对 | Codex | § 4 更新 category / screenshot / image-overlay / AI fallback 实现状态；记录 Playwright 主路径 + wkhtml 兜底策略由 Chora 运行时负责 |

---

## 6. 上游接入剩余 TODO

- Mapbox Static / OSM 地图组件仍未接入，旅行/空间类内容暂不能生成真实路线/地图卡。
- image overlay 的 vision 通道默认关闭；仍需补相对路径素材的常规覆盖、localized tint 细化与 360px 缩略图可读性检查。
- screenshot treatment 已有单图框架，仍需补多截图墙、截图语义分配与更多真实 UI 样例。
- AI fallback 已接入 candidates/download，但 category/theme 传入仍需收束，prompt 与 provenance 需继续强化。
