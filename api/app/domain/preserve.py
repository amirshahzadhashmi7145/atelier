"""Keep earlier APIs when agents rewrite files (Cursor-style, not clobber).

Later tasks often replace backend/main.py from scratch and delete helpers
or endpoints earlier tests still import (e.g. reset_store). Full-file writes
are merged so dropped top-level symbols are copied forward; edits apply as
search/replace on the existing file.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_JS_EXPORT_FN = re.compile(
    r"^export\s+(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{",
    re.MULTILINE,
)
_JS_EXPORT_DECL = re.compile(
    r"^export\s+(?:const|let|var|class)\s+(\w+)\b",
    re.MULTILINE,
)
_JS_SUFFIXES = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")


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


def js_exported_names(source: str) -> set[str]:
    """Top-level `export function` / `export const` names in a JS/TS module."""

    names = set(_JS_EXPORT_FN.findall(source))
    names.update(_JS_EXPORT_DECL.findall(source))
    return names


def removed_js_exports(previous: str, proposed: str) -> list[str]:
    return sorted(js_exported_names(previous) - js_exported_names(proposed))


def _extract_js_export_block(source: str, name: str) -> str | None:
    """Return the source of one exported function/const/class named `name`."""

    for match in _JS_EXPORT_FN.finditer(source):
        if match.group(1) != name:
            continue
        start = match.start()
        brace = source.find("{", match.end() - 1)
        if brace < 0:
            return None
        depth = 0
        for index in range(brace, len(source)):
            char = source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[start : index + 1].rstrip()
        return None
    for match in _JS_EXPORT_DECL.finditer(source):
        if match.group(1) != name:
            continue
        start = match.start()
        # const/let/var: take through the terminating semicolon at depth 0.
        depth = 0
        in_string: str | None = None
        for index in range(start, len(source)):
            char = source[index]
            if in_string:
                if char == in_string and source[index - 1] != "\\":
                    in_string = None
                continue
            if char in {'"', "'", "`"}:
                in_string = char
                continue
            if char in "{[(":
                depth += 1
            elif char in "}])":
                depth = max(0, depth - 1)
            elif char == ";" and depth == 0:
                return source[start : index + 1].rstrip()
        return source[start:].rstrip()
    return None


def merge_keeping_js_exports(previous: str, proposed: str) -> str:
    """Append exported helpers a JS rewrite dropped (keeps prior Vitest imports green)."""

    dropped = removed_js_exports(previous, proposed)
    if not dropped:
        return proposed
    chunks: list[str] = []
    for name in dropped:
        block = _extract_js_export_block(previous, name)
        if block:
            chunks.append(block)
    if not chunks:
        return previous
    return proposed.rstrip() + "\n\n" + "\n\n".join(chunks) + "\n"


def is_harness_path(relative: str) -> bool:
    name = relative.replace("\\", "/").rsplit("/", 1)[-1]
    return name == "test_harness.py" or (
        name.startswith("test_") and name.endswith("_harness.py")
    )


def is_protected_scaffold_path(relative: str) -> bool:
    """Scaffold files agents must not rewrite (green day-one checks)."""

    rel = relative.replace("\\", "/")
    name = rel.rsplit("/", 1)[-1]
    if is_harness_path(rel):
        return True
    if name == "verify_ui.js":
        return True
    if name.endswith(".test.mjs") and "/tests/" in f"/{rel}":
        return True
    return False


def materialize_writes(
    root: Path,
    writes: list[tuple[str, str]],
    edits: list[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    """Resolve full writes + surgical edits into final file contents.

    Edits are Cursor-like search/replace (exactly one match). Full writes to
    existing .py files keep any top-level symbols the rewrite would drop.
    Scaffold harness tests and verify_ui.js are never overwritten — agents
    add sibling feature files instead.
    """

    files: dict[str, str] = {}
    for relative, content in writes:
        files[relative.replace("\\", "/")] = content

    for relative, old, new in edits:
        rel = relative.replace("\\", "/")
        if is_protected_scaffold_path(rel):
            # Ignore edits that would break the green scaffold harness.
            continue
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
        if is_protected_scaffold_path(rel) and path.is_file():
            # Keep the green collect harness; agents must add new test modules.
            try:
                out.append((rel, path.read_text(encoding="utf-8")))
            except OSError:
                out.append((rel, content))
            continue
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
        elif path.is_file() and rel.endswith(_JS_SUFFIXES):
            try:
                previous = path.read_text(encoding="utf-8")
            except OSError:
                previous = ""
            if previous:
                content = merge_keeping_js_exports(previous, content)
        out.append((rel, content))
    return out


def missing_from_rewrites(
    root: Path,
    writes: list[tuple[str, str]],
) -> list[str]:
    """Human-readable reasons a rewrite drops symbols from an existing file."""

    reasons: list[str] = []
    for relative, content in writes:
        path = root / relative
        if not path.is_file():
            continue
        try:
            previous = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if relative.endswith(".py"):
            dropped = removed_symbols(previous, content)
            label = "endpoints and helpers"
        elif relative.endswith(_JS_SUFFIXES):
            dropped = removed_js_exports(previous, content)
            label = "exports"
        else:
            continue
        if not dropped:
            continue
        reasons.append(
            f"{relative} removes {', '.join(dropped)}. Keep prior {label}; "
            "add new code beside them."
        )
    return reasons
