import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.gateway.base import LlmResult
from app.gateway.fake import FakeLlm
from app.main import create_app


def client_for(tmp_path: Path, llm=None, **overrides) -> TestClient:
    settings = Settings(
        database_url="sqlite:///:memory:",
        llm_provider="fake",
        workspaces_dir=str(tmp_path),
        **overrides,
    )
    return TestClient(create_app(settings=settings, llm=llm or FakeLlm()))


def _prepare(client: TestClient) -> str:
    created = client.post(
        "/api/projects",
        json={"name": "Tasks", "description": "A task manager with projects and due dates."},
    )
    project_id = created.json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/interpret")
    snapshot = client.get(f"/api/projects/{project_id}").json()
    client.post(
        f"/api/projects/{project_id}/clarifications",
        json={
            "proceed": False,
            "answers": [
                {"id": item["id"], "answer": "Signed-in members."}
                for item in snapshot["clarifications"]
                if item["status"] == "open"
            ],
        },
    )
    client.post(f"/api/projects/{project_id}/requirements")
    client.post(
        f"/api/projects/{project_id}/gates",
        json={"gate": "requirements", "decision": "approved"},
    )
    client.post(f"/api/projects/{project_id}/architecture")
    client.post(
        f"/api/projects/{project_id}/gates",
        json={"gate": "architecture", "decision": "approved"},
    )
    tasks = client.post(f"/api/projects/{project_id}/tasks")
    assert tasks.status_code == 200, tasks.text
    return project_id


def _by_key(body: dict, key: str) -> dict:
    return next(item for item in body["tasks"] if item["key"] == key)


def _failure(body: dict) -> str:
    event = next(item for item in body["events"] if item["type"] == "task.failed")
    return event["payload"]["cause"]


def test_accepting_a_run_merges_it_and_unblocks_the_next_task(tmp_path: Path):
    client = client_for(tmp_path)
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    assert ran.status_code == 200, ran.text
    body = ran.json()
    first = _by_key(body, "TASK-001")
    assert first["state"] == "in_review"
    assert first["branch_name"] == "task/TASK-001"
    assert _by_key(body, "TASK-002")["state"] == "blocked"
    written = tmp_path / project_id / "server" / "app.py"
    assert "create_record" in written.read_text()

    accepted = client.post(f"/api/projects/{project_id}/tasks/{first['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert _by_key(body, "TASK-001")["state"] == "done"
    assert _by_key(body, "TASK-002")["state"] == "ready"
    assert "run_ready" in body["project"]["next_actions"]
    assert "create_record" in (tmp_path / project_id / "server" / "app.py").read_text()


def test_a_task_in_review_is_not_claimed_again(tmp_path: Path):
    client = client_for(tmp_path)
    project_id = _prepare(client)
    first = client.post(f"/api/projects/{project_id}/tasks/run")
    assert first.status_code == 200, first.text
    second = client.post(f"/api/projects/{project_id}/tasks/run")
    assert second.status_code == 409
    body = client.get(f"/api/projects/{project_id}").json()
    assert _by_key(body, "TASK-001")["state"] == "in_review"
    assert _by_key(body, "TASK-001")["retry_count"] == 0


def test_a_write_outside_the_zone_is_not_saved(tmp_path: Path):
    client = client_for(tmp_path, _OutsideZone())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    assert ran.status_code == 200, ran.text
    body = ran.json()
    assert _by_key(body, "TASK-001")["state"] == "ready"
    assert _by_key(body, "TASK-001")["retry_count"] == 1
    assert "outside" in _failure(body)
    assert not (tmp_path / project_id / "web" / "nope.tsx").exists()


def test_a_run_that_never_finishes_is_stopped_by_the_iteration_budget(tmp_path: Path):
    client = client_for(tmp_path, _NeverDone(), run_max_iterations=2)
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    body = ran.json()
    assert ran.status_code == 200, ran.text
    assert _by_key(body, "TASK-001")["state"] == "ready"
    assert "iteration budget" in _failure(body)
    assert not (tmp_path / project_id / "server" / "app.py").exists()


def test_repeating_the_same_change_stops_the_run(tmp_path: Path):
    client = client_for(tmp_path, _SameChange())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    body = ran.json()
    assert "repeated" in _failure(body)
    assert not (tmp_path / project_id / "server" / "app.py").exists()


def test_a_retry_reuses_the_same_branch(tmp_path: Path):
    client = client_for(tmp_path, _FailOnce())
    project_id = _prepare(client)
    client.post(f"/api/projects/{project_id}/tasks/run")
    second = client.post(f"/api/projects/{project_id}/tasks/run")
    assert second.status_code == 200, second.text
    assert _by_key(second.json(), "TASK-001")["state"] == "in_review"
    listed = subprocess.run(
        ["git", "branch", "--list", "task/TASK-001"],
        cwd=tmp_path / project_id,
        check=True,
        capture_output=True,
        text=True,
    )
    assert listed.stdout.count("task/TASK-001") == 1


class _OutsideZone(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "implement":
            return LlmResult(
                data={
                    "summary": "Wrong tree.",
                    "done": True,
                    "writes": [{"path": "web/nope.tsx", "content": "nope\n"}],
                },
                input_tokens=1,
                output_tokens=1,
                provider=self.provider,
                model=self.model,
            )
        return super().complete_json(purpose=purpose, system=system, user=user)


class _NeverDone(FakeLlm):
    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "implement":
            self.calls += 1
            return LlmResult(
                data={
                    "summary": "Still working.",
                    "done": False,
                    "writes": [{"path": "server/app.py", "content": f"step {self.calls}\n"}],
                },
                input_tokens=1,
                output_tokens=1,
                provider=self.provider,
                model=self.model,
            )
        return super().complete_json(purpose=purpose, system=system, user=user)


class _SameChange(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "implement":
            return LlmResult(
                data={
                    "summary": "Again.",
                    "done": False,
                    "writes": [{"path": "server/app.py", "content": "same\n"}],
                },
                input_tokens=1,
                output_tokens=1,
                provider=self.provider,
                model=self.model,
            )
        return super().complete_json(purpose=purpose, system=system, user=user)


class _FailOnce(FakeLlm):
    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "implement":
            self.calls += 1
            if self.calls == 1:
                return LlmResult(
                    data={
                        "summary": "Wrong tree.",
                        "done": True,
                        "writes": [{"path": "web/nope.tsx", "content": "nope\n"}],
                    },
                    input_tokens=1,
                    output_tokens=1,
                    provider=self.provider,
                    model=self.model,
                )
        return super().complete_json(purpose=purpose, system=system, user=user)
