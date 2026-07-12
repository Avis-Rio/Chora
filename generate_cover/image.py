"""Gemini image generation entry point used by the Chora cover pipeline.

Extracted from the legacy ``generate_cover.py`` on 2026-07-11 as part of the
L5 split tracked in ``skills/ARCHITECTURE.md`` §6.

Provides:

- :func:`generate_cover` — sends a prompt to the Gemini image model
  (``gemini-3.1-flash-image-preview`` by default; see ``config/sources.yaml``
  ``api_keys.gemini`` for overrides), retries on 429 / 5xx, decodes the
  inline base64 image and writes it to disk.

This is the canonical entry point that
``distribution_pipeline/assets/ai_image/gateway.py`` uses via its
``_import_generate_cover`` shim — so it MUST remain reachable as
``generate_cover.generate_cover`` once the package import resolves.
"""

import base64
import os
import time

import requests

from generate_cover._infra import load_config


def generate_cover(prompt, output_path, title=None):
    """
    使用 Gemini 3 Pro Image 生成封面图

    Args:
        prompt: 生成提示词
        output_path: 输出文件路径
        title: 可选的标题，用于增强提示词

    Returns:
        bool: 是否成功生成
    """
    config = load_config()
    api_config = config['api_keys']['gemini']

    base_url = api_config['base_url']
    api_key = api_config['api_key']

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.9,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192
        }
    }

    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"🎨 Generating cover image (Attempt {attempt + 1}/{max_retries})...")
            print(f"   Prompt preview: {prompt[:100]}...")

            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=120,
            )

            print(f"   Response status: {response.status_code}")

            if response.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                print(f"   ⚠️ Rate limit hit (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                print(f"   ❌ API error: {response.text[:300]}")
                if response.status_code in [500, 502, 503, 504]:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"   ⚠️ Server error ({response.status_code}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                return False

            result = response.json()

            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    for part in parts:
                        inline_data = part.get('inlineData') or part.get('inline_data')
                        if inline_data:
                            image_data = base64.b64decode(inline_data['data'])

                            dirname = os.path.dirname(output_path)
                            if dirname:
                                os.makedirs(dirname, exist_ok=True)

                            with open(output_path, 'wb') as f:
                                f.write(image_data)

                            file_size_kb = len(image_data) / 1024
                            print(f"   ✅ Cover saved: {output_path} ({file_size_kb:.1f} KB)")
                            return True
                        elif 'text' in part:
                            print(f"   ⚠️ Model returned text instead of image")
                            print(f"   Text: {part['text'][:200]}...")

            print("   ❌ No image data found in response")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return False

        except (requests.exceptions.RequestException, Exception) as e:
            print(f"   ❌ Error generating image: {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return False
