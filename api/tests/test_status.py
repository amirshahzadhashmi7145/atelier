from app.domain.status import (
    agent_states,
    blocked_with_blockers,
    needs_you,
    open_gates,
    task_counts,
)


class _Dep:
    def __init__(self, depends_on_id: str) -> None:
        self.depends_on_id = depends_on_id


class _Task:
    def __init__(self, key: str, state: str, zone: str = "backend", deps: list[str] | None = None) -> None:
        self.id = f"id-{key}"
        self.key = key
        self.state = state
        self.zone = zone
        self.dependencies = [_Dep(f"id-{item}") for item in (deps or [])]


class _Finding:
    def __init__(self, task_id: str, result: str) -> None:
        self.task_id = task_id
        self.result = result


def test_task_counts_group_by_state():
    assert task_counts([_Task("A", "ready"), _Task("B", "blocked"), _Task("C", "ready")]) == {
        "blocked": 1,
        "ready": 2,
    }


def test_blocked_lists_unfinished_dependencies():
    tasks = [
        _Task("TASK-001", "done"),
        _Task("TASK-002", "blocked", deps=["TASK-001", "TASK-003"]),
        _Task("TASK-003", "ready"),
    ]
    # ids are id-TASK-00x; deps reference those
    assert blocked_with_blockers(tasks) == [("TASK-002", ["TASK-003"])]


def test_open_gates_include_approvals_and_merge():
    gates = open_gates(
        next_actions=["approve_requirements", "pause"],
        tasks=[_Task("TASK-001", "gated"), _Task("TASK-002", "escalated")],
    )
    assert gates == ["requirements", "merge:TASK-001", "resume:TASK-002"]


def test_agent_states_reflect_active_zones():
    assert agent_states(
        stage="tasks_ready",
        tasks=[
            _Task("TASK-001", "in_progress", zone="backend"),
            _Task("TASK-002", "ready", zone="frontend"),
        ],
    ) == [
        ("pm", "idle"),
        ("backend", "working"),
        ("frontend", "waiting"),
        ("ai_engineer", "idle"),
        ("fullstack", "idle"),
        ("qa", "idle"),
    ]

    assert agent_states(
        stage="tasks_ready",
        tasks=[_Task("TASK-001", "in_review", zone="backend")],
    ) == [
        ("pm", "idle"),
        ("backend", "waiting"),
        ("frontend", "idle"),
        ("ai_engineer", "idle"),
        ("fullstack", "working"),
        ("qa", "waiting"),
    ]


def test_needs_you_surfaces_approvals_and_escalations():
    lines = needs_you(
        open_gate_list=["architecture", "resume:TASK-001", "review:TASK-002"],
        tasks=[_Task("TASK-002", "in_review")],
        findings=[_Finding("id-TASK-002", "untestable")],
    )
    assert lines == [
        "Architecture approval pending",
        "TASK-001 escalated",
        "TASK-002 untestable",
    ]
