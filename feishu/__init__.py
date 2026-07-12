"""Feishu (Lark) Bitable API client.

This package replaces the monolithic ``feishu_service.py``. The public
API is unchanged: instantiating ``FeishuService()`` and calling
``.sync_from_export()`` works exactly as before.

Submodules split responsibilities by concern:

* ``_client``  — HTTP session, retry policy, request plumbing.
* ``_auth``    — tenant access token lifecycle.
* ``_fields``  — DEFAULT_FIELD_ALIASES and per-type value formatters.
* ``_records`` — record CRUD against the Bitable API.
* ``_uploads`` — Drive media uploads (used for cover attachments).
* ``_sync``    — high-level orchestration (sync_from_export, completeness check).

The :class:`FeishuService` class below composes all of them via mixins.
"""

from ._client import ClientMixin
from ._auth import AuthMixin
from ._fields import FieldMixin
from ._records import RecordMixin
from ._uploads import UploadMixin
from ._sync import SyncMixin


class FeishuService(ClientMixin, AuthMixin, FieldMixin, RecordMixin, UploadMixin, SyncMixin):
    """Feishu Bitable API wrapper.

    Composition of mixin classes — each one owns a single concern and
    can be tested or replaced in isolation. The public API is identical
    to the legacy monolithic ``feishu_service.FeishuService`` class.
    """


__all__ = ["FeishuService"]
