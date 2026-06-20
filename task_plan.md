# Chora Guizang/XHS 优化计划

## 目标

按优先级完善 daily rewrite -> Guizang 生图 -> XHS 文案/tag 工作流；每完成一项同步文档，使项目进度描述与代码一致。

## 范围

- 自动分发后处理：`process_video.py`、`process_podcast.py`、`process_feed.py`、`batch_rewrite.py`
- Guizang 渲染：`distribution_pipeline/`
- XHS 文案/tag：`distribution_pipeline/renderers/xhs_copy.py`
- QA 与文档：`docs/distribution-pipeline.md`、`docs/guizang-recipe-coverage.md`、`docs/guizang-workflow-rules.md`

## 阶段

| 阶段 | 状态 | 内容 |
|---|---|---|
| P0.1 | complete | daily/rewrite 成功后自动生成 Guizang XHS 分发包，失败记录并继续 |
| P0.2 | complete | 调整图源默认策略，daily 静默流避免默认联网下载未核版权图片 |
| P0.3 | complete | Swiss 页面消费可用证据图，减少纯文字空页 |
| P1.1 | complete | 重写 XHS caption/tag 生成逻辑，降低模板味 |
| P1.2 | complete | 改善标题语义断行 |
| P1.3 | complete | 强化密度/占位/Proxy QA |
| P2.1 | complete | 同步文档、测试说明、项目进度 |
| P2.2 | complete | 验证真实 Token 夹具导出与 validator |
| P2.3 | complete | 修复 Token 导出视觉回退：禁用假 SVG、收紧 Swiss 配方门槛、重跑目检 |
| P2.4 | complete | Guizang 上游接入 P0：修复 PNG/QA 闭环、补 Node 依赖入口、同步接入文档 |
| P2.5 | complete | Guizang 后续优化：xhs-06/xhs-07 R5 密度（2 warn → 1 warn）、S13 Map · Route、WeChat Swiss 渲染、360px 缩略图检查 |

## 决策

- daily 默认只跑 `platform=xhs`、`renderer=guizang`、`guizang_mode=auto`。
- daily 图源默认使用 `plan`，只保留搜索计划与本地封面，不默认下载外部图片，也不生成 CSS/SVG 概念假图。
- 分发失败不阻塞内容归档主流程，写入 `distribution_errors.log`。
- 代码改动后，文档同批更新，避免现状描述落后。
- 2026-06-17 起，本轮仅处理 Guizang 上游接入链路；暂不修改 `process_video.py`、`process_podcast.py`、`process_feed.py` 或订阅采集流程。

## 错误记录

| 时间 | 错误 | 处理 |
|---|---|---|
| 2026-06-14 | `venv` 与系统 Python 均缺 `pytest` | 后续先补可运行测试策略或使用 `py_compile` + 真实导出验证 |
| 2026-06-14 | Codex 沙箱阻止 Playwright Chromium MachPort | 允许同一导出命令非沙箱运行，完成 PNG 与 validator 验收 |
| 2026-06-14 | validator 通过但人工目检发现版式失衡、假图入版、标题截断 | P2.3 改为必须先禁假图、收紧配方，再以关键 PNG 目检作为交付条件 |
| 2026-06-14 | 非沙箱 PNG 导出被 Codex 当前额度限制拒绝 | 已生成 HTML 包并通过静态 QA；P2.3 仍保持 in_progress，等待权限/额度恢复后重跑 PNG |
| 2026-06-17 | `render.cjs` 顶层 `require("playwright")` 使 `wkhtmltoimage` fallback 无法在缺 Playwright 时生效 | P2.4 优先修 render script，再补 Node 依赖入口并重跑 Token PNG |
