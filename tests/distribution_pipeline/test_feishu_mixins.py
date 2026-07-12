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
from feishu._records import RecordMixin  # noqa: E402
from feishu._sync import SyncMixin  # noqa: E402

# ---------------------------------------------------------------------------
# Tiny test-only subclass that composes the mixins without __init__
# touching the real network. We bypass FeishuService.__init__'s network
# setup by overriding the parts that require config.
# ---------------------------------------------------------------------------


class _BareFeishu(FieldMixin, RecordMixin, SyncMixin):
    """Stand-in host for testing :class:`FieldMixin` + :class:`SyncMixin`.

    Mixin-derived test class that skips :class:`FeishuService.__init__`
    (which would call ``load_feishu_config`` + create a real HTTP session)
    and provisions only the attributes the tested methods need
    (``field_aliases``, ``config``).

    Tests can still monkeypatch any method they like (``get_table_fields``,
    ``upload_image``) — :class:`monkeypatch.setattr` on an instance attribute
    shadows whatever would be inherited.

    :class:`RecordMixin` is mixed in so tests can ``monkeypatch.setattr``
    :meth:`create_record` / :meth:`update_record` / :meth:`upload_image`
    on the instance without ``AttributeError`` from the test harness.
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
        # available_fields = {} means no internal keys map. Keys with no
        # matching alias MUST be skipped — falling back to the raw key
        # would cause Feishu to reject the whole record with
        # ``FieldNameNotFound`` (see regression test below).
        out = host._map_to_fields(
            {"title": "Hello", "cover_path": "/tmp/x.jpg"},
            available_fields={},
        )
        assert out == {}

    def test_skips_export_only_fields(self):
        """Export-only fields (``cover_path``, ``folder_path``,
        ``word_count``, ``exported_at``) must never appear on the Bitable
        payload — they live in ``content_export.json`` for downstream
        consumers but Feishu has no column for them.
        """
        host = self._service()
        live_schema = {
            "标题": "text",
            "正文": "text",
            "标签": "multi_select",
            "平台": "text",
            "封面": "attachment",
        }
        out = host._map_to_fields(
            {
                "title": "Hello",
                "rewritten": "body",
                "tags": ["A", "B"],
                "platform": "xiaoyuzhou",
                # Export-only noise — must be filtered:
                "cover_path": "/tmp/cover.jpg",
                "folder_path": "content_archive/x/y/",
                "word_count": 4193,
                "exported_at": "2026-07-12T19:26:46",
                "summary": "## short summary",
                "book_list": "| book | author |",
            },
            available_fields=live_schema,
        )
        # All legitimate fields land on the payload…
        assert set(out.keys()) == {"标题", "正文", "标签", "平台"}
        # …and none of the export-only fields leak through.
        for forbidden in (
            "cover_path",
            "folder_path",
            "word_count",
            "exported_at",
            "summary",
            "book_list",
        ):
            assert forbidden not in out, f"{forbidden!r} leaked into payload: {out}"

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


# ---------------------------------------------------------------------------
# Auto-publish default + frontend refresh behaviour
# ---------------------------------------------------------------------------


class TestAutoPublishDefault:
    """New records should default to ``published=True`` so the frontend
    shows freshly-synced articles immediately, but operators can opt out
    via env var or per-record override.

    These tests pin down the contract added to ``sync_from_export``:

    * Default behaviour (``CHORA_FEISHU_AUTO_PUBLISH`` unset or truthy)
      injects ``item["published"] = True`` for **new** records only —
      existing records still preserve their current flag.
    * Setting ``CHORA_FEISHU_AUTO_PUBLISH=false`` skips the injection.
    * A per-record ``item["published"]`` (even falsy) is respected and
      not overwritten.
    """

    def _host(self, available=None):
        host = _BareFeishu()
        host.get_table_fields = lambda: available or {
            "标题": "text",
            "记录ID": "text",
            "正文": "text",
            "是否发布": "checkbox",
        }
        host.list_records = lambda page_size=500: []  # no existing records
        host.upload_image = lambda path: "fake-token"
        return host

    def _capture_create(self, host, monkeypatch, tmp_path):
        """Patch ``create_record`` to capture the item it receives."""
        captured = {}

        def fake_create(item, available_fields=None, file_token=None):
            captured["item"] = dict(item)
            captured["file_token"] = file_token
            return "fake-record-id"

        monkeypatch.setattr(host, "create_record", fake_create)
        return captured

    def test_default_injects_published_true(self, monkeypatch, tmp_path):
        from feishu._sync import SyncMixin

        export_file = tmp_path / "export.json"
        export_file.write_text(
            '[{"id": "new-1", "title": "午后偏见045", "rewritten": "body", '
            '"cover_path": "", "tags": ["tag"], "publish_date": "2026-05-26", '
            '"quotes": []}]',
            encoding="utf-8",
        )
        host = self._host()
        captured = self._capture_create(host, monkeypatch, tmp_path)

        # CHORA_FEISHU_AUTO_PUBLISH unset → default True
        monkeypatch.delenv("CHORA_FEISHU_AUTO_PUBLISH", raising=False)
        # Don't actually re-run generate_frontend_data.py in the test.
        monkeypatch.setenv("CHORA_FEISHU_REGENERATE_FRONTEND", "false")

        SyncMixin.sync_from_export(host, export_path=str(export_file))

        assert "item" in captured, "create_record was never called"
        assert (
            captured["item"].get("published") is True
        ), f"expected published=True, got {captured['item'].get('published')!r}"

    def test_env_var_disables_auto_publish(self, monkeypatch, tmp_path):
        from feishu._sync import SyncMixin

        export_file = tmp_path / "export.json"
        export_file.write_text(
            '[{"id": "new-2", "title": "Draft article", "rewritten": "body", '
            '"tags": ["tag"], "publish_date": "2026-05-26", "quotes": []}]',
            encoding="utf-8",
        )
        host = self._host()
        captured = self._capture_create(host, monkeypatch, tmp_path)

        monkeypatch.setenv("CHORA_FEISHU_AUTO_PUBLISH", "false")
        monkeypatch.setenv("CHORA_FEISHU_REGENERATE_FRONTEND", "false")

        SyncMixin.sync_from_export(host, export_path=str(export_file))

        assert "item" in captured, "create_record was never called"
        assert (
            "published" not in captured["item"]
        ), f"expected published NOT to be set, got {captured['item'].get('published')!r}"

    def test_per_record_published_false_not_overwritten(self, monkeypatch, tmp_path):
        """Operator-supplied ``item["published"]=False`` must win."""
        from feishu._sync import SyncMixin

        export_file = tmp_path / "export.json"
        export_file.write_text(
            '[{"id": "new-3", "title": "Held-back article", "rewritten": "body", '
            '"tags": ["tag"], "publish_date": "2026-05-26", "quotes": [], '
            '"published": false}]',
            encoding="utf-8",
        )
        host = self._host()
        captured = self._capture_create(host, monkeypatch, tmp_path)

        monkeypatch.delenv("CHORA_FEISHU_AUTO_PUBLISH", raising=False)
        monkeypatch.setenv("CHORA_FEISHU_REGENERATE_FRONTEND", "false")

        SyncMixin.sync_from_export(host, export_path=str(export_file))

        assert (
            captured["item"].get("published") is False
        ), f"operator override lost: got {captured['item'].get('published')!r}"

    def test_published_alias_resolves_in_create_payload(self, monkeypatch, tmp_path):
        """End-to-end: a published item should appear in the Feishu POST body
        as ``{'是否发布': True}`` (checkbox formatted as bool)."""
        from feishu._sync import SyncMixin

        export_file = tmp_path / "export.json"
        export_file.write_text(
            '[{"id": "new-4", "title": "Alias check", "rewritten": "body", '
            '"tags": ["x"], "publish_date": "2026-05-26", "quotes": []}]',
            encoding="utf-8",
        )

        host = _BareFeishu()
        host.get_table_fields = lambda: {
            "标题": "text",
            "正文": "text",
            "标签": "multi_select",
            "发布时间": "date",
            "记录ID": "text",
            "是否发布": "checkbox",
        }
        host.list_records = lambda page_size=500: []
        host.upload_image = lambda path: None

        posted_payloads = []

        def fake_create(item, available_fields=None, file_token=None):
            # Mirror what _map_to_fields would do for the create call —
            # use the host itself since it has field_aliases provisioned.
            payload = host._map_to_fields(item, available_fields, file_token)
            posted_payloads.append(payload)
            return "fake-record-id"

        monkeypatch.setattr(host, "create_record", fake_create)
        monkeypatch.delenv("CHORA_FEISHU_AUTO_PUBLISH", raising=False)
        monkeypatch.setenv("CHORA_FEISHU_REGENERATE_FRONTEND", "false")

        SyncMixin.sync_from_export(host, export_path=str(export_file))

        assert posted_payloads, "create_record was never called"
        # The checkbox field should be formatted as a real bool.
        assert (
            posted_payloads[0].get("是否发布") is True
        ), f"expected checkbox True, got {posted_payloads[0].get('是否发布')!r}"


class TestFrontendRefreshTrigger:
    """``sync_from_export`` should call ``generate_frontend_data.py`` once
    after a successful sync (when anything changed). No-op when the
    operator sets ``CHORA_FEISHU_REGENERATE_FRONTEND=false``."""

    def test_refresh_called_when_records_changed(self, monkeypatch, tmp_path):
        from feishu import _sync

        export_file = tmp_path / "export.json"
        export_file.write_text(
            '[{"id": "r1", "title": "x", "rewritten": "y", "tags": [], '
            '"publish_date": "2026-05-26", "quotes": []}]',
            encoding="utf-8",
        )

        host = _BareFeishu()
        host.get_table_fields = lambda: {"标题": "text", "是否发布": "checkbox"}
        host.list_records = lambda page_size=500: []
        host.upload_image = lambda path: None
        host.create_record = lambda item, af=None, ft=None: "rid"

        calls = []
        monkeypatch.setattr(_sync, "_regenerate_frontend_data", lambda: calls.append(1))
        monkeypatch.delenv("CHORA_FEISHU_REGENERATE_FRONTEND", raising=False)

        _sync.SyncMixin.sync_from_export(host, export_path=str(export_file))

        assert calls == [1], f"expected exactly one frontend refresh call, got {calls}"

    def test_refresh_skipped_when_env_disabled(self, monkeypatch, tmp_path):
        from feishu import _sync

        export_file = tmp_path / "export.json"
        export_file.write_text(
            '[{"id": "r2", "title": "x", "rewritten": "y", "tags": [], '
            '"publish_date": "2026-05-26", "quotes": []}]',
            encoding="utf-8",
        )

        host = _BareFeishu()
        host.get_table_fields = lambda: {"标题": "text", "是否发布": "checkbox"}
        host.list_records = lambda page_size=500: []
        host.upload_image = lambda path: None
        host.create_record = lambda item, af=None, ft=None: "rid"

        calls = []
        monkeypatch.setattr(_sync, "_regenerate_frontend_data", lambda: calls.append(1))
        monkeypatch.setenv("CHORA_FEISHU_REGENERATE_FRONTEND", "false")

        _sync.SyncMixin.sync_from_export(host, export_path=str(export_file))

        assert calls == [], "frontend refresh should have been skipped"
