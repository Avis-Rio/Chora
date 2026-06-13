# Chora 分发素材生成层 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为现有 `content_archive/` 中的 AI 改写文章新增一条可复用的分发素材生成流水线，自动产出小红书卡片图文与微信公众号贴图素材。

**Architecture:** 新流水线作为独立模块消费现有归档文件，不侵入转录、改写、飞书同步和前端展示主链路。系统采用“结构化洞见抽取 -> 视觉母题规划 -> 视觉导演稿 -> 风格语法选择 -> HTML/CSS 渲染 -> 图片导出 -> 自动审稿”的分层架构，以固定安全骨架保证稳定，以动态视觉导演稿和风格语法保证审美变化与陌生化创作。

**Tech Stack:** Python 3、Markdown/JSON 解析、PyYAML、pytest、Playwright 或浏览器截图工具、HTML/CSS 模板、现有 `styles/` 视觉风格资源、现有 `content_archive/` 归档结构。

---

## 总体阶段

1. **阶段 0：基础设施与测试骨架**  
   建立 `distribution_pipeline/` 模块、测试目录、样例归档和命令入口。

2. **阶段 1：内容结构化**  
   从 `metadata.md` 和 `rewritten.md` 稳定抽取标题、来源、标签、金句、核心洞见，并生成 `source.json` 与 `insights.json`。

3. **阶段 2：审美生成中间层**  
   生成每篇文章的 `visual_system.json` 和每条洞见的 `visual_briefs.json`，建立视觉母题、隐喻、构图、禁忌和平台节奏。

4. **阶段 3：风格语法与版式骨架**  
   新增 YAML 风格语法与安全版式骨架，完成数据到 HTML 的模板渲染。

5. **阶段 4：平台产物生成**  
   生成小红书卡片组、公众号首图与文中贴图、平台文案和 manifest。

6. **阶段 5：自动审稿与批量化**  
   检查文字溢出、重复构图、尺寸、品牌、文件完整性，并支持批量生成。

---

## 阶段 0：基础设施与测试骨架

### Task 0.1: 创建分发流水线模块骨架 ✅

**Files:**
- Create: `distribution_pipeline/__init__.py`
- Create: `distribution_pipeline/generate_distribution.py`
- Create: `distribution_pipeline/extractors/__init__.py`
- Create: `distribution_pipeline/directors/__init__.py`
- Create: `distribution_pipeline/renderers/__init__.py`
- Create: `distribution_pipeline/reviewers/__init__.py`
- Create: `tests/distribution_pipeline/__init__.py`

**Step 1: 创建空模块文件**

新增上述文件，先保持最小内容。`generate_distribution.py` 只提供占位 `main()`：

```python
def main():
    raise SystemExit("distribution pipeline is not implemented yet")


if __name__ == "__main__":
    main()
```

**Step 2: 运行命令验证入口可执行**

Run:

```bash
python3 -m distribution_pipeline.generate_distribution
```

Expected:

```text
distribution pipeline is not implemented yet
```

**Step 3: Commit**

```bash
git add distribution_pipeline tests/distribution_pipeline
git commit -m "chore: scaffold distribution pipeline"
```

### Task 0.2: 添加测试夹具 ✅

**Files:**
- Create: `tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/metadata.md`
- Create: `tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/rewritten.md`
- Create: `tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/transcript.md`
- Create: `tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/cover.jpg`

**Step 1: 写入最小 metadata**

```markdown
# Token经济学：AI时代的新货币战争

## 来源
硅谷101

## 原始链接
https://www.youtube.com/watch?v=example12345

## 发布时间
2026-05-13

## 嘉宾
肖志斌，芯片与 Token 效率研究者

## 金句
> Token 正在变成 AI 创业公司最核心的弹药。
> 谁掌握计量单位，谁就掌握经济秩序。
```

**Step 2: 写入最小 rewritten**

```markdown
## 1. 创作说明
- **选题方向**: AI 经济与算力成本
- **评分**: 哲学人文社科关联度 [35] + 故事性 [30] + 现实意义 [20] + 加分项 [8] = 总分 [93/120]

## 3. 核心洞察 (Core Insights)

1. **成本结构的范式转移**：传统 SaaS 的边际成本趋近于零，AI 产品却把每次推理重新变成真实成本。
2. **越贵越便宜的悖论**：强模型单价更高，但复杂任务总成本可能更低。
3. **计量即权力**：谁定义 Token 的计量方式，谁就定义 AI 经济的边界。

## 6. 内容标签 (Tags)
Tags: Technology, Economics, Power & Politics
```

**Step 3: 放置占位文件**

`transcript.md` 写入一句测试文本。`cover.jpg` 可先放置空文件，渲染器测试不依赖其真实内容。

**Step 4: Commit**

```bash
git add tests/fixtures
git commit -m "test: add distribution pipeline fixtures"
```

---

## 阶段 1：内容结构化

### Task 1.1: 实现 metadata 解析器 ✅

**Files:**
- Create: `distribution_pipeline/extractors/metadata_parser.py`
- Test: `tests/distribution_pipeline/test_metadata_parser.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.metadata_parser import parse_metadata


def test_parse_metadata_extracts_core_fields():
    path = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/metadata.md")

    data = parse_metadata(path)

    assert data["title"] == "Token经济学：AI时代的新货币战争"
    assert data["channel"] == "硅谷101"
    assert data["source_url"] == "https://www.youtube.com/watch?v=example12345"
    assert data["publish_date"] == "2026-05-13"
    assert "肖志斌" in data["guests"]
    assert len(data["quotes"]) == 2
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_metadata_parser.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

**Step 3: Write minimal implementation**

实现 `parse_metadata(path: Path) -> dict`，规则复用 `export_to_json.py` 的章节正则，但只返回分发流水线需要的字段：

```python
{
    "title": str,
    "channel": str,
    "source_url": str,
    "publish_date": str,
    "guests": str,
    "quotes": list[str],
}
```

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_metadata_parser.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/extractors/metadata_parser.py tests/distribution_pipeline/test_metadata_parser.py
git commit -m "feat: parse distribution metadata"
```

### Task 1.2: 实现 rewritten 核心洞见解析器 ✅

**Files:**
- Create: `distribution_pipeline/extractors/insight_parser.py`
- Test: `tests/distribution_pipeline/test_insight_parser.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.insight_parser import parse_insights


def test_parse_insights_from_core_insights_section():
    path = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/rewritten.md")

    insights = parse_insights(path)

    assert len(insights) == 3
    assert insights[0]["index"] == 1
    assert insights[0]["title"] == "成本结构的范式转移"
    assert "边际成本" in insights[0]["body"]
    assert insights[2]["title"] == "计量即权力"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_insight_parser.py -v
```

Expected: FAIL.

**Step 3: Write minimal implementation**

实现优先级：

1. 匹配 `## 3. 核心洞察` 到下一个 `##`。
2. 支持 `1. **标题**：正文`。
3. 支持 `- **标题**：正文`。
4. 支持没有粗体时按第一处中文冒号拆分。

输出结构：

```python
{
    "index": 1,
    "title": "成本结构的范式转移",
    "body": "传统 SaaS 的边际成本趋近于零...",
    "one_liner": "传统 SaaS 的边际成本趋近于零...",
    "keywords": []
}
```

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_insight_parser.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/extractors/insight_parser.py tests/distribution_pipeline/test_insight_parser.py
git commit -m "feat: parse core insights for distribution"
```

### Task 1.3: 生成 source.json 与 insights.json ✅

**Files:**
- Create: `distribution_pipeline/extractors/package_builder.py`
- Test: `tests/distribution_pipeline/test_package_builder.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package


def test_build_content_package_combines_metadata_and_insights(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    output_dir = tmp_path / "distribution" / "token-economics"

    package = build_content_package(content_dir, output_dir)

    assert (output_dir / "source.json").exists()
    assert (output_dir / "insights.json").exists()
    assert package["source"]["title"] == "Token经济学：AI时代的新货币战争"
    assert len(package["insights"]) == 3
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_package_builder.py -v
```

Expected: FAIL.

**Step 3: Write minimal implementation**

实现：

- 检查 `metadata.md` 与 `rewritten.md` 必须存在。
- 解析 metadata 与 insights。
- 推断 `platform`：目录名包含 `youtube_` 则为 `youtube`，包含 `xiaoyuzhou_` 则为 `xiaoyuzhou`。
- 写入 UTF-8 JSON，`ensure_ascii=False`，`indent=2`。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_package_builder.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/extractors/package_builder.py tests/distribution_pipeline/test_package_builder.py
git commit -m "feat: build distribution content package"
```

---

## 阶段 2：审美生成中间层

### Task 2.1: 定义视觉系统数据结构 ✅

**Files:**
- Create: `distribution_pipeline/directors/visual_system.py`
- Test: `tests/distribution_pipeline/test_visual_system.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.directors.visual_system import build_visual_system


def test_build_visual_system_returns_motifs_and_constraints():
    source = {
        "title": "Token经济学：AI时代的新货币战争",
        "tags": ["Technology", "Economics", "Power & Politics"],
        "channel": "硅谷101",
    }
    insights = [
        {"title": "计量即权力", "body": "谁定义 Token 的计量方式，谁就定义 AI 经济的边界。"}
    ]

    system = build_visual_system(source, insights)

    assert system["theme"]
    assert len(system["visual_motifs"]) >= 4
    assert "avoid" in system
    assert "composition_rules" in system
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_visual_system.py -v
```

Expected: FAIL.

**Step 3: Write minimal implementation**

先实现规则版，不接 LLM：

- `Technology` + `Economics`：加入 `账本`、`仪表盘`、`电流`、`交易所`。
- `Power & Politics`：加入 `天平`、`印章`、`档案`。
- 默认避开 `普通科技蓝渐变`、`硬币图标`、`抽象球体`。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_visual_system.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/directors/visual_system.py tests/distribution_pipeline/test_visual_system.py
git commit -m "feat: create visual system for distribution assets"
```

### Task 2.2: 生成每条洞见的视觉导演稿 ✅

**Files:**
- Create: `distribution_pipeline/directors/visual_brief.py`
- Test: `tests/distribution_pipeline/test_visual_brief.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.directors.visual_brief import build_visual_briefs


def test_build_visual_briefs_assigns_unique_metaphors():
    visual_system = {
        "visual_motifs": ["账本", "仪表盘", "天平", "电流"],
        "avoid": ["硬币图标"],
    }
    insights = [
        {"index": 1, "title": "成本结构的范式转移", "body": "AI 产品让推理成为真实成本。"},
        {"index": 2, "title": "计量即权力", "body": "谁定义 Token 的计量方式，谁就定义边界。"},
    ]

    briefs = build_visual_briefs(insights, visual_system)

    assert len(briefs) == 2
    assert briefs[0]["visual_metaphor"] != briefs[1]["visual_metaphor"]
    assert briefs[0]["composition"]["text_position"]
    assert "硬币图标" in briefs[0]["forbidden_cliches"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_visual_brief.py -v
```

Expected: FAIL.

**Step 3: Write minimal implementation**

先实现确定性规则：

- 每条洞见轮换使用不同 `visual_motifs`。
- 根据洞见标题关键词选择隐喻：
  - 包含 `成本`：`账本`、`电流`。
  - 包含 `计量` 或 `权力`：`仪表盘`、`天平`。
- 生成 `composition`、`mood`、`texture`、`forbidden_cliches`。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_visual_brief.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/directors/visual_brief.py tests/distribution_pipeline/test_visual_brief.py
git commit -m "feat: generate visual briefs for insights"
```

### Task 2.3: 写入 visual_system.json 与 visual_briefs.json ✅

**Files:**
- Modify: `distribution_pipeline/extractors/package_builder.py`
- Test: `tests/distribution_pipeline/test_package_builder.py`

**Step 1: Extend failing test**

在 `test_build_content_package_combines_metadata_and_insights` 增加断言：

```python
assert (output_dir / "visual_system.json").exists()
assert (output_dir / "visual_briefs.json").exists()
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_package_builder.py -v
```

Expected: FAIL because visual files are missing.

**Step 3: Implement file writing**

在 `build_content_package()` 中调用：

- `build_visual_system(source, insights)`
- `build_visual_briefs(insights, visual_system)`

写入 `visual_system.json` 与 `visual_briefs.json`。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_package_builder.py tests/distribution_pipeline/test_visual_system.py tests/distribution_pipeline/test_visual_brief.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/extractors/package_builder.py tests/distribution_pipeline/test_package_builder.py
git commit -m "feat: write visual planning files"
```

---

## 阶段 3：风格语法与版式骨架

### Task 3.1: 新增风格语法 YAML ✅

**Files:**
- Create: `distribution_pipeline/styles/chora-editorial.yaml`
- Create: `distribution_pipeline/styles/techno-critical.yaml`
- Create: `distribution_pipeline/styles/literary-poster.yaml`
- Create: `distribution_pipeline/directors/style_loader.py`
- Test: `tests/distribution_pipeline/test_style_loader.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.directors.style_loader import load_style


def test_load_style_returns_required_sections():
    style = load_style("chora-editorial")

    assert style["id"] == "chora-editorial"
    assert "typography" in style
    assert "color" in style
    assert "layout" in style
    assert "avoid" in style
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_style_loader.py -v
```

Expected: FAIL.

**Step 3: Create style YAML files**

`chora-editorial.yaml` 至少包含：

```yaml
id: chora-editorial
name: Chora Editorial
best_for:
  - Philosophy
  - Technology
  - Sociology
  - Economics
typography:
  title_font: Huiwen Mincho
  body_font: Noto Sans SC
  title_layout:
    - vertical
    - asymmetrical
color:
  base:
    - "#F4EFE6"
    - "#191713"
  accents:
    - "#D75A2A"
    - "#2D6A73"
layout:
  grid: 12-column
  margin: generous
  asymmetry: high
texture:
  paper_grain: true
  ink_bleed: subtle
avoid:
  - large rounded cards
  - generic icons
  - decorative blobs
```

**Step 4: Implement loader**

使用 `yaml.safe_load()`，当样式不存在时抛出 `ValueError("Unknown style: {style_id}")`。

**Step 5: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_style_loader.py -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add distribution_pipeline/styles distribution_pipeline/directors/style_loader.py tests/distribution_pipeline/test_style_loader.py
git commit -m "feat: add distribution style grammar"
```

### Task 3.2: 实现平台卡片规格 ✅

**Files:**
- Create: `distribution_pipeline/renderers/platform_specs.py`
- Test: `tests/distribution_pipeline/test_platform_specs.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.renderers.platform_specs import get_platform_spec


def test_xhs_spec_uses_vertical_card_size():
    spec = get_platform_spec("xhs")

    assert spec["width"] == 1080
    assert spec["height"] == 1440
    assert spec["max_cards"] == 8


def test_wechat_spec_uses_horizontal_hero_size():
    spec = get_platform_spec("wechat_hero")

    assert spec["width"] == 1200
    assert spec["height"] == 675
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_platform_specs.py -v
```

Expected: FAIL.

**Step 3: Implement specs**

支持：

- `xhs`: `1080x1440`
- `xhs_square`: `1080x1080`
- `wechat_hero`: `1200x675`
- `wechat_inline`: `900x500`

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_platform_specs.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/renderers/platform_specs.py tests/distribution_pipeline/test_platform_specs.py
git commit -m "feat: define distribution platform specs"
```

### Task 3.3: 实现 HTML 卡片渲染器 ✅

**Files:**
- Create: `distribution_pipeline/renderers/html_renderer.py`
- Create: `distribution_pipeline/renderers/templates.py`
- Test: `tests/distribution_pipeline/test_html_renderer.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.renderers.html_renderer import render_card_html


def test_render_card_html_includes_text_and_dimensions():
    card = {
        "type": "single-insight",
        "title": "计量即权力",
        "body": "谁定义 Token 的计量方式，谁就定义 AI 经济的边界。",
        "index": 3,
    }
    visual_brief = {
        "visual_metaphor": "仪表盘连接着发光账本",
        "composition": {"text_position": "left-top"},
        "mood": "冷静、制度化",
    }
    style = {
        "id": "chora-editorial",
        "color": {"base": ["#F4EFE6", "#191713"], "accents": ["#D75A2A"]},
        "typography": {"title_font": "serif", "body_font": "sans-serif"},
    }
    spec = {"width": 1080, "height": 1440}

    html = render_card_html(card, visual_brief, style, spec)

    assert "计量即权力" in html
    assert "1080px" in html
    assert "1440px" in html
    assert "仪表盘连接着发光账本" in html
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_html_renderer.py -v
```

Expected: FAIL.

**Step 3: Implement minimal renderer**

先用 Python 字符串模板实现，不引入复杂模板引擎。要求：

- 输出完整 HTML。
- 设置 `.card { width: ...; height: ...; }`。
- 转义文本，避免 HTML 注入。
- 保留 `data-card-type`、`data-style-id` 方便后续审稿。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_html_renderer.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/renderers/html_renderer.py distribution_pipeline/renderers/templates.py tests/distribution_pipeline/test_html_renderer.py
git commit -m "feat: render distribution cards as html"
```

---

## 阶段 4：平台产物生成

### Task 4.1: 生成小红书卡片计划 ✅

**Files:**
- Create: `distribution_pipeline/renderers/xhs_plan.py`
- Test: `tests/distribution_pipeline/test_xhs_plan.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.renderers.xhs_plan import build_xhs_card_plan


def test_build_xhs_card_plan_creates_cover_insights_and_cta():
    source = {"title": "Token经济学：AI时代的新货币战争", "channel": "硅谷101"}
    insights = [
        {"index": 1, "title": "成本结构的范式转移", "body": "AI 产品让推理成为真实成本。"},
        {"index": 2, "title": "计量即权力", "body": "谁定义 Token 的计量方式，谁就定义边界。"},
    ]

    plan = build_xhs_card_plan(source, insights, max_cards=5)

    assert plan[0]["type"] == "cover-poster"
    assert plan[-1]["type"] == "closing-card"
    assert any(card["type"] == "single-insight" for card in plan)
    assert len(plan) <= 5
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_xhs_plan.py -v
```

Expected: FAIL.

**Step 3: Implement planner**

生成顺序：

1. `cover-poster`
2. 前 N 条 `single-insight`
3. 当洞见数量 >= 3 时插入 1 张 `concept-map`
4. `closing-card`

保证总数不超过 `max_cards`。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_xhs_plan.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/renderers/xhs_plan.py tests/distribution_pipeline/test_xhs_plan.py
git commit -m "feat: plan xhs distribution cards"
```

### Task 4.2: 生成小红书 HTML 文件与 post.md ✅

**Files:**
- Create: `distribution_pipeline/renderers/xhs_renderer.py`
- Test: `tests/distribution_pipeline/test_xhs_renderer.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.xhs_renderer import render_xhs_package


def test_render_xhs_package_writes_html_and_post(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package_dir = tmp_path / "distribution" / "token-economics"
    package = build_content_package(content_dir, package_dir)

    render_xhs_package(package, package_dir, style_id="chora-editorial", max_cards=5)

    assert (package_dir / "xhs" / "cards").exists()
    assert (package_dir / "xhs" / "post.md").exists()
    assert len(list((package_dir / "xhs" / "cards").glob("*.html"))) >= 3
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_xhs_renderer.py -v
```

Expected: FAIL.

**Step 3: Implement renderer**

- 创建 `xhs/cards/`。
- 根据 `build_xhs_card_plan()` 生成 HTML。
- 文件命名：`01-cover.html`、`02-insight.html`。
- 生成 `xhs/post.md`，包含标题、摘要、洞见列表、标签和导流语。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_xhs_renderer.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/renderers/xhs_renderer.py tests/distribution_pipeline/test_xhs_renderer.py
git commit -m "feat: render xhs distribution package"
```

### Task 4.3: 生成公众号 HTML 文件与 appendix.md ✅

**Files:**
- Create: `distribution_pipeline/renderers/wechat_renderer.py`
- Test: `tests/distribution_pipeline/test_wechat_renderer.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.wechat_renderer import render_wechat_package


def test_render_wechat_package_writes_hero_inline_and_appendix(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package_dir = tmp_path / "distribution" / "token-economics"
    package = build_content_package(content_dir, package_dir)

    render_wechat_package(package, package_dir, style_id="chora-editorial")

    assert (package_dir / "wechat" / "hero.html").exists()
    assert len(list((package_dir / "wechat").glob("inline_*.html"))) >= 1
    assert (package_dir / "wechat" / "appendix.md").exists()
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_wechat_renderer.py -v
```

Expected: FAIL.

**Step 3: Implement renderer**

- `hero.html` 使用 `wechat_hero` 规格。
- `inline_01.html` 到 `inline_03.html` 使用 `wechat_inline` 规格。
- `appendix.md` 包含 Chora 链接、Rhizomata 关注语和原始来源。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_wechat_renderer.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/renderers/wechat_renderer.py tests/distribution_pipeline/test_wechat_renderer.py
git commit -m "feat: render wechat distribution package"
```

### Task 4.4: 实现 HTML 到图片导出器 ✅

**Files:**
- Create: `distribution_pipeline/renderers/html_to_image.py`
- Test: `tests/distribution_pipeline/test_html_to_image.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.renderers.html_to_image import discover_html_outputs


def test_discover_html_outputs_finds_cards(tmp_path):
    cards = tmp_path / "xhs" / "cards"
    cards.mkdir(parents=True)
    (cards / "01-cover.html").write_text("<html></html>", encoding="utf-8")

    outputs = discover_html_outputs(tmp_path)

    assert outputs == [cards / "01-cover.html"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_html_to_image.py -v
```

Expected: FAIL.

**Step 3: Implement discovery and export interface**

先实现：

- `discover_html_outputs(package_dir) -> list[Path]`
- `target_image_path(html_path) -> Path`

再实现 `export_html_to_images(package_dir)`，内部调用 Playwright。若环境没有 Playwright，抛出清晰错误：

```text
Playwright is required to export distribution images. Run: python3 -m playwright install chromium
```

**Step 4: Run unit test**

Run:

```bash
pytest tests/distribution_pipeline/test_html_to_image.py -v
```

Expected: PASS.

**Step 5: 手动导出验证**

Run:

```bash
python3 -m distribution_pipeline.renderers.html_to_image distribution/token-economics
```

Expected:

- 每个 `.html` 旁边生成对应 `.png`。
- 失败时给出 Playwright 安装提示。

**Step 6: Commit**

```bash
git add distribution_pipeline/renderers/html_to_image.py tests/distribution_pipeline/test_html_to_image.py
git commit -m "feat: export distribution html cards to images"
```

---

## 阶段 5：自动审稿与批量化

### Task 5.1: 实现 manifest 生成器 ✅

**Files:**
- Create: `distribution_pipeline/renderers/manifest.py`
- Test: `tests/distribution_pipeline/test_manifest.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.renderers.manifest import build_manifest


def test_build_manifest_records_platform_outputs(tmp_path):
    (tmp_path / "xhs" / "cards").mkdir(parents=True)
    (tmp_path / "xhs" / "cards" / "01-cover.html").write_text("", encoding="utf-8")
    (tmp_path / "xhs" / "post.md").write_text("", encoding="utf-8")

    manifest = build_manifest(tmp_path)

    assert manifest["platforms"]["xhs"]["post_md"].endswith("post.md")
    assert manifest["platforms"]["xhs"]["html_count"] == 1
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_manifest.py -v
```

Expected: FAIL.

**Step 3: Implement manifest**

记录：

- 生成时间
- 平台
- HTML 数量
- PNG 数量
- 文案文件
- 源文件路径
- 审稿状态

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_manifest.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/renderers/manifest.py tests/distribution_pipeline/test_manifest.py
git commit -m "feat: build distribution manifest"
```

### Task 5.2: 实现文本密度审稿 ✅

**Files:**
- Create: `distribution_pipeline/reviewers/text_density.py`
- Test: `tests/distribution_pipeline/test_text_density.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.reviewers.text_density import review_text_density


def test_review_text_density_flags_overlong_title():
    card = {
        "title": "这是一个明显过长并且不适合出现在卡片主标题区域里的标题",
        "body": "短正文",
    }

    result = review_text_density(card, max_title_chars=18, max_body_chars=120)

    assert not result["passed"]
    assert "title_too_long" in result["issues"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_text_density.py -v
```

Expected: FAIL.

**Step 3: Implement reviewer**

检查：

- 标题长度
- 正文长度
- 是否空标题
- 是否空正文

返回：

```python
{"passed": bool, "issues": list[str], "warnings": list[str]}
```

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_text_density.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/reviewers/text_density.py tests/distribution_pipeline/test_text_density.py
git commit -m "feat: review distribution text density"
```

### Task 5.3: 实现重复构图审稿 ✅

**Files:**
- Create: `distribution_pipeline/reviewers/repetition.py`
- Test: `tests/distribution_pipeline/test_repetition.py`

**Step 1: Write the failing test**

```python
from distribution_pipeline.reviewers.repetition import review_repetition


def test_review_repetition_flags_duplicate_metaphors():
    briefs = [
        {"visual_metaphor": "账本", "composition": {"text_position": "center"}},
        {"visual_metaphor": "账本", "composition": {"text_position": "center"}},
    ]

    result = review_repetition(briefs)

    assert not result["passed"]
    assert "duplicate_visual_metaphor" in result["issues"]
    assert "duplicate_composition" in result["issues"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_repetition.py -v
```

Expected: FAIL.

**Step 3: Implement reviewer**

检查：

- 连续卡片是否同一 `visual_metaphor`。
- 连续卡片是否同一 `composition.text_position`。
- 同一组卡片是否超过 60% 使用同一构图。

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/distribution_pipeline/test_repetition.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add distribution_pipeline/reviewers/repetition.py tests/distribution_pipeline/test_repetition.py
git commit -m "feat: review visual repetition"
```

### Task 5.4: 串联 CLI 主入口 ✅

**Files:**
- Modify: `distribution_pipeline/generate_distribution.py`
- Test: `tests/distribution_pipeline/test_generate_distribution_cli.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from distribution_pipeline.generate_distribution import run


def test_run_generates_all_platform_outputs(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    output_root = tmp_path / "distribution"

    package_dir = run(
        content_dir=content_dir,
        output_root=output_root,
        platform="all",
        style_id="chora-editorial",
        max_cards=5,
        export_images=False,
    )

    assert (package_dir / "source.json").exists()
    assert (package_dir / "xhs" / "post.md").exists()
    assert (package_dir / "wechat" / "appendix.md").exists()
    assert (package_dir / "manifest.json").exists()
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/distribution_pipeline/test_generate_distribution_cli.py -v
```

Expected: FAIL.

**Step 3: Implement `run()`**

`run()` 参数：

```python
def run(
    content_dir: Path,
    output_root: Path = Path("distribution"),
    platform: str = "all",
    style_id: str = "chora-editorial",
    max_cards: int = 8,
    export_images: bool = True,
) -> Path:
```

执行：

1. 生成 slug。
2. `build_content_package()`。
3. 按 platform 调用 `render_xhs_package()` 和/或 `render_wechat_package()`。
4. 可选导出图片。
5. 写入 `manifest.json`。
6. 返回 package dir。

**Step 4: Implement CLI parser**

支持：

```bash
python3 -m distribution_pipeline.generate_distribution <content_folder> --platform all --style chora-editorial --cards 8 --no-export-images
```

**Step 5: Run tests**

Run:

```bash
pytest tests/distribution_pipeline -v
```

Expected: PASS.

**Step 6: 手动验证**

Run:

```bash
python3 -m distribution_pipeline.generate_distribution \
  tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学 \
  --platform all \
  --style chora-editorial \
  --cards 5 \
  --no-export-images
```

Expected:

```text
Distribution package generated:
```

并生成：

```text
distribution/token-economics-ai/
├── source.json
├── insights.json
├── visual_system.json
├── visual_briefs.json
├── xhs/post.md
├── xhs/cards/*.html
├── wechat/*.html
├── wechat/appendix.md
└── manifest.json
```

**Step 7: Commit**

```bash
git add distribution_pipeline/generate_distribution.py tests/distribution_pipeline/test_generate_distribution_cli.py
git commit -m "feat: add distribution generation cli"
```

### Task 5.5: 新增开发说明文档 ✅

**Files:**
- Create: `docs/distribution-pipeline.md`

**Step 1: Write documentation**

文档必须包含：

- 分发流水线定位。
- 与原内容处理流水线的边界。
- 输入目录要求。
- 输出目录结构。
- CLI 使用示例。
- 小红书与公众号生成策略。
- 风格语法说明。
- 自动审稿说明。
- 常见故障排查。

**Step 2: Run markdown smoke check**

Run:

```bash
test -f docs/distribution-pipeline.md
```

Expected: exit code 0.

**Step 3: Commit**

```bash
git add docs/distribution-pipeline.md
git commit -m "docs: document distribution pipeline"
```

---

## 验收标准

完成全部阶段后，必须满足：

1. `pytest tests/distribution_pipeline -v` 全部通过。
2. 对测试夹具运行 CLI 能生成完整分发包。
3. `source.json`、`insights.json`、`visual_system.json`、`visual_briefs.json` 均为合法 JSON。
4. 小红书目录至少包含 `post.md` 和 3 张以上 HTML 卡片。
5. 公众号目录至少包含 `hero.html`、1 张以上 `inline_*.html` 和 `appendix.md`。
6. 若启用图片导出，所有 HTML 卡片都生成同名 PNG。
7. `manifest.json` 能记录平台产物数量、路径和审稿状态。
8. 新流水线不修改 `content_archive/` 原始归档内容。
9. 新流水线不影响 `export_to_json.py`、`feishu_service.py`、`frontend/api/content.js` 的既有行为。

---

## 后续增强任务

这些任务不进入 MVP，等基础流水线稳定后再做：

1. **LLM 视觉导演增强**  
   用 LLM 替换规则版 `visual_system` 与 `visual_brief`，但保留规则版作为 fallback。

2. **视觉模型审稿**  
   对导出的 PNG 做截图检查，识别文字溢出、对比度不足、构图重复。

3. **本地预览工作台**  
   新增轻量网页，支持选择内容、切换风格、预览卡片、重新生成单张卡片。

4. **多风格混合**  
   支持一组卡片在同一视觉母题下混用两套风格语法。

5. **飞书分发表字段**  
   如未来要管理分发状态，可新增独立飞书表，不建议复用现有内容展示表。

6. **批量生成历史内容**  
   新增 `--archive-root` 和 `--days` 参数，批量为历史归档生成分发包。

---

## 推荐提交节奏

每个 Task 独立提交。若实现过程中发现某个 Task 超过 30 分钟，拆成更小提交：

- `test:` 增加失败测试
- `feat:` 最小实现
- `refactor:` 整理重复逻辑
- `docs:` 更新文档

不要在同一提交中混入无关前端、飞书同步或内容归档改动。
