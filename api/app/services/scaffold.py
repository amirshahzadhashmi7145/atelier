"""Seed a workspace so declared test commands can run before the first agent commit.

Architecture approval creates zone folders, dependency manifests, and harness
tests that match the strategy. Agents expand these files inside their zones.
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath

from app.services.workspace import Workspace

def ownership_roots(ownership: list[tuple[str, str]]) -> dict[str, str]:
    """Map zone -> first directory root from globs like backend/**."""

    roots: dict[str, str] = {}
    for pattern, zone in ownership:
        cleaned = pattern.replace("\\", "/").lstrip("./")
        for suffix in ("/**/*", "/**", "/*", "*"):
            if cleaned.endswith(suffix) and suffix != "*":
                cleaned = cleaned[: -len(suffix)].rstrip("/")
                break
        if not cleaned or cleaned == "*":
            continue
        root = cleaned.split("/")[0]
        if root and zone not in roots:
            roots[zone] = root
    return roots


def ensure_test_ownership(
    ownership: list[tuple[str, str]],
    strategy: dict[str, str],
) -> list[tuple[str, str]]:
    """Append globs so agents can maintain harness paths the strategy names."""

    existing = {(pattern, zone) for pattern, zone in ownership}
    extra: list[tuple[str, str]] = []
    commands = " ".join(str(strategy.get(tier, "")) for tier in ("unit", "integration", "ui"))
    if "pytest" in commands.lower() or "python" in commands.lower():
        for pattern, zone in (("tests/**", "backend"), ("requirements.txt", "backend")):
            if (pattern, zone) not in existing and not any(p == pattern for p, _z in ownership):
                extra.append((pattern, zone))
    if any(prog in commands.lower() for prog in ("npm", "npx", "node ", "yarn", "pnpm")):
        for pattern, zone in (
            ("package.json", "frontend"),
            ("package-lock.json", "frontend"),
            ("scripts/**", "frontend"),
        ):
            if not any(p == pattern for p, _z in ownership):
                extra.append((pattern, zone))
    return [*ownership, *extra]


def scaffold_writes(
    ownership: list[tuple[str, str]],
    strategy: dict[str, str],
) -> list[tuple[str, str]]:
    """Return relative path/content pairs to commit on main."""

    writes: list[tuple[str, str]] = []
    roots = ownership_roots(ownership)
    for zone, root in roots.items():
        writes.append((f"{root}/.gitkeep", ""))

    commands = {tier: str(strategy.get(tier, "")).strip() for tier in ("unit", "integration", "ui")}
    joined = " ".join(commands.values()).lower()

    if "pytest" in joined or "python3 -m pytest" in joined or "python -m pytest" in joined:
        writes.append(
            (
                "requirements.txt",
                "pytest>=8.0\nhttpx>=0.27\nfastapi>=0.115\npydantic>=2.0\n",
            )
        )
        for tier, command in commands.items():
            if "pytest" not in command.lower():
                continue
            target = _pytest_target(command)
            if target:
                writes.append(
                    (
                        f"{target}/test_harness.py",
                        (
                            '"""Harness so declared pytest commands collect before feature tests exist."""\n\n'
                            "def test_harness_collects() -> None:\n"
                            "    assert True\n"
                        ),
                    )
                )

    if any(token in joined for token in ("npm", "npx", "yarn", "pnpm", "node ")):
        frontend = roots.get("frontend", "frontend")
        ui_script = "scripts/verify_ui.js"
        writes.append(
            (
                ui_script,
                (
                    "const assert = require('assert');\n"
                    "const fs = require('fs');\n"
                    "const path = require('path');\n"
                    "assert.ok(fs.existsSync(path.join(__dirname, '..', 'package.json')), "
                    "'package.json missing');\n"
                    f"const zone = {json.dumps(frontend)};\n"
                    "assert.ok(\n"
                    "  fs.existsSync(zone) || fs.existsSync('web') || fs.existsSync('frontend'),\n"
                    "  'frontend zone missing'\n"
                    ");\n"
                    "process.exit(0);\n"
                ),
            )
        )
        writes.append(
            (
                "package.json",
                json.dumps(
                    {
                        "name": "atelier-project",
                        "private": True,
                        "scripts": {
                            "test": "node scripts/verify_ui.js",
                        },
                    },
                    indent=2,
                )
                + "\n",
            )
        )

    # Deduplicate by path (last wins).
    by_path: dict[str, str] = {}
    for relative, content in writes:
        by_path[relative.replace("\\", "/")] = content
    return list(by_path.items())


def apply_scaffold(
    workspace: Workspace,
    ownership: list[tuple[str, str]],
    strategy: dict[str, str],
) -> list[str]:
    """Commit scaffold files on main when missing. Returns written paths."""

    workspace.ensure()
    workspace.start_branch("main")
    writes: list[tuple[str, str]] = []
    for relative, content in scaffold_writes(ownership, strategy):
        path = workspace.root / relative
        if path.exists():
            # Do not clobber agent or prior scaffold content.
            continue
        writes.append((relative, content))
    if not writes:
        return []
    workspace.commit("ARCH", "Seed zone layout and test harnesses.", writes, role="system")
    return [relative for relative, _content in writes]


def _pytest_target(command: str) -> str | None:
    """Extract a directory argument from a pytest command."""

    parts = command.split()
    for part in parts:
        if part.startswith("-"):
            continue
        if part in {"python", "python3", "pytest", "-m"}:
            continue
        if part == "pytest":
            continue
        cleaned = part.strip("'\"")
        if cleaned.endswith(".py"):
            parent = str(PurePosixPath(cleaned).parent)
            return parent if parent != "." else None
        if "test" in cleaned.lower() or cleaned.startswith("tests"):
            return cleaned.rstrip("/")
    # Default layout when command is bare `pytest` / `python -m pytest`.
    if "pytest" in command.lower():
        return "tests/unit"
    return None
