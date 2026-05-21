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
