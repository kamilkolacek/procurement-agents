"""Black-box tests for the Claude Code hooks: feed them hook JSON, check exit codes."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
SCAN = ROOT / "scripts" / "scan_secrets.py"


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    shutil.copy(HOOKS / "policy.json", tmp_path / ".claude" / "hooks" / "policy.json")
    return tmp_path


def run_hook(repo, script, event):
    env = {"CLAUDE_PROJECT_DIR": str(repo), "PATH": "/usr/bin:/bin"}
    return subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)


def pre(repo, tool, **tool_input):
    return run_hook(repo, "pre_tool.py", {"tool_name": tool, "tool_input": tool_input})


A = "agents/spend-classification"


@pytest.mark.parametrize("path", [
    f"{A}/data/real/ap_2026.csv", ".env", ".env.local", "secrets/credentials.json",
    "deploy.pem", ".claude/OVERRIDE",
])
def test_read_blocked(repo, path):
    assert pre(repo, "Read", file_path=str(repo / path)).returncode == 2


def test_read_ok(repo):
    assert pre(repo, "Read", file_path=str(repo / A / "STATUS.md")).returncode == 0


def test_grep_glob_into_real_blocked(repo):
    assert pre(repo, "Grep", pattern="IBAN", path=str(repo / A / "data/real")).returncode == 2
    assert pre(repo, "Glob", pattern="**/data/real/*.csv").returncode == 2


@pytest.mark.parametrize("cmd", [
    "rm -rf build", "rm -fr /", "rm -r -f x", "sudo rm -Rf x", "rm --recursive --force x",
    "git push --force origin main", "git push -f", "git push origin +main",
    "git commit --no-verify -m x",
    f"cat {A}/data/real/ap.csv", "cat .env", "head -5 .env.production",
    "echo 'x | y' > .claude/OVERRIDE",
    f"echo x >> {A}/evals/golden/answers.csv", "sed -i '' s/a/b/ governance/DATA_POLICY.md",
    "cp /tmp/x .claude/settings.json",
    "uv run python -m shared.evals.harness --agent x --update-baseline",
])
def test_bash_blocked(repo, cmd):
    r = pre(repo, "Bash", command=cmd)
    assert r.returncode == 2, cmd
    assert "BLOCKED" in r.stderr


@pytest.mark.parametrize("cmd", [
    "uv run pytest", "rm build/tmp.txt", "git push origin main", "ls agents",
    f"cat {A}/evals/golden/answers.csv", "cat governance/DATA_POLICY.md", "make check",
    "git status", "echo hi > scratch.txt",
])
def test_bash_allowed(repo, cmd):
    assert pre(repo, "Bash", command=cmd).returncode == 0, cmd


@pytest.mark.parametrize("path", [
    f"{A}/evals/golden/answers.csv", "governance/RISK_REGISTER.md", ".claude/settings.json",
    ".claude/hooks/pre_tool.py", "CLAUDE.md", f"{A}/CLAUDE.md", f"{A}/taxonomy/taxonomy.yaml",
    f"{A}/evals/reports/baseline.json", "shared/evals/targets.toml", ".github/workflows/ci.yml",
    "Makefile", "random_root_file.py",
])
def test_write_protected_without_override(repo, path):
    assert pre(repo, "Write", file_path=str(repo / path), content="x").returncode == 2


@pytest.mark.parametrize("path", [
    f"{A}/src/spend_classification/ingest/load.py", f"{A}/STATUS.md", "shared/audit/x.py",
    "tests/test_x.py", "README.md",
])
def test_write_allowed(repo, path):
    assert pre(repo, "Edit", file_path=str(repo / path)).returncode == 0


def test_write_outside_repo_blocked(repo, tmp_path_factory):
    other = tmp_path_factory.mktemp("elsewhere") / "x.py"
    assert pre(repo, "Write", file_path=str(other)).returncode == 2


def test_override_allows_only_matching_prefix(repo):
    (repo / ".claude" / "OVERRIDE").write_text("governance/RISK_REGISTER.md | add R8\n")
    assert pre(repo, "Edit", file_path=str(repo / "governance/RISK_REGISTER.md")).returncode == 0
    assert pre(repo, "Edit", file_path=str(repo / "governance/DATA_POLICY.md")).returncode == 2
    log = (repo / "logs" / "dev-audit.jsonl").read_text()
    assert "allow_override" in log


def test_override_needs_reason_and_cannot_unlock_real_data(repo):
    (repo / ".claude" / "OVERRIDE").write_text("governance/ |\nagents/ | sure\n")
    assert pre(repo, "Edit", file_path=str(repo / "governance/X.md")).returncode == 2
    assert pre(repo, "Write", file_path=str(repo / A / "data/real/x.csv")).returncode == 2
    assert pre(repo, "Write", file_path=str(repo / ".claude/OVERRIDE")).returncode == 2


def test_every_call_is_audited(repo):
    pre(repo, "Bash", command="ls")
    pre(repo, "Bash", command="rm -rf x")
    rows = [json.loads(x) for x in (repo / "logs" / "dev-audit.jsonl").read_text().splitlines()]
    assert [r["decision"] for r in rows] == ["allow", "block"]


def test_stop_gate_respects_stop_hook_active(repo):
    # No uv on the restricted PATH: the gate must not block, and must not loop.
    r = run_hook(repo, "stop_gate.py", {"stop_hook_active": True})
    assert r.returncode == 0


def test_session_start_warns_about_override(repo):
    (repo / ".claude" / "OVERRIDE").write_text("governance/ | review\n")
    r = run_hook(repo, "session_start.py", {})
    assert r.returncode == 0 and "OVERRIDE is present" in r.stdout


def test_secret_scanner_patterns():
    import importlib.util
    spec = importlib.util.spec_from_file_location("scan_secrets", SCAN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    key = "sk-ant-" + "a1" * 15
    assert any(n == "anthropic_key" for _, n in mod.scan_text(f"KEY={key}"))
    # built at runtime so the repo-wide scan stays clean
    card, ssn = "4111 1111 " + "1111 1111", "123-45-" + "6789"
    assert any(n == "payment_card" for _, n in mod.scan_text(f"card {card}"))
    assert any(n == "us_ssn" for _, n in mod.scan_text(f"ssn {ssn}"))
    assert mod.scan_text("invoice 2026-11-08 total 1234.56 PO-778812") == []
    assert mod.scan_text(f"KEY={key}  # scan-ok") == []
