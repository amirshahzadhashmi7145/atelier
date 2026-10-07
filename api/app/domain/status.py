"""Project status for the dashboard (FR-UI-1).

Counts, blockers, open gates and agent activity are derived from the
same rows the orchestrator already stores. The UI does not invent them.
"""

from collections import Counter


AGENT_ROLES = ("pm", "backend", "frontend", "ai_engineer", "fullstack", "qa")


def task_counts(tasks: list) -> dict[str, int]:
    counts = Counter(str(task.state) for task in tasks)
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def blocked_with_blockers(tasks: list) -> list[tuple[str, list[str]]]:
    """Return (task_key, unfinished dependency keys) for blocked tasks."""

    by_id = {task.id: task for task in tasks}
    rows: list[tuple[str, list[str]]] = []
    for task in tasks:
        if task.state != "blocked":
            continue
        waiting: list[str] = []
        for dep in task.dependencies:
            other = by_id.get(dep.depends_on_id)
            if other is None:
                continue
            if other.state != "done":
                waiting.append(other.key)
        rows.append((task.key, sorted(waiting)))
    return sorted(rows, key=lambda item: item[0])


def open_gates(*, next_actions: list[str], tasks: list) -> list[str]:
    gates: list[str] = []
    if "approve_requirements" in next_actions:
        gates.append("requirements")
    if "approve_architecture" in next_actions:
        gates.append("architecture")
    if "unpause" in next_actions:
        gates.append("unpause")
    if "answer_clarifications" in next_actions or "proceed_on_assumptions" in next_actions:
        gates.append("clarifications")
    for task in sorted(tasks, key=lambda item: item.key):
        if task.state == "gated":
            gates.append(f"merge:{task.key}")
        elif task.state == "escalated":
            gates.append(f"resume:{task.key}")
        elif task.state == "in_review":
            gates.append(f"review:{task.key}")
    return gates


def agent_states(*, stage: str, tasks: list) -> list[tuple[str, str]]:
    """Map each role to working, waiting, or idle."""

    states = {role: "idle" for role in AGENT_ROLES}
    planning = stage != "tasks_ready"
    if planning:
        states["pm"] = "working" if stage not in {"intake"} else "waiting"
        if stage == "intake":
            states["pm"] = "waiting"

    for task in tasks:
        zone = str(task.zone)
        if zone not in states:
            continue
        if task.state == "in_progress":
            states[zone] = "working"
        elif task.state == "in_review":
            if states[zone] != "working":
                states[zone] = "waiting"
            states["fullstack"] = "working"
            states["qa"] = "waiting"
        elif task.state == "gated":
            if states[zone] != "working":
                states[zone] = "waiting"
            if states["fullstack"] != "working":
                states["fullstack"] = "waiting"
            if states["qa"] != "working":
                states["qa"] = "waiting"
        elif task.state == "ready" and states[zone] == "idle":
            states[zone] = "waiting"
    return [(role, states[role]) for role in AGENT_ROLES]


def needs_you(*, open_gate_list: list[str], tasks: list, findings: list) -> list[str]:
    lines: list[str] = []
    for gate in open_gate_list:
        if gate == "requirements":
            lines.append("Requirements approval pending")
        elif gate == "architecture":
            lines.append("Architecture approval pending")
        elif gate == "unpause":
            lines.append("Project paused")
        elif gate == "clarifications":
            lines.append("Clarifications waiting")
        elif gate.startswith("merge:"):
            lines.append(f"{gate.split(':', 1)[1]} awaiting merge")
        elif gate.startswith("resume:"):
            lines.append(f"{gate.split(':', 1)[1]} escalated")
    untestable_tasks = {
        finding.task_id
        for finding in findings
        if finding.result == "untestable"
    }
    for task in sorted(tasks, key=lambda item: item.key):
        if task.state == "in_review" and task.id in untestable_tasks:
            lines.append(f"{task.key} untestable")
    seen: set[str] = set()
    ordered: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        ordered.append(line)
    return ordered
