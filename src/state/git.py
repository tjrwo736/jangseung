"""Small git helpers used by the local runtime."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from typing import Any

from src.contracts import GIT_STAGED, GIT_TRACKED_DIFF, GIT_WORKING_TREE, NO_CHANGED_FILES_SOURCE


class GitError(RuntimeError):
    """Raised when a git command needed for evidence binding fails."""


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


def branch_name(repo: str | Path) -> str:
    branch = run_git(["branch", "--show-current"], repo).stdout.strip()
    return branch or "HEAD"


def status_porcelain(repo: str | Path) -> list[str]:
    completed = run_git(["status", "--porcelain=v1"], repo)
    return [line for line in completed.stdout.splitlines() if line.strip()]


def is_dirty(repo: str | Path) -> bool:
    return bool(status_porcelain(repo))


def changed_files(repo: str | Path) -> list[str]:
    files: list[str] = []
    for line in status_porcelain(repo):
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            files.append(path)
    return sorted(dict.fromkeys(files))


def changed_files_with_source(repo: str | Path) -> tuple[list[str], str]:
    lines = status_porcelain(repo)
    files = changed_files(repo)
    if not files:
        return [], NO_CHANGED_FILES_SOURCE

    has_worktree_change = any(line[:2] == "??" or line[1] != " " for line in lines)
    if has_worktree_change:
        return files, GIT_WORKING_TREE
    return files, GIT_STAGED


def changed_file_snapshot(repo: str | Path) -> list[dict[str, Any]]:
    lines = status_porcelain(repo)
    tracked_diff_status = _tracked_diff_status(repo)
    entries = []
    for line in lines:
        entry = _status_entry(line, tracked_diff_status)
        if entry is None:
            continue
        if _is_runtime_state_path(entry["path"]):
            continue
        entries.append(entry)
    return sorted(entries, key=lambda item: (item["path"], item.get("original_path") or ""))


def changed_files_from_snapshot(snapshot: list[dict[str, Any]]) -> list[str]:
    files = [entry.get("path", "") for entry in snapshot if isinstance(entry.get("path"), str)]
    return sorted(dict.fromkeys(path for path in files if path))


def changed_files_source_from_snapshot(snapshot: list[dict[str, Any]]) -> str:
    if not snapshot:
        return NO_CHANGED_FILES_SOURCE
    if any(entry.get("untracked") is True or entry.get("unstaged") is True for entry in snapshot):
        return GIT_WORKING_TREE
    return GIT_STAGED


def changed_files_against(repo: str | Path, base_ref: str) -> tuple[list[str], str]:
    completed = run_git(["diff", "--name-only", base_ref, "--"], repo)
    files = sorted(dict.fromkeys(line.strip() for line in completed.stdout.splitlines() if line.strip()))
    if not files:
        return [], NO_CHANGED_FILES_SOURCE
    return files, GIT_TRACKED_DIFF


def is_ignored(repo: str | Path, path: str) -> bool:
    completed = run_git(["check-ignore", "-q", path], repo, check=False)
    return completed.returncode == 0


def ls_files(repo: str | Path, pathspec: str) -> list[str]:
    completed = run_git(["ls-files", "--", pathspec], repo)
    return [line for line in completed.stdout.splitlines() if line.strip()]


def tracked_file_count(repo: str | Path, pathspec: str) -> int:
    return len(ls_files(repo, pathspec))


def object_exists(repo: str | Path, object_name: str, object_type: str) -> bool:
    if not object_name:
        return False
    completed = run_git(["cat-file", "-e", f"{object_name}^{{{object_type}}}"], repo, check=False)
    return completed.returncode == 0


def _tracked_diff_status(repo: str | Path) -> dict[str, str]:
    completed = run_git(["diff", "--name-status", "HEAD", "--"], repo)
    statuses: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        parts = [part for part in line.split("\t") if part]
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1]
        statuses[_normalize_status_path(path)] = status
    return statuses


def _status_entry(line: str, tracked_diff_status: dict[str, str]) -> dict[str, Any] | None:
    if len(line) < 4:
        return None
    index_status = line[0]
    worktree_status = line[1]
    raw_path = line[3:].strip()
    original_path = None
    path = raw_path
    if " -> " in raw_path:
        original_path, path = raw_path.split(" -> ", 1)
        original_path = _normalize_status_path(original_path)
    path = _normalize_status_path(path)
    if not path:
        return None
    untracked = line[:2] == "??"
    staged = not untracked and index_status != " "
    unstaged = untracked or worktree_status != " "
    tracked = not untracked
    return {
        "path": path,
        "original_path": original_path,
        "index_status": index_status,
        "worktree_status": worktree_status,
        "index_state": _status_name(index_status),
        "worktree_state": _status_name(worktree_status),
        "tracked_diff_status": tracked_diff_status.get(path, "untracked" if untracked else "clean"),
        "staged": staged,
        "unstaged": unstaged,
        "tracked": tracked,
        "untracked": untracked,
    }


def _normalize_status_path(path: str) -> str:
    item = str(path).strip().replace("\\", "/")
    while item.startswith("./"):
        item = item[2:]
    return item


def _status_name(status: str) -> str:
    return {
        " ": "clean",
        "?": "untracked",
        "!": "ignored",
        "M": "modified",
        "A": "added",
        "D": "deleted",
        "R": "renamed",
        "C": "copied",
        "T": "type_changed",
        "U": "unmerged",
    }.get(status, "unknown")


def _is_runtime_state_path(path: str) -> bool:
    normalized = _normalize_status_path(path)
    return normalized == ".aeg" or normalized.startswith(".aeg/")
