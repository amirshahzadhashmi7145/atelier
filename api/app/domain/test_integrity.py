"""Reject diffs that weaken the existing test suite (FR-DEV-10).

Agents must not delete tests, strip assertions, or mark tests skipped
to make a change pass. Review applies these rules to the branch diff
before criteria judgment.
"""

from __future__ import annotations

import re

_TEST_PATH = re.compile(
    r"(^|/)(tests?/|__tests__/)|"
    r"(^|/)test_[^/]+\.py$|"
    r"\.(test|spec)\.[jt]sx?$|"
    r"_test\.py$",
    re.IGNORECASE,
)

_ASSERT_REMOVED = re.compile(
    r"^\-\s*(assert\b|expect\(|self\.assert|pytest\.raises|should\.)",
    re.IGNORECASE,
)

_SKIP_ADDED = re.compile(
    r"^\+\s*(@pytest\.mark\.(skip|xfail)|@unittest\.skip|pytest\.skip\(|"
    r"it\.skip\(|describe\.skip\(|test\.skip\(|xdescribe\(|xit\()",
    re.IGNORECASE,
)


def _is_test_path(path: str) -> bool:
    path = path.replace("\\", "/").lstrip("./")
    if path in {"/dev/null", "dev/null"}:
        return False
    return bool(_TEST_PATH.search(path))


def weakened_tests(diff: str) -> list[str]:
    """Return human-readable reasons the diff weakens tests, or empty."""

    if not diff.strip():
        return []
    reasons: list[str] = []
    current: str | None = None
    new_path: str | None = None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            current = None
            new_path = None
            continue
        if line.startswith("--- "):
            old = line[4:].strip()
            if old.startswith("a/"):
                old = old[2:]
            current = old if old != "/dev/null" else None
            continue
        if line.startswith("+++ "):
            new = line[4:].strip()
            if new.startswith("b/"):
                new = new[2:]
            new_path = None if new == "/dev/null" else new
            old_test = bool(current and _is_test_path(current))
            new_test = bool(new_path and _is_test_path(new_path))
            if old_test and new_path is None:
                reasons.append(f"Deleted test file '{current}'.")
                current = None  # whole-file delete; ignore removed lines in the hunk
                continue
            current = new_path if new_test else (current if old_test else None)
            continue
        if not current or not _is_test_path(current):
            continue
        if _ASSERT_REMOVED.match(line):
            reasons.append(f"Removed an assertion in '{current}'.")
        elif _SKIP_ADDED.match(line):
            reasons.append(f"Marked a test skipped in '{current}'.")
    # Stable unique order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in reasons:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
