TECH_ECON_MOTIFS = ["账本", "仪表盘", "电流", "交易所", "算力机房"]
POWER_MOTIFS = ["天平", "印章", "档案", "刻度线", "边界地图"]
DEFAULT_MOTIFS = ["纸张", "注释线", "索引编号", "暗色几何体"]


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_visual_system(source: dict, insights: list[dict]) -> dict:
    tags = set(source.get("tags", []))
    motifs = []

    if {"Technology", "Economics"} & tags:
        motifs.extend(TECH_ECON_MOTIFS)
    if "Power & Politics" in tags:
        motifs.extend(POWER_MOTIFS)
    motifs.extend(DEFAULT_MOTIFS)

    insight_titles = "、".join(item.get("title", "") for item in insights[:3] if item.get("title"))
    theme = source.get("title") or insight_titles or "Chora 分发素材"

    return {
        "theme": theme,
        "visual_motifs": _unique(motifs),
        "material_language": ["旧纸纹理", "细密刻度线", "扫描颗粒", "微弱荧光"],
        "composition_rules": [
            "避免连续居中大标题",
            "每张卡只使用一个主视觉隐喻",
            "保留统一的编号系统",
            "品牌标识低调固定在边角",
        ],
        "avoid": ["普通科技蓝渐变", "硬币图标", "抽象球体", "SaaS 风插画"],
    }
