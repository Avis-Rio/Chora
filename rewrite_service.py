import os
import sys
import yaml
import json
import re
import requests
import time
from utils.word_count import update_rewritten_file

def load_config():
    config_path = 'config/sources.yaml'
    if not os.path.exists(config_path):
        print(f"错误: 找不到配置文件 {config_path}")
        print(f"请从 config/sources.example.yaml 复制并填入 API 密钥")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if not config:
        print("错误: 配置文件为空")
        return None
    
    return config

def validate_api_config(config):
    """验证 API 配置是否有效"""
    if not config:
        return False, "配置为空"
    
    api_keys = config.get('api_keys', {})
    llm_config = api_keys.get('llm', {})
    api_key = llm_config.get('api_key', '')
    
    if not api_key:
        return False, "LLM API 密钥未配置"
    
    if 'your_' in api_key or api_key == 'your_llm_api_key_here':
        return False, "LLM API 密钥是占位符，请填入有效密钥"
    
    if not llm_config.get('base_url'):
        return False, "LLM base_url 未配置"
    
    return True, "配置有效"

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def save_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def detect_language(text):
    """检测文本是否主要是英文"""
    # 统计ASCII字符比例
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    total_chars = len(text)
    if total_chars == 0:
        return 'unknown'
    ratio = ascii_chars / total_chars
    return 'english' if ratio > 0.8 else 'chinese'

def rewrite_content(transcript_path, metadata_path, output_path):
    print(f"Starting rewrite for {transcript_path}...")
    rewritten_content = ""

    if not os.path.exists(transcript_path):
        print(f"Error: Transcript file not found: {transcript_path}")
        return False

    config = load_config()
    if not config:
        return False
    
    # 验证 API 配置
    is_valid, message = validate_api_config(config)
    if not is_valid:
        print(f"❌ API 配置错误: {message}")
        print("请编辑 config/sources.yaml 并填入有效的 API 密钥")
        return False

    # Read inputs
    transcript = read_file(transcript_path)
    prompt_template = read_file('config/rewrite-prompt.md')
    
    # 检测语言，如果是英文则添加翻译指令
    lang = detect_language(transcript)
    translation_instruction = ""
    if lang == 'english':
        print("📝 检测到英文转录，将在改写时自动翻译为中文")
        translation_instruction = "\n\n**重要提示：原文是英文，请在改写时将内容翻译为流畅的中文。**\n"

    # Read metadata if available
    metadata_context = ""
    if os.path.exists(metadata_path):
        metadata_context = f"\n\nMetadata:\n{read_file(metadata_path)}"

    # Construct prompt for Gemini
    full_prompt = f"""
    {prompt_template}
    {translation_instruction}

    ---

    TRANSCRIPT:
    {transcript}
    {metadata_context}

    ---
    """

    llm_config = config['api_keys']['llm']
    provider = llm_config.get('provider', 'third_party')
    base_url = llm_config['base_url']

    if provider == 'openai_compatible':
        url = base_url
        payload = {
            "model": llm_config['model'],
            "messages": [
                {"role": "user", "content": full_prompt}
            ],
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 65536,
            "stream": True
        }
    else:
        if ":generateContent" in base_url:
            url = base_url.replace(":generateContent", ":streamGenerateContent?alt=sse")
        else:
            url = base_url.rstrip('/') + ":streamGenerateContent?alt=sse"

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "maxOutputTokens": 65536,
            }
        }

    max_retries = 5
    retry_delay = 5

    try:
        for attempt in range(max_retries):
            try:
                print(f"Sending streaming request to {llm_config['model']} (Attempt {attempt + 1}/{max_retries})...")
                print(f"URL: {url}")

                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {llm_config['api_key']}"
                }

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=180,
                    stream=True
                )

                print(f"Response received with status: {response.status_code}")

                if response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"  ⚠️ Rate limit hit (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    print(f"Error: API returned status {response.status_code}")
                    print(f"Response: {response.text[:500]}")
                    # For other errors, maybe retry too if it might be transient
                    if response.status_code in [500, 502, 503, 504]:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"  ⚠️ Server error ({response.status_code}). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    return False

                # Extract text from streaming response
                rewritten_content = ""
                print("Receiving stream...")

                try:
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data: '):
                                json_str = decoded_line[6:]
                                if json_str.strip() == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(json_str)
                                    if provider == 'openai_compatible':
                                        if 'choices' in chunk and chunk['choices']:
                                            delta = chunk['choices'][0].get('delta', {})
                                            text_chunk = delta.get('content', '')
                                            if text_chunk:
                                                rewritten_content += text_chunk
                                                print(".", end="", flush=True)
                                    else:
                                        if 'candidates' in chunk and chunk['candidates']:
                                            candidate = chunk['candidates'][0]
                                            if 'content' in candidate and 'parts' in candidate['content']:
                                                for part in candidate['content']['parts']:
                                                    if part.get('thought', False):
                                                        continue
                                                    if 'text' in part:
                                                        text_chunk = part['text']
                                                        rewritten_content += text_chunk
                                                        print(".", end="", flush=True)
                                except json.JSONDecodeError:
                                    pass
                    
                    print("\nStream complete.")

                    if not rewritten_content:
                        print(f"  ⚠️ Received empty response from Gemini on attempt {attempt + 1}.")
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"  Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print("Error: No content generated after max retries.")
                            return False

                    # If we got meaningful content, break the retry loop
                    break

                except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError) as conn_e:
                    print(f"\n  ⚠️ Connection issue during stream: {conn_e}")
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print("Error: Connection issue persisted after max retries.")
                        return False

            except requests.exceptions.RequestException as req_e:
                print(f"  ❌ API Request Error: {req_e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"  Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False
        
        # Check if we broke out of loop with content
        if not rewritten_content:
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
                'publish_date': '',
                'guests': ''  # 新增：保留已从页面提取的嘉宾
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
                    
                    # 提取已有嘉宾信息（优先保留从页面提取的）
                    existing_guests_match = re.search(r'##\s*嘉宾\s*\n(.+?)(?=\n##|\Z)', existing_content, re.MULTILINE | re.DOTALL)
                    if existing_guests_match:
                        original_fields['guests'] = existing_guests_match.group(1).strip()
            
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
            
            # 嘉宾（优先使用从页面提取的，其次使用 AI 生成的）
            final_guests = original_fields['guests'] or ai_guests
            if final_guests and final_guests.lower() not in ['无', '[主要嘉宾或演讲者姓名']:
                final_metadata += f"## 嘉宾\n{final_guests}\n\n"
            
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
