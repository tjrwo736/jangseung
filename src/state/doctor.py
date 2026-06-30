"""Doctor checks for the local Aegis runtime."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path

from src.contracts import SAFE_DEFAULT, STATE_DIR
from src.state import git
from src.state.store import state_root


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    message: str
    fix_hint: str = ""
    next_step: str = ""
    details: tuple[tuple[str, str], ...] = ()

    @property
    def detail(self) -> str:
        return self.message


def run_doctor(cwd: str | Path) -> list[DoctorCheck]:
    cwd_path = Path(cwd).resolve()
    checks: list[DoctorCheck] = []

    checks.append(
        DoctorCheck(
            "OS / path info",
            PASS,
            "Local OS and command path context recorded.",
            details=(
                ("os", platform.platform()),
                ("cwd", str(cwd_path)),
                ("safe_default", SAFE_DEFAULT),
            ),
        )
    )

    if not git.git_available():
        checks.append(
            DoctorCheck(
                "git command available",
                FAIL,
                "The git command was not found on PATH.",
                fix_hint="Install Git and make sure the git command is available on PATH.",
            )
        )
        checks.append(
            DoctorCheck(
                "inside git repo",
                FAIL,
                "Could not determine whether the current directory is inside a Git work tree because git is unavailable.",
                fix_hint="Install Git, then rerun aeg doctor from inside the target repository.",
            )
        )
        checks.extend(_repo_unavailable_checks("Git is required to detect the repository."))
        checks.extend(_state_unavailable_checks("Git is required to locate folder-local .aeg/ state."))
        checks.extend(_non_requirement_checks())
        return checks

    checks.append(
        DoctorCheck(
            "git command available",
            PASS,
            "The git command is available.",
        )
    )

    if git.inside_work_tree(cwd_path):
        checks.append(
            DoctorCheck(
                "inside git repo",
                PASS,
                "Current directory is inside a Git work tree.",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "inside git repo",
                FAIL,
                "Current directory is not inside a Git work tree.",
                fix_hint="Run aeg doctor from inside a Git repository, or initialize this folder with git init.",
            )
        )
        checks.extend(_repo_unavailable_checks("A Git work tree is required to detect the repository root."))
        checks.extend(_state_unavailable_checks("Repository root is unavailable outside a Git work tree."))
        checks.extend(_non_requirement_checks())
        return checks

    try:
        repo = git.repo_root(cwd_path)
        checks.append(
            DoctorCheck(
                "repo root detected",
                PASS,
                f"Repository root detected: {repo}",
                details=(("repo_root", str(repo)),),
            )
        )
    except git.GitError as exc:
        checks.append(
            DoctorCheck(
                "repo root detected",
                FAIL,
                f"Could not detect repository root: {exc}",
                fix_hint="Run aeg doctor from inside a valid Git repository.",
            )
        )
        checks.extend(_head_tree_unavailable_checks("Repository root was not detected."))
        checks.extend(_state_unavailable_checks("Repository root was not detected."))
        checks.extend(_non_requirement_checks())
        return checks

    for name, reader, detail_key in (
        ("HEAD SHA readable", git.head_sha, "head_sha"),
        ("tree SHA readable", git.tree_sha, "tree_sha"),
    ):
        try:
            value = reader(repo)
            checks.append(
                DoctorCheck(
                    name,
                    PASS,
                    f"{detail_key} is readable: {value}",
                    details=((detail_key, value),),
                )
            )
        except git.GitError as exc:
            checks.append(
                DoctorCheck(
                    name,
                    FAIL,
                    f"Could not read {detail_key}: {exc}",
                    fix_hint="Check that this repository has at least one commit and that Git can read it.",
                )
            )

    checks.extend(_state_checks(repo))
    checks.extend(_non_requirement_checks())
    return checks


def doctor_status(checks: list[DoctorCheck]) -> str:
    if any(check.status == FAIL for check in checks):
        return FAIL
    if any(check.status == WARN for check in checks):
        return PASS_WITH_WARNINGS
    return PASS


def _repo_unavailable_checks(reason: str) -> list[DoctorCheck]:
    return [
        DoctorCheck(
            "repo root detected",
            FAIL,
            f"Repository root is not available. {reason}",
            fix_hint="Run aeg doctor from inside a Git repository, or initialize this folder with git init.",
        ),
        *_head_tree_unavailable_checks(reason),
    ]


def _head_tree_unavailable_checks(reason: str) -> list[DoctorCheck]:
    return [
        DoctorCheck(
            "HEAD SHA readable",
            WARN,
            f"HEAD SHA was not checked. {reason}",
            next_step="After entering a Git repository with at least one commit, rerun aeg doctor.",
        ),
        DoctorCheck(
            "tree SHA readable",
            WARN,
            f"Tree SHA was not checked. {reason}",
            next_step="After entering a Git repository with at least one commit, rerun aeg doctor.",
        ),
    ]


def _state_unavailable_checks(reason: str) -> list[DoctorCheck]:
    return [
        DoctorCheck(
            "folder-local state path",
            WARN,
            f"Folder-local {STATE_DIR}/ path is not available. {reason}",
            next_step="Rerun aeg doctor from inside the target repository.",
            details=(("state_path", "NOT_AVAILABLE"),),
        ),
        DoctorCheck(
            f"{STATE_DIR}/ exists",
            WARN,
            f"{STATE_DIR}/ existence was not checked. {reason}",
            next_step="Rerun aeg doctor from inside the target repository.",
        ),
        DoctorCheck(
            f"{STATE_DIR}/ writable",
            WARN,
            f"{STATE_DIR}/ writability was not checked. {reason}",
            next_step="Rerun aeg doctor from inside the target repository.",
        ),
        DoctorCheck(
            f"{STATE_DIR}/ git ignored",
            WARN,
            f"{STATE_DIR}/ ignore status was not checked. {reason}",
            next_step=f"Rerun aeg doctor from inside the target repository and ensure {STATE_DIR}/ is in .gitignore.",
        ),
        DoctorCheck(
            f"{STATE_DIR}/ tracked file count",
            WARN,
            f"{STATE_DIR}/ tracked file count was not checked. {reason}",
            next_step="Rerun aeg doctor from inside the target repository.",
        ),
        DoctorCheck(
            ".env tracked file count",
            WARN,
            f".env tracked file count was not checked. {reason}",
            next_step="Rerun aeg doctor from inside the target repository.",
        ),
    ]


def _state_checks(repo: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    root = state_root(repo)
    state_path = str(root)

    checks.append(
        DoctorCheck(
            "folder-local state path",
            PASS,
            f"Folder-local state path is {state_path}.",
            details=(("state_path", state_path),),
        )
    )

    state_dir_ready = False
    if root.exists() and root.is_dir():
        state_dir_ready = True
        checks.append(
            DoctorCheck(
                f"{STATE_DIR}/ exists",
                PASS,
                f"{STATE_DIR}/ exists.",
                details=(("state_path", state_path),),
            )
        )
    elif root.exists():
        checks.append(
            DoctorCheck(
                f"{STATE_DIR}/ exists",
                FAIL,
                f"{STATE_DIR} exists but is not a directory.",
                fix_hint=f"Move or remove {STATE_DIR}, then run aeg init to create folder-local state.",
                details=(("state_path", state_path),),
            )
        )
    else:
        checks.append(
            DoctorCheck(
                f"{STATE_DIR}/ exists",
                WARN,
                f"{STATE_DIR}/ does not exist yet.",
                fix_hint="Run aeg init to create folder-local Aegis state.",
                details=(("state_path", state_path),),
            )
        )

    if state_dir_ready:
        if _state_dir_writable(root):
            checks.append(
                DoctorCheck(
                    f"{STATE_DIR}/ writable",
                    PASS,
                    f"{STATE_DIR}/ is writable.",
                    details=(("state_path", state_path),),
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    f"{STATE_DIR}/ writable",
                    FAIL,
                    f"{STATE_DIR}/ exists but is not writable.",
                    fix_hint=f"Fix filesystem permissions or ownership for {state_path}, then rerun aeg doctor.",
                    details=(("state_path", state_path),),
                )
            )
    else:
        checks.append(
            DoctorCheck(
                f"{STATE_DIR}/ writable",
                WARN,
                f"{STATE_DIR}/ writability was not checked because the state directory is missing or invalid.",
                fix_hint="Run aeg init, then rerun aeg doctor.",
                details=(("state_path", state_path),),
            )
        )

    if git.is_ignored(repo, f"{STATE_DIR}/"):
        checks.append(
            DoctorCheck(
                f"{STATE_DIR}/ git ignored",
                PASS,
                f"{STATE_DIR}/ is ignored by Git.",
                details=(("pathspec", f"{STATE_DIR}/"),),
            )
        )
    else:
        checks.append(
            DoctorCheck(
                f"{STATE_DIR}/ git ignored",
                FAIL,
                f"{STATE_DIR}/ is not ignored by Git.",
                fix_hint=f"Add {STATE_DIR}/ to .gitignore so runtime state is not committed.",
                details=(("pathspec", f"{STATE_DIR}/"),),
            )
        )

    checks.append(_tracked_count_check(repo, STATE_DIR, f"{STATE_DIR}/ tracked file count"))
    checks.append(_tracked_count_check(repo, ".env", ".env tracked file count"))
    return checks


def _tracked_count_check(repo: Path, pathspec: str, name: str) -> DoctorCheck:
    try:
        count = git.tracked_file_count(repo, pathspec)
    except git.GitError as exc:
        return DoctorCheck(
            name,
            FAIL,
            f"Could not inspect tracked files for {pathspec}: {exc}",
            fix_hint="Check Git status and rerun aeg doctor.",
            details=(("pathspec", pathspec),),
        )

    if count == 0:
        return DoctorCheck(
            name,
            PASS,
            f"No tracked files found for {pathspec}.",
            details=(("pathspec", pathspec), ("tracked_count", "0")),
        )

    fix_hint = f"Remove tracked {pathspec} files from Git while keeping local files if needed."
    if pathspec == STATE_DIR:
        fix_hint = f"Run git rm --cached -r {STATE_DIR} and keep {STATE_DIR}/ in .gitignore."
    elif pathspec == ".env":
        fix_hint = "Run git rm --cached .env and keep real secrets out of Git."
    return DoctorCheck(
        name,
        FAIL,
        f"{count} tracked file(s) found for {pathspec}.",
        fix_hint=fix_hint,
        details=(("pathspec", pathspec), ("tracked_count", str(count))),
    )


def _state_dir_writable(path: Path) -> bool:
    return os.access(path, os.W_OK)


def _non_requirement_checks() -> list[DoctorCheck]:
    return [
        DoctorCheck(
            "network not required",
            PASS,
            "Network access is not required for the core terminal + repo + folder-local state loop.",
            next_step="No network setup is needed for aeg init, aeg doctor, aeg run, or aeg verify.",
        ),
        DoctorCheck(
            "provider not required",
            PASS,
            "External provider credentials are not required for the core runtime.",
            next_step="Provider configuration can remain absent for this no-op contract-first runtime.",
        ),
        DoctorCheck(
            "OpenAI / Claude / Gemini not required",
            PASS,
            "OpenAI, Claude, and Gemini are optional future providers, not core dependencies.",
            next_step="Do not add provider tokens for doctor; this command does not need them.",
        ),
    ]
