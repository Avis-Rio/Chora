"""High-level orchestration: completeness check + sync_from_export.

Implements the **same behaviour** as the legacy monolithic
``feishu_service.FeishuService.sync_from_export`` method, but on
top of the mixin decomposition.

Key behaviour preserved:

* Platform normalisation (e.g. ``youtube`` → ``YouTube``,
  ``xiaoyuzhou`` → ``小宇宙``) is applied inside :meth:`_map_to_fields`
  in :mod:`feishu._fields`, then we call that here.
* Existing cover file_tokens are reused — only the **missing** or
  force-updated covers are uploaded to Drive.
* Updates preserve the existing ``published`` flag by default.
* :data:`REQUIRED_FIELDS` matches the legacy list (``title``,
  ``rewritten``, ``cover``, ``tags``, ``publish_date``, ``id``,
  ``quotes``).
"""

import os
import json
import sys
from datetime import datetime


class SyncMixin:
    """is_record_complete + sync_from_export (the only public orchestration API)."""

    # Key fields that must have data for a record to be considered complete.
    # These are internal keys; they are resolved to actual Feishu field names
    # via field_aliases when checking completeness.
    REQUIRED_FIELDS = ['title', 'rewritten', 'cover', 'tags', 'publish_date', 'id', 'quotes']

    def is_record_complete(self, record):
        """Check if a record has all required fields filled.

        Uses field aliases to tolerate schema renames.
        Returns tuple: (is_complete, missing_fields)
        """
        fields = record.get('fields', {})
        missing = []

        available_fields = self.get_table_fields()

        for internal_key in self.REQUIRED_FIELDS:
            field_name = self._resolve_field_name(internal_key, available_fields)[0]
            if not field_name:
                # Cannot resolve field; assume schema missing this concept
                continue
            value = fields.get(field_name)

            # Check if field is empty (None / blank string / empty list).
            if value is None:
                missing.append(field_name)
            elif isinstance(value, str) and not value.strip():
                missing.append(field_name)
            elif isinstance(value, list) and len(value) == 0:
                missing.append(field_name)

        return (len(missing) == 0, missing)

    def sync_from_export(self, export_path='content_export.json', force=False):
        """Sync all content from export JSON to Feishu.

        Intelligent sync logic:
        - Complete records: Skip (unless force=True)
        - Incomplete records: Update to fill missing fields
        - New records: Create with all data

        Args:
            export_path: Path to exported JSON file
            force: If True, update all records regardless of completeness
        """
        if not os.path.exists(export_path):
            print(f"❌ Export file not found: {export_path}")
            return

        with open(export_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        # Get available fields from the table
        print("🔍 Checking table fields...")
        available_fields = self.get_table_fields()
        if available_fields:
            print(f"   Found fields: {', '.join(available_fields.keys())}")
        else:
            print("   ⚠️ Could not get field list, will try all fields")

        # Check if cover field exists
        cover_field = self._resolve_field_name('cover', available_fields)[0]
        has_cover_field = bool(cover_field)

        # Pre-fetch all records for efficiency
        print("📥 Fetching existing records...")
        all_records = self.list_records(page_size=500)
        records_by_id = {}
        id_field = self._resolve_field_name('id', available_fields)[0] or '记录ID'
        for record in all_records:
            content_id = record.get('fields', {}).get(id_field)
            if content_id:
                records_by_id[content_id] = record
        print(f"   Found {len(records_by_id)} existing records")

        print(f"\n📦 Processing {len(items)} items...")

        created = 0
        updated = 0
        skipped = 0
        failed = 0

        for item in items:
            content_id = item.get('id')
            title = item.get('title', 'Unknown')[:35]

            try:
                existing = records_by_id.get(content_id)

                if existing:
                    # Check if record is complete
                    is_complete, missing_fields = self.is_record_complete(existing)

                    if is_complete and not force:
                        # Record is complete, skip
                        print(f"⏭️  Skip (complete): {title}...")
                        skipped += 1
                        continue

                    # Record is incomplete or force update
                    if missing_fields:
                        print(f"\n🔧 Updating (missing: {', '.join(missing_fields)}): {title}...")
                    else:
                        print(f"\n🔄 Force update: {title}...")

                    # Upload cover if missing or force-update. Otherwise reuse
                    # the existing file_token so we don't upload the same image twice.
                    file_token = None
                    cover_path = item.get('cover_path')
                    needs_cover = (cover_field in missing_fields) or force

                    if cover_path and os.path.exists(cover_path) and has_cover_field and needs_cover:
                        file_token = self.upload_image(cover_path)
                    elif not needs_cover and cover_field and cover_field in existing.get('fields', {}):
                        cover_obj = existing['fields'][cover_field]
                        if cover_obj and isinstance(cover_obj, list) and len(cover_obj) > 0:
                            file_token = cover_obj[0].get('file_token')

                    # Preserve existing publish status; default True for new records.
                    published_field = self._resolve_field_name('published', available_fields)[0]
                    if published_field and published_field in existing.get('fields', {}):
                        item['published'] = existing['fields'][published_field]

                    record_id = existing.get('record_id')
                    if self.update_record(record_id, item, available_fields, file_token):
                        updated += 1
                    else:
                        failed += 1
                else:
                    # New record — create with all data
                    print(f"\n➕ Creating: {title}...")

                    file_token = None
                    cover_path = item.get('cover_path')
                    if cover_path and os.path.exists(cover_path) and has_cover_field:
                        file_token = self.upload_image(cover_path)

                    if self.create_record(item, available_fields, file_token):
                        created += 1
                    else:
                        failed += 1

            except Exception as e:
                print(f"❌ Error processing {title}: {e}")
                failed += 1

        print(f"\n{'=' * 50}")
        print(f"✅ Sync complete:")
        print(f"   ➕ Created: {created}")
        print(f"   🔧 Updated: {updated}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"   ❌ Failed: {failed}")
