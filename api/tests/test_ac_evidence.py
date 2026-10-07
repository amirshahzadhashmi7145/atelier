from app.domain.ac_evidence import blob_from_test_writes, evidence_gaps


def test_harness_only_is_a_gap_for_201_criteria():
    criteria = [
        ("FR-001/AC-1", "Status code is 201 Created"),
        (
            "FR-001/AC-2",
            "Response body includes id, name, dialect, host, port, database, mode",
        ),
    ]
    gaps = evidence_gaps(
        criteria,
        check_excerpts="unit exited 0\n1 passed",
        write_contents="def test_harness_collects():\n    assert True\n",
    )
    assert "FR-001/AC-1" in gaps
    assert "FR-001/AC-2" in gaps


def test_real_assertions_clear_the_gaps():
    criteria = [
        ("FR-001/AC-1", "Status code is 201 Created"),
        (
            "FR-001/AC-2",
            "Response body includes id, name, dialect, host, port, database, mode",
        ),
    ]
    writes = blob_from_test_writes(
        [
            (
                "tests/unit/test_create.py",
                "assert response.status_code == 201\n"
                "for key in ('id','name','dialect','host','port','database','mode'):\n"
                "    assert key in body\n",
            )
        ]
    )
    gaps = evidence_gaps(
        criteria,
        check_excerpts="PASSED test_create_connection_returns_201",
        write_contents=writes,
    )
    assert gaps == []
