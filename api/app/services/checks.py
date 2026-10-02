"""Run the test commands the architecture declared.

The command is taken from the approved plan and executed in the project
directory. It is one program plus arguments. Shell syntax is rejected
so a plan cannot smuggle a second command into the same string.
"""

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.errors import DomainError

TIERS = ("unit", "integration", "ui")
_OPERATORS = {";", "&&", "||", "|", "&", ">", ">>", "<", "<<"}


@dataclass(frozen=True)
class CheckResult:
    tier: str
    command: str
    exit_code: int
    excerpt: str


def parse_command(command: str) -> list[str]:
    if "\n" in command or "`" in command or "$" in command:
        raise DomainError(
            f"'{command}' is not a single program. Test commands cannot chain other programs.",
            status_code=422,
        )
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise DomainError(
            f"'{command}' could not be read as a program and its arguments.",
            status_code=422,
        ) from exc
    if not parts or any(part in _OPERATORS for part in parts):
        raise DomainError(
            f"'{command}' is not a single program. Test commands cannot chain other programs.",
            status_code=422,
        )
    return parts


def run_checks(root: Path, strategy: dict | None, timeout: int) -> list[CheckResult]:
    if not strategy:
        raise DomainError("This project has no test commands.", status_code=422)
    planned: list[tuple[str, str]] = []
    for tier in TIERS:
        command = str(strategy.get(tier, "")).strip()
        if not command:
            raise DomainError(f"The {tier} test command is missing.", status_code=422)
        parse_command(command)
        planned.append((tier, command))
    return [_run(root, tier, command, timeout) for tier, command in planned]


def _run(root: Path, tier: str, command: str, timeout: int) -> CheckResult:
    argv = parse_command(command)
    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CheckResult(tier, command, 124, _excerpt(exc.stdout, exc.stderr) or "The command timed out.")
    except FileNotFoundError:
        return CheckResult(tier, command, 127, f"Could not run {argv[0]}.")
    return CheckResult(tier, command, completed.returncode, _excerpt(completed.stdout, completed.stderr))


def _excerpt(stdout, stderr) -> str:
    text = "\n".join(part for part in (_as_text(stdout), _as_text(stderr)) if part).strip()
    if len(text) <= 800:
        return text
    return text[-800:]


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
