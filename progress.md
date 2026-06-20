# Chora Guizang/XHS 优化进度

## 2026-06-14

- 已读取技能：`caveman`、`brainstorming`、`planning-with-files`、`guizang-social-card-skill`。
- 已运行 planning session catchup；发现上一会话只涉及 `.agent/workflows/*` name 字段，非本任务范围，暂不改。
- 已检查 `process_video.py`、`process_podcast.py`、`process_feed.py`、`batch_rewrite.py`。
- 已建立计划文件：`task_plan.md`、`findings.md`、`progress.md`。
- P0.1 已完成：新增 `distribution_pipeline/automation.py`，接入 `process_video.py`、`process_podcast.py`、`process_feed.py`，并给 `batch_rewrite.py` 增加 `--generate-distribution`。
- P0.1 文档已同步：`docs/distribution-pipeline.md`、`docs/guizang-workflow-rules.md`、`skills/content-feed-summarizer/SKILL.md`。
- P0.1 编译检查通过：`python3 -m py_compile distribution_pipeline/automation.py process_video.py process_podcast.py process_feed.py batch_rewrite.py`。
- P0.2 已完成：Guizang 图源默认模式改为 `plan`，避免 daily 静默流默认联网下载未核版权图片。
- P0.3 已完成：Swiss S01/S02/S03/S04/S05/S07/S09 等非叠字页面会消费证据图；无 `subject_map` 时不走 S08 overlay。
- P0.3 已验证：Token 夹具 HTML 中 `xhs-02/xhs-03/xhs-06/xhs-08` 证据图均已进入页面。
- P0.3 文档已同步：`docs/distribution-pipeline.md`、`docs/guizang-workflow-rules.md`、`docs/guizang-recipe-coverage.md`。
- P1.1 已完成：`distribution_pipeline/renderers/xhs_copy.py` 改为题材化 caption 与语义 tag，去掉固定通用口号。
- P1.1 已验证：`py_compile` 通过，直跑断言确认 Token caption/tag 命中 AI 商业化、AI 成本、Chora、Rhizomata。
- P1.1 文档已同步：`docs/distribution-pipeline.md`、`docs/guizang-workflow-rules.md`。
- P1.2 已完成：`distribution_pipeline/renderers/guizang/title_breaker.py` 保护 `新形态`，并避免下一行以虚词开头。
- P1.2 已验证：`Token 是新形态的大宗商品` 断为 `Token 是新形态的 / 大宗商品`。
- P1.2 文档已同步：`docs/guizang-workflow-rules.md`。
- P1.3 已完成：Swiss proxy 默认显示改为 `rank 01` 形态，并新增 R14 静态 QA 阻断 `P01/P02` 可见占位符。
- P1.3 已验证：`py_compile` 通过，直跑断言确认 R14 可失败、proxy 渲染不再输出 `P01/P02`。
- P1.3 文档已同步：`docs/guizang-workflow-rules.md`、`docs/guizang-recipe-coverage.md`。
- P1.3 追加完成：Swiss closing 固定 S07 Takeaway Ledger，保留 Chora Archive + Rhizomata CTA，解决尾卡 R5 密度警告。
- P2.1 已完成：计划、发现、进度与 Guizang 文档均已同步为当前实现状态。
- P2.2 已完成：真实 Token 夹具导出 10 张 PNG，全部 `1080x1440`；manifest 记录 Guizang validator `pass`，`10 clean · 0 fails · 0 warns`。
- 完成前最终验证已通过：全量 `py_compile`、关键逻辑直跑断言、PNG 尺寸检查、独立 Guizang validator 复跑均为通过。
- P2.3 视觉回退修复进行中：`image_assets=plan` 不再生成 `chora-generated` CSS/SVG 概念假图。
- P2.3 视觉回退修复进行中：Swiss planner 不再“有图即 S04”；S09 KPI Tower 需要至少 2 个真实数字；单指标洞察回落 S03 File Card。
- P2.3 视觉回退修复进行中：S06 Pipeline 必须有 3 个以上流程/枚举节点；中文枚举会拆成独立结构节点以填满版面。
- P2.3 已验证：`pytest tests/distribution_pipeline/test_image_assets.py tests/distribution_pipeline/test_guizang_page_planner.py tests/distribution_pipeline/test_guizang_title_breaker.py`，47 passed。
- P2.3 已验证：Token HTML 包生成成功，`selected_assets=[]`，无 `chora-generated/generated_svg/evidence.svg` 入版；静态 Guizang QA 5 pass、0 fail。
- P2.3 待完成：PNG 导出因 macOS Chromium MachPort 沙箱失败；非沙箱重试被 Codex 当前额度限制拒绝，需权限/额度恢复后重跑 PNG 目检，不能标记视觉交付完成。

## 2026-06-17

- 本轮遵循用户约束：暂不修改 `process_video.py`、`process_podcast.py`、`process_feed.py` 或 YouTube/小宇宙订阅采集流程。
- 目标收窄为 Guizang 上游接入 P0：修复 `render.cjs` 导出链、补 Node 依赖入口、跑 Token PNG、完成 validator + 目检，并同步 `docs/guizang-upstream-integration-todo.md` / `docs/distribution-pipeline.md` / `VENDORING.md`。
- 已运行 planning session catchup；上一会话 `.agent/workflows/*` name 字段修改仍非本轮范围。
- 已完成导出脚本首修：`render.cjs` 不再顶层加载 Playwright；`wkhtmltoimage` fallback 不再被缺 Playwright 包阻断。
- 已新增依赖入口：根目录 `package.json` 声明 Node 侧 Playwright；`requirements-dev.txt` 声明 Python 测试依赖 pytest。
- 已安装依赖：`npm install --ignore-scripts` 成功并生成 `package-lock.json`；`venv/bin/python -m pip install -r requirements-dev.txt` 成功安装 pytest。
- 已安装 Playwright 浏览器：`npm run guizang:install-browser` 成功，Chromium 1228 与 headless shell 1228 进入用户级 cache。
- 已完成导出脚本二修：`wkhtmltoimage` fallback 临时 HTML 改回包根目录，修复相对资源解析；XHS / WeChat render target 均显式携带平台尺寸。
- 已完成 validator 依赖识别修复：Playwright 浏览器缓存选择改为用户缓存优先、项目缓存兜底；缺浏览器二进制时归入依赖未满足。
- 已验证：`venv/bin/python -m pytest tests/distribution_pipeline/test_guizang_render_script.py tests/distribution_pipeline/test_guizang_exporter.py tests/distribution_pipeline/test_guizang_validator.py -q`，19 passed。
- 已完成导出脚本三修：首次目检发现 wkhtml 主路径 PNG 近似裸 HTML；已改为 Playwright 优先、wkhtml 仅作强制或失败兜底，并修正 wkhtml CSS 抽取 regex。
- 已验证：上述定向 pytest 复跑仍为 19 passed。
- 已验证真实导出：Token 夹具生成 8 张 XHS PNG，全部 `1080x1440`；Playwright 主路径生效；manifest `png_count=8`，Guizang validator `0 fails`、5 个 R5 密度 warning，静态 QA `pass`。
- 已目检关键 PNG：封面图、QR、关键 insight、philosophy、closing 均正常入版，无裸 HTML、标题裁切、资源丢失或重复文案。
- 已同步状态漂移：`docs/distribution-pipeline.md` 路线图改为乙完成、丙/丁/戊部分完成；PNG 依赖命令、Playwright 主路径、Token 8 张验收基线已更新。
- 已同步 vendoring 状态：`distribution_pipeline/vendor/guizang/VENDORING.md` §4 已记录 category 11 类、screenshot 部分实现、image-overlay 部分实现、AI fallback 部分实现、map 未实现。
- 已完成 vision 相对路径修复：renderer 向 planner 传 `_render_root`，`assets/images/...` 可解析为真实本地文件并进入 subject mapper / vision cache。
- 已统一 vision 默认策略：`CHORA_DISTRIBUTION_VISION_PROVIDER` 默认 `none`，无 env 不外呼；显式 `gemini` 才调用外部 API；本地 cache 可复用。
- 已验证：`venv/bin/python -m pytest tests/distribution_pipeline/test_guizang_vision_subject_mapper.py tests/distribution_pipeline/test_guizang_page_planner.py tests/distribution_pipeline/test_guizang_subject_mapper.py -q`，99 passed。
- 已完成 AI fallback 上下文传递：`materialize_image_assets()` 接收 category/theme，Guizang renderer 传入检测品类与 resolved theme，`_ai_fallback()` 不再固定走通用 prompt。
- 已验证：`venv/bin/python -m pytest tests/distribution_pipeline/test_ai_image_gateway.py tests/distribution_pipeline/test_image_assets.py -q`，39 passed。
- 已改善 R5 密度：Swiss S02/S03/S12 面板高度保守上调，Token manifest 从 5 个 R5 warning 降到 2 个，且保持 `0 fail`。
- 已验证：`venv/bin/python -m pytest tests/distribution_pipeline/test_guizang_recipes.py tests/distribution_pipeline/test_guizang_page_planner.py -q`，78 passed。
- 已修复图源候选回归：Pexels provider 现在接受 `src.large` 作为候选图 URL fallback。
- 已验证：`venv/bin/python -m pytest tests/distribution_pipeline/test_image_providers.py -q`，2 passed。
- 后续：剩余 xhs-06/xhs-07 R5 warning 需通过更细的 recipe 选择或内容扩写优化；当前不再硬塞高度，避免产生 R1 overflow。
- 最终回归已验证：`venv/bin/python -m pytest tests/distribution_pipeline -q`，321 passed。
- 最终编译已验证：`python3 -m py_compile distribution_pipeline/renderers/guizang/*.py distribution_pipeline/assets/*.py distribution_pipeline/assets/ai_image/*.py distribution_pipeline/generate_distribution.py` 通过。
- 最终 Token smoke 已验证：8 张 PNG 全部 `1080x1440`，manifest `png_count=8`，Guizang validator `0 fail / 2 R5 warn`，静态 QA `pass`，无 `_tmp_*.html` 残留。
- `git diff --check` 仍失败于既有 `process_podcast.py:472` trailing whitespace；本轮遵守用户约束，未修改 `process_*` 工作流文件。

## 2026-06-18

- 本轮首先修复中高风险问题，再继续 Guizang 后续开发。
- 中高风险修复：
  - 清理 `config/sources.yaml`、`config/feishu.yaml` 中的硬编码 API key，迁移到 `.env`；新增 `config_loader.py` 统一加载，环境变量优先。
  - 新增 `requirements.txt` 锁定 Python 运行时依赖，新增 `python-dotenv`、`Pillow`。
  - 删除空 `skills/podcast-cover-generator/` 目录，更新 `CLAUDE.md` 与 `skills/content-feed-summarizer/SKILL.md` 说明 `.env` 优先与配置统一位置。
  - 新增 `utils/archive_cleanup.py` 与 `process_feed.py` 自动清理逻辑，默认 30 天后删除 `audio.m4a/mp3`。
  - 修复 `process_podcast.py:472` trailing whitespace。
- Guizang P2.5 后续开发：
  - R5 密度优化：xhs-06 短内容改走 S11 Stacked Ledger（补底部 stat），xhs-07 philosophy 默认走 S07 Takeaway Ledger；Token 验证基线从 2 R5 warn 降到 1 warn，0 fail。
  - 新增 S13 Map · Route：按地理/跨境/迁移信号自动提取文本中的区域节点，生成抽象路线卡片；新增 page planner 路由、recipes renderer、3 个回归测试。
  - 补全 WeChat Swiss 渲染：`render_guizang_wechat_package` 支持 `editorial`/`swiss` 两种模式；新增 `_render_wechat_swiss_wide` / `_render_wechat_swiss_square`。
  - 360px 缩略图检查：`export_guizang_images` 导出 PNG 后自动生成 360px 缩略图到 `output/thumbnails/`，manifest 记录 `thumbnail_files`；新增 exporter 回归测试。
- 文档同步：`docs/distribution-pipeline.md`、`docs/guizang-recipe-coverage.md`、`distribution_pipeline/vendor/guizang/VENDORING.md`、`task_plan.md` 已更新。
- 最终回归：`/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m pytest tests/distribution_pipeline -q`，327 passed。
- 最终编译：`python3 -m py_compile` 通过。
- `git diff --check` 通过。
