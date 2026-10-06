"""How a task becomes a pull request description.

The model wrote the code. This module writes the PR: task and requirement
ids, the change summary, the test results, and any assumptions. A missing
piece is left blank rather than invented.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckLine:
    tier: str
    command: str
    exit_code: int
    excerpt: str = ""


@dataclass(frozen=True)
class PullRequestDraft:
    title: str
    body: str


def compose(
    *,
    task_key: str,
    title: str,
    summary: str,
    requirement_keys: list[str],
    checks: list[CheckLine],
    assumptions: list[str],
    dependencies: list[str] | None = None,
) -> PullRequestDraft:
    reqs = ", ".join(requirement_keys) if requirement_keys else "(none)"
    check_lines = "\n".join(
        f"- {item.tier}: `{item.command}` exited {item.exit_code}"
        + (f" — {item.excerpt}" if item.excerpt.strip() else "")
        for item in checks
    ) or "- (no checks recorded)"
    assumption_lines = "\n".join(f"- {item}" for item in assumptions) or "- (none recorded)"
    dep_lines = "\n".join(f"- `{item}`" for item in (dependencies or [])) or "- (none)"
    body = (
        f"## Task\n{task_key}: {title}\n\n"
        f"## Requirements\n{reqs}\n\n"
        f"## Summary\n{summary.strip() or '(no summary)'}\n\n"
        f"## Test results\n{check_lines}\n\n"
        f"## Dependencies\n{dep_lines}\n\n"
        f"## Assumptions\n{assumption_lines}\n"
    )
    return PullRequestDraft(title=f"{task_key}: {title}", body=body)
