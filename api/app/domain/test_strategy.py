"""Reject always-green placeholder test commands.

Architecture must name commands that exercise behaviour, not
`print('unit ok')` / `console.log('ok')` smokes that never fail.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from app.errors import DomainError

TIERS = ("unit", "integration", "ui")
_JS_TEST_BINARIES = frozenset({"vitest", "jest", "mocha"})

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


def normalize_test_strategy(
    strategy: dict,
    *,
    package_prefix: str = "frontend",
) -> dict[str, str]:
    """Rewrite bare JS test binaries so the sandbox can exec them.

    `vitest --run` is not on PATH in the Node image. Prefer
    `npm --prefix <dir> run test:unit` so npm sets cwd to the package root
    (vitest discovers tests) and local node_modules/.bin is used.
    """

    out: dict[str, str] = {}
    for name in TIERS:
        command = str(strategy.get(name, "")).strip()
        if not command:
            out[name] = command
            continue
        try:
            parts = shlex.split(command)
        except ValueError:
            out[name] = command
            continue
        if not parts:
            out[name] = command
            continue
        binary = Path(parts[0]).name.lower()
        if binary not in _JS_TEST_BINARIES:
            out[name] = command
            continue
        prefix = (package_prefix or "frontend").strip().strip("/") or "frontend"
        script = "test:unit" if binary == "vitest" else "test"
        rewritten = ["npm", "--prefix", prefix, "run", script]
        out[name] = " ".join(shlex.quote(part) for part in rewritten)
    return out


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
