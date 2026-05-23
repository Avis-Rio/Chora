---
name: distribute-content
description: "将已处理的内容分发到小红书和微信公众号。支持单篇文章或批量处理。"
license: MIT
---

# 内容分发器 (Content Distributor)

## 🚀 快速使用

```bash
# 分发单篇文章
/distribute-content content_archive/2026-01-26/youtube_硅谷101_xxx

# 分发最近 7 天的所有文章
/distribute-content --recent 7

# 分发指定日期的所有文章
/distribute-content --date 2026-01-26

# 只分发小红书
/distribute-content content_archive/xxx --platform xhs

# 只分发公众号
/distribute-content content_archive/xxx --platform wechat
```

## 📋 工作流

### 步骤 1：解析参数
- 识别目标：单篇文章 / 批量模式
- 识别平台：all / xhs / wechat

### 步骤 2：加载配置
- 读取 `skills/content-feed-summarizer/distribution-config.yaml`
- 确认各平台开关状态

### 步骤 3：执行分发

**单篇文章模式**：
1. 提取文章内容（metadata.md + rewritten.md）
2. 根据内容标签自动选择小红书风格
3. 生成小红书卡片内容文件 → 输出到 `distribution/xhs/`
4. 生成公众号 Markdown → 输出到 `distribution/wechat/article.md`
5. 显示生成提示

**批量模式**：
1. 扫描目标目录下的所有文章
2. 逐篇执行分发
3. 汇总报告

### 步骤 4：输出报告

```
分发完成！

文章: CES 2026：探展50个AI项目背后的泡沫、野心与非共识
├── 小红书 ✓
│   └── 内容已准备: distribution/xhs/xhs_content.md
│   └── 风格: minimal (基于标签 Technology, Economics)
│   └── 请使用 /baoyu-xhs-images 生成卡片
└── 公众号 ✓
    └── distribution/wechat/article.md
```

## 🎯 平台说明

| 平台 | 输出内容 | 文件位置 |
|------|----------|----------|
| **小红书** | 核心洞察 + 哲思结语的卡片内容 | `distribution/xhs/xhs_content.md` |
| **公众号** | 深度改写 + 书单 + 回流链接 | `distribution/wechat/article.md` |

## ⚠️ 注意事项

- 小红书卡片需要手动调用 `/baoyu-xhs-images` 生成图片
- 公众号 Markdown 可直接复制到公众号编辑器
- 分发失败不会阻塞，会继续处理其他文章
