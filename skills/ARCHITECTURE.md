# Chora Skills 编排架构

> 本文件定义三个 Skill 的职责矩阵、调用关系、共同遵守的契约。后续 Skill 调整必须先看这里。
>
> 上次更新：2026-07-12（实测暴露后修订：Python 版本要求 + base_url 智能识别 + FieldNameNotFound 防回归）

## 0. 运行时要求（**必读**）

| 要求 | 说明 |
|---|---|
| **Python ≥ 3.10** | `distribution_pipeline/*` 全包使用 PEP 604 union syntax（如 `Path \| None`），Python 3.9 在 import 阶段立即崩溃。所有 SKILL 命令已统一为 `python3.10 ...` |
| **macOS 默认 python3 = 3.9** | 实测 2026-07-12：macOS 系统默认 `python3` 仍指向 3.9，跑任何 SKILL 都会因 `distribution_pipeline.automation` import 失败而退出 |
| **CI 矩阵已验证** | 3.10 / 3.11 / 3.12 三个版本在 GitHub Actions 全绿（run #14+），实测证明 |
| **本地推荐** | `brew install python@3.11` → `python3.10` / `python3.11` / `python3.12` 任选一个 |

## 1. 三个 Skill 的职责矩阵

| Skill | 类型 | 输入 | 用户交互 | 输出 | 详细程度 |
|---|---|---|---|---|---|
| `content-feed-summarizer` | **协议 / 能力池** | 单 URL 或待处理清单 | 静默（Quiet Mode） | 归档 + 摘要 + 飞书同步 | **235 行主 SKILL**，定义完整 7 步工作流 |
| `process-url` | **薄入口** | 单个 URL（自动识别 YouTube / 小宇宙） | 无确认 | 调用 `process_video.py` 或 `process_podcast.py` | 只描述入口差异，不重复工作流 |
| `process-subscriptions` | **薄入口 + 扫描** | 配置订阅源 | **必须先列清单 + 用户确认** | `fetch_feed.py` 扫描 → 逐项处理 → 完整性修复 → 飞书同步 | 只描述入口差异 + 扫描步骤，不重复工作流 |

**核心原则**：**content-feed-summarizer 是工作流唯一权威定义**。两个薄入口 SKILL 不应复制工作流细节，只声明"调哪个脚本 + 此入口特有的规则"。

## 2. 调用关系图

```
                  ┌───────────────────────────────┐
                  │  content-feed-summarizer     │
                  │  完整工作流（步骤 0-7）        │
                  │  Quiet Mode + Log & Continue  │
                  └──────────────┬────────────────┘
                                 │ 权威定义，薄入口引用
              ┌──────────────────┴────────────────────┐
              │                                       │
       ┌──────▼─────────┐                    ┌─────────▼──────────┐
       │  process-url   │                    │ process-...        │
       │  (单 URL)      │                    │ subscriptions      │
       │                │                    │ (批量 + 必须确认)   │
       └────────────────┘                    └────────────────────┘
              │                                       │
       ┌──────┴──────┐                       ┌────────┼─────────┐
       ▼             ▼                       ▼        ▼         ▼
process_video.py process_podcast.py   fetch_feed.py  process_   feishu_service
                                              video.py  podcast.py  .py sync
                                              +process_
                                              podcast.py
                                                  │
                                                  ▼
                                          utils/content_validator.py --fix
```

**关键观察**：
- 两个入口 SKILL **不互相调用**——它们都遵循 `content-feed-summarizer` 协议，平行存在。
- 三个 Skill **不重叠**——协议权威、入口契约、扫描触发各司其职。
- Python 脚本（`process_video.py` 等）**可绕过 SKILL 被直接调用**——用于 debug 或批量重写场景（如 `batch_rewrite.py`）。

## 3. 共同契约（所有 Skill 强制遵守）

### 3.1 Quiet Mode 协议

**一旦开始处理某项目，不允许中断或重新询问**。细节：
- URL 模式（用户提供 URL）：自动开始，**无需确认**
- 批量模式（订阅扫描）：**必须**先列待处理清单 + 用户确认
- 数据缺失：用 `"Unknown"` / `"N/A"` 兜底，不停下询问
- 失败重试：3 次，间隔 5 秒，仍失败则记录到 `processing_errors.log` 后继续

### 3.2 完整性验证

**每个项目处理完成后必须验证**：

| 阶段 | 验证内容 | 失败处理 |
|---|---|---|
| AI 改写 | `rewritten.md` > 100 字节且非空 | 内嵌重试 5 次 |
| 批处理收尾 | 调 `utils/content_validator.py --fix` | 自动补缺失的 `rewritten.md` |

### 3.3 错误处理：Log & Continue

任何失败**不应阻断主流程**。所有错误必须：
1. 记录到对应日志：`processing_errors.log` / `distribution_errors.log`
2. 继续处理下一个项目
3. 在最终汇报中汇总错误计数

### 3.4 飞书同步

处理完成后**自动**触发：
```bash
python3.10 feishu_service.py sync
```
若环境变量 `FEISHU_*` 未配置，则跳过（不报错）。

### 3.5 数据流向（**不**在 SKILL 控制内，由 Python 脚本管理）

```
content_archive/{date}/{folder}/
    ├── metadata.md         # SKILL 工作流产出
    ├── transcript.md       # SKILL 工作流产出
    ├── rewritten.md        # SKILL 工作流产出
    ├── cover.jpg/png       # SKILL 工作流产出
    └── audio.m4a           # 仅小宇宙

            ↓ export_to_json.py
            ↓
content_export.json (44 条)
            ↓ generate_frontend_data.py
            ↓
frontend/data/content.json + frontend/public/data/content.json
frontend/data/summary.json + frontend/public/data/summary.json
            ↓ feishu_service.py sync
            ↓
飞书多维表格（生产环境）
```

---

## 4. 入口 SKILL 的差异点（不再重复工作流）

### process-url vs process-subscriptions

| 差异 | process-url | process-subscriptions |
|---|---|---|
| **用户确认** | 无（URL 直接开始） | **必须**（扫描清单后确认） |
| **扫描步骤** | 无 | `fetch_feed.py` |
| **完整性自动修复** | 内嵌重试 5 次 | `utils/content_validator.py --fix` |
| **错误日志** | `processing_errors.log` | `processing_errors.log` |
| **飞书同步** | 步骤 5 触发 | 步骤 5 触发 |

共同点（**不写**在入口 SKILL 中）→ 引用 `content-feed-summarizer/SKILL.md`。

### process-url SKILL 应保持精简

预计体量：~50 行（不重复工作流，只声明）：
- URL 识别规则
- 调哪个 Python 脚本
- 单 URL 验证与飞书同步

### process-subscriptions SKILL 应保持精简

预计体量：~80 行（额外加扫描步骤）：
- 配置文件前置检查
- 调 `fetch_feed.py`
- 待处理清单 + 用户确认
- 批量调 `process_video.py` / `process_podcast.py`
- 完整性自动修复 + 飞书同步

---

## 5. Python 工具脚本矩阵

被 SKILL 实际调用的脚本（**核心**）：

| 脚本 | 入口 SKILL | 独立 CLI | 备注 |
|---|---|---|---|
| `process_video.py` | process-url / process-subscriptions | ✅ | 单 YouTube 视频 |
| `process_podcast.py` | process-url / process-subscriptions | ✅ | 单小宇宙播客 |
| `fetch_feed.py` | process-subscriptions | ✅ | 订阅源扫描 |
| `feishu_service.py` | 两个入口 SKILL 步骤 5 | ✅ | 飞书多维表格同步 |
| `utils/content_validator.py` | process-subscriptions 步骤 4 | ✅ | 完整性检查 |
| `batch_rewrite.py` | (无 SKILL) | ✅ | 批量补改写 |
| `generate_cover.py` | (隐式) | ✅ | 封面生成 |
| `export_to_json.py` | (无 SKILL) | ✅ | 数据归档→JSON |
| `generate_frontend_data.py` | (无 SKILL) | ✅ | 前端数据生成 |
| `sync_covers.py` | (无 SKILL) | ✅ | 部署前封面同步 |

辅助脚本（**核心服务模块**，被上面 import）：

| 脚本 | 职责 |
|---|---|
| `youtube_service.py` | YouTube 元数据 + 字幕 |
| `xiaoyuzhou_service.py` | 小宇宙元数据 + 嘉宾 |
| `rewrite_service.py` | LLM 流式改写 |
| `stock_cover_service.py` | Pexels / Unsplash 兜底 |
| `config_loader.py` | YAML + .env 加载 |
| `distribution_pipeline/automation.py` | 改写后自动分发到素材包 |

---

## 6. 已废弃/冗余清单（2026-07-11 起执行）

| 项目 | 类型 | 状态 | 原因 |
|---|---|---|---|
| `process_feed.py` | Python 脚本 | **已删除** | 与 process-subscriptions Skill 功能重叠，无 SKILL 调用方；且文件本身依赖 Python 3.10+ 语法、`.agent/workflows` 中误引用的 `--update-state` 命令从未存在 |
| `clean_tags.py` | Python 脚本 | **已删除** | 功能完全被 `normalize_tags.py` 覆盖 |
| `inspect_page.py` | Python 脚本 | **已删除** | 21 行一次性调试脚本 |
| `batch_process.py` | Python 脚本 | **已删除** | 写死 6 条 URL 的 ad-hoc 触发器 |
| `frontend/src/app/` | 前端目录 | **已删除** | 历史遗留空目录 |
| `frontend/src/components/` | 前端目录 | **已删除** | 历史遗留空目录 |
| `generate_cover.py`（monolith） | 模块 | **已完全拆分** | 原 1008 行 monolithic 全部拆为 `generate_cover/` 包 6 个子模块（_infra / palettes / style / title / image / pipeline）。所有 11 个公开 API 通过 `__init__.py` re-export 保留 `from generate_cover import X` 兼容；同时修复了 `regenerate_missing_covers` 函数定义缺失的 latent bug（CLI `--regenerate-all` 跑会 NameError） |

---

## 7. 修改指南

### 添加新内容源（如 B 站、Spotify）
1. 写解析脚本（参考 `youtube_service.py` / `xiaoyuzhou_service.py`）
2. 加 `process_<source>.py` 调度脚本（参考 `process_video.py`）
3. 在 `content-feed-summarizer/SKILL.md` 的"步骤 1：获取元数据"增加章节
4. 在两个入口 SKILL 的"调用 Python 脚本"步骤加一行
5. 若批量支持，更新 `fetch_feed.py`
6. 更新本文档"Python 工具脚本矩阵"表

### 修改 AI 摘要结构
1. 编辑 `config/rewrite-prompt.md`
2. 若结构变化（章节名变了），同步更新 `content-feed-summarizer/SKILL.md` 的"步骤 3"
3. 不需要修改入口 SKILL

### 调整飞书字段
1. 改 `feishu_service.py` 的 `FIELD_ALIASES`
2. 改 `feishu.yaml` 配置
3. 不需要修改 SKILL

---

## 8. 文档版本

| 版本 | 日期 | 主要变更 |
|---|---|---|
| 1.0 | 2026-07-11 | 初版，建立职责矩阵 + 契约 + 废弃清单 |
