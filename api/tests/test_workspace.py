from pathlib import Path

from app.services.workspace import Workspace


def test_discard_removes_staged_writes(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    workspace.start_branch("task/TASK-001")
    workspace.apply([("server/app.py", "print('hi')\n")])
    assert (tmp_path / "server" / "app.py").read_text() == "print('hi')\n"
    workspace.discard()
    assert not (tmp_path / "server" / "app.py").exists()


def test_commit_happens_only_after_staging(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    workspace.start_branch("task/TASK-001")
    workspace.apply([("server/app.py", "print('hi')\n")])
    workspace.commit_staged("TASK-001", "add the app")
    log = workspace._git("log", "--oneline", "task/TASK-001")
    assert "TASK-001: add the app" in log
