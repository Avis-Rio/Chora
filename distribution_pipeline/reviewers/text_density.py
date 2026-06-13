def review_text_density(card: dict, max_title_chars: int = 18, max_body_chars: int = 120) -> dict:
    issues = []
    warnings = []
    title = (card.get("title") or "").strip()
    body = (card.get("body") or "").strip()

    if not title:
        issues.append("empty_title")
    if not body:
        warnings.append("empty_body")
    if len(title) > max_title_chars:
        issues.append("title_too_long")
    if len(body) > max_body_chars:
        issues.append("body_too_long")

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
    }
