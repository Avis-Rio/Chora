# Guizang 渲染后端接入 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `guizang-social-card-skill` 融合进 Chora 分发素材生成层，使同一篇 AI 改写文章可以稳定生成小红书 3:4 卡片组和微信公众号 21:9 + 1:1 封面对，同时保留现有基础渲染器作为回退。

**Architecture:** Chora 继续负责内容解析、核心洞见、视觉导演稿和平台文案；Guizang 作为第二代视觉渲染后端，负责单文件多画板 HTML、Editorial/Swiss 风格系统、Playwright PNG 导出和自动视觉校验。接入方式采用项目内 vendor 最小资产，运行时不依赖用户本机 `.codex/skills` 路径。

**Tech Stack:** Python 3、pytest、HTML/CSS seed template、Node.js、Playwright、Guizang vendored templates、现有 `distribution_pipeline/` 数据中间层、现有 `content_archive/` 归档结构。

---

## 当前状态

- [x] 可行性评估完成：Guizang 适合作为 Chora 的第二代视觉渲染后端。
- [x] 实施计划已创建：`docs/plans/2026-05-31-guizang-renderer-integration.md`。
- [x] 阶段 0：Vendor 资产与许可边界。
- [x] 阶段 1：CLI 渲染后端开关。
- [x] 阶段 2：Guizang 页面计划中间层。
- [x] 阶段 3：小红书 Editorial HTML spike。
- [x] 阶段 4：Guizang PNG 导出。Codex 非沙箱审批路径已完成真实文章 PNG 导出。
- [x] 阶段 5：自动视觉校验接入 manifest。真实文章 validator 已达到 `pass`。
- [x] 阶段 5A：图像证据层一期。已生成 `image_assets.json`、`xhs/assets/SOURCES.md`，并把本地封面接入 Guizang M01 图文封面；外部图源搜索入口覆盖 Pexels、Unsplash、Wallhaven、Flickr CC。
- [x] 阶段 5B：外部图片候选与下载器一期。已支持手动候选、Pexels/Unsplash/Wallhaven provider adapter、下载落地、`selected_assets` 来源记录，以及有证据图时自动切换 Guizang M10 Evidence Feature。
- [x] 阶段 5C：经验规则固化一期。已沉淀 `docs/guizang-workflow-rules.md` 和 `docs/guizang-recipe-coverage.md`，并把短文本不回落 M03、语义配图优先级、closing 不叠 Archive Index 等问题转成规则与回归测试。
- [x] 阶段 5D：Editorial recipe renderer 补全。已补 M02/M05/M06/M12/M15/M16 renderer；M05/M15 已接保守 planner 路由，M16 需 subject map 才渲染 full-bleed。
- [x] 阶段 6：微信公众号封面对。已接入 `wechat/index.html`、`appendix.md`、`render.cjs`，同文件生成 21:9 主封面、1:1 方形封面与 pair preview；1:1 使用独立短标题，21:9 使用近完整单行标题。
- [ ] 阶段 7：真实文章端到端验收。小红书 Guizang 与微信 Guizang 已可同时生成，待完成多文章全平台抽检。
- [ ] 阶段 8：完整 Guizang Skill 覆盖。阶段 8A 已补 Swiss S01-S12 专属 renderer 与 Swiss planner 路由；阶段 8B 已接 category cookbook 识别、scope notes 与 deck sequence；阶段 8C 已给 S08/M16 加 subject-map gate；阶段 8D 已接图上叠字静态 QA；阶段 8E 已接 Swiss 真实数值抽取与 proxy metric 标记；剩余为多文章全平台抽检、真实 360px thumbnail 像素 QA、screenshot/map 资产。

每完成一个阶段，需要在本节更新对应勾选状态，并在阶段末尾补充验证命令与结果。

阶段 6 验证记录：

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/pytest tests/distribution_pipeline/test_guizang_wechat_renderer.py tests/distribution_pipeline/test_generate_distribution_cli.py tests/distribution_pipeline/test_manifest.py
```

Result: `12 passed in 0.14s`

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/pytest tests/distribution_pipeline
```

Result: `114 passed in 0.47s`

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m distribution_pipeline.generate_distribution "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" --platform wechat --renderer guizang --guizang-mode editorial --guizang-theme auto --image-assets plan --output-root /private/tmp/chora-guizang-wechat-export-v3
```

Result: 生成 `wechat-21x9-cover.png`、`wechat-1x1-cover.png`、`wechat-cover-pair-preview.png`；尺寸分别为 2100x900、1080x1080、2400x844；manifest 记录 `png_count: 3`，Guizang validator `status: pass`，`0 fails · 0 warns`。

阶段 8A 验证记录：

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/pytest tests/distribution_pipeline/test_guizang_recipes.py tests/distribution_pipeline/test_guizang_page_planner.py
```

Result: `60 passed in 0.13s`

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/pytest tests/distribution_pipeline
```

Result: `132 passed in 0.42s`

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m distribution_pipeline.generate_distribution tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学 --platform xhs --renderer guizang --guizang-mode swiss --guizang-theme auto --cards 8 --output-root /private/tmp/chora-guizang-swiss-export-v8
```

Result: 生成 5 张 Swiss 小红书 PNG；manifest 记录 `png_count: 5`，Guizang validator `status: pass`，`5 clean · 0 fails · 0 warns`。

阶段 8B-8E 验证记录：

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/pytest tests/distribution_pipeline/test_guizang_category_router.py tests/distribution_pipeline/test_guizang_page_planner.py tests/distribution_pipeline/test_guizang_recipes.py tests/distribution_pipeline/test_guizang_validator.py -q
```

Result: `74 passed in 0.19s`

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/pytest tests/distribution_pipeline -q
```

Result: `141 passed in 0.53s`

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m distribution_pipeline.generate_distribution tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学 --platform xhs --renderer guizang --guizang-mode swiss --guizang-theme auto --cards 8 --output-root /private/tmp/chora-guizang-swiss-export-v12
```

Result: 生成 5 张 Swiss 小红书 PNG；每张 `1080x1440`；manifest 记录 `png_count: 5`，Guizang validator `status: pass`，静态 QA 记录 `PASS R8 no text-on-image block detected`、`PASS R10 no banned full-canvas black image mask`、`PASS R11 Swiss proxy metric scales are explicitly labelled`。

运行环境结论：

- `render.cjs` 和 `validate-social-deck.mjs` 都依赖 Node 侧 `playwright` 包。当前 Node 可解析 `/Users/Avis/node_modules/playwright`，说明包已安装。
- Codex 默认沙箱无法启动/管理浏览器进程：Playwright 启动本机 Chrome 时触发 `kill EPERM` / `SIGABRT`，Chrome CDP fallback 也无法打开调试端点。
- 这不是 MCP 问题，也不是分发管线业务逻辑问题；根因是浏览器截图进程权限。
- 在 Codex 内使用非沙箱审批运行同一条 `python3 -m distribution_pipeline.generate_distribution ...` 命令，真实文章已完成 8 张 PNG 导出与 validator `pass`。后续无需切到外部 Terminal，但需要允许 Codex 对生图命令执行一次非沙箱授权。

---

## 设计原则

1. **稳定优先**：保留 `--renderer basic`，新增 `--renderer guizang`，任何 Guizang 生成失败都不破坏现有 MVP。
2. **运行时可移植**：不要从 `/Users/Avis/.codex/skills/...` 直接读取模板。需要复制最小必要资产到 `distribution_pipeline/vendor/guizang/`，并保留许可证。
3. **内容中间层不重写**：继续复用 `source.json`、`insights.json`、`visual_system.json`、`visual_briefs.json`，避免另起一套文章解析逻辑。
4. **单文件多画板**：Guizang 后端输出 `xhs/index.html` 和 `wechat/index.html`，而不是当前基础后端的一张卡一个 HTML。
5. **审美变化可控**：陌生化来自 recipe 路由、视觉隐喻、主题、版式节奏和证据层，而不是随机颜色、随机字体或破坏可读性的排版。
6. **测试分层**：默认单元测试不强制安装 Playwright；真实 PNG 导出与 validator 作为可选集成测试或手动验收命令。
7. **经验规则先行**：任何新 recipe、图源策略或主题路由，都必须先对照 `docs/guizang-workflow-rules.md`；若修复过的失败形态可能复发，需要补回归测试。

---

## 目标输出结构

Guizang 后端启用后，输出目录建议如下：

```text
distribution/{slug}/
├── source.json
├── insights.json
├── visual_system.json
├── visual_briefs.json
├── xhs/
│   ├── index.html
│   ├── render.cjs
│   ├── post.md
│   └── output/
│       ├── xhs-01-cover.png
│       ├── xhs-02-insight.png
│       └── ...
├── wechat/
│   ├── index.html
│   ├── render.cjs
│   ├── appendix.md
│   └── output/
│       ├── wechat-21x9-cover.png
│       ├── wechat-1x1-cover.png
│       └── wechat-cover-pair-preview.png
└── manifest.json
```

基础后端继续保持当前结构：

```text
xhs/cards/*.html
wechat/hero.html
wechat/inline_*.html
```

---

## 建议命令形态

保留现有命令：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform all \
  --style chora-editorial \
  --cards 8 \
  --no-export-images
```

新增 Guizang 后端：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform all \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8
```

参数语义：

- `--renderer basic|guizang`：默认 `basic`，保证向后兼容。
- `--style`：继续用于基础后端。
- `--guizang-mode editorial|swiss`：选择 Guizang 视觉系统。
- `--guizang-theme`：Editorial 使用 `ink-classic`、`indigo-porcelain`、`forest-ink`、`kraft-paper`、`dune`、`midnight-ink`；Swiss 使用 `ikb`、`lemon-yellow`、`lemon-green`、`safety-orange`。
- `--no-export-images`：仍然控制是否导出 PNG。对 Guizang 后端而言，不导出时只生成 `index.html`、`render.cjs` 与文案文件。

---

## 阶段 0：Vendor 资产与许可边界

### Task 0.1: 复制 Guizang 最小资产

**Files:**
- Create: `distribution_pipeline/vendor/guizang/LICENSE`
- Create: `distribution_pipeline/vendor/guizang/template-editorial-card.html`
- Create: `distribution_pipeline/vendor/guizang/template-swiss-card.html`
- Create: `distribution_pipeline/vendor/guizang/magazine-bg-webgl.js`
- Create: `distribution_pipeline/vendor/guizang/validate-social-deck.mjs`
- Create: `distribution_pipeline/vendor/guizang/README.md`

**Step 1: 复制资产**

从本机 skill 目录复制以下文件：

```text
/Users/Avis/.codex/skills/guizang-social-card-skill/LICENSE
/Users/Avis/.codex/skills/guizang-social-card-skill/assets/template-editorial-card.html
/Users/Avis/.codex/skills/guizang-social-card-skill/assets/template-swiss-card.html
/Users/Avis/.codex/skills/guizang-social-card-skill/assets/magazine-bg-webgl.js
/Users/Avis/.codex/skills/guizang-social-card-skill/validate-social-deck.mjs
```

`README.md` 需要用中文说明：

- 这些文件 vendored 自 `guizang-social-card-skill`。
- 运行时读取项目内 vendor 文件，不读取用户本机 skill 目录。
- 更新上游资产时需要同步许可证和变更说明。

**Step 2: 写资产存在性测试**

Create: `tests/distribution_pipeline/test_guizang_vendor.py`

```python
from pathlib import Path


VENDOR = Path("distribution_pipeline/vendor/guizang")


def test_guizang_vendor_assets_exist():
    expected = [
        "LICENSE",
        "template-editorial-card.html",
        "template-swiss-card.html",
        "magazine-bg-webgl.js",
        "validate-social-deck.mjs",
        "README.md",
    ]

    for name in expected:
        assert (VENDOR / name).exists(), name
```

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_vendor.py -v
```

Expected: PASS.

**Step 4: 更新状态**

将“阶段 0”勾选为完成，并记录测试结果。

**验证记录：**

```bash
pytest tests/distribution_pipeline/test_guizang_vendor.py -v
```

Result: `1 passed in 0.16s`

---

## 阶段 1：CLI 渲染后端开关

### Task 1.1: 为 CLI 添加 renderer 参数

**Files:**
- Modify: `distribution_pipeline/generate_distribution.py`
- Test: `tests/distribution_pipeline/test_generate_distribution_cli.py`

**Step 1: 写 failing test**

增加测试，验证 `run()` 接收并透传 `renderer="basic"` 时行为不变。

```python
from pathlib import Path

from distribution_pipeline.generate_distribution import run


def test_basic_renderer_still_generates_current_shape(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")

    output = run(
        content,
        output_root=tmp_path,
        platform="xhs",
        renderer="basic",
        export_images=False,
    )

    assert (output / "xhs" / "cards" / "01-cover.html").exists()
    assert (output / "xhs" / "post.md").exists()
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_generate_distribution_cli.py::test_basic_renderer_still_generates_current_shape -v
```

Expected: FAIL with `TypeError: run() got an unexpected keyword argument 'renderer'`.

**Step 3: 实现最小改动**

在 `run()` 增加参数：

```python
renderer: str = "basic",
guizang_mode: str = "editorial",
guizang_theme: str = "indigo-porcelain",
```

在 CLI 增加：

```python
parser.add_argument("--renderer", default="basic", choices=["basic", "guizang"])
parser.add_argument("--guizang-mode", default="editorial", choices=["editorial", "swiss"])
parser.add_argument("--guizang-theme", default="indigo-porcelain")
```

第一步只让 `basic` 走现有逻辑，`guizang` 暂时抛出清晰错误：

```python
if renderer == "guizang":
    raise NotImplementedError("Guizang renderer is not implemented yet")
if renderer != "basic":
    raise ValueError(f"Unknown renderer: {renderer}")
```

**Step 4: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_generate_distribution_cli.py -v
```

Expected: PASS.

### Task 1.2: 更新文档命令说明

**Files:**
- Modify: `docs/distribution-pipeline.md`

**Step 1: 增加 Guizang 后端小节**

说明 `--renderer basic` 与 `--renderer guizang` 的关系，以及 Guizang 暂未完成时的阶段状态。

**Step 2: 文档检查**

Run:

```bash
grep -n "Guizang" docs/distribution-pipeline.md
```

Expected: 至少出现新增小节标题与示例命令。

**Step 3: 更新状态**

将“阶段 1”勾选为完成，并记录测试结果。

**验证记录：**

```bash
pytest tests/distribution_pipeline/test_generate_distribution_cli.py::test_basic_renderer_still_generates_current_shape -v
```

Result: 首次按预期失败，错误为 `TypeError: run() got an unexpected keyword argument 'renderer'`。

```bash
pytest tests/distribution_pipeline/test_generate_distribution_cli.py -v
```

Result: `3 passed in 0.66s`

---

## 阶段 2：Guizang 页面计划中间层

### Task 2.1: 定义 Guizang 页面计划结构

**Files:**
- Create: `distribution_pipeline/renderers/guizang/__init__.py`
- Create: `distribution_pipeline/renderers/guizang/page_planner.py`
- Test: `tests/distribution_pipeline/test_guizang_page_planner.py`

**Step 1: 写 failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.page_planner import build_xhs_pages


def test_build_xhs_pages_uses_cover_insights_and_closing(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    pages = build_xhs_pages(package, max_cards=6, mode="editorial")

    assert pages[0]["id"] == "xhs-01"
    assert pages[0]["role"] == "cover"
    assert pages[-1]["role"] == "closing"
    assert len(pages) <= 6
    assert all(page["recipe"].startswith("M") for page in pages)
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_page_planner.py::test_build_xhs_pages_uses_cover_insights_and_closing -v
```

Expected: FAIL with `ModuleNotFoundError`.

**Step 3: 实现页面计划**

`build_xhs_pages(package, max_cards, mode)` 返回 list[dict]：

```python
{
    "id": "xhs-02",
    "platform": "xhs",
    "role": "insight",
    "recipe": "M03",
    "title": "...",
    "body": "...",
    "kicker": "Insight 02",
    "footer": "Chora · Rhizomata",
    "insight_index": 1,
}
```

Editorial 初始 recipe 路由：

- cover -> `M01`
- insight -> 依次使用 `M03`、`M04`、`M08`、`M11`
- concept-map -> `M14`
- closing -> `M07`

Swiss 初始 recipe 路由：

- cover -> `S01`
- insight -> 依次使用 `S03`、`S04`、`S07`
- concept-map -> `S09`
- closing -> `S12`

**Step 4: 加入去重复规则**

连续两页不能使用同一个 recipe。若路由结果重复，切换到同模式候选池中的下一个。

**Step 5: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_page_planner.py -v
```

Expected: PASS.

### Task 2.2: 增加 Guizang 主题校验

**Files:**
- Create: `distribution_pipeline/renderers/guizang/theme.py`
- Test: `tests/distribution_pipeline/test_guizang_theme.py`

**Step 1: 写 failing test**

```python
import pytest

from distribution_pipeline.renderers.guizang.theme import resolve_theme


def test_resolve_editorial_theme():
    theme = resolve_theme("editorial", "indigo-porcelain")

    assert theme == {"attribute": "data-theme", "value": "indigo-porcelain"}


def test_reject_theme_from_wrong_mode():
    with pytest.raises(ValueError, match="not valid for guizang mode"):
        resolve_theme("editorial", "ikb")
```

**Step 2: 实现主题白名单**

Editorial：

```python
{"ink-classic", "indigo-porcelain", "forest-ink", "kraft-paper", "dune", "midnight-ink"}
```

Swiss：

```python
{"ikb", "lemon-yellow", "lemon-green", "safety-orange"}
```

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_theme.py -v
```

Expected: PASS.

**Step 4: 更新状态**

将“阶段 2”勾选为完成，并记录测试结果。

**验证记录：**

```bash
pytest tests/distribution_pipeline/test_guizang_page_planner.py tests/distribution_pipeline/test_guizang_theme.py tests/distribution_pipeline/test_guizang_template_loader.py tests/distribution_pipeline/test_guizang_recipes.py -q
```

Result: `12 passed in 0.63s`

---

## 阶段 3：小红书 Editorial HTML Spike

### Task 3.1: 实现 template loader

**Files:**
- Create: `distribution_pipeline/renderers/guizang/template_loader.py`
- Test: `tests/distribution_pipeline/test_guizang_template_loader.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.guizang.template_loader import load_template


def test_load_editorial_template_contains_placeholder():
    html = load_template("editorial")

    assert "<!-- POSTERS_HERE -->" in html
    assert "data-theme" in html
```

**Step 2: 实现模板读取**

读取：

- `distribution_pipeline/vendor/guizang/template-editorial-card.html`
- `distribution_pipeline/vendor/guizang/template-swiss-card.html`

只允许 `editorial` 和 `swiss`。未知 mode 抛 `ValueError`。

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_template_loader.py -v
```

Expected: PASS.

### Task 3.2: 实现基础 recipe HTML 片段

**Files:**
- Create: `distribution_pipeline/renderers/guizang/recipes.py`
- Test: `tests/distribution_pipeline/test_guizang_recipes.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.guizang.recipes import render_page_section


def test_render_editorial_cover_section():
    page = {
        "id": "xhs-01",
        "platform": "xhs",
        "role": "cover",
        "recipe": "M01",
        "title": "Token 经济学正在改写 AI 成本",
        "body": "强模型不只是更贵，也可能更省。",
        "kicker": "Issue 01",
        "footer": "Chora · Rhizomata",
    }

    html = render_page_section(page, mode="editorial")

    assert 'class="poster xhs"' in html
    assert 'id="xhs-01"' in html
    assert "Token 经济学" in html
    assert "mag-bg" in html
```

**Step 2: 实现最小 recipe**

先支持 Editorial：

- `M01` cover
- `M03` insight essay
- `M04` pull quote
- `M07` closing
- `M08` tall ledger
- `M11` marginalia essay
- `M14` vertical pipeline

实现要点：

- 使用 `html.escape()` 处理用户内容。
- 每个 section 必须有 `section.poster.xhs`。
- Editorial 页面包含 `<canvas class="mag-bg" data-bg="ink-flow"></canvas>` 和 `<div class="grain"></div>`。
- 不在图片内写使用说明或快捷键。

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_recipes.py -v
```

Expected: PASS.

### Task 3.3: 生成小红书 `index.html`

**Files:**
- Create: `distribution_pipeline/renderers/guizang/guizang_renderer.py`
- Modify: `distribution_pipeline/generate_distribution.py`
- Test: `tests/distribution_pipeline/test_guizang_renderer.py`

**Step 1: 写 failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_xhs_package


def test_render_guizang_xhs_package_writes_single_index(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    written = render_guizang_xhs_package(
        package,
        tmp_path / "pkg",
        max_cards=6,
        mode="editorial",
        theme="indigo-porcelain",
    )

    html_path = tmp_path / "pkg" / "xhs" / "index.html"
    assert html_path in written
    html = html_path.read_text(encoding="utf-8")
    assert 'data-theme="indigo-porcelain"' in html
    assert html.count('class="poster xhs"') >= 2
    assert (tmp_path / "pkg" / "xhs" / "post.md").exists()
```

**Step 2: 实现 renderer**

`render_guizang_xhs_package()`：

1. 调用 `build_xhs_pages()`。
2. 调用 `load_template(mode)`。
3. 将页面 sections 拼接后替换 `<!-- POSTERS_HERE -->`。
4. 设置 `<html data-theme="...">` 或 `<html data-accent="...">`。
5. 写入 `xhs/index.html`。
6. 复用现有 `_build_post_md()` 逻辑，写入 `xhs/post.md`。

**Step 3: 接入 CLI**

`generate_distribution.run()` 中：

- `renderer == "basic"`：走当前 `render_xhs_package()` / `render_wechat_package()`。
- `renderer == "guizang"` 且 platform 包含 xhs：走 `render_guizang_xhs_package()`。
- wechat 先允许抛 `NotImplementedError`，但错误要明确：“Guizang wechat renderer is planned in phase 6”。

**Step 4: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_renderer.py tests/distribution_pipeline/test_generate_distribution_cli.py -v
```

Expected: PASS.

**Step 5: 真实文章无图片导出 smoke test**

Run:

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform xhs \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --no-export-images \
  --output-root /private/tmp/chora-guizang-smoke
```

Expected:

```text
Distribution package generated: /private/tmp/chora-guizang-smoke/...
```

检查：

```bash
find /private/tmp/chora-guizang-smoke -maxdepth 4 -type f | sort
```

Expected: 包含 `xhs/index.html`、`xhs/post.md` 和基础 JSON 中间层。

**Step 6: 更新状态**

将“阶段 3”勾选为完成，并记录测试与 smoke test 结果。

**验证记录：**

```bash
pytest tests/distribution_pipeline/test_guizang_renderer.py tests/distribution_pipeline/test_generate_distribution_cli.py tests/distribution_pipeline/test_manifest.py -q
```

Result: `7 passed in 1.74s`

真实文章 smoke test:

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform xhs \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --no-export-images \
  --output-root /private/tmp/chora-guizang-smoke
```

Result:

```text
Distribution package generated: /private/tmp/chora-guizang-smoke/youtube_硅谷101_谷歌AI的14年-Gemini翻身之战-与视觉理解模型-专访DeepMind前核心科学家Andrew
```

输出检查：

- `xhs/index.html` 已生成。
- `xhs/post.md` 已生成。
- `xhs/assets/magazine-bg-webgl.js` 已复制。
- `manifest.json` 已记录 `html_files: ["xhs/index.html"]`。
- `xhs/index.html` 保留 seed template 的 `Theme tokens` CSS 和 `Magazine WebGL background` 脚本区，避免误替换顶部说明注释里的 `POSTERS_HERE`。

---

## 阶段 4：Guizang PNG 导出

### Task 4.1: 生成平台专用 render.cjs

**Files:**
- Create: `distribution_pipeline/renderers/guizang/render_script.py`
- Test: `tests/distribution_pipeline/test_guizang_render_script.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.guizang.render_script import build_render_script


def test_build_xhs_render_script_targets_posters():
    script = build_render_script(
        html_name="index.html",
        targets=[{"selector": "#xhs-01", "filename": "xhs-01-cover.png"}],
    )

    assert "#xhs-01" in script
    assert "xhs-01-cover.png" in script
    assert "chromium.launch" in script
```

**Step 2: 实现脚本生成**

脚本需要：

- 使用 `playwright`。
- 打开当前目录下 `index.html`。
- 等待字体、图片和 900ms 背景渲染。
- 截取每个目标 selector。
- 输出到 `output/`。
- 校验截图节点存在，否则退出码 1。

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_render_script.py -v
```

Expected: PASS.

### Task 4.2: Python 侧调用 render.cjs

**Files:**
- Create: `distribution_pipeline/renderers/guizang/exporter.py`
- Test: `tests/distribution_pipeline/test_guizang_exporter.py`

**Step 1: 写 failing test**

```python
from pathlib import Path

from distribution_pipeline.renderers.guizang.exporter import discover_guizang_render_scripts


def test_discover_guizang_render_scripts(tmp_path):
    (tmp_path / "xhs").mkdir()
    (tmp_path / "xhs" / "render.cjs").write_text("// test", encoding="utf-8")

    scripts = discover_guizang_render_scripts(tmp_path)

    assert scripts == [tmp_path / "xhs" / "render.cjs"]
```

**Step 2: 实现 exporter**

函数：

- `discover_guizang_render_scripts(package_dir) -> list[Path]`
- `export_guizang_images(package_dir) -> list[Path]`

`export_guizang_images()` 使用 `subprocess.run(["node", "render.cjs"], cwd=script.parent, check=True)`。

若 `node` 或 `playwright` 缺失，错误信息应包含：

```text
Guizang image export requires Node.js and Playwright.
```

**Step 3: 接入主流程**

`generate_distribution.run()` 中：

- `renderer == "basic"`：继续使用 `export_html_to_images(package_dir)`。
- `renderer == "guizang"`：使用 `export_guizang_images(package_dir)`。

**Step 4: Run tests**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_exporter.py tests/distribution_pipeline/test_guizang_renderer.py -v
```

Expected: PASS.

### Task 4.3: 真实文章 PNG 导出验收

**Files:**
- No code change unless发现 bug

**Step 1: 运行真实文章导出**

Run:

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform xhs \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --output-root /private/tmp/chora-guizang-render
```

Expected: `xhs/output/*.png` 存在。

**Step 2: 检查图片尺寸**

Run:

```bash
sips -g pixelWidth -g pixelHeight /private/tmp/chora-guizang-render/*/xhs/output/*.png
```

Expected: 每张图片均为 `1080 x 1440`。

**Step 3: 更新状态**

将“阶段 4”勾选为完成，并记录导出数量与尺寸结果。

**进展记录：**

```bash
pytest tests/distribution_pipeline/test_guizang_render_script.py tests/distribution_pipeline/test_guizang_exporter.py tests/distribution_pipeline/test_guizang_validator.py -q
```

Result: `10 passed in 0.79s`

真实文章导出命令已在 Codex 非沙箱审批路径运行成功：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform xhs \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --output-root /private/tmp/chora-guizang-codex-approved-after-r6
```

Result:

- `xhs/output/` 生成 8 张 PNG。
- `sips -g pixelWidth -g pixelHeight .../xhs/output/*.png` 显示每张图片均为 `1080 x 1440`。
- Codex 默认沙箱仍会在浏览器截图阶段失败；Codex 非沙箱审批路径可正常完成，不需要外部 Terminal。

---

## 阶段 5：自动视觉校验接入 manifest

### Task 5.1: 封装 Guizang validator

**Files:**
- Create: `distribution_pipeline/renderers/guizang/validator.py`
- Modify: `distribution_pipeline/renderers/manifest.py`
- Test: `tests/distribution_pipeline/test_guizang_validator.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.guizang.validator import parse_validator_output


def test_parse_validator_output_counts_pass_fail_warn():
    output = '''
PASS xhs-01
WARN R4 body small
FAIL R1 overflow
'''

    status = parse_validator_output(output)

    assert status["pass_count"] == 1
    assert status["warn_count"] == 1
    assert status["fail_count"] == 1
```

**Step 2: 实现 validator wrapper**

函数：

- `run_guizang_validator(target_dir: Path, mode: str) -> dict`
- `parse_validator_output(output: str) -> dict`

调用：

```bash
node distribution_pipeline/vendor/guizang/validate-social-deck.mjs <target-dir> --style=<mode>
```

注意：

- validator 返回码 1 表示存在 FAIL，不应吞掉。
- manifest 中仍然记录 stdout/stderr 摘要。
- 若环境缺 Node/Playwright，返回 `status: "skipped"`，并给出清晰原因。

**Step 3: manifest 增加 guizang_review**

`review_status` 示例：

```json
{
  "repetition": {"status": "pass"},
  "guizang": {
    "xhs": {
      "status": "pass",
      "pass_count": 8,
      "warn_count": 0,
      "fail_count": 0
    }
  }
}
```

**Step 4: Run tests**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_validator.py tests/distribution_pipeline/test_manifest.py -v
```

Expected: PASS.

### Task 5.2: validator 手动验收

**Step 1: 运行 validator**

Run:

```bash
node distribution_pipeline/vendor/guizang/validate-social-deck.mjs \
  /private/tmp/chora-guizang-render/*/xhs \
  --style=editorial
```

Expected: 无 FAIL。若有 FAIL，按规则修复 recipe 或 copy compression。

**Step 2: 更新状态**

将“阶段 5”勾选为完成，并记录 validator 结果。

**进展记录：**

`manifest.json` 已记录 `review_status.guizang.xhs`。真实文章 validator 已在 Codex 非沙箱审批路径通过：

```json
{
  "status": "pass",
  "warn_count": 0,
  "fail_count": 0,
  "returncode": 0
}
```

输出摘要：

```text
sections: 8 · 8 clean · 0 fails · 0 warns
[PASS] xhs-01
...
[PASS] xhs-08
```

此前封面 R6 warning 的根因是封面标题误用模板默认 `124px` 大标题，并且第二行 `Gemini翻身之战` 对 3:4 封面过长。已修复为 `font-size:92px`，并将封面短标题压缩为 `谷歌AI的14年 / Gemini翻身战`。

---

## 阶段 5A：图像证据层一期

### 已完成范围

本阶段先接入“可追踪的图像资产计划”，不直接做不可控的网页抓图。目标是让每个分发包都具备稳定的图片数据接口，后续可以继续接真实下载器和 M10/M16 图文 recipe。

**Files:**

- Create: `distribution_pipeline/assets/__init__.py`
- Create: `distribution_pipeline/assets/image_assets.py`
- Modify: `distribution_pipeline/extractors/package_builder.py`
- Modify: `distribution_pipeline/renderers/guizang/guizang_renderer.py`
- Modify: `distribution_pipeline/renderers/guizang/page_planner.py`
- Modify: `distribution_pipeline/renderers/guizang/recipes.py`
- Test: `tests/distribution_pipeline/test_image_assets.py`

**输出：**

- `image_assets.json`：包级图像资产计划。
- `xhs/assets/image_assets.json`：XHS 渲染侧 materialized 图像资产。
- `xhs/assets/SOURCES.md`：本地素材来源、外部搜索入口、版权状态说明。
- `xhs/assets/images/source-cover.jpg`：本地封面复制件，供 HTML 直接引用。

**已接入渲染：**

- 若归档目录存在 `cover.jpg/png/webp`，Guizang XHS 封面页自动使用 M01 的大图框。
- 封面仍保留短标题、来源、issue strip，不破坏原有 validator 规则。

**外部搜索计划：**

根据公众号说明和 skill 文档，当前输出覆盖：

- Pexels：`https://www.pexels.com/search/<query>/`
- Unsplash：`https://unsplash.com/s/photos/<query>`
- Wallhaven：`https://wallhaven.cc/search?q=<query>`
- Flickr CC：`https://www.flickr.com/search/?text=<query>&license=2,3,4,5,6,9`

搜索词不再直接拼接整段正文，而是通过语义规则压缩为短 query，例如：

- `computer vision lab`
- `AI research lab`
- `data center machine learning`
- `research team strategy meeting`

### 验证记录

Run:

```bash
pytest tests/distribution_pipeline/test_image_assets.py tests/distribution_pipeline/test_package_builder.py tests/distribution_pipeline/test_guizang_renderer.py -q
```

Result: `5 passed`

真实文章 no-export 验收：

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform xhs \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --no-export-images \
  --output-root /private/tmp/chora-guizang-image-assets
```

Result:

- `image_assets.json` 已生成。
- `xhs/assets/SOURCES.md` 已生成。
- `xhs/assets/images/source-cover.jpg` 已生成。
- `xhs/index.html` 已引用 `assets/images/source-cover.jpg`。

---

## 阶段 5B：外部图片候选与下载器一期

### 已完成范围

本阶段把 5A 的“搜索计划”扩展为可执行的图片候选与下载链路，但仍保持默认离线稳定。主流程默认使用 `--image-assets plan`，只复制本地封面并写搜索计划；只有显式选择 `candidates` 或 `download` 时才尝试联网或处理候选。

**Files:**

- Create: `distribution_pipeline/assets/providers.py`
- Create: `distribution_pipeline/assets/downloader.py`
- Modify: `distribution_pipeline/assets/image_assets.py`
- Modify: `distribution_pipeline/generate_distribution.py`
- Modify: `distribution_pipeline/renderers/guizang/guizang_renderer.py`
- Modify: `distribution_pipeline/renderers/guizang/page_planner.py`
- Modify: `distribution_pipeline/renderers/guizang/recipes.py`
- Test: `tests/distribution_pipeline/test_image_assets.py`
- Test: `tests/distribution_pipeline/test_generate_distribution_cli.py`
- Test: `tests/distribution_pipeline/test_guizang_page_planner.py`
- Test: `tests/distribution_pipeline/test_guizang_recipes.py`

### 设计结果

新增 CLI 参数：

```bash
--image-assets plan|candidates|download
```

模式语义：

- `plan`：默认模式。只复制本地封面，写 `image_assets.json`、`SOURCES.md` 和搜索入口，不访问网络。
- `candidates`：尝试把 planned request 扩展成标准候选图。手动候选和 direct URL 不需要 API；Pexels、Unsplash 需要对应 API key；Wallhaven 使用公开搜索接口。
- `download`：在候选图基础上下载首选候选，写入 `xhs/assets/images/`，并把结果记录到 `selected_assets`。

图像下载器会做基础文件检查：

- 识别 PNG、JPEG、WebP 后缀。
- 解析 PNG/JPEG/WebP 基础尺寸。
- 默认拒绝小于 `640x480` 的图片。
- 记录 `provider`、`source_url`、`author`、`license_status`、`render_path`、`target_pages`。

Guizang 页面计划已消费 `selected_assets`。当洞见页存在可用证据图时，该页自动使用 `M10 Evidence Feature`，让图片成为大幅证据区，而不是装饰性小图。

### 当前边界

本阶段不自动判断版权是否可商用，也不自动判断人脸、商标、主体遮挡等高级视觉风险。`SOURCES.md` 会保留来源、作者和版权状态字段，外部图片默认仍需要人工确认。

Pexels 与 Unsplash 的官方 API 需要环境变量：

```bash
PEXELS_API_KEY=<your_key>
UNSPLASH_ACCESS_KEY=<your_key>
```

没有 API key 时，`plan` 模式仍可稳定生成搜索入口；`download` 模式可通过手动候选或 direct URL 工作。

### 验证记录

先安装临时测试依赖到 `/private/tmp/chora-pytest-deps`：

```bash
/Users/Avis/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -m pip install pytest -t /private/tmp/chora-pytest-deps
```

Run:

```bash
PYTHONPATH=/private/tmp/chora-pytest-deps \
  /Users/Avis/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -m pytest \
  tests/distribution_pipeline/test_generate_distribution_cli.py \
  tests/distribution_pipeline/test_image_assets.py \
  tests/distribution_pipeline/test_guizang_page_planner.py \
  tests/distribution_pipeline/test_guizang_recipes.py \
  -q
```

Result: `20 passed in 31.85s`

### 下一步

阶段 5C 建议做图片质量与版权辅助：

1. 为已下载图片增加明度/安全区/主体裁切检查。
2. 在 `SOURCES.md` 中加入“建议署名文案”。
3. 支持用户维护一个人工批准的 `approved_image_assets.json`，避免每次重新选择。
4. 为 M10/M16 增加多图拼贴与截图框处理。

---

## 阶段 6：微信公众号封面对

### Task 6.1: 更新平台规格

**Files:**
- Modify: `distribution_pipeline/renderers/platform_specs.py`
- Test: `tests/distribution_pipeline/test_platform_specs.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.platform_specs import get_platform_spec


def test_wechat_guizang_cover_specs():
    wide = get_platform_spec("wechat_wide")
    square = get_platform_spec("wechat_square")

    assert (wide["width"], wide["height"]) == (2100, 900)
    assert (square["width"], square["height"]) == (1080, 1080)
```

**Step 2: 实现 specs**

新增：

```python
"wechat_wide": {"width": 2100, "height": 900, "max_cards": 1},
"wechat_square": {"width": 1080, "height": 1080, "max_cards": 1},
"wechat_pair_preview": {"width": 2400, "height": 1180, "max_cards": 1},
```

保留旧的 `wechat_hero` 和 `wechat_inline`，避免基础后端破坏。

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_platform_specs.py -v
```

Expected: PASS.

### Task 6.2: 实现微信短标题生成器

**Files:**
- Create: `distribution_pipeline/renderers/guizang/title_shortener.py`
- Test: `tests/distribution_pipeline/test_guizang_title_shortener.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.guizang.title_shortener import shorten_wechat_title


def test_shorten_wechat_title_removes_interview_prefix():
    title = "谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew"

    short = shorten_wechat_title(title)

    assert len(short) <= 14
    assert "专访" not in short
```

**Step 2: 实现启发式**

规则：

- 去掉 `：专访...`、`｜...`、` - ...` 等副标题尾巴。
- 优先保留核心对象：如 `Gemini`、`谷歌AI`、`视觉理解`。
- 长度目标 4-10 个中文字符或 2 个短 token。
- 无法可靠缩短时，取前 12-14 个可读字符，不挤满 1:1。

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_title_shortener.py -v
```

Expected: PASS.

### Task 6.3: 生成微信 `index.html`

**Files:**
- Modify: `distribution_pipeline/renderers/guizang/page_planner.py`
- Modify: `distribution_pipeline/renderers/guizang/recipes.py`
- Modify: `distribution_pipeline/renderers/guizang/guizang_renderer.py`
- Test: `tests/distribution_pipeline/test_guizang_wechat_renderer.py`

**Step 1: 写 failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_wechat_package


def test_render_guizang_wechat_package_writes_cover_pair(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    written = render_guizang_wechat_package(
        package,
        tmp_path / "pkg",
        mode="editorial",
        theme="indigo-porcelain",
    )

    html_path = tmp_path / "pkg" / "wechat" / "index.html"
    assert html_path in written
    html = html_path.read_text(encoding="utf-8")
    assert 'id="wechat-21x9"' in html
    assert 'id="wechat-1x1"' in html
    assert 'id="wechat-pair-preview"' in html
    assert (tmp_path / "pkg" / "wechat" / "appendix.md").exists()
```

**Step 2: 实现微信页面计划**

`build_wechat_pages(package, mode)` 返回：

- `wechat-21x9`：wide cover，完整或近完整标题。
- `wechat-1x1`：square cover，短标题。
- `wechat-pair-preview`：同 HTML 中的组合预览节点。

**Step 3: 实现微信 recipe**

Editorial：

- wide：借鉴 M01/M09，但 class 用 `poster wide`。
- square：大标题居中，默认无图片。
- preview：把 wide 与 square 缩放并列，用于视觉检查，不作为平台最终图。

Swiss：

- wide：严格网格、左标题、右证据区或结构图。
- square：大字号短标题 + 单一 accent。

**Step 4: 接入 CLI**

`renderer == "guizang"` 且 platform 包含 wechat 时，调用 `render_guizang_wechat_package()`。

**Step 5: Run tests**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_wechat_renderer.py tests/distribution_pipeline/test_generate_distribution_cli.py -v
```

Expected: PASS.

**Step 6: 更新状态**

将“阶段 6”勾选为完成，并记录测试结果。

---

## 阶段 7：真实文章端到端验收

### Task 7.1: 运行 2026-05-19 真实文章全平台 Guizang 输出

**Files:**
- No planned code change

**Step 1: 生成全平台素材**

Run:

```bash
python3 -m distribution_pipeline.generate_distribution \
  "content_archive/2026-05-19/youtube_硅谷101_谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew" \
  --platform all \
  --renderer guizang \
  --guizang-mode editorial \
  --guizang-theme indigo-porcelain \
  --cards 8 \
  --output-root /private/tmp/chora-guizang-e2e
```

Expected:

- `xhs/index.html`
- `xhs/output/xhs-01-cover.png`
- `wechat/index.html`
- `wechat/output/wechat-21x9-cover.png`
- `wechat/output/wechat-1x1-cover.png`
- `wechat/output/wechat-cover-pair-preview.png`
- `manifest.json`

**Step 2: 检查图片尺寸**

Run:

```bash
sips -g pixelWidth -g pixelHeight /private/tmp/chora-guizang-e2e/*/xhs/output/*.png
sips -g pixelWidth -g pixelHeight /private/tmp/chora-guizang-e2e/*/wechat/output/*.png
```

Expected:

- xhs: `1080 x 1440`
- wechat 21x9: `2100 x 900`
- wechat 1x1: `1080 x 1080`

**Step 3: 视觉抽检**

使用本地图片查看工具检查：

- 封面标题是否一眼可读。
- 小红书连续页面版式不重复。
- 公众号 1:1 没有塞入完整长标题。
- 没有文字溢出、底部 footer 撞车或大面积空洞。

**Step 4: Run full tests**

Run:

```bash
pytest tests/distribution_pipeline -v
```

Expected: PASS.

**Step 5: 更新状态**

将“阶段 7”勾选为完成，并记录真实文章输出路径与测试结果。

---

## 阶段 8：审美陌生化策略增强

### Task 8.1: 增加确定性风格变奏种子

**Files:**
- Create: `distribution_pipeline/renderers/guizang/variation.py`
- Test: `tests/distribution_pipeline/test_guizang_variation.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.renderers.guizang.variation import build_variation_seed


def test_variation_seed_is_stable_for_same_article():
    source = {"title": "Token经济学", "channel": "硅谷101", "publish_date": "2026-05-13"}

    assert build_variation_seed(source) == build_variation_seed(source)
```

**Step 2: 实现稳定 seed**

用 `title + channel + publish_date` 生成 hash，派生：

- recipe 起始偏移
- issue label
- section rhythm
- cover emphasis
- accent usage pattern

禁止把 seed 用于随机字体、随机低对比配色或随机压缩字号。

**Step 3: Run test**

Run:

```bash
pytest tests/distribution_pipeline/test_guizang_variation.py -v
```

Expected: PASS.

### Task 8.2: 增加 recipe diversity reviewer

**Files:**
- Create: `distribution_pipeline/reviewers/recipe_diversity.py`
- Test: `tests/distribution_pipeline/test_recipe_diversity.py`

**Step 1: 写 failing test**

```python
from distribution_pipeline.reviewers.recipe_diversity import review_recipe_diversity


def test_review_recipe_diversity_flags_repeated_recipes():
    pages = [
        {"id": "xhs-01", "recipe": "M03"},
        {"id": "xhs-02", "recipe": "M03"},
    ]

    result = review_recipe_diversity(pages)

    assert result["status"] == "warn"
```

**Step 2: 实现 reviewer**

规则：

- 连续 recipe 相同：warn。
- 8 张卡中同一 recipe 超过 3 次：warn。
- 全部 insight 都是 essay 型 recipe：warn。

**Step 3: 接入 manifest**

在 Guizang 渲染后把页面计划的 diversity review 写入 `manifest.json`。

**Step 4: Run tests**

Run:

```bash
pytest tests/distribution_pipeline/test_recipe_diversity.py tests/distribution_pipeline/test_manifest.py -v
```

Expected: PASS.

**Step 5: 更新状态**

将“阶段 8”勾选为完成，并记录测试结果。

---

## 完成定义

Guizang 接入完成时，需要满足：

- `pytest tests/distribution_pipeline -v` 全部通过。
- `--renderer basic` 与现有输出结构完全兼容。
- `--renderer guizang --platform xhs` 可以输出 `xhs/index.html` 和 PNG 卡组。
- `--renderer guizang --platform wechat` 可以输出 21:9、1:1 和 pair preview。
- `manifest.json` 能记录 basic reviewer、Guizang validator 和 recipe diversity 的结果。
- 2026-05-19 真实文章可以成功生成全平台素材。
- 计划文档的阶段状态已更新到全部完成。

---

## 风险与回滚

- **Playwright 或 Node 缺失**：默认测试不依赖真实导出；PNG 导出失败时错误信息必须明确指向 Node/Playwright。
- **Guizang 模板上游变化**：项目内 vendor 资产固定版本，避免本机 skill 更新导致 Chora 输出漂移。
- **模板体积较大**：只 vendor 必要资产，不复制完整 skill 参考文档和 package-lock。
- **视觉过度同质化**：通过 recipe diversity、variation seed 和视觉导演稿路由降低重复。
- **视觉过度随机**：主题白名单、固定 seed、validator 和平台规格约束保证稳定。
- **基础后端被破坏**：`--renderer basic` 是默认值，所有现有测试必须继续通过。

---

## 下一轮开工建议

优先完成阶段 4 和阶段 5 的运行时验收：

1. 在普通终端运行 2026-05-19 真实文章导出命令，去掉 `--no-export-images`。
2. 检查 `xhs/output/*.png` 是否生成，并用 `sips` 确认每张为 `1080 x 1440`。
3. 运行 `node distribution_pipeline/vendor/guizang/validate-social-deck.mjs <xhs-dir> --style=editorial`。
4. 若 validator 无 FAIL，勾选阶段 4 和阶段 5。
5. 继续阶段 6：微信公众号 `21:9 + 1:1` 封面对。
