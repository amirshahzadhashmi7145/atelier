"""Refuse agent rewrites that drop existing public symbols.

Later tasks often replace backend/main.py from scratch and delete helpers
or endpoints earlier tests still import (e.g. reset_store). That turns a
green suite red before the new feature is even exercised.
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
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def removed_symbols(previous: str, proposed: str) -> list[str]:
    """Names defined at module top-level in previous that proposed drops."""

    return sorted(top_level_symbols(previous) - top_level_symbols(proposed))


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
