---
name: process-subscriptions
description: 批量处理订阅源中的所有新内容，支持 YouTube 频道和小宇宙播客
---

# /process-subscriptions 工作流

扫描 `config/sources.yaml` 中的所有订阅源，识别新内容并批量处理。

## 使用方式

```
/process-subscriptions
```

## 执行步骤

### 步骤 0: 前置检查

验证配置文件存在且 API 密钥已配置。

### 步骤 1: 扫描订阅源

执行 `fetch_feed.py` 获取最新内容列表。

### 步骤 2: 生成待处理清单 (需要用户确认)

扫描完成后，**必须列出待处理清单**并请求用户确认：

```
📋 待处理内容清单:

YouTube:
1. [频道名] 视频标题 (发布日期) - 时长
2. ...

小宇宙:
1. [播客名] 节目标题 (发布日期) - 时长
2. ...

共 X 条新内容，是否开始处理？
```

**等待用户确认后再继续。**

### 步骤 3: 批量处理 (用户确认后执行)

对于每个待处理项目：

**YouTube 视频:**
```bash
python3 process_video.py "<VIDEO_URL>"
```

**小宇宙播客:**
```bash
python3 process_podcast.py "<EPISODE_URL>"
```

每个项目处理流程：
1. 获取元数据（标题、频道、日期）
2. 创建归档目录
3. 下载封面 / 生成封面
4. 获取字幕 / 转录音频
5. **AI 深度改写**（包含完整性验证 ⚠️）
6. 更新 metadata.md 嘉宾/金句

### 步骤 4: 完整性检查

批量处理完成后，执行完整性检查：
```bash
python3 utils/content_validator.py --fix
```

这会自动修复任何缺失的 `rewritten.md`。

### 步骤 5: 同步至飞书

确认所有内容完整后，同步至飞书多维表格：
```bash
python3 feishu_service.py sync
```

## 过滤规则

| 规则 | 说明 |
|------|------|
| 关键词过滤 | 仅处理标题包含 `include_keywords` 的内容 |
| ID 去重 | 检查 `config/state.yaml` 中的 `processed_ids` |
| 文件夹去重 | 检查 `content_archive/` 是否已存在对应文件夹 |
| 时间范围 | 仅处理 `date_range_days` 天内的新内容 |
| 时长过滤 | 仅处理时长超过 `min_duration_minutes` 的内容 |

## 完整性保证

- **AI 改写验证**: 每个项目完成后检查 `rewritten.md` 是否成功生成
- **自动修复**: 批量处理后运行完整性检查，自动重试失败项
- **分批处理**: 大文件 (>40KB) 单独排队，避免超时

## 注意事项

- 批量模式**必须确认**后才开始处理
- 每个项目处理完成后自动继续下一个
- 处理过程中遇到错误会记录并继续，不会中断整体流程