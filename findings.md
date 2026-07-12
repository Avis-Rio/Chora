# Chora Guizang/XHS 优化发现

## 初始现状

- 当前工区已有上一轮未提交改动：Guizang auto mode、copy-slot、R11/R12、Swiss 收尾 CTA、标题断行等。
- `process_video.py` 与 `process_podcast.py` 在 rewrite 成功后停止，没有自动调用 `distribution_pipeline.generate_distribution`。
- `process_feed.py` 的简化批处理同样只到 rewrite 与 state 更新。
- `batch_rewrite.py` 修复缺失 `rewritten.md` 后没有分发后处理。
- `generate_distribution.py` 当前 Guizang 参数默认 `guizang_mode=auto`，但 CLI 默认 renderer 仍是 `basic`。
- `generate_distribution.py` 当前 `image_asset_mode=download`，对静默 daily 流存在版权与网络不稳定风险。

## P0 完成记录

- 新增 `distribution_pipeline/automation.py`，提供 `generate_distribution_after_rewrite()`。
- `process_video.py`、`process_podcast.py`、`process_feed.py` 已在 rewrite 成功后自动调用 Guizang XHS 分发。
- `batch_rewrite.py` 新增 `--generate-distribution`，用于补写 `rewritten.md` 后生成分发包。
- 自动分发失败会写入内容目录 `distribution_errors.log` 并继续主流程。
- P0.2 已把 `generate_distribution.run()`、CLI `--image-assets`、Guizang XHS/WeChat renderer 的默认图源模式改回 `plan`。
- 手动下载外部图仍可用 `--image-assets download` 显式开启。
- P0.3 已让 Swiss 多个非叠字 recipe 消费证据图；没有 `subject_map` 时不走 S08 overlay，避免图片生成了但页面仍是纯文字。
- Token 夹具 HTML 级验证已看到 `xhs-02/xhs-03/xhs-06/xhs-08` 证据图进入页面，且没有把这些图放入 `.image-hero` overlay。
- P1.1 已将 XHS caption 从固定通用段落改为题材化开场、问题清单和读者场景。
- P1.1 已扩展语义标签，并为 `深度阅读`、`Chora`、`Rhizomata` 预留位置，避免题材标签过多时挤掉品牌标签。
- P1.2 已把 `新形态` 加入标题保护短语，并提高次行以虚词开头的惩罚，避免 `Token 是新形 / 态的大宗商品` 与 `的...` 起行。
- P1.3 已把 Swiss proxy 默认显示从 `P01/P02` 改为 `rank 01/rank 02`，并新增 R14 静态 QA 阻断内部 proxy placeholder 外泄。
- P1.3 已把 Swiss closing 固定回 S07 Takeaway Ledger，避免在前一页也是 S07 时为避重落到稀疏 S12。
- P2.2 已完成真实 Token 夹具导出：10 张 PNG 均为 `1080x1440`，Guizang validator `pass`，`10 clean · 0 fails · 0 warns`。

## P2.3 视觉回退复盘

- 人工目检发现 P2.2 虽然 validator 通过，但 `xhs-02/xhs-03` 消费了本地生成的 CSS/SVG 概念假图，实际观感弱于原 Guizang 审美。
- 根因一：`image_assets=plan` 仍会追加 `chora-generated` fallback，使搜索计划被误当作可用 evidence。
- 根因二：Swiss planner 曾把“有图但无 subject_map”直接派到 S04，导致假图优先级压过文本语义。
- 根因三：S09 KPI Tower 只需 1 个数字即可启用，`50倍` 这种单指标洞察被撑成低密度塔式布局。
- 根因四：S06 Pipeline 对两句正文也启用三栏卡，节点不足时形成大片空白。
- 当前修复：plan 模式不再生成 SVG fallback；S04 不再被普通 evidence 强派；S09 需至少 2 个真实数字；S06 需至少 3 个流程/枚举节点，中文顿号枚举会拆成三节点。
- 新交付标准：validator 通过只能算机器 QA 通过，最终仍需对关键 PNG 做目检，尤其检查假图、标题裁切、下方空白与版式重心。

## Guizang Skill 规则

- XHS 3:4 必须 `1080x1440`。
- 页面应一页一观点，内容填充需覆盖约 75%-78% 画布高度。
- 静默自动化不能反复询问图片来源；daily 流应采用保守默认并记录 provenance。
- `image_assets=plan` 只允许生成搜索计划与复制本地素材，不允许把 CSS/SVG 概念图写成可用 evidence。
- 图上叠字必须有 subject map 与缩略图可读性检查。
- 重复可见文案是硬失败；R11/R12 已存在。

## 2026-06-17 Guizang 上游接入发现

- 用户明确要求：`process` 工作流（YouTube 订阅、小宇宙）暂不修改；本轮只检查与修复 Guizang skill 上游接入流程。
- 新增 `docs/guizang-upstream-integration-todo.md`，记录已完成模块、P0/P1/P2 问题与后续方案。
- `render_script.py` 生成的 `render.cjs` 顶层 `require("playwright")`，导致缺 Playwright 时无法进入 `wkhtmltoimage` fallback，是 PNG 导出 P0 阻塞。
- `VENDORING.md` 与 `docs/distribution-pipeline.md` 存在状态漂移：乙/丙/丁/戊代码已部分落地，但部分表格仍写待办/未实现。
- 已修复 `render_script.py`：Playwright 改为 `_loadPlaywrightChromium()` 延迟加载；若可用 `wkhtmltoimage` 且未显式设置 `PLAYWRIGHT_CHROMIUM_PATH`，会先走 sandbox-safe fallback。
- 真实 Token 首次 PNG 导出能写出 8 张，但 wkhtml 警告 `source-cover.jpg` 与 `rhizomata-qr.png` 从 `xhs/output/assets/...` 查找，根因是临时 HTML 写在 `output/` 下导致相对资源基准错位。
- 首次 PNG 尺寸为 `1242x1660`，不符合上游 XHS `1080x1440` 要求，根因是 wkhtml fallback 写死旧 viewport。
- 已修复尺寸与资源根因：XHS / WeChat render target 显式携带平台尺寸；wkhtml 临时 HTML 改写到包根目录；相关定向测试 19 passed。
- validator 首次失败不是内容 QA 失败，而是 Playwright 1.61 期待 `chromium_headless_shell-1228`，项目 `.ms-playwright` 仅有 1223 且压住用户级缓存；已改为用户缓存优先，缺浏览器二进制归类为依赖未满足。
- 第二次 PNG 目检发现虽然尺寸为 `1080x1440` 且资源警告消失，但页面近似裸 HTML，视觉失败；根因是 `wkhtmltoimage` 旧 WebKit 路径被置为主路径，且 CSS 抽取 regex 使用了错误的 `\\s\\S` 字面匹配。
- 已修正：Playwright 恢复为主渲染路径，`wkhtmltoimage` 仅在 `GUIZANG_RENDERER=wkhtmltoimage` 或 Playwright 不可用/启动失败时兜底；CSS 抽取 regex 改为 `[\s\S]`。
- 第三次真实导出已走 Playwright `screenshot` 主路径，8 张 PNG 均为 `1080x1440`，封面图与 QR 正常；manifest 中 Guizang validator `0 fails`、静态 QA `pass`。
- 残留风险：xhs-02/03/04/06/07 有 R5 密度 warning（70%-72%，xhs-07 58%），目检未见裁切或资源问题；后续应从 recipe/planner 层增加密度填充，而不是影响已闭合的 PNG 导出链。
- `docs/distribution-pipeline.md` 的路线图与导出说明已对齐当前代码：乙完成，丙/丁/戊部分完成；Playwright 为主渲染路径，wkhtml 仅兜底；Token 验收基线为 8 张 PNG。
- `distribution_pipeline/vendor/guizang/VENDORING.md` §4 已对齐当前消费状态，不再误称 category 仅 4 类、image-overlay / screenshot-treatment 未实现。
- Vision 相对路径问题已修复：`assets/images/...` 现在会按 `_render_root` 解析为真实文件路径，传给 `build_subject_map(image_path=...)` 与 vision cache。
- Vision 默认策略已统一为保守默认：`CHORA_DISTRIBUTION_VISION_PROVIDER` 未设时关闭外部调用；显式 `gemini` 才访问 API；本地 `.subject_map_cache.json` 命中仍可复用。
- AI fallback 语义漂移已修复：`materialize_image_assets()` 可接收 category/theme，Guizang renderer 传入实际品类与 resolved theme；candidates/download 模式不再总是走通用 prompt。
- R5 密度优化需谨慎：上调 S12 3-cell 高度到 260px 会让 xhs-06 产生 R1 overflow（scrollH 1539 > clientH 1440）；最终保留 3-cell 220px、4-cell 300px，Token R5 从 5 warn 降到 2 warn 且 0 fail。
- 全量 distribution_pipeline 测试暴露 Pexels 候选解析缺口：mock / API 可只返回 `src.large`，原实现只读 `medium/small/large2x`，导致 Pexels 候选被过滤；已补 `large` fallback。

## 2026-07-12 process-url 实测暴露的飞书同步链路 bug

### B1 飞书 schema 缺「是否发布」字段

- 现象：用户新建飞书表 → 没有「是否发布」复选框 → `/api/content` 过滤 `isPublished === true` 永远取不到 `undefined` → 文章**永不显示**
- 修复：`config/feishu-setup.md` 加入该字段推荐
- 教训：所有 schema 变更必须**同时**更新 `feishu-setup.md` / `_fields.py:DEFAULT_FIELD_ALIASES` / `frontend/api/content.js:FIELD_ALIASES`

### B2 新建飞书记录不自动勾选发布

- 现象：表里有字段，但新文章默认 `published=False`
- 修复：`sync_from_export` 在 `create_record` 前注入 `item["published"]=True`
- 设计要点：
  - 默认开启（用户期望"即创即显"）
  - env override `CHORA_FEISHU_AUTO_PUBLISH=false` 可关
  - per-record override 永远不被覆盖（`if "published" not in item`）
- 防回归：3 个新单测

### B3 本地 fallback JSON 不同步

- 现象：`frontend/data/content.json` 与飞书表脱节；API 抖动时显示陈旧数据
- 修复：`sync_from_export` 末尾自动调 `generate_frontend_data.py`（subprocess.run，失败仅 print 不抛异常）
- 设计要点：
  - 仅在 `(created + updated) > 0` 时触发（避免 0 改动也跑）
  - env override `CHORA_FEISHU_REGENERATE_FRONTEND=false` 可关（CI 场景）
- 防回归：2 个新单测

### B4 Bitable type 7↔17 互换（最阴险）

- 现象：`_feishu_type_to_internal` 把 `7→checkbox` / `11→attachment`
- 影响链：
  1. `get_table_fields()` 把"封面"字段报为 `text`
  2. `_map_to_fields` 走 text formatter → 返回字符串 `str(file_token)`
  3. 飞书 API 收到 `{"封面": "EX00xxxx..."}` 而不是 `[{file_token}]`
  4. 飞书返回 `code=1254069, msg=AttachFieldConvFail`
  5. `update_record` 失败但日志只说"create failed"——根因被埋
- 修复：交换 7↔17 + 加 string alias 表
- 教训：**type ID 是 Bitable 不可绕过的契约**，错了静默丢失 attachment 而不报错
- 历史数据恢复：045 这条记录 out-of-band raw PUT 修复

### CI 调试经验（避坑）

- `set +e` + `head -c 4500` 截断 stdout 看似"节省日志"，实际：
  - 截断后 pytest exit code 是 head 的，不是 pytest 的
  - traceback 被 head 吃掉，看不到真实错误
  - 在 ubuntu runner 上行为与 macOS 不一致
- 简化 ci.yml 为 `python -m pytest ... -q --tb=short` + artifact 上传完整 stdout/stderr，是最稳的 CI 写法

### Vercel 部署根 = frontend/

- DEPLOY.md 第 35 行明确 "Root Directory: frontend"
- Vercel 静态文件路径以 `frontend/` 为根
- 仓库根下的同名目录（`covers/`、`content.json`）Vercel 看不到
- 前端 `<img src="/covers/xxx.jpg">` → 部署后对应 `frontend/covers/xxx.jpg`
- 含义：**所有"在仓库根 covers/ 下加文件"的操作对线上无效**，必须放到 `frontend/covers/`

### 封面图双轨制

| 路径 | 服务方式 | 自动同步？ |
|---|---|---|
| 飞书 cover field | `/api/image?token=xxx` 代理 | ✅ `sync_from_export` 自动 |
| `frontend/covers/{safe_name}.jpg` | 直接静态托管 | ❌ 需手动 cp + commit |

未来改进方向：让 `process-podcast.py` 跑完自动调 `sync_covers.py`（已在 #7 follow-up 列表）。
