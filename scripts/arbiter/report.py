"""Render scan + detect results as a Markdown report."""

SECTIONS = {
    "skill-name": "Duplicate skill names",
    "skill-description": "Similar skill descriptions",
    "hook": "Hooks on the same event and matcher",
    "mcp-name": "Duplicate MCP server names",
    "mcp-command": "Same MCP server under different names",
}


def to_markdown(result, findings):
    lines = ["# plugin-arbiter audit", "", "## Scanned", ""]
    lines += [f"- {s['name']}: {len(s['skills'])} skills, {len(s['hooks'])} hooks, {len(s['mcp'])} MCP servers"
              for s in result["sources"]]
    for kind, title in SECTIONS.items():
        group = [f for f in findings if f["kind"] == kind]
        lines += ["", f"## {title} ({len(group)})", ""]
        for f in group:
            lines.append(f"- {f['summary']}")
            lines += [f"  - {item}" for item in f["items"]]
        if not group:
            lines.append("None found.")
    if result["skipped"]:
        lines += ["", "## Skipped", ""] + [f"- {s}" for s in result["skipped"]]
    return "\n".join(lines) + "\n"
