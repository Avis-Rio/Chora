"""Record CRUD against the Feishu Bitable API."""

import json
import time
from datetime import datetime


class RecordMixin:
    """list / find / create / update records plus schema introspection."""

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
        """Create a new record. Returns the record_id on success, ``None`` on failure."""
        url = f"{self._base_url()}/records"
        mapped = self._map_to_fields(data, available_fields, file_token)
        payload = {"fields": mapped}
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
        """Update an existing record. Returns ``True`` on success, ``False`` on failure."""
        url = f"{self._base_url()}/records/{record_id}"
        mapped = self._map_to_fields(data, available_fields, file_token)
        payload = {"fields": mapped}
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
        """Get the live table schema — list of field definitions."""
        url = f"{self._base_url()}/fields"
        try:
            response = self._request("GET", url, headers=self._headers())
            result = response.json()
            if result.get('code') == 0:
                items = result.get('data', {}).get('items', [])
                field_map = {}
                for f in items:
                    name = f.get('field_name')
                    ftype = self._feishu_type_to_internal(f.get('type'))
                    field_map[name] = ftype
                return field_map
            else:
                print(f"⚠️ Failed to get table fields: {result}")
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
