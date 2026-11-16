"""Shared environment-only credential resolution for the news agent."""
import json
import os
from pathlib import Path
import re
import urllib.parse

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
    for target in config.get("targets", {}).values():
        if "api_key" in target:
            raise ValueError("Replace target api_key with api_key_env")
    return config


def model_key(provider, references):
    if provider not in MODEL_KEY_ENVS:
        raise ValueError("Provider must be openai, anthropic or gemini")
    return environment_value((references or {}).get(provider, MODEL_KEY_ENVS[provider]))


def target_settings(config, target_name):
    target = config["targets"][target_name]
    base = target["url"].rstrip("/")
    url = urllib.parse.urlsplit(base)
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError(f"Invalid URL for target {target_name}")
    key = environment_value(target["api_key_env"])
    if not re.fullmatch(r"wob_[0-9a-fA-F]{64}", key):
        raise ValueError(f"{target['api_key_env']} must contain a Robot News page publishing key")
    return base, key


def fetch_frequency_minutes(config, topic=None):
    minutes = (topic or {}).get("news_fetch_frequency_minutes",
                                config.get("news_fetch_frequency_minutes", 30))
    if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not 0 < minutes <= 525600:
        raise ValueError("news_fetch_frequency_minutes must be positive and no more than one year")
    return minutes
