---
name: generate-cover-baoyu
description: 使用全局安装的 Baoyu Cover Image Skill 为当前文档生成封面图
---

# /generate-cover-baoyu 工作流

此工作流调用全局安装的 `baoyu-cover-image` skill 来生成高质量封面图。

## 步骤

1. **加载 Skill 定义**
   读取全局 Skill 文件以获取最新逻辑：
   `cat /Users/Avis/.agents/skills/baoyu-cover-image/SKILL.md`

2. **准备上下文**
   - 确定目标内容文件（默认为当前打开的文件，或用户指定的文件）。
   - 确定输出目录（通常是内容文件所在目录）。

3. **执行 Skill 逻辑**
   严格遵循 `SKILL.md` 中的步骤：
   - **Step 1: Analyze Content**: 分析内容主题、核心信息、语气。
   - **Step 2: Confirm Options**: 询问用户偏好 (Type, Style, Aspect Ratio)。
     - 参考样式文件位于: `/Users/Avis/.agents/skills/baoyu-cover-image/references/styles/`
   - **Step 3: Create Prompt**: 生成提示词并保存到 `prompts/cover.md` (在输出目录中)。
   - **Step 4: Generate Image**: 使用 `generate_image` 工具生成图片。

## 依赖路径
- Skill Root: `/Users/Avis/.agents/skills/baoyu-cover-image`
- Styles: `/Users/Avis/.agents/skills/baoyu-cover-image/references/styles`
