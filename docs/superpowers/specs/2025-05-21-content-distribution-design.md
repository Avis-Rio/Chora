# Chora 内容分发功能设计规格

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**目标**: 为 Chora 项目添加自动化的内容分发能力，将处理完成的订阅内容自动生成为小红书卡片和微信公众号 Markdown，实现多平台内容复用和流量回流。

**架构**: 扩展现有 `content-feed-summarizer` Skill，新增分发步骤，通过配置文件控制分发行为。调用牛马AI内置的 `baoyu-xhs-images` 技能生成小红书卡片，生成公众号 Markdown 模板。

**技术栈**: Claude Code Skills, baoyu-xhs-images, YAML 配置, Markdown 模板

---

## 1. 功能概述

### 1.1 核心需求

| 需求项 | 描述 |
|--------|------|
| 目标平台 | 小红书、微信公众号 |
| 自动化程度 | 生成待发布内容，人工复制粘贴 |
| 触发方式 | 随内容处理自动触发 |
| 输出位置 | 与原文同目录 (`content_archive/{文章}/distribution/`) |
| 回流机制 | 链接到 Chora 网站 + 引导关注公众号 |

### 1.2 小红书卡片需求

| 项目 | 规格 |
|------|------|
| 内容类型 | 洞察卡片（核心洞察 5-10 条）+ 结尾卡片 |
| 视觉风格 | 根据内容自动适配，支持手动调整重选 |
| 布局 | dense（洞察卡片）、sparse（结尾卡片） |
| 图片数量 | 3-6 张（封面 + 洞察 + 结尾） |

### 1.3 微信公众号需求

| 项目 | 规格 |
|------|------|
| 内容类型 | 深度改写正文 + 书单推荐 |
| 格式 | Markdown，适配公众号编辑器 |
| 回流链接 | 文末添加「阅读原文」链接到 Chora |
| 引导关注 | 文末添加公众号关注引导 |

---

## 2. 架构设计

### 2.1 整体流程

```
内容处理流程（现有）
─────────────────────
Step 1-6: 获取 → 转录 → 摘要 → 保存 → 同步飞书

                    ↓ 新增

Step 7: 内容分发
─────────────────────
┌─────────────────────────────────────────────────────┐
│  读取 distribution 配置                              │
│  ├── xiaohongshu.enabled: true/false               │
│  ├── wechat.enabled: true/false                    │
│  └── backlinks 配置                                 │
├─────────────────────────────────────────────────────┤
│  小红书分发                                          │
│  ├── 提取核心洞察 + 哲思结语                         │
│  ├── 调用 baoyu-xhs-images 生成卡片                 │
│  ├── 风格自动适配（基于内容标签）                    │
│  └── 输出到 distribution/xhs/                       │
├─────────────────────────────────────────────────────┤
│  微信公众号分发                                      │
│  ├── 提取深度改写 + 书单推荐                         │
│  ├── 生成公众号 Markdown                            │
│  ├── 添加回流链接和引导关注                          │
│  └── 输出到 distribution/wechat/                    │
└─────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
content_archive/
└── {date}_{platform}_{channel}_{title}/
    ├── metadata.md           # 现有
    ├── transcript.md         # 现有
    ├── rewritten.md          # 现有
    ├── cover.jpg             # 现有
    └── distribution/         # 新增
        ├── xhs/
        │   ├── 01-cover.png
        │   ├── 02-insight.png
        │   ├── 03-insight.png
        │   ├── ...
        │   └── NN-ending.png
        └── wechat/
            └── article.md    # 公众号 Markdown
```

### 2.3 配置文件设计

在 `skills/content-feed-summarizer/` 下新增 `distribution-config.yaml`:

```yaml
# 内容分发配置
distribution:
  enabled: true  # 全局开关

  # 小红书配置
  xiaohongshu:
    enabled: true
    # 内容选择
    content:
      - insights    # 核心洞察
      - ending      # 哲思结语
    # 视觉风格：auto 表示根据内容自动适配
    style: auto
    # 布局配置
    layout:
      insights: dense
      ending: sparse
    # 图片数量限制
    max_images: 6

  # 微信公众号配置
  wechat:
    enabled: true
    # 内容选择
    content:
      - rewrite     # 深度改写
      - booklist    # 书单推荐
    # 回流配置
    backlinks:
      chora_site: true
      wechat_account: "Rhizomata"  # 公众号名称

  # 回流链接配置
  backlinks:
    chora_base_url: "https://chora.example.com"  # Chora 网站地址
    wechat_guide: |
      关注公众号「Rhizomata」，获取更多深度内容。
```

---

## 3. 组件设计

### 3.1 小红书卡片生成器

**职责**: 从 `rewritten.md` 提取内容，调用 `baoyu-xhs-images` 生成卡片图片。

**输入**:
- `rewritten.md` 中的核心洞察部分
- `rewritten.md` 中的哲思结语部分
- `metadata.md` 中的标题和金句

**输出**:
- 3-6 张小红书卡片图片（PNG 格式，3:4 竖版）

**风格自动适配规则**:

| 内容标签 | 推荐风格 | 布局 |
|----------|----------|------|
| Philosophy, Sociology, Psychology | notion | dense |
| Technology, Economics | minimal | dense |
| History, Anthropology | chalkboard | balanced |
| Art & Aesthetics | warm | balanced |
| 其他 | notion | dense |

**调用方式**:
```bash
/baoyu-xhs-images {content_path} --style {style} --layout {layout}
```

### 3.2 微信公众号 Markdown 生成器

**职责**: 从 `rewritten.md` 提取内容，生成适配公众号的 Markdown 文档。

**输入**:
- `rewritten.md` 中的深度改写部分
- `rewritten.md` 中的推荐书单部分
- `metadata.md` 中的标题

**输出**:
- `article.md`：公众号 Markdown 文档

**模板结构**:
```markdown
# {标题}

{深度改写正文}

---

## 📚 延伸阅读

{书单表格}

---

> 本文由 Chora 自动生成，原文链接：{Chora_URL}
>
> 关注公众号「Rhizomata」，获取更多深度内容。
```

### 3.3 分发步骤集成

在 `content-feed-summarizer/SKILL.md` 中新增 Step 7:

```markdown
### Step 7: 内容分发（可选）

**前置条件**: Step 6 完成，且 `distribution.enabled: true`

**流程**:
1. 读取 `distribution-config.yaml`
2. 检查各平台开关
3. 执行小红书分发（如启用）
4. 执行微信公众号分发（如启用）
5. 输出分发报告

**错误处理**:
- 分发失败不阻塞主流程
- 记录错误到 `distribution/errors.log`
- 继续处理下一个平台
```

---

## 4. 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                      content_archive/{article}/                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  metadata.md ──────┐                                            │
│  rewritten.md ─────┼──→ Step 7: 内容分发                        │
│  cover.jpg ────────┘         │                                  │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                          │
│                    │ 读取配置文件     │                          │
│                    │ distribution-    │                          │
│                    │ config.yaml      │                          │
│                    └────────┬────────┘                          │
│                             │                                   │
│              ┌──────────────┼──────────────┐                    │
│              ▼              ▼              ▼                    │
│         xiaohongshu     wechat      (disabled)                  │
│         enabled: true   enabled: true                            │
│              │              │                                   │
│              ▼              ▼                                   │
│    ┌──────────────┐  ┌──────────────┐                          │
│    │ 提取洞察+结语 │  │ 提取改写+书单 │                          │
│    └──────┬───────┘  └──────┬───────┘                          │
│           │                 │                                   │
│           ▼                 ▼                                   │
│    ┌──────────────┐  ┌──────────────┐                          │
│    │ baoyu-xhs-   │  │ 生成公众号   │                          │
│    │ images       │  │ Markdown     │                          │
│    └──────┬───────┘  └──────┬───────┘                          │
│           │                 │                                   │
│           ▼                 ▼                                   │
│    distribution/xhs/  distribution/wechat/                      │
│    ├── 01-cover.png   └── article.md                            │
│    ├── 02-insight.png                                           │
│    └── ...                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| 配置文件不存在 | 跳过分发，记录警告 |
| `baoyu-xhs-images` 调用失败 | 记录错误，继续公众号分发 |
| 内容提取失败（无洞察/无书单） | 使用默认占位内容 |
| 输出目录已存在 | 覆盖已有文件 |
| 图片生成超时 | 重试 1 次，失败则跳过 |

---

## 6. 测试策略

### 6.1 单元测试

- 配置文件解析测试
- 内容提取测试（洞察、书单、结语）
- 风格映射测试

### 6.2 集成测试

- 使用现有文章（如 `2026-01-26/youtube_硅谷101_CES_2026`）进行端到端测试
- 验证输出文件存在且格式正确
- 验证图片可正常打开

### 6.3 手动验证

- 小红书卡片：检查图片风格、布局、内容完整性
- 公众号 Markdown：复制到公众号编辑器预览效果

---

## 7. 实施计划

### Phase 1: 基础设施（1-2 天）
- 创建配置文件 `distribution-config.yaml`
- 修改 `SKILL.md` 添加 Step 7 框架

### Phase 2: 小红书分发（2-3 天）
- 实现内容提取逻辑
- 集成 `baoyu-xhs-images` 调用
- 实现风格自动适配

### Phase 3: 微信公众号分发（1-2 天）
- 实现 Markdown 模板生成
- 添加回流链接和引导关注

### Phase 4: 测试与优化（1 天）
- 端到端测试
- 修复问题
- 文档完善

---

## 8. 后续扩展

| 扩展方向 | 描述 |
|----------|------|
| 即刻分发 | 金句 + 封面发动态 |
| 自动发布 | 集成浏览器自动化，自动填充草稿箱 |
| 数据回流 | 各平台数据反馈到 Chora |
| A/B 测试 | 不同标题/封面效果对比 |
