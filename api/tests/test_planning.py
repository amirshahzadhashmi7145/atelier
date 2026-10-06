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
