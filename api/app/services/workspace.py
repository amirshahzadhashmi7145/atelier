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
        self._git("checkout", "main")
        listed = self._git("branch", "--list", branch).strip()
        if listed:
            self._git("checkout", branch)
        else:
            self._git("checkout", "-b", branch)

    def apply(self, writes: list[tuple[str, str]]) -> None:
        """Write files and stage them. Does not create a commit."""

        for relative, content in writes:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            self._git("add", "--", relative)

    def commit_staged(self, key: str, summary: str) -> None:
        message = f"{key}: {summary}".replace("\n", " ")
        self._git("commit", "-m", message)

    def commit(self, key: str, summary: str, writes: list[tuple[str, str]]) -> None:
        self.apply(writes)
        self.commit_staged(key, summary)

    def discard(self) -> None:
        """Drop uncommitted changes so a failed check leaves no residue."""

        self._git("reset", "--hard", "HEAD")
        self._git("clean", "-fd")

    def diff(self, branch: str) -> str:
        return self._git("diff", f"main...{branch}")

    def merge(self, branch: str, key: str) -> None:
        self._git("checkout", "main")
        self._git("merge", "--no-ff", branch, "-m", f"Accept {key}.")

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
