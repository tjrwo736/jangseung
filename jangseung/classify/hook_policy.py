"""Optional per-project hook policy read from ``.aeg/policy.json``.

This is the approval path for what the built-in rules stop. Agents cannot write
this file because ``.aeg/`` is denied for every tool, so only a person can widen
the rules. A file that cannot be trusted is ignored as a whole, which keeps the
stricter built-in rules in force.
"""

from __future__ import annotations

from jangseung.records import dataclass, replace
import json
from pathlib import Path
import re
import shlex
TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Any

from jangseung.classify.git_program_paths import git_program_paths
from jangseung.classify.rules import PathPolicy
from jangseung.contracts import STATE_DIR

HOOK_POLICY_FILE = "policy.json"
MAX_POLICY_BYTES = 64 * 1024
# A policy a team commits to git. It can only add protection: ``protect_paths`` is
# its one key. ``.aeg/`` stays each person's own and is not committed. Agents cannot
# write this folder (it is a guard path), so a person edits it, by hand or with
# ``aeg policy add --shared --protect <path>``.
SHARED_POLICY_DIR = ".jangseung"
SHARED_POLICY_FILE = "policy.json"
_SHARED_KEYS = frozenset({"protect_paths"})

_KNOWN_KEYS = frozenset({"allow_paths", "protect_paths", "allow_commands", "allow_mcp_tools"})
_APPROVED_COMMAND = re.compile(r"[\w ./:=@+-]+")
# One exact MCP tool name, ``mcp__<server>__<tool>``. No patterns: a server name
# may itself contain ``__``, so a prefix could approve another server's tools.
_APPROVED_MCP_TOOL = re.compile(r"mcp__[A-Za-z0-9_-]+__[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class HookPolicy:
    paths: PathPolicy = PathPolicy()
    allow_commands: tuple[tuple[str, ...], ...] = ()
    allow_mcp_tools: frozenset[str] = frozenset()
    present: bool = False
    error: str | None = None

    def approves_command(self, argv: tuple[str, ...]) -> bool:
        return any(argv[: len(prefix)] == prefix for prefix in self.allow_commands)

    def approves_mcp_tool(self, tool_name: str) -> bool:
        return tool_name in self.allow_mcp_tools


def load_hook_policy(repo_root: str | Path, working_dir: str | Path | None = None) -> HookPolicy:
    """The person's policy plus what git would run, which no policy can open to agents."""

    policy = _read_policy_file(repo_root)
    shared, shared_error = read_shared_protect_paths(repo_root)
    if shared_error is not None:
        # A broken team file must not quietly drop its protection. Which paths it meant
        # cannot be known, so every path is protected until a person fixes the file,
        # and the policy is marked as failed (no host delegation, no file-operation allows).
        shared = (*shared, "*")
        if policy.error is None:
            policy = replace(policy, error=f"shared_{shared_error}")
    git_paths = git_program_paths(repo_root, working_dir)
    extra = (*shared, *git_paths)
    if not extra:
        return policy
    return replace(policy, paths=replace(policy.paths, protect_paths=(*policy.paths.protect_paths, *extra)))


def read_shared_protect_paths(repo_root: str | Path) -> tuple[tuple[str, ...], str | None]:
    """``protect_paths`` of the committed team policy, and an error when it cannot be used."""

    path = Path(repo_root) / SHARED_POLICY_DIR / SHARED_POLICY_FILE
    try:
        if path.parent.is_symlink() or path.is_symlink():
            return (), "policy_file_is_a_link"
        if not path.exists():
            return (), None
        if not path.is_file() or path.stat().st_size > MAX_POLICY_BYTES:
            return (), "policy_file_not_a_small_regular_file"
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return (), "policy_file_unreadable"
    if not isinstance(data, dict) or set(data) - _SHARED_KEYS:
        return (), "policy_file_may_only_hold_protect_paths"
    value = data.get("protect_paths", [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        return (), "policy_protect_paths_must_be_a_list_of_strings"
    return tuple(value), None


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
    return parse_policy(data)


def parse_policy(data: Any) -> HookPolicy:
    """Check policy data the way the hook does; ``error`` is set when it would be ignored."""

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
    if not all(_APPROVED_MCP_TOOL.fullmatch(text) for text in lists["allow_mcp_tools"]):
        return HookPolicy(present=True, error="policy_allow_mcp_tools_must_be_exact_mcp_tool_names")
    return HookPolicy(
        paths=PathPolicy(allow_paths=lists["allow_paths"], protect_paths=lists["protect_paths"]),
        allow_commands=tuple(commands),
        allow_mcp_tools=frozenset(lists["allow_mcp_tools"]),
        present=True,
    )


__all__ = [
    "HOOK_POLICY_FILE",
    "MAX_POLICY_BYTES",
    "SHARED_POLICY_DIR",
    "SHARED_POLICY_FILE",
    "HookPolicy",
    "load_hook_policy",
    "parse_policy",
    "read_shared_protect_paths",
]
