TEXT_POSITIONS = ["left-top", "right-lower", "vertical-left", "split-axis", "bottom-annotation"]


def _select_motif(insight: dict, motifs: list[str], index: int) -> str:
    title = insight.get("title", "")
    body = insight.get("body", "")
    text = f"{title} {body}"

    if "成本" in text and "账本" in motifs:
        return "账本"
    if ("计量" in text or "权力" in text) and "仪表盘" in motifs:
        return "仪表盘"
    if "价格" in text and "交易所" in motifs:
        return "交易所"
    return motifs[index % len(motifs)] if motifs else "纸张"


def build_visual_briefs(insights: list[dict], visual_system: dict) -> list[dict]:
    motifs = visual_system.get("visual_motifs", [])
    forbidden = visual_system.get("avoid", [])
    briefs = []
    used_metaphors = set()

    for offset, insight in enumerate(insights):
        motif = _select_motif(insight, motifs, offset)
        if motif in used_metaphors and motifs:
            motif = motifs[(offset + 1) % len(motifs)]
        used_metaphors.add(motif)

        briefs.append(
            {
                "insight_index": insight.get("index", offset + 1),
                "card_type": "single-insight",
                "insight_title": insight.get("title", ""),
                "core_sentence": insight.get("one_liner") or insight.get("body", "")[:80],
                "visual_metaphor": f"{motif}作为“{insight.get('title', '')}”的核心视觉隐喻",
                "composition": {
                    "focal_point": motif,
                    "text_position": TEXT_POSITIONS[offset % len(TEXT_POSITIONS)],
                    "negative_space": "顶部保留克制留白",
                    "depth": "前景材质，中景主体，背景注释线",
                },
                "mood": "冷静、克制、带有制度感",
                "texture": visual_system.get("material_language", [])[:3],
                "forbidden_cliches": forbidden,
            }
        )

    return briefs
