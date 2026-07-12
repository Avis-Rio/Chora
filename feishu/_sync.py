"""High-level orchestration: completeness check + sync_from_export."""

import os
import json
import sys
from datetime import datetime


class SyncMixin:
    """is_record_complete + sync_from_export (the only public orchestration API)."""

    REQUIRED_KEYS = ('title', 'rewritten', 'source_url')

    def is_record_complete(self, record):
        """Return (is_complete, missing_field_names)."""
        fields = record.get('fields', {})
        missing = []
        for internal_key in self.REQUIRED_KEYS:
            resolved_name, _ = self._resolve_field_name(internal_key, {'placeholder': 'text'})
            # When the table has no placeholder column, fall back to known names.
            if not resolved_name:
                # Best-effort: try the first alias for each key directly.
                first_alias = self.field_aliases.get(internal_key, [internal_key])[0]
                resolved_name = first_alias
            if not fields.get(resolved_name):
                missing.append(internal_key)
        return (len(missing) == 0), missing

    def sync_from_export(self, export_path='content_export.json', force=False):
        """Sync content_export.json records to the Bitable.

        Args:
            export_path: path to the JSON export (default content_export.json).
            force: when True, update even complete records.
        """
        if not os.path.exists(export_path):
            print(f"❌ Export file not found: {export_path}")
            return

        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)

        if not isinstance(export_data, list):
            print("❌ Export file should be a list of records")
            return

        print(f"📦 Loaded {len(export_data)} records from {export_path}")

        # Discover live schema once.
        available_fields = self.get_table_fields()
        if not available_fields:
            print("⚠️  Could not load live schema; writing will likely fail.")

        # Pre-fetch existing records for idempotent upsert.
        existing_by_id = {}
        for record in self.list_records(page_size=500):
            fields = record.get('fields', {})
            _, id_alias = self._resolve_field_name('id', available_fields)
            id_key = id_alias or '记录ID'
            cid = fields.get(id_key)
            if cid:
                existing_by_id[cid] = record

        created = 0
        updated = 0
        skipped = 0
        failed = 0

        for entry in export_data:
            title = entry.get('title', '<no title>')[:35]
            try:
                # Translate internal keys to Feishu columns and format values.
                record_payload = {
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'channel': entry.get('channel'),
                    'rewritten': entry.get('rewritten') or entry.get('summary'),
                    'guests': entry.get('guests'),
                    'quotes': entry.get('quotes'),
                    'transcript': entry.get('transcript'),
                    'reading_time': entry.get('reading_time'),
                    'score': entry.get('score'),
                    'source_url': entry.get('source_url'),
                    'publish_date': entry.get('publish_date'),
                    'platform': entry.get('platform'),
                    'tags': entry.get('tags'),
                    'cover': entry.get('cover_path'),
                    'published': entry.get('published', True),
                }
                # Trim empty values to avoid junk keys.
                record_payload = {k: v for k, v in record_payload.items() if v not in (None, '', [])}

                cover_path = entry.get('cover_path')
                file_token = None
                if cover_path and os.path.exists(cover_path):
                    file_token = self.upload_image(cover_path)

                existing = existing_by_id.get(entry.get('id'))
                if existing and not force:
                    is_complete, missing = self.is_record_complete(existing)
                    if is_complete:
                        print(f"   ⏭️  Skipping (complete): {title}")
                        skipped += 1
                        continue
                    record_id = existing.get('record_id')
                    result = self.update_record(record_id, record_payload, available_fields, file_token)
                    if result:
                        updated += 1
                        print(f"   🔧 Updated: {title}")
                    else:
                        failed += 1
                else:
                    result = self.create_record(record_payload, available_fields, file_token)
                    if result:
                        created += 1
                        print(f"   ➕ Created: {title}")
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
