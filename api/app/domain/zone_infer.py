"""Infer the right ownership zone so mis-zoned tasks self-correct.

Task generation and implement agents sometimes put Vite/package.json work on
backend. Prefer path ownership and strong text signals over the model's zone.
"""

from __future__ import annotations

from app.domain.zones import zone_for

_FRONTEND_STRONG = (
    "vite",
    "package.json",
    "typescript with vite",
    "html canvas",
    "no game engine",
    "ui framework",
    "settings overlay",
    "pause menu",
    "sound effects",
    "requestanimationframe",
    "technology stack",
)

_FRONTEND_WEAK = (
    "hud",
    "canvas",
    "overlay",
    "animation",
    "frontend",
    "dom",
    "typescript",
    "volume slider",
)

_BACKEND_STRONG = (
    "fastapi",
    "pytest",
    "api endpoint",
    "database",
    "sqlalchemy",
    "server/",
)


def infer_zone_from_text(
    title: str,
    description: str,
    known_zones: set[str],
) -> str | None:
    """Return a better zone from task wording, or None when unsure."""

    text = f"{title}\n{description}".lower()
    if any(needle in text for needle in _FRONTEND_STRONG) and "frontend" in known_zones:
        return "frontend"
    if any(needle in text for needle in _BACKEND_STRONG) and "backend" in known_zones:
        # Don't override clear frontend stack wording.
        if not any(needle in text for needle in _FRONTEND_STRONG):
            return "backend"
    front = sum(1 for needle in _FRONTEND_WEAK if needle in text)
    back = sum(1 for needle in ("backend", "server", "api", "grid size") if needle in text)
    if front > back and "frontend" in known_zones:
        return "frontend"
    if back > front and "backend" in known_zones:
        return "backend"
    return None


def infer_zone_from_paths(
    paths: list[str],
    rules: list[tuple[str, str]],
) -> str | None:
    """If every path has the same owner, return that zone."""

    owners: list[str] = []
    for path in paths:
        owner = zone_for(path, rules)
        if owner is None:
            return None
        owners.append(owner)
    if not owners:
        return None
    unique = set(owners)
    if len(unique) != 1:
        return None
    return next(iter(unique))


def normalize_task_zone(
    *,
    zone: str,
    title: str,
    description: str,
    known_zones: set[str],
) -> str:
    """Prefer inferred zone when the model picked a conflicting one."""

    inferred = infer_zone_from_text(title, description, known_zones)
    if inferred and inferred in known_zones:
        return inferred
    return zone if zone in known_zones else zone
