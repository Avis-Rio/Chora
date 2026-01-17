# Chora 产品需求文档 (PRD)

## 文档信息
- **创建日期**: 2026-01-17
- **最后更新**: 2026-01-17
- **版本**: 1.0

---

## 变更记录

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
