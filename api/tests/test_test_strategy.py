import pytest

from app.domain.test_strategy import (
    is_trivial_test_command,
    normalize_test_strategy,
    validate_test_strategy,
)
from app.errors import DomainError


def test_print_ok_smokes_are_trivial():
    assert is_trivial_test_command('python3 -c "print(\'unit ok\')"')
    assert is_trivial_test_command("node -e \"console.log('unit ok')\"")
    assert is_trivial_test_command("true")


def test_asserting_commands_are_not_trivial():
    assert not is_trivial_test_command(
        'python3 -c "from pathlib import Path; assert Path(\'server\').is_dir()"'
    )
    assert not is_trivial_test_command("node scripts/verify.js")
    assert not is_trivial_test_command("npm test")
    assert not is_trivial_test_command('python3 -c "import sys; sys.exit(2)"')


def test_validate_test_strategy_rejects_placeholder_smokes():
    with pytest.raises(DomainError, match="placeholder"):
        validate_test_strategy(
            {
                "unit": 'python3 -c "print(\'unit ok\')"',
                "integration": 'python3 -c "print(\'integration ok\')"',
                "ui": 'python3 -c "print(\'ui ok\')"',
            }
        )


def test_validate_test_strategy_accepts_real_commands():
    validate_test_strategy(
        {
            "unit": 'python3 -c "from pathlib import Path; assert Path(\'server\').is_dir()"',
            "integration": "node scripts/verify.js",
            "ui": "npm test",
        }
    )


def test_normalize_rewrites_bare_vitest_to_npm_exec():
    out = normalize_test_strategy(
        {
            "unit": "vitest --run",
            "integration": "vitest --run",
            "ui": "npm --prefix frontend test",
        }
    )
    assert out["unit"] == "npm --prefix frontend run test:unit"
    assert out["integration"] == "npm --prefix frontend run test:unit"
    assert out["ui"] == "npm --prefix frontend test"
