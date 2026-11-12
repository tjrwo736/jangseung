"""Phase 11-C-8 hook judgment alignment with existing Aegis gates.

This module is a side-effect-free adapter from validated Claude Code PreToolUse-shaped data
to existing Aegis judgment components. It does not install hooks, emit hook
output, execute tools, read secrets, write state, or grant authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shlex
import stat
import sys
from types import MappingProxyType
from typing import Any

from jangseung.classify import (
    Classification,
    classify_task,
    contains_protected_path,
    git_exclusion_pathspecs,
    is_host_resolved_path,
    is_protected_path,
    is_read_protected_path,
    is_prose_path,
    is_secret_path,
    names_secret_file,
    search_exclusion_globs,
    strip_path_decorations,
)
from jangseung.classify.hook_policy import HookPolicy, load_hook_policy
from jangseung.contracts import (
    CLEAN_CORE,
    GIT_WORKING_TREE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    LOW,
    MEDIUM,
    NEEDS_USER_GATE,
    NOT_CHECKED,
    NOT_CHECKED_SOURCE,
    SAFE_DEFAULT,
)
from jangseung.evidence.b1_aeg_integrity_guard import decide_b1_aeg_integrity_guard
from jangseung.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    PreToolUseInputValidationResult,
    is_mcp_tool_name,
    validate_claude_code_pretooluse_input,
)
from jangseung.evidence.mcp_tool_gate import judge_mcp_tool_call
from jangseung.evidence.claude_code_tool_call_mapping import (
    BASH_DANGEROUS,
    BASH_NOT_CHECKED,
    DENY_CANDIDATE,
    EDIT_FILE,
    POWERSHELL_DANGEROUS,
    POWERSHELL_NOT_CHECKED,
    READ_REPO,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    extract_apply_patch_targets,
    extract_bash_write_delete_targets,
    extract_powershell_write_delete_targets,
    map_pretooluse_input_to_structured_action_candidate,
    powershell_argvs,
    powershell_words,
    rewrite_apply_patch_targets,
)
from jangseung.evidence.claude_code_tool_call_mapping import RUN_COMMAND as MAPPING_RUN_COMMAND
from jangseung.evidence.claude_code_tool_call_mapping import WRITE_FILE as MAPPING_WRITE_FILE
from jangseung.evidence.hook_decision_adapter import ALLOW, ASK, DEFER, DENY
from jangseung.evidence.mediated_repo_boundary_write_path import resolve_repo_boundary_path
from jangseung.evidence.shell_command_risk import (
    GUARD_SELF_DISABLE_REASON,
    bash_words,
    brace_expansions,
    command_name,
    git_subcommand,
    nested_shell_payloads,
    scan_bash_command,
    secret_references,
    strip_assignments,
)
from jangseung.evidence.shell_glob_targets import (
    GlobBudget,
    expand_glob_word,
    glob_forms,
    has_glob,
    names_something,
    path_words,
    project_roots,
    reads_matched_files,
    repository_relative_text,
)
from jangseung.evidence.shell_read_only import classify_shell_read, git_output_command
from jangseung.evidence.shell_normal_work import (
    classify_shell_file_operation, host_execution_candidate, plain_command_words,
)
from jangseung.evidence.shell_command_risk import BASH_TRAILING_ESCAPE_REASON
from jangseung.evidence.structured_action_capabilities import (
    CAPABILITY_DENIED,
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    FUTURE_GATE_REQUIRED,
    NOT_IMPLEMENTED_REJECTED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
    SCOPE_LIMIT_REJECTED,
    UNKNOWN_CAPABILITY_REJECTED,
    evaluate_action_capabilities,
)
from jangseung.evidence.structured_actions import (
    NOOP,
    REQUEST_REPO_READ,
    RUN_COMMAND,
    WRITE_FILE,
)
from jangseung.law import apply_law
from jangseung.state.session_marks import secret_naming_writes

PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION = (
    "phase11c_8_hook_judgment_engine_alignment_v0"
)

ENGINE_ALLOWED_CAPABILITY_RESULTS = frozenset(
    {
        CAPABILITY_GATE_ALLOWED,
        CAPABILITY_GATE_LIMITED_ALLOWED,
    }
)
ENGINE_DENY_CAPABILITY_RESULTS = frozenset(
    {
        CAPABILITY_DENIED,
        FUTURE_GATE_REQUIRED,
        NOT_IMPLEMENTED_REJECTED,
        UNKNOWN_CAPABILITY_REJECTED,
        REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
        SCOPE_LIMIT_REJECTED,
    }
)

HOOK_DECISION_STRENGTH = MappingProxyType({ALLOW: 0, ASK: 1, DEFER: 2, DENY: 3})
ENGINE_BASIS_SOURCES = (
    "jangseung.classify.classify_task",
    "jangseung.classify.is_protected_path",
    "jangseung.law.apply_law",
    "jangseung.evidence.structured_action_capabilities.evaluate_action_capabilities",
    "jangseung.evidence.b1_aeg_integrity_guard.decide_b1_aeg_integrity_guard",
    "jangseung.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path",
)

# WRITE_FILE/RUN_COMMAND capability policy answers "may Aegis itself execute
# this action" (always denied under the 11-B propose-only executor model).
# That is a different question from "should the hook allow this substrate
# tool call", which must be judged by the target path/command risk
# (is_protected_path, the .aeg state-dir guard, the dangerous-Bash gate, and
# classify/law), not by reusing Aegis's own self-execution capability denial
# as if it answered the hook question. These two action types are therefore
# excluded from driving the hook decision via the capability gate; the
# capability gate result is still computed and recorded in evidence for
# transparency, but it is not treated as hook judgment basis for them.
_SELF_EXECUTION_CAPABILITY_ACTION_TYPES_NOT_HOOK_JUDGMENT_BASIS = frozenset(
    {MAPPING_WRITE_FILE, EDIT_FILE, MAPPING_RUN_COMMAND}
)
_WRITE_LIKE_CANDIDATE_ACTION_TYPES = frozenset({MAPPING_WRITE_FILE, EDIT_FILE})
_WRITE_LIKE_TOOL_NAMES = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"})
_READ_LIKE_TOOL_NAMES = frozenset({"Read", "Grep", "Glob"})
_COMMAND_TOOL_NAMES = frozenset({"Bash", "PowerShell"})
_COMMAND_TARGET_DENY_KINDS = frozenset({"out_of_scope", "secret_path", "protected_path", "protected_state_dir"})
_SHELL_READ_DENY_KINDS = frozenset({"out_of_scope", "secret_path", "protected_state_dir"})
_PROJECT_WORKING_FOLDER_KINDS = frozenset({"safe_in_repo", "protected_path", "secret_path"})
_APPROVED_COMMAND_REJECTED_CHARACTERS = "\n\r\x00$`{}()&;<>|#"
_TYPOGRAPHIC_QUOTES = frozenset("‘’‚‛“”„‟")
# Only a space or a tab separates words in every shell. Other "white" characters
# are word text in bash, so ``tool.py\f2>&1`` runs a file named ``tool.py\f2``.
_STDERR_TO_STDOUT = re.compile(r"[ \t]+2>&1[ \t]*$")
# A folder name made of plain components. No option-like ``-`` or ``--``, no ``..``,
# no dots or spaces a file system might trim: the folder judged must be the folder
# the shell enters. An optional ``./`` keeps bash from searching CDPATH.
_LEADING_CD = re.compile(
    r"[ \t]*cd[ \t]+((?:\./)?[A-Za-z0-9_][A-Za-z0-9_-]*(?:/[A-Za-z0-9_][A-Za-z0-9_-]*)*)[ \t]*&&[ \t]*(?=\S)"
)
# A word of an approved prefix that can only name a program, a subcommand or an
# option. Anything with a dot or a slash may be a file, and a relative file is a
# different file after ``cd``.
_FOLDER_INDEPENDENT_WORD = re.compile(r"-{0,2}[A-Za-z0-9_+:=@-]+")

# Permission modes in which the host puts the hook's question to a person. Only modes
# with that behavior documented or measured belong here; in every other mode a
# review-tier change stays denied, as it was before this tier existed.
# Measured with Claude Code 2.1.316 (``claude -p``, Windows): a hook's ``ask`` stopped an
# Edit in ``default`` and in ``acceptEdits``. ``auto`` stopped it too, but there a
# classifier may answer in the person's place, so it is left out; ``dontAsk`` and
# ``bypassPermissions`` were not measured.
_MODES_WHERE_HOST_ASKS_A_PERSON = frozenset({"default", "acceptEdits"})
REVIEW_TIER_REASON = "build_or_dependency_file_change_needs_user_review"
APPROVAL_HELD_REASON = "approved_command_held_after_write_naming_secret_file"

_WRITTEN_TEXT_SEPARATORS = re.compile(r"[\s'\"`(),;=+\[\]{}<>|&:]+")
_MAX_WRITTEN_TEXT_SCANNED = 400_000
_MAX_WRITTEN_WORDS_CHECKED = 40_000
# A copied file is read whole when small; a larger one is marked without reading.
_MAX_COPIED_BYTES_SCANNED = 1024 * 1024
_MAX_ASKED_SOURCES_CHECKED = 8
_MAX_AUDIT_ITEMS = 16
# A program name is short and mostly letters. Anything else in command position, a
# pasted token included, is recorded as "<other>" so the record cannot carry it.
_AUDIT_COMMAND_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.+-]{0,23}")
_AUDIT_GIT_SUBCOMMANDS = frozenset(
    {
        "add", "am", "apply", "archive", "bisect", "blame", "branch", "checkout", "cherry-pick", "clean",
        "clone", "commit", "config", "describe", "diff", "fetch", "gc", "grep", "init", "log", "ls-files",
        "merge", "mv", "pull", "push", "rebase", "reflog", "remote", "reset", "restore", "rev-parse",
        "revert", "rm", "show", "stash", "status", "submodule", "switch", "tag", "worktree",
    }
)
_MAX_AUDIT_NAME_DIGITS = 3
_MAX_AUDIT_NAME_HYPHENS = 2
OUTSIDE_PROJECT_TARGET = "<outside-project>"

# Read/Write/Edit of a repo-internal, non-protected file that the existing
# engine classified as a definite LOW or MEDIUM change is "clearly safe normal
# work" and is allowed so the hook does not obstruct ordinary safe operations.
# Everything ambiguous is deliberately excluded from this set:
#  - protected paths / dangerous Bash / repo-external / traversal already
#    returned DENY before this check;
#  - Bash maps to HOLD_CURRENT_STATE_CANDIDATE with impact NOT_CHECKED, so it is
#    never a STRUCTURED_ACTION_CANDIDATE and never clearly-safe -> ask/defer;
#    proven shell file reads have a separate allow gate before that fallback;
#  - PowerShell uses its own target gate, which can only deny; automatic allow
#    comes from the same positive shell-read grammar as Bash;
#  - a NOT_CHECKED / NOT_CHECKED_NO_MUTATION impact (unclassifiable / unknown
#    source) is not in the safe impact set -> ask/defer.
_CLEARLY_SAFE_FILE_ACTION_TYPES = frozenset(
    {READ_REPO, MAPPING_WRITE_FILE, EDIT_FILE}
)
_CLEARLY_SAFE_IMPACT_RISKS = frozenset({LOW, MEDIUM})
_CLEARLY_SAFE_RISK_LEVELS = frozenset({LOW, MEDIUM})

_REPORTED_ONLY_KEYS = frozenset(
    {
        "reported_only",
        "report_only",
        "self_report",
        "self_reported",
        "self_reported_allow",
        "self_reported_decision",
    }
)
_REPORTED_ONLY_VALUE_KEYS = frozenset({"basis", "source", "grant_source"})


@dataclass(frozen=True)
class HookJudgmentEngineRequest:
    tool_name: str | None
    tool_use_id: str | None
    target_paths: tuple[str, ...]
    command_present: bool
    raw_hook_input_hash: str
    raw_hook_input_hash_algorithm: str = "sha256_canonical_json_v0"
    raw_hook_input_stored: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_paths", tuple(self.target_paths))

    def to_record(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_use_id": self.tool_use_id,
            "target_paths": self.target_paths,
            "command_present": self.command_present,
            "raw_hook_input_hash": self.raw_hook_input_hash,
            "raw_hook_input_hash_algorithm": self.raw_hook_input_hash_algorithm,
            "raw_hook_input_stored": self.raw_hook_input_stored,
        }


@dataclass(frozen=True)
class HookJudgmentEngineDecision:
    decision_id: str
    decision_hash: str
    contract_version: str
    request: HookJudgmentEngineRequest
    engine_decision: str
    hook_decision: str
    decision_reasons: tuple[str, ...]
    engine_decision_basis: Mapping[str, Any]
    engine_basis_sources: tuple[str, ...]
    hook_decision_matches_or_is_stricter_than_engine: bool
    protected_path_policy_duplicated_in_hook: bool = False
    hook_policy_divergence_allowed: bool = False
    reported_only_trusted_as_judgment_basis: bool = False
    not_checked_is_allow: bool = False
    unclassified_bash_is_allow: bool = False
    safe_default: str = SAFE_DEFAULT
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    # What the host must run instead of the submitted input. Not evidence: it holds
    # raw tool input, so it stays out of the decision hash and record.
    updated_tool_input: Mapping[str, Any] | None = None
    # Redacted facts for the hook record: which project files and which programs the
    # call names. Like updated_tool_input, they stay out of the decision hash.
    audit_targets: tuple[str, ...] = ()
    audit_commands: tuple[str, ...] = ()
    written_text_names_secret_file: bool = False
    # Eligibility is not an allow. Only the wiring for Claude Code/default may
    # omit its permission decision and let the host's normal rules decide.
    host_delegation_eligible: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_reasons", tuple(self.decision_reasons))
        object.__setattr__(self, "engine_basis_sources", tuple(self.engine_basis_sources))
        object.__setattr__(
            self,
            "engine_decision_basis",
            _freeze_value(self.engine_decision_basis),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            **_plain_json_data(_decision_payload(self)),
        }


def judge_pretooluse_with_aeg_engine(
    raw_hook_input: Mapping[str, Any],
    *,
    repo_root: str | Path,
    working_dir: str | Path | None = None,
) -> HookJudgmentEngineDecision:
    """Return a hook decision candidate aligned with existing Aegis gates.

    ``repo_root`` anchors the policy. ``working_dir`` is where relative targets
    resolve; the hook input's own ``cwd`` wins when it names a real directory.
    """

    validation = validate_claude_code_pretooluse_input(raw_hook_input)
    hook_input = validation.hook_input
    ignored_reported_only_fields = _reported_only_fields(raw_hook_input)

    if not validation.valid or hook_input is None:
        request = _build_request(raw_hook_input, hook_input)
        basis = {
            "input_validation": _validation_record(validation),
            "ignored_reported_only_fields": ignored_reported_only_fields,
            "reported_only_trusted_as_judgment_basis": False,
            "not_checked_is_allow": False,
            "safe_default": SAFE_DEFAULT,
        }
        return _build_decision(
            request=request,
            engine_decision=DEFER,
            hook_decision=DEFER,
            reasons=(
                "pretooluse_input_invalid_or_unsupported",
                "invalid_unknown_or_unsupported_tool_maps_to_defer",
                "safe_default_hold_current_state",
            ),
            basis=basis,
        )

    if is_mcp_tool_name(hook_input.tool_name):
        return _judge_mcp_tool_call(
            raw_hook_input, hook_input, validation, ignored_reported_only_fields, repo_root, working_dir
        )

    # Tools may send absolute paths or paths relative to the session's directory.
    # Rewrite repo-internal ones to their canonical repo-relative form so the
    # engine judges the file that would really be touched; a repo-external or
    # traversal-escaping path keeps its form so the scope defense rejects it.
    base_dir = _effective_working_dir(hook_input, repo_root, working_dir)
    policy = load_hook_policy(repo_root, base_dir)
    judged = (raw_hook_input, hook_input, validation, ignored_reported_only_fields, repo_root, base_dir)
    decision = _judge_file_or_command_call(*judged, policy)
    if decision.hook_decision != DENY or not _host_asks_a_person(raw_hook_input):
        return decision
    # Judge again with the review tier left out. If nothing else objects, the only
    # thing in the way was a build or dependency file, and a person may approve that.
    reviewed = _judge_file_or_command_call(
        *judged, replace(policy, paths=replace(policy.paths, review_lifted=True))
    )
    if reviewed.hook_decision == DENY:
        return decision
    return _build_decision(
        request=reviewed.request,
        engine_decision=ASK,
        hook_decision=ASK,
        reasons=(REVIEW_TIER_REASON, "hook_decision_matches_or_is_stricter_than_engine"),
        basis={
            **reviewed.engine_decision_basis,
            "review_tier": {
                "decision_without_review_tier": reviewed.hook_decision,
                "host_asks_a_person": True,
            },
        },
        audit_targets=reviewed.audit_targets,
        audit_commands=reviewed.audit_commands,
        written_text_names_secret_file=reviewed.written_text_names_secret_file,
    )


def _host_asks_a_person(raw_hook_input: Mapping[str, Any]) -> bool:
    mode = raw_hook_input.get("permission_mode")
    return isinstance(mode, str) and mode in _MODES_WHERE_HOST_ASKS_A_PERSON


def _judge_file_or_command_call(
    raw_hook_input: Mapping[str, Any],
    hook_input: ClaudeCodePreToolUseInput,
    validation: PreToolUseInputValidationResult,
    ignored_reported_only_fields: Any,
    repo_root: str | Path,
    base_dir: Path,
    policy: HookPolicy,
) -> HookJudgmentEngineDecision:
    unnormalized_input = hook_input
    hook_input, path_normalization = _normalize_hook_input_repo_paths(
        hook_input, repo_root, base_dir
    )
    request = _build_request(raw_hook_input, hook_input, repo_root, base_dir)

    action_candidate = map_pretooluse_input_to_structured_action_candidate(
        hook_input, path_policy=policy.paths
    )
    classification = _classify_hook_target(hook_input, request.target_paths, policy)
    law_result = apply_law(classification)
    # The capability gate only knows the built-in secret names, so a path a
    # person approved in the project policy is judged by the other gates alone.
    engine_action = _engine_action_for_hook_input(
        hook_input,
        classification.risk_level,
        tuple(path for path in request.target_paths if not _secret_lifted_by_policy(path, policy)),
    )
    capability_result = evaluate_action_capabilities(engine_action, repo_root=repo_root)
    aeg_guard_records = _aeg_guard_records(repo_root, request.target_paths)
    repo_boundary_records = _repo_boundary_records(repo_root, request.target_paths)
    protected_path_gate = _protected_path_gate(hook_input, request.target_paths, repo_root, policy)
    bash_target_gate = _bash_write_delete_target_gate(hook_input, repo_root, base_dir, policy)
    powershell_target_gate = _powershell_write_delete_target_gate(hook_input, repo_root, base_dir, policy)
    shell_read_gate = _shell_read_only_gate(hook_input, repo_root, base_dir, policy)
    shell_file_gate = _shell_file_operation_gate(hook_input, repo_root, base_dir, policy)
    secret_reference_gate = _secret_reference_gate(hook_input, shell_read_gate, policy, repo_root, base_dir)
    approved_by_policy = _command_approved_by_policy(hook_input, action_candidate.reasons, policy, repo_root, base_dir)
    # An approved command runs project code. Once this session has written text that
    # names a secret file, that code may read it, so the approval goes back to a person.
    approval_held = approved_by_policy and secret_naming_writes(
        repo_root, raw_hook_input.get("session_id")
    ) != ()
    command_approved = approved_by_policy and not approval_held
    dangerous_bash_gate = {
        "risk_status": action_candidate.risk_status,
        "dangerous_bash": action_candidate.risk_status in {BASH_DANGEROUS, POWERSHELL_DANGEROUS},
        "unclassified_bash": (
            action_candidate.risk_status == BASH_NOT_CHECKED
            and not shell_read_gate.get("classified")
        ),
        "unclassified_bash_is_allow": False,
        "reasons": action_candidate.reasons,
    }

    basis = {
        "input_validation": _validation_record(validation),
        "tool_call_mapping": {
            "candidate_status": action_candidate.candidate_status,
            "candidate_action_type": action_candidate.candidate_action_type,
            "risk_status": action_candidate.risk_status,
            "declared_risk": action_candidate.declared_risk,
            "reasons": action_candidate.reasons,
            "protected_path_policy_source": "jangseung.classify.is_protected_path",
            "protected_path_policy_duplicated_in_hook": False,
        },
        "classification": classification.as_dict(),
        "law": law_result.as_dict(),
        "capability_gate": _capability_record(capability_result),
        "protected_path_gate": protected_path_gate,
        "aeg_guard": aeg_guard_records,
        "repo_boundary_gate": repo_boundary_records,
        "path_normalization": path_normalization,
        "bash_target_gate": bash_target_gate,
        "powershell_target_gate": powershell_target_gate,
        "shell_read_gate": shell_read_gate,
        "shell_file_gate": shell_file_gate,
        "secret_reference_gate": secret_reference_gate,
        "hook_policy": {
            "present": policy.present,
            "error": policy.error,
            "command_approved": command_approved,
            "approval_held": approval_held,
        },
        "dangerous_bash_gate": dangerous_bash_gate,
        "ignored_reported_only_fields": ignored_reported_only_fields,
        "reported_only_trusted_as_judgment_basis": False,
        "not_checked_is_allow": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }

    engine_decision, reasons = _collapse_engine_decision(
        candidate_action_type=action_candidate.candidate_action_type,
        law_status=law_result.status,
        capability_gate_result=capability_result.gate_result,
        action_candidate_status=action_candidate.candidate_status,
        action_risk_status=action_candidate.risk_status,
        aeg_guard_records=aeg_guard_records,
        repo_boundary_records=repo_boundary_records,
        classification=classification,
        bash_target_gate=bash_target_gate,
        powershell_target_gate=powershell_target_gate,
        shell_read_gate=shell_read_gate,
        protected_path_gate=protected_path_gate,
        secret_reference_gate=secret_reference_gate,
        command_approved=command_approved,
        approval_held=approval_held,
        shell_file_gate=shell_file_gate,
        action_reasons=action_candidate.reasons,
    )
    hook_decision = engine_decision
    if BASH_TRAILING_ESCAPE_REASON in action_candidate.reasons:
        reasons = (*reasons, BASH_TRAILING_ESCAPE_REASON)
    updated_tool_input = None
    if hook_input.tool_name == "Grep" and hook_decision != DENY:
        updated_tool_input = _grep_input_without_read_protected_files(raw_hook_input["tool_input"], policy)
    elif hook_decision == ALLOW and shell_read_gate.get("allow"):
        updated_tool_input = _git_input_without_read_protected_files(
            raw_hook_input["tool_input"], hook_input.tool_name, repo_root, base_dir, policy
        )
    return _build_decision(
        request=request,
        engine_decision=engine_decision,
        hook_decision=hook_decision,
        reasons=reasons,
        basis=basis,
        updated_tool_input=updated_tool_input,
        # PowerShell targets are named from the command's own words: once normalized,
        # a provider path such as HKCU:\x can no longer be told from a project path.
        audit_targets=_audit_targets(
            () if hook_input.tool_name == "PowerShell" else request.target_paths,
            (*bash_target_gate.get("targets", ()), *powershell_target_gate.get("targets", ())),
            repo_root,
            base_dir,
        ),
        audit_commands=_audit_commands(hook_input),
        # A denied write puts nothing on disk, so there is nothing to mark.
        written_text_names_secret_file=hook_decision != DENY and (
            _written_text_names_secret_file(unnormalized_input, request.target_paths, policy)
            or (hook_decision == ALLOW and _shell_file_operation_names_secret_file(hook_input, shell_file_gate, policy))
            or (
                hook_decision in {ASK, DEFER}
                and hook_input.tool_name in _COMMAND_TOOL_NAMES
                and _asked_shell_copy_names_secret_file(
                    hook_input, (bash_target_gate, powershell_target_gate), repo_root, base_dir, policy
                )
            )
        ),
        host_delegation_eligible=(
            hook_decision == DEFER and not policy.error
            and _host_execution_gate(hook_input, repo_root, base_dir, policy)
            and secret_naming_writes(repo_root, raw_hook_input.get("session_id")) == ()
        ),
    )


def _audit_targets(
    request_paths: Sequence[str],
    command_targets: Sequence[str],
    repo_root: str | Path,
    base_dir: str | Path,
) -> tuple[str, ...]:
    """Project-relative names of the files a call targets; nothing outside is named."""

    named: list[str] = []
    for path in request_paths:
        inside = _repo_relative_candidate(path) and not path.strip().startswith("~") and not is_host_resolved_path(path)
        named.append(path if inside else OUTSIDE_PROJECT_TARGET)
    for target in command_targets:
        text = target.strip()
        # The shell resolves these itself: a home folder, another drive's current
        # folder, a PowerShell provider such as HKCU:, an alternate data stream.
        shell_resolved = text.startswith("~") or (":" in text and not _looks_like_windows_absolute_path(text))
        try:
            normalized, record = _normalize_command_target(target, repo_root, base_dir)
        except Exception:  # noqa: BLE001 - a record must never fail the judgment.
            normalized, record = OUTSIDE_PROJECT_TARGET, {"in_repo": False}
        inside = record.get("in_repo") is True and not shell_resolved
        named.append(normalized if inside else OUTSIDE_PROJECT_TARGET)
    kept = [item if len(item) <= 240 else "<long-path>" for item in named]
    return tuple(dict.fromkeys(kept))[:_MAX_AUDIT_ITEMS]


def _audit_commands(hook_input: ClaudeCodePreToolUseInput) -> tuple[str, ...]:
    """Program names of a command, such as ``git push``; arguments are never kept."""

    command = hook_input.tool_input.get("command")
    if hook_input.tool_name not in _COMMAND_TOOL_NAMES or not isinstance(command, str):
        return ()
    try:
        if hook_input.tool_name == "PowerShell":
            argvs = powershell_argvs(command)
        else:
            scan = scan_bash_command(command)
            if scan.dynamic or scan.error is not None:
                # After a substitution the scanner cannot tell a program from an argument.
                return ("<dynamic>",)
            argvs = scan.argvs()
    except Exception:  # noqa: BLE001 - a record must never fail the judgment.
        return ("<unparsed>",)
    names: list[str] = []
    for argv in argvs:
        words = strip_assignments(argv)
        if not words:
            continue
        name = command_name(words[0])
        if (
            not _AUDIT_COMMAND_NAME.fullmatch(name)
            or sum(char.isdigit() for char in name) > _MAX_AUDIT_NAME_DIGITS
            or name.count("-") > _MAX_AUDIT_NAME_HYPHENS
            or not _written_bare_in_command_position(words[0], command)
        ):
            names.append("<other>")
            continue
        if name == "git":
            subcommand, _ = git_subcommand(words[1:])
            if subcommand in _AUDIT_GIT_SUBCOMMANDS:
                name = f"git {subcommand}"
        names.append(name)
    return tuple(dict.fromkeys(names))[:_MAX_AUDIT_ITEMS]


def _written_bare_in_command_position(word: str, command: str) -> bool:
    """True when ``word`` stands unquoted where a command starts in the raw text.

    A quoted string in command position is data, not a program, and the same word
    used elsewhere as an argument must not vouch for it.
    """

    starts_a_command = r"(?:^|[;|&({\n])[ \t]*(?:[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+)*"
    return re.search(starts_a_command + re.escape(word) + r"(?=$|[\s;|&)}<>])", command) is not None


def _written_text(hook_input: ClaudeCodePreToolUseInput) -> tuple[str, ...]:
    tool_input = hook_input.tool_input
    texts: tuple[Any, ...] = ()
    if hook_input.tool_name == "Write":
        texts = (tool_input.get("content"),)
    elif hook_input.tool_name == "Edit":
        texts = (tool_input.get("new_string"),)
    elif hook_input.tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if _is_sequence(edits):
            texts = tuple(edit.get("new_string") for edit in edits if isinstance(edit, Mapping))
    elif hook_input.tool_name == "NotebookEdit":
        texts = (tool_input.get("new_source"),)
    elif hook_input.tool_name == "apply_patch":
        command = tool_input.get("command")
        if isinstance(command, str):
            texts = tuple(line[1:] for line in command.splitlines() if line.startswith("+"))
    return tuple(text for text in texts if isinstance(text, str))


def _written_text_names_secret_file(
    hook_input: ClaudeCodePreToolUseInput,
    target_paths: Sequence[str],
    policy: HookPolicy,
) -> bool:
    """True when a write to a non-documentation file names a secret file such as ``.env``.

    This reads names, not behavior. Text that builds the name from pieces passes.
    """

    if hook_input.tool_name not in _WRITE_LIKE_TOOL_NAMES:
        return False
    if target_paths and all(is_prose_path(path) for path in target_paths):
        return False
    return _text_names_secret_file(_written_text(hook_input), policy)


def _shell_file_operation_names_secret_file(
    hook_input: ClaudeCodePreToolUseInput,
    shell_file_gate: Mapping[str, Any],
    policy: HookPolicy,
) -> bool:
    """The same check for an allowed shell file operation that leaves a non-documentation file.

    ``mv plan.md run.py`` turns text no one marked, because it went to a document,
    into a file a command may run; ``cp`` does the same and ``echo ... > f`` writes text.
    """

    operation = shell_file_gate.get("operation")
    paths = shell_file_gate.get("paths", ())
    if not shell_file_gate.get("allow") or operation not in {"cp", "mv", "write"} or not paths:
        return False
    source, destination = Path(paths[0]), Path(paths[-1])
    if is_prose_path(destination.name):
        return False
    if operation == "write":
        command = hook_input.tool_input.get("command")
        return isinstance(command, str) and _text_names_secret_file((command,), policy)
    return _file_names_secret_file(source, policy)


def _file_names_secret_file(path: Path, policy: HookPolicy) -> bool:
    """Whether a project file's content names a secret file; unreadable or large counts as yes."""

    try:
        if path.stat().st_size > _MAX_COPIED_BYTES_SCANNED:
            return True
        data = path.read_bytes()
    except OSError:
        return True
    texts = [data.decode("utf-8", errors="replace")]
    if b"\x00" in data:
        # PowerShell runs UTF-16 scripts; read them as text too.
        texts += [data.decode(encoding, errors="replace") for encoding in ("utf-16-le", "utf-16-be")]
    return any(_text_names_secret_file((text,), policy) for text in texts)


def _asked_shell_copy_names_secret_file(
    hook_input: ClaudeCodePreToolUseInput,
    target_gates: Sequence[Mapping[str, Any]],
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> bool:
    """For a shell command a person is asked about: does it put named content into a runnable file?

    ``cp -f plan.md conftest.py`` or ``cat plan.md > conftest.py`` asks, and the person
    sees only names. If a project file the command names holds a secret file name and
    a write target is not prose, mark the session, as an allowed copy would.
    """

    targets = [target for gate in target_gates for target in gate.get("targets", ())]
    if not targets or all(is_prose_path(target) for target in targets):
        return False
    command = hook_input.tool_input.get("command")
    if not isinstance(command, str):
        return False
    words = (
        powershell_words(command)
        if hook_input.tool_name == "PowerShell"
        else tuple(bash_words(scan_bash_command(command)))
    )
    checked = 0
    for word in dict.fromkeys(words):
        if word.startswith("-") or word in targets:
            continue
        try:
            if _classify_command_target(word, repo_root, base_dir, policy) != "safe_in_repo":
                continue
            source = _canonical_command_target(word, repo_root, base_dir)
            if not source.is_file():
                continue
        except (OSError, ValueError):
            continue
        checked += 1
        if checked > _MAX_ASKED_SOURCES_CHECKED or _file_names_secret_file(source, policy):
            return True
    return False


def _text_names_secret_file(texts: Sequence[str], policy: HookPolicy) -> bool:
    if sum(len(text) for text in texts) > _MAX_WRITTEN_TEXT_SCANNED:
        # Text past the limit is not read. Marking costs a question; missing costs more.
        return True
    scanned = 0
    words: set[str] = set()
    for text in texts:
        piece = text[: _MAX_WRITTEN_TEXT_SCANNED - scanned]
        scanned += len(piece)
        words.update(_WRITTEN_TEXT_SEPARATORS.split(piece))
        if scanned >= _MAX_WRITTEN_TEXT_SCANNED:
            break
    words.discard("")
    if len(words) > _MAX_WRITTEN_WORDS_CHECKED:
        # Too much to read within a hook call. Marking costs a question; missing costs more.
        return True
    return any(names_secret_file(word, policy.paths) for word in words)


def _judge_mcp_tool_call(
    raw_hook_input: Mapping[str, Any],
    hook_input: ClaudeCodePreToolUseInput,
    validation: PreToolUseInputValidationResult,
    ignored_reported_only_fields: Any,
    repo_root: str | Path,
    working_dir: str | Path | None,
) -> HookJudgmentEngineDecision:
    """MCP calls are judged by name and the project policy; arguments are never read."""

    base_dir = _effective_working_dir(hook_input, repo_root, working_dir)
    policy = load_hook_policy(repo_root, base_dir)
    gate = judge_mcp_tool_call(hook_input.tool_name, policy)
    basis = {
        "input_validation": _validation_record(validation),
        "mcp_tool_gate": gate.to_record(),
        "hook_policy": {"present": policy.present, "error": policy.error},
        "ignored_reported_only_fields": ignored_reported_only_fields,
        "reported_only_trusted_as_judgment_basis": False,
        "not_checked_is_allow": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }
    return _build_decision(
        request=_build_request(raw_hook_input, hook_input, repo_root, base_dir),
        engine_decision=gate.hook_decision,
        hook_decision=gate.hook_decision,
        reasons=gate.reasons,
        basis=basis,
    )


def _grep_input_without_read_protected_files(
    tool_input: Mapping[str, Any],
    policy: HookPolicy,
) -> dict[str, Any]:
    """Return a Grep input that leaves read-protected files out of any walk.

    A walk's files cannot be judged from the request: a glob of the call's own,
    such as ``.en*``, overrides ``.gitignore`` as well. The exclusions go last
    because ripgrep lets the last matching glob win. They are added even when
    ``path`` looks like a file: ripgrep ignores globs for a file it is handed, so
    nothing is lost, and the walk stays covered if that reading of ``path`` is wrong.
    """

    own_glob = tool_input.get("glob")
    own_globs = (own_glob,) if _is_non_empty_string(own_glob) else ()
    return {**tool_input, "glob": " ".join((*own_globs, *search_exclusion_globs(policy.paths)))}


def _git_input_without_read_protected_files(
    tool_input: Mapping[str, Any],
    tool_name: str,
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> dict[str, Any] | None:
    """Return a command input whose git output leaves read-protected files out.

    Which files such a command prints cannot be judged from the request: ``git log -p``
    reaches whatever history holds, and a file named today may be a folder in the past.
    """

    command = tool_input["command"]
    output = classify_shell_read(command, tool_name=tool_name).git_output
    if output is None:
        return None
    named = tuple(argument for argument in output.arguments if _names_an_existing_path(argument, repo_root, base_dir))
    paths = (*named, *output.paths)
    revisions = tuple(argument for argument in output.arguments if argument not in named)
    files = tuple(path for path in paths if _readable_file_verdict(path, repo_root, base_dir) == "readable")
    exclusions = git_exclusion_pathspecs(policy.paths, named_files=files) if output.prints_file_content else ()
    rebuilt = git_output_command(command, output, revisions=revisions, paths=paths, exclusions=exclusions)
    return None if rebuilt is None else {**tool_input, "command": rebuilt}


def _names_an_existing_path(argument: str, repo_root: str | Path, base_dir: str | Path) -> bool:
    try:
        return _canonical_command_target(argument, repo_root, base_dir).exists()
    except (OSError, ValueError):
        return False


# tool_input fields that carry a repo file path.
_PATH_TOOL_INPUT_FIELDS = ("file_path", "notebook_path", "path")
_WINDOWS_DRIVE_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")


def _effective_working_dir(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    working_dir: str | Path | None,
) -> Path:
    """Directory relative targets resolve against; the host reports it per call."""

    default = Path(repo_root if working_dir is None else working_dir)
    reported = hook_input.cwd
    if isinstance(reported, str):
        try:
            candidate = default / reported
            if candidate.is_dir():
                return candidate
        except (OSError, ValueError):
            pass
    return default


def _normalize_hook_input_repo_paths(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    base_dir: str | Path,
) -> tuple[ClaudeCodePreToolUseInput, tuple[Mapping[str, Any], ...]]:
    """Rewrite repo-internal file paths in tool_input to canonical repo-relative.

    Repo-external, traversal-escaping, and symlink-escaping paths are left in a
    form the existing scope defense still rejects, and a relative path holding
    ``..`` is left unchanged so relative traversal stays rejected.
    """

    tool_input = dict(hook_input.tool_input)
    records: list[Mapping[str, Any]] = []
    changed = False
    if hook_input.tool_name in {"Grep", "Glob"} and not _is_non_empty_string(tool_input.get("path")):
        # A search without a path covers the session's working directory.
        tool_input["path"] = "."
        changed = True
    for field_name in _PATH_TOOL_INPUT_FIELDS:
        value = tool_input.get(field_name)
        if not _is_non_empty_string(value):
            continue
        normalized, record = _normalize_repo_internal_path(value, repo_root, base_dir)
        records.append({"field": field_name, **record})
        if normalized != value:
            tool_input[field_name] = normalized
            changed = True
    if hook_input.tool_name == "apply_patch" and _is_non_empty_string(tool_input.get("command")):
        judged = _patch_with_repo_relative_targets(tool_input["command"], repo_root, base_dir)
        if judged != tool_input["command"]:
            records.append({"field": "command", "action": "apply_patch_absolute_targets_judged_repo_relative"})
            tool_input["command"] = judged
            changed = True

    if not changed:
        return hook_input, tuple(records)
    return replace(hook_input, tool_input=tool_input), tuple(records)


def _patch_with_repo_relative_targets(
    command: str,
    repo_root: str | Path,
    base_dir: str | Path,
) -> str:
    """Return the patch text to judge, with absolute targets in the project made relative.

    Only this machine's own absolute form counts. Codex would not read ``/c/x`` as
    ``C:\\x`` the way the resolver here does, so any other form stays as written and
    is refused. The hook returns no new input for a patch, so Codex still applies
    the text it wrote; this changes what is judged, the same file under its project name.
    """

    def judged_path(path: str) -> str:
        if os.name == "nt":
            native_absolute = _WINDOWS_DRIVE_ABSOLUTE.match(path) is not None
        else:
            native_absolute = path.startswith("/") and not path.startswith("//")
        if not native_absolute:
            return path
        normalized, record = _normalize_repo_internal_path(path, repo_root, base_dir)
        return normalized if record["in_repo"] is True and normalized != "." else path

    return rewrite_apply_patch_targets(command, judged_path)


def _normalize_repo_internal_path(
    path_value: str,
    repo_root: str | Path,
    base_dir: str | Path,
) -> tuple[str, dict[str, Any]]:
    if is_host_resolved_path(path_value):
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": False,
            "in_repo": None,
            "action": "host_resolved_path_unchanged_for_rejection",
        }

    cleaned = strip_path_decorations(path_value)
    was_absolute = cleaned.startswith("/") or _looks_like_windows_absolute_path(cleaned)

    if not was_absolute and ".." in _path_parts(cleaned):
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": False,
            "in_repo": None,
            "action": "relative_traversal_unchanged_for_rejection",
        }

    candidate = cleaned if was_absolute else str(Path(base_dir) / cleaned)
    try:
        resolution = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=candidate,
        )
    except Exception:  # noqa: BLE001 - normalization failure keeps the submitted path (fail-closed).
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": was_absolute,
            "in_repo": None,
            "action": "normalization_error_kept_submitted_path_fail_closed",
        }

    if not resolution.target_under_repo:
        return candidate, {
            "original": path_value,
            "normalized": candidate,
            "was_absolute": was_absolute,
            "in_repo": False,
            "action": "outside_repo_kept_absolute_for_scope_rejection",
        }

    try:
        normalized = _repo_relative_posix_from_resolution(resolution) or "."
    except Exception:  # noqa: BLE001 - keep absolute on any relativization error.
        return candidate, {
            "original": path_value,
            "normalized": candidate,
            "was_absolute": was_absolute,
            "in_repo": True,
            "action": "relative_computation_error_kept_absolute_fail_closed",
        }

    return normalized, {
        "original": path_value,
        "normalized": normalized,
        "was_absolute": was_absolute,
        "in_repo": True,
        "action": (
            "repo_internal_absolute_normalized_to_relative"
            if was_absolute
            else "repo_internal_relative_path_canonicalized"
        ),
    }


def _repo_relative_posix_from_resolution(resolution: Any) -> str:
    if _looks_like_windows_absolute_path(resolution.repo_root) or _looks_like_windows_absolute_path(
        resolution.canonical_target
    ):
        relative = PureWindowsPath(resolution.canonical_target).relative_to(
            PureWindowsPath(resolution.repo_root)
        )
        return relative.as_posix()

    relative = Path(resolution.canonical_target).relative_to(Path(resolution.repo_root))
    return relative.as_posix()


def _build_request(
    raw_hook_input: Mapping[str, Any],
    hook_input: ClaudeCodePreToolUseInput | None,
    repo_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> HookJudgmentEngineRequest:
    tool_input = hook_input.tool_input if hook_input is not None else {}
    target_paths = _target_paths(hook_input)
    if hook_input is not None and repo_root is not None and base_dir is not None and (
        hook_input.tool_name in {"apply_patch", "PowerShell"}
    ):
        # These targets come from inside the patch or command text, so they were
        # not canonicalized with the tool_input path fields.
        target_paths = tuple(
            dict.fromkeys(
                _normalize_repo_internal_path(path, repo_root, base_dir)[0]
                for path in target_paths
            )
        )
    return HookJudgmentEngineRequest(
        tool_name=hook_input.tool_name if hook_input is not None else _string_or_none(raw_hook_input.get("tool_name")),
        tool_use_id=(
            hook_input.tool_use_id
            if hook_input is not None
            else _string_or_none(raw_hook_input.get("tool_use_id"))
        ),
        target_paths=target_paths,
        command_present=isinstance(tool_input.get("command"), str),
        raw_hook_input_hash=_sha256_json(raw_hook_input),
    )


def _target_paths(hook_input: ClaudeCodePreToolUseInput | None) -> tuple[str, ...]:
    if hook_input is None:
        return tuple()
    if hook_input.tool_name in {"Read", "Write", "Edit", "MultiEdit"}:
        file_path = hook_input.tool_input.get("file_path")
        if isinstance(file_path, str) and file_path.strip():
            return (file_path,)
    if hook_input.tool_name == "NotebookEdit":
        notebook_path = hook_input.tool_input.get("notebook_path")
        if isinstance(notebook_path, str) and notebook_path.strip():
            return (notebook_path,)
    if hook_input.tool_name in {"Grep", "Glob"}:
        search_path = hook_input.tool_input.get("path")
        return (search_path if isinstance(search_path, str) and search_path.strip() else ".",)
    if hook_input.tool_name == "apply_patch":
        command = hook_input.tool_input.get("command")
        if isinstance(command, str) and command.strip():
            extraction = extract_apply_patch_targets(command)
            if not extraction.parse_ambiguous:
                return extraction.target_paths
    if hook_input.tool_name == "PowerShell":
        command = hook_input.tool_input.get("command")
        if isinstance(command, str) and command.strip():
            extraction = extract_powershell_write_delete_targets(command)
            if not extraction.parse_ambiguous:
                return extraction.write_delete_targets
    return tuple()


def _classify_hook_target(
    hook_input: ClaudeCodePreToolUseInput,
    target_paths: tuple[str, ...],
    policy: HookPolicy,
):
    def write_check(path: str) -> bool:
        return is_protected_path(path, policy.paths)

    def read_check(path: str) -> bool:
        return is_read_protected_path(path, policy.paths)

    if hook_input.tool_name == "Bash":
        return classify_task(
            "run command through Claude Code Bash tool",
            changed_files=[],
            changed_files_source=NOT_CHECKED_SOURCE,
            no_mutation=False,
        )
    if hook_input.tool_name == "PowerShell":
        return classify_task(
            "run command through Claude Code PowerShell tool",
            changed_files=target_paths,
            changed_files_source=GIT_WORKING_TREE if target_paths else NOT_CHECKED_SOURCE,
            no_mutation=not target_paths,
            protected_check=write_check,
        )

    read_like = hook_input.tool_name in _READ_LIKE_TOOL_NAMES
    intent_text = "update documentation"
    if read_like:
        intent_text = "read documentation"
    elif hook_input.tool_name == "apply_patch":
        intent_text = "apply patch file update"
    return classify_task(
        intent_text,
        changed_files=target_paths,
        changed_files_source=GIT_WORKING_TREE if target_paths else NOT_CHECKED_SOURCE,
        no_mutation=read_like,
        protected_check=read_check if read_like else write_check,
    )


def _secret_lifted_by_policy(path: str, policy: HookPolicy) -> bool:
    return is_secret_path(path) and not is_secret_path(path, policy.paths)


def _engine_action_for_hook_input(
    hook_input: ClaudeCodePreToolUseInput,
    declared_risk: str,
    target_paths: tuple[str, ...],
) -> dict[str, Any]:
    if hook_input.tool_name in _READ_LIKE_TOOL_NAMES:
        action_type = REQUEST_REPO_READ
        capabilities = ["read_repo"]
    elif hook_input.tool_name in _WRITE_LIKE_TOOL_NAMES:
        action_type = WRITE_FILE
        capabilities = ["write_file"]
    elif hook_input.tool_name in _COMMAND_TOOL_NAMES:
        action_type = RUN_COMMAND
        capabilities = ["run_command"]
    else:
        action_type = NOOP
        capabilities = ["noop"]

    return {
        "action_type": action_type,
        "action_id": f"phase11c8:{hook_input.tool_use_id}",
        "declared_intent": f"Claude Code {hook_input.tool_name} PreToolUse judgment",
        "declared_risk": declared_risk,
        "capability_requirements": capabilities,
        "target_scope": {
            "repo_relative": all(_repo_relative_candidate(path) for path in target_paths),
            "target_paths": list(target_paths),
        },
        "payload": {
            "request_kind": "claude_code_pretooluse_engine_judgment",
            "tool_name": hook_input.tool_name,
        },
    }


def _bash_write_delete_target_gate(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> dict[str, Any]:
    """Deny a Bash command with a literal write/delete target that is protected
    or outside the repo, even when another part of the command cannot be parsed.
    Finding no target proves nothing: the decision then stays with the ask/defer
    path and is never promoted to allow."""

    if hook_input.tool_name != "Bash":
        return {
            "applicable": False,
            "deny": False,
            "parse_ambiguous": False,
            "targets": tuple(),
            "deny_targets": tuple(),
            "reason": "not_a_bash_tool_call",
        }

    command = hook_input.tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return {
            "applicable": True,
            "deny": False,
            "parse_ambiguous": True,
            "targets": tuple(),
            "deny_targets": tuple(),
            "reason": "missing_or_empty_command",
        }

    extraction = extract_bash_write_delete_targets(command)
    deny_targets: list[dict[str, str]] = []
    for target in extraction.write_delete_targets:
        kind = _classify_bash_target(target, repo_root, base_dir, policy)
        if kind == "safe_in_repo" and target in extraction.delete_targets:
            kind = _classify_deleted_directory(target, repo_root, base_dir)
        if kind in _COMMAND_TARGET_DENY_KINDS:
            deny_targets.append({"target": target, "kind": kind})

    return {
        "applicable": True,
        "deny": bool(deny_targets),
        "parse_ambiguous": extraction.parse_ambiguous,
        "targets": extraction.write_delete_targets,
        "deny_targets": tuple(deny_targets),
        "protected_path_policy_source": "jangseung.classify.is_protected_path",
        "repo_boundary_policy_source": (
            "jangseung.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path"
        ),
        "reason": (
            f"bash_target_unparseable_maps_to_ask_defer_not_allow:{extraction.reason}"
            if extraction.parse_ambiguous
            else extraction.reason
        ),
    }


def _powershell_write_delete_target_gate(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> dict[str, Any]:
    """Deny a PowerShell command whose structurally-parsed write/delete target
    is protected or outside the repo. Ambiguous PowerShell remains ask/defer
    unless a parsed target is already clearly denied."""

    if hook_input.tool_name != "PowerShell":
        return {
            "applicable": False,
            "deny": False,
            "parse_ambiguous": False,
            "read_only": False,
            "targets": tuple(),
            "target_operations": tuple(),
            "deny_targets": tuple(),
            "reason": "not_a_powershell_tool_call",
        }

    command = hook_input.tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return {
            "applicable": True,
            "deny": False,
            "parse_ambiguous": True,
            "read_only": False,
            "targets": tuple(),
            "target_operations": tuple(),
            "deny_targets": tuple(),
            "reason": "missing_or_empty_command",
        }

    extraction = extract_powershell_write_delete_targets(command)
    deny_targets: list[dict[str, str]] = []
    for target in extraction.write_delete_targets:
        kind = _classify_command_target(target, repo_root, base_dir, policy)
        if kind == "safe_in_repo" and ("delete", target) in extraction.target_operations:
            kind = _classify_deleted_directory(target, repo_root, base_dir)
        if kind in _COMMAND_TARGET_DENY_KINDS:
            deny_targets.append({"target": target, "kind": kind})

    return {
        "applicable": True,
        "deny": bool(deny_targets),
        "parse_ambiguous": extraction.parse_ambiguous,
        "read_only": extraction.read_only,
        "targets": extraction.write_delete_targets,
        "target_operations": extraction.target_operations,
        "deny_targets": tuple(deny_targets),
        "protected_path_policy_source": "jangseung.classify.is_protected_path",
        "repo_boundary_policy_source": (
            "jangseung.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path"
        ),
        "reason": extraction.reason,
    }


def _classify_bash_target(
    target: str,
    repo_root: str | Path,
    base_dir: str | Path | None = None,
    policy: HookPolicy | None = None,
) -> str:
    return _classify_command_target(target, repo_root, base_dir, policy)


def _classify_command_target(
    target: str,
    repo_root: str | Path,
    base_dir: str | Path | None = None,
    policy: HookPolicy | None = None,
) -> str:
    path_policy = policy.paths if policy is not None else None
    if is_secret_path(target, path_policy):
        return "secret_path"
    if target.strip().startswith("~") or is_host_resolved_path(target):
        return "out_of_scope"

    normalized, record = _normalize_command_target(target, repo_root, base_dir)
    if record["in_repo"] is False:
        return "out_of_scope"

    try:
        resolution = resolve_repo_boundary_path(repo_root=repo_root, submitted_target=normalized)
    except Exception:  # noqa: BLE001 - unresolvable target -> do not deny, leave to ask/defer.
        return "unresolvable_ambiguous"

    if resolution.target_outside_repo:
        return "out_of_scope"

    try:
        relative = _repo_relative_posix_from_resolution(resolution)
    except Exception:  # noqa: BLE001 - keep fail-closed to ask/defer, not a claimed deny.
        return "unresolvable_ambiguous"

    if is_secret_path(relative, path_policy):
        return "secret_path"

    try:
        guard = decide_b1_aeg_integrity_guard(repo_root=repo_root, submitted_path=normalized)
    except Exception:  # noqa: BLE001
        return "unresolvable_ambiguous"
    if getattr(guard, "protected_target", False):
        return "protected_state_dir"

    if is_protected_path(relative, path_policy) or _is_guard_runtime_target(relative, repo_root):
        return "protected_path"

    return "safe_in_repo"


def _normalize_command_target(
    target: str,
    repo_root: str | Path,
    base_dir: str | Path | None,
) -> tuple[str, dict[str, Any]]:
    """A shell resolves ``..`` from its own directory, so here it stays meaningful."""

    base = Path(repo_root if base_dir is None else base_dir)
    cleaned = strip_path_decorations(target)
    if not (cleaned.startswith("/") or _looks_like_windows_absolute_path(cleaned)):
        cleaned = str(base / cleaned)
    return _normalize_repo_internal_path(cleaned, repo_root, base)


def _classify_deleted_directory(
    target: str,
    repo_root: str | Path,
    base_dir: str | Path | None,
) -> str:
    normalized, _ = _normalize_command_target(target, repo_root, base_dir)
    return "protected_path" if contains_protected_path(normalized) else "safe_in_repo"


def _guard_runtime_roots() -> tuple[Path, ...]:
    """Directories the running hook executes from, such as a venv in the project."""

    return (Path(__file__).resolve().parents[1], Path(sys.prefix).resolve())


def _is_guard_runtime_target(target: str, repo_root: str | Path) -> bool:
    try:
        resolved = (Path(repo_root) / target).resolve(strict=False)
        return any(
            resolved == root or root in resolved.parents
            for root in (Path(item).resolve(strict=False) for item in _guard_runtime_roots())
        )
    except (OSError, ValueError):
        return False


def _is_clearly_safe_normal_file_operation(
    *,
    candidate_action_type: str,
    action_candidate_status: str,
    classification: Classification,
    repo_boundary_records: tuple[Mapping[str, Any], ...],
) -> bool:
    """Return True only for a Read/Write/Edit of a repo-internal, non-protected
    file that the existing engine classified as a definite LOW/MEDIUM change.

    Fail-closed: anything ambiguous (Bash, NOT_CHECKED impact, non-candidate
    mapping status, or any out-of-repo boundary record) returns False and is
    left to the ask/defer/deny paths.
    """

    if candidate_action_type not in _CLEARLY_SAFE_FILE_ACTION_TYPES:
        return False
    if action_candidate_status != STRUCTURED_ACTION_CANDIDATE:
        return False
    if classification.risk_level not in _CLEARLY_SAFE_RISK_LEVELS:
        return False
    if classification.impact_risk not in _CLEARLY_SAFE_IMPACT_RISKS:
        return False
    if not repo_boundary_records:
        return False
    if any(record.get("target_outside_repo") is True for record in repo_boundary_records):
        return False
    if not all(record.get("target_under_repo") is True for record in repo_boundary_records):
        return False
    return True


def _shell_read_only_gate(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> dict[str, Any]:
    if hook_input.tool_name not in _COMMAND_TOOL_NAMES:
        return {"classified": False, "allow": False, "deny": False}
    extraction = classify_shell_read(
        hook_input.tool_input.get("command"), tool_name=hook_input.tool_name,
    )
    if not extraction.classified:
        return {"classified": False, "allow": False, "deny": False}

    def kind(path: str) -> str:
        return _classify_command_target(path, repo_root, base_dir, policy)

    verdicts: list[str] = []
    for path in extraction.paths:
        verdict = kind(path)
        if verdict in {"safe_in_repo", "protected_path"}:
            verdict = _readable_file_verdict(path, repo_root, base_dir)
        verdicts.append(verdict)
    for path in (*extraction.tree_paths, *extraction.compared_paths):
        verdict = kind(path)
        verdicts.append("readable" if verdict in {"safe_in_repo", "protected_path"} else verdict)
    if extraction.compared_paths and _compares_a_directory(extraction.compared_paths, repo_root, base_dir):
        verdicts.append("directory_comparison")
    if extraction.runs_git and not _git_uses_a_guarded_repository(base_dir):
        verdicts.append("unguarded_git_directory")
    if extraction.git_output is not None and not extraction.git_output.can_be_narrowed:
        verdicts.append("git_output_cannot_be_narrowed")
    # The host runs the command in the folder it reports, which can be another
    # repository (Codex's workdir), and a form naming no path says nothing about it.
    for path in (".", *extraction.metadata_paths):
        # Names and attributes do not expose a secret's content. State stays
        # with a person because listing it serves no ordinary work.
        verdict = kind(path)
        if verdict in {"safe_in_repo", "protected_path", "secret_path"}:
            verdicts.append("readable")
        else:
            verdicts.append("metadata_of_state" if verdict == "protected_state_dir" else verdict)
    return {
        "classified": True,
        "allow": all(verdict == "readable" for verdict in verdicts),
        "deny": any(verdict in _SHELL_READ_DENY_KINDS for verdict in verdicts),
        "path_verdicts": tuple(verdicts),
    }


def _shell_file_operation_gate(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> dict[str, Any]:
    operation = classify_shell_file_operation(hook_input.tool_input.get("command"), tool_name=hook_input.tool_name)
    if operation is None or policy.error:
        return {"allow": False}
    if _classify_command_target(".", repo_root, base_dir, policy) != "safe_in_repo":
        return {"allow": False}
    targets = []
    root = Path(repo_root).resolve()
    # The trusted project root itself may have an OS alias (macOS /var ->
    # /private/var). Canonicalize that prefix only, not links below the root:
    # resolving the whole working directory would hide an in-project link.
    raw_base = Path(base_dir).absolute()
    for spelling in (Path(repo_root).absolute(), root):
        try:
            base = root / raw_base.relative_to(spelling)
            break
        except ValueError:
            continue
    else:
        return {"allow": False}
    for path in operation.paths:
        if _classify_command_target(path, repo_root, base_dir, policy) != "safe_in_repo":
            return {"allow": False}
        target = base / path
        # A copy/move through a link may reach a different file; hard links can
        # overwrite a secret under another name. Do not grant either case here.
        for part in (target, *target.parents):
            try:
                attributes = getattr(part.lstat(), "st_file_attributes", 0)
            except (FileNotFoundError, NotADirectoryError):
                attributes = 0
            # st_file_attributes also covers Windows junctions on Python 3.10,
            # which does not yet provide Path.is_junction().
            if part.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                return {"allow": False}
            if part == root:
                break
        if target.is_file() and target.stat().st_nlink != 1:
            return {"allow": False}
        targets.append(target)
    if operation.operation == "mkdir":
        allowed = all(not target.exists() or target.is_dir() for target in targets)
    elif operation.operation in {"touch", "write"}:
        allowed = all(not target.exists() or target.is_file() for target in targets)
    elif operation.operation in {"cp", "mv"}:
        source, destination = targets
        allowed = source.is_file() and (not destination.exists() or destination.is_file())
    else:  # rm: one existing regular file, never a directory or a recursive form.
        allowed = targets[0].is_file()
    return {"allow": allowed, "operation": operation.operation, "paths": tuple(str(target) for target in targets)}


def _host_execution_gate(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
) -> bool:
    command = hook_input.tool_input.get("command")
    if hook_input.tool_name not in _COMMAND_TOOL_NAMES or not host_execution_candidate(command):
        return False
    if _classify_command_target(".", repo_root, base_dir, policy) != "safe_in_repo":
        return False
    words = plain_command_words(command)
    if words[0] == "git" and not _git_uses_a_guarded_repository(base_dir):
        return False
    # Do not hand literal secret, guard, review or external paths to the host.
    # A flag's value is a possible path too; unknown shell syntax never got here.
    for word in words[1:]:
        candidate = word.partition("=")[2] if "=" in word else word
        if candidate.startswith("-"):
            if any(char in candidate for char in "/:") or ".." in candidate:
                return False
            continue
        if candidate and _classify_command_target(candidate, repo_root, base_dir, policy) != "safe_in_repo":
            return False
    return True


def _canonical_command_target(path: str, repo_root: str | Path, base_dir: str | Path) -> Path:
    normalized, _ = _normalize_command_target(path, repo_root, base_dir)
    return Path(resolve_repo_boundary_path(repo_root=repo_root, submitted_target=normalized).canonical_target)


def _readable_file_verdict(path: str, repo_root: str | Path, base_dir: str | Path) -> str:
    try:
        return "readable" if _canonical_command_target(path, repo_root, base_dir).is_file() else "not_a_regular_file"
    except (OSError, ValueError):
        return "unresolvable_ambiguous"


def _compares_a_directory(paths: tuple[str, ...], repo_root: str | Path, base_dir: str | Path) -> bool:
    """``git diff a b [pathspec]`` walks directories, secrets included, without a usable repository.

    That also covers a ``.git`` it refuses over ownership, so its presence proves
    nothing here. An argument naming no path is a revision, as in ``HEAD -- docs``.
    """

    try:
        targets = [_canonical_command_target(path, repo_root, base_dir) for path in paths[:2]]
        return all(target.exists() for target in targets) and any(target.is_dir() for target in targets)
    except (OSError, ValueError):
        return True


def _git_uses_a_guarded_repository(start: str | Path) -> bool:
    """False unless git takes its config from a ``.git``, which agents cannot write.

    Agents can write ``HEAD`` and ``config`` anywhere else. git walks up the same way
    and accepts such a directory as a repository; its config can name programs that
    ``git status`` runs, so a read-only form proves nothing without this.
    """

    try:
        current = Path(start).resolve()
        for directory in (current, *current.parents):
            if (directory / ".git").exists():
                return True
            if (directory / "HEAD").exists():
                return False
    except OSError:
        pass
    return False


def _secret_reference_gate(
    hook_input: ClaudeCodePreToolUseInput,
    shell_read_gate: Mapping[str, Any],
    policy: HookPolicy,
    repo_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Deny an unproven command that names a secret path as a literal argument.

    A command in the read grammar is judged by its parsed paths instead, which
    is what lets ``grep .env README.md`` search for text without being denied.
    The matched values are not recorded here, so they cannot reach any output.
    """

    command = hook_input.tool_input.get("command")
    if (
        hook_input.tool_name not in _COMMAND_TOOL_NAMES
        or shell_read_gate.get("classified")
        or not isinstance(command, str)
    ):
        return {"applicable": False, "deny": False, "reference_count": 0}
    words = (
        powershell_words(command)
        if hook_input.tool_name == "PowerShell"
        else tuple(bash_words(scan_bash_command(command)))
    )
    if hook_input.tool_name != "PowerShell":
        # ``cat .en{v,x}`` reaches the file without spelling its name.
        braced = [word for word in dict.fromkeys(words) if "{" in word][:_MAX_BRACE_WORDS_EXPANDED]
        words = (*words, *(expanded for word in braced for expanded in brace_expansions(word)))
    references = secret_references(words, policy=policy.paths)
    glob_matches = 0
    if not references and repo_root is not None and base_dir is not None:
        glob_matches = _wildcards_reaching_secret_files(
            _command_segments(command, hook_input.tool_name), words, repo_root, base_dir, policy,
            windows_style=hook_input.tool_name == "PowerShell",
            include_hidden=hook_input.tool_name == "PowerShell" or "dotglob" in words,
            substitutes="$" in command or "`" in command,
        )
    return {
        "applicable": True,
        "deny": bool(references) or glob_matches > 0,
        "reference_count": len(references) + glob_matches,
    }


_MAX_GLOB_WORDS_CHECKED = 32
_MAX_GLOB_FULL_JUDGMENTS = 48
_MAX_BRACE_WORDS_EXPANDED = 32
_MAX_GLOB_FOLDERS = 5
_MAX_GLOB_SEGMENTS = 64
_MAX_GLOB_ASSIGNMENTS = 16
_DIRECTORY_CHANGE_COMMANDS = frozenset({"cd", "pushd", "chdir", "set-location", "push-location", "sl"})
_ASSIGNMENT_WORD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.+)", re.DOTALL)
_ASSIGNING_COMMANDS = frozenset({"export", "declare", "typeset", "local", "readonly"})
_SHELL_KEYWORDS = frozenset({"if", "then", "else", "elif", "do", "while", "until", "!", "time", "{", "("})
_NAME_PASSING_PROGRAMS = frozenset({"xargs", "parallel"})
_POWERSHELL_FILE_LISTERS = frozenset(
    {"get-item", "gi", "get-childitem", "gci", "ls", "dir", "resolve-path", "rvpa", "get-itemproperty"}
)
_FILE_SUBSTITUTION = re.compile(r"\$\(<[ \t]*([^\s()]{1,512})\)")
_MAX_SUBSTITUTION_WORD = 4096


def _command_segments(command: str, tool_name: str, depth: int = 0) -> list[tuple[str, ...]]:
    """Each simple command of ``command`` as its own word list, nested shells included."""

    argvs = powershell_argvs(command) if tool_name == "PowerShell" else scan_bash_command(command).argvs()
    segments: list[tuple[str, ...]] = []
    for argv in argvs:
        if len(segments) >= _MAX_GLOB_SEGMENTS:
            break
        segments.append(tuple(argv))
        if depth < 4:
            for payload in nested_shell_payloads(argv):
                segments.extend(_command_segments(payload, tool_name, depth + 1))
    return segments[:_MAX_GLOB_SEGMENTS]


def _wildcards_reaching_secret_files(
    segments: Sequence[Sequence[str]],
    words: Sequence[str],
    repo_root: str | Path,
    base_dir: str | Path,
    policy: HookPolicy,
    *,
    windows_style: bool,
    include_hidden: bool,
    substitutes: bool = True,
) -> int:
    """How many wildcard words hand a command a secret file that exists now.

    ``cat .en?`` names no secret file as text, but the shell hands ``cat`` the file.
    Each pattern is matched against the real folder, so ``wc -l *.py`` beside a
    ``.env`` is not caught. Three limits keep this from stopping ordinary work or
    being turned against the hook:

    * Only folders inside the project are listed, and the listing has a fixed
      budget for the whole call.
    * A bare ``*`` or ``.*`` is not matched: it is also arithmetic and a regular
      expression.
    * Commands that only use the names (``ls``, ``find`` without an action,
      ``git status``) are skipped, as are PowerShell commands that are not file
      commands, since PowerShell hands the pattern to the command unexpanded.

    Whatever is skipped or cut short stays where it was, with the person asked.
    """

    # ``cd certs && cat *.pem`` expands in ``certs``. The folder a command moves into
    # is known only when it is written out, so each one named is tried as well.
    folders: list[Path] = [Path(base_dir)]
    forms: list[str] = []
    assignments = 0

    def assignment(word: str) -> bool:
        nonlocal assignments
        match = _ASSIGNMENT_WORD.fullmatch(word)
        if match is None:
            return False
        name, value = match.groups()
        assignments += 1
        # ``f=.en?; cat $f``: the pattern is expanded where the variable is used.
        if assignments <= _MAX_GLOB_ASSIGNMENTS and has_glob(value) and any(
            f"${name}" in other or f"${{{name}}}" in other for other in words
        ):
            forms.append(value)
        return True

    reading: list[tuple[Sequence[str], str]] = []
    naming: list[tuple[Sequence[str], str]] = []
    hands_names_on = False
    for segment in segments:
        for word in segment:
            if not assignment(word):
                break
        argv = strip_assignments(segment)
        while argv and argv[0] in _SHELL_KEYWORDS:
            argv = argv[1:]  # ``if [ -f x ]``, ``do cat $f``: the command is what follows.
        if not argv:
            continue
        program = command_name(argv[0])
        if program in _ASSIGNING_COMMANDS:
            for word in argv[1:]:
                assignment(word)
            continue
        if program in _DIRECTORY_CHANGE_COMMANDS:
            target = next((item for item in argv[1:4] if not item.startswith("-")), None)
            if target and not has_glob(target) and len(folders) < _MAX_GLOB_FOLDERS:
                folders.append(Path(base_dir, target))
            continue
        if windows_style:
            if reads_matched_files(argv, program, None, windows_style=True):
                reading.append((argv, program))
            elif any(word.lower() in _POWERSHELL_FILE_LISTERS for word in argv):
                naming.append((argv, program))  # ``Get-Item .en? | Get-Content``: the pipeline carries the file.
            continue
        if program in {"for", "select"}:
            naming.append((argv, program))  # The names go into the loop variable.
            continue
        hands_names_on = hands_names_on or program in _NAME_PASSING_PROGRAMS
        git_verb = git_subcommand(argv[1:])[0] if program == "git" else None
        if reads_matched_files(argv, program, git_verb, windows_style=False):
            reading.append((argv, program))
        else:
            naming.append((argv, program))

    def collect(argv: Sequence[str], program: str) -> None:
        for word in path_words(argv, program, windows_style=windows_style):
            for form in glob_forms(word, windows_style=windows_style):
                forms.append(form)
                if not windows_style and "{" in form and len(forms) < 4 * _MAX_GLOB_WORDS_CHECKED:
                    forms.extend(brace_expansions(form))

    for argv, program in reading:
        collect(argv, program)
    # ``ls .en?`` only shows a name. The name reaches a reading command through
    # ``xargs``, a substitution or a variable (``cat $(ls .en?)``, ``for f in .en?;
    # do cat $f; done``); a plain pipe carries text (``ls certs/* | wc -l``). In
    # PowerShell a pipeline carries the file itself. So the names-only commands
    # are checked only when the line has a reading command and such a route.
    if reading and (windows_style or hands_names_on or substitutes):
        for argv, program in naming:
            collect(argv, program)
    # ``echo "$(<.en?)"`` reads the file with no program at all.
    for word in words:
        if "$(<" in word and len(word) <= _MAX_SUBSTITUTION_WORD:
            forms.extend(match.group(1) for match in _FILE_SUBSTITUTION.finditer(word))

    budget = GlobBudget(project_roots(repo_root, base_dir))
    matched = 0
    checked = 0
    judged = 0
    for form in dict.fromkeys(forms):
        if not has_glob(form) or not names_something(form):
            continue
        checked += 1
        if checked > _MAX_GLOB_WORDS_CHECKED:
            break
        reached = False
        for folder in folders:
            for candidate in expand_glob_word(
                form, folder, windows_style=windows_style, include_hidden=include_hidden, budget=budget
            ):
                judged += 1
                if judged <= _MAX_GLOB_FULL_JUDGMENTS:
                    reached = _classify_command_target(candidate, repo_root, folder, policy) == "secret_path"
                else:
                    # The full judgment resolves links and costs about a millisecond a
                    # path; past the first few, the name alone is checked.
                    reached = is_secret_path(repository_relative_text(candidate, folder, repo_root), policy.paths)
                if reached:
                    break
            if reached:
                break
        if reached:
            matched += 1
    return matched


def _blank_quoted_text(command: str) -> str | None:
    """``command`` with each quoted run replaced by filler of the same length.

    None when the shells behind the tool could disagree about where a quote ends.
    PowerShell also closes on typographic quotes, stops parsing at ``--%`` and
    expands ``$`` and backticks inside double quotes; a backslash escapes a quote in
    a POSIX shell only; and a quote in mid-word splits words differently.
    """

    if "'" not in command and '"' not in command:
        return command
    if "\\" in command or "--%" in command or _TYPOGRAPHIC_QUOTES.intersection(command):
        return None
    blanked: list[str] = []
    index = 0
    previous = " "
    while index < len(command):
        char = command[index]
        if char not in "'\"":
            blanked.append(char)
            previous = char
            index += 1
            continue
        end = command.find(char, index + 1)
        if previous not in " \t" or end == -1:
            return None
        inner = command[index + 1 : end]
        if any(mark in inner for mark in "\n\r\x00") or (char == '"' and ("$" in inner or "`" in inner)):
            return None
        if '"' in inner:
            # A literal double quote ends the quoting cmd.exe applies when the
            # program is a .cmd or .bat file, and what follows runs as a command.
            return None
        if end + 1 < len(command) and command[end + 1] not in " \t":
            return None
        blanked.append("Q" * (end - index + 1))
        previous = "Q"
        index = end + 1
    return "".join(blanked)


def _approvable_command(command: str) -> tuple[tuple[str, ...], str | None] | None:
    """Reduce ``command`` to the one plain command a policy prefix can approve.

    Three spellings do not change which program runs and are read through: quoted
    text, a trailing ``2>&1`` and a leading ``cd <folder> &&``. The folder is
    returned for the caller to judge. Anything else a shell would act on leaves the
    command unapproved.
    """

    blanked = _blank_quoted_text(command)
    text = command if blanked is None else blanked
    start, end, folder = 0, len(text), None
    if blanked is not None:
        merged_streams = _STDERR_TO_STDOUT.search(text)
        if merged_streams is not None:
            end = merged_streams.start()
        leading_cd = _LEADING_CD.match(text[:end])
        if leading_cd is not None:
            start, folder = leading_cd.end(), leading_cd.group(1)
            if command[leading_cd.start(1) : leading_cd.end(1)] != folder:
                # The folder was quoted: the match saw filler, not its name.
                return None
    if any(char in text[start:end] for char in _APPROVED_COMMAND_REJECTED_CHARACTERS):
        return None
    try:
        argv = tuple(shlex.split(command[start:end]))
    except ValueError:
        return None
    return (argv, folder) if argv else None


def _command_approved_by_policy(
    hook_input: ClaudeCodePreToolUseInput,
    mapping_reasons: Sequence[str],
    policy: HookPolicy,
    repo_root: str | Path,
    base_dir: str | Path,
) -> bool:
    """True for a single plain command matching a prefix a person approved.

    The approval belongs to this project, so it does not follow the command into
    another folder, where the same ``pytest`` would run that folder's code.
    """

    command = hook_input.tool_input.get("command")
    if (
        not policy.allow_commands
        or hook_input.tool_name not in _COMMAND_TOOL_NAMES
        or not isinstance(command, str)
        or GUARD_SELF_DISABLE_REASON in mapping_reasons
    ):
        return False
    parsed = _approvable_command(command)
    if parsed is None:
        return False
    argv, folder = parsed
    if not policy.approves_command(argv):
        return False
    if _classify_command_target(".", repo_root, base_dir, policy) not in _PROJECT_WORKING_FOLDER_KINDS:
        return False
    if folder is None:
        return True
    # ``cd sub && bash scripts/run.sh`` runs sub's script, not the one a person
    # approved, so after ``cd`` only prefixes that name no file are honored. And
    # with CDPATH set, bash may enter another folder unless the name starts with ./
    prefixes = [prefix for prefix in policy.allow_commands if argv[: len(prefix)] == prefix]
    if not any(all(_FOLDER_INDEPENDENT_WORD.fullmatch(word) for word in prefix) for prefix in prefixes):
        return False
    if os.environ.get("CDPATH") and not folder.startswith("./"):
        return False
    try:
        return (
            _classify_command_target(folder, repo_root, base_dir, policy) == "safe_in_repo"
            and _canonical_command_target(folder, repo_root, base_dir).is_dir()
        )
    except (OSError, ValueError):
        return False


DANGEROUS_COMMAND_KIND_PREFIX = "dangerous_command_kind:"
_DANGEROUS_COMMAND_KINDS = frozenset(
    {"publish", "deploy", "remote_destroy", "database_destroy", "system_destroy", "rm_recursive_force", "token"}
)


def _dangerous_command_kind(action_reasons: Sequence[str]) -> str | None:
    """Which family of risk the command gate found, so the stop can say what it is.

    Only a fixed family name is passed on, never a word taken from the command.
    """

    for reason in action_reasons:
        if isinstance(reason, str) and reason.startswith("dangerous_bash_"):
            kind = reason[len("dangerous_bash_") :].split(":", 1)[0]
            if kind in _DANGEROUS_COMMAND_KINDS:
                return kind
    return None


def _collapse_engine_decision(
    *,
    candidate_action_type: str,
    law_status: str,
    capability_gate_result: str,
    action_candidate_status: str,
    action_risk_status: str,
    aeg_guard_records: tuple[Mapping[str, Any], ...],
    repo_boundary_records: tuple[Mapping[str, Any], ...],
    classification: Classification,
    bash_target_gate: Mapping[str, Any],
    powershell_target_gate: Mapping[str, Any],
    shell_read_gate: Mapping[str, Any],
    protected_path_gate: Mapping[str, Any],
    secret_reference_gate: Mapping[str, Any],
    command_approved: bool,
    approval_held: bool = False,
    shell_file_gate: Mapping[str, Any] | None = None,
    action_reasons: Sequence[str] = (),
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if any(record.get("target_outside_repo") is True for record in repo_boundary_records):
        reasons.append("repo_boundary_gate_denies_outside_repo_target")
    if any(record.get("protected_target") is True for record in aeg_guard_records):
        reasons.append("aeg_integrity_guard_denies_state_dir_target")
    # A command's only deny candidate is its danger rating, which is what an
    # approved prefix lifts. Targets and secrets below still apply to it.
    if action_candidate_status == DENY_CANDIDATE and not command_approved:
        reasons.append("tool_call_mapping_deny_candidate")
    if action_risk_status == BASH_DANGEROUS and not command_approved:
        reasons.append("dangerous_bash_gate_denies_command")
    if action_risk_status == POWERSHELL_DANGEROUS and not command_approved:
        reasons.append("dangerous_powershell_gate_denies_command")
    if action_risk_status in {BASH_DANGEROUS, POWERSHELL_DANGEROUS} and not command_approved:
        kind = _dangerous_command_kind(action_reasons)
        if kind is not None:
            reasons.append(f"{DANGEROUS_COMMAND_KIND_PREFIX}{kind}")
    if protected_path_gate.get("protected_path_detected") is True:
        reasons.append("protected_path_gate_denies_target")
    if shell_read_gate.get("deny") is True:
        reasons.append("shell_read_targets_secret_state_or_outside_repo")
    if secret_reference_gate.get("deny") is True:
        reasons.append("shell_command_references_secret_path")
    if bash_target_gate.get("deny") is True:
        reasons.append("bash_write_delete_target_protected_or_out_of_scope")
    if powershell_target_gate.get("deny") is True:
        reasons.append("powershell_write_delete_target_protected_or_out_of_scope")

    # WRITE_FILE/RUN_COMMAND capability status reflects Aegis's own
    # propose-only self-execution policy (11-B), not the risk of the
    # substrate's tool call target/command. It is excluded from hook
    # judgment for those two action types; the target-path risk gates above
    # (tool_call_mapping deny-candidate, aeg guard, repo boundary) and the
    # dangerous-Bash gate already carry that judgment instead.
    capability_gate_is_hook_judgment_basis = (
        candidate_action_type
        not in _SELF_EXECUTION_CAPABILITY_ACTION_TYPES_NOT_HOOK_JUDGMENT_BASIS
    )
    if capability_gate_is_hook_judgment_basis and capability_gate_result in ENGINE_DENY_CAPABILITY_RESULTS:
        reasons.append(f"capability_gate_denies:{capability_gate_result}")
    if law_status == NEEDS_USER_GATE:
        reasons.append("law_requires_user_gate_hook_uses_deny_safe_default")

    if reasons:
        return DENY, tuple((*reasons, "hook_decision_matches_or_is_stricter_than_engine"))

    if shell_read_gate.get("allow") is True:
        return ALLOW, (
            "structurally_classified_read_only_shell_command",
            "shell_read_paths_are_regular_non_secret_files_in_repo",
            "hook_decision_matches_engine_decision",
        )

    if shell_file_gate and shell_file_gate.get("allow") is True:
        return ALLOW, (
            "structurally_classified_simple_file_operation",
            "shell_file_targets_are_regular_non_protected_paths_in_repo",
            "hook_decision_matches_engine_decision",
        )

    if approval_held:
        return ASK, (
            APPROVAL_HELD_REASON,
            "hook_decision_matches_or_is_stricter_than_engine",
        )

    if command_approved:
        return ALLOW, (
            "hook_policy_approved_command",
            "hook_decision_matches_engine_decision",
        )

    # Clearly-safe normal work: a repo-internal, non-protected Read/Write/Edit
    # that the existing engine classified as a definite LOW/MEDIUM change is
    # allowed so the hook does not obstruct ordinary safe operations. This
    # promotion is based only on the existing engine's classification; it never
    # applies to Bash, to ambiguous / NOT_CHECKED-impact inputs, or to anything
    # that produced a deny reason above.
    if _is_clearly_safe_normal_file_operation(
        candidate_action_type=candidate_action_type,
        action_candidate_status=action_candidate_status,
        classification=classification,
        repo_boundary_records=repo_boundary_records,
    ):
        return ALLOW, (
            "engine_classified_normal_non_protected_in_repo_file_operation_as_safe",
            f"clearly_safe_impact={classification.impact_risk}_risk={classification.risk_level}",
            "clearly_safe_normal_work_maps_to_allow",
            "ambiguous_not_checked_or_unclassified_never_reaches_this_branch",
            "hook_decision_matches_engine_decision",
        )

    if (
        capability_gate_is_hook_judgment_basis
        and capability_gate_result in ENGINE_ALLOWED_CAPABILITY_RESULTS
        and law_status == CLEAN_CORE
    ):
        return ALLOW, (
            "classification_law_and_capability_gate_allow_read_only_candidate",
            "hook_decision_matches_engine_decision",
        )

    if (
        candidate_action_type in _WRITE_LIKE_CANDIDATE_ACTION_TYPES
        and action_candidate_status == STRUCTURED_ACTION_CANDIDATE
    ):
        return ASK, (
            "write_or_edit_judgment_basis_is_target_path_risk_not_capability_gate",
            "normal_target_path_maps_to_ask_candidate",
            "aegis_self_write_file_capability_remains_denied_and_unrelated_to_hook_judgment",
            "hook_decision_matches_or_is_stricter_than_engine",
        )

    if (
        action_risk_status in {BASH_NOT_CHECKED, POWERSHELL_NOT_CHECKED, UNKNOWN_TOOL}
        or law_status == NOT_CHECKED
    ):
        return DEFER, (
            "not_checked_or_unclassified_maps_to_defer",
            "not_checked_unknown_or_unclassified_never_maps_to_allow",
            "safe_default_hold_current_state",
            "hook_decision_matches_or_is_stricter_than_engine",
        )

    return DEFER, (
        "engine_basis_not_clean_maps_to_defer",
        "safe_default_hold_current_state",
        "hook_decision_matches_or_is_stricter_than_engine",
    )


def _build_decision(
    *,
    request: HookJudgmentEngineRequest,
    engine_decision: str,
    hook_decision: str,
    reasons: Sequence[str],
    basis: Mapping[str, Any],
    updated_tool_input: Mapping[str, Any] | None = None,
    audit_targets: Sequence[str] = (),
    audit_commands: Sequence[str] = (),
    written_text_names_secret_file: bool = False,
    host_delegation_eligible: bool = False,
) -> HookJudgmentEngineDecision:
    payload = {
        "contract_version": PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION,
        "request": request.to_record(),
        "engine_decision": engine_decision,
        "hook_decision": hook_decision,
        "decision_reasons": tuple(reasons),
        "engine_decision_basis": basis,
        "engine_basis_sources": ENGINE_BASIS_SOURCES,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }
    decision_hash = _sha256_json(payload)
    return HookJudgmentEngineDecision(
        decision_id=f"phase11c8-hook-judgment:{decision_hash}",
        decision_hash=decision_hash,
        contract_version=PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION,
        request=request,
        engine_decision=engine_decision,
        hook_decision=hook_decision,
        decision_reasons=tuple(reasons),
        engine_decision_basis=basis,
        engine_basis_sources=ENGINE_BASIS_SOURCES,
        hook_decision_matches_or_is_stricter_than_engine=(
            HOOK_DECISION_STRENGTH[hook_decision]
            >= HOOK_DECISION_STRENGTH[engine_decision]
        ),
        updated_tool_input=updated_tool_input,
        audit_targets=tuple(audit_targets),
        audit_commands=tuple(audit_commands),
        written_text_names_secret_file=written_text_names_secret_file,
        host_delegation_eligible=host_delegation_eligible,
    )


def _protected_path_gate(
    hook_input: ClaudeCodePreToolUseInput,
    target_paths: tuple[str, ...],
    repo_root: str | Path,
    policy: HookPolicy,
) -> dict[str, Any]:
    if hook_input.tool_name in _READ_LIKE_TOOL_NAMES:
        protected_paths = tuple(
            path for path in target_paths if is_read_protected_path(path, policy.paths)
        )
    else:
        protected_paths = tuple(
            path
            for path in target_paths
            if is_protected_path(path, policy.paths) or _is_guard_runtime_target(path, repo_root)
        )
    return {
        "policy_source": "jangseung.classify.is_protected_path",
        "target_paths": target_paths,
        "protected_paths": protected_paths,
        "protected_path_detected": bool(protected_paths),
        "protected_path_policy_duplicated_in_hook": False,
    }


def _aeg_guard_records(
    repo_root: str | Path,
    target_paths: tuple[str, ...],
) -> tuple[Mapping[str, Any], ...]:
    records = []
    for path in target_paths:
        records.append(
            decide_b1_aeg_integrity_guard(
                repo_root=repo_root,
                submitted_path=path,
            ).to_record()
        )
    return tuple(records)


def _repo_boundary_records(
    repo_root: str | Path,
    target_paths: tuple[str, ...],
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=path,
        ).to_record()
        for path in target_paths
    )


def _validation_record(validation: Any) -> dict[str, Any]:
    return {
        "valid": validation.valid,
        "status": validation.status,
        "reasons": validation.reasons,
        "tool_support_status": validation.tool_support_status,
        "ignored_untrusted_fields": validation.ignored_untrusted_fields,
        "unsupported_unknown_or_not_checked_is_pass": (
            validation.unsupported_unknown_or_not_checked_is_pass
        ),
        "hook_input_trusted_as_decision": validation.hook_input_trusted_as_decision,
        "hook_input_trusted_as_capability_grant": (
            validation.hook_input_trusted_as_capability_grant
        ),
    }


def _capability_record(capability_result: Any) -> dict[str, Any]:
    return {
        "action_type": capability_result.action_type,
        "required_capabilities": capability_result.required_capabilities,
        "capability_decisions": tuple(
            {
                "capability_name": decision.capability_name,
                "status": decision.status,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
            for decision in capability_result.capability_decisions
        ),
        "gate_result": capability_result.gate_result,
        "gate_reason": capability_result.gate_reason,
        "schema_validation_status": capability_result.schema_validation_status,
        "execution_allowed": capability_result.execution_allowed,
        "mutation_allowed": capability_result.mutation_allowed,
        "write_authority_granted": capability_result.write_authority_granted,
        "live_executor_ready": capability_result.live_executor_ready,
        "live_executor_authority": capability_result.live_executor_authority,
    }


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _repo_relative_candidate(path: str) -> bool:
    stripped = path.strip()
    if not stripped:
        return False
    if stripped.startswith("/") or _looks_like_windows_absolute_path(stripped):
        return False
    return ".." not in _path_parts(stripped)


def _path_parts(path_value: str) -> tuple[str, ...]:
    normalized = "/".join(path_value.split("\\"))
    return tuple(part for part in normalized.split("/") if part and part != ".")


def _looks_like_windows_absolute_path(path_value: str) -> bool:
    return (
        len(path_value) >= 3
        and path_value[1] == ":"
        and path_value[2] in ("/", "\\")
        and path_value[0].isalpha()
    )


def _reported_only_fields(value: Any) -> tuple[str, ...]:
    fields: list[str] = []
    _scan_reported_only(value, "raw_hook_input", fields)
    return tuple(sorted(dict.fromkeys(fields)))


def _scan_reported_only(value: Any, location: str, fields: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(str(key))
            nested_location = f"{location}.{key}"
            if normalized_key in _REPORTED_ONLY_KEYS:
                fields.append(nested_location)
            if normalized_key in _REPORTED_ONLY_VALUE_KEYS and nested == "reported_only":
                fields.append(nested_location)
            _scan_reported_only(nested, nested_location, fields)
        return
    if _is_sequence(value):
        for index, nested in enumerate(value):
            _scan_reported_only(nested, f"{location}[{index}]", fields)


def _normalize_key(value: str) -> str:
    normalized_spaces = "_".join(value.strip().lower().split())
    return "_".join(normalized_spaces.split("-"))


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _decision_payload(record: HookJudgmentEngineDecision) -> dict[str, Any]:
    return {
        "contract_version": record.contract_version,
        "request": record.request.to_record(),
        "engine_decision": record.engine_decision,
        "hook_decision": record.hook_decision,
        "decision_reasons": record.decision_reasons,
        "engine_decision_basis": record.engine_decision_basis,
        "engine_basis_sources": record.engine_basis_sources,
        "hook_decision_matches_or_is_stricter_than_engine": (
            record.hook_decision_matches_or_is_stricter_than_engine
        ),
        "protected_path_policy_duplicated_in_hook": (
            record.protected_path_policy_duplicated_in_hook
        ),
        "hook_policy_divergence_allowed": record.hook_policy_divergence_allowed,
        "reported_only_trusted_as_judgment_basis": (
            record.reported_only_trusted_as_judgment_basis
        ),
        "not_checked_is_allow": record.not_checked_is_allow,
        "unclassified_bash_is_allow": record.unclassified_bash_is_allow,
        "safe_default": record.safe_default,
        "live_executor_authority": record.live_executor_authority,
    }


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(nested) for key, nested in value.items()})
    if isinstance(value, tuple):
        return tuple(_freeze_value(nested) for nested in value)
    if isinstance(value, list):
        return tuple(_freeze_value(nested) for nested in value)
    return value


def _plain_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_data(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return tuple(_plain_json_data(nested) for nested in value)
    if isinstance(value, list):
        return [_plain_json_data(nested) for nested in value]
    return value


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        _plain_json_data(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "APPROVAL_HELD_REASON",
    "ENGINE_BASIS_SOURCES",
    "OUTSIDE_PROJECT_TARGET",
    "REVIEW_TIER_REASON",
    "PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION",
    "HookJudgmentEngineDecision",
    "HookJudgmentEngineRequest",
    "judge_pretooluse_with_aeg_engine",
]
