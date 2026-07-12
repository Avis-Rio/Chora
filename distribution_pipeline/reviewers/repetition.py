from collections import Counter


def review_repetition(briefs: list[dict]) -> dict:
    issues = []
    warnings = []

    for prev, current in zip(briefs, briefs[1:]):
        if prev.get("visual_metaphor") == current.get("visual_metaphor"):
            issues.append("duplicate_visual_metaphor")
        if prev.get("composition", {}).get("text_position") == current.get("composition", {}).get(
            "text_position"
        ):
            issues.append("duplicate_composition")

    positions = [
        brief.get("composition", {}).get("text_position") for brief in briefs if brief.get("composition")
    ]
    if positions:
        most_common_count = Counter(positions).most_common(1)[0][1]
        if most_common_count / len(positions) > 0.6:
            warnings.append("composition_overused")

    return {
        "passed": not issues,
        "issues": sorted(set(issues)),
        "warnings": warnings,
    }
