"""Deterministic full-stack review before QA.

LLM QA cannot be trusted alone. This gate fails the branch when symbols
were dropped vs main or tests do not evidence acceptance criteria.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.domain.ac_evidence import blob_from_test_writes, evidenced_keys, evidence_gaps
from app.domain.preserve import removed_symbols
from app.domain.qa import Finding


def staff_gate_issues(
    *,
    root: Path,
    main_files: dict[str, str],
    criteria: list[tuple[str, str]],
    check_excerpts: str,
) -> list[tuple[str, str]]:
    """Return (code, detail) problems that must block QA."""

    issues: list[tuple[str, str]] = []
    on_disk: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", ".deps", "node_modules", "__pycache__"} for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            on_disk.append((rel, path.read_text(encoding="utf-8")))
        except OSError:
            continue

    gaps = evidence_gaps(
        criteria,
        check_excerpts=check_excerpts,
        write_contents=blob_from_test_writes(on_disk),
    )
    if gaps:
        issues.append(
            (
                "ac_evidence",
                "Tests/checks do not evidence: " + ", ".join(gaps) + ".",
            )
        )

    for rel, content in on_disk:
        if not rel.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
            continue
        previous = main_files.get(rel)
        if previous is None:
            continue
        dropped = removed_symbols(previous, content)
        if dropped:
            issues.append(
                (
                    "api_clobber",
                    f"{rel} drops {', '.join(dropped)} vs main. "
                    "Keep prior exports and extend.",
                )
            )
    return issues


def force_evidenced_passes(
    criteria: list[tuple[str, str]],
    findings: list[Finding],
    *,
    check_excerpts: str,
    root: Path,
) -> list[Finding]:
    """Upgrade untestable→pass only when tests/checks already prove that AC.

    Criteria with no extractable signals stay as QA marked them — the gate
    cannot invent proof for wall-clock or observational checks.
    """

    on_disk: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", ".deps", "node_modules", "__pycache__"} for part in path.parts):
            continue
        try:
            on_disk.append(
                (path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
            )
        except OSError:
            continue
    proven = evidenced_keys(
        criteria,
        check_excerpts=check_excerpts,
        write_contents=blob_from_test_writes(on_disk),
    )
    upgraded: list[Finding] = []
    for item in findings:
        if item.result != "untestable" or item.criterion_key not in proven:
            upgraded.append(item)
            continue
        note = (item.note or "").strip()
        suffix = "staff evidence gate: proven by tests/checks"
        upgraded.append(
            replace(
                item,
                result="pass",
                note=f"{note} [{suffix}]".strip() if note else suffix,
            )
        )
    return upgraded
