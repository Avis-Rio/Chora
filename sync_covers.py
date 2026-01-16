#!/usr/bin/env python3
"""
Sync covers to Vercel public directory for static hosting.
"""

import os
import shutil
import glob
import json
import yaml

def load_config():
    """Load configuration including Vercel domain."""
    config_path = 'config/vercel.yaml'
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}

def sync_covers(archive_dir='content_archive', output_dir='frontend/public/covers'):
    """Copy all cover images to Vercel public directory."""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    synced = []
    
    for date_dir in glob.glob(f'{archive_dir}/*'):
        if not os.path.isdir(date_dir):
            continue
        
        for content_dir in glob.glob(f'{date_dir}/*'):
            if not os.path.isdir(content_dir):
                continue
            
            folder_name = os.path.basename(content_dir)
            
            # Find cover file
            for ext in ['png', 'jpg', 'jpeg']:
                cover_src = os.path.join(content_dir, f'cover.{ext}')
                if os.path.exists(cover_src):
                    # Generate safe filename based on folder
                    safe_name = folder_name.replace(' ', '_')[:50]
                    cover_dst = os.path.join(output_dir, f'{safe_name}.{ext}')
                    
                    shutil.copy2(cover_src, cover_dst)
                    synced.append({
                        'folder': folder_name,
                        'src': cover_src,
                        'dst': cover_dst,
                        'url': f'/covers/{safe_name}.{ext}'
                    })
                    print(f"✅ {folder_name[:40]}... -> {os.path.basename(cover_dst)}")
                    break
    
    print(f"\n✅ Synced {len(synced)} covers to {output_dir}")
    return synced

def update_export_with_cover_urls(export_path='content_export.json', base_url=''):
    """Update export JSON with Vercel cover URLs."""
    
    if not os.path.exists(export_path):
        print(f"❌ Export file not found: {export_path}")
        return
    
    with open(export_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for item in data:
        if item.get('cover_path'):
            folder_name = os.path.basename(os.path.dirname(item['cover_path']))
            safe_name = folder_name.replace(' ', '_')[:50]
            ext = item['cover_path'].split('.')[-1]
            item['cover_url'] = f"{base_url}/covers/{safe_name}.{ext}"
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated cover URLs in {export_path}")

if __name__ == "__main__":
    import sys
    
    # Load config for Vercel domain
    config = load_config()
    default_base_url = config.get('vercel', {}).get('domain', '')
    
    if len(sys.argv) > 1 and sys.argv[1] == '--update-urls':
        base_url = sys.argv[2] if len(sys.argv) > 2 else default_base_url
        update_export_with_cover_urls(base_url=base_url)
    else:
        sync_covers()
        update_export_with_cover_urls(base_url=default_base_url)

