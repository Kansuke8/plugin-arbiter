import json
from pathlib import Path

import pytest

from arbiter.__main__ import main
from arbiter.detect import detect, matchers_overlap, tokens
from arbiter.scan import parse_frontmatter, scan

FIXTURES = Path(__file__).parent / "fixtures"


def install(home, plugins, **extra):
    """Write installed_plugins.json under `home` for fixture plugins installed at user scope."""
    entries = {f"{name}@test": [{"scope": "user", "installPath": str(FIXTURES / "plugins" / name)}] for name in plugins}
    (home / "plugins").mkdir(parents=True)
    (home / "plugins" / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {**entries, **extra}}))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture
def result(tmp_path):
    install(tmp_path, ["alpha", "beta"], **{"gone@test": [{"scope": "user", "installPath": str(tmp_path / "nowhere")}]})
    return scan(tmp_path, FIXTURES / "project")


def kinds(findings, kind):
    return [f for f in findings if f["kind"] == kind]


def test_scan_reads_every_source(result):
    by_name = {s["name"]: s for s in result["sources"]}
    assert sorted(sk["name"] for sk in by_name["alpha@test"]["skills"]) == ["deploy", "review"]
    assert by_name["beta@test"]["skills"][0]["description"] == "Review pull request code changes for bugs and security issues."
    assert [h["matcher"] for h in by_name["beta@test"]["hooks"]] == ["Edit|Bash"]
    assert set(by_name["beta@test"]["mcp"]) == {"gh"}
    assert [h["event"] for h in by_name["project"]["hooks"]] == ["PostToolUse"]


def test_missing_paths_are_skipped_not_raised(result):
    skipped = "\n".join(result["skipped"])
    assert "gone@test" in skipped
    assert "missing.json" in skipped


def test_detects_expected_conflicts_only(result):
    findings = detect(result["sources"])
    assert [f["summary"] for f in kinds(findings, "skill-name")] == ["`review` is defined by 2 sources"]
    similar = kinds(findings, "skill-description")
    assert len(similar) == 1 and "deploy" not in similar[0]["summary"]
    hooks = kinds(findings, "hook")
    assert len(hooks) == 1 and "PreToolUse" in hooks[0]["summary"]  # project's PostToolUse does not collide
    assert kinds(findings, "mcp-name")[0]["items"] == ["alpha@test: github", "project: GitHub"]
    assert kinds(findings, "mcp-command")[0]["items"] == ["alpha@test: github", "beta@test: gh"]


def test_enabled_plugins_precedence_local_over_project_over_user(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    install(home, ["alpha", "beta"])
    write_json(home / "settings.json", {"enabledPlugins": {"alpha@test": False, "beta@test": False}})
    write_json(project / ".claude/settings.json", {"enabledPlugins": {"alpha@test": True, "beta@test": True}})
    write_json(project / ".claude/settings.local.json", {"enabledPlugins": {"beta@test": False}})

    result = scan(home, project)
    names = [s["name"] for s in result["sources"]]
    assert "alpha@test" in names  # project re-enables what user disabled
    assert "beta@test" not in names and result["disabled"] == ["beta@test"]  # local wins over project
    assert detect(result["sources"]) == []  # alpha alone conflicts with nothing


def test_unlisted_plugins_stay_enabled(result):
    assert result["disabled"] == []


def test_project_scoped_install_only_applies_to_its_project(tmp_path):
    home, here, elsewhere = tmp_path / "home", tmp_path / "here", tmp_path / "elsewhere"
    here.mkdir()
    entry = {"scope": "project", "installPath": str(FIXTURES / "plugins" / "beta"), "projectPath": str(elsewhere)}
    install(home, ["alpha"], **{"beta@test": [entry]})
    assert "beta@test" not in [s["name"] for s in scan(home, here)["sources"]]
    assert "beta@test" in [s["name"] for s in scan(home, elsewhere)["sources"]]


def test_matchers_overlap():
    assert matchers_overlap("Bash", "Edit|Bash")
    assert matchers_overlap("", "Write")
    assert not matchers_overlap("Edit", "Write")


def test_tokens_handle_japanese():
    assert tokens("コードをレビュー") & tokens("コードレビューを行う")
    assert "the" not in tokens("the review")


def test_frontmatter():
    assert parse_frontmatter("---\nname: x\ndescription: |\n  a\n  b\n---\nbody") == {"name": "x", "description": "a b"}
    assert parse_frontmatter("no frontmatter") == {}


def test_cli_prints_report(tmp_path, capsys):
    main(["--claude-home", str(tmp_path), "--project", str(FIXTURES / "project")])
    out = capsys.readouterr().out
    assert out.startswith("# plugin-arbiter audit")
    assert "installed_plugins.json" in out  # missing file reported under Skipped
