"""Small git helpers used by the doctor and evidence commands."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class GitError(RuntimeError):
    """Raised when a git command needed by a diagnostic or evidence command fails."""


def git_available() -> bool:
    return shutil.which("git") is not None


def run_git(args: list[str], cwd: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GitError(f"{' '.join(command)} failed: {detail}")
    return completed


def repo_root(cwd: str | Path) -> Path:
    completed = run_git(["rev-parse", "--show-toplevel"], cwd)
    return Path(completed.stdout.strip()).resolve()


def inside_work_tree(cwd: str | Path) -> bool:
    completed = run_git(["rev-parse", "--is-inside-work-tree"], cwd, check=False)
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def head_sha(repo: str | Path) -> str:
    return run_git(["rev-parse", "HEAD"], repo).stdout.strip()


def tree_sha(repo: str | Path) -> str:
    return run_git(["rev-parse", "HEAD^{tree}"], repo).stdout.strip()


def ls_files(repo: str | Path, pathspec: str) -> list[str]:
    completed = run_git(["ls-files", "--", pathspec], repo)
    return [line for line in completed.stdout.splitlines() if line.strip()]


def tracked_file_count(repo: str | Path, pathspec: str) -> int:
    return len(ls_files(repo, pathspec))
