"""Field-alias resolution + value-formatting for the Feishu service.

Owns:

* :attr:`DEFAULT_FIELD_ALIASES` — internal-key → Feishu column name candidates.
* :meth:`_resolve_field_name` — picks the live alias present in the table.
* :meth:`_format_field_value` — converts Python values to Feishu's wire format.
* :meth:`_feishu_type_to_internal` — Feishu numeric type → internal name.
* :meth:`_map_to_fields` — full payload assembly (alias match + value format).

The alias strategy is **first-match-wins**: aliases are iterated strictly
left-to-right, and the *first* alias that exists in the live Bitable
schema wins. Operators may add new alias variants to the *end* of an
alias list to roll forward without breaking downstream tables.
"""


class FieldMixin:
    """Field-alias map plus per-field value formatters."""

    # Default field name aliases for resilient schema mapping.
    #
    # Each internal key maps to one or more Feishu column names to try in
    # ``DEFAULT_FIELD_ALIASES`` order. Resolution behaviour:
    #
    #   1. The aliases list is iterated strictly left-to-right.
    #   2. The **first alias that exists** in the live Bitable schema wins.
    #   3. Remaining aliases are not consulted.
    #
    # This guarantees deterministic behaviour even when several aliases
    # coexist in the live table. Operators add new alias variants here as
    # new schemas are encountered; do **not** drop earlier aliases silently,
    # since down-stream tables may still rely on them.
    DEFAULT_FIELD_ALIASES = {
        "title": ["标题", "Title"],
        "id": ["记录ID", "ID", "内容ID"],
        "channel": ["频道", "Channel", "来源频道"],
        # Primary is "正文" (full rewrite). "摘要" is the AI summary;
        # "内容" is the legacy column kept for backwards compatibility.
        "rewritten": ["正文", "摘要", "内容"],
        "guests": ["嘉宾", "Guests", "主讲人"],
        "quotes": ["金句渲染", "金句", "Quotes", "Highlight"],
        "transcript": ["原文逐字稿", "Transcript", "逐字稿"],
        "reading_time": ["阅读时长", "Reading Time", "预计阅读"],
        "score": ["评分", "Score", "Rating"],
        "source_url": ["原始链接", "Source URL", "原文链接", "链接"],
        "cover": ["封面", "Cover", "配图"],
        "publish_date": ["发布时间", "Publish Date", "日期", "发布日期"],
        "platform": ["平台", "Platform", "来源平台"],
        "tags": ["标签", "Tags", "Tag"],
        "published": ["是否发布", "Published", "发布"],
    }

    def _resolve_field_name(self, internal_key, available_fields):
        """Map an internal field key to the actual Feishu field name.

        available_fields can be a dict (name -> type) or a set/list of names.
        Returns (resolved_name, field_type) or (None, None).
        """
        if available_fields is None:
            available_fields = {}
        names = (
            set(available_fields.keys())
            if isinstance(available_fields, dict)
            else set(available_fields or [])
        )
        aliases = self.field_aliases.get(internal_key, [internal_key])
        for alias in aliases:
            if alias in names:
                field_type = (
                    available_fields.get(alias, "text") if isinstance(available_fields, dict) else "text"
                )
                return alias, field_type
        return None, None

    # ------------------------------------------------------------------
    # Value formatting
    # ------------------------------------------------------------------

    def _format_field_value(self, value, field_type):
        """Format a Python value according to Feishu Bitable field type.

        Feishu Bitable expects:
        - SingleSelect: plain option name string
        - MultiSelect: list of option name strings
        - Url: {'link': ..., 'text': ...} dict
        - Attachment: [{'file_token': ...}] list (only file_token accepted here)
        - Date: ms-since-epoch int OR ISO-8601 string
        - Checkbox: bool
        - Number: int/float
        - Text: str
        """
        if value is None or value == "":
            return None

        if field_type == "multi_select":
            if isinstance(value, list):
                return [str(v) for v in value]
            return [str(value)]

        if field_type == "single_select":
            return str(value)

        if field_type == "url":
            if isinstance(value, dict):
                return value
            return {"link": str(value), "text": str(value)}

        if field_type == "attachment":
            tokens = value if isinstance(value, list) else [value]
            return [{"file_token": str(t)} for t in tokens if t]

        if field_type == "date":
            if isinstance(value, (int, float)):
                # Already ms-since-epoch.
                return int(value)
            if isinstance(value, str):
                # Try parsing as ISO date.
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except Exception:
                    return value  # Pass through; Feishu may still parse it.
            return value

        if field_type == "checkbox":
            return bool(value)

        if field_type == "number":
            return float(value) if not isinstance(value, (int, float)) else value

        # Default: text
        return str(value)

    # ------------------------------------------------------------------
    # Full payload assembly
    # ------------------------------------------------------------------

    def _map_to_fields(self, data, available_fields=None, file_token=None):
        """Map internal-keyed data dict to Feishu field name + format.

        Also applies a small ``platform`` normalisation table so callers can
        pass the lowercase internal platform identifier (``youtube``,
        ``xiaoyuzhou``) and have it stored as the human-readable label
        (``YouTube``, ``小宇宙``) the operator expects in the Bitable.

        Args:
            data: dict with internal keys (``title``, ``rewritten``, ...).
            available_fields: live schema dict (name -> internal_type) or None.
            file_token: optional attachment token to insert into cover field.

        Returns:
            dict ready to POST/PUT as Feishu ``fields`` payload, or ``{}``
            if nothing was mapped.
        """
        if available_fields is None:
            available_fields = self.get_table_fields()

        # Local copy so we never mutate caller's dict.
        candidates = dict(data)

        # Platform name mapping: lowercase internal → displayed label.
        platform_map = {"youtube": "YouTube", "xiaoyuzhou": "小宇宙"}
        if candidates.get("platform"):
            candidates["platform"] = platform_map.get(candidates["platform"], candidates["platform"])

        mapped = {}
        for internal_key, raw_value in candidates.items():
            if raw_value is None or raw_value == "":
                continue
            field_name, field_type = self._resolve_field_name(internal_key, available_fields)
            if not field_name:
                # If no schema metadata, fall back to the first alias so the
                # caller can still attempt a write (useful for dry runs/tests).
                aliases = self.field_aliases.get(internal_key, [internal_key])
                field_name = aliases[0]
                field_type = "text"

            # Cover gets replaced by file_token only when caller explicitly
            # provides one — otherwise we pass the raw ``cover_path`` value.
            if internal_key == "cover" and file_token:
                raw_value = file_token

            formatted = self._format_field_value(raw_value, field_type)
            if formatted is not None:
                mapped[field_name] = formatted

        return mapped
