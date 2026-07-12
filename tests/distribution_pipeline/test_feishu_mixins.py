"""Unit tests for the mixin decomposition of ``feishu_service.py``.

These tests cover the conversion / orchestration logic that has no
external dependencies and is the highest-risk surface after splitting
the monolithic class into mixins. They run without any Feishu API
credentials and without network access.

Goals:

* Lock the behaviour of :class:`feishu._fields.FieldMixin` (alias
  resolution first-match-wins, value formatting per type, platform
  normalisation, cover-token injection).
* Lock the behaviour of :class:`feishu._sync.SyncMixin` completeness
  detection (None / blank string / empty list).
* Catch regressions if anyone reorders or removes mixins.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure repo root is on path so `import feishu` works.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from feishu._fields import FieldMixin  # noqa: E402
from feishu._sync import SyncMixin  # noqa: E402

# ---------------------------------------------------------------------------
# Tiny test-only subclass that composes the mixins without __init__
# touching the real network. We bypass FeishuService.__init__'s network
# setup by overriding the parts that require config.
# ---------------------------------------------------------------------------


class _BareFeishu(FieldMixin, SyncMixin):
    """Stand-in host for testing :class:`FieldMixin` + :class:`SyncMixin`.

    Mixin-derived test class that skips :class:`FeishuService.__init__`
    (which would call ``load_feishu_config`` + create a real HTTP session)
    and provisions only the attributes the tested methods need
    (``field_aliases``, ``config``).

    Tests can still monkeypatch any method they like (``get_table_fields``,
    ``upload_image``) — :class:`monkeypatch.setattr` on an instance attribute
    shadows whatever would be inherited.
    """

    def __init__(self):
        # Provision attributes read by the tested methods.
        self.DEFAULT_FIELD_ALIASES = FieldMixin.DEFAULT_FIELD_ALIASES
        self.field_aliases = dict(FieldMixin.DEFAULT_FIELD_ALIASES)
        self.config = {}
        # Stub for SyncMixin.is_record_complete which calls
        # self.get_table_fields(). Tests override this with monkeypatch
        # or by direct assignment.
        self.get_table_fields = lambda: {}
        # Deliberately do NOT set ``access_token`` / ``session`` /
        # ``token_expires`` — tests that touch auth paths patch those.


# ---------------------------------------------------------------------------
# _resolve_field_name
# ---------------------------------------------------------------------------


class TestResolveFieldName:
    def test_first_alias_hit_wins(self):
        host = _BareFeishu()
        # "title" aliases: ["标题", "Title"] — both candidates exist.
        # First alias "标题" should win, even though "Title" is also present.
        available = {"标题": "text", "Title": "text", "频道": "text"}
        name, ftype = host._resolve_field_name("title", available)
        assert name == "标题"
        assert ftype == "text"

    def test_skips_missing_aliases_until_one_exists(self):
        host = _BareFeishu()
        # Only the second alias "Title" exists in the live schema.
        available = {"Title": "text"}
        name, ftype = host._resolve_field_name("title", available)
        assert name == "Title"

    def test_returns_none_for_unknown_field(self):
        host = _BareFeishu()
        # "id" first alias is "记录ID", which is not in the supplied schema.
        # Lookups for "id" only succeed when one of the IDs is present.
        available = {"频道": "text"}
        name, ftype = host._resolve_field_name("id", available)
        # All id-aliases are missing, so we get (None, None).
        assert name is None and ftype is None


# ---------------------------------------------------------------------------
# _format_field_value
# ---------------------------------------------------------------------------


class TestFormatFieldValue:
    @pytest.mark.parametrize("value", [None, ""])
    def test_empty_inputs_return_none(self, value):
        host = _BareFeishu()
        assert host._format_field_value(value, "text") is None

    def test_multi_select_wraps_scalar_in_list(self):
        host = _BareFeishu()
        assert host._format_field_value("AI", "multi_select") == ["AI"]
        assert host._format_field_value(["AI", "Chora"], "multi_select") == ["AI", "Chora"]

    def test_single_select_is_plain_string(self):
        host = _BareFeishu()
        assert host._format_field_value("YouTube", "single_select") == "YouTube"

    def test_url_field_becomes_dict(self):
        host = _BareFeishu()
        out = host._format_field_value("https://x.com/a", "url")
        assert out == {"link": "https://x.com/a", "text": "https://x.com/a"}

    def test_url_field_preserves_existing_dict(self):
        host = _BareFeishu()
        # Custom link/text should pass through.
        out = host._format_field_value({"link": "https://x.com/a", "text": "X"}, "url")
        assert out == {"link": "https://x.com/a", "text": "X"}

    def test_attachment_wraps_file_token(self):
        host = _BareFeishu()
        assert host._format_field_value("tok123", "attachment") == [{"file_token": "tok123"}]

    def test_attachment_passes_through_list(self):
        host = _BareFeishu()
        assert host._format_field_value(["t1", "t2"], "attachment") == [
            {"file_token": "t1"},
            {"file_token": "t2"},
        ]

    def test_date_passthrough_for_int(self):
        host = _BareFeishu()
        assert host._format_field_value(1234567890000, "date") == 1234567890000

    def test_date_parses_iso_string(self):
        host = _BareFeishu()
        out = host._format_field_value("2026-05-13T00:00:00", "date")
        assert isinstance(out, int)

    def test_checkbox_is_bool(self):
        host = _BareFeishu()
        assert host._format_field_value(1, "checkbox") is True
        assert host._format_field_value(0, "checkbox") is False
        assert host._format_field_value("yes", "checkbox") is True

    def test_number_passes_through_int_float(self):
        host = _BareFeishu()
        assert host._format_field_value(7, "number") == 7
        assert host._format_field_value(3.14, "number") == 3.14

    def test_text_str_casts_everything(self):
        host = _BareFeishu()
        assert host._format_field_value(42, "text") == "42"
        assert host._format_field_value("hello", "text") == "hello"


# ---------------------------------------------------------------------------
# _map_to_fields — alias + platform_map + cover-token injection
# ---------------------------------------------------------------------------


class TestMapToFields:
    def _service(self):
        host = _BareFeishu()
        host.field_aliases = dict(host.DEFAULT_FIELD_ALIASES)
        return host

    def test_skips_internal_keys_not_in_schema(self):
        host = self._service()
        # available_fields = {} means no internal keys map. The legacy
        # fallback (first alias as 'text') is honoured for each key so we
        # can at least attempt a write — useful for dry runs and dry tests.
        out = host._map_to_fields({"title": "Hello"}, available_fields={})
        assert "标题" in out  # first alias used as fallback name
        assert out["标题"] == "Hello"

    def test_uses_resolved_field_name_when_present(self):
        host = self._service()
        out = host._map_to_fields({"title": "Hi"}, available_fields={"标题": "text"})
        assert out == {"标题": "Hi"}

    def test_platform_normalisation(self):
        host = self._service()
        fields = {"平台": "text"}
        out = host._map_to_fields({"platform": "youtube"}, available_fields=fields)
        assert out == {"平台": "YouTube"}
        out = host._map_to_fields({"platform": "xiaoyuzhou"}, available_fields=fields)
        assert out == {"平台": "小宇宙"}

    def test_platform_passthrough_when_already_human_readable(self):
        host = self._service()
        out = host._map_to_fields({"platform": "Apple Podcasts"}, available_fields={"平台": "text"})
        assert out == {"平台": "Apple Podcasts"}

    def test_cover_replaced_by_file_token_when_provided(self):
        host = self._service()
        out = host._map_to_fields(
            {"cover": "/some/local/path.jpg"},
            available_fields={"封面": "attachment"},
            file_token="tok_xyz",
        )
        # file_token wins, formatting wraps in attachment dict.
        assert out == {"封面": [{"file_token": "tok_xyz"}]}

    def test_cover_path_passthrough_when_no_file_token(self):
        host = self._service()
        out = host._map_to_fields(
            {"cover": "/some/local/path.jpg"},
            available_fields={"封面": "attachment"},
        )
        # No file_token — value stays as-is; formatter stringifies to one element.
        assert out == {"封面": [{"file_token": "/some/local/path.jpg"}]}

    def test_skips_empty_values(self):
        host = self._service()
        out = host._map_to_fields(
            {"title": "", "rewritten": None, "tags": ["keep"]},
            available_fields={"标题": "text", "正文": "text", "标签": "multi_select"},
        )
        # Empty / None values must be dropped from the payload.
        assert "标题" not in out
        assert "正文" not in out
        assert out.get("标签") == ["keep"]


# ---------------------------------------------------------------------------
# is_record_complete
# ---------------------------------------------------------------------------


class TestIsRecordComplete:
    REQUIRED_KEYS = ("title", "rewritten", "cover", "tags", "publish_date", "id", "quotes")

    def _record(self, **fields):
        # Build a record whose Feishu schema aliases all map to themselves.
        return {"fields": fields}

    def _available(self):
        # Live schema using the legacy first-alias name for each key.
        return {
            "标题": "text",
            "正文": "text",
            "封面": "attachment",
            "标签": "multi_select",
            "发布时间": "date",
            "记录ID": "text",
            "金句": "text",
        }

    def _host(self):
        host = _BareFeishu()
        host.get_table_fields = lambda: self._available()
        return host

    def test_complete_record_reports_no_missing(self):
        host = self._host()
        record = self._record(
            标题="Hi",
            正文="Long rewrite body",
            封面=[{"file_token": "t"}],
            标签=["tag1"],
            发布时间=1234567890000,
            记录ID="rec-1",
            金句=["quote"],
        )
        is_complete, missing = host.is_record_complete(record)
        assert is_complete is True
        assert missing == []

    def test_blank_string_field_marked_missing(self):
        host = self._host()
        record = self._record(标题="", 正文="Long body")
        is_complete, missing = host.is_record_complete(record)
        assert is_complete is False
        assert "标题" in missing

    def test_none_field_marked_missing(self):
        host = self._host()
        record = self._record(标题="Hi", 正文=None)
        is_complete, missing = host.is_record_complete(record)
        assert is_complete is False
        assert "正文" in missing

    def test_empty_list_field_marked_missing(self):
        host = self._host()
        record = self._record(标题="Hi", 正文="body", 标签=[])
        is_complete, missing = host.is_record_complete(record)
        assert is_complete is False
        assert "标签" in missing


# ---------------------------------------------------------------------------
# DEFAULT_FIELD_ALIASES invariant
# ---------------------------------------------------------------------------


class TestDefaultAliases:
    """Lock down the structure of DEFAULT_FIELD_ALIASES so unexpected
    schema changes are caught at test time rather than at runtime."""

    def test_required_internal_keys_present(self):
        from feishu._fields import FieldMixin

        required = {"title", "id", "rewritten", "cover", "tags", "publish_date", "platform"}
        assert required.issubset(FieldMixin.DEFAULT_FIELD_ALIASES.keys())

    def test_alias_lists_are_non_empty_strings(self):
        from feishu._fields import FieldMixin

        for internal_key, aliases in FieldMixin.DEFAULT_FIELD_ALIASES.items():
            assert aliases, f"{internal_key} has empty alias list"
            for alias in aliases:
                assert isinstance(alias, str), f"{internal_key} contains non-string alias: {alias!r}"
                assert alias, f"{internal_key} contains empty alias string"
