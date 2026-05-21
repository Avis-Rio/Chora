"""
小红书卡片生成器

调用 baoyu-xhs-images 技能生成小红书卡片图片。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from config_loader import DistributionConfig, get_style_for_tags
from content_extractor import ExtractedContent


@dataclass
class XHSOutput:
    """小红书生成输出"""
    success: bool
    image_paths: list
    error_message: str = ""


class XHSGenerator:
    """小红书卡片生成器"""
    
    def __init__(self, config: DistributionConfig, article_dir: str):
        """
        初始化生成器
        
        Args:
            config: 分发配置
            article_dir: 文章目录路径
        """
        self.config = config
        self.article_dir = Path(article_dir)
        self.output_dir = self.article_dir / "distribution" / "xhs"
    
    def generate(self, content: ExtractedContent) -> XHSOutput:
        """
        生成小红书卡片
        
        Args:
            content: 提取的内容
        
        Returns:
            XHSOutput: 生成结果
        """
        if not self.config.xiaohongshu.enabled:
            return XHSOutput(success=False, image_paths=[], error_message="小红书分发已禁用")
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 确定风格
        if self.config.xiaohongshu.style == "auto":
            style = get_style_for_tags(content.tags, self.config.style_mapping)
        else:
            style = self.config.xiaohongshu.style
        
        # 准备内容
        xhs_content = self._prepare_content(content)
        
        # 保存临时内容文件
        temp_content_path = self.output_dir / "_temp_content.md"
        with open(temp_content_path, "w", encoding="utf-8") as f:
            f.write(xhs_content)
        
        # 调用 baoyu-xhs-images 技能
        # 注意：这里需要通过 Claude Code 的 Skill 系统调用
        # 实际实现中，这个函数会返回一个提示，让 AI 调用 /baoyu-xhs-images
        
        return XHSOutput(
            success=True,
            image_paths=[],
            error_message="请使用 /baoyu-xhs-images 技能生成卡片，内容已准备好"
        )
    
    def _prepare_content(self, content: ExtractedContent) -> str:
        """
        准备小红书卡片内容
        
        Args:
            content: 提取的内容
        
        Returns:
            str: 格式化的内容文本
        """
        parts = []
        
        # 封面：标题 + 来源
        parts.append(f"# {content.title}")
        parts.append(f"来源：{content.source}")
        if content.guest and content.guest != "无":
            parts.append(f"嘉宾：{content.guest}")
        parts.append("")
        
        # 核心洞察
        if "insights" in self.config.xiaohongshu.content and content.insights:
            parts.append("## 核心洞察")
            for i, insight in enumerate(content.insights[:self.config.xiaohongshu.max_images - 2], 1):
                title = insight.get("title", "")
                body = insight.get("content", "")
                if title:
                    parts.append(f"### {i}. {title}")
                parts.append(body)
                parts.append("")
        
        # 哲思结语
        if "ending" in self.config.xiaohongshu.content and content.philosophical_epilogue:
            parts.append("## 哲思结语")
            parts.append(content.philosophical_epilogue)
        
        return "\n".join(parts)
    
    def get_generation_prompt(self, content: ExtractedContent) -> str:
        """
        获取用于调用 baoyu-xhs-images 的提示
        
        Args:
            content: 提取的内容
        
        Returns:
            str: 调用提示
        """
        # 确定风格
        if self.config.xiaohongshu.style == "auto":
            style = get_style_for_tags(content.tags, self.config.style_mapping)
        else:
            style = self.config.xiaohongshu.style
        
        # 确定布局
        layout = self.config.xiaohongshu.layout.get("insights", "dense")
        
        # 构建内容
        xhs_content = self._prepare_content(content)
        
        # 保存内容文件
        content_file = self.output_dir / "xhs_content.md"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(xhs_content)
        
        return f"""请使用 /baoyu-xhs-images 技能生成小红书卡片：

**内容文件**: `{content_file}`
**风格**: `{style}`
**布局**: `{layout}`

**调用命令**:
```
/baoyu-xhs-images {content_file} --style {style} --layout {layout}
```

**输出目录**: `{self.output_dir}`

生成完成后，请将图片移动到该目录。"""
