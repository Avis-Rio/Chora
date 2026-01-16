import os
import re
import glob

def clean_tags_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define blacklist of tags (channel names, etc.)
    blacklist = [
        '忽左忽右', '硅谷101', '翻转电台', '翻转台电', 'Dan Koe', 'Kevin Kelly', 
        'Unknown', 'JustPod', '午后偏见', '翻电', 'Gavin Wang', 'Alex Wang',
        '薛茗', '刘燕', '梁永安', '端木易', '陈茜'
    ]
    
    # Find the Tags line
    # Pattern: 标签: tag1, tag2, ...
    tag_match = re.search(r'(标签[:：])\s*(.+)', content)
    
    if tag_match:
        prefix = tag_match.group(1)
        tags_str = tag_match.group(2)
        
        # Split tags
        tags = [t.strip() for t in re.split(r'[,，、]', tags_str) if t.strip()]
        
        # Filter tags
        clean_tags = []
        for tag in tags:
            is_blacklisted = False
            for bad_word in blacklist:
                if bad_word.lower() in tag.lower():
                    is_blacklisted = True
                    break
            
            if not is_blacklisted:
                clean_tags.append(tag)
        
        # Reconstruct line
        new_line = f"{prefix} {', '.join(clean_tags)}"
        
        # Replace in content
        new_content = content.replace(tag_match.group(0), new_line)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Cleaned tags in {os.path.basename(os.path.dirname(file_path))}")
            print(f"   Old: {tags_str}")
            print(f"   New: {', '.join(clean_tags)}")
            return True
            
    return False

def main():
    archive_dir = 'content_archive'
    print(f"Scanning {archive_dir} for tag cleanup...")
    
    count = 0
    for rewritten_path in glob.glob(f'{archive_dir}/*/*/rewritten.md'):
        if clean_tags_in_file(rewritten_path):
            count += 1
            
    print(f"\n🎉 Cleanup complete! Updated {count} files.")

if __name__ == "__main__":
    main()
