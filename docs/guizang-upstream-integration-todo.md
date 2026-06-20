# Guizang 上游接入 TODO

本文只记录 Chora 对 `guizang-social-card-skill` 上游规范的接入进度、问题点和后续动作。暂不处理 `process_video.py`、`process_podcast.py`、`process_feed.py`、订阅扫描或内容采集流程。

## 当前接入链路

```text
上游 guizang-social-card-skill
  -> distribution_pipeline/vendor/guizang/
  -> template_loader.py 读取 vendored template
  -> generate_distribution.py --renderer guizang
  -> guizang_renderer.py 生成 xhs/wechat 包
  -> image_assets.py 物化本地封面、搜索计划、候选图、AI fallback
  -> page_planner.py 分配页面与 recipe
  -> recipes.py 渲染 M/S recipe
  -> render.cjs 导出 PNG
  -> validator.py + validate-social-deck.mjs 做 QA
  -> manifest.json 记录结果
```

## 已完成

| 模块 | 状态 | 说明 |
|---|---|---|
| Vendor 同步 | 已完成 | `vendor/guizang` 已纳入上游 v0.14：`SKILL.md`、`README`、`PRODUCT`、`HANDOFF`、15 个 `references`、9 张 screenshot WebP、模板与 validator。 |
| 模板读取 | 已完成 | Chora 运行时通过 `template_loader.py` 读取 vendored template，不依赖本机 `~/.codex/skills/...`。 |
| XHS 基础输出 | 已完成 | 可生成 `xhs/index.html`、`xhs/post.md`、`xhs/render.cjs`。无 PNG 模式已实测可走通。 |
| WeChat cover pair | 部分完成 | 仅 Editorial 模式支持 21:9、1:1、pair preview；Swiss 会抛 `NotImplementedError`。 |
| Layout recipes | 基本完成 | Editorial M01-M16、Swiss S01-S12 均已有 renderer；planner 已有保守路由。 |
| Theme presets | 基本完成 | Editorial 6 套、Swiss 4 套可解析。 |
| Category cookbook | 部分完成 | 11 类小红书 category 与 4 类 out-of-scope pushback 已进入 `category_router.py`，但还未完整变成用户侧提示或 manifest review。 |
| Screenshot treatment | 部分完成 | 已有 `screenshot_treatment.py`，可识别截图并输出 `.frame-shot` 六参数；多截图墙、截图语义分配仍弱。 |
| Image overlay | 部分完成 | 已有 `subject_mapper.py`、`vision_subject_mapper.py`、R8/R9/R10 静态 QA；真实 360px 缩略图检查和 localized tint 仍未落地。 |
| AI fallback | 部分完成 | 已有 `assets/ai_image/gateway.py`，`candidates/download` 模式可触发 Gemini 生图兜底，`plan` 默认不触发。 |
| QA | 部分完成 | 静态 QA 已含 subject map、thumbnail policy、重复文案、scaffold label、proxy placeholder 检查；PNG 级视觉验收仍未闭环。 |

## 主要问题

### P0

1. PNG 导出链不稳
   - 已修：`render.cjs` 不再顶层 `require("playwright")`；若存在 `wkhtmltoimage` 且未显式指定 Chrome，会优先走 fallback。
   - 已修：`wkhtmltoimage` fallback 不再把临时 HTML 写进 `output/`，避免相对资源解析到错误的 `output/assets/...`。
   - 已修：XHS / WeChat render target 已带平台尺寸；XHS 为 `1080x1440`，WeChat 为 `2100x900`、`1080x1080`、pair preview `2400x844`。
   - 已修：导出策略改为 Playwright 优先，`wkhtmltoimage` 仅作强制或失败兜底；首次目检发现 wkhtml 输出近似裸 HTML，不能作为主路径。
   - 已补：根目录新增 `package.json`，声明 Guizang PNG 导出所需的 Node 侧 `playwright` 依赖。
   - 已验证：`npm install --ignore-scripts` 成功，根目录生成 `package-lock.json`，Node 可解析 `playwright` 包。
   - 已验证：`npm run guizang:install-browser` 成功，Playwright Chromium 1228 与 headless shell 1228 已安装到用户级 cache。
   - 已验证：Token 真实夹具以 Playwright 主路径生成 8 张 XHS PNG，全部 `1080x1440`；manifest `png_count=8`；validator `0 fails`、静态 QA `pass`。
   - 已目检：封面图、QR、关键 insight、philosophy、closing 均正常入版，无裸 HTML、标题裁切、资源丢失或重复文案。
   - 残留：validator 有 5 个 R5 密度 warning，属于可视质量优化项；当前不阻断 P0 导出链闭环，后续归入配方密度 P1。

2. 文档状态冲突
   - 已修：`docs/distribution-pipeline.md` 路线图已对齐为乙完成、丙/丁/戊部分完成。
   - 已修：`VENDORING.md` §4 已对齐 category 11 类、screenshot 部分实现、image-overlay 部分实现、AI fallback 部分实现、map 未实现。

3. Vision 接入未真正覆盖常规本地素材
   - 已修：`guizang_renderer.py` 向 planner 传 `_render_root`，`page_planner._asset_for_page()` 可把 `assets/images/...` 解析为真实本地文件并传给 subject mapper / vision cache。
   - 已修：`CHORA_DISTRIBUTION_VISION_PROVIDER` 默认改为 `none`；无 env 时不外呼，显式 `gemini` 才调用 vision；已有本地 cache 仍可复用。
   - 已修：`subject_mapper.py` 文件头已更新为“启发式默认 + 显式 vision 增强”的真实语义。
   - 已补测：相对路径解析、默认关闭、cache 优先、vision mock 全链路已覆盖。
   - 残留：localized tint 与 360px 缩略图检查仍未落地。

### P1

4. AI fallback 未带入真实上下文
   - 已修：`materialize_image_assets()` 新增 `category` / `theme` 参数，`guizang_renderer.py` 会传入 `detect_rednote_category(...).key` 与 resolved theme。
   - 已修：`_ai_fallback()` 不再固定 `category=None, theme=None`，candidates/download 模式会把真实上下文传给 AI gateway。
   - 已补测：candidates 模式捕捉 `_ai_fallback` kwargs，确认 category/theme 传递。
   - `candidates/download` 模式会自动 AI 兜底，需明确是否必须由用户显式选择 C 通道。

5. QA 还缺像素级验收
   - 目前有静态 HTML QA，但 360px thumbnail readability、主体避让、标题裁切、空白重心仍依赖人工。
   - 之前已发生 validator 通过但视觉失败，说明机器 QA 不是交付终点。
   - 已改善：Token 夹具 R5 密度 warning 从 5 个降到 2 个；再硬性增高会导致 xhs-06 溢出，剩余 xhs-06/xhs-07 归后续配方选择优化。

6. WeChat 上游覆盖不足
   - WeChat 仅 Editorial 支持；Swiss mode 直接 `NotImplementedError`。
   - `title-shortener.md` 只部分转成规则，仍未形成通用短标题模块。

7. Map component 未接
   - `map-component.md` 仍未落地。旅行/空间类内容只能走文本或图片证据，不能生成真实路线/地图卡。

### P2

8. License 元数据不一致
   - `LICENSE` 与 README 均为 AGPL-3.0，但 `vendor/guizang/package.json` 仍标 ISC。

9. 依赖与测试不可复现
   - 已补：根目录新增 `requirements-dev.txt`，声明 Python 测试依赖 `pytest`。
   - 已验：`venv/bin/python -m pytest tests/distribution_pipeline/test_guizang_render_script.py tests/distribution_pipeline/test_guizang_exporter.py tests/distribution_pipeline/test_guizang_validator.py -q`，19 passed。
   - 待验：Guizang 真实导出链与完整 distribution_pipeline 测试。

## 后续方案

### 1. 先收 PNG/QA 闭环

- 已完成：改 `render_script.py`，延迟 `require("playwright")`，让 `wkhtmltoimage` fallback 可先行判断。
- 已完成：建立根目录 Node 依赖入口，并由 `npm install --ignore-scripts` 生成 lock、安装 Playwright 包。
- 已完成：修正 `wkhtmltoimage` 兜底的资源相对路径与平台画板尺寸。
- 已完成：修正渲染优先级，Playwright 为主路径，wkhtml 仅作兜底；同时修正 wkhtml CSS 抽取 regex。
- 已完成：修正 validator 的 Playwright 缓存选择，避免旧项目 `.ms-playwright` 压住用户级缓存；缺浏览器二进制时归类为依赖未满足。
- 已完成：用 Token 真实夹具导出 PNG，检查数量、尺寸、manifest validator 与关键页目检。
- 将“validator 通过但仍需目检”写入 manifest 或 QA checklist。

### 2. 修文档与状态源

- 已完成：更新 `docs/distribution-pipeline.md` 路线图状态：乙完成，丙/丁/戊部分完成，并列剩余缺口。
- 已完成：更新 `VENDORING.md` §4：category 11 类、screenshot 部分实现、image-overlay 部分实现、AI fallback 部分实现、map 未实现。
- 修正 `package.json` license 或在 VENDORING 中明确该字段保留上游原样但以 LICENSE 为准。

### 3. 补 vision 真实路径

- 已完成：让 `render_guizang_xhs_package()` / `render_guizang_wechat_package()` 传入 `_render_root`，`_asset_for_page()` 可把 `assets/images/foo.jpg` 解析为真实路径。
- 已完成：统一 vision 默认策略，需 `CHORA_DISTRIBUTION_VISION_PROVIDER=gemini` 才调用外部 API；本地 cache 可在默认关闭时复用。
- 已完成：增加相对路径 vision 回归测试，避免只测绝对路径。

### 4. 收束 AI fallback 语义

- 已完成：将 category/theme 从 `guizang_renderer.py` 传入 `materialize_image_assets()`，再传给 `_ai_fallback()`。
- 增加开关语义：默认 plan 不生图；`candidates/download` 是否允许自动 AI，需要文档与环境变量一致。
- 记录 AI prompt、model、license_status、source_type 到 `SOURCES.md` 与 `image_assets.json`。

### 5. 补上游剩余能力

- Map：先做静态 schematic，再接 Mapbox/OSM。
- Screenshot：补多截图墙、设备框选择、截图可读性规则。
- WeChat：补 Swiss 或明确 WeChat 仅 Editorial。
- Title shortener：抽成独立模块，并覆盖 21:9/1:1 成对测试。

## 验证记录

- `python3 -m py_compile distribution_pipeline/renderers/guizang/*.py distribution_pipeline/assets/*.py distribution_pipeline/assets/ai_image/*.py distribution_pipeline/generate_distribution.py`：通过。
- `npm install --ignore-scripts`：通过，生成根目录 `package-lock.json`。
- `npm run guizang:install-browser`：通过，安装 Playwright Chromium 1228 与 headless shell 1228。
- `venv/bin/python -m pip install -r requirements-dev.txt`：通过，安装 pytest 8.4.2。
- `venv/bin/python -m pytest tests/distribution_pipeline/test_guizang_render_script.py tests/distribution_pipeline/test_guizang_exporter.py tests/distribution_pipeline/test_guizang_validator.py -q`：通过，19 passed。
- Guizang XHS `--no-export-images`：已可生成 HTML 与文案包。
- PNG 导出：通过。Token 真实夹具生成 8 张 XHS PNG，全部 `1080x1440`；Playwright 主路径生效；manifest 记录 Guizang validator `warn`（0 fail、5 个 R5 密度提示）；关键页目检通过。
- Vision 路径：通过。`venv/bin/python -m pytest tests/distribution_pipeline/test_guizang_vision_subject_mapper.py tests/distribution_pipeline/test_guizang_page_planner.py tests/distribution_pipeline/test_guizang_subject_mapper.py -q`：99 passed。
- AI fallback 语义：通过。`venv/bin/python -m pytest tests/distribution_pipeline/test_ai_image_gateway.py tests/distribution_pipeline/test_image_assets.py -q`：39 passed。
- 配方密度：部分改善。`tests/distribution_pipeline/test_guizang_recipes.py tests/distribution_pipeline/test_guizang_page_planner.py`：78 passed；Token manifest R5 从 5 warn 降至 2 warn，0 fail。
- 最终回归：`venv/bin/python -m pytest tests/distribution_pipeline -q`：321 passed。
- 编译检查：`python3 -m py_compile distribution_pipeline/renderers/guizang/*.py distribution_pipeline/assets/*.py distribution_pipeline/assets/ai_image/*.py distribution_pipeline/generate_distribution.py`：通过。
- 最终 Token smoke：8 张 PNG 全部 `1080x1440`；manifest `png_count=8`，Guizang validator `0 fail / 2 R5 warn`，静态 QA `pass`；`xhs` 目录无残留 `_tmp_*.html`。
- `git diff --check`：未通过，原因是既有 `process_podcast.py:472` trailing whitespace；本轮按约束不改 `process_*`。
