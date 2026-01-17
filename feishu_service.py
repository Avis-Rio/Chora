#!/usr/bin/env python3
"""
Feishu (Lark) Bitable API Service for syncing content to multi-dimensional table.
Supports image upload for cover attachments.
"""

import os
import sys
import json
import requests
import yaml
import time
import mimetypes
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class FeishuService:
    """Feishu Bitable API wrapper."""
    
    def __init__(self, config_path='config/feishu.yaml'):
        """Initialize with config file."""
        self.config = self._load_config(config_path)
        self.access_token = None
        self.token_expires = 0
        
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
    
    def _load_config(self, config_path):
        """Load Feishu configuration."""
        if not os.path.exists(config_path):
            print(f"⚠️ Config not found: {config_path}")
            print("Please create config/feishu.yaml with app_id, app_secret, base_id, table_id")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('feishu', {})
    
    def get_access_token(self):
        """Get tenant access token from Feishu API."""
        if self.access_token and datetime.now().timestamp() < self.token_expires:
            return self.access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.config.get('app_id'),
            "app_secret": self.config.get('app_secret')
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
        except:
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
        base_id = self.config.get('base_id')
        table_id = self.config.get('table_id')
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
        """Find a record by content ID."""
        records = self.list_records()
        for record in records:
            fields = record.get('fields', {})
            if fields.get('记录ID') == content_id:
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
        """Get list of field names from the table."""
        base_id = self.config.get('base_id')
        table_id = self.config.get('table_id')
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/fields"
        
        try:
            response = self._request("GET", url, headers=self._headers())
            result = response.json()
            
            if result.get('code') == 0:
                fields = result.get('data', {}).get('items', [])
                return [f.get('field_name') for f in fields]
            else:
                print(f"⚠️ Failed to get fields: {result}")
                return []
        except Exception as e:
            print(f"⚠️ Error getting fields: {e}")
            return []
    
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
                'parent_node': self.config.get('base_id'),
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
    
    def _map_to_fields(self, data, available_fields=None, file_token=None):
        """Map export data to Feishu field format.
        Only includes fields that exist in the table.
        """
        # Build all possible fields
        all_fields = {
            "标题": data.get('title', ''),
        }
        
        # Optional text fields
        if data.get('id'):
            all_fields["记录ID"] = data['id']
        if data.get('channel'):
            all_fields["频道"] = data['channel']
        if data.get('rewritten'):
            all_fields["正文"] = data['rewritten']
        
        # Metadata fields (嘉宾, 金句)
        if data.get('guests'):
            all_fields["嘉宾"] = data['guests']
        if data.get('quotes'):
            # Join quotes with newlines, each as blockquote
            all_fields["金句"] = '\n'.join([f'> {q}' for q in data['quotes'][:5]])
        
        # Transcript field (原文逐字稿)
        if data.get('transcript'):
            all_fields["原文逐字稿"] = data['transcript']
        
        # Optional number fields
        if data.get('reading_time'):
            all_fields["阅读时长"] = data['reading_time']
        if data.get('score'):
            all_fields["评分"] = data['score']
        
        # Handle link fields
        if data.get('source_url'):
            all_fields["原始链接"] = {"link": data['source_url'], "text": "查看原始内容"}
        
        # Handle cover as attachment (if file_token provided)
        if file_token:
            all_fields["封面"] = [{'file_token': file_token}]
        
        # Handle date field - use 发布时间 (the field name in user's table)
        if data.get('publish_date'):
            try:
                dt = datetime.strptime(data['publish_date'], '%Y-%m-%d')
                all_fields["发布时间"] = int(dt.timestamp() * 1000)
            except:
                pass
        
        # Handle single select (platform)
        platform_map = {'youtube': 'YouTube', 'xiaoyuzhou': '小宇宙'}
        if data.get('platform'):
            all_fields["平台"] = platform_map.get(data['platform'], data['platform'])
        
        # Handle multi-select (tags)
        if data.get('tags'):
            all_fields["标签"] = data['tags']
        
        # Set default publish status to True (checked)
        all_fields["是否发布"] = True
        
        # Filter to only available fields if provided
        if available_fields:
            fields = {k: v for k, v in all_fields.items() if k in available_fields}
        else:
            fields = all_fields
        
        return fields
    
    # Key fields that must have data for a record to be considered complete
    REQUIRED_FIELDS = ['标题', '正文', '封面', '标签', '发布时间', '记录ID']
    
    def is_record_complete(self, record):
        """Check if a record has all required fields filled.
        
        Returns tuple: (is_complete, missing_fields)
        """
        fields = record.get('fields', {})
        missing = []
        
        for field_name in self.REQUIRED_FIELDS:
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
            print(f"   Found fields: {', '.join(available_fields)}")
        else:
            print("   ⚠️ Could not get field list, will try all fields")
        
        # Check if cover field exists
        has_cover_field = '封面' in available_fields if available_fields else True
        
        # Pre-fetch all records for efficiency
        print("📥 Fetching existing records...")
        all_records = self.list_records(page_size=500)
        records_by_id = {}
        for record in all_records:
            content_id = record.get('fields', {}).get('记录ID')
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
                    needs_cover = '封面' in missing_fields or force
                    
                    if cover_path and os.path.exists(cover_path) and has_cover_field and needs_cover:
                        file_token = self.upload_image(cover_path)
                    
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
    
    if not service.config.get('app_id'):
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
