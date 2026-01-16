---
description: 为所有缺少封面的小宇宙播客批量生成封面图
---

# /regenerate-covers 工作流

扫描 `content_archive/` 目录，为所有缺少封面的小宇宙播客生成封面图。

## 使用方式

```
/regenerate-covers
```

## 执行步骤

### 1. 执行批量封面生成
// turbo
```bash
cd /Users/Avis/Vibe_Coding/Chora && python3 generate_cover.py --regenerate-all
```

### 2. 封面风格

生成的封面将使用**汇文明朝体 (Huiwen Mincho)** 风格:
- 字体类别：繁體明體 / 宋體
- 视觉风格：復古、懷舊、木版印刷風格
- 细节特征：微損、墨暈感
- 笔画特征：橫細豎粗對比明顯、Sharp serifs
- 整体气质：儒雅書卷氣

### 3. 输出

脚本会自动:
1. 扫描所有 `xiaoyuzhou_*` 目录
2. 跳过已有封面的目录
3. 为缺失封面的目录生成 `cover.png`

## 注意事项

- 此命令**无需确认**，直接执行
- 每个封面生成约需 10-30 秒
- 如遇 API 错误，脚本会记录失败并继续处理下一个
