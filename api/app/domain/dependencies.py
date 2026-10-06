"""Dependency manifest changes and registry allowlisting (FR-DEV-8).

Touched manifests are listed on the pull request. Added lines that pull
from a host outside the configured allowlist are rejected.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

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

_URL = re.compile(r"(?:git\+)?https?://[^\s\"'`\]]+", re.IGNORECASE)
_GIT_SSH = re.compile(r"git\+ssh://[^\s\"'`\]]+", re.IGNORECASE)


def is_dependency_path(path: str) -> bool:
    name = path.replace("\\", "/").lstrip("./").rsplit("/", 1)[-1]
    return name in _DEP_NAMES


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
        if is_dependency_path(path) and path not in seen:
            seen.add(path)
            found.append(path)
    return found


def _hosts_in_text(text: str) -> list[str]:
    hosts: list[str] = []
    for match in _URL.finditer(text):
        parsed = urlparse(match.group(0).removeprefix("git+"))
        if parsed.hostname:
            hosts.append(parsed.hostname.lower())
    for match in _GIT_SSH.finditer(text):
        hosts.append("git-ssh")
    return hosts


def forbidden_dependency_sources(
    *,
    diff: str = "",
    writes: list[tuple[str, str]] | None = None,
    allowed_hosts: set[str],
) -> list[str]:
    """Return reasons for dependency sources outside the allowlist."""

    allowed = {host.lower().strip() for host in allowed_hosts if host.strip()}
    reasons: list[str] = []
    seen: set[str] = set()

    def note(host: str, where: str) -> None:
        key = f"{host}|{where}"
        if key in seen:
            return
        seen.add(key)
        reasons.append(f"Dependency source '{host}' in {where} is not on the allowlist.")

    for path, content in writes or []:
        if not is_dependency_path(path):
            continue
        for host in _hosts_in_text(content):
            if host == "git-ssh" or host not in allowed:
                note(host, path)

    current: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            current = None if path == "/dev/null" else path.replace("\\", "/").lstrip("./")
            continue
        if not current or not is_dependency_path(current) or not line.startswith("+"):
            continue
        for host in _hosts_in_text(line[1:]):
            if host == "git-ssh" or host not in allowed:
                note(host, current)
    return reasons
