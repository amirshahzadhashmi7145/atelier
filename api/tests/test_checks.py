from pathlib import Path

import pytest

from app.errors import DomainError
from app.services.checks import parse_command, run_checks


def test_a_command_is_one_program_and_its_arguments():
    assert parse_command("python3 -m unittest tests.test_smoke") == [
        "python3",
        "-m",
        "unittest",
        "tests.test_smoke",
    ]


def test_a_chained_command_is_rejected():
    with pytest.raises(DomainError) as caught:
        parse_command("pytest && rm -rf .")
    assert caught.value.status_code == 422


def test_a_failing_command_is_reported_with_its_output(tmp_path: Path):
    results = run_checks(
        tmp_path,
        {
            "unit": 'python3 -c "import sys; print(\'nope\'); sys.exit(2)"',
            "integration": "python3 -c \"print('integration ok')\"",
            "ui": "python3 -c \"print('ui ok')\"",
        },
        timeout=5,
    )
    by_tier = {item.tier: item for item in results}
    assert by_tier["unit"].exit_code == 2
    assert "nope" in by_tier["unit"].excerpt
    assert by_tier["integration"].exit_code == 0
    assert by_tier["ui"].exit_code == 0


def test_a_command_that_runs_too_long_is_stopped(tmp_path: Path):
    results = run_checks(
        tmp_path,
        {
            "unit": 'python3 -c "import time; time.sleep(30)"',
            "integration": "python3 -c \"print('integration ok')\"",
            "ui": "python3 -c \"print('ui ok')\"",
        },
        timeout=1,
    )
    assert results[0].exit_code == 124
    assert "timed out" in results[0].excerpt
