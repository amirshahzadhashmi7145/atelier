"""Open a pull request on GitHub when a project names a repository.

A token is optional. Without one, Atelier still records the PR locally.
With one, the branch is expected to already be on the remote; this module
only creates the pull request document (FR-DEV-7 fields in the body).
"""

from dataclasses import dataclass

import httpx

from app.errors import DomainError


@dataclass(frozen=True)
class RemotePullRequest:
    number: int
    url: str


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
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"title": title, "body": body, "head": head, "base": base},
        timeout=30,
    )
    if response.status_code >= 400:
        detail = response.text.strip() or f"GitHub returned {response.status_code}."
        raise DomainError(f"GitHub could not open the pull request: {detail}", status_code=502)
    data = response.json()
    return RemotePullRequest(number=int(data["number"]), url=str(data["html_url"]))
