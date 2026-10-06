from fastapi.testclient import TestClient

from app.gateway.base import LlmResult
from app.gateway.fake import FakeLlm
from app.main import create_app


def client_for(llm=None) -> TestClient:
    app = create_app(database_url="sqlite:///:memory:", llm=llm or FakeLlm())
    return TestClient(app)


def _create(client: TestClient) -> str:
    response = client.post(
        "/api/projects",
        json={
            "name": "Tasks",
            "description": "A task manager with projects, assignment, and due dates.",
            "tech_preferences": "TypeScript and Python",
        },
    )
    assert response.status_code == 200
    return response.json()["project"]["id"]


def _answer_open(client: TestClient, project_id: str, text: str = "Signed-in team members.") -> dict:
    snapshot = client.get(f"/api/projects/{project_id}").json()
    answers = [
        {"id": item["id"], "answer": text}
        for item in snapshot["clarifications"]
        if item["status"] == "open"
    ]
    response = client.post(
        f"/api/projects/{project_id}/clarifications",
        json={"answers": answers, "proceed": False},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_a_paused_project_blocks_planning_steps():
    client = client_for()
    project_id = _create(client)
    paused = client.post(f"/api/projects/{project_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["project"]["paused"] is True
    assert paused.json()["project"]["next_actions"] == ["unpause"]
    refused = client.post(f"/api/projects/{project_id}/interpret")
    assert refused.status_code == 409
    assert "paused" in refused.json()["detail"]
    client.post(f"/api/projects/{project_id}/unpause")
    interpreted = client.post(f"/api/projects/{project_id}/interpret")
    assert interpreted.status_code == 200


def test_revoking_agents_blocks_planning_but_allows_restore():
    client = client_for()
    project_id = _create(client)
    revoked = client.post(f"/api/projects/{project_id}/revoke-agents")
    assert revoked.status_code == 200
    assert revoked.json()["project"]["agents_revoked"] is True
    assert "interpret" not in revoked.json()["project"]["next_actions"]
    assert "restore_agents" in revoked.json()["project"]["next_actions"]
    refused = client.post(f"/api/projects/{project_id}/interpret")
    assert refused.status_code == 409
    assert "revoked" in refused.json()["detail"]
    restored = client.post(f"/api/projects/{project_id}/restore-agents")
    assert restored.json()["project"]["agents_revoked"] is False
    assert "interpret" in restored.json()["project"]["next_actions"]
    again = client.post(f"/api/projects/{project_id}/interpret")
    assert again.status_code == 200, again.text


def test_planning_spend_is_broken_down_by_role():
    client = client_for()
    project_id = _create(client)
    interpreted = client.post(f"/api/projects/{project_id}/interpret")
    assert interpreted.status_code == 200, interpreted.text
    body = interpreted.json()
    assert body["project"]["spend_by_role"] == [{"role": "pm", "tokens": 50}]
    assert body["project"]["spend_by_task"] == []
    assert body["runs"][0]["task_id"] is None


def test_hitting_the_spend_ceiling_pauses_the_project():
    client = client_for()
    created = client.post(
        "/api/projects",
        json={
            "name": "Budget",
            "description": "A tiny app so spend can be measured.",
            "spend_ceiling_tokens": 40,
        },
    )
    project_id = created.json()["project"]["id"]
    assert created.json()["project"]["spend_ceiling_tokens"] == 40
    first = client.post(f"/api/projects/{project_id}/interpret")
    assert first.status_code == 200, first.text
    assert first.json()["project"]["spend_tokens"] == 50
    snapshot = client.get(f"/api/projects/{project_id}").json()
    answers = [
        {"id": item["id"], "answer": "Signed-in team members."}
        for item in snapshot["clarifications"]
        if item["status"] == "open"
    ]
    refused = client.post(
        f"/api/projects/{project_id}/clarifications",
        json={"answers": answers, "proceed": False},
    )
    assert refused.status_code == 409
    assert "ceiling" in refused.json()["detail"].lower()
    snapshot = client.get(f"/api/projects/{project_id}").json()
    assert snapshot["project"]["paused"] is True
    assert any(event["type"] == "project.spend_ceiling" for event in snapshot["events"])
    raised = client.post(
        f"/api/projects/{project_id}/spend-ceiling",
        json={"spend_ceiling_tokens": 500},
    )
    assert raised.status_code == 200, raised.text
    client.post(f"/api/projects/{project_id}/unpause")
    snapshot = client.get(f"/api/projects/{project_id}").json()
    answers = [
        {"id": item["id"], "answer": "Signed-in team members."}
        for item in snapshot["clarifications"]
        if item["status"] == "open"
    ]
    again = client.post(
        f"/api/projects/{project_id}/clarifications",
        json={"answers": answers, "proceed": False},
    )
    assert again.status_code == 200, again.text


def test_crossing_spend_thresholds_alerts_once_per_level():
    client = client_for()
    created = client.post(
        "/api/projects",
        json={
            "name": "Alerts",
            "description": "Watch spend thresholds fire as planning runs.",
            "spend_ceiling_tokens": 100,
        },
    )
    project_id = created.json()["project"]["id"]
    first = client.post(f"/api/projects/{project_id}/interpret")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["project"]["spend_tokens"] == 50
    assert body["project"]["spend_alerts"] == [50]
    threshold_events = [event for event in body["events"] if event["type"] == "project.spend_threshold"]
    assert len(threshold_events) == 1
    assert threshold_events[0]["payload"]["percent"] == 50
    snapshot = client.get(f"/api/projects/{project_id}").json()
    answers = [
        {"id": item["id"], "answer": "Signed-in team members."}
        for item in snapshot["clarifications"]
        if item["status"] == "open"
    ]
    second = client.post(
        f"/api/projects/{project_id}/clarifications",
        json={"answers": answers, "proceed": False},
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["project"]["spend_tokens"] == 100
    assert body["project"]["spend_alerts"] == [50, 80, 95]
    percents = sorted(
        event["payload"]["percent"]
        for event in body["events"]
        if event["type"] == "project.spend_threshold"
    )
    assert percents == [50, 80, 95]


def test_projects_start_with_human_gate_policy():
    client = client_for()
    project_id = _create(client)
    body = client.get(f"/api/projects/{project_id}").json()
    assert body["project"]["gate_policy"]["requirements"] == "human"
    assert body["project"]["gate_policy"]["merge"] == "human"
    assert body["project"]["gate_policy"]["deployment"] == "human"


def test_project_status_summarises_tasks_and_open_gates():
    client = client_for()
    project_id = _create(client)
    client.post(f"/api/projects/{project_id}/interpret")
    _answer_open(client, project_id)
    client.post(f"/api/projects/{project_id}/requirements")
    draft = client.get(f"/api/projects/{project_id}").json()
    assert "requirements" in draft["project"]["status"]["open_gates"]
    assert "Requirements approval pending" in draft["project"]["status"]["needs_you"]
    assert draft["project"]["status"]["agents"][0] == {"role": "pm", "state": "working"}
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
    body = tasks.json()
    status = body["project"]["status"]
    assert status["task_counts"]
    assert sum(status["task_counts"].values()) == len(body["tasks"])
    blocked = status["blocked"]
    assert all("task_key" in item and "blocked_by" in item for item in blocked)
    assert {"role", "state"} <= set(status["agents"][0])


def test_automatic_merge_needs_an_acknowledgement():
    client = client_for()
    project_id = _create(client)
    refused = client.post(
        f"/api/projects/{project_id}/gate-policy",
        json={"gate_policy": {"merge": "automatic"}},
    )
    assert refused.status_code == 422
    assert "acknowledgement" in refused.json()["detail"].lower()
    accepted = client.post(
        f"/api/projects/{project_id}/gate-policy",
        json={
            "gate_policy": {"merge": "automatic"},
            "acknowledgement": "I accept unattended merges.",
        },
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["project"]["gate_policy"]["merge"] == "automatic"
    event = next(item for item in body["events"] if item["type"] == "project.gate_policy")
    assert event["payload"]["acknowledgement"] == "I accept unattended merges."


def test_automatic_requirements_gate_approves_without_a_person():
    client = client_for()
    project_id = _create(client)
    policy = client.post(
        f"/api/projects/{project_id}/gate-policy",
        json={"gate_policy": {"requirements": "automatic"}},
    )
    assert policy.status_code == 200, policy.text
    assert policy.json()["project"]["gate_policy"]["requirements"] == "automatic"
    client.post(f"/api/projects/{project_id}/interpret")
    _answer_open(client, project_id)
    drafted = client.post(f"/api/projects/{project_id}/requirements")
    assert drafted.status_code == 200, drafted.text
    body = drafted.json()
    assert body["project"]["stage"] == "requirements_approved"
    assert "approve_requirements" not in body["project"]["next_actions"]
    gate = next(item for item in body["gates"] if item["gate"] == "requirements")
    assert gate["decision"] == "approved"
    assert gate["note"] == "Approved by automatic policy."
    assert any(
        event["type"] == "gate.decided" and event["actor_kind"] == "system"
        for event in body["events"]
    )


def test_happy_path_stops_at_a_task_graph():
    client = client_for()
    project_id = _create(client)

    interpreted = client.post(f"/api/projects/{project_id}/interpret")
    assert interpreted.status_code == 200
    body = interpreted.json()
    assert body["project"]["stage"] == "clarifying"
    assert len(body["clarifications"]) == 3
    assert "interpret" not in body["project"]["next_actions"]
    assert "pause" in body["project"]["next_actions"]

    closed = _answer_open(client, project_id)
    assert closed["project"]["stage"] == "interpreted"

    drafted = client.post(f"/api/projects/{project_id}/requirements")
    assert drafted.status_code == 200
    requirements = drafted.json()["requirements"]
    assert all(item["criteria"] for item in requirements if item["kind"] == "functional")

    approved = client.post(
        f"/api/projects/{project_id}/gates",
        json={"gate": "requirements", "decision": "approved"},
    )
    assert approved.json()["project"]["stage"] == "requirements_approved"

    # Tasks are refused until the architecture gate is passed.
    skipped = client.post(f"/api/projects/{project_id}/tasks")
    assert skipped.status_code == 409

    architecture = client.post(f"/api/projects/{project_id}/architecture")
    assert architecture.status_code == 200
    assert architecture.json()["ownership"]

    client.post(
        f"/api/projects/{project_id}/gates",
        json={"gate": "architecture", "decision": "approved"},
    )
    tasks = client.post(f"/api/projects/{project_id}/tasks")
    assert tasks.status_code == 200, tasks.text
    body = tasks.json()
    assert body["project"]["stage"] == "tasks_ready"
    states = {item["key"]: item["state"] for item in body["tasks"]}
    assert states["TASK-001"] == "ready"
    assert states["TASK-002"] == "blocked"
    assert states["TASK-003"] == "blocked"
    assert body["project"]["uncovered_requirement_keys"] == []
    assert any(event["type"] == "plan.stage_changed" for event in body["events"])
    assert body["runs"][0]["role"] == "pm"


def test_a_functional_requirement_without_a_criterion_cannot_be_approved():
    client = client_for()
    project_id = _create(client)
    client.post(f"/api/projects/{project_id}/interpret")
    _answer_open(client, project_id)
    drafted = client.post(f"/api/projects/{project_id}/requirements").json()
    first = next(item for item in drafted["requirements"] if item["kind"] == "functional")
    edited = client.patch(
        f"/api/projects/{project_id}/requirements/{first['id']}",
        json={
            "kind": "functional",
            "title": first["title"],
            "statement": first["statement"],
            "criteria": [],
        },
    )
    assert edited.status_code == 422
    approved = client.post(
        f"/api/projects/{project_id}/gates",
        json={"gate": "requirements", "decision": "approved"},
    )
    assert approved.status_code == 200


def test_proceeding_records_an_assumption_and_stops_asking():
    client = client_for(_AlwaysAsk())
    project_id = _create(client)
    client.post(f"/api/projects/{project_id}/interpret")
    response = client.post(
        f"/api/projects/{project_id}/clarifications",
        json={"answers": [], "proceed": True},
    )
    body = response.json()
    assert body["project"]["stage"] == "interpreted"
    assert body["assumptions"]
    assert body["project"]["clarification_round"] == 1


def test_clarification_stops_after_three_rounds():
    client = client_for(_AlwaysAsk())
    project_id = _create(client)
    client.post(f"/api/projects/{project_id}/interpret")
    for _ in range(3):
        body = _answer_open(client, project_id, text="Still the same user.")
    assert body["project"]["stage"] == "interpreted"
    assert any("budget" in item["statement"].lower() for item in body["assumptions"])


def test_a_cyclic_task_graph_is_rejected():
    client = client_for(_CyclicTasks())
    project_id = _create(client)
    client.post(f"/api/projects/{project_id}/interpret")
    _answer_open(client, project_id)
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
    response = client.post(f"/api/projects/{project_id}/tasks")
    assert response.status_code == 409
    assert "cycle" in response.json()["detail"].lower()
    snapshot = client.get(f"/api/projects/{project_id}").json()
    assert snapshot["project"]["stage"] == "architecture_approved"
    assert snapshot["tasks"] == []


class _AlwaysAsk(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "followup":
            return LlmResult(
                data={"more": True, "clarifications": [{"question": "Who else uses this?", "resolves": "audience"}]},
                input_tokens=1,
                output_tokens=1,
                provider=self.provider,
                model=self.model,
            )
        return super().complete_json(purpose=purpose, system=system, user=user)


class _CyclicTasks(FakeLlm):
    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if purpose == "tasks":
            return LlmResult(
                data={
                    "tasks": [
                        {
                            "title": "API",
                            "description": "Build the API.",
                            "zone": "backend",
                            "size": "S",
                            "depends_on": [1],
                            "requirement_indexes": [0],
                        },
                        {
                            "title": "Schema",
                            "description": "Build the schema.",
                            "zone": "backend",
                            "size": "S",
                            "depends_on": [0],
                            "requirement_indexes": [1],
                        },
                    ]
                },
                input_tokens=1,
                output_tokens=1,
                provider=self.provider,
                model=self.model,
            )
        return super().complete_json(purpose=purpose, system=system, user=user)
