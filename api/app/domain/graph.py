"""Dependency cycles.

A task graph with a cycle can never become ready: each task waits on
another task that is waiting on it. The orchestrator rejects the graph
and nothing is saved (FR-ORCH-7).
"""

from app.errors import DomainError


def find_cycle(nodes: list[str], edges: list[tuple[str, str]]) -> list[str] | None:
    """Return one cycle if `edges` of (task, depends_on) loop, else None.

    Depth-first search with three colours:
    white = not seen, grey = on the current path, black = finished.
    A grey node seen again is a cycle.
    """

    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for task_id, depends_on in edges:
        adjacency.setdefault(task_id, []).append(depends_on)
        adjacency.setdefault(depends_on, [])

    color: dict[str, str] = {node: "white" for node in adjacency}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = "grey"
        stack.append(node)
        for nxt in adjacency.get(node, []):
            if color.get(nxt) == "grey":
                start = stack.index(nxt)
                return stack[start:] + [nxt]
            if color.get(nxt, "white") == "white":
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = "black"
        return None

    for node in list(adjacency):
        if color[node] == "white":
            found = visit(node)
            if found:
                return found
    return None


def require_acyclic(nodes: list[str], edges: list[tuple[str, str]]) -> None:
    cycle = find_cycle(nodes, edges)
    if cycle:
        raise DomainError(
            "Task graph has a cycle: " + " -> ".join(cycle) + ". Nothing was saved."
        )
