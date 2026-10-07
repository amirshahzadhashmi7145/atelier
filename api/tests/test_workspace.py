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


def test_agent_commits_carry_role_and_run_trailers(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    workspace.start_branch("task/TASK-001")
    workspace.commit(
        "TASK-001",
        "add the app",
        [("server/app.py", "print('hi')\n")],
        role="backend",
        run_id="run_abc123",
    )
    body = workspace._git("log", "-1", "--format=%B", "task/TASK-001")
    assert "TASK-001: add the app" in body
    assert "Atelier-Agent: backend" in body
    assert "Atelier-Run: run_abc123" in body


def test_empty_task_branch_resets_onto_new_main(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    workspace.start_branch("task/TASK-001")
    workspace._git("checkout", "main")
    workspace.commit("ARCH", "seed", [("package.json", '{"name":"demo"}\n')])
    workspace.start_branch("task/TASK-001")
    assert (tmp_path / "package.json").is_file()
    assert workspace._git("rev-parse", "task/TASK-001") == workspace._git("rev-parse", "main")


def test_rebase_onto_main_replays_the_branch(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    workspace.start_branch("task/TASK-001")
    workspace.commit("TASK-001", "add the app", [("server/app.py", "print('branch')\n")])
    workspace._git("checkout", "main")
    workspace.commit("MAIN", "docs", [("server/readme.txt", "ok\n")])
    workspace.rebase_onto_main("task/TASK-001")
    assert (tmp_path / "server" / "app.py").read_text() == "print('branch')\n"
    assert (tmp_path / "server" / "readme.txt").read_text() == "ok\n"


def test_a_conflicted_rebase_is_aborted(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    workspace.start_branch("task/TASK-001")
    workspace.commit("TASK-001", "branch edit", [("server/app.py", "print('branch')\n")])
    workspace._git("checkout", "main")
    workspace.commit("MAIN", "main edit", [("server/app.py", "print('main')\n")])
    try:
        workspace.rebase_onto_main("task/TASK-001")
    except RuntimeError as exc:
        assert "conflict" in str(exc).lower() or "Could not apply" in str(exc) or str(exc)
    else:
        raise AssertionError("expected a conflict")
    status = workspace._git("status")
    assert "rebase in progress" not in status.lower()
    assert (tmp_path / "server" / "app.py").read_text() == "print('branch')\n"
