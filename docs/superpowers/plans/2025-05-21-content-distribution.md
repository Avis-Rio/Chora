# Chora 内容分发功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Chora 项目添加自动化的内容分发能力，将处理完成的订阅内容自动生成为小红书卡片和微信公众号 Markdown。

**Architecture:** 扩展现有 `content-feed-summarizer` Skill，新增 Step 7 分发步骤。通过配置文件 `distribution-config.yaml` 控制分发行为。调用牛马AI内置的 `baoyu-xhs-images` 技能生成小红书卡片，生成公众号 Markdown 模板。

**Tech Stack:** Claude Code Skills, baoyu-xhs-images, YAML, Python, Markdown

---

## 文件结构

```
skills/content-feed-summarizer/
├── SKILL.md                      # 修改：新增 Step 7
├── distribution-config.yaml      # 新增：分发配置文件
└── distribution/
    ├── __init__.py               # 新增：Python 模块初始化
    ├── config_loader.py          # 新增：配置加载器
    ├── content_extractor.py      # 新增：内容提取器
    ├── xhs_generator.py          # 新增：小红书卡片生成
    └── wechat_generator.py       # 新增：公众号 Markdown 生成

content_archive/{article}/
└── distribution/                 # 新增：分发输出目录
    ├── xhs/
    │   ├── 01-cover.png
    │   ├── 02-insight.png
    │   └── ...
    └── wechat/
        └── article.md
```

---

## Task 1: 创建分发配置文件

**Files:**
- Create: `skills/content-feed-summarizer/distribution-config.yaml`

- [ ] **Step 1: 创建配置文件**

```yaml
# 内容分发配置
# 路径: skills/content-feed-summarizer/distribution-config.yaml

distribution:
  # 全局开关
  enabled: true

  # 小红书配置
  xiaohongshu:
    enabled: true
    # 内容选择
    content:
      - insights    # 核心洞察
      - ending      # 哲思结语
    # 视觉风格：auto 表示根据内容标签自动适配
    style: auto
    # 布局配置
    layout:
      insights: dense
      ending: sparse
    # 图片数量限制
    max_images: 6

  # 微信公众号配置
  wechat:
    enabled: true
    # 内容选择
    content:
      - rewrite     # 深度改写
      - booklist    # 书单推荐
    # 回流配置
    backlinks:
      chora_site: true
      wechat_account: "Rhizomata"

  # 回流链接配置
  backlinks:
    # Chora 网站基础 URL（需根据实际部署修改）
    chora_base_url: "https://chora.limyai.com"
    # 公众号引导语
    wechat_guide: |
      关注公众号「Rhizomata」，获取更多深度内容。

  # 风格映射规则（内容标签 → 小红书风格）
  style_mapping:
    Philosophy: notion
    Sociology: notion
    Psychology: notion
    Technology: minimal
    Economics: minimal
    History: chalkboard
    Anthropology: chalkboard
    "Art & Aesthetics": warm
    default: notion
```

- [ ] **Step 2: 验证配置文件格式**

Run: `python3 -c "import yaml; yaml.safe_load(open('skills/content-feed-summarizer/distribution-config.yaml'))"`
Expected: 无错误输出

- [ ] **Step 3: 提交配置文件**

```bash
git add skills/content-feed-summarizer/distribution-config.yaml
git commit -m "feat: 添加内容分发配置文件

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: 创建配置加载器

**Files:**
- Create: `skills/content-feed-summarizer/distribution/__init__.py`
- Create: `skills/content-feed-summarizer/distribution/config_loader.py`

- [ ] **Step 1: 创建模块初始化文件**

```python
# skills/content-feed-summarizer/distribution/__init__.py
"""
Chora 内容分发模块

提供小红书卡片和微信公众号 Markdown 的自动生成能力。
"""

from .config_loader import DistributionConfig, load_config
from .content_extractor import ContentExtractor
from .xhs_generator import XHSGenerator
from .wechat_generator import WeChatGenerator

__all__ = [
    "DistributionConfig",
    "load_config",
    "ContentExtractor",
    "XHSGenerator",
    "WeChatGenerator",
]
```

- [ ] **Step 2: 创建配置加载器**

```python
# skills/content-feed-summarizer/distribution/config_loader.py
"""
分发配置加载器

负责读取和解析 distribution-config.yaml 配置文件。
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class XHSConfig:
    """小红书分发配置"""
    enabled: bool = True
    content: list = field(default_factory=lambda: ["insights", "ending"])
    style: str = "auto"
    layout: dict = field(default_factory=lambda: {"insights": "dense", "ending": "sparse"})
    max_images: int = 6


@dataclass
class WeChatConfig:
    """微信公众号分发配置"""
    enabled: bool = True
    content: list = field(default_factory=lambda: ["rewrite", "booklist"])
    backlinks: dict = field(default_factory=lambda: {"chora_site": True, "wechat_account": "Rhizomata"})


@dataclass
class BacklinksConfig:
    """回流链接配置"""
    chora_base_url: str = "https://chora.limyai.com"
    wechat_guide: str = "关注公众号「Rhizomata」，获取更多深度内容。"


@dataclass
class DistributionConfig:
    """分发总配置"""
    enabled: bool = True
    xiaohongshu: XHSConfig = field(default_factory=XHSConfig)
    wechat: WeChatConfig = field(default_factory=WeChatConfig)
    backlinks: BacklinksConfig = field(default_factory=BacklinksConfig)
    style_mapping: dict = field(default_factory=lambda: {
        "Philosophy": "notion",
        "Sociology": "notion",
        "Psychology": "notion",
        "Technology": "minimal",
        "Economics": "minimal",
        "History": "chalkboard",
        "Anthropology": "chalkboard",
        "Art & Aesthetics": "warm",
        "default": "notion",
    })


def load_config(config_path: Optional[str] = None) -> DistributionConfig:
    """
    加载分发配置文件
    
    Args:
        config_path: 配置文件路径，默认为 skills/content-feed-summarizer/distribution-config.yaml
    
    Returns:
        DistributionConfig: 分发配置对象
    """
    if config_path is None:
        # 默认路径：相对于项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "skills" / "content-feed-summarizer" / "distribution-config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"[Distribution] 配置文件不存在: {config_path}，使用默认配置")
        return DistributionConfig()
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    
    if not raw_config or "distribution" not in raw_config:
        print("[Distribution] 配置文件格式无效，使用默认配置")
        return DistributionConfig()
    
    dist = raw_config["distribution"]
    
    # 解析小红书配置
    xhs_raw = dist.get("xiaohongshu", {})
    xhs_config = XHSConfig(
        enabled=xhs_raw.get("enabled", True),
        content=xhs_raw.get("content", ["insights", "ending"]),
        style=xhs_raw.get("style", "auto"),
        layout=xhs_raw.get("layout", {"insights": "dense", "ending": "sparse"}),
        max_images=xhs_raw.get("max_images", 6),
    )
    
    # 解析公众号配置
    wc_raw = dist.get("wechat", {})
    wc_config = WeChatConfig(
        enabled=wc_raw.get("enabled", True),
        content=wc_raw.get("content", ["rewrite", "booklist"]),
        backlinks=wc_raw.get("backlinks", {"chora_site": True, "wechat_account": "Rhizomata"}),
    )
    
    # 解析回流配置
    bl_raw = dist.get("backlinks", {})
    bl_config = BacklinksConfig(
        chora_base_url=bl_raw.get("chora_base_url", "https://chora.limyai.com"),
        wechat_guide=bl_raw.get("wechat_guide", "关注公众号「Rhizomata」，获取更多深度内容。"),
    )
    
    return DistributionConfig(
        enabled=dist.get("enabled", True),
        xiaohongshu=xhs_config,
        wechat=wc_config,
        backlinks=bl_config,
        style_mapping=dist.get("style_mapping", DistributionConfig().style_mapping),
    )


def get_style_for_tags(tags: list, style_mapping: dict) -> str:
    """
    根据内容标签获取推荐的小红书风格
    
    Args:
        tags: 内容标签列表（如 ["Technology", "Sociology"]）
        style_mapping: 风格映射字典
    
    Returns:
        str: 推荐的风格名称
    """
    for tag in tags:
        if tag in style_mapping:
            return style_mapping[tag]
    return style_mapping.get("default", "notion")
```

- [ ] **Step 3: 测试配置加载器**

```bash
cd /Users/Avis/Vibe_Coding/Chora
python3 -c "
from skills.content_feed_summarizer.distribution.config_loader import load_config, get_style_for_tags

config = load_config()
print(f'分发启用: {config.enabled}')
print(f'小红书启用: {config.xiaohongshu.enabled}')
print(f'公众号启用: {config.wechat.enabled}')

# 测试风格映射
tags = ['Technology', 'Economics']
style = get_style_for_tags(tags, config.style_mapping)
print(f'标签 {tags} 推荐风格: {style}')
"
```
Expected: 输出配置信息，无错误

- [ ] **Step 4: 提交配置加载器**

```bash
git add skills/content-feed-summarizer/distribution/
git commit -m "feat: 添加分发配置加载器

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: 创建内容提取器

**Files:**
- Create: `skills/content-feed-summarizer/distribution/content_extractor.py`

- [ ] **Step 1: 创建内容提取器**

```python
# skills/content-feed-summarizer/distribution/content_extractor.py
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
```

- [ ] **Step 2: 测试内容提取器**

```bash
cd /Users/Avis/Vibe_Coding/Chora
python3 -c "
from skills.content_feed_summarizer.distribution.content_extractor import ContentExtractor

# 使用现有文章测试
extractor = ContentExtractor('content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识')
content = extractor.extract()

print(f'标题: {content.title}')
print(f'来源: {content.source}')
print(f'嘉宾: {content.guest}')
print(f'金句数量: {len(content.quotes)}')
print(f'洞察数量: {len(content.insights)}')
print(f'标签: {content.tags}')
print(f'Slug: {extractor.get_article_slug()}')

if content.insights:
    print(f'\\n第一条洞察:')
    print(f'  标题: {content.insights[0][\"title\"]}')
    print(f'  内容: {content.insights[0][\"content\"][:100]}...')
"
```
Expected: 输出提取的内容信息，无错误

- [ ] **Step 3: 提交内容提取器**

```bash
git add skills/content-feed-summarizer/distribution/content_extractor.py
git commit -m "feat: 添加内容提取器

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: 创建小红书卡片生成器

**Files:**
- Create: `skills/content-feed-summarizer/distribution/xhs_generator.py`

- [ ] **Step 1: 创建小红书卡片生成器**

```python
# skills/content-feed-summarizer/distribution/xhs_generator.py
"""
小红书卡片生成器

调用 baoyu-xhs-images 技能生成小红书卡片图片。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config_loader import DistributionConfig, get_style_for_tags
from .content_extractor import ExtractedContent


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
```

- [ ] **Step 2: 测试小红书生成器**

```bash
cd /Users/Avis/Vibe_Coding/Chora
python3 -c "
from skills.content_feed_summarizer.distribution.config_loader import load_config
from skills.content_feed_summarizer.distribution.content_extractor import ContentExtractor
from skills.content_feed_summarizer.distribution.xhs_generator import XHSGenerator

config = load_config()
extractor = ContentExtractor('content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识')
content = extractor.extract()

generator = XHSGenerator(config, 'content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识')
prompt = generator.get_generation_prompt(content)
print(prompt)
"
```
Expected: 输出生成提示，无错误

- [ ] **Step 3: 提交小红书生成器**

```bash
git add skills/content-feed-summarizer/distribution/xhs_generator.py
git commit -m "feat: 添加小红书卡片生成器

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 创建微信公众号 Markdown 生成器

**Files:**
- Create: `skills/content-feed-summarizer/distribution/wechat_generator.py`

- [ ] **Step 1: 创建微信公众号生成器**

```python
# skills/content-feed-summarizer/distribution/wechat_generator.py
"""
微信公众号 Markdown 生成器

生成适配微信公众号编辑器的 Markdown 文档。
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import re

from .config_loader import DistributionConfig
from .content_extractor import ExtractedContent


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
```

- [ ] **Step 2: 测试微信公众号生成器**

```bash
cd /Users/Avis/Vibe_Coding/Chora
python3 -c "
from skills.content_feed_summarizer.distribution.config_loader import load_config
from skills.content_feed_summarizer.distribution.content_extractor import ContentExtractor
from skills.content_feed_summarizer.distribution.wechat_generator import WeChatGenerator

config = load_config()
extractor = ContentExtractor('content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识')
content = extractor.extract()

generator = WeChatGenerator(config, 'content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识')
result = generator.generate(content)

print(f'成功: {result.success}')
print(f'输出路径: {result.markdown_path}')

if result.success:
    with open(result.markdown_path, 'r') as f:
        print('\\n--- Markdown 预览 (前 500 字符) ---')
        print(f.read()[:500])
"
```
Expected: 输出生成结果和预览，无错误

- [ ] **Step 3: 提交微信公众号生成器**

```bash
git add skills/content-feed-summarizer/distribution/wechat_generator.py
git commit -m "feat: 添加微信公众号 Markdown 生成器

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: 更新 SKILL.md 添加分发步骤

**Files:**
- Modify: `skills/content-feed-summarizer/SKILL.md`

- [ ] **Step 1: 在 SKILL.md 末尾添加 Step 7**

在现有 SKILL.md 的 `## ⚠️ 常见问题处理` 表格之前，添加以下内容：

```markdown
### 步骤 6：内容分发（可选）

**前置条件**: 步骤 5 完成，且 `distribution.enabled: true`

**配置文件**: `skills/content-feed-summarizer/distribution-config.yaml`

**流程**:

1. **读取配置**: 加载 `distribution-config.yaml`
2. **检查开关**: 确认各平台是否启用
3. **提取内容**: 从 `rewritten.md` 和 `metadata.md` 提取所需内容
4. **小红书分发**（如启用）:
   - 提取核心洞察 + 哲思结语
   - 根据内容标签自动选择风格
   - 调用 `/baoyu-xhs-images` 生成卡片
   - 输出到 `distribution/xhs/`
5. **微信公众号分发**（如启用）:
   - 提取深度改写 + 书单推荐
   - 生成 Markdown 文档
   - 添加回流链接和公众号引导
   - 输出到 `distribution/wechat/article.md`
6. **输出报告**: 显示生成的文件路径

**输出目录结构**:
```
content_archive/{article}/
└── distribution/
    ├── xhs/
    │   ├── 01-cover.png
    │   ├── 02-insight.png
    │   └── ...
    └── wechat/
        └── article.md
```

**错误处理**:
- 分发失败不阻塞主流程
- 记录错误到日志
- 继续处理下一个平台

**手动触发**:
```bash
# 单独运行动作分发
python3 -c "
from skills.content_feed_summarizer.distribution import (
    load_config, ContentExtractor, XHSGenerator, WeChatGenerator
)

config = load_config()
article_dir = 'content_archive/YYYY-MM-DD/xxx'

extractor = ContentExtractor(article_dir)
content = extractor.extract()

# 小红书
xhs = XHSGenerator(config, article_dir)
print(xhs.get_generation_prompt(content))

# 公众号
wc = WeChatGenerator(config, article_dir)
result = wc.generate(content)
print(f'公众号文章: {result.markdown_path}')
"
```
```

- [ ] **Step 2: 验证 SKILL.md 格式**

```bash
head -100 skills/content-feed-summarizer/SKILL.md
echo "---"
tail -80 skills/content-feed-summarizer/SKILL.md
```
Expected: 确认新步骤已添加，格式正确

- [ ] **Step 3: 提交 SKILL.md 更新**

```bash
git add skills/content-feed-summarizer/SKILL.md
git commit -m "feat: 在 SKILL.md 中添加内容分发步骤

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: 端到端测试

**Files:**
- Test: 使用现有文章进行完整测试

- [ ] **Step 1: 运行完整测试**

```bash
cd /Users/Avis/Vibe_Coding/Chora
python3 -c "
from skills.content_feed_summarizer.distribution import (
    load_config, ContentExtractor, XHSGenerator, WeChatGenerator
)

# 加载配置
config = load_config()
print(f'✓ 配置加载成功')
print(f'  - 分发启用: {config.enabled}')
print(f'  - 小红书启用: {config.xiaohongshu.enabled}')
print(f'  - 公众号启用: {config.wechat.enabled}')

# 测试文章
article_dir = 'content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识'

# 提取内容
extractor = ContentExtractor(article_dir)
content = extractor.extract()
print(f'\\n✓ 内容提取成功')
print(f'  - 标题: {content.title}')
print(f'  - 洞察数量: {len(content.insights)}')
print(f'  - 标签: {content.tags}')

# 生成公众号 Markdown
wc = WeChatGenerator(config, article_dir)
result = wc.generate(content)
if result.success:
    print(f'\\n✓ 公众号 Markdown 生成成功')
    print(f'  - 路径: {result.markdown_path}')
else:
    print(f'\\n✗ 公众号生成失败: {result.error_message}')

# 获取小红书生成提示
xhs = XHSGenerator(config, article_dir)
prompt = xhs.get_generation_prompt(content)
print(f'\\n✓ 小红书内容准备完成')
print(f'  - 输出目录: {xhs.output_dir}')
print(f'\\n--- 小红书生成提示 ---')
print(prompt)
"
```
Expected: 所有步骤成功，无错误

- [ ] **Step 2: 检查输出文件**

```bash
ls -la "content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识/distribution/"
```
Expected: 显示 distribution 目录结构

- [ ] **Step 3: 预览公众号 Markdown**

```bash
cat "content_archive/2026-01-26/youtube_硅谷101_CES_2026：探展50个AI项目背后的泡沫、野心与非共识/distribution/wechat/article.md" | head -50
```
Expected: 显示 Markdown 内容

---

## Task 8: 更新 __init__.py 并最终提交

**Files:**
- Modify: `skills/content-feed-summarizer/distribution/__init__.py`

- [ ] **Step 1: 确认 __init__.py 导出正确**

```python
# skills/content-feed-summarizer/distribution/__init__.py
"""
Chora 内容分发模块

提供小红书卡片和微信公众号 Markdown 的自动生成能力。
"""

from .config_loader import DistributionConfig, load_config, get_style_for_tags
from .content_extractor import ContentExtractor, ExtractedContent
from .xhs_generator import XHSGenerator, XHSOutput
from .wechat_generator import WeChatGenerator, WeChatOutput

__all__ = [
    # 配置
    "DistributionConfig",
    "load_config",
    "get_style_for_tags",
    # 内容提取
    "ContentExtractor",
    "ExtractedContent",
    # 小红书
    "XHSGenerator",
    "XHSOutput",
    # 微信公众号
    "WeChatGenerator",
    "WeChatOutput",
]
```

- [ ] **Step 2: 最终提交**

```bash
git add -A
git commit -m "feat: 完成内容分发功能

- 添加分发配置文件 distribution-config.yaml
- 添加配置加载器 config_loader.py
- 添加内容提取器 content_extractor.py
- 添加小红书卡片生成器 xhs_generator.py
- 添加微信公众号 Markdown 生成器 wechat_generator.py
- 更新 SKILL.md 添加 Step 7 分发步骤

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

- [ ] **Step 3: 推送到远程仓库**

```bash
git push origin main
```

---

## 完成检查清单

- [ ] 配置文件 `distribution-config.yaml` 已创建
- [ ] 配置加载器 `config_loader.py` 已创建并测试
- [ ] 内容提取器 `content_extractor.py` 已创建并测试
- [ ] 小红书生成器 `xhs_generator.py` 已创建并测试
- [ ] 微信公众号生成器 `wechat_generator.py` 已创建并测试
- [ ] SKILL.md 已更新添加 Step 7
- [ ] 端到端测试通过
- [ ] 所有代码已提交
