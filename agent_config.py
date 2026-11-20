"""Shared environment-only credential resolution for the news agent."""
import json
import os
from pathlib import Path
import re
from robot_news import PRODUCTION_URL

DEFAULT_CONFIG = str(Path(__file__).resolve().with_name("config.json"))

TARGET_URLS = {"localhost": "http://localhost:3000", "production": PRODUCTION_URL}

MODEL_KEY_ENVS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def environment_value(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Credential references must be environment variable names")
    value = os.environ.get(name, "")
    if not value.strip():
        raise ValueError(f"Set environment variable {name}")
    if value != value.strip() or any(char.isspace() for char in value):
        raise ValueError(f"{name} contains whitespace")
    if value.lower().startswith(("your-", "your_", "replace", "changeme", "wob_your")):
        raise ValueError(f"{name} contains a placeholder")
    return value


def load_config(path):
    config = json.loads(Path(path).read_text())
    if "api_keys" in config:
        raise ValueError("Replace api_keys with model_api_key_env references")
    if not isinstance(config.get("model_api_key_env", {}), dict):
        raise ValueError("model_api_key_env must map providers to environment variable names")
    return config


def model_key(provider, references):
    if provider not in MODEL_KEY_ENVS:
        raise ValueError("Provider must be openai, anthropic or gemini")
    return environment_value((references or {}).get(provider, MODEL_KEY_ENVS[provider]))


def target_url(target_name):
    if target_name not in TARGET_URLS:
        raise ValueError(f"Unknown publishing target: {target_name}")
    return TARGET_URLS[target_name]


def target_settings(target_name):
    base = target_url(target_name)
    key = environment_value("ROBOT_NEWS_API_KEY")
    if not re.fullmatch(r"wob_[0-9a-fA-F]{64}", key):
        raise ValueError("ROBOT_NEWS_API_KEY must contain a Robot News account API key")
    return base, key
