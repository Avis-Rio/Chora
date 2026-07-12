#!/usr/bin/env python3
"""
Feishu (Lark) Bitable API Service for syncing content to multi-dimensional table.
Supports image upload for cover attachments.
"""

import os
import sys
import json
import requests
import time
import mimetypes
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config_loader import load_feishu_config

class FeishuService:
    """Feishu Bitable API wrapper."""
    
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

    def __init__(self, config_path='config/feishu.yaml'):
        """Initialize with config file."""
        self.config = load_feishu_config(config_path)
        if self.config is None:
            self.config = {}
        self.access_token = None
        self.token_expires = 0

        # Field aliases can be overridden in config
        aliases = self.config.get('field_aliases', {})
        self.field_aliases = {**self.DEFAULT_FIELD_ALIASES, **aliases}

        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _request(self, method, url, **kwargs):
        """Wrapper for requests with error handling."""
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            return response
        except Exception as e:
            print(f"⚠️ Request failed: {e}")
            raise
    
    def get_access_token(self):
        """Get tenant access token from Feishu API."""
        if self.access_token and datetime.now().timestamp() < self.token_expires:
            return self.access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}

        feishu_cfg = self.config.get('feishu', self.config)
        data = {
            "app_id": feishu_cfg.get('app_id'),
            "app_secret": feishu_cfg.get('app_secret'),
        }

        try:
            response = self._request("POST", url, headers=headers, json=data)
            result = response.json()

            if result.get('code') == 0:
                self.access_token = result.get('tenant_access_token')
                self.token_expires = datetime.now().timestamp() + result.get('expire', 7200) - 60
                return self.access_token
            else:
                print(f"❌ Failed to get access token: {result}")
                return None
        except Exception as exc:
            print(f"❌ Exception getting access token: {exc}")
            return None
    
    def _headers(self):
        """Get request headers with auth token."""
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def _auth_header(self):
        """Get auth header only (for multipart requests)."""
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {"Authorization": f"Bearer {token}"}
    
    def _base_url(self):
        """Get base URL for bitable API."""
        feishu_cfg = self.config.get('feishu', self.config)
        base_id = feishu_cfg.get('base_id')
        table_id = feishu_cfg.get('table_id')
        return f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}"
    
    def list_records(self, page_size=100):
        """List all records in the table."""
        url = f"{self._base_url()}/records"
        params = {"page_size": page_size}
        
        try:
            response = self._request("GET", url, headers=self._headers(), params=params)
            result = response.json()
            
            if result.get('code') == 0:
                return result.get('data', {}).get('items', [])
            else:
                print(f"❌ Failed to list records: {result}")
                return []
        except:
            return []
    
    def find_by_id(self, content_id):
        """Find a record by content ID using field aliases."""
        records = self.list_records()
        id_field = self._resolve_field_name('id', self.get_table_fields())[0] or '记录ID'
        for record in records:
            fields = record.get('fields', {})
            if fields.get(id_field) == content_id:
                return record
        return None
    
    def create_record(self, data, available_fields=None, file_token=None):
        """Create a new record."""
        url = f"{self._base_url()}/records"
        
        fields = self._map_to_fields(data, available_fields, file_token)
        payload = {"fields": fields}
        
        try:
            response = self._request("POST", url, headers=self._headers(), json=payload)
            result = response.json()
            
            if result.get('code') == 0:
                record_id = result.get('data', {}).get('record', {}).get('record_id')
                print(f"✅ Created record: {data.get('title', 'Unknown')[:30]}...")
                return record_id
            else:
                print(f"❌ Failed to create record: {result.get('msg', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"❌ Error creating record: {e}")
            return None
    
    def update_record(self, record_id, data, available_fields=None, file_token=None):
        """Update an existing record."""
        url = f"{self._base_url()}/records/{record_id}"
        
        fields = self._map_to_fields(data, available_fields, file_token)
        payload = {"fields": fields}
        
        try:
            response = self._request("PUT", url, headers=self._headers(), json=payload)
            result = response.json()
            
            if result.get('code') == 0:
                print(f"✅ Updated record: {data.get('title', 'Unknown')[:30]}...")
                return True
            else:
                print(f"❌ Failed to update record: {result.get('msg', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Error updating record: {e}")
            return False
    
    def get_table_fields(self):
        """Get field metadata from the table.

        Returns a dict mapping field_name -> field_type (e.g. 'text', 'single_select').
        Falls back to field-name-only list if API shape is unexpected.
        """
        feishu_cfg = self.config.get('feishu', self.config)
        base_id = feishu_cfg.get('base_id')
        table_id = feishu_cfg.get('table_id')
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/fields"

        try:
            response = self._request("GET", url, headers=self._headers())
            result = response.json()

            if result.get('code') == 0:
                items = result.get('data', {}).get('items', [])
                return {
                    f.get('field_name'): self._feishu_type_to_internal(f.get('type'))
                    for f in items
                    if f.get('field_name')
                }
            else:
                print(f"⚠️ Failed to get fields: {result}")
                return {}
        except Exception as e:
            print(f"⚠️ Error getting fields: {e}")
            return {}

    @staticmethod
    def _feishu_type_to_internal(type_value):
        """Map Feishu Bitable numeric/string type to internal type name."""
        mapping = {
            1: 'text',
            2: 'number',
            3: 'single_select',
            4: 'multi_select',
            5: 'date',
            7: 'checkbox',
            11: 'attachment',
            15: 'url',
        }
        if isinstance(type_value, int):
            return mapping.get(type_value, 'text')
        return str(type_value).lower() if type_value else 'text'
    
    def upload_image(self, image_path):
        """Upload image to Feishu Drive and return file_token.
        
        Uses the media upload API to upload file to Feishu,
        returns file_token that can be used in attachment fields.
        """
        if not os.path.exists(image_path):
            print(f"⚠️ Image not found: {image_path}")
            return None
        
        # Get file info
        file_name = os.path.basename(image_path)
        file_size = os.path.getsize(image_path)
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = 'image/jpeg'
        
        # Upload to Feishu media
        url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
        
        with open(image_path, 'rb') as f:
            files = {
                'file': (file_name, f, mime_type)
            }
            data = {
                'file_name': file_name,
                'parent_type': 'bitable_image',
                'parent_node': self.config.get('feishu', self.config).get('base_id'),
                'size': str(file_size)
            }
            
            try:
                response = self.session.post(
                    url,
                    headers=self._auth_header(),
                    files=files,
                    data=data,
                    timeout=60
                )
                result = response.json()
                
                if result.get('code') == 0:
                    file_token = result.get('data', {}).get('file_token')
                    print(f"   📷 Uploaded: {file_name[:30]}...")
                    return file_token
                else:
                    print(f"⚠️ Upload failed: {result.get('msg', 'Unknown error')}")
                    return None
            except Exception as e:
                print(f"⚠️ Upload error: {e}")
                return None
    
    def _resolve_field_name(self, internal_key, available_fields):
        """Map an internal field key to the actual Feishu field name.

        available_fields can be a dict (name -> type) or a set/list of names.
        Returns (resolved_name, field_type) or (None, None).
        """
        if available_fields is None:
            available_fields = {}
        names = set(available_fields.keys()) if isinstance(available_fields, dict) else set(available_fields or [])
        aliases = self.field_aliases.get(internal_key, [internal_key])
        for alias in aliases:
            if alias in names:
                field_type = available_fields.get(alias, 'text') if isinstance(available_fields, dict) else 'text'
                return alias, field_type
        return None, None

    def _format_field_value(self, value, field_type):
        """Format a Python value according to Feishu Bitable field type.

        Feishu Bitable expects:
        - SingleSelect: plain option name string
        - MultiSelect: list of option name strings
        - Url: {'link': ..., 'text': ...} dict
        - Attachment: list of {'file_token': ...} dicts
        """
        if value is None:
            return None

        field_type = (field_type or 'text').lower()

        if field_type == 'single_select':
            # Feishu expects a plain string of the option name.
            if isinstance(value, dict) and 'text' in value:
                return value['text']
            return str(value).strip()

        if field_type == 'multi_select':
            # Feishu expects a list of plain option name strings.
            if isinstance(value, list):
                out = []
                for item in value:
                    if isinstance(item, dict) and 'text' in item:
                        out.append(item['text'])
                    elif isinstance(item, str):
                        for part in item.split(','):
                            part = part.strip()
                            if part:
                                out.append(part)
                    else:
                        out.append(str(item))
                return out
            if isinstance(value, str):
                return [p.strip() for p in value.split(',') if p.strip()]
            return [str(value)]

        if field_type == 'checkbox':
            return bool(value)

        if field_type in ('url', 'link'):
            if isinstance(value, dict) and 'link' in value:
                return value
            url = str(value)
            return {'link': url, 'text': url[:50] or '链接'}

        if field_type == 'attachment':
            if isinstance(value, list):
                return value
            return [{'file_token': str(value)}]

        if field_type == 'number':
            try:
                return float(value)
            except Exception:
                return value

        if field_type in ('date', 'datetime'):
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # Try common date formats and return milliseconds timestamp
                for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S'):
                    try:
                        dt = datetime.strptime(value, fmt)
                        return int(dt.timestamp() * 1000)
                    except Exception:
                        continue
            return value

        # Default: text / multi-line text
        return value

    def _map_to_fields(self, data, available_fields=None, file_token=None):
        """Map export data to Feishu field format.

        Uses field metadata (when available) to format values for the correct
        Bitable field types, and resolves field names via aliases so that minor
        schema renames do not break sync.
        """
        if available_fields is None:
            available_fields = {}

        candidates = {
            'title': data.get('title', ''),
            'id': data.get('id'),
            'channel': data.get('channel'),
            'rewritten': data.get('rewritten'),
            'guests': data.get('guests'),
            'quotes': data.get('quotes'),
            'transcript': data.get('transcript'),
            'reading_time': data.get('reading_time'),
            'score': data.get('score'),
            'source_url': data.get('source_url'),
            'cover': [{'file_token': file_token}] if file_token else None,
            'publish_date': data.get('publish_date'),
            'platform': data.get('platform'),
            'tags': data.get('tags'),
            'published': data.get('published', True),
        }

        # Platform normalization
        platform_map = {'youtube': 'YouTube', 'xiaoyuzhou': '小宇宙'}
        if candidates.get('platform'):
            candidates['platform'] = platform_map.get(candidates['platform'], candidates['platform'])

        fields = {}
        for internal_key, raw_value in candidates.items():
            if raw_value is None or raw_value == '':
                continue
            field_name, field_type = self._resolve_field_name(internal_key, available_fields)
            if not field_name:
                # If no schema metadata, fall back to the first alias so the
                # caller can still attempt a write (useful for dry runs/tests).
                aliases = self.field_aliases.get(internal_key, [internal_key])
                field_name = aliases[0]
                field_type = 'text'
            formatted = self._format_field_value(raw_value, field_type)
            if formatted is not None:
                fields[field_name] = formatted

        return fields
    
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
        
        for internal_key in self.REQUIRED_FIELDS:
            field_name = self._resolve_field_name(internal_key, self.get_table_fields())[0]
            if not field_name:
                # Cannot resolve field; assume schema missing this concept
                continue
            value = fields.get(field_name)
            
            # Check if field is empty
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
                    
                    # Upload cover if missing or force
                    file_token = None
                    cover_path = item.get('cover_path')
                    needs_cover = cover_field in missing_fields or force

                    if cover_path and os.path.exists(cover_path) and has_cover_field and needs_cover:
                        file_token = self.upload_image(cover_path)
                    elif not needs_cover and cover_field and cover_field in existing.get('fields', {}):
                        cover_obj = existing['fields'][cover_field]
                        if cover_obj and isinstance(cover_obj, list) and len(cover_obj) > 0:
                            file_token = cover_obj[0].get('file_token')

                    # Preserve existing publish status; default to True for new records
                    published_field = self._resolve_field_name('published', available_fields)[0]
                    if published_field and published_field in existing.get('fields', {}):
                        item['published'] = existing['fields'][published_field]

                    record_id = existing.get('record_id')
                    if self.update_record(record_id, item, available_fields, file_token):
                        updated += 1
                    else:
                        failed += 1
                else:
                    # New record - create with all data
                    print(f"\n➕ Creating: {title}...")
                    
                    # Upload cover for new record
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
        
        print(f"\n{'='*50}")
        print(f"✅ Sync complete:")
        print(f"   ➕ Created: {created}")
        print(f"   🔧 Updated: {updated}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"   ❌ Failed: {failed}")

def main():
    """Main entry point."""
    service = FeishuService()

    feishu_cfg = service.config.get('feishu', {})
    if not feishu_cfg.get('app_id'):
        print("❌ Feishu not configured. Please set up config/feishu.yaml")
        print("See config/feishu-setup.md for instructions.")
        return

    if len(sys.argv) > 1:
        if sys.argv[1] == 'sync':
            # Parse arguments
            export_path = 'content_export.json'
            force = False
            
            for arg in sys.argv[2:]:
                if arg == '--force':
                    force = True
                elif not arg.startswith('--'):
                    export_path = arg
            
            service.sync_from_export(export_path, force=force)
            
        elif sys.argv[1] == 'list':
            records = service.list_records()
            print(f"Found {len(records)} records")
            for r in records:
                print(f"  - {r.get('fields', {}).get('标题', 'Unknown')}")
                
        elif sys.argv[1] == 'check':
            # Check record completeness
            print("🔍 Checking record completeness...")
            records = service.list_records()
            complete = 0
            incomplete = 0
            for r in records:
                is_complete, missing = service.is_record_complete(r)
                title = r.get('fields', {}).get('标题', 'Unknown')[:35]
                if is_complete:
                    print(f"  ✅ {title}")
                    complete += 1
                else:
                    print(f"  ⚠️  {title} (missing: {', '.join(missing)})")
                    incomplete += 1
            print(f"\n📊 Summary: {complete} complete, {incomplete} incomplete")
            
        elif sys.argv[1] == 'test':
            token = service.get_access_token()
            if token:
                print(f"✅ Auth successful, token: {token[:20]}...")
            else:
                print("❌ Auth failed")
    else:
        print("Usage:")
        print("  python3 feishu_service.py test                 # Test authentication")
        print("  python3 feishu_service.py list                 # List all records")
        print("  python3 feishu_service.py check                # Check record completeness")
        print("  python3 feishu_service.py sync                 # Smart sync (skip complete records)")
        print("  python3 feishu_service.py sync --force         # Force update all records")
        print("  python3 feishu_service.py sync <path>          # Sync from specific file")
        print("  python3 feishu_service.py sync <path> --force  # Force sync from specific file")

if __name__ == "__main__":
    main()
