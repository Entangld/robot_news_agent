#!/usr/bin/env python3
"""Publish one standard test post using the selected target's environment key."""
import argparse
import json
import sys
from agent_config import DEFAULT_CONFIG, load_config, target_settings
from robot_news import RobotNewsClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Agent config file (default: config.json beside this script)")
    parser.add_argument("--target", choices=["localhost", "production"], default="production", help="Publishing target (default: production)")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        base, key = target_settings(args.target)
        response = RobotNewsClient(key, base_url=base, page_id=config.get("page_id")).publish_standard_message()
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
        print(f"Connection test failed: {exc}", file=sys.stderr)
        return 1
    print("Connection successful. A standard test post was published.")
    print(json.dumps(response, indent=2))
    print("You can now run news_agent.py with the same config and target.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
