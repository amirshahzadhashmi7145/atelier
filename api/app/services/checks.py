"""Run the test commands the architecture declared.

The command is taken from the approved plan and executed in the project
directory. It is one program plus arguments. Shell syntax is rejected
so a plan cannot smuggle a second command into the same string.

When a sandbox is configured, the workspace is copied to a temp directory,
declared npm/pip dependencies are installed with network into the copy
(pip packages land under /.deps so they survive the next container), then
each verify command runs offline against that copy. Host mode (no sandbox)
runs the commands in-place for fast unit tests.
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
_DEPS_DIR = ".deps"
_NODE_PROGRAMS = frozenset(
    {
        "node",
        "nodejs",
        "npm",
        "npx",
        "yarn",
        "pnpm",
        "bun",
        "vitest",
        "jest",
        "mocha",
    }
)
_PYTHON_PROGRAMS = frozenset({"python", "python3", "pytest", "pip", "pip3"})
_JS_TEST_BINARIES = frozenset({"vitest", "jest", "mocha"})


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
        # Sandbox drops CAP_DAC_OVERRIDE — host-private (0700) dirs are invisible inside Docker.
        _relax_tree_permissions(work)
        install_timeout = max(timeout, 120)
        blocked, hard_fail = _prepare_dependencies(work, planned, sandbox, install_timeout)
        if hard_fail is not None:
            # Pip/npm install failure blocks every tier — nothing useful can run.
            return [
                CheckResult(tier, command, hard_fail.exit_code, hard_fail.excerpt)
                for tier, command in planned
            ]
        results: list[CheckResult] = []
        for tier, command in planned:
            if tier in blocked:
                results.append(blocked[tier])
            else:
                results.append(_run_sandbox_command(work, tier, command, timeout, sandbox))
        return results
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _ignore_vcs(directory: str, names: list[str]) -> set[str]:
    ignored = set()
    if ".git" in names:
        ignored.add(".git")
    # Always reinstall inside the sandbox copy — host node_modules may lack +x
    # (NTFS/fuseblk) or be the wrong platform.
    if "node_modules" in names:
        ignored.add("node_modules")
    return ignored


def _prepare_dependencies(
    root: Path,
    planned: list[tuple[str, str]],
    sandbox: SandboxOptions,
    timeout: int,
) -> tuple[dict[str, CheckResult], CheckResult | None]:
    """Install deps. Missing package.json fails only npm/node tiers; pip still runs."""

    commands = [command for _tier, command in planned]
    blocked: dict[str, CheckResult] = {}
    if not _package_json_present(root):
        missing = CheckResult(
            "deps",
            "npm",
            1,
            "Architecture declared npm/node tests but this branch has no package.json "
            "at the repo root (or under a path npm --prefix can reach). Add package.json "
            "with a test script, or change the ui command to match the tree.",
        )
        for tier, command in planned:
            program = Path(parse_command(command)[0]).name.lower()
            if program in _NODE_PROGRAMS:
                blocked[tier] = CheckResult(tier, command, missing.exit_code, missing.excerpt)

    if _package_json_present(root):
        for prefix in _npm_install_prefixes(root):
            argv = ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]
            if prefix:
                argv = [
                    "npm",
                    "--prefix",
                    prefix,
                    "install",
                    "--ignore-scripts",
                    "--no-audit",
                    "--no-fund",
                ]
            code, excerpt = run_in_sandbox(
                root,
                argv,
                image=sandbox.node_image,
                timeout=timeout,
                memory=sandbox.memory,
                cpus=sandbox.cpus,
                pids_limit=sandbox.pids_limit,
                network=True,
                writable=True,
            )
            if code != 0:
                return {}, CheckResult(
                    "deps",
                    " ".join(argv),
                    code,
                    excerpt or "npm install failed.",
                )

    pip_argv = _pip_install_argv(root, commands)
    if pip_argv:
        code, excerpt = run_in_sandbox(
            root,
            pip_argv,
            image=sandbox.image,
            timeout=timeout,
            memory=sandbox.memory,
            cpus=sandbox.cpus,
            pids_limit=sandbox.pids_limit,
            network=True,
            writable=True,
        )
        if code != 0:
            return blocked, CheckResult(
                "deps", " ".join(pip_argv), code, excerpt or "pip install failed."
            )
    return blocked, None


def _commands_need_pytest(commands: list[str]) -> bool:
    for command in commands:
        lowered = command.lower()
        if "pytest" in lowered:
            return True
        parts = parse_command(command)
        if Path(parts[0]).name.lower() == "pytest":
            return True
        if len(parts) >= 3 and Path(parts[0]).name.lower() in {"python", "python3"} and parts[1] == "-m" and parts[2] == "pytest":
            return True
    return False


def _package_json_present(root: Path) -> bool:
    if (root / "package.json").is_file():
        return True
    # Common zone layouts from architecture ownership.
    for relative in ("web/package.json", "frontend/package.json", "client/package.json"):
        if (root / relative).is_file():
            return True
    return False


def _npm_package_dirs(root: Path) -> list[Path]:
    found: list[Path] = []
    for relative in (".", "web", "frontend", "client"):
        package = root / relative / "package.json" if relative != "." else root / "package.json"
        if package.is_file():
            found.append(package.parent)
    return found


def _npm_install_prefixes(root: Path) -> list[str]:
    """Return '' for root, or zone folder names that need npm install."""

    prefixes: list[str] = []
    for directory in _npm_package_dirs(root):
        if (directory / "node_modules").is_dir():
            continue
        try:
            data = json.loads((directory / "package.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        deps = {}
        if isinstance(data.get("dependencies"), dict):
            deps.update(data["dependencies"])
        if isinstance(data.get("devDependencies"), dict):
            deps.update(data["devDependencies"])
        if not deps:
            continue
        if directory == root:
            prefixes.append("")
        else:
            prefixes.append(directory.name)
    return prefixes


def _relax_tree_permissions(root: Path) -> None:
    """Make the check copy traversable/writable without CAP_DAC_OVERRIDE."""

    try:
        root.chmod(0o777)
    except OSError:
        pass
    for path in root.rglob("*"):
        try:
            if path.is_dir():
                path.chmod(0o777)
            else:
                # Keep execute bits for package bins when the filesystem allows them.
                path.chmod(0o777)
        except OSError:
            continue


def _ensure_deps_dir(root: Path) -> Path:
    """Create a world-writable deps dir on the host before the container writes into it."""

    deps = root / _DEPS_DIR
    deps.mkdir(exist_ok=True)
    try:
        deps.chmod(0o777)
    except OSError:
        pass
    return deps


def _pip_install_argv(root: Path, commands: list[str]) -> list[str] | None:
    """Install into /workspace/.deps so packages survive the next container."""

    needs_req = (root / "requirements.txt").is_file() or (root / "pyproject.toml").is_file()
    needs_pytest = _commands_need_pytest(commands)
    if not needs_req and not needs_pytest:
        return None
    _ensure_deps_dir(root)
    target = f"/workspace/{_DEPS_DIR}"
    base = ["pip", "install", "--no-cache-dir", "--target", target]
    if (root / "requirements.txt").is_file():
        argv = [*base, "-r", "requirements.txt"]
        if needs_pytest:
            argv.append("pytest")
        return argv
    if (root / "pyproject.toml").is_file():
        argv = [*base, "."]
        if needs_pytest:
            argv.append("pytest")
        return argv
    # Strategy asked for pytest but the branch never declared deps — still install it.
    return [*base, "pytest"]


def _python_env(root: Path) -> dict[str, str] | None:
    deps = root / _DEPS_DIR
    if not deps.is_dir():
        return None
    return {
        "PYTHONPATH": f"/workspace/{_DEPS_DIR}",
        "PATH": f"/workspace/{_DEPS_DIR}/bin:/usr/local/bin:/usr/bin:/bin",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }


def _normalize_python_argv(argv: list[str]) -> list[str]:
    name = Path(argv[0]).name.lower()
    if name == "pytest":
        return ["python3", "-m", "pytest", *argv[1:]]
    return argv


def _package_prefix(root: Path) -> str | None:
    if (root / "package.json").is_file():
        return ""
    for folder in ("frontend", "web", "client"):
        if (root / folder / "package.json").is_file():
            return folder
    return None


def _normalize_node_argv(root: Path, argv: list[str]) -> list[str]:
    """Turn bare vitest/jest into npm run so cwd is the package root."""

    if not argv:
        return argv
    name = Path(argv[0]).name.lower()
    if name not in _JS_TEST_BINARIES:
        return argv
    prefix = _package_prefix(root)
    script = "test:unit" if name == "vitest" else "test"
    if prefix is None:
        # No package.json yet — still force Node via npx so image routing is correct.
        return ["npx", "--no-install", name, *argv[1:]]
    if prefix == "":
        return ["npm", "run", script]
    return ["npm", "--prefix", prefix, "run", script]


def _normalize_check_argv(root: Path, argv: list[str]) -> list[str]:
    return _normalize_node_argv(root, _normalize_python_argv(argv))


def _run_sandbox_command(
    root: Path,
    tier: str,
    command: str,
    timeout: int,
    sandbox: SandboxOptions,
) -> CheckResult:
    argv = _normalize_check_argv(root, parse_command(command))
    program = Path(argv[0]).name.lower()
    image = image_for_program(
        argv[0],
        default_image=sandbox.image,
        node_image=sandbox.node_image,
        python_image=sandbox.image,
    )
    env = _python_env(root) if program in _PYTHON_PROGRAMS or program == "python3" else None
    # npm --prefix web when package.json lives under web/ but command is bare npm.
    if program in _NODE_PROGRAMS and not (root / "package.json").is_file():
        for folder in ("web", "frontend", "client"):
            if (root / folder / "package.json").is_file():
                if program == "npm" and "--prefix" not in argv:
                    argv = [argv[0], "--prefix", folder, *argv[1:]]
                break
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
        env=env,
    )
    return CheckResult(tier, command, exit_code, excerpt)


def _run_host(root: Path, tier: str, command: str, timeout: int) -> CheckResult:
    argv = _normalize_check_argv(root, parse_command(command))
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
