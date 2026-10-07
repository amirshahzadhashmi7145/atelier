"""Require check output / test writes to mention acceptance signals.

QA marked FR-001 untestable when pytest only ran an empty harness. A green
exit code is not enough — the excerpts (or newly written tests) must speak
to status codes and named response fields from the criteria.
"""

from __future__ import annotations

import re

_STATUS = re.compile(r"\b([1-5]\d{2})\b")
_FIELD_LIST = re.compile(
    r"(?:includes?|contain(?:s|ing)?|with|has)\s+([a-z_][a-z0-9_]*(?:\s*,\s*[a-z_][a-z0-9_]*)+)",
    re.IGNORECASE,
)
_TEST_PATH = re.compile(
    r"(^|/)(tests?/|__tests__/)|(^|/)test_[^/]+\.py$|\.(test|spec)\.[jt]sx?$|_test\.py$",
    re.IGNORECASE,
)


def evidence_gaps(
    criteria: list[tuple[str, str]],
    *,
    check_excerpts: str,
    write_contents: str,
) -> list[str]:
    """Return criterion keys whose signals never appear in tests or check output."""

    corpus = f"{check_excerpts}\n{write_contents}".lower()
    gaps: list[str] = []
    for key, statement in criteria:
        needles = _needles(statement)
        if not needles:
            continue
        # Pass when every status code is present, or (for field lists) most fields.
        statuses = [n for n in needles if n.isdigit()]
        fields = [n for n in needles if not n.isdigit()]
        status_ok = not statuses or all(s.lower() in corpus for s in statuses)
        if fields:
            hit = sum(1 for f in fields if f.lower() in corpus)
            fields_ok = hit >= max(1, (len(fields) + 1) // 2)
        else:
            fields_ok = True
        if status_ok and fields_ok:
            continue
        gaps.append(key)
    return gaps


def evidenced_keys(
    criteria: list[tuple[str, str]],
    *,
    check_excerpts: str,
    write_contents: str,
) -> set[str]:
    """Keys that declare extractable signals and are fully covered by tests/checks."""

    gaps = set(
        evidence_gaps(
            criteria,
            check_excerpts=check_excerpts,
            write_contents=write_contents,
        )
    )
    covered: set[str] = set()
    for key, statement in criteria:
        if not _needles(statement):
            continue
        if key not in gaps:
            covered.add(key)
    return covered


def _needles(statement: str) -> list[str]:
    found: list[str] = []
    for match in _STATUS.finditer(statement):
        found.append(match.group(1))
    listed = _FIELD_LIST.search(statement)
    if listed:
        for part in listed.group(1).split(","):
            name = part.strip().strip("'\"")
            if name and name.lower() not in {"and", "or", "the", "a", "an"}:
                found.append(name)
    # Deduplicate, keep order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in found:
        low = item.lower()
        if low in seen:
            continue
        seen.add(low)
        ordered.append(item)
    return ordered


def blob_from_test_writes(writes: list[tuple[str, str]]) -> str:
    """Concatenate contents of files that look like tests."""

    chunks: list[str] = []
    for path, content in writes:
        if _TEST_PATH.search(path.replace("\\", "/")):
            chunks.append(content)
    return "\n".join(chunks)
