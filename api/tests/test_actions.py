from app.domain.actions import action_kind


def test_events_are_grouped_for_the_action_log():
    assert action_kind("gate.decided") == "decision"
    assert action_kind("agent.implement") == "tool"
    assert action_kind("agent.qa") == "tool"
    assert action_kind("pr.opened") == "artefact"
    assert action_kind("run.phase") == "artefact"
    assert action_kind("qa.passed") == "outcome"
    assert action_kind("task.failed") == "outcome"
