---
name: process-subscriptions
description: 批量处理订阅源中的所有新内容
---

# /process-subscriptions 工作流

扫描 `config/sources.yaml` 中的所有订阅源，识别新内容并批量处理。

## 使用方式

```
/process-subscriptions
```

## 执行步骤

### 0. 前置检查：配置文件验证
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && test -f config/sources.yaml && echo "✅ 配置文件存在" || (echo "❌ 配置文件不存在，正在从示例复制..." && cp config/sources.example.yaml config/sources.yaml && echo "⚠️ 请编辑 config/sources.yaml 填入 API 密钥")
```

### 1. 验证 API 密钥
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 -c "
import yaml
with open('config/sources.yaml', 'r') as f:
    config = yaml.safe_load(f)

api_keys = config.get('api_keys', {})
llm_key = api_keys.get('llm', {}).get('api_key', '')

if 'your_' in llm_key or not llm_key:
    print('❌ LLM API 密钥未配置或为占位符')
    print('请编辑 config/sources.yaml 填入有效的 API 密钥')
    exit(1)
else:
    print('✅ API 密钥已配置')
"
```

### 2. 扫描订阅源
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 fetch_feed.py
```

### 3. 生成待处理清单 (需要用户确认)

扫描完成后，**必须列出待处理清单**并请求用户确认:

```
📋 待处理内容清单:

YouTube:
1. [频道名] 视频标题 (发布日期)
2. ...

小宇宙:
1. [播客名] 节目标题 (发布日期)
2. ...

共 X 条新内容，是否开始处理？
```

**等待用户确认后再继续。**

### 4. 批量处理 (用户确认后执行)

对于每个待处理项目:

**YouTube 视频:**
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 process_video.py "<VIDEO_URL>"
```

**小宇宙播客:**
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 process_podcast.py "<EPISODE_URL>"
```

### 5. 更新状态（无需操作）

`process_video.py` 和 `process_podcast.py` 内部在每次成功处理后会自动将 ID 追加到 `config/state.yaml` 的 `processed_ids` 列表中。

> **历史说明**：早期版本曾通过 `python3 process_feed.py --update-state` 单独更新状态，
> 但 `process_feed.py` 自 2026-07-11 起已废弃（与 `/process-subscriptions` Skill 功能完全重叠，
> 且该命令从未实现 —— `--update-state` 参数根本不存在，文件本身还存在 Python 3.10+
> 语法依赖）。状态更新已下沉到 `process_video.py` / `process_podcast.py` 内部，无需额外步骤。

如果你想确认状态已正确写入，可以查看：
```bash
cat config/state.yaml
```

### 6. 同步至飞书多维表格

处理并更新状态完成后，将最新数据导出并同步至飞书，以便在前端展示:
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 export_to_json.py --all && python3 feishu_service.py sync
```

## 过滤规则

- **关键词过滤**: 仅处理标题包含 `include_keywords` 的内容
- **ID 去重**: 检查 `config/state.yaml` 中的 `processed_ids`
- **文件夹去重**: 检查 `content_archive/` 是否已存在对应文件夹
- **时间范围**: 仅处理 `date_range_days` 天内的新内容
- **时长过滤**: 仅处理时长超过 `min_duration_minutes` 的内容

## 配置示例 (config/sources.yaml)

```yaml
settings:
  min_duration_minutes: 30
  date_range_days: 7

subscriptions:
  youtube:
    - channel_id: "UCxxxxxxx"
      name: "频道名称"
  xiaoyuzhou:
    - podcast_id: "5exxxxxxx"
      name: "播客名称"
      include_keywords: ["关键词1", "关键词2"]
```

## 注意事项

- 批量模式**必须确认**后才开始处理
- 每个项目处理完成后自动继续下一个
- 处理过程中遇到错误会记录并继续，不会中断整体流程
