"""Run one program inside a short-lived container.

By default the project directory is mounted read-only with no network.
Install steps may opt into a writable mount and network so declared
dependencies can be fetched before offline verify commands run.
"""

import subprocess
from pathlib import Path

_NODE_PROGRAMS = frozenset({"node", "nodejs", "npm", "npx", "yarn", "pnpm", "bun"})
_PYTHON_PROGRAMS = frozenset({"python", "python3", "pytest", "pip", "pip3"})


def image_for_program(
    program: str,
    *,
    default_image: str,
    node_image: str,
    python_image: str | None = None,
) -> str:
    """Pick a container image that actually contains the program."""

    name = Path(program).name.lower()
    if name in _NODE_PROGRAMS:
        return node_image
    if name in _PYTHON_PROGRAMS:
        return python_image or default_image
    return default_image


def run_in_sandbox(
    root: Path,
    argv: list[str],
    *,
    image: str,
    timeout: int,
    memory: str,
    cpus: str,
    pids_limit: int,
    network: bool = False,
    writable: bool = False,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Return (exit_code, excerpt) for argv run under Docker."""

    if not argv:
        return 127, "No program was given to the sandbox."
    mount = f"type=bind,source={root.resolve()},target=/workspace"
    if not writable:
        mount += ",readonly"
    docker_argv = [
        "docker",
        "run",
        "--rm",
    ]
    if network:
        docker_argv.append("--network=bridge")
    else:
        docker_argv.append("--network=none")
    docker_argv.extend(
        [
            f"--memory={memory}",
            f"--cpus={cpus}",
            f"--pids-limit={pids_limit}",
        ]
    )
    if not writable:
        docker_argv.append("--read-only")
        docker_argv.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])
    else:
        docker_argv.extend(["--tmpfs", "/tmp:rw,exec,nosuid,size=256m"])
    for key, value in (env or {}).items():
        docker_argv.extend(["-e", f"{key}={value}"])
    docker_argv.extend(
        [
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges",
            "--mount",
            mount,
            "--workdir",
            "/workspace",
            image,
            *argv,
        ]
    )
    try:
        completed = subprocess.run(
            docker_argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return 127, "Docker is not available on this host."
    except subprocess.TimeoutExpired as exc:
        return 124, _excerpt(exc.stdout, exc.stderr) or "The command timed out."
    return completed.returncode, _excerpt(completed.stdout, completed.stderr)


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
