"""Find conflict candidates between sources. Pure functions over scan() output."""
import re
from itertools import combinations

STOPWORDS = frozenset("the and for use when this that with from your you are any not only into its".split())
WILDCARD_MATCHERS = {"", "*", ".*"}
# Built-in slash commands and their aliases (bundled skills such as `code-review` are not included).
# Source: https://code.claude.com/docs/en/commands.md, fetched 2026-10-28.
# Static snapshot: the set changes between Claude Code versions, so refresh it from that page.
BUILTIN_COMMANDS = frozenset("""
    add-dir advisor agents artifacts auto-mode-setup autocompact autofix-pr background bg branch btw bug share cd
    chrome clear reset new color compact config settings context copy cost design-login desktop app diff effort exit
    quit export fast feedback fork focus goal heapdump help hooks ide import init insights install-github-app install-
    slack-app keybindings list-agents peers login logout mcp memory mobile ios android model output-style passes
    permissions allowed-tools plan plugin powerup privacy-settings radio rate-limit-options recap release-notes
    reload-plugins reload-skills remote-control rc remote-env rename resume continue rewind checkpoint undo sandbox
    schedule routines scroll-speed security-review setup-bedrock setup-vertex skill-doctor skills status statusline
    stickers stop subtask tasks bashes team-onboarding teleport tp terminal-setup theme tui ultrareview upgrade usage
    stats usage-credits voice web-setup workflows
    """.split())


def detect(sources, threshold=0.3):
    return (duplicate_skill_names(sources) + similar_skill_descriptions(sources, threshold)
            + overlapping_hooks(sources) + duplicate_mcp_servers(sources) + builtin_name_shadowing(sources))


def duplicate_skill_names(sources):
    # Agents live in their own namespace: they only collide with other agents, never with skills or commands.
    by_name = {}
    for src, skill in _items(sources, "skills"):
        by_name.setdefault((skill["kind"] == "agent", skill["name"].lower()), []).append((src, skill))
    return [_finding("skill-name", f"`{name}` is defined by {len({s for s, _ in hits})} sources",
                     [f"{s}: {sk['path']}" for s, sk in hits])
            for (_, name), hits in sorted(by_name.items()) if len({s for s, _ in hits}) > 1]


def similar_skill_descriptions(sources, threshold):
    skills = [(src, sk, tokens(sk["description"])) for src, sk in _items(sources, "skills")]
    out = []
    for (sa, a, ta), (sb, b, tb) in combinations(skills, 2):
        if sa == sb or not ta or not tb:
            continue
        score = len(ta & tb) / len(ta | tb)
        if score >= threshold:
            out.append(_finding("skill-description",
                                f"`{sa}:{a['name']}` ~ `{sb}:{b['name']}` (similarity {score:.2f})",
                                [f"{sa}: {a['path']}", f"{sb}: {b['path']}"], score=score))
    return sorted(out, key=lambda f: -f["score"])


def overlapping_hooks(sources):
    out = []
    for (sa, a), (sb, b) in combinations(list(_items(sources, "hooks")), 2):
        if sa != sb and a["event"] == b["event"] and matchers_overlap(a["matcher"], b["matcher"]):
            out.append(_finding("hook", f"{a['event']}: `{sa}` [{a['matcher'] or '*'}] and `{sb}` [{b['matcher'] or '*'}]",
                                [f"{sa}: {a['path']}", f"{sb}: {b['path']}"]))
    return out


def duplicate_mcp_servers(sources):
    by_name, by_command = {}, {}
    for s in sources:
        for name, cfg in s["mcp"].items():
            cfg = cfg if isinstance(cfg, dict) else {}
            by_name.setdefault(name.lower(), []).append((s["name"], name))
            command = cfg.get("url") or " ".join([cfg.get("command", "")] + [str(a) for a in cfg.get("args", [])])
            by_command.setdefault(command.strip(), []).append((s["name"], name))
    out = [_finding("mcp-name", f"`{name}` is registered by {len(hits)} sources", [f"{s}: {n}" for s, n in hits])
           for name, hits in sorted(by_name.items()) if len(hits) > 1]
    # Same command under one shared name is already reported above.
    out += [_finding("mcp-command", f"`{command}` runs as {len(hits)} servers", [f"{s}: {n}" for s, n in hits])
            for command, hits in sorted(by_command.items())
            if command and len(hits) > 1 and len({n.lower() for _, n in hits}) > 1]
    return out


def builtin_name_shadowing(sources, builtin_names=BUILTIN_COMMANDS):
    """Plugin commands named like a built-in. Only commands count: skills and agents are other namespaces."""
    return [_finding("builtin-name", f"`{src}:/{sk['name']}` may be confused with built-in command `/{sk['name'].lower()}`",
                     [f"{src}: {sk['path']}"])
            for src, sk in _items(sources, "skills") if sk["kind"] == "command" and sk["name"].lower() in builtin_names]


def matchers_overlap(m1, m2):
    # shortcut: `a|b` alternatives are compared literally; real regex matchers (e.g. `mcp__.*`) need regex intersection.
    if m1 in WILDCARD_MATCHERS or m2 in WILDCARD_MATCHERS:
        return True
    return bool(set(m1.split("|")) & set(m2.split("|")))


def tokens(text):
    """English words of 3+ chars, plus character bigrams for non-ASCII (CJK) text."""
    text = text.lower()
    words = {w for w in re.findall(r"[a-z0-9]{3,}", text) if w not in STOPWORDS}
    runs = re.findall(r"[^\x00-\x7f\s、。,.()()「」]+", text)
    return words | {run[i:i + 2] for run in runs for i in range(len(run) - 1)}


def _items(sources, key):
    for s in sources:
        for item in s[key]:
            yield s["name"], item


def _finding(kind, summary, items, score=None):
    return {"kind": kind, "summary": summary, "items": items, "score": score}
