# plugin-arbiter

A Claude Code plugin that finds conflicts between your installed plugins.

As plugins pile up, they start to interfere: two skills with the same name, skills whose descriptions
compete for the same requests, hooks fired on the same event, the same MCP server registered twice.
`plugin-arbiter` scans everything installed and reports the candidates. It runs only when you call it.

## Install (development)

```bash
claude --plugin-dir /path/to/plugin-arbiter
```

Then run `/plugin-arbiter:audit` inside a project.

## What `/audit` checks (v0.1)

| Check | How |
|---|---|
| Duplicate skill names | same `name` across plugins, user and project skills |
| Similar skill descriptions | token overlap (Jaccard; CJK text uses character bigrams) |
| Overlapping hooks | same event and an overlapping matcher (`*`/empty matches everything) |
| Duplicate MCP servers | same server name, or the same command/URL under different names |

It reads `~/.claude/plugins/installed_plugins.json`, each plugin's `plugin.json`, `skills/`, `commands/`,
`hooks/hooks.json` and `.mcp.json`, plus `~/.claude/settings.json` and the project's `.claude/settings*.json`,
`.claude/skills/` and `.mcp.json`. All paths live at the top of `scripts/arbiter/scan.py`.
Missing or unreadable files are listed under "Skipped" instead of failing.

Plugins turned off in `enabledPlugins` are left out. The user, project (`.claude/settings.json`) and local
(`.claude/settings.local.json`) values are merged with the same precedence as Claude Code: local > project > user.
Plugins with no entry are checked. Plugins installed at project scope are checked only in that project.

The report lists candidates, not confirmed conflicts. Nothing is written.

## Standalone use

```bash
python scripts/audit.py --project . --threshold 0.3
```

Python 3.10+, standard library only.

## Roadmap

- v0.2: have Claude judge each candidate pair for real contradictions and suggest a priority
- v0.3: `/apply` — propose `enabledPlugins` and CLAUDE.md priority rules as a diff, write after approval
- v0.4: optional PreToolUse hook that blocks lower-priority MCP calls

## Development

```bash
pip install pytest
python -m pytest
```

## License

MIT
