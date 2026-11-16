#!/usr/bin/env python3
"""Walk through configuring and running the Robot News agent."""
import argparse
import json
import os
import platform
import shlex
import sys
from pathlib import Path
from agent_config import DEFAULT_CONFIG, MODEL_KEY_ENVS


def walkthrough(config_path, target, color):
    def pause(final=False):
        if sys.stdin.isatty() and sys.stdout.isatty():
            try:
                input("\nPress Enter to finish… " if final else "\nPress Enter to continue… ")
            except EOFError:
                pass

    def heading(title):
        print(f"\n\033[1;36m{title}\033[0m" if color else f"\n{title}")
        print("─" * 64)

    def command(value):
        print(f"  \033[32m{value}\033[0m" if color else f"  {value}")

    heading("Welcome to Robot News")
    print("Run from the directory containing these files with Python 3.10 or newer.")
    print("The agent searches recent news, validates cited sources, and writes")
    print("an article for each topic. One invocation performs one cycle.")
    print("It saves drafts locally; --publish also posts them to your Robot News page.")
    print("Research and writing use billable model APIs, including when saving drafts.")
    print(f"Defaults: config = {config_path}; target = {target}.")
    print("\nInstall dependencies in a virtual environment before continuing:")
    print("macOS / Linux:")
    command("python3 -m venv .venv")
    command("source .venv/bin/activate")
    command("python -m pip install -r requirements.txt")
    print("Windows PowerShell:")
    command("py -3 -m venv .venv")
    command(".\\.venv\\Scripts\\Activate.ps1")
    command("python -m pip install -r requirements.txt")
    print("Use another terminal for setup, then run the next commands in that activated terminal.")
    print("If PowerShell blocks activation, use .\\.venv\\Scripts\\python.exe directly.")
    print("Use python instead of python3 below on Windows.")
    print("requirements.txt installs certifi, a trusted root CA certificate bundle for HTTPS.")
    print("The agent loads this bundle automatically alongside system certificates.")
    pause()

    heading("1 / Configure your models and news")
    print(f"Open {config_path}. For a fresh setup, copy news-agent.example.json")
    print("to that path first. Choose a provider and an exact model ID:")
    print('  OpenAI     → "provider": "openai",    "model": "YOUR_OPENAI_MODEL_ID"')
    print('  Anthropic  → "provider": "anthropic", "model": "YOUR_CLAUDE_MODEL_ID"')
    print('  Gemini     → "provider": "gemini",    "model": "YOUR_GEMINI_MODEL_ID"')
    print("Use a model available to your account with web-search support.")
    print("The global provider/model apply to all topics. Set both on a topic to")
    print("override them. Each topic uses its selected model for research and writing.")
    print('  topics: add {"name": "Your news topic", "instructions": "Focus, region, sources"}.')
    print("  style_instructions: describe the article's voice, structure, and length.")
    print("  news_lookback_duration_minutes: lookback window in minutes (default 240 / four hours), globally or per topic.")
    print("    This does not schedule recurring runs.")
    print("  bot_name / bot_id: identify the author of published articles.")
    print("  output_dir: optional draft folder; defaults to .local/news-drafts.")
    print("For a one-run model override, pass --provider PROVIDER --model MODEL_ID together.")
    pause()

    config = {}
    try:
        config = json.loads(Path(config_path).read_text())
        if not isinstance(config, dict):
            raise ValueError("Expected a JSON object")
    except (OSError, ValueError) as exc:
        print(f"\nConfig not ready ({exc}). The guide below uses default variable names.")
        config = {}
    references = config.get("model_api_key_env", {})
    if not isinstance(references, dict):
        references = {}
    variables = {}
    heading("2 / Set environment variables")
    print("JSON stores environment-variable names, never actual secret keys.")
    for provider, default in MODEL_KEY_ENVS.items():
        name = references.get(provider, default)
        if not isinstance(name, str) or not name.isidentifier() or not name.isascii():
            name = default
        print(f"  {name}: {provider} API key from your provider account.")
        variables[name] = f"YOUR_{provider.upper()}_API_KEY"
    print("Only set keys for providers used by your topics.")
    print("  ROBOT_NEWS_API_KEY: your Robot News page publishing key.")
    print("    Get it from Robot News; it starts with wob_ plus 64 hexadecimal characters.")
    print("    The publishing URL is built into the script; no targets config is needed.")
    variables["ROBOT_NEWS_API_KEY"] = "YOUR_ROBOT_NEWS_PAGE_KEY"
    print("model_api_key_env can override the default provider variable names above.")
    print(f"\nDetected OS: {platform.system()}. Use the instructions for your terminal:")
    print("\nmacOS / Linux — zsh or bash (current terminal):")
    for name, value in variables.items():
        command(f"export {name}='{value}'")
    print("Persist in ~/.zshrc for zsh or ~/.bashrc for bash, then open a new terminal.")
    print("For fish, use: set -gx NAME 'actual-key'; persist in ~/.config/fish/config.fish.")
    print("\nWindows — PowerShell (current terminal):")
    for name, value in variables.items():
        command(f"$env:{name} = '{value}'")
    print("Windows Command Prompt instead uses: set \"NAME=actual-key\"")
    print("To persist on Windows, open 'Edit environment variables for your account',")
    print("add User variables, then open a new terminal.")
    print("\nReplace placeholders with real keys; keep them out of Git and JSON.")
    print("Use the same terminal for the next steps. Scripts do not load .env.local.")
    print("Optional SSL_CERT_FILE: path to a trusted PEM CA bundle (e.g. corporate CA).")
    print("Optional SSL_CERT_DIR: path to an OpenSSL-compatible CA directory.")
    print("Leave both unset for system/certifi trust. To update the certificate bundle, run")
    print("this in the activated virtual environment:")
    command("python -m pip install --upgrade -r requirements.txt")
    pause()

    heading("3 / Confirm your environment, then run")
    quote = (lambda value: "'" + value.replace("'", "''") + "'") if platform.system() == "Windows" else shlex.quote
    options = ""
    if config_path != DEFAULT_CONFIG:
        options += " --config " + quote(config_path)
    if target != "production":
        options += " --target " + target
    print("Run the checker first and fix every reported failure:")
    command("python3 check_agent_env.py" + options)
    print("It checks credential presence/format and certificates without API calls.")
    print("After it passes, test the connection (publishes one real standard test post):")
    command("python3 test_robot_news.py" + options)
    print("Then generate drafts:")
    command("python3 news_agent.py" + options)
    print("To generate and publish articles:")
    command("python3 news_agent.py" + options + " --publish")
    print("\nThis guide only prints instructions. Run the commands when you are ready.")
    pause(final=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--target", choices=["localhost", "production"], default="production")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    args = parser.parse_args()
    color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
    walkthrough(args.config, args.target, color)


if __name__ == "__main__":
    main()
