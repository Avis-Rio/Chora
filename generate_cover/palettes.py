"""Topic-keyed palette catalogue for Chora cover image prompts.

Each domain maps a title keyword set to a colour palette dict suitable for
inclusion in a Gemini image prompt. The palette dict shape::

    {
        'palette_description': str,
        'primary_colors': str,
        'accent_colors': str,
        'text_color': str,
        'mood': str,
        'inspiration': str,
        'theme_hint': str,
    }

Extracted from the legacy monolithic ``generate_cover.py`` on 2026-07-11
as part of the L5 split tracked in ``skills/ARCHITECTURE.md`` §6.
"""


def get_color_palette_for_topic(title):
    """
    根据标题内容判断主题领域，返回对应的配色方案。

    支持的领域：
    - 艺术/美学：暖色调，博物馆质感
    - 科技/未来：冷色调，霓虹感
    - 哲学/思想：深沉中性色，沉思感
    - 历史/文化：复古暖色，岁月感
    - 社会/政治：对比强烈，新闻感
    - 自然/环境：绿色系，生机感
    - 心理/情感：柔和渐变，温暖感
    - 文学/诗歌：水墨风，意境感
    - 经济/商业：稳重蓝色，专业感
    - 默认：多彩但和谐的配色
    """
    title_lower = title.lower()

    # 艺术/美学领域
    art_keywords = [
        "艺术",
        "美术",
        "绘画",
        "画家",
        "雕塑",
        "博物馆",
        "美学",
        "审美",
        "设计",
        "摄影",
        "建筑",
        "装置",
        "展览",
        "art",
        "museum",
        "painting",
    ]
    if any(kw in title_lower for kw in art_keywords):
        return {
            "palette_description": "Museum-quality sophistication with rich earth tones and gallery lighting",
            "primary_colors": "Burnt sienna, terracotta, deep burgundy, warm ochre",
            "accent_colors": "Antique gold, cream white, charcoal grey",
            "text_color": "Aged ivory or warm cream that complements the earthy background",
            "mood": "Contemplative, refined, culturally rich",
            "inspiration": "Renaissance gallery walls, Vermeer lighting, classic art catalogs",
            "theme_hint": "Evoke the warmth of a candlelit gallery or the texture of aged canvas.",
        }

    # 科技/未来领域
    tech_keywords = [
        "科技",
        "人工智能",
        "AI",
        "技术",
        "数字",
        "互联网",
        "算法",
        "编程",
        "机器人",
        "量子",
        "虚拟",
        "元宇宙",
        "tech",
        "digital",
        "future",
    ]
    if any(kw in title_lower for kw in tech_keywords):
        return {
            "palette_description": "Futuristic cyberpunk aesthetics with electric neon and deep shadows",
            "primary_colors": "Electric blue, deep purple, midnight black",
            "accent_colors": "Neon cyan, magenta pink, holographic silver",
            "text_color": "Glowing cyan or electric blue with subtle neon glow effect",
            "mood": "Cutting-edge, mysterious, forward-thinking",
            "inspiration": "Blade Runner cityscape, Tron aesthetics, sci-fi book covers",
            "theme_hint": "Create a sense of digital depth and technological wonder.",
        }

    # 哲学/思想领域
    philosophy_keywords = [
        "哲学",
        "思想",
        "存在",
        "意识",
        "认知",
        "伦理",
        "道德",
        "本质",
        "真理",
        "理性",
        "自由意志",
        "形而上",
        "philosophy",
        "mind",
    ]
    if any(kw in title_lower for kw in philosophy_keywords):
        return {
            "palette_description": "Deep contemplative tones evoking intellectual depth and mystery",
            "primary_colors": "Slate grey, deep navy, muted indigo",
            "accent_colors": "Soft silver, pale moonlight, dusty rose",
            "text_color": "Soft silver or pale grey with ethereal quality",
            "mood": "Meditative, profound, intellectually stimulating",
            "inspiration": "Academic press covers, monastery libraries, Rothko paintings",
            "theme_hint": "Suggest the weight of ideas and the depth of contemplation.",
        }

    # 历史/文化领域
    history_keywords = [
        "历史",
        "古代",
        "朝代",
        "帝国",
        "文明",
        "传统",
        "遗产",
        "考古",
        "文物",
        "典籍",
        "古典",
        "history",
        "ancient",
        "heritage",
    ]
    if any(kw in title_lower for kw in history_keywords):
        return {
            "palette_description": "Vintage sepia tones with aged paper texture and classical elegance",
            "primary_colors": "Sepia brown, antique gold, deep mahogany",
            "accent_colors": "Faded ivory, dusty rose, aged bronze",
            "text_color": "Antique gold or aged bronze with weathered patina",
            "mood": "Nostalgic, dignified, timelessly elegant",
            "inspiration": "Ancient manuscripts, vintage maps, classic history books",
            "theme_hint": "Evoke the patina of time and the weight of centuries.",
        }

    # 社会/政治领域
    social_keywords = [
        "社会",
        "政治",
        "权力",
        "制度",
        "民主",
        "公民",
        "阶层",
        "不平等",
        "革命",
        "运动",
        "抗争",
        "social",
        "political",
        "power",
    ]
    if any(kw in title_lower for kw in social_keywords):
        return {
            "palette_description": "Bold contrasts with editorial punch and newsroom gravitas",
            "primary_colors": "Deep crimson, stark white, jet black",
            "accent_colors": "Steel grey, newspaper yellow, urgent orange",
            "text_color": "Bold white or stark black for maximum impact",
            "mood": "Urgent, thought-provoking, socially conscious",
            "inspiration": "Time Magazine covers, documentary posters, protest art",
            "theme_hint": "Convey the tension and importance of social discourse.",
        }

    # 自然/环境领域
    nature_keywords = [
        "自然",
        "生态",
        "环境",
        "气候",
        "动物",
        "植物",
        "海洋",
        "森林",
        "地球",
        "可持续",
        "nature",
        "ecology",
        "environment",
    ]
    if any(kw in title_lower for kw in nature_keywords):
        return {
            "palette_description": "Organic earth tones and lush natural greens with vitality",
            "primary_colors": "Forest green, ocean teal, earthy brown",
            "accent_colors": "Sunrise orange, wildflower purple, sky blue",
            "text_color": "Cream white or pale sage that breathes with nature",
            "mood": "Vibrant, life-affirming, environmentally conscious",
            "inspiration": "National Geographic covers, nature documentaries, botanical illustrations",
            "theme_hint": "Celebrate the beauty and fragility of the natural world.",
        }

    # 心理/情感领域
    psychology_keywords = [
        "心理",
        "情感",
        "情绪",
        "焦虑",
        "抑郁",
        "幸福",
        "关系",
        "亲密",
        "创伤",
        "疗愈",
        "自我",
        "psychology",
        "emotion",
        "mental",
    ]
    if any(kw in title_lower for kw in psychology_keywords):
        return {
            "palette_description": "Soft gradients and warm tones evoking emotional depth",
            "primary_colors": "Soft lavender, warm peach, gentle coral",
            "accent_colors": "Misty blue, sunset pink, healing green",
            "text_color": "Warm cream or soft white with gentle glow",
            "mood": "Empathetic, introspective, healing",
            "inspiration": "Therapy book covers, mindfulness apps, impressionist soft focus",
            "theme_hint": "Create a safe space for emotional exploration.",
        }

    # 文学/诗歌领域
    literature_keywords = [
        "文学",
        "诗",
        "小说",
        "散文",
        "作家",
        "写作",
        "叙事",
        "故事",
        "阅读",
        "书籍",
        "literature",
        "poetry",
        "novel",
        "writer",
    ]
    if any(kw in title_lower for kw in literature_keywords):
        return {
            "palette_description": "Ink wash aesthetics with poetic brushstrokes and literary elegance",
            "primary_colors": "Ink black, rice paper white, misty grey",
            "accent_colors": "Cherry blossom pink, jade green, vermillion red",
            "text_color": "Traditional ink black or cinnabar red with calligraphic grace",
            "mood": "Poetic, evocative, literarily refined",
            "inspiration": "Chinese ink painting, Penguin Classics, literary magazine covers",
            "theme_hint": "Let words and images dance together in harmonious composition.",
        }

    # 经济/商业领域
    business_keywords = [
        "经济",
        "金融",
        "商业",
        "投资",
        "市场",
        "创业",
        "管理",
        "战略",
        "货币",
        "资本",
        "business",
        "economy",
        "finance",
        "market",
    ]
    if any(kw in title_lower for kw in business_keywords):
        return {
            "palette_description": "Professional sophistication with corporate elegance",
            "primary_colors": "Navy blue, charcoal grey, deep teal",
            "accent_colors": "Metallic gold, silver accents, pure white",
            "text_color": "Crisp white or metallic gold for executive presence",
            "mood": "Authoritative, trustworthy, professionally refined",
            "inspiration": "Harvard Business Review, The Economist, financial reports",
            "theme_hint": "Project confidence and analytical clarity.",
        }

    # 女性/性别领域
    gender_keywords = ["女性", "女权", "性别", "厌女", "母职", "feminism", "gender", "women"]
    if any(kw in title_lower for kw in gender_keywords):
        return {
            "palette_description": "Empowering tones with artistic boldness and feminine strength",
            "primary_colors": "Deep magenta, royal purple, passionate red",
            "accent_colors": "Soft pink, ivory, midnight blue",
            "text_color": "Bold white or soft cream with elegant femininity",
            "mood": "Empowering, thought-provoking, artistically bold",
            "inspiration": "Feminist art, contemporary gallery exhibitions, Frida Kahlo palette",
            "theme_hint": "Celebrate feminine power and critical discourse.",
        }

    return {
        "palette_description": "Rich, sophisticated palette with museum-quality depth and subtle gradients",
        "primary_colors": "Deep teal, burnt umber, muted olive",
        "accent_colors": "Antique gold, dusty rose, soft cream",
        "text_color": "Colors that harmonize with the background - warm ivory, soft gold, or muted tones",
        "mood": "Evocative, atmospheric, intellectually stimulating",
        "inspiration": "New Yorker covers, Penguin Classics, art house film posters",
        "theme_hint": "Create a unique visual identity that captures the essence of this topic.",
    }
