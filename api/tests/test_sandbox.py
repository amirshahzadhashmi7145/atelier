import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.checks import SandboxOptions, run_checks
from app.services.sandbox import run_in_sandbox


def test_sandbox_argv_has_no_network_and_a_read_only_mount(tmp_path: Path):
    captured: list[list[str]] = []

    def fake_run(argv, **kwargs):
        captured.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="ok\n", stderr="")

    with patch("app.services.sandbox.subprocess.run", side_effect=fake_run):
        code, excerpt = run_in_sandbox(
            tmp_path,
            ["python3", "-c", "print('ok')"],
            image="python:3.12-slim",
            timeout=5,
            memory="128m",
            cpus="0.5",
            pids_limit=32,
        )

    assert code == 0
    assert "ok" in excerpt
    argv = captured[0]
    assert argv[:3] == ["docker", "run", "--rm"]
    assert "--network=none" in argv
    assert "--read-only" in argv
    assert "--cap-drop=ALL" in argv
    assert "no-new-privileges" in argv
    assert f"type=bind,source={tmp_path.resolve()},target=/workspace,readonly" in argv
    assert "--memory=128m" in argv
    assert "--cpus=0.5" in argv
    assert "--pids-limit=32" in argv
    assert argv[-4:] == ["python:3.12-slim", "python3", "-c", "print('ok')"]


def test_missing_docker_is_reported_as_exit_127(tmp_path: Path):
    with patch("app.services.sandbox.subprocess.run", side_effect=FileNotFoundError):
        code, excerpt = run_in_sandbox(
            tmp_path,
            ["python3", "-c", "print('ok')"],
            image="python:3.12-slim",
            timeout=5,
            memory="128m",
            cpus="0.5",
            pids_limit=32,
        )
    assert code == 127
    assert "Docker" in excerpt


def test_run_checks_uses_the_sandbox_when_configured(tmp_path: Path):
    calls: list[tuple] = []

    def fake_sandbox(root, argv, **kwargs):
        calls.append((root, argv, kwargs))
        return 0, "sandboxed"

    with patch("app.services.checks.run_in_sandbox", side_effect=fake_sandbox):
        results = run_checks(
            tmp_path,
            {
                "unit": "python3 -c \"print('unit')\"",
                "integration": "python3 -c \"print('integration')\"",
                "ui": "python3 -c \"print('ui')\"",
            },
            timeout=5,
            sandbox=SandboxOptions(image="python:3.12-slim"),
        )

    assert len(calls) == 3
    assert all(item.exit_code == 0 for item in results)
    assert all(item.excerpt == "sandboxed" for item in results)
    assert calls[0][1][:1] == ["python3"]


@pytest.mark.skipif(
    subprocess.call(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
    reason="Docker daemon is not available",
)
def test_a_real_container_runs_the_command(tmp_path: Path):
    results = run_checks(
        tmp_path,
        {
            "unit": "python3 -c \"print('unit ok')\"",
            "integration": "python3 -c \"print('integration ok')\"",
            "ui": "python3 -c \"print('ui ok')\"",
        },
        timeout=60,
        sandbox=SandboxOptions(image="python:3.12-slim", memory="128m", cpus="0.5"),
    )
    assert all(item.exit_code == 0 for item in results)
    assert "unit ok" in results[0].excerpt
