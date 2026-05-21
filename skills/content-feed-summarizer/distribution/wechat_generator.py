"""
微信公众号 Markdown 生成器

生成适配微信公众号编辑器的 Markdown 文档。
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import re

from config_loader import DistributionConfig
from content_extractor import ExtractedContent


@dataclass
class WeChatOutput:
    """微信公众号生成输出"""
    success: bool
    markdown_path: str = ""
    error_message: str = ""


class WeChatGenerator:
    """微信公众号 Markdown 生成器"""
    
    def __init__(self, config: DistributionConfig, article_dir: str):
        """
        初始化生成器
        
        Args:
            config: 分发配置
            article_dir: 文章目录路径
        """
        self.config = config
        self.article_dir = Path(article_dir)
        self.output_dir = self.article_dir / "distribution" / "wechat"
    
    def generate(self, content: ExtractedContent) -> WeChatOutput:
        """
        生成微信公众号 Markdown
        
        Args:
            content: 提取的内容
        
        Returns:
            WeChatOutput: 生成结果
        """
        if not self.config.wechat.enabled:
            return WeChatOutput(success=False, error_message="微信公众号分发已禁用")
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成 Markdown
        markdown = self._generate_markdown(content)
        
        # 保存文件
        output_path = self.output_dir / "article.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return WeChatOutput(success=True, markdown_path=str(output_path))
    
    def _generate_markdown(self, content: ExtractedContent) -> str:
        """
        生成 Markdown 内容
        
        Args:
            content: 提取的内容
        
        Returns:
            str: Markdown 文本
        """
        parts = []
        
        # 标题
        parts.append(f"# {content.title}")
        parts.append("")
        
        # 来源信息
        if content.source:
            parts.append(f"**来源**: {content.source}")
        if content.guest and content.guest != "无":
            parts.append(f"**嘉宾**: {content.guest}")
        parts.append("")
        
        # 深度改写正文
        if "rewrite" in self.config.wechat.content and content.rewrite_body:
            parts.append(content.rewrite_body)
            parts.append("")
        
        # 推荐书单
        if "booklist" in self.config.wechat.content and content.booklist:
            parts.append("---")
            parts.append("")
            parts.append("## 📚 延伸阅读")
            parts.append("")
            parts.append(content.booklist)
            parts.append("")
        
        # 回流链接
        parts.append("---")
        parts.append("")
        
        if self.config.wechat.backlinks.get("chora_site"):
            # 生成 Chora 链接（基于文章目录名）
            article_slug = self._get_article_slug()
            chora_url = f"{self.config.backlinks.chora_base_url}/article/{article_slug}"
            parts.append(f"> 📖 [阅读原文]({chora_url})")
            parts.append("")
        
        if self.config.wechat.backlinks.get("wechat_account"):
            guide = self.config.backlinks.wechat_guide.strip()
            if guide:
                parts.append(f"> {guide}")
        
        return "\n".join(parts)
    
    def _get_article_slug(self) -> str:
        """获取文章的 slug（用于生成 URL）"""
        dir_name = self.article_dir.name
        # 移除日期前缀
        parts = dir_name.split("_", 2)
        if len(parts) >= 3:
            slug = parts[2]
            # 清理特殊字符
            slug = re.sub(r"[：:]", "-", slug)
            slug = re.sub(r"[^\w一-鿿\-]", "", slug)
            return slug[:100]
        return dir_name[:100]
