from app.domain.dependencies import dependency_files, forbidden_dependency_sources
from app.domain.pull_request import CheckLine, compose
from app.services.github import (
    create_repository,
    open_pull_request,
    resolve_or_create_repository,
    slugify_repo_name,
)
from unittest.mock import patch

import httpx

from app.errors import DomainError


def test_a_pull_request_names_the_task_requirements_summary_and_checks():
    draft = compose(
        task_key="TASK-001",
        title="Persist records",
        summary="Add the create endpoint.",
        requirement_keys=["FR-001", "FR-002"],
        checks=[
            CheckLine("unit", "python3 -c \"print('unit ok')\"", 0, "unit ok"),
            CheckLine("integration", "python3 -c \"print('integration ok')\"", 0),
        ],
        assumptions=["Members sign in with email."],
        dependencies=["server/requirements.txt"],
    )
    assert draft.title == "TASK-001: Persist records"
    assert "TASK-001" in draft.body
    assert "FR-001, FR-002" in draft.body
    assert "Add the create endpoint." in draft.body
    assert "unit" in draft.body and "exited 0" in draft.body
    assert "Members sign in with email." in draft.body
    assert "## Dependencies" in draft.body
    assert "server/requirements.txt" in draft.body


def test_dependency_files_are_listed_from_the_diff():
    diff = """\
diff --git a/server/requirements.txt b/server/requirements.txt
--- a/server/requirements.txt
+++ b/server/requirements.txt
@@ -0,0 +1 @@
+fastapi
diff --git a/server/app.py b/server/app.py
--- /dev/null
+++ b/server/app.py
@@ -0,0 +1 @@
+print(1)
"""
    assert dependency_files(diff) == ["server/requirements.txt"]


def test_dependency_urls_outside_the_allowlist_are_rejected():
    allowed = {"pypi.org", "files.pythonhosted.org"}
    assert (
        forbidden_dependency_sources(
            writes=[("server/requirements.txt", "fastapi\n")],
            allowed_hosts=allowed,
        )
        == []
    )
    blocked = forbidden_dependency_sources(
        writes=[
            (
                "server/requirements.txt",
                "evil @ https://evil.example/pkg.whl\n",
            )
        ],
        allowed_hosts=allowed,
    )
    assert blocked and "evil.example" in blocked[0]


def test_github_open_pull_request_posts_the_draft():
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return httpx.Response(
            201,
            json={"number": 12, "html_url": "https://github.com/acme/app/pull/12"},
            request=httpx.Request("POST", url),
        )

    with patch("app.services.github.httpx.post", side_effect=fake_post):
        remote = open_pull_request(
            api_url="https://api.github.com",
            token="gho_test",
            repo="acme/app",
            title="TASK-001: Persist",
            body="body",
            head="task/TASK-001",
        )
    assert remote.number == 12
    assert remote.url.endswith("/pull/12")
    assert captured["url"].endswith("/repos/acme/app/pulls")
    assert captured["json"]["head"] == "task/TASK-001"
    assert captured["json"]["base"] == "main"


def test_a_bad_repo_name_is_rejected():
    try:
        open_pull_request(
            api_url="https://api.github.com",
            token="gho_test",
            repo="not-a-repo",
            title="t",
            body="b",
            head="task/TASK-001",
        )
    except DomainError as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("expected a rejection")


def test_slugify_repo_name_is_github_safe():
    assert slugify_repo_name("Dynamic Tic Tac Toe!") == "dynamic-tic-tac-toe"
    assert slugify_repo_name("@@@") == "atelier-project"


def test_create_repository_posts_under_the_user():
    calls: list[tuple[str, str]] = []

    def fake_get(url, **kwargs):
        calls.append(("GET", url))
        if url.endswith("/user"):
            return httpx.Response(
                200,
                json={"login": "amir"},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(404, request=httpx.Request("GET", url))

    def fake_post(url, **kwargs):
        calls.append(("POST", url))
        assert kwargs["json"]["name"] == "dynamic-tic-tac-toe"
        assert kwargs["json"]["auto_init"] is False
        return httpx.Response(
            201,
            json={
                "full_name": "amir/dynamic-tic-tac-toe",
                "html_url": "https://github.com/amir/dynamic-tic-tac-toe",
            },
            request=httpx.Request("POST", url),
        )

    with (
        patch("app.services.github.httpx.get", side_effect=fake_get),
        patch("app.services.github.httpx.post", side_effect=fake_post),
    ):
        remote = create_repository(
            api_url="https://api.github.com",
            token="gho_test",
            name="Dynamic Tic Tac Toe",
            description="make a game",
        )
    assert remote.full_name == "amir/dynamic-tic-tac-toe"
    assert remote.created is True
    assert any(method == "POST" and url.endswith("/user/repos") for method, url in calls)


def test_resolve_or_create_mints_from_project_name_when_blank():
    with (
        patch(
            "app.services.github.authenticated_login",
            return_value="amir",
        ),
        patch(
            "app.services.github._get_repo",
            return_value=None,
        ),
        patch(
            "app.services.github.httpx.post",
            return_value=httpx.Response(
                201,
                json={
                    "full_name": "amir/notes-app",
                    "html_url": "https://github.com/amir/notes-app",
                },
                request=httpx.Request("POST", "https://api.github.com/user/repos"),
            ),
        ),
    ):
        remote = resolve_or_create_repository(
            api_url="https://api.github.com",
            token="gho_test",
            project_name="Notes App",
        )
    assert remote.full_name == "amir/notes-app"
