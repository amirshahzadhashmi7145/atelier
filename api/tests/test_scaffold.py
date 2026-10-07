from pathlib import Path

from app.services.scaffold import apply_scaffold, ensure_test_ownership, scaffold_writes
from app.services.workspace import Workspace


def test_scaffold_writes_zone_dirs_and_harnesses():
    ownership = [("backend/**", "backend"), ("frontend/**", "frontend")]
    strategy = {
        "unit": "python3 -m pytest tests/unit",
        "integration": "python3 -m pytest tests/integration",
        "ui": "npm test -- --watchAll=false",
    }
    paths = {relative for relative, _content in scaffold_writes(ownership, strategy)}
    assert "backend/.gitkeep" in paths
    assert "frontend/.gitkeep" in paths
    assert "requirements.txt" in paths
    assert "package.json" in paths
    assert "tests/unit/test_harness.py" in paths
    assert "tests/integration/test_harness.py" in paths
    assert "scripts/verify_ui.js" in paths


def test_ensure_test_ownership_adds_harness_globs():
    ownership = [("backend/**", "backend"), ("frontend/**", "frontend")]
    strategy = {
        "unit": "python3 -m pytest tests/unit",
        "integration": "python3 -m pytest tests/integration",
        "ui": "npm test",
    }
    expanded = ensure_test_ownership(ownership, strategy)
    globs = {pattern for pattern, _zone in expanded}
    assert "tests/**" in globs
    assert "requirements.txt" in globs
    assert "package.json" in globs


def test_apply_scaffold_commits_on_main(tmp_path: Path):
    workspace = Workspace(tmp_path)
    written = apply_scaffold(
        workspace,
        [("backend/**", "backend"), ("frontend/**", "frontend")],
        {
            "unit": "python3 -m pytest tests/unit",
            "integration": "python3 -m pytest tests/integration",
            "ui": "npm test -- --watchAll=false",
        },
    )
    assert "package.json" in written
    assert (tmp_path / "package.json").is_file()
    assert (tmp_path / "requirements.txt").is_file()
    assert (tmp_path / "backend" / ".gitkeep").is_file()
    log = workspace._git("log", "--oneline", "main")
    assert "Seed zone layout" in log
    # Second apply is a no-op.
    assert apply_scaffold(
        workspace,
        [("backend/**", "backend"), ("frontend/**", "frontend")],
        {
            "unit": "python3 -m pytest tests/unit",
            "integration": "python3 -m pytest tests/integration",
            "ui": "npm test -- --watchAll=false",
        },
    ) == []
