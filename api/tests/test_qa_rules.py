from app.domain.qa import Finding, decide_untestable, judge, needs_human
from app.errors import DomainError


def _finding(key: str, result: str, **extra) -> Finding:
    fields = {"note": "noted", **extra}
    return Finding(criterion_key=key, result=result, **fields)


def test_every_criterion_must_pass():
    verdict = judge(
        ["FR-001/AC-1", "FR-001/AC-2"],
        [_finding("FR-001/AC-1", "pass"), _finding("FR-001/AC-2", "pass")],
    )
    assert verdict == "pass"


def test_one_failure_is_enough_to_send_the_task_back():
    verdict = judge(
        ["FR-001/AC-1", "FR-001/AC-2"],
        [
            _finding("FR-001/AC-1", "pass"),
            _finding(
                "FR-001/AC-2",
                "fail",
                reproduction="POST /records with no session",
                observed="201",
                expected="401",
            ),
        ],
    )
    assert verdict == "fail"


def test_an_untestable_criterion_does_not_count_as_a_pass():
    verdict = judge(
        ["FR-004/AC-1"],
        [_finding("FR-004/AC-1", "untestable", note="No clock is available in this run.")],
    )
    assert verdict == "untestable"


def test_a_missing_criterion_is_rejected():
    try:
        judge(["FR-001/AC-1", "FR-001/AC-2"], [_finding("FR-001/AC-1", "pass")])
    except DomainError as exc:
        assert exc.status_code == 502
        assert "FR-001/AC-2" in exc.message
    else:
        raise AssertionError("expected a rejection")


def test_a_failure_without_a_reproduction_is_rejected():
    try:
        judge(["FR-001/AC-1"], [_finding("FR-001/AC-1", "fail")])
    except DomainError as exc:
        assert "reproduction" in exc.message
    else:
        raise AssertionError("expected a rejection")


def test_untestable_findings_need_a_person():
    findings = [
        _finding("FR-001/AC-1", "pass"),
        _finding("FR-001/AC-2", "untestable", note="No clock in this run."),
    ]
    assert needs_human(findings)
    assert decide_untestable(findings, "waive") == "waive"
    assert decide_untestable(findings, "reject") == "reject"


def test_a_clean_pass_does_not_ask_a_person():
    assert not needs_human([_finding("FR-001/AC-1", "pass")])
    try:
        decide_untestable([_finding("FR-001/AC-1", "pass")], "waive")
    except DomainError as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("expected a rejection")


def test_a_failure_does_not_ask_a_person():
    findings = [
        _finding(
            "FR-001/AC-1",
            "fail",
            reproduction="open /",
            observed="500",
            expected="200",
        )
    ]
    assert not needs_human(findings)
