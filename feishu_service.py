#!/usr/bin/env python3
"""Thin CLI shim for the Feishu (Lark) Bitable service.

This module preserves the legacy ``feishu_service.py`` entry point so
existing subprocess invocations (``python3 feishu_service.py sync``,
``list``, ``check``, ``test``) keep working unchanged. All real
implementation now lives in the :mod:`feishu` package.
"""

import sys

from feishu import FeishuService


def main():
    """Main entry point. Delegates to :class:`FeishuService`."""
    service = FeishuService()

    feishu_cfg = service.config.get("feishu", {})
    if not feishu_cfg.get("app_id"):
        print("❌ Feishu not configured. Please set up config/feishu.yaml")
        print("See config/feishu-setup.md for instructions.")
        return

    if len(sys.argv) > 1:
        if sys.argv[1] == "sync":
            # Parse arguments
            export_path = "content_export.json"
            force = False

            for arg in sys.argv[2:]:
                if arg == "--force":
                    force = True
                elif not arg.startswith("--"):
                    export_path = arg

            service.sync_from_export(export_path, force=force)

        elif sys.argv[1] == "list":
            records = service.list_records()
            print(f"Found {len(records)} records")
            for r in records:
                print(f"  - {r.get('fields', {}).get('标题', 'Unknown')}")

        elif sys.argv[1] == "check":
            # Check record completeness
            print("🔍 Checking record completeness...")
            records = service.list_records()
            complete = 0
            incomplete = 0
            for r in records:
                is_complete, missing = service.is_record_complete(r)
                title = r.get("fields", {}).get("标题", "Unknown")[:35]
                if is_complete:
                    print(f"  ✅ {title}")
                    complete += 1
                else:
                    print(f"  ⚠️  {title} (missing: {', '.join(missing)})")
                    incomplete += 1
            print(f"\n📊 Summary: {complete} complete, {incomplete} incomplete")

        elif sys.argv[1] == "test":
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
