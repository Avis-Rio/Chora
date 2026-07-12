# Chora 项目现状报告

> **报告日期**：2026-07-11
> **最近一次有效代码提交**：`01e56d7 feat(cover): add Pexels/Unsplash fallback for Gemini failures`
> **当前工区**：有未提交改动（distribution_pipeline 改进）
> **最近一次完整回归测试**：2026-06-18，`pytest tests/distribution_pipeline -q` → 327 passed

---

## 一、项目定位

**Chora** 是一个自动化的内容聚合与处理流水线，覆盖：

1. **采集**：YouTube 频道 + 小宇宙播客
2. **转录**：yt-dlp / YouTube 字幕 API / Groq Whisper（large-v3）
3. **改写**：基于 LLM 的中文结构化摘要（执行摘要/金句/核心概念/批判性讨论/行动指南）
4. **归档**：本地 `content_archive/{date}_{platform}_{channel}_{title}/`
5. **分发**：本地 README / 飞书多维表格 / Vercel 前端展示
6. **运营素材**：微信公众号 + 小红书双平台素材包（Editorial + Swiss 双风格，Guizang 渲染后端）

整体处于"内容采集+AI 改写"核心成熟、"运营素材生成"半成熟、"自动化运营闭环"待补的阶段。

---

## 二、架构与数据流

### 2.1 端到端数据流

```
┌────────────────────────────────────────────────────────────────────┐
│  内容源                                                            │
│  YouTube 频道 RSS ─┐                                                │
│                    ├──> fetch_feed.py                              │
│  小宇宙播客列表 ───┘    (关键词/日期/时长/去重 过滤)                  │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  单 URL / 批量处理 Skill                                           │
│  process-url / process-subscriptions                                │
│  → process_video.py        → process_podcast.py                    │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  content_archive/{date}/{platform}_{channel}_{title}/              │
│    ├── metadata.md       (YAML frontmatter + 嘉宾 + 金句)          │
│    ├── transcript.md     (原始转录)                                │
│    ├── rewritten.md      (AI 改写结构化摘要)                       │
│    ├── cover.{jpg,png}   (封面：原图 or Gemini 生成)                │
│    └── audio.m4a         (原始音频，30 天自动清理)                  │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  下游分发（4 个出口）                                              │
│  ① export_to_json.py        → content_export.json（44 条，最全字段）│
│  ② generate_frontend_data.py → frontend/public/data/*.json（30 条）│
│  ③ feishu_service.py sync   → 飞书多维表格（手动控制 isPublished）  │
│  ④ distribution_pipeline/   → 微信公众号 + 小红书素材包           │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  Vercel 前端                                                       │
│  api/content.js (飞书代理) + api/image.js (封面代理)               │
│  index.html / app.js / styles.css                                  │
│  CDN 缓存 30s + stale-while-revalidate=15                          │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 Skill 编排（"1 核 2 入口"）

```
content-feed-summarizer  (核心引擎，含配置、协议、维护工具)
        │
        ├─→ process-url            (单 URL，无须确认)
        │
        └─→ process-subscriptions  (批量，必须先列清单+确认)
```

---

## 三、模块清单

### 3.1 Skills（3 个）

| Skill | 行数 | 职责 |
|---|---|---|
| `content-feed-summarizer` | SKILL.md 235 行 | 核心引擎；持有完整工作流、配置规范、维护工具、反例集、理想输出样例 |
| `process-url` | SKILL.md ~110 行 | 薄 façade：单 URL 入口，无须确认 |
| `process-subscriptions` | SKILL.md ~105 行 | 薄 façade：批量入口，先列清单再确认 |

**评价**：薄 façade 设计符合"一个核心 + 多个薄入口"原则，冗余度低。但 `process-subscriptions` 比 `process-url` 多一步"列出清单等待确认"，与 `content-feed-summarizer` 反例集"❌ 停下来请求确认"形成正反对照——是有意编排的训练契约，**不要去掉确认步骤**。

### 3.2 Python 脚本（19 个，5,382 行）

#### 核心工作流（被 Skill 调用）

| 脚本 | 行数 | 职责 |
|---|---|---|
| `process_video.py` | 177 | YouTube 单视频全流程（5 步：元数据→归档→封面→字幕→改写→分发） |
| `process_podcast.py` | 426 | 小宇宙单播客全流程（最复杂：含 ffmpeg 切片 + Groq Whisper 并行转录） |
| `batch_rewrite.py` | 298 | 扫描 `rewritten.md` 缺失项分批重写；支持 `--generate-distribution` 联动 |
| `fetch_feed.py` | 444 | 扫描 YouTube + 小宇宙 RSS，按过滤规则返回待处理项 |
| `feishu_service.py` | 653 | 飞书 Bitable API 封装（access token 缓存 + 字段别名 + 批量 upsert + 封面上传） |
| `generate_cover.py` | 1008 | 30+ 风格 prompt 调 Gemini 出图，失败回落 stock_cover_service |

#### 核心服务模块

| 脚本 | 行数 | 职责 |
|---|---|---|
| `youtube_service.py` | 230 | yt-dlp + youtube-transcript-api + LLM 翻译字幕 |
| `xiaoyuzhou_service.py` | 392 | 小宇宙 Next.js __NEXT_DATA__ → JSON-LD → OpenGraph → meta 四级 fallback |
| `rewrite_service.py` | 389 | LLM 流式改写，按 rewrite-prompt.md 输出 6 段式中文摘要 |
| `stock_cover_service.py` | 204 | Pexels / Unsplash API 兜底封面 |
| `config_loader.py` | 117 | 统一 YAML + .env 合并 |

#### 辅助 / 手动工具

| 脚本 | 行数 | 状态 |
|---|---|---|
| `export_to_json.py` | 327 | 手动；归档 → JSON 导出（前端/飞书/分发的前置） |
| `generate_frontend_data.py` | 94 | 手动；content_export.json → 前端 JSON |
| `sync_covers.py` | 94 | 手动；封面同步到 frontend/public/covers/ |
| `normalize_tags.py` | 213 | 维护期；中英标签映射到 25 个标准 taxonomy |
| `process_feed.py` | 192 | 半废弃；与 process-subscriptions Skill 重叠 |
| `batch_process.py` | 36 | 历史遗物；写死 6 条 URL |
| `clean_tags.py` | 67 | 历史遗留；已被 normalize_tags 替代 |
| `inspect_page.py` | 21 | 调试遗物；硬编码 page.html |

**调用关系图核心结论**：被 Skill 直接调用的脚本只有 **6 个**，其余 13 个是辅助服务或手动工具，存在明显冗余空间。

### 3.3 前端

| 文件 | 行数 | 用途 |
|---|---|---|
| `index.html` | 190 | 单页结构（导航/搜索/标签/卡片网格/阅读器/弹窗） |
| `app.js` | 783 | 原生 JS（无框架）：loadData / 搜索 / 过滤 / 渲染 / 阅读器 |
| `styles.css` | 1740 | 设计系统（CSS Variables + 3 段响应式 1024/768/480） |
| `api/content.js` | 236 | Vercel Serverless：飞书代理，CDN 缓存 30s |
| `api/image.js` | 81 | Vercel Serverless：飞书图片代理 |
| `data/content.json` | 124KB | 老版本（9 条，本机/历史） |
| `public/data/content.json` | 504KB | 主数据（30 条，供 Vercel 静态托管） |

**CLAUDE.md 描述功能 vs 实际实现**：100% 匹配（卡片网格、TOC、搜索、过滤、Logo 旋转、移动端优化、表格横滚、IntersectionObserver 高亮、CDN 缓存）——代码实现扎实。

### 3.4 distribution_pipeline（第二代分发素材流水线）

**结构**（自下而上）：

```
vendor/guizang/                上游 vendored：模板 + 15 份 references + magazine-bg-webgl.js
  ↓
extractors/                    metadata_parser / insight_parser / package_builder
  ↓
directors/                     visual_system / visual_brief / card_copy / style_loader
  ↓
renderers/
   ├─ html/wechat/xhs (基础后端)
   └─ guizang/                第二代：recipe(M01-M16/S01-S13) + page_planner + subject_mapper
                              + vision_subject_mapper + validator(R11/R12/R14/R16) + exporter
  ↓
reviewers/                     text_density / repetition
  ↓
assets/                        image_assets / providers / downloader / ai_image/gateway
  ↓
automation.py                  自动后处理入口（CHORA_DISTRIBUTION_AUTO 触发）
generate_distribution.py       CLI 入口（--platform / --renderer / --guizang-mode / --image-assets）
```

**测试覆盖**：39 个 test_*.py，估计 **300+ test_ 函数**，最近一次全量 327 passed（2026-06-18）。

**Guizang 集成进度**：Editorial 16/16 recipe（M01-M16）+ Swiss S01-S13；6 套 Editorial 主题 + 4 套 Swiss 主题；11 类小红书品类 cookbook；SubjectMapper 启发式 + Gemini Vision 双实现；18 条静态 QA 规则；WeChat 21:9 + 1:1 + pair preview 画板。

### 3.5 配置 / 文档

| 类别 | 文件 | 用途 |
|---|---|---|
| 配置 | `config/sources.yaml` | 真实运行配置（3 YouTube + 2 小宇宙订阅源） |
| 配置 | `config/state.yaml` | 已处理 ID 去重列表（19 个） |
| 配置 | `config/rewrite-prompt.md` | 119 行改写 Prompt（评分模型 + 强制结构） |
| 配置 | `config/feishu.yaml` | 飞书凭据占位 |
| 文档 | `docs/PRD.md` | 产品需求文档 v1.0 |
| 文档 | `docs/distribution-pipeline.md` | 分发流水线核心文档（681 行） |
| 文档 | `docs/guizang-*.md` | Guizang 接入相关 3 份（workflow-rules / recipe-coverage / upstream-integration-todo） |
| Plan | `docs/plans/2026-05-26-distribution-asset-pipeline.md` | 基础流水线 plan（1445 行） |
| Plan | `docs/plans/2026-05-31-guizang-renderer-integration.md` | Guizang 集成 plan（1588 行） |
| 部署 | `frontend/DEPLOY.md` | Vercel 部署指南（178 行） |
| 部署 | `config/feishu-setup.md` | 飞书多维表格部署指南（122 行） |
| 部署 | `config/vercel-deploy-guide.md` | Vercel 部署步骤（108 行） |

---

## 四、数据规模

| 维度 | 数量 | 备注 |
|---|---|---|
| `content_archive/` | 43 个日期目录 | 最早 2021-09-06，最新 2026-05-19 |
| `content_export.json` | 44 条 | 最全字段（含 transcript/word_count/folder_path） |
| `frontend/public/data/content.json` | 30 条 | 主前端数据 |
| `frontend/data/content.json` | 9 条 | **老版本，未同步** |
| `distribution/` | 1 个发布包 | 2026-06-21 生成（关键词"午后偏见"触发的小宇宙节目） |
| `frontend/covers/` | 12 个封面文件 | 4 小宇宙 + 7 YouTube + 1 重复 |
| 测试文件 | 41 个 | 39 个 distribution_pipeline + 2 个根级 + conftest |

---

## 五、依赖与基础设施

### 5.1 Python 依赖（8 个）

```
groq>=0.4.0              Whisper 音频转录
PyYAML>=6.0              YAML 配置解析
requests>=2.31.0         HTTP 请求
python-dotenv>=1.0.0     .env 自动加载
Pillow>=10.0.0           封面裁剪
yt-dlp>=2024.0.0         YouTube 元数据/字幕下载
youtube-transcript-api>=0.6.0  YouTube 字幕获取
playwright>=1.40.0       PNG 导出（需 chromium）
```

外加系统依赖 `ffmpeg`（音频切分）。

### 5.2 Node 依赖

仅 `playwright@^1.60.0`（chromium 安装用）。无构建工具。

### 5.3 环境变量（10 个）

```
GROQ_API_KEY            Whisper 转录
GEMINI_API_KEY          Gemini 出图
GEMINI_BASE_URL         可选覆盖
GEMINI_MODEL            gemini-3.1-flash-image-preview
LLM_API_KEY             内容改写
LLM_BASE_URL            可选覆盖
LLM_MODEL               claude-sonnet-4-20250514
FEISHU_APP_ID/SECRET    飞书多维表格
FEISHU_BASE_ID/TABLE_ID
VERCEL_BASE_URL         部署域名
```

### 5.4 CI 状态

**未配置 CI**（无 `.github/workflows/`、无 `pyproject.toml`、无 `pytest.ini`、无 `Makefile`、无 `.pre-commit-config.yaml`）。所有 41 个测试仅本地运行。

### 5.5 测试规模与质量

- **根级**：`tests/conftest.py` 仅 8 行 sys.path 注入，无 fixture、无 .env 加载。
- **distribution_pipeline**：39 个文件，估计 300+ 测试用例，覆盖率重；最近一次 327 passed（0.42s）。
- **测试与 .env 完全解耦**：测试套件纯函数式，少数网络测试显式 `pytest.skip` 处理失败。

---

## 六、已发现的问题清单

### 6.1 数据未同步（高优）

| 问题 | 影响 | 修复方式 |
|---|---|---|
| `frontend/data/content.json` 9 条 vs `content_export.json` 44 条 | 前端 API 失败时只展示 9 条老内容 | 重跑 `generate_frontend_data.py` |
| `public/data/summary.json` 含反引号包裹的脏标签（`` `Deep Dive` `` 等） | 影响 summary 过滤逻辑 | 修复 `generate_frontend_data.py` 标签清洗 |
| `distribution/` 仅 1 个发布包 | 分发链路未批量跑通 | 跑 `batch_rewrite.py --generate-distribution` |

### 6.2 前端隐性 bug（中优）

| 问题 | 影响 | 修复方式 |
|---|---|---|
| `covers/` 缺少 `default.jpg`（`app.js:233/337` 引用） | 封面缺失直接 404 | 添加兜底图或改为 `onerror` |
| `app.js` 降级路径用 `/data/content.json` 而非 `/public/data/content.json` | API 失败时数据缩水到 9 条 | 改降级路径 |
| `covers/` 含 2 个同名不同 encoding 的重复文件 | 占用 124 KB | 去重 |
| `index.html` 无 `.nav-links` 元素但 `styles.css:730` 隐藏 | 死 CSS（730 行） | 删除 |
| `src/app/` 与 `src/components/` 两个空目录 | 历史遗留 | 删除 |
| `content.js` field alias 中 `rewritten` 同时映射 `正文/摘要/内容` | 飞书表多字段时行为不可预测 | 改冲突消解策略 |
| 平台/频道级过滤缺失 | 仅支持 tag 过滤 | 加 YouTube/小宇宙切换按钮 |

### 6.3 仓库卫生（低优）

| 问题 | 影响 | 修复方式 |
|---|---|---|
| `clean_tags.py` 完全可删（被 `normalize_tags.py` 替代） | 冗余代码 67 行 | 删除 |
| `inspect_page.py` 21 行调试遗物 | 冗余 | 删除或移入 `tests/` |
| `batch_process.py` 36 行写死 6 条 URL | 历史遗物 | 删除 |
| `process_feed.py` 192 行与 `process-subscriptions` Skill 重叠 | 功能重叠 | 合并或废弃 |
| 7 个根目录文件未被 `.gitignore`（`.m4a`、2×169KB HTML、3 个 debug .py） | 会被 git 跟踪 | 补 `.gitignore` |
| `.pytest_cache/` 未被 `.gitignore` | 仓库污染 | 补 `.gitignore` |
| `generate_cover.py` 1008 行独占 18% 代码量 | 单文件过大 | 按风格拆分（可选） |
| AGENTS.md 与 CLAUDE.md 同步滞后（脚本清单、Gemini 模型版本） | 双份文档漂移 | 以 CLAUDE.md 为准删除 AGENTS.md 或同步更新 |

### 6.4 文档与代码一致性

| 问题 | 备注 |
|---|---|
| CLAUDE.md 列出的脚本与实际完全对齐 | ✅ 一致 |
| CLAUDE.md 描述的前端功能与代码 100% 匹配 | ✅ 一致 |
| `docs/distribution-pipeline.md` 与代码对齐 | ✅ 一致 |
| `progress.md` / `task_plan.md` / `findings.md` 时间最新 2026-06-18 | ⚠️ 距今近一个月未更新 |
| Guizang 残留 TODO（`guizang-upstream-integration-todo.md`）：WeChat Swiss `NotImplementedError`、360px thumbnail 像素 QA、真实 Mapbox/OSM | 待补 |

### 6.5 安全与可观测性

| 问题 | 备注 |
|---|---|
| 无 CI（41 个测试无自动回归保护） | **关键缺口** |
| 无结构化日志框架（混用 `print` 和 `logging`） | 调试困难 |
| 无错误上报（仅 `processing_errors.log` / `distribution_errors.log` 本地文件） | 远程故障难发现 |
| 无 retry / rate-limit 统一封装（脚本内部各自重试） | 维护成本高 |
| `requirements.txt` 无版本上限 | 依赖漂移风险 |

---

## 七、改进优先级建议

### P0（立即处理，影响线上）

1. **同步前端数据**：重跑 `generate_frontend_data.py`，让 `frontend/data/content.json` 反映 44 条全集。
2. **修复 `covers/default.jpg` 缺失**：添加兜底图，避免封面 404。
3. **修复 `app.js` 降级路径**：从 `/data/content.json` 改到 `/public/data/content.json`。
4. **修复 `summary.json` 脏标签**：在 `generate_frontend_data.py` 中过滤反引号。

### P1（一周内，影响开发效率）

5. **删除冗余脚本**：`clean_tags.py` / `inspect_page.py` / `batch_process.py`。
6. **补 `.gitignore`**：`.pytest_cache/`、根目录 7 个调试文件、`*.html`（调试用）。
7. **添加 CI**：GitHub Actions 跑 `pytest tests/`，最少保住 distribution_pipeline 的 327 个用例。
8. **跑通批量分发**：用 `batch_rewrite.py --generate-distribution` 在 44 条全集上跑一遍，验证 Guizang 端到端。

### P2（一月内，影响架构整洁）

9. **合并/废弃 `process_feed.py`**：与 `process-subscriptions` Skill 整合到一处入口。
10. **删除 `src/app/` `src/components/` 空目录**。
11. **删除重复封面文件**。
12. **同步或删除 AGENTS.md**。
13. **修复 `content.js` field alias 冲突**：在 `rewritten: ['正文', '摘要', '内容']` 上加优先级。
14. **添加平台/频道过滤按钮**：前端体验补全。

### P3（远期，看需求）

15. **Guizang 残留 TODO**：WeChat Swiss、360px thumbnail 像素 QA、真实 Mapbox/OSM。
16. **拆 `generate_cover.py`**：1008 行单文件按风格拆分（如果风格持续扩张）。
17. **结构化日志与错误上报**：从 print/logging 收敛到统一框架。

---

## 八、总结

### 8.1 项目成熟度评估

| 模块 | 成熟度 | 说明 |
|---|---|---|
| 内容采集 + AI 改写 | ⭐⭐⭐⭐ | 6 个核心脚本稳定，Skill 编排清晰 |
| 飞书多维表格 | ⭐⭐⭐⭐ | API 封装完整，凭据分离干净 |
| Vercel 前端展示 | ⭐⭐⭐⭐ | 功能实现扎实，但数据同步滞后 |
| 分发素材流水线（基础后端） | ⭐⭐⭐ | xhs/wechat 基础渲染跑通 |
| 分发素材流水线（Guizang 后端） | ⭐⭐⭐½ | 核心 recipe 落地，残留 TODO 与视觉回退风险 |
| 自动化运营闭环 | ⭐⭐ | 仅手工触发，未形成定时/触发器 |
| CI / 可观测性 | ⭐ | 完全缺失 |

### 8.2 一句话总结

> Chora 处在"采集+改写核心已生产可用 + 前端展示扎实 + 第二代运营素材生成器基本可用"的状态；下一步关键动作是**同步前端数据、补 CI、跑通批量分发链路**，再逐步清理仓库冗余与历史遗物。

### 8.3 风险提示

- **没有 CI**：任何对 `distribution_pipeline/` 的改动都缺少回归保护，最近一次 327 passed 距今近一个月。
- **数据不同步**：前端 fallback 路径会让用户看到 9 条老内容，是当前最隐蔽的线上 bug。
- **Guizang 视觉回退**：根据 `findings.md` 复盘，"validator 通过 ≠ 视觉通过，必须目检关键 PNG"——目前仍依赖人工抽检。

---

## 附录 A：项目目录速查

```
Chora/
├── CLAUDE.md                       Claude Code 工作指南（最新）
├── AGENTS.md                       Codex 工作指南（滞后）
├── README.md                       7 字节（占位）
├── progress.md                     最近会话日志（2026-06-18）
├── task_plan.md                    P0.1-P2.5 全部 complete
├── findings.md                     经验教训文档
├── config/                         配置（yaml + prompt + 部署指南）
├── skills/                         3 个 Skill（content-feed-summarizer + 2 个薄入口）
├── content_archive/                43 个日期目录（最早 2021-09-06）
├── distribution/                   1 个发布包（2026-06-21）
├── distribution_pipeline/          第二代分发素材流水线（39 个测试）
├── docs/                           PRD + 分发文档 + Guizang 文档 + 2 个 plan
├── frontend/                       Vercel 静态站点（index + api + data + covers）
├── styles/                         23 个风格 markdown（postcard-sketch/vintage/chora-style/...）
├── tests/                          41 个测试（39 distribution + 2 根级）
├── utils/                          content_validator / word_count / archive_cleanup
├── node_modules/ + venv/ + .ms-playwright/  依赖与浏览器
├── 19 个 Python 脚本               5,382 行
└── 6 个根级 Markdown 文档          设计/调试/历史参考
```

## 附录 B：核心脚本调用速查

```
process-url <URL>            → process_video.py | process_podcast.py → feishu_service.py sync
process-subscriptions        → fetch_feed.py → [process_video.py | process_podcast.py] × N
                                 → utils/content_validator.py --fix → feishu_service.py sync
content-feed-summarizer      → batch_rewrite.py [--generate-distribution]
                                 → generate_cover.py --regenerate-all
手动：
  export_to_json.py          → content_export.json
  sync_covers.py             → frontend/public/covers/ + 写回 cover_path
  generate_frontend_data.py  → frontend/public/data/{content,summary}.json
  distribution_pipeline/generate_distribution.py → distribution/{package}/
```