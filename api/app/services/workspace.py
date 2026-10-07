"""A local git checkout for one project.

Agents propose file contents; this module is the only writer. Declared
tests run against the working tree before a commit is created. A later
step can move that tree into an isolated sandbox; the branch and the
merge stay the same either way.
"""

import subprocess
from pathlib import Path


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if (self.root / ".git").exists():
            return
        self._git("init", "-b", "main")
        (self.root / "server").mkdir()
        (self.root / "web").mkdir()
        (self.root / "server" / ".gitkeep").write_text("")
        (self.root / "web" / ".gitkeep").write_text("")
        self._git("add", "server", "web")
        self._git("commit", "-m", "Start the integration branch.")

    def start_branch(self, branch: str) -> None:
        """Check out the task branch on top of the current main tip.

        Empty branches (no commits of their own) are reset to main so a
        scaffold or dependency commit on main is visible after a failed run.
        Branches that already carry commits are rebased onto main.
        """

        self._git("checkout", "main")
        if branch in {"main", "master"}:
            return
        listed = self._git("branch", "--list", branch).strip()
        if not listed:
            self._git("checkout", "-b", branch)
            return
        ahead = self._git("rev-list", "--count", f"main..{branch}").strip()
        if ahead == "0":
            self._git("branch", "-f", branch, "main")
            self._git("checkout", branch)
            return
        self._git("checkout", branch)
        self.rebase_onto_main(branch)

    def apply(self, writes: list[tuple[str, str]]) -> None:
        """Write files and stage them. Does not create a commit."""

        for relative, content in writes:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            self._git("add", "--", relative)

    def commit_staged(
        self,
        key: str,
        summary: str,
        *,
        role: str | None = None,
        run_id: str | None = None,
    ) -> None:
        message = f"{key}: {summary}".replace("\n", " ")
        trailers: list[str] = []
        if role:
            trailers.append(f"Atelier-Agent: {role}")
        if run_id:
            trailers.append(f"Atelier-Run: {run_id}")
        if trailers:
            message = f"{message}\n\n" + "\n".join(trailers)
        self._git("commit", "-m", message)

    def commit(
        self,
        key: str,
        summary: str,
        writes: list[tuple[str, str]],
        *,
        role: str | None = None,
        run_id: str | None = None,
    ) -> None:
        self.apply(writes)
        self.commit_staged(key, summary, role=role, run_id=run_id)

    def discard(self) -> None:
        """Drop uncommitted changes so a failed check leaves no residue."""

        self._git("reset", "--hard", "HEAD")
        self._git("clean", "-fd")

    def diff(self, branch: str) -> str:
        return self._git("diff", f"main...{branch}")

    def rebase_onto_main(self, branch: str) -> None:
        """Replay the task branch on the current integration head.

        On conflict the rebase is aborted and the branch is left as it was.
        """

        self._git("checkout", branch)
        result = subprocess.run(
            ["git", "rebase", "main"],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        detail = (result.stderr or result.stdout).strip()
        abort = subprocess.run(
            ["git", "rebase", "--abort"],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )
        if abort.returncode != 0 and "no rebase in progress" not in (abort.stderr or "").lower():
            raise RuntimeError(
                (abort.stderr or abort.stdout).strip()
                or "The conflicted rebase could not be aborted."
            )
        raise RuntimeError(detail or f"git rebase main onto {branch} failed")

    def merge(self, branch: str, key: str) -> None:
        self._git("checkout", "main")
        self._git("merge", "--no-ff", branch, "-m", f"Accept {key}.")

    def push(self, remote_url: str, branch: str) -> None:
        """Publish the task branch. Replaces a prior origin if present."""

        remotes = self._git("remote").split()
        if "origin" in remotes:
            self._git("remote", "set-url", "origin", remote_url)
        else:
            self._git("remote", "add", "origin", remote_url)
        self._git("push", "-u", "origin", branch)

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise RuntimeError(detail or f"git {' '.join(args)} failed")
        return result.stdout
