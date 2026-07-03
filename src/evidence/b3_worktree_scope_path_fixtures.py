"""B3-4 in-memory worktree scope and path normalization fixtures.

This module classifies path-scope bypass candidates as executable fixtures. It
does not touch the filesystem, create symlinks, mutate .aeg state, call network
or provider surfaces, run commands, or wire runtime executor authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import unicodedata
from typing import Any, Mapping

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    SAFE_DEFAULT,
)

B3_WORKTREE_SCOPE_PATH_FIXTURE_REPORT_V0 = "b3_worktree_scope_path_fixture_report_v0"

IN_WORKTREE_CANDIDATE = "IN_WORKTREE_CANDIDATE"
AEG_SCOPE_OUT_REQUIRED = "AEG_SCOPE_OUT_REQUIRED"
OUTSIDE_REPO_SCOPE_REQUIRED = "OUTSIDE_REPO_SCOPE_REQUIRED"
PARENT_TRAVERSAL_CANDIDATE = "PARENT_TRAVERSAL_CANDIDATE"
ABSOLUTE_PATH_CANDIDATE = "ABSOLUTE_PATH_CANDIDATE"
SIBLING_WORKTREE_CANDIDATE = "SIBLING_WORKTREE_CANDIDATE"
SYMLINK_ESCAPE_CANDIDATE = "SYMLINK_ESCAPE_CANDIDATE"
UNICODE_AMBIGUITY_CANDIDATE = "UNICODE_AMBIGUITY_CANDIDATE"
STRUCTURED_TOOL_SCOPE_CANDIDATE = "STRUCTURED_TOOL_SCOPE_CANDIDATE"
FUTURE_CLOSURE_REQUIRED = "FUTURE_CLOSURE_REQUIRED"
EXPECTED_RED_OR_KNOWN_GAP = "EXPECTED_RED_OR_KNOWN_GAP"

CLOSURE_WORKTREE_SCOPE = "worktree_scope_required"
CLOSURE_AEG_SCOPE_OUT = "aeg_state_scope_out_required"
CLOSURE_REPO_OUTSIDE = "repo_outside_write_denial_required"
CLOSURE_PATH_CANONICALIZATION = "path_canonicalization_required"
CLOSURE_PARENT_TRAVERSAL = "parent_traversal_handling_required"
CLOSURE_ABSOLUTE_PATH = "absolute_path_handling_required"
CLOSURE_SIBLING_WORKTREE = "sibling_worktree_handling_required"
CLOSURE_SYMLINK_ESCAPE = "symlink_escape_handling_required"
CLOSURE_UNICODE_AMBIGUITY = "unicode_path_ambiguity_handling_required"
CLOSURE_STRUCTURED_TOOL_SCOPE = "structured_tool_broad_filesystem_scope_required"

AUTHORITY_SNAPSHOT = {
    "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "safe_default": SAFE_DEFAULT,
}

NON_CLAIM_CAVEATS = (
    "fixture classification is not path denial enforcement",
    "fixture classification is not a raw shell authority grant",
    "fixture classification is not a write_file tool",
    "fixture classification is not a run_command tool",
    "fixture classification is not a process_spawn tool",
    "fixture classification is not a network authority grant",
    "fixture classification is not a provider/model call authority grant",
    "fixture classification is not a remote write authority grant",
    "fixture classification is not a repo outside write authority grant",
    "fixture classification is not OS/filesystem enforcement",
    "fixture classification is not a sandbox/container",
    "fixture classification is not a physical impossibility proof",
    "fixture classification is not executor isolation",
    "fixture classification is not runtime tool gating",
    "fixture classification is not a live executor",
    "fixture classification is not runtime write authority grant",
    "fixture classification is not a Phase 11-A start",
    "fixture classification is not B3 closure",
    "fixture classification is not B1 hard blocker fully green",
    "fixture classification is not Live Executor Entry Gate approval",
)

_STRUCTURED_MARKERS = ("://", "**", "{repo}", "{workspace}", "<worktree>")


@dataclass(frozen=True)
class FixtureCase:
    case_id: str
    input_path: str
    worktree_root: str
    expected_candidate_type: str
    expected_required_closure: tuple[str, ...]
    note: str
    synthetic_symlink_map: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassificationResult:
    case_id: str
    input_path: str
    worktree_root: str
    normalized_input_path: str
    synthetic_resolved_path: str
    candidate_type: str
    classification_statuses: tuple[str, ...]
    required_closure: tuple[str, ...]
    interpretation: str
    note: str


def default_fixture_cases() -> tuple[FixtureCase, ...]:
    root = "/workspace/Aegis"
    return (
        FixtureCase(
            case_id="normal_in_worktree_relative_path",
            input_path="src/evidence/example.py",
            worktree_root=root,
            expected_candidate_type=IN_WORKTREE_CANDIDATE,
            expected_required_closure=(CLOSURE_WORKTREE_SCOPE,),
            note="Baseline relative path under the intended worktree.",
        ),
        FixtureCase(
            case_id="aeg_direct_path",
            input_path=".aeg/evidence.jsonl",
            worktree_root=root,
            expected_candidate_type=AEG_SCOPE_OUT_REQUIRED,
            expected_required_closure=(CLOSURE_AEG_SCOPE_OUT, CLOSURE_PATH_CANONICALIZATION),
            note=".aeg direct target must remain scoped out in future closure work.",
        ),
        FixtureCase(
            case_id="aeg_via_parent_traversal",
            input_path="src/../.aeg/ledger.jsonl",
            worktree_root=root,
            expected_candidate_type=AEG_SCOPE_OUT_REQUIRED,
            expected_required_closure=(
                CLOSURE_AEG_SCOPE_OUT,
                CLOSURE_PARENT_TRAVERSAL,
                CLOSURE_PATH_CANONICALIZATION,
            ),
            note="Parent traversal can hide a .aeg target from lexical prefix checks.",
        ),
        FixtureCase(
            case_id="outside_repo_via_parent_traversal",
            input_path="../outside-repo/file.txt",
            worktree_root=root,
            expected_candidate_type=OUTSIDE_REPO_SCOPE_REQUIRED,
            expected_required_closure=(CLOSURE_REPO_OUTSIDE, CLOSURE_PARENT_TRAVERSAL),
            note="Traversal out of the intended worktree remains a future closure candidate.",
        ),
        FixtureCase(
            case_id="absolute_path_outside_repo",
            input_path="/var/tmp/aegis-output.txt",
            worktree_root=root,
            expected_candidate_type=OUTSIDE_REPO_SCOPE_REQUIRED,
            expected_required_closure=(CLOSURE_REPO_OUTSIDE, CLOSURE_ABSOLUTE_PATH),
            note="Absolute outside path bypasses relative worktree assumptions.",
        ),
        FixtureCase(
            case_id="sibling_worktree_path",
            input_path="../Aegis-sibling/src/file.py",
            worktree_root=root,
            expected_candidate_type=SIBLING_WORKTREE_CANDIDATE,
            expected_required_closure=(CLOSURE_SIBLING_WORKTREE, CLOSURE_PARENT_TRAVERSAL),
            note="Sibling checkout/worktree confusion remains measurable fixture input.",
        ),
        FixtureCase(
            case_id="symlink_escape_to_aeg",
            input_path="links/aeg-state/evidence.jsonl",
            worktree_root=root,
            synthetic_symlink_map={"links/aeg-state": ".aeg"},
            expected_candidate_type=SYMLINK_ESCAPE_CANDIDATE,
            expected_required_closure=(CLOSURE_SYMLINK_ESCAPE, CLOSURE_AEG_SCOPE_OUT),
            note="Synthetic symlink map resolves an allowed-looking path into .aeg.",
        ),
        FixtureCase(
            case_id="symlink_escape_to_outside_repo",
            input_path="links/outside/file.txt",
            worktree_root=root,
            synthetic_symlink_map={"links/outside": "../outside-repo"},
            expected_candidate_type=SYMLINK_ESCAPE_CANDIDATE,
            expected_required_closure=(CLOSURE_SYMLINK_ESCAPE, CLOSURE_REPO_OUTSIDE),
            note="Synthetic symlink map resolves an allowed-looking path outside the repo.",
        ),
        FixtureCase(
            case_id="unicode_path_ambiguity_candidate",
            input_path="src/\uff0eaeg/report.txt",
            worktree_root=root,
            expected_candidate_type=UNICODE_AMBIGUITY_CANDIDATE,
            expected_required_closure=(CLOSURE_UNICODE_AMBIGUITY, CLOSURE_PATH_CANONICALIZATION),
            note="Fullwidth dot normalizes differently and is tracked as ambiguity only.",
        ),
        FixtureCase(
            case_id="structured_tool_broad_filesystem_scope",
            input_path="structured://filesystem/{workspace}/**",
            worktree_root=root,
            expected_candidate_type=STRUCTURED_TOOL_SCOPE_CANDIDATE,
            expected_required_closure=(CLOSURE_STRUCTURED_TOOL_SCOPE, CLOSURE_WORKTREE_SCOPE),
            note="Structured broad filesystem scope can be capability-like without raw shell.",
        ),
    )


def classify_fixture_case(fixture_case: FixtureCase) -> ClassificationResult:
    root = _normalize_absolute_path(fixture_case.worktree_root)
    normalized_input = _normalize_input_path(fixture_case.input_path, root)
    resolved = _resolve_synthetic_symlink(normalized_input, root, fixture_case.synthetic_symlink_map)
    statuses = _classification_statuses(fixture_case, normalized_input, resolved, root)
    candidate_type = _candidate_type(statuses, normalized_input, resolved, root)
    required_closure = _required_closure(statuses, normalized_input, resolved, root)

    return ClassificationResult(
        case_id=fixture_case.case_id,
        input_path=fixture_case.input_path,
        worktree_root=root,
        normalized_input_path=normalized_input,
        synthetic_resolved_path=resolved,
        candidate_type=candidate_type,
        classification_statuses=statuses,
        required_closure=required_closure,
        interpretation=EXPECTED_RED_OR_KNOWN_GAP,
        note=fixture_case.note,
    )


def build_fixture_report(
    fixture_cases: tuple[FixtureCase, ...] | None = None,
) -> dict[str, Any]:
    cases = fixture_cases if fixture_cases is not None else default_fixture_cases()
    results = tuple(classify_fixture_case(fixture_case) for fixture_case in cases)
    report = {
        "report_version": B3_WORKTREE_SCOPE_PATH_FIXTURE_REPORT_V0,
        "scope": "fixture_measurement_classification_only",
        "authority_snapshot": dict(AUTHORITY_SNAPSHOT),
        "b3_1_b3_2_b3_3_preservation": {
            "b3_1_worktree_path_inventory_preserved": True,
            "b3_2_capability_non_grant_contract_preserved": True,
            "b3_3_evidence_verify_replay_preserved": True,
            "b3_5_status_note_started": False,
        },
        "non_claim_caveats": list(NON_CLAIM_CAVEATS),
        "fixture_cases": [_case_record(fixture_case) for fixture_case in cases],
        "classification_results": [_result_record(result) for result in results],
        "digest_interpretation": "fixture report digest only; not enforcement proof",
    }
    report["fixture_report_digest"] = fixture_report_digest(report)
    return report


def fixture_report_digest(report: Mapping[str, Any]) -> str:
    payload = dict(report)
    payload.pop("fixture_report_digest", None)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _classification_statuses(
    fixture_case: FixtureCase,
    normalized_input: str,
    resolved: str,
    root: str,
) -> tuple[str, ...]:
    statuses: list[str] = []
    if _is_absolute_path(fixture_case.input_path):
        statuses.append(ABSOLUTE_PATH_CANDIDATE)
    if _contains_parent_traversal(fixture_case.input_path):
        statuses.append(PARENT_TRAVERSAL_CANDIDATE)
    if _is_structured_scope_input(fixture_case.input_path):
        statuses.append(STRUCTURED_TOOL_SCOPE_CANDIDATE)
    if _has_unicode_ambiguity(fixture_case.input_path):
        statuses.append(UNICODE_AMBIGUITY_CANDIDATE)
    if fixture_case.synthetic_symlink_map:
        statuses.append(SYMLINK_ESCAPE_CANDIDATE)
    if _is_aeg_path(normalized_input, root) or _is_aeg_path(resolved, root):
        statuses.append(AEG_SCOPE_OUT_REQUIRED)
    if _is_sibling_worktree_path(normalized_input, root) or _is_sibling_worktree_path(resolved, root):
        statuses.append(SIBLING_WORKTREE_CANDIDATE)
    if not _is_within(resolved, root) and not _is_structured_scope_input(fixture_case.input_path):
        statuses.append(OUTSIDE_REPO_SCOPE_REQUIRED)
    if _is_within(resolved, root) and not _is_aeg_path(resolved, root):
        statuses.append(IN_WORKTREE_CANDIDATE)
    statuses.append(FUTURE_CLOSURE_REQUIRED)
    statuses.append(EXPECTED_RED_OR_KNOWN_GAP)
    return _unique(statuses)


def _candidate_type(
    statuses: tuple[str, ...],
    normalized_input: str,
    resolved: str,
    root: str,
) -> str:
    priority = (
        SYMLINK_ESCAPE_CANDIDATE,
        STRUCTURED_TOOL_SCOPE_CANDIDATE,
        UNICODE_AMBIGUITY_CANDIDATE,
        AEG_SCOPE_OUT_REQUIRED,
        SIBLING_WORKTREE_CANDIDATE,
        OUTSIDE_REPO_SCOPE_REQUIRED,
        ABSOLUTE_PATH_CANDIDATE,
        PARENT_TRAVERSAL_CANDIDATE,
        IN_WORKTREE_CANDIDATE,
    )
    if _is_aeg_path(normalized_input, root) or _is_aeg_path(resolved, root):
        if SYMLINK_ESCAPE_CANDIDATE not in statuses:
            return AEG_SCOPE_OUT_REQUIRED
    for candidate in priority:
        if candidate in statuses:
            return candidate
    return IN_WORKTREE_CANDIDATE


def _required_closure(
    statuses: tuple[str, ...],
    normalized_input: str,
    resolved: str,
    root: str,
) -> tuple[str, ...]:
    closures: list[str] = []
    if IN_WORKTREE_CANDIDATE in statuses:
        closures.append(CLOSURE_WORKTREE_SCOPE)
    if AEG_SCOPE_OUT_REQUIRED in statuses or _is_aeg_path(normalized_input, root) or _is_aeg_path(resolved, root):
        closures.append(CLOSURE_AEG_SCOPE_OUT)
        closures.append(CLOSURE_PATH_CANONICALIZATION)
    if OUTSIDE_REPO_SCOPE_REQUIRED in statuses:
        closures.append(CLOSURE_REPO_OUTSIDE)
    if PARENT_TRAVERSAL_CANDIDATE in statuses:
        closures.append(CLOSURE_PARENT_TRAVERSAL)
        closures.append(CLOSURE_PATH_CANONICALIZATION)
    if ABSOLUTE_PATH_CANDIDATE in statuses:
        closures.append(CLOSURE_ABSOLUTE_PATH)
    if SIBLING_WORKTREE_CANDIDATE in statuses:
        closures.append(CLOSURE_SIBLING_WORKTREE)
    if SYMLINK_ESCAPE_CANDIDATE in statuses:
        closures.append(CLOSURE_SYMLINK_ESCAPE)
    if UNICODE_AMBIGUITY_CANDIDATE in statuses:
        closures.append(CLOSURE_UNICODE_AMBIGUITY)
        closures.append(CLOSURE_PATH_CANONICALIZATION)
    if STRUCTURED_TOOL_SCOPE_CANDIDATE in statuses:
        closures.append(CLOSURE_STRUCTURED_TOOL_SCOPE)
        closures.append(CLOSURE_WORKTREE_SCOPE)
    return _unique(closures)


def _case_record(fixture_case: FixtureCase) -> dict[str, Any]:
    return {
        "case_id": fixture_case.case_id,
        "input_path": fixture_case.input_path,
        "worktree_root": fixture_case.worktree_root,
        "synthetic_symlink_map": dict(sorted(fixture_case.synthetic_symlink_map.items())),
        "expected_candidate_type": fixture_case.expected_candidate_type,
        "expected_required_closure": list(fixture_case.expected_required_closure),
        "note": fixture_case.note,
    }


def _result_record(result: ClassificationResult) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "input_path": result.input_path,
        "worktree_root": result.worktree_root,
        "normalized_input_path": result.normalized_input_path,
        "synthetic_resolved_path": result.synthetic_resolved_path,
        "candidate_type": result.candidate_type,
        "classification_statuses": list(result.classification_statuses),
        "required_closure": list(result.required_closure),
        "interpretation": result.interpretation,
        "note": result.note,
    }


def _normalize_absolute_path(path: str) -> str:
    normalized = _normalize_separators(path)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return _collapse_segments(normalized)


def _normalize_input_path(path: str, root: str) -> str:
    normalized = _normalize_separators(path)
    if _is_structured_scope_input(normalized):
        return normalized
    if normalized.startswith("/"):
        return _collapse_segments(normalized)
    return _collapse_segments(root + "/" + normalized)


def _resolve_synthetic_symlink(path: str, root: str, synthetic_symlink_map: Mapping[str, str]) -> str:
    if not synthetic_symlink_map or _is_structured_scope_input(path):
        return path

    normalized_links = {
        _normalize_input_path(link, root): _normalize_input_path(target, root)
        for link, target in synthetic_symlink_map.items()
    }
    for link in sorted(normalized_links, key=len, reverse=True):
        if path == link or path.startswith(link + "/"):
            tail = path[len(link) :].lstrip("/")
            target = normalized_links[link]
            return _collapse_segments(target + ("/" + tail if tail else ""))
    return path


def _collapse_segments(path: str) -> str:
    absolute = path.startswith("/")
    parts: list[str] = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            elif not absolute:
                parts.append(segment)
            continue
        parts.append(segment)
    prefix = "/" if absolute else ""
    collapsed = prefix + "/".join(parts)
    return collapsed or ("/" if absolute else ".")


def _normalize_separators(path: str) -> str:
    return path.replace("\\", "/")


def _is_absolute_path(path: str) -> bool:
    normalized = _normalize_separators(path)
    return normalized.startswith("/") or (
        len(normalized) >= 3 and normalized[1] == ":" and normalized[2] == "/"
    )


def _contains_parent_traversal(path: str) -> bool:
    return ".." in _normalize_separators(path).split("/")


def _is_structured_scope_input(path: str) -> bool:
    return any(marker in path for marker in _STRUCTURED_MARKERS)


def _has_unicode_ambiguity(path: str) -> bool:
    if path.isascii():
        return False
    return unicodedata.normalize("NFC", path) != path or unicodedata.normalize("NFKC", path) != path


def _is_aeg_path(path: str, root: str) -> bool:
    if not _is_within(path, root):
        return False
    relative = path[len(root) :].lstrip("/")
    return relative == ".aeg" or relative.startswith(".aeg/")


def _is_sibling_worktree_path(path: str, root: str) -> bool:
    if _is_within(path, root) or _is_structured_scope_input(path):
        return False
    root_parent, root_name = root.rsplit("/", 1)
    relative = path[len(root_parent) :].lstrip("/") if path.startswith(root_parent + "/") else ""
    if not relative:
        return False
    first_segment = relative.split("/", 1)[0]
    return first_segment.startswith(root_name + "-") or first_segment.startswith(root_name + "_")


def _is_within(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
