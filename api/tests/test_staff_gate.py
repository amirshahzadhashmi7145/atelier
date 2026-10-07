from pathlib import Path

from app.domain.qa import Finding
from app.domain.staff_gate import force_evidenced_passes, staff_gate_issues


def test_staff_gate_flags_missing_ac_evidence(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_harness.py").write_text(
        "def test_harness_collects():\n    assert True\n", encoding="utf-8"
    )
    issues = staff_gate_issues(
        root=tmp_path,
        main_files={},
        criteria=[("FR-001/AC-1", "Status code is 201 Created")],
        check_excerpts="1 passed",
    )
    assert any(code == "ac_evidence" for code, _detail in issues)


def test_staff_gate_flags_clobber_vs_main(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.py").write_text(
        "def create_connection():\n    pass\n", encoding="utf-8"
    )
    issues = staff_gate_issues(
        root=tmp_path,
        main_files={
            "backend/main.py": (
                "def reset_store():\n    pass\ndef create_connection():\n    pass\n"
            )
        },
        criteria=[],
        check_excerpts="ok",
    )
    assert any(code == "api_clobber" and "reset_store" in detail for code, detail in issues)


def test_force_evidenced_passes_upgrades_untestable(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_api.py").write_text(
        "assert response.status_code == 201\n", encoding="utf-8"
    )
    findings = [
        Finding(
            criterion_key="FR-001/AC-1",
            result="untestable",
            note="nope",
            reproduction="",
            observed="",
            expected="",
        )
    ]
    findings = force_evidenced_passes(
        [("FR-001/AC-1", "Status code is 201 Created")],
        findings,
        check_excerpts="PASSED 201",
        root=tmp_path,
    )
    assert findings[0].result == "pass"


def test_force_evidenced_passes_leaves_needleless_untestable(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_api.py").write_text("assert True\n", encoding="utf-8")
    findings = [
        Finding(
            criterion_key="FR-001/AC-3",
            result="untestable",
            note="No clock is available in this run.",
            reproduction="",
            observed="",
            expected="",
        )
    ]
    findings = force_evidenced_passes(
        [("FR-001/AC-3", "Wall-clock behaviour matches the product brief on a live clock.")],
        findings,
        check_excerpts="PASSED",
        root=tmp_path,
    )
    assert findings[0].result == "untestable"
