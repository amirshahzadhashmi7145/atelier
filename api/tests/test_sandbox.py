import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.checks import SandboxOptions, run_checks
from app.services.sandbox import image_for_program, run_in_sandbox


def test_image_for_program_picks_node_for_npm():
    assert (
        image_for_program(
            "npm",
            default_image="python:3.12-slim",
            node_image="node:20-slim",
        )
        == "node:20-slim"
    )
    assert (
        image_for_program(
            "vitest",
            default_image="python:3.12-slim",
            node_image="node:20-slim",
        )
        == "node:20-slim"
    )
    assert (
        image_for_program(
            "python3",
            default_image="python:3.12-slim",
            node_image="node:20-slim",
        )
        == "python:3.12-slim"
    )


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
    assert all(kwargs.get("writable") for _root, _argv, kwargs in calls)


def test_run_checks_uses_the_node_image_for_npm(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name":"demo","scripts":{"test:unit":"node -e 0"}}', encoding="utf-8")
    images: list[str] = []

    def fake_sandbox(root, argv, **kwargs):
        images.append(kwargs["image"])
        return 0, "ok"

    with patch("app.services.checks.run_in_sandbox", side_effect=fake_sandbox):
        results = run_checks(
            tmp_path,
            {
                "unit": "npm run test:unit",
                "integration": "npm run test:integration",
                "ui": "npm run test:ui",
            },
            timeout=5,
            sandbox=SandboxOptions(image="python:3.12-slim", node_image="node:20-slim"),
        )

    assert all(item.exit_code == 0 for item in results)
    assert images == ["node:20-slim", "node:20-slim", "node:20-slim"]


def test_run_checks_rewrites_bare_vitest_to_npm_exec(tmp_path: Path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        '{"name":"demo","devDependencies":{"vitest":"^3.0.0"}}',
        encoding="utf-8",
    )
    calls: list[tuple[list[str], str]] = []

    def fake_sandbox(root, argv, **kwargs):
        calls.append((list(argv), kwargs["image"]))
        if argv[:1] == ["npm"] and "install" in argv:
            (frontend / "node_modules").mkdir(exist_ok=True)
        return 0, "ok"

    with patch("app.services.checks.run_in_sandbox", side_effect=fake_sandbox):
        results = run_checks(
            tmp_path,
            {
                "unit": "vitest --run",
                "integration": "vitest --run",
                "ui": "npm --prefix frontend test",
            },
            timeout=5,
            sandbox=SandboxOptions(image="python:3.12-slim", node_image="node:20-slim"),
        )

    assert all(item.exit_code == 0 for item in results)
    verify = [argv for argv, _image in calls if "install" not in argv]
    assert verify[0][:5] == ["npm", "--prefix", "frontend", "run", "test:unit"]
    assert all(image == "node:20-slim" for _argv, image in calls)


def test_run_checks_installs_npm_deps_before_verify(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"name":"demo","dependencies":{"left-pad":"1.3.0"}}',
        encoding="utf-8",
    )
    calls: list[tuple[list[str], dict]] = []

    def fake_sandbox(root, argv, **kwargs):
        calls.append((list(argv), dict(kwargs)))
        if argv[:1] == ["npm"] and "install" in argv:
            (root / "node_modules").mkdir(exist_ok=True)
        return 0, "ok"

    with patch("app.services.checks.run_in_sandbox", side_effect=fake_sandbox):
        results = run_checks(
            tmp_path,
            {
                "unit": "node scripts/verify.js",
                "integration": "node scripts/verify.js",
                "ui": "node scripts/verify.js",
            },
            timeout=5,
            sandbox=SandboxOptions(image="python:3.12-slim", node_image="node:20-slim"),
        )

    assert all(item.exit_code == 0 for item in results)
    assert calls[0][0][:2] == ["npm", "install"]
    assert calls[0][1].get("network") is True
    assert calls[0][1].get("writable") is True
    assert calls[0][1]["image"] == "node:20-slim"
    assert len(calls) == 4
    assert all(call[1].get("network") is False for call in calls[1:])


def test_run_checks_installs_pytest_into_workspace_deps(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask==3.0.0\n", encoding="utf-8")
    calls: list[tuple[list[str], dict]] = []

    def fake_sandbox(root, argv, **kwargs):
        calls.append((list(argv), dict(kwargs)))
        if argv[:2] == ["pip", "install"]:
            (root / ".deps").mkdir(exist_ok=True)
        return 0, "ok"

    with patch("app.services.checks.run_in_sandbox", side_effect=fake_sandbox):
        results = run_checks(
            tmp_path,
            {
                "unit": "python3 -m pytest tests/unit",
                "integration": "python3 -m pytest tests/integration",
                "ui": "python3 -c \"print('ui')\"",
            },
            timeout=5,
            sandbox=SandboxOptions(image="python:3.12-slim"),
        )

    assert all(item.exit_code == 0 for item in results)
    assert calls[0][0][:4] == ["pip", "install", "--no-cache-dir", "--target"]
    assert "/workspace/.deps" in calls[0][0]
    assert "-r" in calls[0][0]
    assert "pytest" in calls[0][0]
    assert calls[0][1].get("network") is True
    # Verify runs see PYTHONPATH into the persisted deps tree.
    assert calls[1][1].get("env", {}).get("PYTHONPATH") == "/workspace/.deps"


def test_run_checks_fails_only_npm_tiers_when_package_json_missing(tmp_path: Path):
    calls: list[list[str]] = []

    def fake_sandbox(root, argv, **kwargs):
        calls.append(list(argv))
        return 0, "ok"

    with patch("app.services.checks.run_in_sandbox", side_effect=fake_sandbox):
        results = run_checks(
            tmp_path,
            {
                "unit": "python3 -c \"print('unit')\"",
                "integration": "python3 -c \"print('integration')\"",
                "ui": "npm test -- --watchAll=false",
            },
            timeout=5,
            sandbox=SandboxOptions(image="python:3.12-slim", node_image="node:20-slim"),
        )

    by_tier = {item.tier: item for item in results}
    assert by_tier["unit"].exit_code == 0
    assert by_tier["integration"].exit_code == 0
    assert by_tier["ui"].exit_code == 1
    assert "package.json" in by_tier["ui"].excerpt
    # Python tiers still run (and may pip-install); npm install is skipped.
    assert any(argv and argv[0] == "python3" for argv in calls)


def test_sandbox_install_mode_allows_network_and_writable_mount(tmp_path: Path):
    captured: list[list[str]] = []

    def fake_run(argv, **kwargs):
        captured.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="ok\n", stderr="")

    with patch("app.services.sandbox.subprocess.run", side_effect=fake_run):
        code, _excerpt = run_in_sandbox(
            tmp_path,
            ["npm", "install", "--ignore-scripts"],
            image="node:20-slim",
            timeout=5,
            memory="128m",
            cpus="0.5",
            pids_limit=32,
            network=True,
            writable=True,
        )

    assert code == 0
    argv = captured[0]
    assert "--network=bridge" in argv
    assert "--network=none" not in argv
    assert "--read-only" not in argv
    mounts = [item for item in argv if item.startswith("type=bind,")]
    assert mounts == [f"type=bind,source={tmp_path.resolve()},target=/workspace"]


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
