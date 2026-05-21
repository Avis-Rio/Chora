"""
内容提取器

从 rewritten.md 和 metadata.md 中提取分发所需的内容片段。
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedContent:
    """提取的内容结构"""
    # 元数据
    title: str = ""
    source: str = ""
    guest: str = ""
    quotes: list = field(default_factory=list)
    
    # 深度改写
    rewrite_body: str = ""
    
    # 核心洞察
    insights: list = field(default_factory=list)
    
    # 哲思结语
    philosophical_epilogue: str = ""
    
    # 推荐书单
    booklist: str = ""
    
    # 内容标签
    tags: list = field(default_factory=list)


class ContentExtractor:
    """内容提取器"""
    
    def __init__(self, article_dir: str):
        """
        初始化提取器
        
        Args:
            article_dir: 文章目录路径（如 content_archive/2026-01-26/youtube_xxx）
        """
        self.article_dir = Path(article_dir)
        self.metadata_path = self.article_dir / "metadata.md"
        self.rewritten_path = self.article_dir / "rewritten.md"
    
    def extract(self) -> ExtractedContent:
        """
        提取所有内容
        
        Returns:
            ExtractedContent: 提取的内容对象
        """
        content = ExtractedContent()
        
        # 提取元数据
        if self.metadata_path.exists():
            self._extract_metadata(content)
        
        # 提取改写内容
        if self.rewritten_path.exists():
            self._extract_rewritten(content)
        
        return content
    
    def _extract_metadata(self, content: ExtractedContent) -> None:
        """从 metadata.md 提取元数据"""
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # 提取标题（第一个 # 开头的行）
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            content.title = title_match.group(1).strip()
        
        # 提取来源
        source_match = re.search(r"^## 来源\s*$\s*(.+)$", text, re.MULTILINE)
        if source_match:
            content.source = source_match.group(1).strip()
        
        # 提取嘉宾
        guest_match = re.search(r"^## 嘉宾\s*$\s*(.+)$", text, re.MULTILINE)
        if guest_match:
            content.guest = guest_match.group(1).strip()
        
        # 提取金句（> 开头的行）
        quotes = re.findall(r"^>\s*(.+)$", text, re.MULTILINE)
        content.quotes = [q.strip() for q in quotes if q.strip()]
    
    def _extract_rewritten(self, content: ExtractedContent) -> None:
        """从 rewritten.md 提取改写内容"""
        with open(self.rewritten_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # 提取深度改写正文（## 2. 深度改写 部分）
        rewrite_match = re.search(
            r"## 2\. 深度改写.*?\n(.*?)(?=## 3\. 核心洞察|$)",
            text,
            re.DOTALL
        )
        if rewrite_match:
            content.rewrite_body = rewrite_match.group(1).strip()
        
        # 提取核心洞察
        insights_match = re.search(
            r"## 3\. 核心洞察.*?\n(.*?)(?=## 4\. 哲思结语|$)",
            text,
            re.DOTALL
        )
        if insights_match:
            insights_text = insights_match.group(1)
            # 提取编号的洞察条目
            insights = re.findall(r"^\d+\.\s*\*\*(.+?)\*\*[:：](.+?)(?=\n\d+\.|\n##|$)", insights_text, re.DOTALL)
            content.insights = [
                {"title": title.strip(), "content": body.strip()}
                for title, body in insights
            ]
            # 如果上面的模式没匹配到，尝试简单匹配
            if not content.insights:
                simple_insights = re.findall(r"^\d+\.\s*(.+?)$", insights_text, re.MULTILINE)
                content.insights = [{"title": "", "content": i.strip()} for i in simple_insights if i.strip()]
        
        # 提取哲思结语
        epilogue_match = re.search(
            r"## 4\. 哲思结语.*?\n(.*?)(?=## 5\. 推荐书单|$)",
            text,
            re.DOTALL
        )
        if epilogue_match:
            content.philosophical_epilogue = epilogue_match.group(1).strip()
        
        # 提取推荐书单
        booklist_match = re.search(
            r"## 5\. 推荐书单.*?\n(.*?)(?=## 6\. 内容标签|$)",
            text,
            re.DOTALL
        )
        if booklist_match:
            content.booklist = booklist_match.group(1).strip()
        
        # 提取标签
        tags_match = re.search(r"Tags:\s*(.+)$", text, re.MULTILINE)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            content.tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    
    def get_article_slug(self) -> str:
        """获取文章的 slug（用于生成文件名）"""
        # 从目录名提取 slug
        dir_name = self.article_dir.name
        # 移除日期前缀
        parts = dir_name.split("_", 2)
        if len(parts) >= 3:
            return parts[2].lower().replace(" ", "-").replace("：", "-")[:50]
        return dir_name.lower().replace(" ", "-")[:50]
