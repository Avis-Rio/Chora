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
