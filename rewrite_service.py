import os
import sys
import yaml
import json
import re
import requests
from utils.word_count import update_rewritten_file

def load_config():
    with open('config/sources.yaml', 'r') as f:
        return yaml.safe_load(f)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def save_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def rewrite_content(transcript_path, metadata_path, output_path):
    print(f"Starting rewrite for {transcript_path}...")

    if not os.path.exists(transcript_path):
        print(f"Error: Transcript file not found: {transcript_path}")
        return False

    config = load_config()

    # Read inputs
    transcript = read_file(transcript_path)
    prompt_template = read_file('config/rewrite-prompt.md')

    # Read metadata if available
    metadata_context = ""
    if os.path.exists(metadata_path):
        metadata_context = f"\n\nMetadata:\n{read_file(metadata_path)}"

    # Construct prompt for Gemini
    full_prompt = f"""
    {prompt_template}

    ---

    TRANSCRIPT:
    {transcript}
    {metadata_context}

    ---
    """

    # Gemini API Setup
    llm_config = config['api_keys']['llm']
    # 使用 Bearer Token 认证方式（云雾API要求）
    base_url = llm_config['base_url']

    # 切换到流式 API 端点
    if ":generateContent" in base_url:
        url = base_url.replace(":generateContent", ":streamGenerateContent?alt=sse")
    else:
        # Fallback if URL format is unexpected, append stream method
        url = base_url.rstrip('/') + ":streamGenerateContent?alt=sse"

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "maxOutputTokens": 65536, # Further increased to prevent truncation
        }
    }

    try:
        print(f"Sending streaming request to Gemini ({llm_config['model']})...")
        print(f"URL: {url}")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {llm_config['api_key']}"
        }

        # 使用 requests 发送流式请求
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=120, # 连接超时120秒，读取超时由流式处理
            stream=True
        )

        print(f"Response received with status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

        # Extract text from Gemini streaming response
        rewritten_content = ""
        print("Receiving stream...")

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    json_str = decoded_line[6:] # Remove 'data: ' prefix
                    try:
                        chunk = json.loads(json_str)
                        if 'candidates' in chunk and chunk['candidates']:
                            candidate = chunk['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                for part in candidate['content']['parts']:
                                    # 跳过 Gemini 的 thinking 内容 (thought: true)
                                    if part.get('thought', False):
                                        continue
                                    if 'text' in part:
                                        text_chunk = part['text']
                                        rewritten_content += text_chunk
                                        # Optional: print progress dot
                                        print(".", end="", flush=True)
                    except json.JSONDecodeError:
                        pass

        print("\nStream complete.")

        if not rewritten_content:
            print("Error: No content generated.")
            return False

        # Content completeness validation
        required_sections = ["核心洞察", "哲思结语"]
        missing_sections = [s for s in required_sections if s not in rewritten_content]
        if missing_sections:
            print(f"⚠️ Warning: Content may be incomplete. Missing sections: {missing_sections}")
            print(f"   Total generated content length: {len(rewritten_content)} characters")

        # Save output

        # 1. Extract Metadata Section
        # Allow missing closing tag to handle cutoff content
        metadata_match = re.search(r'<METADATA_SECTION>(.*?)(?:</METADATA_SECTION>|$)', rewritten_content, re.DOTALL)
        if metadata_match:
            ai_metadata = metadata_match.group(1).strip()

            # Remove any trailing XML tags if they got caught (e.g., <REWRITE_SECTION>)
            ai_metadata = re.sub(r'<REWRITE_SECTION>.*', '', ai_metadata, flags=re.DOTALL).strip()
            
            # 从现有 metadata.md 读取所有原始字段（必须完整保留）
            original_fields = {
                'title': '',
                'source': '',
                'source_url': '',
                'publish_date': ''
            }
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                    
                    # 提取标题 (# 开头)
                    for line in existing_content.split('\n'):
                        if line.startswith('# '):
                            original_fields['title'] = line
                            break
                    
                    # 提取来源
                    source_match = re.search(r'##\s*来源\s*\n(.+?)(?=\n##|\Z)', existing_content, re.MULTILINE | re.DOTALL)
                    if source_match:
                        original_fields['source'] = source_match.group(1).strip()
                    
                    # 提取原始链接
                    url_match = re.search(r'##\s*原始链接\s*\n(.+?)(?=\n##|\Z)', existing_content, re.MULTILINE | re.DOTALL)
                    if url_match:
                        original_fields['source_url'] = url_match.group(1).strip()
                    
                    # 提取发布时间
                    date_match = re.search(r'##\s*发布时间\s*\n(.+?)(?=\n##|\Z)', existing_content, re.MULTILINE | re.DOTALL)
                    if date_match:
                        original_fields['publish_date'] = date_match.group(1).strip()
            
            # 从 AI 输出中提取嘉宾和金句
            ai_guests = ""
            ai_quotes = ""
            
            guests_match = re.search(r'##\s*嘉宾\s*\n(.+?)(?=\n##|\Z)', ai_metadata, re.MULTILINE | re.DOTALL)
            if guests_match:
                ai_guests = guests_match.group(1).strip()
            
            quotes_match = re.search(r'##\s*金句\s*\n(.+?)(?=\n##|\Z)', ai_metadata, re.MULTILINE | re.DOTALL)
            if quotes_match:
                ai_quotes = quotes_match.group(1).strip()
            
            # 构建最终 metadata（按标准格式）
            final_metadata = ""
            
            # 标题
            if original_fields['title']:
                final_metadata += f"{original_fields['title']}\n\n"
            
            # 来源
            if original_fields['source']:
                final_metadata += f"## 来源\n{original_fields['source']}\n\n"
            
            # 原始链接
            if original_fields['source_url']:
                final_metadata += f"## 原始链接\n{original_fields['source_url']}\n\n"
            
            # 发布时间
            if original_fields['publish_date']:
                final_metadata += f"## 发布时间\n{original_fields['publish_date']}\n\n"
            
            # 嘉宾（AI 生成）
            if ai_guests and ai_guests.lower() not in ['无', '[主要嘉宾或演讲者姓名']:
                final_metadata += f"## 嘉宾\n{ai_guests}\n\n"
            
            # 金句（AI 生成）
            if ai_quotes and not ai_quotes.startswith('['):
                final_metadata += f"## 金句\n{ai_quotes}\n"

            save_file(metadata_path, final_metadata.strip())
            print(f"Updated metadata saved to {metadata_path}")
        else:
            print("Warning: No <METADATA_SECTION> found in output.")

        # 2. Extract Rewrite Section
        # Allow missing closing tag
        rewrite_match = re.search(r'<REWRITE_SECTION>(.*?)(?:</REWRITE_SECTION>|$)', rewritten_content, re.DOTALL)
        if rewrite_match:
            final_rewrite_content = rewrite_match.group(1).strip()
            save_file(output_path, final_rewrite_content)
            print(f"Rewritten content saved to {output_path}")
        else:
            # Fallback: save everything to rewritten.md if no tags found
            # But try to exclude METADATA_SECTION if it exists
            print("Warning: No <REWRITE_SECTION> found, saving filtered output.")

            filtered_content = re.sub(r'<METADATA_SECTION>.*?</METADATA_SECTION>', '', rewritten_content, flags=re.DOTALL).strip()
            # Also remove just the tags if they remain
            filtered_content = filtered_content.replace('<METADATA_SECTION>', '').replace('</METADATA_SECTION>', '')

            save_file(output_path, filtered_content)
            print(f"Rewritten content saved to {output_path}")

        # Update word count
        try:
            update_rewritten_file(output_path)
        except Exception as wc_e:
            print(f"Warning: Failed to update word count: {wc_e}")

        return True

    except Exception as e:
        print(f"Error during rewrite: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python rewrite_service.py <transcript_path> <metadata_path> <output_path>")
        sys.exit(1)

    rewrite_content(sys.argv[1], sys.argv[2], sys.argv[3])
