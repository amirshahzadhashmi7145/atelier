"""Seed a workspace so declared test commands can run before the first agent commit.

Architecture approval creates zone folders, dependency manifests, and harness
tests that match the strategy. Agents expand these files inside their zones.
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath

from app.services.workspace import Workspace

_JS_TEST_TOKENS = ("vitest", "jest", "mocha")


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
    lowered = commands.lower()
    if "pytest" in lowered or "python" in lowered:
        for pattern, zone in (("tests/**", "backend"), ("requirements.txt", "backend")):
            if (pattern, zone) not in existing and not any(p == pattern for p, _z in ownership):
                extra.append((pattern, zone))
    needs_node = any(
        prog in lowered for prog in ("npm", "npx", "node ", "yarn", "pnpm", *_JS_TEST_TOKENS)
    )
    if needs_node:
        prefix = _npm_prefix(str(strategy.get("ui", ""))) or _js_package_prefix(strategy)
        patterns = [
            ("package.json", "frontend"),
            ("package-lock.json", "frontend"),
            ("scripts/**", "frontend"),
        ]
        if prefix:
            patterns = [
                (f"{prefix}/package.json", "frontend"),
                (f"{prefix}/package-lock.json", "frontend"),
                (f"{prefix}/scripts/**", "frontend"),
                *patterns,
            ]
        for pattern, zone in patterns:
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
                # Unique basenames — same test_harness.py in unit+integration
                # collides under pytest import caching.
                stem = target.rstrip("/").replace("/", "_")
                writes.append(
                    (
                        f"{target}/test_{stem}_harness.py",
                        (
                            '"""Harness so declared pytest commands collect before feature tests exist."""\n\n'
                            "def test_harness_collects() -> None:\n"
                            "    assert True\n"
                        ),
                    )
                )

    needs_node = any(
        token in joined for token in ("npm", "npx", "yarn", "pnpm", "node ", *_JS_TEST_TOKENS)
    )
    if needs_node:
        # `npm --prefix <dir> test` needs package.json under <dir>; bare `npm test` at root.
        prefix = _npm_prefix(commands.get("ui", "")) or _js_package_prefix(strategy)
        # Default frontend zone when vitest/jest is declared without an npm --prefix.
        if prefix is None and any(token in joined for token in _JS_TEST_TOKENS):
            prefix = roots.get("frontend", "frontend")
        pkg_dir = prefix or ""
        ui_script = f"{pkg_dir}/scripts/verify_ui.js" if pkg_dir else "scripts/verify_ui.js"
        pkg_path = f"{pkg_dir}/package.json" if pkg_dir else "package.json"
        # npm --prefix <dir> runs scripts with cwd=<dir>; package.json is parent of scripts/.
        writes.append(
            (
                ui_script,
                (
                    "const assert = require('assert');\n"
                    "const fs = require('fs');\n"
                    "const path = require('path');\n"
                    "const pkg = path.join(__dirname, '..', 'package.json');\n"
                    "assert.ok(fs.existsSync(pkg), 'package.json missing at ' + pkg);\n"
                    "process.exit(0);\n"
                ),
            )
        )
        pkg: dict = {
            "name": "atelier-frontend" if pkg_dir else "atelier-project",
            "private": True,
            "scripts": {
                "test": "node scripts/verify_ui.js",
            },
        }
        if "vitest" in joined:
            # Invoke via node — workspace disks (e.g. NTFS) often strip +x on .bin shims.
            # Single worker stays under the sandbox pids limit.
            pkg["scripts"]["test:unit"] = (
                "node ./node_modules/vitest/vitest.mjs --run --pool=threads --maxWorkers=1"
            )
            pkg["devDependencies"] = {"vitest": "^3.0.0"}
            # .mjs so package.json can stay CommonJS for scripts/verify_ui.js.
            harness = f"{pkg_dir}/tests/harness.test.mjs" if pkg_dir else "tests/harness.test.mjs"
            writes.append(
                (
                    harness,
                    (
                        "import { describe, expect, it } from 'vitest';\n\n"
                        "describe('harness', () => {\n"
                        "  it('collects', () => {\n"
                        "    expect(true).toBe(true);\n"
                        "  });\n"
                        "});\n"
                    ),
                )
            )
        elif "jest" in joined:
            pkg["devDependencies"] = {"jest": "^29.7.0"}
        writes.append((pkg_path, json.dumps(pkg, indent=2) + "\n"))

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
            # Merge vitest/jest deps into an existing package.json; never clobber other files.
            if path.name == "package.json":
                merged = _merge_package_json(path.read_text(encoding="utf-8"), content)
                if merged is not None and merged != path.read_text(encoding="utf-8"):
                    writes.append((relative, merged))
            continue
        writes.append((relative, content))
    if not writes:
        return []
    workspace.commit("ARCH", "Seed zone layout and test harnesses.", writes, role="system")
    return [relative for relative, _content in writes]


def _merge_package_json(existing_text: str, desired_text: str) -> str | None:
    """Add missing scripts/devDependencies from the scaffold desired manifest."""

    try:
        existing = json.loads(existing_text)
        desired = json.loads(desired_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(existing, dict) or not isinstance(desired, dict):
        return None
    changed = False
    scripts = existing.setdefault("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}
        existing["scripts"] = scripts
    for key, value in (desired.get("scripts") or {}).items():
        if key not in scripts:
            scripts[key] = value
            changed = True
    dev = existing.setdefault("devDependencies", {})
    if not isinstance(dev, dict):
        dev = {}
        existing["devDependencies"] = dev
    for key, value in (desired.get("devDependencies") or {}).items():
        if key not in dev:
            dev[key] = value
            changed = True
    if not changed:
        return None
    return json.dumps(existing, indent=2) + "\n"


def _npm_prefix(command: str) -> str | None:
    """Return the directory from `npm --prefix <dir> …`, if present."""

    parts = command.split()
    for index, part in enumerate(parts):
        if part == "--prefix" and index + 1 < len(parts):
            return parts[index + 1].strip("'\"").rstrip("/")
        if part.startswith("--prefix="):
            return part.split("=", 1)[1].strip("'\"").rstrip("/")
    return None


def _js_package_prefix(strategy: dict[str, str]) -> str | None:
    """Infer package dir from normalized `npm --prefix <dir> exec -- vitest` commands."""

    for tier in ("unit", "integration", "ui"):
        prefix = _npm_prefix(str(strategy.get(tier, "")))
        if prefix:
            return prefix
    return None


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
