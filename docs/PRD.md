# Chora 产品需求文档 (PRD)

## 文档信息
- **创建日期**: 2026-01-17
- **最后更新**: 2026-05-25
- **版本**: 1.0

---

## 变更记录

### 2026-05-25 更新

#### 1. 项目架构与工作流调研

**调研范围**：
- 根目录 Python 处理脚本
- `.agent/workflows/` 工作流文档
- `frontend/` 前端与 Vercel API
- `feishu_service.py`、`export_to_json.py`、`generate_frontend_data.py`
- `content_archive/` 归档目录结构

**当前架构观察**：
- 项目以 Python 内容处理流水线为主，静态前端展示与飞书同步为辅
- 存在两类主要入口：
  - 批量订阅入口：`fetch_feed.py`
  - 单条内容入口：`process_video.py` / `process_podcast.py`
- 两类入口最终都会沉淀到 `content_archive/{日期}/{平台}_{频道}_{标题}/`
- 归档核心文件稳定为：`metadata.md`、`transcript.md`、`rewritten.md`、`cover.*`

**运行链路观察**：
1. 订阅扫描：`fetch_feed.py` 读取 `config/sources.yaml`，按平台扫描 YouTube / 小宇宙
2. 去重过滤：结合 `config/state.yaml` 与 `content_archive/` 目录做 ID 和文件夹去重
3. 单条处理：
   - YouTube：拉取元数据、下载封面、获取字幕，字幕缺失时降级到音频 + Whisper
   - 小宇宙：抓取页面 `__NEXT_DATA__`、提取音频 URL、下载音频、Groq Whisper 转录
4. AI 改写：`rewrite_service.py` 读取转录和 `config/rewrite-prompt.md`，调用 LLM 流式生成
5. 结构化导出：`export_to_json.py` 从归档目录抽取结构化字段
6. 飞书同步：`feishu_service.py` 将内容同步到多维表格，并上传封面附件
7. 前端消费：
   - 生产环境优先读取 `frontend/api/content.js` 提供的飞书数据
   - 本地开发回退到静态 JSON 数据

**工作流文档观察**：
- `/process-subscriptions`：先扫描，再列待处理清单，需用户确认后批量执行
- `/process-url`：识别 URL 类型后直接执行单条处理
- `/sync-feishu`：先导出 JSON，再按“新增 / 不完整 / 完整跳过”策略同步飞书

**当前结论**：
- 已完成对项目目录、入口脚本、数据流、同步层和前端消费层的结构化调研
- 当前处于“等待新增工作流需求”状态，尚未进入方案设计与实现阶段

#### 2. 新增需求方向确认：双平台分发素材工作流

**用户目标**：
- 将现有 AI 改写交付文章，进一步作为微信公众号贴图与小红书卡片图文的分发基础
- 期望以每篇文章中的“核心洞见”为最小内容单元，生成不同风格样式的视觉卡片
- 希望建立可复用的双平台一体化素材生成方案，而非仅产出单次内容

**已确认范围**：
- 优先方向：双平台一体化
- 目标平台：
  - 微信公众号图文场景
  - 小红书多卡片图文场景

**现状观察**：
- 仓库已存在小红书分发雏形：
  - `distribution/xhs/xhs_source.md`
  - `distribution/xhs/xhs_cards.md`
  - `distribution/xhs/images/card_p1.html` ~ `card_p4.html`
- 仓库已存在多套视觉风格定义：`styles/` 目录
- 但目前尚未形成“改写文章 -> 核心洞见拆解 -> 卡片脚本 -> 平台素材输出”的标准化工作流
- 也尚未看到面向微信公众号配图的独立生成链路

**当前状态**：
- 已完成需求方向确认与现有基础摸查
- 下一步需要进入“构思”或“计划”阶段，才能正式输出详细评估与设计方案

### 2026-01-17 更新

#### 1. 小宇宙嘉宾信息提取优化

**问题背景**：
AI 从音频转录中推断嘉宾信息不准确。例如，将"刘佳林"错误识别为"刘佳"，简介信息也与实际不符。

**根本原因**：
- 音频转录文本中嘉宾信息可能不清晰或缺失
- 依赖 AI 从转录推断准确率低

**解决方案**：
直接从小宇宙页面的 `description` 字段提取"本期话题成员"列表，而非依赖 AI 推断。

**技术实现**：

##### 1.1 新增 `extract_guests_from_description()` 函数

**文件**: `process_podcast.py`

```python
def extract_guests_from_description(description):
    """从小宇宙节目描述中提取嘉宾信息。
    
    支持格式：
    - "- 本期话题成员 -\n嘉宾1，简介\n嘉宾2，简介"
    - "嘉宾：xxx"
    - "本期嘉宾：xxx"
    
    返回: 提取的嘉宾信息字符串（多行）
    """
```

**匹配模式**（优先级从高到低）：
1. `[-–—]\s*本期话题成员\s*[-–—]\s*\n(.*?)(?=\n[-–—]|\n\n|\Z)`
2. `[-–—]\s*嘉宾\s*[-–—]\s*\n(.*?)(?=\n[-–—]|\n\n|\Z)`
3. `本期嘉宾[：:]\s*(.*?)(?=\n\n|\Z)`
4. `嘉宾[：:]\s*(.*?)(?=\n\n|\Z)`

**过滤逻辑**：
- 跳过时间轴格式（如 "01:58 xxx"）
- 跳过短分隔符（如单独的 "-"）

##### 1.2 修改 `get_episode_metadata()` 函数

**文件**: `process_podcast.py`

从 `__NEXT_DATA__` JSON 中提取 episode 的 `description` 字段，并调用 `extract_guests_from_description()` 解析嘉宾。

**返回值新增字段**：
```python
{
    ...
    'guests': guests,       # 提取的嘉宾信息
    'description': description  # 原始描述（供 AI 参考）
}
```

##### 1.3 修改 `process_podcast()` 函数

**文件**: `process_podcast.py`

保存 `metadata.md` 时，如果提取到嘉宾信息，直接写入：

```markdown
## 嘉宾
刘佳林，上海交通大学人文学院中文系教授、《纳博科夫传》译者
郑诗亮，《上海书评》执行主编
```

##### 1.4 修改 `rewrite_content()` 函数

**文件**: `rewrite_service.py`

**优先级逻辑**：
```python
# 优先使用从页面提取的嘉宾，其次使用 AI 生成的
final_guests = original_fields['guests'] or ai_guests
```

---

#### 2. 订阅源扫描优化

**问题背景**：
`/process-subscriptions` 工作流执行时存在多个问题。

**修复内容**：

##### 2.1 配置文件验证

**文件**: `fetch_feed.py`, `rewrite_service.py`

- 检查 `config/sources.yaml` 是否存在
- 检查 API 密钥是否为占位符

```python
def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"错误: 找不到配置文件 {CONFIG_PATH}")
        return None
    
    # 检查 API 密钥是否为占位符
    llm_key = api_keys.get('llm', {}).get('api_key', '')
    if 'your_' in llm_key or not llm_key:
        print("⚠️ 警告: LLM API 密钥未配置")
```

##### 2.2 早期退出逻辑

**文件**: `fetch_feed.py` - `_fetch_via_ytdlp()`

连续 2 个视频超出日期范围后停止扫描，减少无效日志：

```python
consecutive_old = 0
max_consecutive_old = 2

if video_date < cutoff_date:
    consecutive_old += 1
    if consecutive_old >= max_consecutive_old:
        break
else:
    consecutive_old = 0  # 重置计数器
```

##### 2.3 减少获取数量

**文件**: `fetch_feed.py`

`--playlist-items` 从 `1-15` 改为 `1-8`，加快扫描速度。

##### 2.4 时长获取增强

**文件**: `fetch_feed.py` - `_get_video_duration()`

添加备选方案：
1. 首先尝试 `yt-dlp --print duration`
2. 失败则使用 `yt-dlp -J` 获取完整 JSON

##### 2.5 英文转录自动翻译

**文件**: `rewrite_service.py`

检测转录语言，如果是英文则在 prompt 中添加翻译指令：

```python
def detect_language(text):
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    ratio = ascii_chars / len(text)
    return 'english' if ratio > 0.8 else 'chinese'

if lang == 'english':
    translation_instruction = "\n\n**重要提示：原文是英文，请在改写时将内容翻译为流畅的中文。**\n"
```

---

#### 3. 飞书同步优化

**问题背景**：
新同步到飞书的记录默认"是否发布"为未勾选状态。

**修复内容**：

**文件**: `feishu_service.py` - `_map_to_fields()`

```python
# Set default publish status to True (checked)
all_fields["是否发布"] = True
```

---

#### 4. 前端内容发布控制

**实现内容**：

**文件**: `frontend/api/content.js`

- 通过飞书表格的"是否发布"复选框控制文章可见性
- 仅返回 `是否发布 === true` 的记录
- CDN 缓存时间：30 秒 (`s-maxage=30, stale-while-revalidate=15`)

---

## 数据流图

```
小宇宙页面
    ↓ (curl 抓取)
__NEXT_DATA__ JSON
    ↓ (解析 episode.description)
extract_guests_from_description()
    ↓
metadata.md (嘉宾信息)
    ↓
rewrite_service.py (优先保留)
    ↓
飞书多维表格
    ↓
前端展示
```

---

## 测试用例

### 嘉宾提取测试

**输入**:
```
本期节目是「JUSTREAD!夏日播客读书月」的直播录音...
- 本期话题成员 -
刘佳林，上海交通大学人文学院中文系教授、《纳博科夫传》《陀思妥耶夫斯基：受难的年代，1850-1859》译者
郑诗亮，《上海书评》执行主编（微博@PomBom，豆瓣ID：PooomBooom）
- 时间轴 -
01:58 陀思妥耶夫斯基笔下的人物往往是滔滔不绝
```

**期望输出**:
```
刘佳林，上海交通大学人文学院中文系教授、《纳博科夫传》《陀思妥耶夫斯基：受难的年代，1850-1859》译者
郑诗亮，《上海书评》执行主编（微博@PomBom，豆瓣ID：PooomBooom）
```

---

## 后续优化建议

1. **嘉宾格式标准化**：考虑解析嘉宾名字和简介为结构化数据
2. **更多页面信息提取**：时间轴、节目简介等
3. **缓存小宇宙页面**：减少重复抓取
4. **嘉宾数据库**：建立嘉宾信息库，支持跨节目关联

---

## Project Status Kanban

### Doing
- 2026-05-25：调研项目架构、运行逻辑与现有工作流，并确认新增需求方向为“双平台一体化分发素材工作流”

### Done
- 2026-05-25：完成对批量订阅处理、单 URL 处理、飞书同步、前端读取链路的现状梳理

### Blocked
- 暂无

---

## Executor Feedback or Request for Help

- 2026-05-25：已完成现状调研，当前未进行任何业务代码修改。新增需求已明确为：基于 AI 改写文章与核心洞见，设计面向微信公众号与小红书的双平台分发素材工作流。尚待用户明确切换至“构思”或“计划”模式。

---

## Lessons Learned

- 2026-05-25：该项目并非单一入口应用，而是“脚本工作流 + 归档目录 + 飞书表格 + 前端展示”组成的串联式流水线，后续变更需要先确认影响的是入口层、归档格式、同步层还是前端消费层。
- 2026-05-25：现有仓库已具备“小红书素材示例 + 多套视觉风格”基础，但缺少把文章内容资产化、模板化、跨平台化的中间抽象层；后续方案设计需优先处理这一层。
