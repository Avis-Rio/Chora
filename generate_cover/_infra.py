"""Internal infrastructure for the ``generate_cover`` package.

Houses shared constants and small LLM/config helpers used by multiple
sub-modules:

- :data:`STYLES_DIR` — populated from the global Baoyu cover-image skill
  styles directory if missing.
- :func:`load_config` — thin wrapper around ``config_loader.load_sources_config``.
- :func:`call_gemini_text` — single-call LLM text client used by style and
  title helpers.

Not part of the package's public surface; import via ``generate_cover._infra``
or simply from within the package as ``from generate_cover import _infra``.
"""

import glob
import os
import shutil

import requests

from config_loader import load_sources_config

# Populate ``styles/`` from the global Baoyu skill if it's missing.
STYLES_DIR = os.path.join(os.getcwd(), "styles")
if not os.path.exists(STYLES_DIR):
    os.makedirs(STYLES_DIR)
    global_styles = "/Users/Avis/.agents/skills/baoyu-cover-image/references/styles"
    if os.path.exists(global_styles):
        for f in glob.glob(os.path.join(global_styles, "*.md")):
            shutil.copy(f, STYLES_DIR)


def load_config():
    return load_sources_config("config/sources.yaml")


def call_gemini_text(prompt):
    """
    调用 LLM 文本模型 (支持 Gemini 原生和 OpenAI 兼容格式)
    """
    config = load_config()
    api_config = config["api_keys"]["llm"]

    base_url = api_config["base_url"]
    api_key = api_config["api_key"]
    provider = api_config.get("provider", "third_party")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    if provider == "openai_compatible":
        url = base_url
        payload = {
            "model": api_config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 2048,
        }
    else:
        url = base_url
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            print(f"Error calling LLM Text API: {response.text}")
            return None

        result = response.json()

        if provider == "openai_compatible":
            if "choices" in result and result["choices"]:
                return result["choices"][0].get("message", {}).get("content", "")
            return None
        else:
            if "candidates" in result and result["candidates"]:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    final_text = ""
                    for part in candidate["content"]["parts"]:
                        if part.get("thought", False):
                            continue
                        if "text" in part:
                            final_text += part["text"]
                    return final_text
            return None
    except Exception as e:
        print(f"Exception calling LLM Text API: {e}")
        return None
