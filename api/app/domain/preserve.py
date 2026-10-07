"""Keep earlier APIs when agents rewrite files (Cursor-style, not clobber).

Later tasks often replace backend/main.py from scratch and delete helpers
or endpoints earlier tests still import (e.g. reset_store). Full-file writes
are merged so dropped top-level symbols are copied forward; edits apply as
search/replace on the existing file.
"""

from __future__ import annotations

import ast
from pathlib import Path


def top_level_symbols(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in tree.body:
        names |= _node_names(node)
    return names


def _node_names(node: ast.AST) -> set[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, ast.Assign):
        return {target.id for target in node.targets if isinstance(target, ast.Name)}
    return set()


def removed_symbols(previous: str, proposed: str) -> list[str]:
    """Names defined at module top-level in previous that proposed drops."""

    return sorted(top_level_symbols(previous) - top_level_symbols(proposed))


def merge_keeping_symbols(previous: str, proposed: str) -> str:
    """Append any top-level defs the rewrite dropped (Python modules)."""

    dropped = set(removed_symbols(previous, proposed))
    if not dropped:
        return proposed
    try:
        tree = ast.parse(previous)
    except SyntaxError:
        return previous
    chunks: list[str] = []
    for node in tree.body:
        if not (_node_names(node) & dropped):
            continue
        segment = ast.get_source_segment(previous, node)
        if segment:
            chunks.append(segment.rstrip())
    if not chunks:
        return proposed
    return proposed.rstrip() + "\n\n" + "\n\n".join(chunks) + "\n"


def materialize_writes(
    root: Path,
    writes: list[tuple[str, str]],
    edits: list[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    """Resolve full writes + surgical edits into final file contents.

    Edits are Cursor-like search/replace (exactly one match). Full writes to
    existing .py files keep any top-level symbols the rewrite would drop.
    """

    files: dict[str, str] = {}
    for relative, content in writes:
        files[relative.replace("\\", "/")] = content

    for relative, old, new in edits:
        rel = relative.replace("\\", "/")
        if not old:
            raise ValueError(f"{rel}: edit old_string must not be empty.")
        base = files.get(rel)
        if base is None:
            path = root / rel
            if not path.is_file():
                raise ValueError(f"{rel}: edit target does not exist; use writes for new files.")
            base = path.read_text(encoding="utf-8")
        count = base.count(old)
        if count == 0:
            raise ValueError(f"{rel}: edit old_string not found in file.")
        if count > 1:
            raise ValueError(f"{rel}: edit old_string matches {count} times; make it unique.")
        files[rel] = base.replace(old, new, 1)

    out: list[tuple[str, str]] = []
    for rel, content in sorted(files.items()):
        path = root / rel
        if path.is_file() and rel.endswith(".py"):
            try:
                previous = path.read_text(encoding="utf-8")
            except OSError:
                previous = ""
            if previous:
                # Edits already started from disk; merge only when a full write
                # (or edit result) would still drop names vs the pre-edit file.
                # Use pre-materialize disk text so we never lose TASK-001 helpers.
                content = merge_keeping_symbols(previous, content)
        out.append((rel, content))
    return out


def missing_from_rewrites(
    root: Path,
    writes: list[tuple[str, str]],
) -> list[str]:
    """Human-readable reasons a rewrite drops symbols from an existing file."""

    reasons: list[str] = []
    for relative, content in writes:
        if not relative.endswith(".py"):
            continue
        path = root / relative
        if not path.is_file():
            continue
        try:
            previous = path.read_text(encoding="utf-8")
        except OSError:
            continue
        dropped = removed_symbols(previous, content)
        if not dropped:
            continue
        reasons.append(
            f"{relative} removes {', '.join(dropped)}. Keep prior endpoints and "
            "helpers; add new code beside them."
        )
    return reasons
