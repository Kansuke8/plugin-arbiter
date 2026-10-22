---
name: audit
description: >
  Audit installed Claude Code plugins for conflicts: duplicate skill names,
  skills with overlapping descriptions, hooks registered on the same event and
  matcher, and duplicate MCP servers. Read-only report. Use for "audit plugins",
  "plugin conflicts", "which plugins overlap", /audit.
---

# Plugin conflict audit

Run the scanner from the user's project directory:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py"
```

Use `python` instead of `python3` if `python3` is not available (common on Windows).
Pass `--threshold 0.2` to see more description pairs, or `--project <dir>` to audit another project.

The script prints a Markdown report. Then:

1. Show the user a short summary: how many candidates per section, and the few that matter most.
   Hooks on the same event and duplicate MCP servers usually matter more than similar descriptions.
2. Mention the "Skipped" section if present, so the user knows what was not checked.
3. The report lists *candidates* found by string matching, not confirmed conflicts. Say so.

Do not change any settings or files. This skill only reports.
