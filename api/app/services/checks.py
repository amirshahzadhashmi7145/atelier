"""Run the test commands the architecture declared.

The command is taken from the approved plan and executed in the project
directory. It is one program plus arguments. Shell syntax is rejected
so a plan cannot smuggle a second command into the same string.

When a sandbox is configured, the workspace is copied to a temp directory,
declared npm/pip dependencies are installed with network, then each verify
command runs offline against that copy. Host mode (no sandbox) runs the
commands in-place for fast unit tests.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.errors import DomainError
from app.services.sandbox import image_for_program, run_in_sandbox

TIERS = ("unit", "integration", "ui")
_OPERATORS = {";", "&&", "||", "|", "&", ">", ">>", "<", "<<"}


@dataclass(frozen=True)
class CheckResult:
    tier: str
    command: str
    exit_code: int
    excerpt: str


@dataclass(frozen=True)
class SandboxOptions:
    image: str
    node_image: str = "node:20-slim"
    memory: str = "256m"
    cpus: str = "1"
    pids_limit: int = 64


def parse_command(command: str) -> list[str]:
    if "\n" in command or "`" in command or "$" in command:
        raise DomainError(
            f"'{command}' is not a single program. Test commands cannot chain other programs.",
            status_code=422,
        )
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise DomainError(
            f"'{command}' could not be read as a program and its arguments.",
            status_code=422,
        ) from exc
    if not parts or any(part in _OPERATORS for part in parts):
        raise DomainError(
            f"'{command}' is not a single program. Test commands cannot chain other programs.",
            status_code=422,
        )
    return parts


def run_checks(
    root: Path,
    strategy: dict | None,
    timeout: int,
    *,
    sandbox: SandboxOptions | None = None,
) -> list[CheckResult]:
    if not strategy:
        raise DomainError("This project has no test commands.", status_code=422)
    planned: list[tuple[str, str]] = []
    for tier in TIERS:
        command = str(strategy.get(tier, "")).strip()
        if not command:
            raise DomainError(f"The {tier} test command is missing.", status_code=422)
        parse_command(command)
        planned.append((tier, command))
    if sandbox is None:
        return [_run_host(root, tier, command, timeout) for tier, command in planned]
    return _run_sandboxed(root, planned, timeout, sandbox)


def _run_sandboxed(
    root: Path,
    planned: list[tuple[str, str]],
    timeout: int,
    sandbox: SandboxOptions,
) -> list[CheckResult]:
    work = Path(tempfile.mkdtemp(prefix="atelier-checks-"))
    try:
        shutil.copytree(root, work, dirs_exist_ok=True, ignore=_ignore_vcs)
        install_timeout = max(timeout, 120)
        prep = _prepare_dependencies(work, sandbox, install_timeout)
        if prep is not None and prep.exit_code != 0:
            # Surface install failure on every tier so review has a clear signal.
            return [
                CheckResult(tier, command, prep.exit_code, prep.excerpt)
                for tier, command in planned
            ]
        return [
            _run_sandbox_command(work, tier, command, timeout, sandbox)
            for tier, command in planned
        ]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _ignore_vcs(directory: str, names: list[str]) -> set[str]:
    ignored = set()
    if ".git" in names:
        ignored.add(".git")
    return ignored


def _prepare_dependencies(
    root: Path,
    sandbox: SandboxOptions,
    timeout: int,
) -> CheckResult | None:
    if _needs_npm_install(root):
        code, excerpt = run_in_sandbox(
            root,
            ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"],
            image=sandbox.node_image,
            timeout=timeout,
            memory=sandbox.memory,
            cpus=sandbox.cpus,
            pids_limit=sandbox.pids_limit,
            network=True,
            writable=True,
        )
        if code != 0:
            return CheckResult("deps", "npm install --ignore-scripts", code, excerpt or "npm install failed.")
    if _needs_pip_install(root):
        argv = _pip_install_argv(root)
        if argv:
            code, excerpt = run_in_sandbox(
                root,
                argv,
                image=sandbox.image,
                timeout=timeout,
                memory=sandbox.memory,
                cpus=sandbox.cpus,
                pids_limit=sandbox.pids_limit,
                network=True,
                writable=True,
            )
            if code != 0:
                return CheckResult("deps", " ".join(argv), code, excerpt or "pip install failed.")
    return None


def _needs_npm_install(root: Path) -> bool:
    package = root / "package.json"
    if not package.is_file():
        return False
    if (root / "node_modules").is_dir():
        return False
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    deps = {}
    if isinstance(data.get("dependencies"), dict):
        deps.update(data["dependencies"])
    if isinstance(data.get("devDependencies"), dict):
        deps.update(data["devDependencies"])
    return bool(deps)


def _needs_pip_install(root: Path) -> bool:
    if (root / "requirements.txt").is_file():
        return True
    return (root / "pyproject.toml").is_file()


def _pip_install_argv(root: Path) -> list[str] | None:
    if (root / "requirements.txt").is_file():
        return ["pip", "install", "--no-cache-dir", "-r", "requirements.txt"]
    if (root / "pyproject.toml").is_file():
        return ["pip", "install", "--no-cache-dir", "."]
    return None


def _run_sandbox_command(
    root: Path,
    tier: str,
    command: str,
    timeout: int,
    sandbox: SandboxOptions,
) -> CheckResult:
    argv = parse_command(command)
    image = image_for_program(
        argv[0],
        default_image=sandbox.image,
        node_image=sandbox.node_image,
        python_image=sandbox.image,
    )
    exit_code, excerpt = run_in_sandbox(
        root,
        argv,
        image=image,
        timeout=timeout,
        memory=sandbox.memory,
        cpus=sandbox.cpus,
        pids_limit=sandbox.pids_limit,
        network=False,
        writable=True,
    )
    return CheckResult(tier, command, exit_code, excerpt)


def _run_host(root: Path, tier: str, command: str, timeout: int) -> CheckResult:
    argv = parse_command(command)
    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CheckResult(tier, command, 124, _excerpt(exc.stdout, exc.stderr) or "The command timed out.")
    except FileNotFoundError:
        return CheckResult(tier, command, 127, f"Could not run {argv[0]}.")
    return CheckResult(tier, command, completed.returncode, _excerpt(completed.stdout, completed.stderr))


def _excerpt(stdout, stderr) -> str:
    text = "\n".join(part for part in (_as_text(stdout), _as_text(stderr)) if part).strip()
    if len(text) <= 800:
        return text
    return text[-800:]


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
