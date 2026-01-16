import re
import sys
import os

def count_words(text):
    # Count Chinese characters
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # Count English words
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    return chinese_chars + english_words

def update_rewritten_file(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    total_words = count_words(content)
    
    # First, try to remove any existing word count lines to avoid duplicates
    content = re.sub(r'-\s*(\*\*)?字数(\*\*)?:\s*.*?\n', '', content)

    # Target placeholder pattern: - **字数**: [预计生成的总字数]/2500字 or - 字数: [预计生成的总字数]/2500字
    # Also handle cases where it's already partially filled

    # Re-insert into "创作说明" section
    section_pattern = r'(#+\s*\d*\.?\s*创作说明.*?\n)'
    if re.search(section_pattern, content):
        new_content = re.sub(section_pattern, rf'\1- **字数**: {total_words}/2500字\n', content)
        print(f"Updated word count in {file_path}: {total_words}")
    else:
        print(f"Could not find '创作说明' section in {file_path}")
        return

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/word_count.py <file_path>")
        sys.exit(1)
    
    update_rewritten_file(sys.argv[1])
