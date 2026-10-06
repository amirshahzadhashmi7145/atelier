from app.domain.pull_request import CheckLine, compose
from app.services.github import open_pull_request
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
    )
    assert draft.title == "TASK-001: Persist records"
    assert "TASK-001" in draft.body
    assert "FR-001, FR-002" in draft.body
    assert "Add the create endpoint." in draft.body
    assert "unit" in draft.body and "exited 0" in draft.body
    assert "Members sign in with email." in draft.body


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
