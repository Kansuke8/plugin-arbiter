"""Collect skills, hooks and MCP servers from installed plugins and user/project config."""
import json
from pathlib import Path

# Every location arbiter reads. Claude Code layouts change between versions: edit them here only.
INSTALLED_PLUGINS = "plugins/installed_plugins.json"  # under ~/.claude
PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
PLUGIN_SKILLS = ("skills/*/SKILL.md", "commands/*.md")
PLUGIN_HOOKS = "hooks/hooks.json"
PLUGIN_MCP = ".mcp.json"
USER_SKILLS = ("skills/*/SKILL.md", "commands/*.md")  # under ~/.claude
USER_SETTINGS = ("settings.json",)
PROJECT_SKILLS = (".claude/skills/*/SKILL.md", ".claude/commands/*.md")
PROJECT_SETTINGS = (".claude/settings.json", ".claude/settings.local.json")
PROJECT_MCP = ".mcp.json"


def scan(claude_home, project=None):
    """Return {"sources", "disabled", "skipped"}. Missing or broken files are skipped, never raised."""
    claude_home = Path(claude_home)
    sources, disabled, skipped = [], [], []
    enabled = enabled_plugins(claude_home, project, skipped)

    installed = _read_json(claude_home / INSTALLED_PLUGINS, skipped)
    seen = set()
    for key, entries in _dict(installed).get("plugins", {}).items():
        if enabled.get(key) is False:
            disabled.append(key)
            continue
        for entry in entries:
            root = Path(entry.get("installPath", ""))
            # Project/local-scope installs only apply to the project they were installed in.
            other_project = entry.get("projectPath") and (
                not project or Path(entry["projectPath"]).resolve() != Path(project).resolve())
            if root in seen or other_project:
                continue
            seen.add(root)
            if root.is_dir():
                sources.append(_plugin(key, root, skipped))
            else:
                skipped.append(f"{key}: install path not found: {root}")

    sources.append(_config("user", claude_home, USER_SKILLS, USER_SETTINGS, None, skipped))
    if project:
        sources.append(_config("project", Path(project), PROJECT_SKILLS, PROJECT_SETTINGS, PROJECT_MCP, skipped))
    # Settings files are read twice (enabledPlugins, hooks), so a broken one would be listed twice.
    return {"sources": sources, "disabled": disabled, "skipped": list(dict.fromkeys(skipped))}


def enabled_plugins(claude_home, project, skipped):
    """Merge enabledPlugins from user, project and local settings; later files win per plugin."""
    # shortcut: managed (enterprise) settings are ignored; add them as the highest layer if needed.
    paths = [Path(claude_home) / rel for rel in USER_SETTINGS]
    paths += [Path(project) / rel for rel in PROJECT_SETTINGS] if project else []  # PROJECT_SETTINGS: project, then local
    merged = {}
    for path in paths:
        if path.is_file():
            merged.update(_dict(_dict(_read_json(path, skipped)).get("enabledPlugins")))
    return merged


def _source(name, root):
    return {"name": name, "root": str(root), "skills": [], "hooks": [], "mcp": {}}


def _plugin(key, root, skipped):
    src = _source(key, root)
    manifest = _dict(_read_json(root / PLUGIN_MANIFEST, skipped)) if (root / PLUGIN_MANIFEST).is_file() else {}
    _add_skills(src, root, PLUGIN_SKILLS, skipped)
    # plugin.json may point hooks/mcpServers at a path, a list of paths, or inline the config.
    for ref in _refs(manifest.get("hooks"), root / PLUGIN_HOOKS, root):
        data = ref if isinstance(ref, dict) else _read_json(ref, skipped)
        src["hooks"] += _hooks(_unwrap(data, "hooks"), ref if isinstance(ref, Path) else root / PLUGIN_MANIFEST)
    for ref in _refs(manifest.get("mcpServers"), root / PLUGIN_MCP, root):
        data = ref if isinstance(ref, dict) else _read_json(ref, skipped)
        src["mcp"].update(_dict(_unwrap(data, "mcpServers")))
    return src


def _config(name, root, skill_globs, settings_files, mcp_file, skipped):
    src = _source(name, root)
    _add_skills(src, root, skill_globs, skipped)
    for rel in settings_files:
        if (root / rel).is_file():
            src["hooks"] += _hooks(_dict(_read_json(root / rel, skipped)).get("hooks"), root / rel)
    if mcp_file and (root / mcp_file).is_file():
        src["mcp"].update(_dict(_unwrap(_read_json(root / mcp_file, skipped), "mcpServers")))
    return src


def _refs(declared, default, root):
    refs = [default] if default.is_file() else []
    for d in declared if isinstance(declared, list) else [declared] if declared else []:
        ref = d if isinstance(d, dict) else root / d
        if ref not in refs:
            refs.append(ref)
    return refs


def _hooks(events, origin):
    out = []
    for event, groups in _dict(events).items():
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict):
                continue
            commands = [h.get("command") or h.get("prompt") or h.get("type", "")
                        for h in group.get("hooks", []) if isinstance(h, dict)]
            out.append({"event": event, "matcher": str(group.get("matcher") or ""),
                        "commands": commands, "path": str(origin)})
    return out


def _add_skills(src, root, globs, skipped):
    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            try:
                meta = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            except OSError as e:
                skipped.append(f"could not read {path} ({type(e).__name__})")
                continue
            default = path.parent.name if path.name == "SKILL.md" else path.stem
            src["skills"].append({"name": meta.get("name") or default,
                                  "description": meta.get("description", ""), "path": str(path)})


def parse_frontmatter(text):
    """Read flat `key: value` frontmatter, including `>` / `|` block scalars."""
    # shortcut: not a YAML parser (no nesting, lists or escapes); add PyYAML if skills start needing it.
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1] in (" ", "\t") and key:
            out[key] = (out[key] + " " + line.strip()).strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            out[key] = "" if value in (">", "|", ">-", "|-") else value.strip("\"'")
    return out


def _read_json(path, skipped):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        skipped.append(f"could not read {path} ({type(e).__name__})")
        return None


def _unwrap(data, key):
    return data[key] if isinstance(data, dict) and key in data else data


def _dict(value):
    return value if isinstance(value, dict) else {}
