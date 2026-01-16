---
description: 批量处理订阅源中的所有新内容，需要用户确认后执行
---

# /process-subscriptions 工作流

扫描 `config/sources.yaml` 中的所有订阅源，识别新内容并批量处理。

## 使用方式

```
/process-subscriptions
```

## 执行步骤

### 1. 读取配置
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && cat config/sources.yaml
```

### 2. 扫描订阅源

**YouTube 频道:**
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 fetch_feed.py --platform youtube
```

**小宇宙播客:**
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 fetch_feed.py --platform xiaoyuzhou
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

### 5. 更新状态

处理完成后，将已处理的 ID 写入 `config/state.yaml`:
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 process_feed.py --update-state
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
