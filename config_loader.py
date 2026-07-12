"""
统一配置加载器。

规则：
1. 读取 config/sources.yaml 中的非敏感配置（订阅源、过滤规则等）。
2. 敏感信息（API keys、飞书凭证）优先从环境变量读取。
3. 保持向后兼容：如果环境变量未设置，仍回退到 YAML 中的值。

推荐：在仓库根目录创建 .env 文件并填入真实密钥，.env 已被 .gitignore 忽略。
"""

import os

import yaml

# 自动加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def load_yaml(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_sources_config(path="config/sources.yaml"):
    """
    加载 sources.yaml，并用环境变量覆盖 api_keys。

    支持的环境变量：
    - GROQ_API_KEY
    - GEMINI_API_KEY
    - GEMINI_BASE_URL
    - GEMINI_MODEL
    - LLM_API_KEY
    - LLM_BASE_URL
    - LLM_MODEL
    """
    config = load_yaml(path)
    if config is None:
        return None

    if "api_keys" not in config:
        config["api_keys"] = {}

    # Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        config["api_keys"]["groq"] = groq_key

    # Gemini
    gemini_cfg = config["api_keys"].get("gemini", {})
    if os.getenv("GEMINI_API_KEY"):
        gemini_cfg["api_key"] = os.getenv("GEMINI_API_KEY")
    if os.getenv("GEMINI_BASE_URL"):
        gemini_cfg["base_url"] = os.getenv("GEMINI_BASE_URL")
    if os.getenv("GEMINI_MODEL"):
        gemini_cfg["model"] = os.getenv("GEMINI_MODEL")
    if gemini_cfg:
        config["api_keys"]["gemini"] = gemini_cfg

    # LLM (OpenAI-compatible)
    llm_cfg = config["api_keys"].get("llm", {})
    if os.getenv("LLM_PROVIDER"):
        llm_cfg["provider"] = os.getenv("LLM_PROVIDER")
    if os.getenv("LLM_API_KEY"):
        llm_cfg["api_key"] = os.getenv("LLM_API_KEY")
    if os.getenv("LLM_BASE_URL"):
        llm_cfg["base_url"] = os.getenv("LLM_BASE_URL")
    if os.getenv("LLM_MODEL"):
        llm_cfg["model"] = os.getenv("LLM_MODEL")
    if llm_cfg:
        config["api_keys"]["llm"] = llm_cfg

    return config


def load_feishu_config(path="config/feishu.yaml"):
    """
    加载 feishu.yaml，并用环境变量覆盖凭证。

    支持的环境变量：
    - FEISHU_APP_ID
    - FEISHU_APP_SECRET
    - FEISHU_BASE_ID
    - FEISHU_TABLE_ID
    """
    config = load_yaml(path)
    if config is None:
        return None

    if "feishu" not in config:
        config["feishu"] = {}

    feishu_cfg = config["feishu"]
    if os.getenv("FEISHU_APP_ID"):
        feishu_cfg["app_id"] = os.getenv("FEISHU_APP_ID")
    if os.getenv("FEISHU_APP_SECRET"):
        feishu_cfg["app_secret"] = os.getenv("FEISHU_APP_SECRET")
    if os.getenv("FEISHU_BASE_ID"):
        feishu_cfg["base_id"] = os.getenv("FEISHU_BASE_ID")
    if os.getenv("FEISHU_TABLE_ID"):
        feishu_cfg["table_id"] = os.getenv("FEISHU_TABLE_ID")

    if "vercel" not in config:
        config["vercel"] = {}

    return config


def mask_secret(value, visible=4):
    if not value or len(str(value)) <= visible * 2:
        return "***"
    s = str(value)
    return s[:visible] + "***" + s[-visible:]
