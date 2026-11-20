#!/usr/bin/env python3
"""Check configured environment references and required credentials without API calls."""
import argparse
import sys
from agent_config import DEFAULT_CONFIG, load_config, model_key, target_settings
from robot_news import tls_context


def check(config, target_name):
    errors = []
    try:
        target_settings(target_name)
        print(f"OK: {target_name} URL and publishing-key format")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    try:
        context = tls_context()
        if not context.get_ca_certs():
            errors.append("No trusted CA certificates loaded. Install certifi or set SSL_CERT_FILE.")
        else:
            print("OK: trusted TLS certificates loaded")
    except (ValueError, OSError) as exc:
        errors.append(f"Cannot load trusted TLS certificates: {exc}")
    provider = config.get("provider")
    if not config.get("model"):
        errors.append("Configure a model in config.json.")
    try:
        model_key(provider, config.get("model_api_key_env", {}))
        print(f"OK: {provider} credential configured")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Agent config file (default: config.json beside this script)")
    parser.add_argument("--target", choices=["localhost", "production"], default="production", help="Publishing target (default: production)")
    args = parser.parse_args()
    try:
        errors = check(load_config(args.config), args.target)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        errors = [str(exc)]
    for error in errors:
        print("FAIL: " + error, file=sys.stderr)
    if errors:
        return 1
    print("Configuration passed. Credential presence and format checked; authentication requires the connection test.")
    print("Next: run python3 test_robot_news.py from the agent directory using the same configuration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
