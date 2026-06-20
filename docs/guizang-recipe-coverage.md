# Guizang Skill 接入覆盖表

本文记录 Chora 当前 `distribution_pipeline` 对 `guizang-social-card-skill` 的接入状态。这里的“完整落地”不只指 recipe 数量，也包括平台规格、内容规划、图片策略、主题系统、渲染流程和 QA。

## 结论

当前已接入核心 Editorial 小红书流程、Swiss S01-S13 专属 renderer、Category cookbook 一期、图上叠字静态 QA、Swiss 数值抽取一期、`copy_slots` 文案分配层、重复文案/内部 scaffold/proxy label 静态 QA，以及 Swiss 尾卡双组 CTA，可稳定生成 3:4 卡组；但还不是完整 Guizang Skill。

- Editorial Magazine x E-ink：16 / 16 个 recipe 已有 renderer；其中 M01/M03/M04/M07/M08/M09/M10/M11/M13/M14 已稳定参与自动规划，M02/M05/M06/M12/M15/M16 已补 renderer，planner 采用保守路由。
- Swiss International：S01-S13 已有专属 renderer（新增 S13 Map · Route）；planner 已能按图片、对比、风险、流程、清单、排名、数据、地理/迁移等信号路由；无 `subject_map` 的真实证据图会进入非叠字 evidence panel，但不再仅因“有图”强制派到 S04。
- 主题 token：Editorial 6 套、Swiss 4 套已可解析。
- 小红书 3:4：已落地核心链路。
- 微信公众号 21:9 + 1:1 封面对：已落地 Editorial 与 Swiss 两种模式的 cover pair，输出 21:9、1:1、pair preview 三个画板。
- Category cookbook：已接识别、scope notes、deck sequence 和保守 recipe 偏置；支持 旅行、职场、游戏、影视、美食、彩妆、健身、家居、穿搭、情感、推荐。
- Skill 级规则：已沉淀到 `docs/guizang-workflow-rules.md`，其中图上叠字、category 误触发、Swiss proxy metric 已转成自动 QA / 回归测试。

## Skill 模块覆盖

| Guizang 模块 | 当前状态 | Chora 现状 | 后续要求 |
|---|---|---|---|
| `platform-specs.md` | 基本落地 | 小红书 1080x1440、WeChat 2100x900 / 1080x1080 / pair preview、命名、PNG 导出已落地 | 后续补更多平台规格与批量 QA |
| `content-planning.md` | 部分落地 | 已有封面、洞察、哲思、closing 规划 | 补 category-aware page roles；长文/短文合并策略继续机器化 |
| `layout-recipes.md` | 基本落地 | Editorial 16/16 renderer 已接入；Swiss S01-S13 专属 renderer 已接入（含新增 S13 Map · Route）；category-aware sequence 已一期接入 | 强化 M06/M12、多截图、多地图等复杂资产条件 |
| `style-system.md` | 部分落地 | Editorial 背景、字体、主题已接入；Swiss 已使用 template 原生组件与轻量 mat | 增加 Swiss identity 自动检查；防止 generic template |
| `theme-presets.md` | 基本落地 | 6 套 Editorial、4 套 Swiss 可解析；auto theme 已有内容画像 | 增加更细 profile routing，避免所有文章长一样 |
| `components.md` | 部分落地 | 字体、frame-img、issue-strip、ledger/marginalia、Swiss card-fill、device-browser、image-hero、kpi、h-bar、stacked-ledger、matrix、map route 使用中 | 补更细 screenshot treatment 与真实地图 API 可选集成 |
| `background-systems.md` | 部分落地 | Editorial WebGL + grain + paper-wash 已接入 | 做 deterministic background QA；控制深色主题可读性 |
| `portrait-fill.md` | 部分落地 | 已修短文本空白、closing 重叠、M03 误用 | 自动化 4-band density check |
| `image-overlay.md` | 部分落地 | M16/S08 自动路由需 subject map；HTML 写入 subject map 与 thumbnail policy；静态 QA 检查 R8/R9/R10 | 后续补真实 360px thumbnail 像素检查、localized tint 自动决策与更多 subject-map 来源 |
| `screenshot-treatment.md` | 部分落地 | Swiss S04 已可把证据图放入 browser mock / evidence panel，使用 `object-fit: contain`；仍未有专属多截图语义 renderer | 补 M06 多截图墙、S08 subject-safe screenshot、真实 thumbnail QA |
| `map-component.md` | 已部分落地 | 新增 S13 Map · Route：基于文本地理/跨境/迁移关键词生成抽象路线卡片，使用 CSS 节点与连线，不依赖外部地图 API token | 旅行/空间内容可接入真实 Mapbox/OSM/static schematic |
| `title-shortener.md` | 部分落地 | WeChat 1:1 已用独立短标题，21:9 使用近完整单行标题 | 把短标题抽取从规则特例升级为通用语义压缩 |
| `category-cookbook.md` | 部分落地 | 11 类小红书 category 已有识别、scope notes、deck sequence 与 recipe hints；单泛词误触发已有回归测试 | 增强用户显式类别输入与用户侧 scope pushback |
| `production-workflow.md` | 部分落地 | 单文件多画板、Playwright PNG、360px 缩略图检查、SOURCES、WeChat 同 HTML 预览、静态 Guizang QA 已接入 | 补 render wait 与自动 thumbnail readability 评分 |
| `qa-checklist.md` | 部分落地 | 单元测试、validator、artifact contract、尺寸检查、R8/R10/R11/R12/R14 静态 QA 已有；浏览器 validator 继续负责 R5 密度 | 自动化 thumbnail 像素检查、subject safety 目检辅助、style identity |

## Editorial Recipe

| Recipe | Guizang 名称 | 当前状态 | Chora 用途 |
|---|---|---|---|
| M01 | Cover: Magazine Issue Cover | 已接入 | 小红书封面 |
| M02 | Field Note Photo | renderer 已接入，planner 待 category router | 可用于照片笔记页 |
| M03 | Editorial Essay Split | 已接入 | 中长正文页 |
| M04 | Pull Quote / Thesis | 已接入 | 大观点 / 引语页 |
| M05 | Checklist / Buying Guide | renderer 已接入，planner 已按清单信号保守路由 | 清单型内容 |
| M06 | Evidence Wall | renderer 已接入，planner 待多图资产 | 多图 / 多截图证据墙 |
| M07 | Closing Note | 已接入 | 收尾卡 |
| M08 | Tall Ledger | 已接入 | 多条 ledger |
| M09 | Atmospheric Thesis | 已接入 | 短观点氛围页 |
| M10 | Evidence Feature | 已接入 | 单图证据页 |
| M11 | Marginalia Essay | 已接入 | 短文 + 旁注页 |
| M12 | Section Divider | renderer 已接入，planner 待长卡组节奏策略 | 章节分隔页 |
| M13 | Hero Question | 已接入 | 哲思结语 |
| M14 | Vertical Pipeline | 已接入 | 结构 / 流程页 |
| M15 | Before / After | renderer 已接入，planner 已按标题对比信号保守路由 | 对比页 |
| M16 | Image-Led Cover | renderer 已接入，需 subject map 才启用 | 全图封面 |

Editorial 缺口优先级：

1. M02 Field Note Photo：renderer 已有；category router 已可在旅行有图时偏置；后续增强图片语义判定。
2. M05 Checklist / Buying Guide：renderer 与保守路由已接；后续增强行动指南识别。
3. M06 Evidence Wall：renderer 已有；下一步支持多图 / 多截图资产。
4. M15 Before / After：renderer 与保守路由已接；后续增强 before/after 内容抽取。
5. M12 Section Divider：renderer 已有；下一步接长卡组节奏策略。
6. M16 Image-Led Cover：renderer 已有；必须接 image-overlay subject safety 后才可自动启用。

## Swiss Recipe

| Recipe | Guizang 名称 | 当前状态 |
|---|---|---|
| S01 | Accent Cover | renderer 已接入 |
| S02 | Two Signals / Comparison | renderer 已接入，按对比信号路由 |
| S03 | Data Layer / File Card | renderer 已接入 |
| S04 | Interface / Browser Mock | renderer 已接入；只按界面/证据语义使用，不再由普通 evidence 图片强制触发 |
| S05 | Trap / Warning Rows | renderer 已接入，按风险/误区信号路由 |
| S06 | Pipeline / Architecture | renderer 已接入，按流程/系统信号路由；需 3 个以上流程/枚举节点 |
| S07 | Takeaway Ledger | renderer 已接入，用于收尾/结论 |
| S08 | Image Hero | renderer 已接入，有图优先路由 |
| S09 | KPI Tower | renderer 已接入，按指标/成本/增长信号路由；需至少 2 个真实数字 |
| S10 | H-Bar Chart | renderer 已接入，按排名/多点信号路由 |
| S11 | Stacked Ledger | renderer 已接入，按清单信号路由；已补底部 stat，短内容可用来替代 S12 |
| S12 | Matrix + Hero Stat | renderer 已接入，按多能力/多概念信号路由；短内容避免使用 |
| S13 | Map · Route | renderer 已接入，按地理/跨境/迁移信号路由；使用 CSS 节点与连线，不依赖外部地图 API token |

Swiss 结论：

- Swiss 已从“通用占位”升级为 S01-S13 专属 renderer。
- `tests/fixtures/.../Token经济学` 的 Swiss 小红书真实导出需要同时满足 validator 与关键 PNG 目检；此前 validator 通过仍暴露过假 SVG、重心失衡和标题裁切问题，后续不能仅凭机器 pass 交付。
- 后续重点不再是 renderer 数量，而是 screenshot、多图语义、自动 thumbnail readability 评分和更强数值抽取。

## 已知设计债

- 短文本页不能默认落到 M03，否则在 3:4 画布上容易出现大片空白。
- 深色主题下，背景纹理会增强氛围，但也会抢小字号正文注意力；短正文更适合 M09/M11/M10。
- 图片 evidence 当前默认 4 张；Swiss 已会消费这些图作为非叠字证据区，后续仍需按内容语义优先级选择，而不是固定页码。
- `image_assets=plan` 只能写搜索计划和复制本地素材，不得生成 CSS/SVG 概念假图进入 `selected_assets`。
- Swiss 模板已有 S01-S13 专属 renderer；Swiss closing 固定走 S07 Takeaway Ledger，保留 Chora Archive + Rhizomata 双组 CTA；数据型 recipe 已先抽真实数字，S09 至少需要 2 个真实数字，无真数值时标记 proxy，且 R14 阻断 `P01/P02` 内部占位符外泄；后续需增强中文数字/复杂单位抽取。
- Swiss recipe 已接 `copy_slots`，短正文不再靠重复首句填充版面；R11/R12 会阻断单卡可见文案重复和 `注记/脉络/张力` 等内部标签泄露。
- Swiss 尾卡 CTA 已改为两组：`CHORA ARCHIVE + 图标 + WWW.CHORA.AVISIONARY.TOP`，以及 `二维码 + WECHAT / RHIZOMATA`。
- WeChat 1:1 不能从 21:9 盲裁，必须按短标题重新构图；21:9 标题需控制为单行或近单行，避免宽封面校验告警。
- full-bleed 图上叠字必须做 subject safety；S08/M16 已有 subject-map gate，静态 QA 已检查 subject map、thumbnail policy 和禁用全画布黑遮罩。
- category cookbook 已接识别、scope notes 和 deck sequence，但还没有把 scope pushback 完整显式展示给用户。

## 下一步建议

1. 把 `docs/guizang-workflow-rules.md` 中的规则继续转成测试和 validator。
2. 强化 Editorial planner：M06/M12 需要多图资产、截图资产和长卡组节奏后再自动启用。
3. 把 category cookbook 的 scope pushback 写入用户侧提示或 manifest review。
4. 把 thumbnail readability 从静态 policy 检查升级为真实 360px 缩略图 QA（已生成缩略图，待接入自动可读性评分）。
5. 为 Swiss 增强中文数字、货币、时间跨度和比例抽取，进一步减少 proxy metric。
