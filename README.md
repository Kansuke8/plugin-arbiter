<p align="center"><img src=".claude-plugin/icon.png" width="96" alt=""></p>

# plugin-arbiter

A Claude Code plugin that finds conflicts between your installed plugins.

## The problem

Every plugin you install adds skills, hooks and MCP servers to the same session. As the list grows, they start to interfere:

- **Two skills with the same name**, or with descriptions that compete for the same requests, so Claude picks the wrong one.
- **Hooks on the same event and matcher**, such as two `PreToolUse` hooks on `Bash` that both rewrite or block the same command.
- **The same MCP server registered twice**, under one name or two, which duplicates tools and wastes context.

Nothing warns you about this. You only see the symptoms: a skill that never triggers, a hook that fires twice, a tool list full of near-duplicates.

`plugin-arbiter` scans every enabled plugin, plus your user and project config, and reports the conflict candidates in one place. It only runs when you call it, and it never changes your files.

## Install

In Claude Code:

```
/plugin marketplace add Kansuke8/plugin-arbiter
/plugin install plugin-arbiter@plugin-arbiter
```

On Claude Code 2.1.275 or later you can do it in one step:

```
/plugin install plugin-arbiter --marketplace Kansuke8/plugin-arbiter
```

Requires Python 3.10+ on your `PATH`. No other dependencies.

## Usage

Open Claude Code in a project and run:

```
/plugin-arbiter:audit
```

Claude runs the scanner, shows the report, and summarizes the candidates that matter most.

You can also run the scanner directly, without Claude:

```bash
python scripts/audit.py                       # audit the current directory
python scripts/audit.py --project path/to/app # audit another project
python scripts/audit.py --threshold 0.2       # show more similar-description pairs
```

## Example report

This report comes from the dummy plugins in [`tests/fixtures/`](tests/fixtures/). The two plugins `alpha` and `beta` and one project are built to conflict on purpose:

```markdown
# plugin-arbiter audit

## Scanned

- alpha@demo: 2 skills, 1 hooks, 1 MCP servers
- beta@demo: 1 skills, 1 hooks, 1 MCP servers
- user: 0 skills, 0 hooks, 0 MCP servers
- project: 0 skills, 1 hooks, 1 MCP servers

## Duplicate skill names (1)

- `review` is defined by 2 sources
  - alpha@demo: skills/review/SKILL.md
  - beta@demo: skills/review/SKILL.md

## Similar skill descriptions (1)

- `alpha@demo:review` ~ `beta@demo:review` (similarity 0.60)
  - alpha@demo: skills/review/SKILL.md
  - beta@demo: skills/review/SKILL.md

## Hooks on the same event and matcher (1)

- PreToolUse: `alpha@demo` [Bash] and `beta@demo` [Edit|Bash]
  - alpha@demo: hooks/hooks.json
  - beta@demo: hooks/extra.json

## Duplicate MCP server names (1)

- `github` is registered by 2 sources
  - alpha@demo: github
  - project: GitHub

## Same MCP server under different names (1)

- `npx -y @mcp/github` runs as 2 servers
  - alpha@demo: github
  - beta@demo: gh

## Skipped

- could not read .../tests/fixtures/plugins/beta/hooks/missing.json (FileNotFoundError)
```

The last line shows how missing files are handled: `beta` points to a hooks file that does not exist, so the file is listed under "Skipped" and the audit keeps going. (The absolute path is shortened here.)

## What it checks

| Check | How |
|---|---|
| Duplicate skill names | Same `name` across plugins, user skills and project skills |
| Similar skill descriptions | Token overlap (Jaccard). English uses words; Japanese and other non-ASCII text uses character bigrams |
| Overlapping hooks | Same event, and matchers that overlap (`*` or an empty matcher matches everything; `a\|b` is split) |
| Duplicate MCP servers | Same server name, or the same command or URL under different names |

The report lists **candidates** found by string matching, not confirmed conflicts. Deciding whether two skills really contradict each other is planned for v0.2.

### What it reads

- `~/.claude/plugins/installed_plugins.json`, and for each plugin: `.claude-plugin/plugin.json`, `skills/*/SKILL.md`, `commands/*.md`, `hooks/hooks.json` (plus any hook files that `plugin.json` points to) and `.mcp.json`
- `~/.claude/settings.json` and `~/.claude/skills/`
- The project's `.claude/settings.json`, `.claude/settings.local.json`, `.claude/skills/` and `.mcp.json`

All paths are defined at the top of [`scripts/arbiter/scan.py`](scripts/arbiter/scan.py), so a layout change in Claude Code needs a fix in one place only.

### What it skips

- Plugins turned off in `enabledPlugins`. User, project and local settings are merged with the same precedence as Claude Code (local > project > user). Plugins with no entry are checked.
- Plugins installed at project scope for a different project.
- Files that are missing or unreadable. They are listed in the report instead of stopping the audit.

### Known limits

- Managed (enterprise) settings and MCP servers in `~/.claude.json` are not read yet.
- MCP *tool* names are not compared, because that would mean starting every server. Servers are compared by name and command.
- Hook matchers that are full regular expressions (such as `mcp__.*`) are compared as plain text.

## Roadmap

- **v0.1** `/audit`: detect conflict candidates mechanically and report them *(current)*
- **v0.2**: have Claude read each candidate pair, judge whether it is a real contradiction, and suggest which plugin should win
- **v0.3** `/apply`: propose `enabledPlugins` and CLAUDE.md priority rules as a diff, and write them only after you approve
- **v0.4**: optional `PreToolUse` hook that blocks calls to lower-priority MCP servers

## Development

The plugin needs no dependencies. Tests use pytest, which is declared as a `dev` extra in `pyproject.toml`. Install it into a virtual environment rather than your global Python:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m pytest
```

Tests run only against the dummy plugins in `tests/fixtures/`, never against your real `~/.claude`.

To try your local copy in Claude Code:

```bash
claude --plugin-dir /path/to/plugin-arbiter
```

## License

[MIT](LICENSE)
