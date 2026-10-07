"""Reject always-green placeholder test commands.

Architecture must name commands that exercise behaviour, not
`print('unit ok')` / `console.log('ok')` smokes that never fail.
"""

from __future__ import annotations

import re

from app.errors import DomainError

TIERS = ("unit", "integration", "ui")

_OK_PRINT = re.compile(
    r"""(?ix)
    (?:print|console\.log)\s*\(\s*['"][^'"]*\bok\b[^'"]*['"]\s*\)
    """
)


def is_trivial_test_command(command: str) -> bool:
    text = " ".join(command.strip().split())
    if not text:
        return True
    lowered = text.lower()
    if lowered in {"true", ":", "exit 0", "/bin/true", "cmd /c exit 0"}:
        return True
    if not _OK_PRINT.search(text):
        return False
    # A print/console.log of "…ok…" is fine only when the script also asserts.
    if re.search(r"\bassert\b", lowered) or "raise " in lowered or "throw " in lowered:
        return False
    if re.search(r"\b(import|require|from)\b", lowered) and (
        "sys.exit" in lowered or ".exit(" in lowered or "process.exit" in lowered
    ):
        return False
    return True


def validate_test_strategy(strategy: dict) -> None:
    """Raise DomainError when unit/integration/ui are missing or placeholders."""

    missing = [name for name in TIERS if not str(strategy.get(name, "")).strip()]
    if missing:
        raise DomainError(
            "The architecture must name commands for: " + ", ".join(missing),
            status_code=422,
        )
    commands = {name: str(strategy[name]).strip() for name in TIERS}
    trivial = [name for name, command in commands.items() if is_trivial_test_command(command)]
    if trivial:
        raise DomainError(
            "Test commands must exercise acceptance behaviour, not placeholder "
            "print/console.log smokes. Replace: " + ", ".join(trivial) + ".",
            status_code=422,
        )
    values = list(commands.values())
    if len(set(values)) == 1 and is_trivial_test_command(values[0]):
        raise DomainError(
            "Unit, integration, and ui commands cannot be the same placeholder.",
            status_code=422,
        )
