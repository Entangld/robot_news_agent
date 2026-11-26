"""Small shared helpers for terminal output."""

def styled(text, code, enabled):
    return f"\033[{code}m{text}\033[0m" if enabled else text


def page_table(pages, selected_id, color=False, *, highlight_missing=False):
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
        if highlight_missing and row[0].startswith("* ") and row[3] == "not configured":
            cells = [styled(str(value).ljust(width), "1;31", color) for value, width in zip(row, widths)]
        print(" | ".join(cells))
    if not rows:
        print("No owned pages returned.")
    print("\n* Publishing destination. Schedule: not recorded = external scheduler unknown.")

