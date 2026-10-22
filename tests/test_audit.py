import json
from pathlib import Path

import pytest

from arbiter.__main__ import main
from arbiter.detect import detect, matchers_overlap, tokens
from arbiter.scan import parse_frontmatter, scan

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def result(tmp_path):
    plugins = {f"{name}@test": [{"scope": "user", "installPath": str(FIXTURES / "plugins" / name)}]
               for name in ("alpha", "beta")}
    plugins["gone@test"] = [{"scope": "user", "installPath": str(tmp_path / "nowhere")}]
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": plugins}))
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
