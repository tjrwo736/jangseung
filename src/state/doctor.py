"""Doctor checks for the local Aegis runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.contracts import STATE_DIR
from src.state import git
from src.state.store import state_root


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


def run_doctor(cwd: str | Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []

    if git.git_available():
        checks.append(DoctorCheck("git.available", "PASS", "git command is available"))
    else:
        checks.append(DoctorCheck("git.available", "FAIL", "git command was not found"))
        return checks

    if git.inside_work_tree(cwd):
        checks.append(DoctorCheck("git.work_tree", "PASS", "current directory is inside a git work tree"))
    else:
        checks.append(DoctorCheck("git.work_tree", "FAIL", "current directory is not inside a git work tree"))
        return checks

    try:
        repo = git.repo_root(cwd)
        checks.append(DoctorCheck("git.repo_root", "PASS", str(repo)))
    except git.GitError as exc:
        checks.append(DoctorCheck("git.repo_root", "FAIL", str(exc)))
        return checks

    for name, reader in (("git.head_sha", git.head_sha), ("git.tree_sha", git.tree_sha)):
        try:
            checks.append(DoctorCheck(name, "PASS", reader(repo)))
        except git.GitError as exc:
            checks.append(DoctorCheck(name, "FAIL", str(exc)))

    root = state_root(repo)
    if root.exists() and root.is_dir():
        if os.access(root, os.W_OK):
            checks.append(DoctorCheck("state.writable", "PASS", f"{STATE_DIR}/ exists"))
        else:
            checks.append(DoctorCheck("state.writable", "FAIL", f"{STATE_DIR}/ is not writable"))
    else:
        checks.append(DoctorCheck("state.writable", "WARN", f"{STATE_DIR}/ does not exist; run aeg init"))

    if git.is_ignored(repo, f"{STATE_DIR}/"):
        checks.append(DoctorCheck("state.git_ignored", "PASS", f"{STATE_DIR}/ is ignored by git"))
    else:
        checks.append(DoctorCheck("state.git_ignored", "FAIL", f"{STATE_DIR}/ is not ignored by git"))

    checks.append(
        DoctorCheck(
            "providers.required",
            "PASS",
            "external provider credentials are not required for Day-1 no-op runtime",
        )
    )
    return checks


def doctor_status(checks: list[DoctorCheck]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "WARN" for check in checks):
        return "WARN"
    return "PASS"
