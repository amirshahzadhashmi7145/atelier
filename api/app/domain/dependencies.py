"""Detect dependency-manifest changes in a branch diff (FR-DEV-8).

Additions must be called out in the pull request. Registry enforcement
is a later gate; this module only names the files that changed.
"""

from __future__ import annotations

_DEP_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "requirements.in",
    "pyproject.toml",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Gemfile",
    "Gemfile.lock",
}


def dependency_files(diff: str) -> list[str]:
    """Return dependency manifest paths touched in a unified diff."""

    found: list[str] = []
    seen: set[str] = set()
    for line in diff.splitlines():
        if not line.startswith("+++ "):
            continue
        path = line[4:].strip()
        if path.startswith("b/"):
            path = path[2:]
        if path == "/dev/null":
            continue
        path = path.replace("\\", "/").lstrip("./")
        name = path.rsplit("/", 1)[-1]
        if name in _DEP_NAMES and path not in seen:
            seen.add(path)
            found.append(path)
    return found
