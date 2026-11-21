"""Personal approvals come only from user-owned storage; checkout files can only restrict."""

from __future__ import annotations

from jangseung.records import dataclass, replace
from jangseung._resolve import resolved
import json
from pathlib import Path
import re
import shlex
TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Any

from jangseung.classify.git_program_paths import git_program_paths
from jangseung.classify.rules import PathPolicy
from jangseung.state.approvals import approval_root, read_small_file
from jangseung.state.paths import state_root

HOOK_POLICY_FILE = "policy.json"
MAX_POLICY_BYTES = 64 * 1024
# A policy a team commits to git. It can only add protection: ``protect_paths`` is
# its one key. Agents cannot write this folder (it is a guard path), so a
# person edits it, by hand or with
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

    try:
        policy = _read_policy_file(approval_root(repo_root) / HOOK_POLICY_FILE, personal=True)
    except (OSError, ValueError, RuntimeError, KeyError):
        policy = HookPolicy(present=True, error="personal_approval_directory_unavailable")
    try:
        legacy = _read_policy_file(state_root(repo_root) / HOOK_POLICY_FILE)
    except (OSError, ValueError, RuntimeError):
        legacy = HookPolicy(present=True, error="unsafe_project_state_directory")
    shared, shared_error = read_shared_protect_paths(repo_root)
    error = policy.error or legacy.error or (f"shared_{shared_error}" if shared_error else None)
    if error:
        # Unknown restrictions cannot be silently dropped; no personal grant applies.
        policy = HookPolicy(paths=PathPolicy(protect_paths=("*",)), present=True, error=error)
    elif legacy.present:
        policy = replace(policy, present=True)
    if working_dir is not None and (policy.paths.allow_paths or policy.allow_commands or policy.allow_mcp_tools):
        try:
            inside = resolved(working_dir, strict=True).is_relative_to(resolved(repo_root, strict=True))
        except (OSError, ValueError, RuntimeError):
            inside = False
        if not inside:
            # The host may keep publishing its original project after a cd.
            # In particular, a named MCP tool must not inherit that project's grants.
            policy = replace(policy, paths=replace(policy.paths, allow_paths=()),
                             allow_commands=(), allow_mcp_tools=frozenset())
    git_paths = git_program_paths(repo_root, working_dir)
    extra = (*legacy.paths.protect_paths, *shared, *git_paths)
    if not extra:
        return policy
    return replace(policy, paths=replace(policy.paths, protect_paths=(*policy.paths.protect_paths, *extra)))


def read_shared_protect_paths(repo_root: str | Path) -> tuple[tuple[str, ...], str | None]:
    """``protect_paths`` of the committed team policy, and an error when it cannot be used."""

    path = Path(repo_root) / SHARED_POLICY_DIR / SHARED_POLICY_FILE
    try:
        import stat

        try:
            parent = path.parent.lstat()
        except FileNotFoundError:
            return (), None
        if (not stat.S_ISDIR(parent.st_mode)
                or getattr(parent, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            return (), "policy_file_is_a_link"
        raw = read_small_file(path, MAX_POLICY_BYTES)
        if raw is None:
            return (), None
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, RecursionError):
        return (), "policy_file_unreadable"
    if not isinstance(data, dict) or set(data) - _SHARED_KEYS:
        return (), "policy_file_may_only_hold_protect_paths"
    value = data.get("protect_paths", [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        return (), "policy_protect_paths_must_be_a_list_of_strings"
    return tuple(value), None


def _read_policy_file(path: Path, *, personal: bool = False) -> HookPolicy:
    try:
        raw = read_small_file(path, MAX_POLICY_BYTES, personal=personal)
        if raw is None:
            return HookPolicy()
        data = json.loads(raw.decode("utf-8"))
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
