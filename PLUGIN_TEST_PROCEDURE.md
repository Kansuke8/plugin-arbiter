# Field test procedure

Install plugins step by step into a test-bed app (an email-sorting app) and record the conflicts that actually happen, so they can be fed back into plugin-arbiter.

## Purpose

- This is a **one-round field survey to run before starting v0.2** (semantic judgment). The goal is not to verify v0.1 but to **collect ground truth for v0.2**.
- Do not leave observed conflicts as notes: **turn them into fixtures and tests** (step 7 of the common flow). After this one round, development runs on fixtures and tests, not on the test bed.
- The v0.2 judgment (the part whose answer varies between runs) is measured with `claude plugin eval`, not pytest. Introduce it when starting the v0.2 implementation.

## Ground rules

- Install everything at **local scope** ("Install for you, in this repo only"), so other projects are not affected.
- Add **one group at a time**. Adding everything at once makes it impossible to tell which plugin caused what.
- Groups are **cumulative** (plugins from earlier groups stay installed). Only when a conflict has a "high" severity, temporarily disable every plugin except the ones involved to isolate it.
- **Do not connect to a real mailbox** during the test. Work with dummy data only.
- Hook plugins execute code locally. Do not launch them outside the test-bed folder.
- Install only plugins from the official marketplace (claude-plugins-official).
- Type commands by hand, so that symbols such as `❯` do not get mixed in when copying.

## Setup

1. Create a test-bed folder and initialize git (if you push to GitHub, set up a noreply email address).
2. Start `claude` in the folder.
3. Create `notes/plugin-log.md` for records (template at the end).

## Group 0: baseline (nothing added)

Start with only the plugins already installed at user scope.

1. Keep the app minimal: loading dummy emails from JSON and one function that sorts them by rules is enough (`/audit` is a static scan, so app features do not affect its result).
2. Save the raw output with `python <path to plugin-arbiter>/scripts/audit.py --project . > notes/audit-group0.md`.
3. Commit in this state (it is the baseline for later comparisons).

## Common flow for each group

1. Install the plugins (choose local scope).
2. `/reload-plugins`
3. Record the name and version of each installed plugin (check the Installed tab of `/plugin`).
4. Do the work that exercises the group (see "Task to try" below).
5. Take notes on what you noticed: which one ran, what differed from your intent, which instructions clashed.
   - Confirm which skills and hooks were actually invoked from the session transcript (the jsonl files under `~/.claude/projects/`), not from impressions.
   - For conflicts with a "high" severity, repeat the same request 2-3 times and check whether it reproduces every time.
     - Run each repetition **serially**. Running them in parallel lets one run see the other's edits.
     - Between repetitions, reset the working tree to its initial state (for example `git stash push -u`).
   - Classify each conflict into one of three layers (see the template).
6. Save the raw output with `python <path to plugin-arbiter>/scripts/audit.py --project . > notes/audit-groupN.md`, and compare the diff from the previous group against your notes.
7. Feed misses and false positives back to plugin-arbiter: rewrite each one as a minimal dummy plugin under `tests/fixtures/plugins/` (**do not copy the original text**), and add one test that does not pass yet.
8. Commit the notes and code.

### Verify against the official docs before adding a gap

Before turning an observation into a fixture and a failing test, check the intended behavior in the official Claude Code docs. An observation may be expected behavior, not a gap.

Example: a command that shares its name with a bundled skill looked like a conflict. The docs say plugin commands are invoked with a namespace (`/plugin-name:command`), so they do not replace the bundled one. It was not a conflict, and arbiter does not report it.

## Group 1: code review

```
/plugin install code-review@claude-plugins-official
/plugin install pr-review-toolkit@claude-plugins-official
```

**Task to try**: add one feature to the sorting rules, then ask "review this change". Check which review feature was used, and whether it got mixed up with the built-in `/code-review` or with a review skill from a plugin installed at user scope.

## Group 2: development workflow

```
/plugin install superpowers@claude-plugins-official
/plugin install feature-dev@claude-plugins-official
```

**Task to try**: ask "add a feature that counts emails per label". Check which procedure was followed (starting from brainstorming, TDD, or feature-dev's stages), and whether it contradicts the "minimal change" policy of any plugin installed at user scope.

## Group 3: hooks

```
/plugin install security-guidance@claude-plugins-official
/plugin install hookify@claude-plugins-official
```

**Task to try**: edit the config-loading part. Check how many times and in what order warnings and hooks fired, and whether any appeared twice. This is the only group that can confirm the v0.1 duplicate-hook detection in practice, so do not skip it.

## Optional: comparison without a user-scope plugin

A plugin installed at user scope is always enabled, so you cannot tell whether it is the cause of a conflict. Only if a conflict with it was "high" in group 2, disable it and repeat the same request once.

## Optional groups

Run these only if they are needed to decide the scope of v0.2.

### Group 4: git

```
/plugin install commit-commands@claude-plugins-official
```

**Task to try**: ask it to commit your changes. Check whether the commit message style and procedure clash with built-in behavior or with instructions from other plugins.

The github plugin (MCP) needs GitHub authentication, so it is optional. Add it only if the test bed is hosted on GitHub.

### Group 5: simplification

```
/plugin install code-simplifier@claude-plugins-official
```

**Task to try**: ask it to "tidy up this module". Check how it interacts with the policies of plugins installed at user scope and with the superpowers procedure.

## When things go wrong

- If "plugin not found" appears, refresh the list with `/plugin marketplace update claude-plugins-official`, or search for the name in the Discover tab of `/plugin`.
- If a plugin was renamed or cannot be found, do not hunt for it: record that and move on.

## Cleanup

Remove plugins you have finished testing with:

```
/plugin uninstall <plugin name>@claude-plugins-official
```

## Record template (notes/plugin-log.md)

```markdown
## Group N: <topic> (YYYY-MM-DD)

### Environment
- Claude Code version:
- Installed plugins: name@marketplace:version

### Tasks tried
- 

### Conflicts and oddities noticed
- Situation:
  - What happened:
  - Suspected plugin:
  - Evidence (relevant jsonl location):
  - Reproduction (M of N runs):
  - Severity (high/medium/low):
  - Layer: (a) v0.1 should catch it / (b) needs semantic judgment (v0.2) / (c) not visible statically (runtime-injected text, built-in features, etc.)

### /audit result (notes/audit-groupN.md)
- Number of findings:
- Things in the notes that /audit missed:
- Things /audit reported that were actually fine:
- Turned into fixtures and tests:
```
