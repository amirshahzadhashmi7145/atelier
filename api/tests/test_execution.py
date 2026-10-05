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
        check_sandbox=False,
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

    too_soon = client.post(f"/api/projects/{project_id}/tasks/{first['id']}/accept")
    assert too_soon.status_code == 409

    reviewed = client.post(f"/api/projects/{project_id}/tasks/{first['id']}/review")
    assert reviewed.status_code == 200, reviewed.text
    assert _by_key(reviewed.json(), "TASK-001")["state"] == "gated"
    assert reviewed.json()["findings"]
    assert {item["tier"] for item in reviewed.json()["checks"]} == {"unit", "integration", "ui"}
    assert all(item["exit_code"] == 0 for item in reviewed.json()["checks"])

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


def test_a_failed_review_sends_the_task_back_with_a_defect(tmp_path: Path):
    client = client_for(tmp_path, _FailFirstCriterion())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert _by_key(body, "TASK-001")["state"] == "ready"
    assert body["defects"][0]["expected"] == "401"
    assert body["defects"][0]["observed"] == "201"
    log = subprocess.run(
        ["git", "log", "main", "--oneline"],
        cwd=tmp_path / project_id,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "TASK-001" not in log.stdout

    again = client.post(f"/api/projects/{project_id}/tasks/run")
    assert again.status_code == 200, again.text
    assert _by_key(again.json(), "TASK-001")["state"] == "in_review"
    assert "revised after review" in (tmp_path / project_id / "server" / "app.py").read_text()
    passed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert _by_key(passed.json(), "TASK-001")["state"] == "gated"


def test_an_untestable_criterion_stays_in_review(tmp_path: Path):
    client = client_for(tmp_path, _Untestable())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert reviewed.status_code == 200, reviewed.text
    assert _by_key(reviewed.json(), "TASK-001")["state"] == "in_review"
    assert reviewed.json()["findings"][0]["result"] == "untestable"
    accepted = client.post(f"/api/projects/{project_id}/tasks/{task_id}/accept")
    assert accepted.status_code == 409


def test_a_person_can_waive_untestable_criteria(tmp_path: Path):
    client = client_for(tmp_path, _Untestable())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    waived = client.post(
        f"/api/projects/{project_id}/tasks/{task_id}/untestable",
        json={"decision": "waive"},
    )
    assert waived.status_code == 200, waived.text
    body = waived.json()
    assert _by_key(body, "TASK-001")["state"] == "gated"
    task_findings = [item for item in body["findings"] if item["task_id"] == task_id]
    assert any(item["result"] == "waived" for item in task_findings)
    assert all(item["result"] in {"waived", "pass"} for item in task_findings)
    assert any(event["type"] == "qa.waived" for event in body["events"])


def test_a_person_can_reject_untestable_criteria(tmp_path: Path):
    client = client_for(tmp_path, _Untestable())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    rejected = client.post(
        f"/api/projects/{project_id}/tasks/{task_id}/untestable",
        json={"decision": "reject"},
    )
    assert rejected.status_code == 200, rejected.text
    body = rejected.json()
    assert _by_key(body, "TASK-001")["state"] == "ready"
    assert any(defect["task_id"] == task_id for defect in body["defects"])
    assert any(event["type"] == "qa.rejected_untestable" for event in body["events"])


def test_waive_is_refused_when_review_passed(tmp_path: Path):
    client = client_for(tmp_path)
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert _by_key(reviewed.json(), "TASK-001")["state"] == "gated"
    refused = client.post(
        f"/api/projects/{project_id}/tasks/{task_id}/untestable",
        json={"decision": "waive"},
    )
    assert refused.status_code == 409


def test_a_review_that_skips_a_criterion_records_nothing(tmp_path: Path):
    client = client_for(tmp_path, _DropsACriterion())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert reviewed.status_code == 502
    body = client.get(f"/api/projects/{project_id}").json()
    assert _by_key(body, "TASK-001")["state"] == "in_review"
    assert body["findings"] == []


def test_qa_cannot_change_the_branch(tmp_path: Path):
    client = client_for(tmp_path, _QaTriesToWrite())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    before = (tmp_path / project_id / "server" / "app.py").read_text()
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert reviewed.status_code == 200, reviewed.text
    assert (tmp_path / project_id / "server" / "app.py").read_text() == before


def test_a_failing_test_command_blocks_a_pass(tmp_path: Path):
    llm = _BrokenUnitTests()
    client = client_for(tmp_path, llm)
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert _by_key(body, "TASK-001")["state"] == "ready"
    assert llm.qa_calls == 0
    unit = next(item for item in body["checks"] if item["tier"] == "unit")
    assert unit["exit_code"] == 2
    defect = next(item for item in body["defects"] if item["criterion_key"] == "tests/unit")
    assert defect["reproduction"].startswith("python3")
    assert "The command exits 0." == defect["expected"]
    log = subprocess.run(
        ["git", "log", "main", "--oneline"],
        cwd=tmp_path / project_id,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "TASK-001" not in log.stdout


def test_a_chained_test_command_does_not_run(tmp_path: Path):
    client = client_for(tmp_path, _ChainedTest())
    project_id = _prepare(client)
    ran = client.post(f"/api/projects/{project_id}/tasks/run")
    task_id = _by_key(ran.json(), "TASK-001")["id"]
    reviewed = client.post(f"/api/projects/{project_id}/tasks/{task_id}/review")
    assert reviewed.status_code == 422
    body = client.get(f"/api/projects/{project_id}").json()
    assert _by_key(body, "TASK-001")["state"] == "in_review"
    assert body["checks"] == []
    assert not (tmp_path / project_id / "chained.txt").exists()


def test_the_review_prompt_states_criteria_before_the_diff():
    from app.agents.qa import review_prompt

    _system, user = review_prompt(
        task_key="TASK-001",
        title="Persist",
        criteria=[("FR-001/AC-1", "A missing session returns 401.")],
        checks="- unit: python3 -c \"print('unit ok')\" exited 0",
        diff="diff --git a/server/app.py",
    )
    assert user.index("Criteria:") < user.index("Test results:") < user.index("Diff:")


class _BrokenUnitTests(FakeLlm):
    def __init__(self) -> None:
        self.qa_calls = 0

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "qa":
            self.qa_calls += 1
        result = super().complete_json(purpose=purpose, system=system, user=user)
        if purpose == "architecture":
            result.data["test_strategy"]["unit"] = 'python3 -c "import sys; sys.exit(2)"'
        return result


class _ChainedTest(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        result = super().complete_json(purpose=purpose, system=system, user=user)
        if purpose == "architecture":
            result.data["test_strategy"]["unit"] = "python3 -c \"print('ok')\" && touch chained.txt"
        return result


class _FailFirstCriterion(FakeLlm):
    def __init__(self) -> None:
        self.reviews = 0

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "qa":
            self.reviews += 1
            result = super().complete_json(purpose=purpose, system=system, user=user)
            if self.reviews == 1:
                result.data["findings"][0]["result"] = "fail"
                result.data["findings"][0]["reproduction"] = "POST /records with no session"
                result.data["findings"][0]["observed"] = "201"
                result.data["findings"][0]["expected"] = "401"
            return result
        return super().complete_json(purpose=purpose, system=system, user=user)


class _Untestable(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "qa":
            result = super().complete_json(purpose=purpose, system=system, user=user)
            result.data["findings"][0]["result"] = "untestable"
            result.data["findings"][0]["note"] = "No clock is available in this run."
            return result
        return super().complete_json(purpose=purpose, system=system, user=user)


class _DropsACriterion(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "qa":
            result = super().complete_json(purpose=purpose, system=system, user=user)
            result.data["findings"] = result.data["findings"][:1]
            return result
        return super().complete_json(purpose=purpose, system=system, user=user)


class _QaTriesToWrite(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "qa":
            result = super().complete_json(purpose=purpose, system=system, user=user)
            result.data["writes"] = [{"path": "server/app.py", "content": "hacked\n"}]
            return result
        return super().complete_json(purpose=purpose, system=system, user=user)


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
