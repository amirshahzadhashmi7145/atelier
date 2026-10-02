"""Which directories a role is allowed to write.

The ownership map is a list of (glob, zone) rules produced with the
architecture. A write is legal only when the most specific matching
rule names the role that is running. `server/**` can belong to backend
while `server/ai/**` belongs to the AI engineer.
"""

import fnmatch
from pathlib import PurePosixPath

from app.errors import DomainError


def glob_matches(pattern: str, relative_path: str) -> bool:
    pattern = pattern.replace("\\", "/").lstrip("./")
    path = relative_path.replace("\\", "/").lstrip("./")
    if pattern.endswith("/**"):
        root = pattern[: -3].rstrip("/")
        return path == root or path.startswith(root + "/")
    return fnmatch.fnmatch(path, pattern)


def zone_for(relative_path: str, rules: list[tuple[str, str]]) -> str | None:
    matched = [(pattern, zone) for pattern, zone in rules if glob_matches(pattern, relative_path)]
    if not matched:
        return None
    matched.sort(key=lambda item: len(item[0]), reverse=True)
    return matched[0][1]


def require_inside_zone(relative_path: str, zone: str, rules: list[tuple[str, str]]) -> None:
    if relative_path.startswith("/") or ".." in PurePosixPath(relative_path).parts:
        raise DomainError(f"'{relative_path}' is not a path inside the workspace.", status_code=422)
    owner = zone_for(relative_path, rules)
    if owner != zone:
        raise DomainError(
            f"'{relative_path}' is outside the {zone} zone. Nothing was written.",
            status_code=422,
        )
