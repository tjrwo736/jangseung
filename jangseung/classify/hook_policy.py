"""Optional per-project hook policy read from ``.aeg/policy.json``.

This is the approval path for what the built-in rules stop. Agents cannot write
this file because ``.aeg/`` is denied for every tool, so only a person can widen
the rules. A file that cannot be trusted is ignored as a whole, which keeps the
stricter built-in rules in force.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
import shlex
from typing import Any

from jangseung.classify.git_program_paths import git_program_paths
from jangseung.classify.rules import PathPolicy
from jangseung.contracts import STATE_DIR

HOOK_POLICY_FILE = "policy.json"
MAX_POLICY_BYTES = 64 * 1024

_KNOWN_KEYS = frozenset({"allow_paths", "protect_paths", "allow_commands"})
_APPROVED_COMMAND = re.compile(r"[\w ./:=@+-]+")


@dataclass(frozen=True)
class HookPolicy:
    paths: PathPolicy = PathPolicy()
    allow_commands: tuple[tuple[str, ...], ...] = ()
    present: bool = False
    error: str | None = None

    def approves_command(self, argv: tuple[str, ...]) -> bool:
        return any(argv[: len(prefix)] == prefix for prefix in self.allow_commands)


def load_hook_policy(repo_root: str | Path, working_dir: str | Path | None = None) -> HookPolicy:
    """The person's policy plus what git would run, which no policy can open to agents."""

    policy = _read_policy_file(repo_root)
    git_paths = git_program_paths(repo_root, working_dir)
    if not git_paths:
        return policy
    return replace(policy, paths=replace(policy.paths, protect_paths=(*policy.paths.protect_paths, *git_paths)))


def _read_policy_file(repo_root: str | Path) -> HookPolicy:
    path = Path(repo_root) / STATE_DIR / HOOK_POLICY_FILE
    try:
        if path.is_symlink():
            return HookPolicy(present=True, error="policy_file_is_a_link")
        if not path.exists():
            return HookPolicy()
        if not path.is_file() or path.stat().st_size > MAX_POLICY_BYTES:
            return HookPolicy(present=True, error="policy_file_not_a_small_regular_file")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return HookPolicy(present=True, error="policy_file_unreadable")
    return _parse_policy(data)


def _parse_policy(data: Any) -> HookPolicy:
    if not isinstance(data, dict) or set(data) - _KNOWN_KEYS:
        return HookPolicy(present=True, error="policy_file_has_unexpected_shape")
    lists: dict[str, tuple[str, ...]] = {}
    for key in _KNOWN_KEYS:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            return HookPolicy(present=True, error=f"policy_{key}_must_be_a_list_of_strings")
        lists[key] = tuple(value)
    commands: list[tuple[str, ...]] = []
    for text in lists["allow_commands"]:
        if not _APPROVED_COMMAND.fullmatch(text):
            return HookPolicy(present=True, error="policy_allow_commands_must_be_plain_words")
        commands.append(tuple(shlex.split(text)))
    return HookPolicy(
        paths=PathPolicy(allow_paths=lists["allow_paths"], protect_paths=lists["protect_paths"]),
        allow_commands=tuple(commands),
        present=True,
    )


__all__ = ["HOOK_POLICY_FILE", "HookPolicy", "load_hook_policy"]
