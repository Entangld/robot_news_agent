#!/usr/bin/env python3
"""Check configured environment references and required credentials and inspect owned pages and saved news schedules."""
import argparse
import os
import shutil
import textwrap
import sys
from agent_config import DEFAULT_CONFIG, load_config, model_key, target_settings
from robot_news import RobotNewsClient, tls_context


def styled(text, code, enabled):
    return f"\033[{code}m{text}\033[0m" if enabled else text


def page_table(pages, selected_id, color=False):
    headers = ("Page", "Page ID", "Access", "News plan", "Schedule", "Every (min)", "Timezone")
    rows = []
    for entry in pages:
        page = entry["page"]
        scheduling = entry.get("scheduling") or {}
        schedule = scheduling.get("host_schedule")
        rows.append((
            ("* " if page["id"] == selected_id else "") + page["name"], page["id"], page["visibility"],
            "configured" if entry["configured"] else "not configured",
            scheduling["status"] if schedule else "not recorded",
            str(schedule["frequency_minutes"]) if schedule else "-",
            schedule["timezone"] if schedule else "-",
        ))
    widths = [max(len(str(row[i])) for row in [headers, *rows]) for i in range(len(headers))]
    print("\nOwned pages (set page_id in your config file to a Page ID below):")
    print(styled(" | ".join(value.ljust(width) for value, width in zip(headers, widths)), "1;36", color))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        cells = [str(value).ljust(width) for value, width in zip(row, widths)]
        cells[3] = styled(cells[3], "32" if row[3] == "configured" else "33", color)
        cells[4] = styled(cells[4], "32" if row[4] == "active" else "33", color)
        print(" | ".join(cells))
    if not rows:
        print("No owned pages returned.")
    print("\n* Publishing destination. Schedule: not recorded = external scheduler unknown.")


def check(config, target_name, *, color=None):
    if color is None:
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    def ok(message):
        print(styled("OK: ", "32", color) + message)

    errors = []
    try:
        target_settings(target_name)
        ok(f"{target_name} URL and publishing-key format")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    try:
        context = tls_context()
        if not context.get_ca_certs():
            errors.append("No trusted CA certificates loaded. Install certifi or set SSL_CERT_FILE.")
        else:
            ok("trusted TLS certificates loaded")
    except (ValueError, OSError) as exc:
        errors.append(f"Cannot load trusted TLS certificates: {exc}")
    provider = config.get("provider")
    if not config.get("model"):
        errors.append("Configure a model in config.json.")
    try:
        model_key(provider, config.get("model_api_key_env", {}))
        ok(f"{provider} credential configured")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    try:
        base, key = target_settings(target_name)
        client = RobotNewsClient(key, base_url=base, page_id=config.get("page_id"))
        pages = client.pages()
        destination = None
        selected_id = None
        configured_id = config.get("page_id")
        valid_ids = {value for entry in pages for value in
                     (entry["page"]["id"], entry["page"].get("public_id")) if value}
        if configured_id is not None and configured_id not in valid_ids:
            errors.append(f"Configured page_id {configured_id!r} does not match any page you own. "
                          "Please configure page_id correctly in your config file using one of the valid "
                          "page IDs shown in the Owned pages list, or remove page_id to use your default page.")
        else:
            try:
                destination = client.destination()
                selected_id = destination["page_id"]
            except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                errors.append(f"Cannot resolve publishing destination: {exc}. "
                              "Set page_id in your config file to an owned page ID from the Owned pages list, "
                              "or remove page_id to use your default page.")
        page_table(pages, selected_id, color)
        selected = next((entry for entry in pages if entry["page"]["id"] == selected_id), None)
        if destination is not None:
            print(f"Publishing destination: {destination['name']} ({selected_id})")
            if not selected or not selected["configured"]:
                errors.append("Save a news plan for the publishing destination in Robot News page settings.")
        print("Schedule records are host-reported; this check cannot verify a live scheduler or local cron.")
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
        errors.append(f"Cannot check Robot News pages: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Agent config file (default: config.json beside this script)")
    parser.add_argument("--target", choices=["localhost", "production"], default="production", help="Publishing target (default: production)")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    args = parser.parse_args()
    stdout_color = not args.no_color and "NO_COLOR" not in os.environ and sys.stdout.isatty()
    stderr_color = not args.no_color and "NO_COLOR" not in os.environ and sys.stderr.isatty()
    try:
        errors = check(load_config(args.config), args.target, color=stdout_color)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        errors = [str(exc)]
    sys.stdout.flush()
    for error in errors:
        message = textwrap.fill("FAIL: " + error, width=max(60, min(100, shutil.get_terminal_size().columns)),
                                subsequent_indent="      ")
        print("\n" + styled(message, "1;31", stderr_color), file=sys.stderr)
    if errors:
        return 1
    print("Configuration passed. Robot News authenticated; model credentials checked locally only.")
    print("Next: run python3 test_robot_news.py from the agent directory using the same configuration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
