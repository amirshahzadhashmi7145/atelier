"""Talk to the GitHub HTTP API for pull requests and repositories.

A token is optional for local-only work. Creating a remote repository or
opening a remote pull request requires GITHUB_TOKEN.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.errors import DomainError


@dataclass(frozen=True)
class RemotePullRequest:
    number: int
    url: str


@dataclass(frozen=True)
class RemoteRepository:
    full_name: str
    html_url: str
    created: bool


def slugify_repo_name(name: str) -> str:
    """Turn a project title into a GitHub-safe repository name."""

    text = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    text = text.strip("-")[:80]
    return text or "atelier-project"


def authenticated_login(*, api_url: str, token: str) -> str:
    data = _get_json(api_url, token, "/user")
    login = str(data.get("login") or "").strip()
    if not login:
        raise DomainError("GitHub did not return the authenticated user login.", status_code=502)
    return login


def create_repository(
    *,
    api_url: str,
    token: str,
    name: str,
    description: str = "",
    private: bool = False,
    owner: str | None = None,
) -> RemoteRepository:
    """Create a repository under the token user (or an org when owner is set).

    Returns the owner/name and whether GitHub created it now (False if it
    already existed and was reused).
    """

    if not token.strip():
        raise DomainError("GITHUB_TOKEN is required to create a GitHub repository.", status_code=422)
    repo_name = slugify_repo_name(name)
    login = authenticated_login(api_url=api_url, token=token)
    if owner and owner.strip() and owner.strip().lower() != login.lower():
        path = f"/orgs/{owner.strip()}/repos"
        full_name = f"{owner.strip()}/{repo_name}"
    else:
        path = "/user/repos"
        full_name = f"{login}/{repo_name}"

    existing = _get_repo(api_url=api_url, token=token, repo=full_name)
    if existing is not None:
        return existing

    response = httpx.post(
        f"{api_url.rstrip('/')}{path}",
        headers=_headers(token),
        json={
            "name": repo_name,
            "description": (description or "")[:350],
            "private": private,
            "auto_init": False,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": False,
        },
        timeout=30,
    )
    if response.status_code == 422 and "already exists" in response.text.lower():
        reused = _get_repo(api_url=api_url, token=token, repo=full_name)
        if reused is not None:
            return RemoteRepository(
                full_name=reused.full_name,
                html_url=reused.html_url,
                created=False,
            )
    if response.status_code >= 400:
        detail = response.text.strip() or f"GitHub returned {response.status_code}."
        raise DomainError(f"GitHub could not create the repository: {detail}", status_code=502)
    data = response.json()
    return RemoteRepository(
        full_name=str(data["full_name"]),
        html_url=str(data["html_url"]),
        created=True,
    )


def resolve_or_create_repository(
    *,
    api_url: str,
    token: str,
    project_name: str,
    project_description: str = "",
    github_repo: str | None = None,
    private: bool = False,
) -> RemoteRepository:
    """Pick owner/name from an optional field, otherwise mint one and create it."""

    raw = (github_repo or "").strip()
    if raw:
        if raw.count("/") == 1:
            owner, name = (part.strip() for part in raw.split("/", 1))
            if not owner or not name:
                raise DomainError("github_repo must look like owner/name.", status_code=422)
            existing = _get_repo(api_url=api_url, token=token, repo=f"{owner}/{name}")
            if existing is not None:
                return existing
            login = authenticated_login(api_url=api_url, token=token)
            org_owner = owner if owner.lower() != login.lower() else None
            return create_repository(
                api_url=api_url,
                token=token,
                name=name,
                description=project_description,
                private=private,
                owner=org_owner,
            )
        return create_repository(
            api_url=api_url,
            token=token,
            name=raw,
            description=project_description,
            private=private,
        )
    return create_repository(
        api_url=api_url,
        token=token,
        name=project_name,
        description=project_description,
        private=private,
    )


def open_pull_request(
    *,
    api_url: str,
    token: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> RemotePullRequest:
    if "/" not in repo or repo.count("/") != 1:
        raise DomainError(
            f"'{repo}' is not an owner/name GitHub repository.",
            status_code=422,
        )
    if not token.strip():
        raise DomainError("GITHUB_TOKEN is required to open a remote pull request.", status_code=422)
    response = httpx.post(
        f"{api_url.rstrip('/')}/repos/{repo}/pulls",
        headers=_headers(token),
        json={"title": title, "body": body, "head": head, "base": base},
        timeout=30,
    )
    if response.status_code >= 400:
        detail = response.text.strip() or f"GitHub returned {response.status_code}."
        raise DomainError(f"GitHub could not open the pull request: {detail}", status_code=502)
    data = response.json()
    return RemotePullRequest(number=int(data["number"]), url=str(data["html_url"]))


def _get_repo(*, api_url: str, token: str, repo: str) -> RemoteRepository | None:
    response = httpx.get(
        f"{api_url.rstrip('/')}/repos/{repo}",
        headers=_headers(token),
        timeout=30,
    )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        detail = response.text.strip() or f"GitHub returned {response.status_code}."
        raise DomainError(f"GitHub could not read the repository: {detail}", status_code=502)
    data = response.json()
    return RemoteRepository(
        full_name=str(data["full_name"]),
        html_url=str(data["html_url"]),
        created=False,
    )


def _get_json(api_url: str, token: str, path: str) -> dict:
    if not token.strip():
        raise DomainError("GITHUB_TOKEN is required to call GitHub.", status_code=422)
    response = httpx.get(
        f"{api_url.rstrip('/')}{path}",
        headers=_headers(token),
        timeout=30,
    )
    if response.status_code >= 400:
        detail = response.text.strip() or f"GitHub returned {response.status_code}."
        raise DomainError(f"GitHub request failed: {detail}", status_code=502)
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
