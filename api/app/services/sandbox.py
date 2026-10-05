"""Run one program inside a short-lived container.

The project directory is mounted read-only. The container has no network,
no extra capabilities, and hard limits on memory, CPU and processes.
The container is removed when the command finishes.
"""

import subprocess
from pathlib import Path


def run_in_sandbox(
    root: Path,
    argv: list[str],
    *,
    image: str,
    timeout: int,
    memory: str,
    cpus: str,
    pids_limit: int,
) -> tuple[int, str]:
    """Return (exit_code, excerpt) for argv run under Docker."""

    if not argv:
        return 127, "No program was given to the sandbox."
    docker_argv = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        f"--memory={memory}",
        f"--cpus={cpus}",
        f"--pids-limit={pids_limit}",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--cap-drop=ALL",
        "--security-opt",
        "no-new-privileges",
        "--mount",
        f"type=bind,source={root.resolve()},target=/workspace,readonly",
        "--workdir",
        "/workspace",
        image,
        *argv,
    ]
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
