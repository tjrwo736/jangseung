"""Deterministic verification replay for latest evidence and ledger chain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.classify import classify_task
from src.contracts import (
    ACTION_AUTHORITY_FIELDS,
    ACTION_BOUNDARY_CLEAN,
    ACTION_BOUNDARY_FIELDS,
    ACTION_BOUNDARY_NOT_CHECKED,
    BOUND,
    BYPASS_RESULT_MISMATCH_REJECTED,
    AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS,
    AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    AEG_STATE_WRITE_DENIAL_FIELDS,
    AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD,
    AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY,
    AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0,
    AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA,
    AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY,
    CAPABILITY_AUTHORITY_FIELDS,
    CAPABILITY_BOUNDARY_CLEAN,
    CAPABILITY_BOUNDARY_NOT_CHECKED,
    CAPABILITY_ISOLATION_FIELDS,
    CLEAN_CORE,
    CITIZEN_ONE_EVIDENCE_FIELDS,
    EVIDENCE_STORE_CLEAN,
    EVIDENCE_STORE_INTEGRITY_NOT_CHECKED,
    EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED,
    EVIDENCE_STORE_TRUST_FIELDS,
    EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY,
    EXECUTOR_CAPABILITY_BOOL_FIELDS,
    EXECUTOR_CAPABILITY_EXPOSURE_FIELDS,
    EXECUTOR_CAPABILITY_TRANSPORT_STRUCTURED_TOOL_CALL,
    GIT_STATUS_PORCELAIN_V1,
    HIGH,
    LEDGER_FILE,
    LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY,
    LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED,
    LEDGER_INTEGRITY_FIELDS,
    LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD,
    LEDGER_INTEGRITY_SCAFFOLD_V0,
    LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY,
    LEDGER_PREVIOUS_HASH_GENESIS,
    LEDGER_PREVIOUS_HASH_NOT_AVAILABLE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    LOW,
    MEDIATED_WRITE_BOUNDARY_ENFORCEMENT_STATUS_NOT_IMPLEMENTED,
    MEDIATED_WRITE_BOUNDARY_FIELDS,
    MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0,
    MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA,
    MEDIATED_WRITE_DECISION_SOURCE_EXECUTOR_SELF_REPORT,
    MEDIATED_WRITE_DECISION_SOURCE_EXTERNAL_ENFORCEMENT,
    MEDIATED_WRITE_DIRECT_ALLOW_FIELDS,
    MEDIATED_WRITE_EVIDENCE_MISMATCH_REJECTED,
    MEDIATED_WRITE_PASSLIKE_STATUSES,
    MUTATION_BOUNDARY_CLEAN,
    MUTATION_BOUNDARY_DELTA_DETECTED,
    MUTATION_BOUNDARY_DIRTY_PREEXISTING,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    MUTATION_DELTA_SOURCE_COMPUTED,
    SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
    NEEDS_USER_GATE,
    NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION,
    NOT_CHECKED,
    NOT_CHECKED_PASS_OVERCLAIM_REJECTED,
    NOT_CHECKED_IMPACT_RISKS,
    PROVIDER_NETWORK_GUARD_METADATA_FIELDS,
    LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE,
    PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED,
    PROMPT_REDACTION_METADATA_FIELDS,
    PROPOSAL_CONTRACT_FIELDS,
    PROVIDER_ADAPTER_DISABLED_FIELDS,
    PROVIDER_REQUEST_METADATA_FIELDS,
    PROVIDER_RESPONSE_ERROR_METADATA_FIELDS,
    PROVIDER_RUNTIME_STATE_FIELDS,
    PROVIDER_SECRET_ENV_METADATA_FIELDS,
    PROVIDER_SELECTION_METADATA_FIELDS,
    PRE_LIVE_EXECUTOR_GATE_FIELDS,
    PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD,
    PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS,
    PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY,
    PRE_LIVE_EXECUTOR_GATE_RESULT_HOLD_CURRENT_STATE,
    PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
    PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0,
    PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD,
    RESPONSE_REDACTION_METADATA_FIELDS,
    RISK_LEVELS,
    REPORTED_ONLY_PROOF_REJECTED,
    RUN_MANIFEST_V1,
    RUNTIME_WIRING_NOT_IMPLEMENTED,
    STATUSES,
    STATUS_OVERCLAIM_REJECTED,
    STORE_WRITE_MEDIATION_FIELDS,
    STORE_WRITE_MEDIATION_RESULT_BLOCKED,
    TOOL_AUTHORITY_GRANT_FIELDS,
    TOOL_SURFACE_CLEAN,
    TOOL_SURFACE_FIELDS,
    TOOL_SURFACE_SCAFFOLD_ONLY,
    WBYP_IDS,
    WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT,
    WRITE_BYPASS_HARNESS_FIELDS,
    WRITE_BYPASS_HARNESS_PASSLIKE_STATUSES,
    WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
    WRITE_BYPASS_HARNESS_SCAFFOLD_V0,
    WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    WRITE_MEDIATION_COMPONENT_MISMATCH_REJECTED,
    WRITE_CLASSES,
    WRITE_CLASS_DEFAULT_MEDIATION_STATUSES,
)
from src.evidence.action_boundary import expected_action_log_hash
from src.evidence.binding import (
    aeg_state_write_denial_manifest_fields,
    action_boundary_manifest_fields,
    capability_exposure_manifest_fields,
    capability_isolation_manifest_fields,
    changed_files_hash,
    evidence_store_trust_manifest_fields,
    expected_artifact_path,
    manifest_hash,
    mediated_write_boundary_manifest_fields,
    pre_live_executor_gate_manifest_fields,
    repo_relative_path,
    sha256_json,
    sha256_text,
    store_write_mediation_manifest_fields,
    citizen_one_manifest_fields,
    provider_network_guard_manifest_fields,
    provider_request_manifest_fields,
    provider_response_error_manifest_fields,
    provider_runtime_state_manifest_fields,
    provider_secret_env_manifest_fields,
    provider_selection_manifest_fields,
    prompt_redaction_manifest_fields,
    provider_adapter_manifest_fields,
    proposal_manifest_fields,
    response_redaction_manifest_fields,
    tool_surface_manifest_fields,
    write_bypass_harness_manifest_fields,
)
from src.evidence.aeg_state_write_denial import expected_aeg_state_write_denial_metadata_hash
from src.evidence.capability_exposure import (
    expected_executor_capability_exposure_hash,
    expected_executor_capability_exposure_metadata_hash,
)
from src.evidence.capability_isolation import (
    expected_capability_isolation_proof_hash,
    expected_capability_matrix_hash,
)
from src.evidence.evidence_store import expected_evidence_store_trust_metadata_hash
from src.evidence.ledger_integrity import (
    expected_current_evidence_hash,
    expected_current_manifest_hash,
    expected_ledger_chain_hash,
    expected_ledger_entry_hash,
    expected_ledger_integrity_metadata_hash,
    is_sha256_hex,
    ledger_integrity_manifest_fields,
)
from src.evidence.mediated_write_boundary import (
    expected_bypass_fixture_result_hash,
    expected_mediated_write_binding_hash,
    expected_mediated_write_boundary_metadata_hash,
    expected_mediator_contract_hash,
    expected_write_mediation_decision_hash,
)
from src.evidence.pre_live_executor_gate import expected_pre_live_executor_gate_metadata_hash
from src.evidence.store_write_mediation import (
    expected_store_write_mediation_metadata_hash,
    verify_store_write_mediation_metadata,
)
from src.evidence.tool_surface import (
    expected_tool_authority_grant_hash,
    expected_tool_surface_metadata_hash,
)
from src.evidence.write_bypass_harness import (
    expected_write_bypass_harness_metadata_hash,
    expected_write_bypass_harness_registry_hash,
)
from src.evidence.mutation_boundary import compute_mutation_delta
from src.evidence.schema import (
    validate_completion_contract_v0,
    validate_evidence_binding_v0,
    validate_evidence_binding_v1,
    validate_evidence_packet,
    validate_no_forbidden_raw_prompt_response_keys,
    validate_user_gate_reason_card_v1,
)
from src.law import apply_law
from src.state import git
from src.state.store import load_latest_evidence, state_root


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checks: list[str]
    errors: list[str]
    evidence: dict[str, Any] | None


_LEDGER_REQUIRED_FIELDS = (
    "run_id",
    "evidence_path",
    "run_path",
    "manifest_path",
    "manifest_hash",
    "head_sha",
    "tree_sha",
    "risk_level",
    "status",
)
_LEDGER_POSITION_FIELDS = (
    "ledger_sequence_number",
    "ledger_position",
    "position",
)
_LEDGER_BOOL_FIELDS = (
    "ledger_tamper_evident_enabled",
    "ledger_tamper_proof_claimed",
)
_LEDGER_HASH_FIELDS = (
    "manifest_hash",
    "current_evidence_hash",
    "current_manifest_hash",
    "current_ledger_entry_hash",
    "ledger_chain_hash",
    "ledger_integrity_metadata_hash",
)
_LEDGER_STRING_METADATA_FIELDS = tuple(
    field
    for field in LEDGER_INTEGRITY_FIELDS
    if field not in (*_LEDGER_BOOL_FIELDS, "ledger_sequence_number")
)
_LEDGER_MANIFEST_BINDING_FIELDS = (
    "run_id",
    "head_sha",
    "tree_sha",
    "risk_level",
    "status",
    "evidence_path",
    "run_path",
)
_LEDGER_EVIDENCE_BINDING_FIELDS = (
    "run_id",
    "head_sha",
    "tree_sha",
    "risk_level",
    "status",
)
_LEDGER_RUN_BINDING_FIELDS = (
    "run_id",
    "risk_level",
    "status",
)


def verify_latest(cwd: str | Path) -> VerifyResult:
    checks: list[str] = []
    errors: list[str] = []

    try:
        repo = git.repo_root(cwd)
    except git.GitError as exc:
        return VerifyResult(False, checks, [f"git repo root unavailable: {exc}"], None)

    ledger_chain_checks, ledger_chain_errors = _verify_ledger_full_chain(repo)
    checks.extend(ledger_chain_checks)
    errors.extend(ledger_chain_errors)

    try:
        evidence, evidence_path, ledger_entry = load_latest_evidence(repo)
    except Exception as exc:  # JSON parse errors should be human-readable.
        return VerifyResult(False, checks, [*errors, f"latest evidence could not be loaded: {exc}"], None)

    if not ledger_entry:
        return VerifyResult(False, checks, [*errors, "latest run/evidence not found"], None)
    checks.append("latest ledger entry found")

    if evidence_path is None or evidence is None:
        latest_run_id = ledger_entry.get("run_id") if isinstance(ledger_entry, dict) else "UNKNOWN"
        return VerifyResult(
            False,
            checks,
            [*errors, f"latest evidence file not found for run: {latest_run_id}"],
            None,
        )
    checks.append(f"latest evidence loaded: {evidence_path}")

    schema_errors = validate_evidence_packet(evidence)
    if schema_errors:
        errors.extend(schema_errors)
    else:
        checks.append("evidence schema valid")

    binding_errors = validate_evidence_binding_v0(evidence)
    if binding_errors:
        errors.extend(binding_errors)
    else:
        checks.append("evidence binding v0 valid")

    binding_v1_errors = validate_evidence_binding_v1(evidence)
    if binding_v1_errors:
        errors.extend(binding_v1_errors)
    else:
        checks.append("evidence binding v1 valid")

    manifest, manifest_checks, manifest_errors = _verify_manifest_binding(repo, evidence, evidence_path, ledger_entry)
    checks.extend(manifest_checks)
    errors.extend(manifest_errors)

    mutation_checks, mutation_errors = _verify_mutation_boundary(evidence, manifest)
    checks.extend(mutation_checks)
    errors.extend(mutation_errors)

    action_checks, action_errors = _verify_action_boundary(evidence, manifest)
    checks.extend(action_checks)
    errors.extend(action_errors)

    capability_checks, capability_errors = _verify_capability_isolation(evidence, manifest)
    checks.extend(capability_checks)
    errors.extend(capability_errors)

    tool_surface_checks, tool_surface_errors = _verify_tool_surface_authority(evidence, manifest)
    checks.extend(tool_surface_checks)
    errors.extend(tool_surface_errors)

    exposure_checks, exposure_errors = _verify_executor_capability_exposure(evidence, manifest)
    checks.extend(exposure_checks)
    errors.extend(exposure_errors)

    store_checks, store_errors = _verify_evidence_store_trust_boundary(evidence, manifest)
    checks.extend(store_checks)
    errors.extend(store_errors)

    aeg_state_checks, aeg_state_errors = _verify_aeg_state_write_denial(evidence, manifest)
    checks.extend(aeg_state_checks)
    errors.extend(aeg_state_errors)

    mediated_write_checks, mediated_write_errors = _verify_mediated_write_boundary(evidence, manifest)
    checks.extend(mediated_write_checks)
    errors.extend(mediated_write_errors)

    write_bypass_checks, write_bypass_errors = _verify_write_bypass_harness_scaffold(evidence, manifest)
    checks.extend(write_bypass_checks)
    errors.extend(write_bypass_errors)

    gate_checks, gate_errors = _verify_pre_live_executor_gate(evidence, manifest)
    checks.extend(gate_checks)
    errors.extend(gate_errors)

    store_write_mediation_checks, store_write_mediation_errors = _verify_store_write_mediation(evidence, manifest)
    checks.extend(store_write_mediation_checks)
    errors.extend(store_write_mediation_errors)

    ledger_checks, ledger_errors = _verify_ledger_integrity(evidence, manifest, ledger_entry)
    checks.extend(ledger_checks)
    errors.extend(ledger_errors)

    completion_errors = validate_completion_contract_v0(evidence)
    if completion_errors:
        errors.extend(completion_errors)
    else:
        checks.append("completion contract v0 valid")

    gate_card_errors = validate_user_gate_reason_card_v1(evidence)
    if gate_card_errors:
        errors.extend(gate_card_errors)
    elif evidence.get("risk_level") == HIGH:
        checks.append("HIGH user gate reason card valid")

    evidence_repo_root = evidence.get("repo_root")
    if isinstance(evidence_repo_root, str) and evidence_repo_root.strip():
        if Path(evidence_repo_root).resolve() == repo:
            checks.append("repo_root is bound to current repository")
        else:
            errors.append(f"INVALID_EVIDENCE: repo_root mismatch: evidence={evidence_repo_root} replay={repo}")

    bound_head_sha = evidence.get("bound_head_sha") or evidence.get("head_sha", "")
    if evidence and git.object_exists(repo, str(bound_head_sha), "commit"):
        checks.append("bound_head_sha is readable")
    else:
        errors.append("NOT_CHECKED: bound_head_sha is not readable in current repository")

    bound_tree_sha = evidence.get("bound_tree_sha") or evidence.get("tree_sha", "")
    if evidence and git.object_exists(repo, str(bound_tree_sha), "tree"):
        checks.append("bound_tree_sha is readable")
    else:
        errors.append("NOT_CHECKED: bound_tree_sha is not readable in current repository")

    if evidence:
        status = evidence.get("status")
        replay_changed_files = evidence.get("changed_files", [])
        replay_changed_files_source = evidence.get("changed_files_source")
        if manifest:
            replay_changed_files = manifest.get("changed_files", [])
            replay_changed_files_source = manifest.get("changed_files_source")
        saved_changed_files = _string_list(replay_changed_files)
        task_text = evidence.get("task_text", "")
        if not isinstance(task_text, str):
            task_text = ""
        replay = classify_task(
            task_text,
            changed_files=list(saved_changed_files),
            changed_files_source=replay_changed_files_source,
            no_mutation=False,
        )
        replay_law = apply_law(replay)
        if evidence.get("intent_risk") == replay.intent_risk:
            checks.append(f"intent_risk replay matched: {replay.intent_risk}")
        else:
            errors.append(f"INVALID_EVIDENCE: intent_risk mismatch: evidence={evidence.get('intent_risk')} replay={replay.intent_risk}")

        if evidence.get("risk_level") == replay.risk_level:
            checks.append(f"risk_level replay matched: {replay.risk_level}")
        else:
            errors.append(f"INVALID_EVIDENCE: risk_level mismatch: evidence={evidence.get('risk_level')} replay={replay.risk_level}")

        if evidence.get("impact_risk") == replay.impact_risk:
            checks.append(f"impact_risk replay matched: {replay.impact_risk}")
        else:
            errors.append(f"INVALID_EVIDENCE: impact_risk mismatch: evidence={evidence.get('impact_risk')} replay={replay.impact_risk}")

        if evidence.get("impact_reasons", []) == replay.impact_reasons:
            checks.append("impact_reasons replay matched")
        else:
            errors.append(f"INVALID_EVIDENCE: impact_reasons mismatch: evidence={evidence.get('impact_reasons')} replay={replay.impact_reasons}")

        if evidence.get("changed_files_source") == replay.changed_files_source:
            checks.append(f"changed_files_source replay matched: {replay.changed_files_source}")
        else:
            errors.append(
                "INVALID_EVIDENCE: changed_files_source mismatch: "
                f"evidence={evidence.get('changed_files_source')} replay={replay.changed_files_source}"
            )

        if evidence.get("protected_paths_touched", []) == replay.protected_paths_touched:
            checks.append("protected_paths_touched replay matched")
        else:
            errors.append(
                "INVALID_EVIDENCE: protected_paths_touched mismatch: "
                f"evidence={evidence.get('protected_paths_touched')} replay={replay.protected_paths_touched}"
            )

        if evidence.get("risk_escalation_applied") == replay.risk_escalation_applied:
            checks.append(f"risk_escalation_applied replay matched: {replay.risk_escalation_applied}")
        else:
            errors.append(
                "INVALID_EVIDENCE: risk_escalation_applied mismatch: "
                f"evidence={evidence.get('risk_escalation_applied')} replay={replay.risk_escalation_applied}"
            )

        if evidence.get("final_risk_rule") == replay.final_risk_rule:
            checks.append(f"final_risk_rule replay matched: {replay.final_risk_rule}")
        else:
            errors.append(f"INVALID_EVIDENCE: final_risk_rule mismatch: evidence={evidence.get('final_risk_rule')} replay={replay.final_risk_rule}")

        saved_protected_paths = evidence.get("protected_paths_touched", [])
        if not isinstance(saved_protected_paths, list):
            saved_protected_paths = []
        if (replay.protected_paths_touched or saved_protected_paths) and evidence.get("risk_level") == LOW:
            errors.append("INVALID_EVIDENCE: protected path touched but saved risk_level is LOW")

        if replay.impact_risk in NOT_CHECKED_IMPACT_RISKS and status == CLEAN_CORE:
            errors.append("INVALID_EVIDENCE: NOT_CHECKED impact cannot be CLEAN_CORE")

        if replay.risk_level == HIGH and status != NEEDS_USER_GATE:
            errors.append("HIGH risk evidence must remain NEEDS_USER_GATE")
        elif replay.risk_level == HIGH:
            checks.append("HIGH risk remained NEEDS_USER_GATE")

        if replay.risk_level == LOW and status == NEEDS_USER_GATE:
            errors.append("LOW risk was over-gated as NEEDS_USER_GATE")
        elif replay.risk_level == LOW and status == CLEAN_CORE:
            checks.append("LOW risk remained CLEAN_CORE")

        if status == "PASS":
            errors.append("NOT_CHECKED/PASS invariant violated: PASS status is forbidden")
        else:
            checks.append("NOT_CHECKED was not promoted to PASS")

        if status != replay_law.status:
            errors.append(f"INVALID_EVIDENCE: law status mismatch: evidence={status} replay={replay_law.status}")
        else:
            checks.append(f"law status replay matched: {replay_law.status}")

        root = state_root(repo).resolve()
        run_id = str(evidence.get("run_id", ""))
        run_path = root / "runs" / run_id / "run.json"
        resolved_evidence = evidence_path.resolve()
        if _is_under(root, run_path) and _is_under(root, resolved_evidence):
            checks.append("runtime artifacts are under .aeg/")
        else:
            errors.append("runtime artifact path escaped .aeg/")

        if evidence.get("checks", {}).get("runtime_artifacts_under_state") is True:
            checks.append("evidence declares runtime artifacts under state")
        else:
            errors.append("evidence did not declare runtime artifacts under state")

    return VerifyResult(not errors, checks, errors, evidence)


def _verify_ledger_full_chain(repo: Path) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []
    ledger_path = state_root(repo) / LEDGER_FILE
    if not ledger_path.exists():
        return checks, [f"INVALID_EVIDENCE: ledger file missing: {ledger_path.relative_to(repo).as_posix()}"]

    parsed_entries: list[tuple[int, dict[str, Any]]] = []
    non_empty_count = 0
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        non_empty_count += 1
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"INVALID_EVIDENCE: ledger line {line_number} must be JSON object: {exc.msg}")
            continue
        if not isinstance(parsed, dict):
            errors.append(f"INVALID_EVIDENCE: ledger line {line_number} must be JSON object")
            continue
        parsed_entries.append((line_number, parsed))

    if non_empty_count == 0:
        errors.append("INVALID_EVIDENCE: ledger full-chain walk found no entries")
        return checks, errors
    checks.append(f"ledger full-chain walk parsed entries: {len(parsed_entries)}")

    previous_chain_hash: str | None = None
    for position, (line_number, entry) in enumerate(parsed_entries, start=1):
        current_chain_hash = _verify_ledger_chain_entry(
            repo,
            line_number,
            position,
            entry,
            previous_chain_hash,
            checks,
            errors,
        )
        previous_chain_hash = current_chain_hash if is_sha256_hex(current_chain_hash) else None

    if parsed_entries and not errors:
        checks.append("ledger full-chain walk validation passed")
    return checks, errors


def _verify_ledger_chain_entry(
    repo: Path,
    line_number: int,
    position: int,
    entry: dict[str, Any],
    previous_chain_hash: str | None,
    checks: list[str],
    errors: list[str],
) -> str | None:
    checks.append(f"ledger line {line_number} object parsed")
    for field in _LEDGER_REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"INVALID_EVIDENCE: ledger line {line_number} missing required field: {field}")
        _require_ledger_string(errors, line_number, entry, field)
    for field in _LEDGER_BOOL_FIELDS:
        _require_ledger_bool(errors, line_number, entry, field)
    for field in _LEDGER_STRING_METADATA_FIELDS:
        _require_ledger_string(errors, line_number, entry, field)
    for field in _LEDGER_HASH_FIELDS:
        _require_ledger_sha256(errors, line_number, entry, field)

    run_id = entry.get("run_id")
    risk_level = entry.get("risk_level")
    status = entry.get("status")
    if isinstance(risk_level, str) and risk_level not in RISK_LEVELS:
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} invalid risk_level: {risk_level}")
    if isinstance(status, str) and status not in STATUSES:
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} invalid status: {status}")

    sequence = entry.get("ledger_sequence_number")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} ledger_sequence_number must be integer")
    elif sequence != position:
        errors.append(
            "INVALID_EVIDENCE: ledger line "
            f"{line_number} ledger_sequence_number mismatch: actual={sequence} expected={position}"
        )
    else:
        checks.append(f"ledger line {line_number} ledger_sequence_number matched position")

    for field in _LEDGER_POSITION_FIELDS[1:]:
        if field not in entry:
            continue
        value = entry.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} must be integer")
        elif value != position:
            errors.append(
                f"INVALID_EVIDENCE: ledger line {line_number} {field} mismatch: actual={value} expected={position}"
            )
        else:
            checks.append(f"ledger line {line_number} {field} matched position")

    previous_hash = entry.get("previous_ledger_hash")
    if position == 1:
        if previous_hash in (LEDGER_PREVIOUS_HASH_GENESIS, LEDGER_PREVIOUS_HASH_NOT_AVAILABLE):
            checks.append(f"ledger line {line_number} genesis previous hash explicit")
        else:
            errors.append(f"INVALID_EVIDENCE: ledger line {line_number} first entry previous hash invalid")
    elif previous_chain_hash is None:
        errors.append(
            "INVALID_EVIDENCE: ledger line "
            f"{line_number} previous_ledger_hash cannot be verified after invalid prior chain hash"
        )
    elif previous_hash == previous_chain_hash:
        checks.append(f"ledger line {line_number} previous_ledger_hash matched prior chain hash")
    else:
        errors.append(
            "INVALID_EVIDENCE: ledger line "
            f"{line_number} previous_ledger_hash mismatch: actual={previous_hash} expected={previous_chain_hash}"
        )

    expected_evidence_rel = expected_run_rel = expected_manifest_rel = None
    if isinstance(run_id, str) and run_id.strip():
        expected_evidence_rel = expected_artifact_path(run_id, "evidence.json")
        expected_run_rel = expected_artifact_path(run_id, "run.json")
        expected_manifest_rel = expected_artifact_path(run_id, "manifest.json")

    evidence_path = _ledger_entry_file_path(
        repo,
        line_number,
        entry,
        "evidence_path",
        expected_evidence_rel,
        checks,
        errors,
    )
    run_path = _ledger_entry_file_path(repo, line_number, entry, "run_path", expected_run_rel, checks, errors)
    manifest_path = _ledger_entry_file_path(
        repo,
        line_number,
        entry,
        "manifest_path",
        expected_manifest_rel,
        checks,
        errors,
    )

    evidence = _load_ledger_object(evidence_path, line_number, "evidence", errors)
    run_payload = _load_ledger_object(run_path, line_number, "run", errors)
    manifest = _load_ledger_object(manifest_path, line_number, "manifest", errors)

    if manifest is not None:
        actual_manifest_hash = manifest_hash(manifest)
        _check_equal(checks, errors, f"ledger line {line_number} manifest_hash", entry.get("manifest_hash"), actual_manifest_hash)
        for field in _LEDGER_MANIFEST_BINDING_FIELDS:
            _check_equal(checks, errors, f"ledger line {line_number} manifest {field}", manifest.get(field), entry.get(field))
        expected_manifest_hash = expected_current_manifest_hash(manifest)
        _check_equal(
            checks,
            errors,
            f"ledger line {line_number} current_manifest_hash",
            entry.get("current_manifest_hash"),
            expected_manifest_hash,
        )
        _check_equal(
            checks,
            errors,
            f"ledger line {line_number} manifest current_manifest_hash",
            manifest.get("current_manifest_hash"),
            entry.get("current_manifest_hash"),
        )
        manifest_group_hash = sha256_json(ledger_integrity_manifest_fields(manifest))
        _check_equal(
            checks,
            errors,
            f"ledger line {line_number} manifest ledger_integrity_manifest_hash",
            manifest.get("ledger_integrity_manifest_hash"),
            manifest_group_hash,
        )
        for field in LEDGER_INTEGRITY_FIELDS:
            _check_equal(checks, errors, f"ledger line {line_number} manifest {field}", manifest.get(field), entry.get(field))

    if evidence is not None:
        for field in _LEDGER_EVIDENCE_BINDING_FIELDS:
            _check_equal(checks, errors, f"ledger line {line_number} evidence {field}", evidence.get(field), entry.get(field))
        if expected_manifest_rel is not None:
            _check_equal(
                checks,
                errors,
                f"ledger line {line_number} evidence bound_manifest_path",
                evidence.get("bound_manifest_path"),
                expected_manifest_rel,
            )
        _check_equal(
            checks,
            errors,
            f"ledger line {line_number} evidence bound_manifest_hash",
            evidence.get("bound_manifest_hash"),
            entry.get("manifest_hash"),
        )
        expected_evidence_hash = expected_current_evidence_hash(evidence)
        _check_equal(
            checks,
            errors,
            f"ledger line {line_number} current_evidence_hash",
            entry.get("current_evidence_hash"),
            expected_evidence_hash,
        )
        for field in LEDGER_INTEGRITY_FIELDS:
            _check_equal(checks, errors, f"ledger line {line_number} evidence {field}", evidence.get(field), entry.get(field))

    if run_payload is not None:
        for field in _LEDGER_RUN_BINDING_FIELDS:
            if field in run_payload:
                _check_equal(checks, errors, f"ledger line {line_number} run {field}", run_payload.get(field), entry.get(field))

    expected_entry_hash = expected_ledger_entry_hash(entry)
    _check_equal(
        checks,
        errors,
        f"ledger line {line_number} current_ledger_entry_hash",
        entry.get("current_ledger_entry_hash"),
        expected_entry_hash,
    )
    expected_chain_hash = expected_ledger_chain_hash(entry)
    _check_equal(
        checks,
        errors,
        f"ledger line {line_number} ledger_chain_hash",
        entry.get("ledger_chain_hash"),
        expected_chain_hash,
    )
    expected_metadata_hash = expected_ledger_integrity_metadata_hash(entry)
    _check_equal(
        checks,
        errors,
        f"ledger line {line_number} ledger_integrity_metadata_hash",
        entry.get("ledger_integrity_metadata_hash"),
        expected_metadata_hash,
    )
    current_chain_hash = entry.get("ledger_chain_hash")
    return current_chain_hash if isinstance(current_chain_hash, str) else None


def _ledger_entry_file_path(
    repo: Path,
    line_number: int,
    entry: dict[str, Any],
    field: str,
    expected_rel: str | None,
    checks: list[str],
    errors: list[str],
) -> Path | None:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        return None
    if Path(value).is_absolute():
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} must be repository-relative")
        return None
    resolved = (repo / value).resolve()
    root = state_root(repo).resolve()
    if not _is_under(root, resolved):
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} escaped .aeg/: {value}")
        return None
    if expected_rel is not None:
        _check_equal(checks, errors, f"ledger line {line_number} {field}", value, expected_rel)
    if resolved.exists():
        checks.append(f"ledger line {line_number} {field} exists")
    else:
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} missing: {value}")
    return resolved


def _load_ledger_object(path: Path | None, line_number: int, label: str, errors: list[str]) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {label} could not be parsed: {exc}")
        return None
    if not isinstance(parsed, dict):
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {label} must be object")
        return None
    return parsed


def _require_ledger_string(errors: list[str], line_number: int, entry: dict[str, Any], field: str) -> None:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} must be non-empty string")


def _require_ledger_bool(errors: list[str], line_number: int, entry: dict[str, Any], field: str) -> None:
    if not isinstance(entry.get(field), bool):
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} must be boolean")


def _require_ledger_sha256(errors: list[str], line_number: int, entry: dict[str, Any], field: str) -> None:
    value = entry.get(field)
    if not isinstance(value, str) or not is_sha256_hex(value):
        errors.append(f"INVALID_EVIDENCE: ledger line {line_number} {field} must be sha256 hex")


def _verify_manifest_binding(
    repo: Path,
    evidence: dict[str, Any],
    evidence_path: Path,
    ledger_entry: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    run_id = evidence.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return None, checks, ["INVALID_EVIDENCE: manifest binding requires evidence run_id"]

    expected_manifest_rel = expected_artifact_path(run_id, "manifest.json")
    expected_evidence_rel = expected_artifact_path(run_id, "evidence.json")
    expected_run_rel = expected_artifact_path(run_id, "run.json")

    bound_manifest_path = evidence.get("bound_manifest_path")
    if not isinstance(bound_manifest_path, str) or not bound_manifest_path.strip():
        return None, checks, ["INVALID_EVIDENCE: missing bound_manifest_path"]
    if Path(bound_manifest_path).is_absolute():
        errors.append("INVALID_EVIDENCE: bound_manifest_path must be repository-relative")
        return None, checks, errors
    if bound_manifest_path != expected_manifest_rel:
        errors.append(
            "INVALID_EVIDENCE: bound_manifest_path mismatch: "
            f"evidence={bound_manifest_path} expected={expected_manifest_rel}"
        )

    manifest_path = (repo / bound_manifest_path).resolve()
    root = state_root(repo).resolve()
    if not _is_under(root, manifest_path):
        errors.append(f"INVALID_EVIDENCE: manifest path escaped .aeg/: {bound_manifest_path}")
        return None, checks, errors
    if not manifest_path.exists():
        errors.append(f"INVALID_EVIDENCE: manifest missing: {bound_manifest_path}")
        return None, checks, errors

    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"INVALID_EVIDENCE: manifest could not be parsed: {exc}")
        return None, checks, errors
    if not isinstance(loaded, dict):
        errors.append("INVALID_EVIDENCE: manifest must be object")
        return None, checks, errors
    manifest = loaded
    manifest_forbidden_errors = validate_no_forbidden_raw_prompt_response_keys(manifest, label="manifest")
    if manifest_forbidden_errors:
        errors.extend(manifest_forbidden_errors)
    else:
        checks.append("manifest contains no forbidden raw/secret storage keys")

    actual_manifest_hash = manifest_hash(manifest)
    if evidence.get("bound_manifest_hash") == actual_manifest_hash:
        checks.append(f"manifest hash matched: {actual_manifest_hash[:12]}")
    else:
        errors.append(
            "INVALID_EVIDENCE: manifest hash mismatch: "
            f"evidence={evidence.get('bound_manifest_hash')} actual={actual_manifest_hash}"
        )

    if manifest.get("manifest_version") == RUN_MANIFEST_V1:
        checks.append("manifest version valid")
    else:
        errors.append(f"INVALID_EVIDENCE: manifest_version must be {RUN_MANIFEST_V1}")

    actual_evidence_rel = repo_relative_path(repo, evidence_path)
    if actual_evidence_rel == expected_evidence_rel:
        checks.append("evidence path matches expected run path")
    else:
        errors.append(
            "INVALID_EVIDENCE: loaded evidence path mismatch: "
            f"actual={actual_evidence_rel} expected={expected_evidence_rel}"
        )

    if ledger_entry:
        _check_equal(checks, errors, "ledger run_id", ledger_entry.get("run_id"), run_id)
        if ledger_entry.get("evidence_path") is not None:
            _check_equal(checks, errors, "ledger evidence_path", ledger_entry.get("evidence_path"), expected_evidence_rel)
        if ledger_entry.get("run_path") is not None:
            _check_equal(checks, errors, "ledger run_path", ledger_entry.get("run_path"), expected_run_rel)
        if ledger_entry.get("manifest_path") is not None:
            _check_equal(checks, errors, "ledger manifest_path", ledger_entry.get("manifest_path"), expected_manifest_rel)
        if ledger_entry.get("manifest_hash") is not None:
            _check_equal(checks, errors, "ledger manifest_hash", ledger_entry.get("manifest_hash"), actual_manifest_hash)

    _check_equal(checks, errors, "manifest run_id", manifest.get("run_id"), run_id)
    _check_equal(checks, errors, "manifest repo_root", manifest.get("repo_root"), evidence.get("repo_root"))
    _check_equal(checks, errors, "manifest branch", manifest.get("branch"), evidence.get("branch"))
    _check_equal(checks, errors, "manifest head_sha", manifest.get("head_sha"), evidence.get("head_sha"))
    _check_equal(checks, errors, "manifest tree_sha", manifest.get("tree_sha"), evidence.get("tree_sha"))
    _check_equal(
        checks,
        errors,
        "manifest changed_files_source",
        manifest.get("changed_files_source"),
        evidence.get("changed_files_source"),
    )
    _check_equal(checks, errors, "manifest risk_level", manifest.get("risk_level"), evidence.get("risk_level"))
    _check_equal(checks, errors, "manifest status", manifest.get("status"), evidence.get("status"))
    _check_equal(checks, errors, "manifest safe_default", manifest.get("safe_default"), evidence.get("safe_default"))
    evidence_citizen_one = citizen_one_manifest_fields(evidence)
    manifest_citizen_one = citizen_one_manifest_fields(manifest)
    for field in CITIZEN_ONE_EVIDENCE_FIELDS:
        _check_equal(checks, errors, f"manifest {field}", manifest.get(field), evidence.get(field))
    _check_equal(
        checks,
        errors,
        "manifest citizen_one_evidence_hash",
        manifest.get("citizen_one_evidence_hash"),
        sha256_json(manifest_citizen_one),
    )
    if evidence_citizen_one == manifest_citizen_one:
        checks.append("citizen one evidence fields matched manifest")
    else:
        errors.append("INVALID_EVIDENCE: citizen one evidence fields mismatch")

    evidence_provider_adapter = provider_adapter_manifest_fields(evidence)
    manifest_provider_adapter = provider_adapter_manifest_fields(manifest)
    for field in PROVIDER_ADAPTER_DISABLED_FIELDS:
        _check_equal(checks, errors, f"manifest {field}", manifest.get(field), evidence.get(field))
    _check_equal(
        checks,
        errors,
        "manifest provider_adapter_evidence_hash",
        manifest.get("provider_adapter_evidence_hash"),
        sha256_json(manifest_provider_adapter),
    )
    if evidence_provider_adapter == manifest_provider_adapter:
        checks.append("provider adapter disabled fields matched manifest")
    else:
        errors.append("INVALID_EVIDENCE: provider adapter disabled fields mismatch")
    checks.append("provider adapter output is reported_only and not an external oracle")

    _check_manifest_field_group(
        checks,
        errors,
        "provider runtime state metadata",
        PROVIDER_RUNTIME_STATE_FIELDS,
        "provider_runtime_state_metadata_hash",
        evidence,
        manifest,
        provider_runtime_state_manifest_fields(evidence),
        provider_runtime_state_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "provider selection metadata",
        PROVIDER_SELECTION_METADATA_FIELDS,
        "provider_selection_metadata_hash",
        evidence,
        manifest,
        provider_selection_manifest_fields(evidence),
        provider_selection_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "provider secret/env safe metadata",
        PROVIDER_SECRET_ENV_METADATA_FIELDS,
        "provider_secret_env_metadata_hash",
        evidence,
        manifest,
        provider_secret_env_manifest_fields(evidence),
        provider_secret_env_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "provider network opt-in guard metadata",
        PROVIDER_NETWORK_GUARD_METADATA_FIELDS,
        "provider_network_guard_metadata_hash",
        evidence,
        manifest,
        provider_network_guard_manifest_fields(evidence),
        provider_network_guard_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "provider request safe metadata",
        PROVIDER_REQUEST_METADATA_FIELDS,
        "provider_request_safe_metadata_hash",
        evidence,
        manifest,
        provider_request_manifest_fields(evidence),
        provider_request_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "provider response/error safe metadata",
        PROVIDER_RESPONSE_ERROR_METADATA_FIELDS,
        "provider_response_error_safe_metadata_hash",
        evidence,
        manifest,
        provider_response_error_manifest_fields(evidence),
        provider_response_error_manifest_fields(manifest),
    )
    checks.append("provider runtime opt-in guard metadata is not an external oracle")

    evidence_prompt_redaction = prompt_redaction_manifest_fields(evidence)
    manifest_prompt_redaction = prompt_redaction_manifest_fields(manifest)
    for field in PROMPT_REDACTION_METADATA_FIELDS:
        _check_equal(checks, errors, f"manifest {field}", manifest.get(field), evidence.get(field))
    _check_equal(
        checks,
        errors,
        "manifest prompt_redaction_metadata_hash",
        manifest.get("prompt_redaction_metadata_hash"),
        sha256_json(manifest_prompt_redaction),
    )
    if evidence_prompt_redaction == manifest_prompt_redaction:
        checks.append("prompt redaction metadata fields matched manifest")
    else:
        errors.append("INVALID_EVIDENCE: prompt redaction metadata fields mismatch")

    evidence_response_redaction = response_redaction_manifest_fields(evidence)
    manifest_response_redaction = response_redaction_manifest_fields(manifest)
    for field in RESPONSE_REDACTION_METADATA_FIELDS:
        _check_equal(checks, errors, f"manifest {field}", manifest.get(field), evidence.get(field))
    _check_equal(
        checks,
        errors,
        "manifest response_redaction_metadata_hash",
        manifest.get("response_redaction_metadata_hash"),
        sha256_json(manifest_response_redaction),
    )
    if evidence_response_redaction == manifest_response_redaction:
        checks.append("response redaction metadata fields matched manifest")
    else:
        errors.append("INVALID_EVIDENCE: response redaction metadata fields mismatch")
    checks.append("provider/model response remains reported_only and not an external oracle")

    _check_manifest_field_group(
        checks,
        errors,
        "action boundary scaffold metadata",
        ACTION_BOUNDARY_FIELDS,
        "action_boundary_metadata_hash",
        evidence,
        manifest,
        action_boundary_manifest_fields(evidence),
        action_boundary_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "capability isolation scaffold metadata",
        CAPABILITY_ISOLATION_FIELDS,
        "capability_isolation_metadata_hash",
        evidence,
        manifest,
        capability_isolation_manifest_fields(evidence),
        capability_isolation_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "tool surface scaffold metadata",
        TOOL_SURFACE_FIELDS,
        "tool_surface_authority_metadata_hash",
        evidence,
        manifest,
        tool_surface_manifest_fields(evidence),
        tool_surface_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "executor capability exposure metadata",
        EXECUTOR_CAPABILITY_EXPOSURE_FIELDS,
        "executor_capability_exposure_manifest_hash",
        evidence,
        manifest,
        capability_exposure_manifest_fields(evidence),
        capability_exposure_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "evidence store trust boundary metadata",
        EVIDENCE_STORE_TRUST_FIELDS,
        "evidence_store_trust_manifest_hash",
        evidence,
        manifest,
        evidence_store_trust_manifest_fields(evidence),
        evidence_store_trust_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "aeg state write denial metadata",
        AEG_STATE_WRITE_DENIAL_FIELDS,
        "aeg_state_write_denial_manifest_hash",
        evidence,
        manifest,
        aeg_state_write_denial_manifest_fields(evidence),
        aeg_state_write_denial_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "mediated write boundary scaffold metadata",
        MEDIATED_WRITE_BOUNDARY_FIELDS,
        "mediated_write_boundary_manifest_hash",
        evidence,
        manifest,
        mediated_write_boundary_manifest_fields(evidence),
        mediated_write_boundary_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "write bypass harness scaffold metadata",
        WRITE_BYPASS_HARNESS_FIELDS,
        "write_bypass_harness_manifest_hash",
        evidence,
        manifest,
        write_bypass_harness_manifest_fields(evidence),
        write_bypass_harness_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "pre-live executor gate metadata",
        PRE_LIVE_EXECUTOR_GATE_FIELDS,
        "pre_live_executor_gate_manifest_hash",
        evidence,
        manifest,
        pre_live_executor_gate_manifest_fields(evidence),
        pre_live_executor_gate_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "store write mediation metadata",
        STORE_WRITE_MEDIATION_FIELDS,
        "store_write_mediation_manifest_hash",
        evidence,
        manifest,
        store_write_mediation_manifest_fields(evidence),
        store_write_mediation_manifest_fields(manifest),
    )
    _check_manifest_field_group(
        checks,
        errors,
        "ledger integrity scaffold metadata",
        LEDGER_INTEGRITY_FIELDS,
        "ledger_integrity_manifest_hash",
        evidence,
        manifest,
        ledger_integrity_manifest_fields(evidence),
        ledger_integrity_manifest_fields(manifest),
    )

    evidence_proposal = proposal_manifest_fields(evidence)
    manifest_proposal = proposal_manifest_fields(manifest)
    if evidence.get("citizen_one_requested") is True:
        for field in PROPOSAL_CONTRACT_FIELDS:
            _check_equal(checks, errors, f"manifest {field}", manifest.get(field), evidence.get(field))
        _check_equal(
            checks,
            errors,
            "manifest proposal_evidence_hash",
            manifest.get("proposal_evidence_hash"),
            sha256_json(manifest_proposal),
        )
        if evidence_proposal == manifest_proposal:
            checks.append("proposal contract fields matched manifest")
        else:
            errors.append("INVALID_EVIDENCE: proposal contract fields mismatch")
        checks.append("proposal contract is reported_only and not an external oracle")
    else:
        for field in (*PROPOSAL_CONTRACT_FIELDS, "proposal_evidence_hash"):
            if field in evidence or field in manifest:
                errors.append(f"INVALID_EVIDENCE: proposal field present without Citizen One opt-in: {field}")
    _check_equal(checks, errors, "manifest pre_snapshot_source", manifest.get("pre_snapshot_source"), evidence.get("pre_snapshot_source"))
    _check_equal(checks, errors, "manifest post_snapshot_source", manifest.get("post_snapshot_source"), evidence.get("post_snapshot_source"))
    _check_equal(checks, errors, "manifest snapshot_collector", manifest.get("snapshot_collector"), evidence.get("snapshot_collector"))
    _check_equal(checks, errors, "manifest mutation_delta_source", manifest.get("mutation_delta_source"), evidence.get("mutation_delta_source"))
    _check_equal(
        checks,
        errors,
        "manifest protected_path_mutation_detected",
        manifest.get("protected_path_mutation_detected"),
        evidence.get("protected_path_mutation_detected"),
    )
    _check_equal(
        checks,
        errors,
        "manifest mutation_boundary_status",
        manifest.get("mutation_boundary_status"),
        evidence.get("mutation_boundary_status"),
    )
    _check_equal(checks, errors, "bound_run_id", evidence.get("bound_run_id"), run_id)
    _check_equal(checks, errors, "bound_repo_root", evidence.get("bound_repo_root"), manifest.get("repo_root"))
    _check_equal(checks, errors, "bound_branch", evidence.get("bound_branch"), manifest.get("branch"))
    _check_equal(checks, errors, "bound_head_sha", evidence.get("bound_head_sha"), manifest.get("head_sha"))
    _check_equal(checks, errors, "bound_tree_sha", evidence.get("bound_tree_sha"), manifest.get("tree_sha"))

    _check_equal(checks, errors, "manifest evidence_path", manifest.get("evidence_path"), expected_evidence_rel)
    _check_equal(checks, errors, "manifest run_path", manifest.get("run_path"), expected_run_rel)

    evidence_changed_files = evidence.get("changed_files")
    manifest_changed_files = manifest.get("changed_files")
    if not _is_string_list(evidence_changed_files):
        errors.append("INVALID_EVIDENCE: evidence changed_files must be list of strings")
        evidence_changed_files = []
    if not _is_string_list(manifest_changed_files):
        errors.append("INVALID_EVIDENCE: manifest changed_files must be list of strings")
        manifest_changed_files = []
    if evidence_changed_files == manifest_changed_files:
        checks.append("manifest changed_files matched evidence")
    else:
        errors.append(
            "INVALID_EVIDENCE: changed_files mismatch: "
            f"evidence={evidence_changed_files} manifest={manifest_changed_files}"
        )

    evidence_changed_files_hash = changed_files_hash(evidence_changed_files)
    manifest_changed_files_hash = changed_files_hash(manifest_changed_files)
    _check_equal(
        checks,
        errors,
        "manifest changed_files_hash",
        manifest.get("changed_files_hash"),
        manifest_changed_files_hash,
    )
    _check_equal(
        checks,
        errors,
        "bound_changed_files_hash",
        evidence.get("bound_changed_files_hash"),
        evidence_changed_files_hash,
    )
    _check_equal(checks, errors, "changed_files hash", evidence_changed_files_hash, manifest_changed_files_hash)

    for field in (
        "pre_run_changed_files",
        "post_run_changed_files",
        "computed_mutation_delta",
        "pre_existing_dirty_tree",
        "executor_created_mutation",
    ):
        evidence_value = evidence.get(field)
        manifest_value = manifest.get(field)
        if not isinstance(evidence_value, list):
            errors.append(f"INVALID_EVIDENCE: evidence {field} must be list")
            evidence_value = []
        if not isinstance(manifest_value, list):
            errors.append(f"INVALID_EVIDENCE: manifest {field} must be list")
            manifest_value = []
        if evidence_value == manifest_value:
            checks.append(f"manifest {field} matched evidence")
        else:
            errors.append(f"INVALID_EVIDENCE: {field} mismatch: evidence={evidence_value} manifest={manifest_value}")
        expected_hash = sha256_json(manifest_value)
        _check_equal(checks, errors, f"manifest {field}_hash", manifest.get(f"{field}_hash"), expected_hash)

    snapshot_trust_boundary = evidence.get("snapshot_trust_boundary")
    manifest_snapshot_trust_boundary = manifest.get("snapshot_trust_boundary")
    if not isinstance(snapshot_trust_boundary, dict):
        errors.append("INVALID_EVIDENCE: snapshot_trust_boundary must be object")
        snapshot_trust_boundary = {}
    if not isinstance(manifest_snapshot_trust_boundary, dict):
        errors.append("INVALID_EVIDENCE: manifest snapshot_trust_boundary must be object")
        manifest_snapshot_trust_boundary = {}
    if snapshot_trust_boundary == manifest_snapshot_trust_boundary:
        checks.append("manifest snapshot_trust_boundary matched evidence")
    else:
        errors.append("INVALID_EVIDENCE: snapshot_trust_boundary mismatch")
    _check_equal(
        checks,
        errors,
        "manifest snapshot_trust_boundary_hash",
        manifest.get("snapshot_trust_boundary_hash"),
        sha256_json(manifest_snapshot_trust_boundary),
    )
    _check_equal(
        checks,
        errors,
        "bound_pre_run_changed_files_hash",
        evidence.get("bound_pre_run_changed_files_hash"),
        sha256_json(evidence.get("pre_run_changed_files", [])),
    )
    _check_equal(
        checks,
        errors,
        "bound_post_run_changed_files_hash",
        evidence.get("bound_post_run_changed_files_hash"),
        sha256_json(evidence.get("post_run_changed_files", [])),
    )
    _check_equal(
        checks,
        errors,
        "bound_computed_mutation_delta_hash",
        evidence.get("bound_computed_mutation_delta_hash"),
        sha256_json(evidence.get("computed_mutation_delta", [])),
    )
    _check_equal(
        checks,
        errors,
        "bound_snapshot_trust_boundary_hash",
        evidence.get("bound_snapshot_trust_boundary_hash"),
        sha256_json(snapshot_trust_boundary),
    )
    _check_equal(
        checks,
        errors,
        "bound_action_boundary_metadata_hash",
        evidence.get("bound_action_boundary_metadata_hash"),
        sha256_json(action_boundary_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_capability_isolation_metadata_hash",
        evidence.get("bound_capability_isolation_metadata_hash"),
        sha256_json(capability_isolation_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_tool_surface_metadata_hash",
        evidence.get("bound_tool_surface_metadata_hash"),
        sha256_json(tool_surface_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_executor_capability_exposure_metadata_hash",
        evidence.get("bound_executor_capability_exposure_metadata_hash"),
        sha256_json(capability_exposure_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_evidence_store_trust_metadata_hash",
        evidence.get("bound_evidence_store_trust_metadata_hash"),
        sha256_json(evidence_store_trust_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_aeg_state_write_denial_metadata_hash",
        evidence.get("bound_aeg_state_write_denial_metadata_hash"),
        sha256_json(aeg_state_write_denial_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_mediated_write_boundary_metadata_hash",
        evidence.get("bound_mediated_write_boundary_metadata_hash"),
        sha256_json(mediated_write_boundary_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_write_bypass_harness_metadata_hash",
        evidence.get("bound_write_bypass_harness_metadata_hash"),
        sha256_json(write_bypass_harness_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_pre_live_executor_gate_metadata_hash",
        evidence.get("bound_pre_live_executor_gate_metadata_hash"),
        sha256_json(pre_live_executor_gate_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_store_write_mediation_metadata_hash",
        evidence.get("bound_store_write_mediation_metadata_hash"),
        sha256_json(store_write_mediation_manifest_fields(evidence)),
    )
    _check_equal(
        checks,
        errors,
        "bound_ledger_integrity_metadata_hash",
        evidence.get("bound_ledger_integrity_metadata_hash"),
        sha256_json(ledger_integrity_manifest_fields(evidence)),
    )

    task_text = evidence.get("task_text")
    if isinstance(task_text, str):
        _check_equal(checks, errors, "manifest task_text_hash", manifest.get("task_text_hash"), sha256_text(task_text))
    else:
        errors.append("INVALID_EVIDENCE: task_text must be string for manifest binding")

    if evidence.get("binding_status") != BOUND:
        errors.append("INVALID_EVIDENCE: binding_status is not BOUND")
    else:
        checks.append("binding_status is BOUND")

    return manifest, checks, errors


def _verify_mutation_boundary(evidence: dict[str, Any], manifest: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    pre_snapshot = evidence.get("pre_run_changed_files")
    post_snapshot = evidence.get("post_run_changed_files")
    if not _is_object_list(pre_snapshot):
        errors.append("INVALID_EVIDENCE: pre_run_changed_files must be list of objects")
        pre_snapshot = []
    if not _is_object_list(post_snapshot):
        errors.append("INVALID_EVIDENCE: post_run_changed_files must be list of objects")
        post_snapshot = []

    recomputed_delta = compute_mutation_delta(pre_snapshot, post_snapshot)
    saved_delta = evidence.get("computed_mutation_delta")
    if not _is_object_list(saved_delta):
        errors.append("INVALID_EVIDENCE: computed_mutation_delta must be list of objects")
        saved_delta = []
    if saved_delta == recomputed_delta:
        checks.append("computed_mutation_delta replay matched independent snapshots")
    else:
        errors.append(
            "INVALID_EVIDENCE: computed_mutation_delta mismatch: "
            f"evidence={saved_delta} replay={recomputed_delta}"
        )

    boundary = evidence.get("snapshot_trust_boundary")
    if not isinstance(boundary, dict):
        errors.append("INVALID_EVIDENCE: snapshot_trust_boundary must be object")
        boundary = {}
    trusted = (
        evidence.get("pre_snapshot_source") == GIT_STATUS_PORCELAIN_V1
        and evidence.get("post_snapshot_source") == GIT_STATUS_PORCELAIN_V1
        and evidence.get("snapshot_collector") == SNAPSHOT_COLLECTOR_GIT_STATUS_V1
        and boundary.get("executor_controlled") is False
        and boundary.get("pre_captured_before_executor") is True
        and boundary.get("post_captured_after_executor") is True
        and boundary.get("same_collector") is True
        and boundary.get("trust_boundary_satisfied") is True
    )
    if trusted:
        checks.append("mutation boundary snapshot trust satisfied")
    else:
        errors.append("INVALID_EVIDENCE: mutation boundary snapshot trust not satisfied")

    expected_status = _expected_mutation_boundary_status(trusted, pre_snapshot, recomputed_delta)
    if evidence.get("mutation_boundary_status") == expected_status:
        checks.append(f"mutation_boundary_status replay matched: {expected_status}")
    else:
        errors.append(
            "INVALID_EVIDENCE: mutation_boundary_status mismatch: "
            f"evidence={evidence.get('mutation_boundary_status')} replay={expected_status}"
        )

    expected_delta_source = MUTATION_DELTA_SOURCE_COMPUTED if trusted else evidence.get("mutation_delta_source")
    if trusted and evidence.get("mutation_delta_source") != expected_delta_source:
        errors.append(
            "INVALID_EVIDENCE: mutation_delta_source mismatch: "
            f"evidence={evidence.get('mutation_delta_source')} replay={expected_delta_source}"
        )
    elif trusted:
        checks.append(f"mutation_delta_source replay matched: {expected_delta_source}")

    if evidence.get("mutation_boundary_status") == MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT:
        errors.append("INVALID_EVIDENCE: untrusted snapshot boundary cannot be replay-clean")

    if evidence.get("status") == "PASS":
        errors.append("INVALID_EVIDENCE: mutation boundary cannot promote status PASS")

    if manifest is not None and manifest.get("computed_mutation_delta") == recomputed_delta:
        checks.append("manifest computed_mutation_delta replay matched")
    elif manifest is not None:
        errors.append("INVALID_EVIDENCE: manifest computed_mutation_delta mismatch with replay")

    return checks, errors


def _verify_action_boundary(evidence: dict[str, Any], manifest: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("action boundary replay used recorded metadata only")
    actions = evidence.get("intercepted_actions")
    if not _is_object_list(actions):
        errors.append("INVALID_EVIDENCE: intercepted_actions must be list of objects")
        actions = []

    if evidence.get("computed_action_log_hash") == expected_action_log_hash(evidence):
        checks.append("computed_action_log_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: computed_action_log_hash mismatch")

    action_count = evidence.get("action_count")
    expected_action_count = evidence.get("expected_action_count")
    if action_count == len(actions) == expected_action_count == 0:
        checks.append("action_count replay matched expected no-op count: 0")
    else:
        errors.append(
            "INVALID_EVIDENCE: action_count replay mismatch: "
            f"action_count={action_count} expected={expected_action_count} intercepted={len(actions)}"
        )

    authority_defaults = all(evidence.get(field) is False for field in ACTION_AUTHORITY_FIELDS)
    if authority_defaults:
        checks.append("action authority flags default false")
    else:
        errors.append("INVALID_EVIDENCE: action authority flags must default false")

    executor_reported = evidence.get("executor_reported_actions")
    if (
        isinstance(executor_reported, dict)
        and executor_reported.get("trust_boundary") == "reported_only"
        and executor_reported.get("judgment_basis") is False
    ):
        checks.append("executor_reported_actions remains reported_only context, not judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_actions cannot become judgment basis")

    if evidence.get("command_enumeration_only") is True and evidence.get("action_boundary_status") == ACTION_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: command_enumeration_only cannot produce ACTION_BOUNDARY_CLEAN")
    else:
        checks.append("command enumeration alone grants no authority")

    if evidence.get("no_matched_dangerous_command") is True and evidence.get("action_boundary_status") == ACTION_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN")
    else:
        checks.append("no matched dangerous command did not imply action clean")

    if evidence.get("mutation_boundary_status") == MUTATION_BOUNDARY_CLEAN and evidence.get("action_boundary_status") != ACTION_BOUNDARY_CLEAN:
        checks.append("mutation boundary clean did not imply action boundary clean")
    if evidence.get("changed_files") == [] and evidence.get("action_boundary_status") != ACTION_BOUNDARY_CLEAN:
        checks.append("git diff clean did not imply action clean")

    if evidence.get("action_boundary_status") == ACTION_BOUNDARY_NOT_CHECKED:
        checks.append("action boundary status remained ACTION_BOUNDARY_NOT_CHECKED")
    else:
        errors.append("INVALID_EVIDENCE: action boundary status must not claim ACTION_BOUNDARY_CLEAN")

    if manifest is not None:
        manifest_actions = manifest.get("intercepted_actions")
        if manifest_actions == actions:
            checks.append("manifest intercepted_actions matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest intercepted_actions mismatch with evidence")
        if manifest.get("computed_action_log_hash") == evidence.get("computed_action_log_hash"):
            checks.append("manifest computed_action_log_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest computed_action_log_hash mismatch with evidence")

    return checks, errors


def _verify_capability_isolation(evidence: dict[str, Any], manifest: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("capability isolation replay used recorded scaffold metadata only")

    if evidence.get("capability_matrix_hash") == expected_capability_matrix_hash(evidence):
        checks.append("capability_matrix_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: capability_matrix_hash mismatch")

    if evidence.get("capability_isolation_proof_hash") == expected_capability_isolation_proof_hash(evidence):
        checks.append("capability_isolation_proof_hash replay matched scaffold unavailable proof")
    else:
        errors.append("INVALID_EVIDENCE: capability_isolation_proof_hash mismatch")

    if evidence.get("capability_isolation_enabled") is False:
        checks.append("capability isolation default disabled")
    else:
        errors.append("INVALID_EVIDENCE: capability_isolation_enabled must be false in scaffold v0")

    authority_flags_valid = True
    for field in CAPABILITY_AUTHORITY_FIELDS:
        value = evidence.get(field)
        if not isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be bool")
            authority_flags_valid = False
        elif value is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must default false")
            errors.append(
                "INVALID_EVIDENCE: authority_granted=true without implemented "
                f"capability isolation proof: {field}"
            )
            authority_flags_valid = False
    if authority_flags_valid:
        checks.append("capability authority flags default false")
    else:
        errors.append("INVALID_EVIDENCE: capability authority flags must default false")

    executor_reported = evidence.get("executor_reported_capabilities")
    if (
        isinstance(executor_reported, dict)
        and isinstance(executor_reported.get("capabilities"), list)
        and executor_reported.get("reported_capability_count") == len(executor_reported.get("capabilities"))
        and executor_reported.get("trust_boundary") == "reported_only"
        and executor_reported.get("judgment_basis") is False
    ):
        checks.append("executor_reported_capabilities remains reported_only context, not judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_capabilities cannot become judgment basis")

    boundary_status = evidence.get("capability_boundary_status")
    if boundary_status == CAPABILITY_BOUNDARY_NOT_CHECKED:
        checks.append("capability boundary status remained CAPABILITY_BOUNDARY_NOT_CHECKED")
        checks.append("unavailable capability proof remained NOT_CHECKED")
    else:
        errors.append("INVALID_EVIDENCE: capability_boundary_status must not claim CLEAN or implemented isolation")

    if boundary_status == CAPABILITY_BOUNDARY_CLEAN or boundary_status == ACTION_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: capability not implemented cannot be CLEAN")
    else:
        checks.append("capability not implemented did not claim CLEAN")

    if evidence.get("command_enumeration_only") is True and boundary_status == CAPABILITY_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: command enumeration only cannot produce CAPABILITY_BOUNDARY_CLEAN")
    else:
        checks.append("command enumeration only did not produce capability clean")

    if evidence.get("judgment_basis") == "executor_reported_capabilities":
        errors.append("INVALID_EVIDENCE: executor_reported_capabilities cannot become judgment basis")

    if manifest is not None:
        if manifest.get("capability_matrix_hash") == evidence.get("capability_matrix_hash"):
            checks.append("manifest capability_matrix_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest capability_matrix_hash mismatch with evidence")
        if manifest.get("capability_isolation_proof_hash") == evidence.get("capability_isolation_proof_hash"):
            checks.append("manifest capability_isolation_proof_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest capability_isolation_proof_hash mismatch with evidence")

    return checks, errors


def _verify_tool_surface_authority(evidence: dict[str, Any], manifest: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("tool surface replay used recorded scaffold metadata only")

    if evidence.get("tool_authority_grant_hash") == expected_tool_authority_grant_hash(evidence):
        checks.append("tool_authority_grant_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: tool_authority_grant_hash mismatch")

    if evidence.get("tool_surface_metadata_hash") == expected_tool_surface_metadata_hash(evidence):
        checks.append("tool_surface_metadata_hash replay matched scaffold unavailable proof")
    else:
        errors.append("INVALID_EVIDENCE: tool_surface_metadata_hash mismatch")

    if evidence.get("tool_surface_enabled") is False:
        checks.append("tool surface default disabled")
    else:
        errors.append("INVALID_EVIDENCE: tool_surface_enabled must be false in scaffold v0")

    requested = evidence.get("requested_tool_capabilities")
    granted = evidence.get("granted_tool_capabilities")
    denied = evidence.get("denied_tool_capabilities")
    if requested == [] and granted == [] and denied == []:
        checks.append("tool capability request/grant/deny lists default empty")
    else:
        errors.append("INVALID_EVIDENCE: tool capability lists must default empty")

    if (
        evidence.get("tool_authority_grant_count")
        == evidence.get("expected_tool_authority_grant_count")
        == 0
        and granted == []
    ):
        checks.append("tool authority grant count replay matched expected zero: 0")
        checks.append("no granted tool authority by default")
    else:
        errors.append(
            "INVALID_EVIDENCE: tool authority grant count mismatch: "
            f"grant_count={evidence.get('tool_authority_grant_count')} "
            f"expected={evidence.get('expected_tool_authority_grant_count')} granted={granted}"
        )

    authority_flags_valid = True
    for field in TOOL_AUTHORITY_GRANT_FIELDS:
        value = evidence.get(field)
        if not isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be bool")
            authority_flags_valid = False
        elif value is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must default false")
            errors.append(
                "INVALID_EVIDENCE: authority_granted=true without implemented "
                f"tool surface proof/source/trust boundary: {field}"
            )
            authority_flags_valid = False
    if authority_flags_valid:
        checks.append("tool authority flags default false")
    else:
        errors.append("INVALID_EVIDENCE: tool authority flags must default false")

    executor_reported = evidence.get("executor_reported_tool_usage")
    if (
        isinstance(executor_reported, dict)
        and isinstance(executor_reported.get("tools"), list)
        and executor_reported.get("reported_tool_count") == len(executor_reported.get("tools"))
        and executor_reported.get("trust_boundary") == "reported_only"
        and executor_reported.get("judgment_basis") is False
    ):
        checks.append("executor_reported_tool_usage remains reported_only context, not judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_tool_usage cannot become judgment basis")

    surface_status = evidence.get("tool_surface_status")
    if surface_status == TOOL_SURFACE_SCAFFOLD_ONLY:
        checks.append("tool surface status remained TOOL_SURFACE_SCAFFOLD_ONLY")
    else:
        errors.append("INVALID_EVIDENCE: tool_surface_status must not claim CLEAN or implemented tool surface")

    if surface_status in (TOOL_SURFACE_CLEAN, ACTION_BOUNDARY_CLEAN, CAPABILITY_BOUNDARY_CLEAN):
        errors.append("INVALID_EVIDENCE: tool surface not implemented cannot be CLEAN")
    else:
        checks.append("tool surface not implemented did not claim CLEAN")

    if evidence.get("command_enumeration_only") is True and any(
        evidence.get(field) is True for field in TOOL_AUTHORITY_GRANT_FIELDS
    ):
        errors.append("INVALID_EVIDENCE: command denylist/enumeration alone cannot grant tool authority")
    else:
        checks.append("command denylist alone grants no tool authority")

    if evidence.get("judgment_basis") == "executor_reported_tool_usage":
        errors.append("INVALID_EVIDENCE: executor_reported_tool_usage cannot become judgment basis")

    if manifest is not None:
        if manifest.get("tool_authority_grant_hash") == evidence.get("tool_authority_grant_hash"):
            checks.append("manifest tool_authority_grant_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest tool_authority_grant_hash mismatch with evidence")
        if manifest.get("tool_surface_metadata_hash") == evidence.get("tool_surface_metadata_hash"):
            checks.append("manifest tool_surface_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest tool_surface_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_executor_capability_exposure(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("executor capability exposure replay used recorded scaffold metadata only")

    if evidence.get("executor_capability_exposure_hash") == expected_executor_capability_exposure_hash(evidence):
        checks.append("executor_capability_exposure_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: executor_capability_exposure_hash mismatch")

    if evidence.get("executor_capability_exposure_metadata_hash") == expected_executor_capability_exposure_metadata_hash(
        evidence
    ):
        checks.append("executor_capability_exposure_metadata_hash replay matched current no-op scaffold")
    else:
        errors.append("INVALID_EVIDENCE: executor_capability_exposure_metadata_hash mismatch")

    capability_defaults_valid = True
    for field in EXECUTOR_CAPABILITY_BOOL_FIELDS:
        value = evidence.get(field)
        if not isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be bool")
            capability_defaults_valid = False
        elif value is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must default false for current no-op executor")
            capability_defaults_valid = False
    if capability_defaults_valid:
        checks.append("executor capability exposure fields default false")
    else:
        errors.append("INVALID_EVIDENCE: executor capability exposure fields must default false")

    if evidence.get("current_executor_capability_status") == NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION:
        checks.append(f"current no-op executor capability status matched: {NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION}")
    else:
        errors.append("INVALID_EVIDENCE: current no-op executor capability status mismatch")

    if (
        evidence.get("executor_capability_file_mutation") is False
        and evidence.get("executor_capability_provider_calls") is False
        and evidence.get("executor_capability_network_calls") is False
        and evidence.get("executor_capability_actions") == []
        and evidence.get("executor_capability_action_count") == 0
        and evidence.get("executor_capability_expected_action_count") == 0
    ):
        checks.append("current no-op executor has no shell/network/provider/action capability")
    else:
        errors.append("INVALID_EVIDENCE: current no-op executor capability metadata mismatch")

    dangerous_capabilities = _dangerous_executor_capability_fields(evidence)
    if evidence.get("capability_shell") is False and dangerous_capabilities:
        errors.append("INVALID_EVIDENCE: NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY")
    else:
        checks.append("no raw shell was not treated as proof of no dangerous capability")

    if (
        evidence.get("executor_capability_transport") == EXECUTOR_CAPABILITY_TRANSPORT_STRUCTURED_TOOL_CALL
        and dangerous_capabilities
    ):
        errors.append("INVALID_EVIDENCE: STRUCTURED_TOOL_CALL != SAFE_CAPABILITY")
    else:
        checks.append("structured tool call was not treated as safe capability")

    reported = evidence.get("executor_reported_capability_exposure")
    if (
        isinstance(reported, dict)
        and isinstance(reported.get("capabilities"), list)
        and isinstance(reported.get("tools"), list)
        and reported.get("reported_capability_count") == len(reported.get("capabilities"))
        and reported.get("reported_tool_count") == len(reported.get("tools"))
        and reported.get("trust_boundary") == "reported_only"
        and reported.get("judgment_basis") is False
    ):
        checks.append("executor_reported_capability_exposure remains reported_only context, not judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure cannot become judgment basis")

    if evidence.get("judgment_basis") == "executor_reported_capability_exposure":
        errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure cannot become judgment basis")

    if manifest is not None:
        if manifest.get("executor_capability_exposure_hash") == evidence.get("executor_capability_exposure_hash"):
            checks.append("manifest executor_capability_exposure_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest executor_capability_exposure_hash mismatch with evidence")
        if manifest.get("executor_capability_exposure_metadata_hash") == evidence.get(
            "executor_capability_exposure_metadata_hash"
        ):
            checks.append("manifest executor_capability_exposure_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest executor_capability_exposure_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_evidence_store_trust_boundary(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("evidence store trust boundary replay used recorded scaffold metadata only")

    if evidence.get("evidence_store_trust_metadata_hash") == expected_evidence_store_trust_metadata_hash(evidence):
        checks.append("evidence_store_trust_metadata_hash replay matched folder-local scaffold")
    else:
        errors.append("INVALID_EVIDENCE: evidence_store_trust_metadata_hash mismatch")

    if evidence.get("evidence_store_trust_boundary") == EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED:
        checks.append("evidence store trust boundary remained folder_local_not_executor_isolated")
    else:
        errors.append("INVALID_EVIDENCE: .aeg/ folder-local state is not executor-isolated")

    if evidence.get("evidence_store_is_executor_isolated") is False:
        checks.append("evidence_store_is_executor_isolated remained false")
    else:
        errors.append("INVALID_EVIDENCE: AEG_FOLDER_LOCAL_STATE != EXECUTOR_ISOLATED_EVIDENCE_STORE")

    can_write = evidence.get("executor_can_write_evidence_store")
    if can_write == EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY:
        checks.append("executor_can_write_evidence_store remained NOT_CHECKED_SAME_USER_AUTHORITY")
    else:
        errors.append(
            "INVALID_EVIDENCE: executor_can_write_evidence_store must remain "
            "NOT_CHECKED_SAME_USER_AUTHORITY before executor isolation proof"
        )

    integrity_status = evidence.get("evidence_store_integrity_status")
    if integrity_status == EVIDENCE_STORE_INTEGRITY_NOT_CHECKED:
        checks.append("evidence store integrity status remained NOT_CHECKED")
    else:
        errors.append("INVALID_EVIDENCE: evidence_store_integrity_status must remain NOT_CHECKED in scaffold v0")

    if evidence.get("evidence_store_is_executor_isolated") is False and integrity_status == EVIDENCE_STORE_CLEAN:
        errors.append("INVALID_EVIDENCE: evidence_store_is_executor_isolated=false cannot claim EVIDENCE_STORE_CLEAN")
    else:
        checks.append(".aeg folder-local state was not treated as executor-isolated")

    if can_write in (True, EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY) and integrity_status == EVIDENCE_STORE_CLEAN:
        errors.append("INVALID_EVIDENCE: executor write access true/NOT_CHECKED cannot promote evidence store CLEAN")
    else:
        checks.append("executor write access true/NOT_CHECKED was not promoted to evidence store CLEAN")

    if evidence.get("binding_status") == BOUND and integrity_status == EVIDENCE_STORE_CLEAN:
        errors.append("INVALID_EVIDENCE: EVIDENCE_BINDING != EVIDENCE_STORE_TAMPER_PROOF")
    else:
        checks.append("evidence binding was not treated as evidence store tamper-proof")

    if manifest is not None:
        if manifest.get("evidence_store_trust_metadata_hash") == evidence.get("evidence_store_trust_metadata_hash"):
            checks.append("manifest evidence_store_trust_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest evidence_store_trust_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_aeg_state_write_denial(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("aeg state write denial replay used recorded scaffold metadata only")

    if evidence.get("aeg_state_write_denial_version") == AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0:
        checks.append(f"aeg_state_write_denial_version matched: {AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0}")
    else:
        errors.append(
            "INVALID_EVIDENCE: aeg_state_write_denial_version must be "
            f"{AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0}"
        )

    if evidence.get("aeg_state_write_denial_mode") == AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD:
        checks.append("aeg_state_write_denial_mode remained metadata scaffold")
    else:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_mode must remain metadata scaffold")

    denial_status = evidence.get("aeg_state_write_denial_status")
    if denial_status == AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY:
        checks.append("aeg_state_write_denial_status remained DENIAL_SCAFFOLD_ONLY")
    else:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_status must remain DENIAL_SCAFFOLD_ONLY")
    if denial_status in ("CLEAN", "PASS", "ENFORCED", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_status cannot claim CLEAN/PASS/ENFORCED")
    else:
        checks.append("aeg_state_write_denial_status did not claim CLEAN/PASS/ENFORCED")

    if evidence.get("capability_write_aeg_state_requested") is False:
        checks.append("capability_write_aeg_state_requested remained false")
    else:
        errors.append("INVALID_EVIDENCE: capability_write_aeg_state_requested must remain false")

    if evidence.get("capability_write_aeg_state_granted") is False:
        checks.append("capability_write_aeg_state_granted remained false")
    else:
        errors.append("INVALID_EVIDENCE: capability_write_aeg_state_granted must remain false")

    if evidence.get("capability_write_aeg_state_denied") is True:
        checks.append("capability_write_aeg_state_denied remained explicit true")
    else:
        errors.append("INVALID_EVIDENCE: capability_write_aeg_state_denied must be explicit true")

    bypass_flags_valid = True
    for field in AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS:
        value = evidence.get(field)
        if not isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be bool")
            bypass_flags_valid = False
        elif value is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must remain false")
            bypass_flags_valid = False
    if bypass_flags_valid:
        checks.append("aeg state write bypass flags default false")
    else:
        errors.append("INVALID_EVIDENCE: aeg state write bypass flags must default false")

    enforcement_status = evidence.get("aeg_state_write_denial_enforcement_status")
    if enforcement_status == AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED:
        checks.append("aeg_state_write_denial_enforcement_status remained SCAFFOLD_ONLY_NOT_ENFORCED")
    else:
        errors.append(
            "INVALID_EVIDENCE: aeg_state_write_denial_enforcement_status must remain "
            "SCAFFOLD_ONLY_NOT_ENFORCED"
        )
    if enforcement_status in ("CLEAN", "PASS", "ENFORCED", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_enforcement_status cannot claim ENFORCED/CLEAN/PASS")
    else:
        checks.append("aeg_state_write_denial_enforcement_status did not claim ENFORCED/CLEAN/PASS")

    if evidence.get("aeg_state_write_denial_source") == AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA:
        checks.append("aeg_state_write_denial_source remained aegis runtime scaffold metadata")
    else:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_source must be aegis runtime scaffold metadata")
    if evidence.get("aeg_state_write_denial_source") == "executor_self_report":
        errors.append("INVALID_EVIDENCE: executor self-report cannot prove aeg state write denial")
    else:
        checks.append("executor self-report was not treated as aeg state write denial proof")

    if evidence.get("aeg_state_write_denial_reason") == AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY:
        checks.append("aeg_state_write_denial_reason described scaffold-only metadata denial")
    else:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_reason must describe scaffold-only metadata denial")

    if evidence.get("aeg_state_write_denial_metadata_hash") == expected_aeg_state_write_denial_metadata_hash(evidence):
        checks.append("aeg_state_write_denial_metadata_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_metadata_hash mismatch")

    reported = evidence.get("executor_reported_aeg_state_write_denial")
    if isinstance(reported, dict) and reported.get("judgment_basis") is True:
        errors.append("INVALID_EVIDENCE: executor_reported_aeg_state_write_denial cannot become judgment basis")
    elif evidence.get("judgment_basis") == "executor_reported_aeg_state_write_denial":
        errors.append("INVALID_EVIDENCE: executor_reported_aeg_state_write_denial cannot become judgment basis")
    else:
        checks.append("executor reported aeg state write denial was not treated as proof")

    checks.append("capability_write_aeg_state denied metadata was not treated as external enforcement")

    if manifest is not None:
        if manifest.get("aeg_state_write_denial_metadata_hash") == evidence.get(
            "aeg_state_write_denial_metadata_hash"
        ):
            checks.append("manifest aeg_state_write_denial_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest aeg_state_write_denial_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_mediated_write_boundary(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("mediated write boundary replay used recorded scaffold metadata only")
    checks.append("mediated write scaffold did not perform OS/filesystem write mediation")

    if evidence.get("mediated_write_boundary_scaffold_version") == MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0:
        checks.append(f"mediated_write_boundary_scaffold_version matched: {MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0}")
    else:
        errors.append(
            "INVALID_EVIDENCE: mediated_write_boundary_scaffold_version must be "
            f"{MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0}"
        )

    scaffold_status = evidence.get("mediated_write_boundary_scaffold_status")
    if scaffold_status == MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED:
        checks.append("mediated_write_boundary_scaffold_status remained SCAFFOLD_ONLY_NOT_ENFORCED")
    else:
        errors.append(
            "INVALID_EVIDENCE: mediated_write_boundary_scaffold_status must remain "
            "SCAFFOLD_ONLY_NOT_ENFORCED"
        )
    if scaffold_status in MEDIATED_WRITE_PASSLIKE_STATUSES:
        errors.append("INVALID_EVIDENCE: mediated_write_boundary_scaffold_status cannot claim PASS/SAFE/ENFORCED")
    else:
        checks.append("SCAFFOLD_ONLY_NOT_ENFORCED was not promoted to PASS/SAFE/ENFORCED")

    enforcement_status = evidence.get("mediated_write_boundary_enforcement_status")
    if enforcement_status in (
        MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        MEDIATED_WRITE_BOUNDARY_ENFORCEMENT_STATUS_NOT_IMPLEMENTED,
    ):
        checks.append(f"mediated_write_boundary_enforcement_status remained non-enforced: {enforcement_status}")
    else:
        errors.append(
            "INVALID_EVIDENCE: mediated_write_boundary_enforcement_status must remain "
            "SCAFFOLD_ONLY_NOT_ENFORCED or NOT_IMPLEMENTED"
        )
    if enforcement_status in MEDIATED_WRITE_PASSLIKE_STATUSES:
        errors.append("INVALID_EVIDENCE: mediated_write_boundary_enforcement_status cannot claim PASS/SAFE/ENFORCED")
    else:
        checks.append("mediated write enforcement did not claim PASS/SAFE/ENFORCED")

    if evidence.get("write_mediation_enabled") is False:
        checks.append("write_mediation_enabled remained false")
    else:
        errors.append("INVALID_EVIDENCE: write_mediation_enabled must remain false in scaffold v0")

    if evidence.get("write_mediation_enforced") is False:
        checks.append("write_mediation_enforced remained false")
    else:
        errors.append("INVALID_EVIDENCE: write_mediation_enforced must remain false in scaffold v0")
        errors.append(
            f"INVALID_EVIDENCE: {STATUS_OVERCLAIM_REJECTED}: "
            "write_mediation_enforced=true cannot be accepted before runtime wiring"
        )

    declared = evidence.get("write_classes_declared")
    granted = evidence.get("write_classes_granted")
    denied = evidence.get("write_classes_denied")
    if declared == list(WRITE_CLASSES):
        checks.append("write classes vocabulary matched Phase 10 scaffold")
    else:
        errors.append("INVALID_EVIDENCE: write_classes_declared must match Phase 10 scaffold vocabulary")
    if granted == []:
        checks.append("write_classes_granted remained empty")
    else:
        errors.append("INVALID_EVIDENCE: write_classes_granted must be empty in scaffold v0")
    if isinstance(denied, list) and set(denied) == set(WRITE_CLASSES):
        checks.append("write_classes_denied included every scaffold write class")
    else:
        errors.append("INVALID_EVIDENCE: write_classes_denied must include every declared write class in scaffold v0")

    decisions = evidence.get("write_class_mediation_statuses")
    if decisions == dict(WRITE_CLASS_DEFAULT_MEDIATION_STATUSES):
        checks.append("write class mediation statuses matched scaffold defaults")
    else:
        errors.append("INVALID_EVIDENCE: write_class_mediation_statuses must match scaffold default decisions")
    if isinstance(decisions, dict):
        passlike = [write_class for write_class, status in decisions.items() if status in MEDIATED_WRITE_PASSLIKE_STATUSES]
        if passlike:
            errors.append(
                "INVALID_EVIDENCE: write mediation status cannot claim PASS/SAFE/ENFORCED: "
                f"{', '.join(sorted(passlike))}"
            )
        else:
            checks.append("write mediation decisions did not claim PASS/SAFE/ENFORCED")
    else:
        errors.append("INVALID_EVIDENCE: write_class_mediation_statuses must be object")

    if evidence.get("write_mediation_decision_source") == MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA:
        checks.append("write_mediation_decision_source remained aegis runtime scaffold metadata")
    else:
        errors.append("INVALID_EVIDENCE: write_mediation_decision_source must be aegis runtime scaffold metadata")
    if evidence.get("write_mediation_decision_source") == MEDIATED_WRITE_DECISION_SOURCE_EXECUTOR_SELF_REPORT:
        errors.append("INVALID_EVIDENCE: executor self-report cannot prove write mediation")
    else:
        checks.append("executor self-report was not treated as write mediation proof")
    if evidence.get("write_mediation_decision_source") == MEDIATED_WRITE_DECISION_SOURCE_EXTERNAL_ENFORCEMENT:
        errors.append("INVALID_EVIDENCE: metadata denial is not externally enforced denial")
    else:
        checks.append("metadata denial was not treated as external enforcement")

    evidence_status = evidence.get("write_mediation_evidence_status")
    if evidence_status == NOT_CHECKED:
        checks.append("write_mediation_evidence_status remained NOT_CHECKED")
        checks.append("write mediation NOT_CHECKED was not promoted to PASS")
    else:
        errors.append("INVALID_EVIDENCE: write_mediation_evidence_status must remain NOT_CHECKED in scaffold v0")
    if evidence_status in MEDIATED_WRITE_PASSLIKE_STATUSES:
        errors.append("INVALID_EVIDENCE: write_mediation_evidence_status cannot claim PASS/SAFE/ENFORCED")
        errors.append(
            f"INVALID_EVIDENCE: {NOT_CHECKED_PASS_OVERCLAIM_REJECTED}: "
            "write_mediation_evidence_status cannot promote NOT_CHECKED to PASS/CLEAN/ENFORCED"
        )

    direct_grants_valid = True
    for field in MEDIATED_WRITE_DIRECT_ALLOW_FIELDS:
        value = evidence.get(field)
        if not isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be bool")
            direct_grants_valid = False
        elif value is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must remain false in scaffold v0")
            direct_grants_valid = False
    if direct_grants_valid:
        checks.append("dangerous direct write grants default false")
    else:
        errors.append("INVALID_EVIDENCE: dangerous direct write grants must default false")

    if (
        evidence.get("phase10e_write_mediation_component_status")
        == PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED
    ):
        checks.append(
            "phase10e write mediation component label remained "
            "PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED"
        )
    else:
        errors.append(
            f"INVALID_EVIDENCE: {WRITE_MEDIATION_COMPONENT_MISMATCH_REJECTED}: "
            "phase10e_write_mediation_component_status must remain "
            "PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED"
        )

    if evidence.get("runtime_wiring_status") == RUNTIME_WIRING_NOT_IMPLEMENTED:
        checks.append("runtime wiring status remained RUNTIME_WIRING_NOT_IMPLEMENTED")
    else:
        errors.append(
            f"INVALID_EVIDENCE: {STATUS_OVERCLAIM_REJECTED}: "
            "runtime_wiring_status must remain RUNTIME_WIRING_NOT_IMPLEMENTED"
        )
    if evidence.get("live_executor_authority_status") == LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        checks.append("live executor authority status remained LIVE_EXECUTOR_AUTHORITY_ON_HOLD")
    else:
        errors.append(
            f"INVALID_EVIDENCE: {STATUS_OVERCLAIM_REJECTED}: "
            "live_executor_authority_status must remain LIVE_EXECUTOR_AUTHORITY_ON_HOLD"
        )

    _verify_phase10e_mismatch_rejection_claims(evidence, checks, errors)
    _verify_phase10e_component_hash(
        evidence,
        checks,
        errors,
        "mediator_contract_hash",
        expected_mediator_contract_hash(),
        WRITE_MEDIATION_COMPONENT_MISMATCH_REJECTED,
    )
    _verify_phase10e_component_hash(
        evidence,
        checks,
        errors,
        "mediated_write_binding_hash",
        expected_mediated_write_binding_hash(),
        MEDIATED_WRITE_EVIDENCE_MISMATCH_REJECTED,
    )
    _verify_phase10e_component_hash(
        evidence,
        checks,
        errors,
        "bypass_fixture_result_hash",
        expected_bypass_fixture_result_hash(),
        BYPASS_RESULT_MISMATCH_REJECTED,
    )

    if evidence.get("write_mediation_decision_hash") == expected_write_mediation_decision_hash(evidence):
        checks.append("write_mediation_decision_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: write_mediation_decision_hash mismatch")

    if evidence.get("mediated_write_boundary_metadata_hash") == expected_mediated_write_boundary_metadata_hash(evidence):
        checks.append("mediated_write_boundary_metadata_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: mediated_write_boundary_metadata_hash mismatch")

    if manifest is not None:
        if manifest.get("mediated_write_boundary_metadata_hash") == evidence.get(
            "mediated_write_boundary_metadata_hash"
        ):
            checks.append("manifest mediated_write_boundary_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest mediated_write_boundary_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_phase10e_component_hash(
    evidence: dict[str, Any],
    checks: list[str],
    errors: list[str],
    field: str,
    expected_hash: str,
    rejection_code: str,
) -> None:
    actual = evidence.get(field)
    if not isinstance(actual, str) or not is_sha256_hex(actual):
        errors.append(f"INVALID_EVIDENCE: {rejection_code}: {field} must be sha256 hex")
    elif actual == expected_hash:
        checks.append(f"{field} replay matched")
    else:
        errors.append(f"INVALID_EVIDENCE: {rejection_code}: {field} mismatch")


def _verify_phase10e_mismatch_rejection_claims(
    evidence: dict[str, Any],
    checks: list[str],
    errors: list[str],
) -> None:
    mismatch_found = False
    if evidence.get("mediation_enforced") is True:
        mismatch_found = True
        errors.append(
            f"INVALID_EVIDENCE: {STATUS_OVERCLAIM_REJECTED}: "
            "mediation_enforced=true cannot be accepted without runtime wiring proof"
        )

    for field, rejected_values in (
        ("mediator_status", {"ENFORCED"}),
        ("write_denial_status", {"ACTIVE", "ENFORCED"}),
        ("bypass_harness_status", {"COVERAGE_COMPLETE", "ENFORCED"}),
    ):
        value = evidence.get(field)
        if value in rejected_values:
            mismatch_found = True
            errors.append(f"INVALID_EVIDENCE: {STATUS_OVERCLAIM_REJECTED}: {field}={value}")

    for field, rejected_values in (
        ("write_mediation_status", {"PASS", "CLEAN", "ENFORCED"}),
        ("mediation_scaffold_status", {"PASS", "CLEAN", "ENFORCED"}),
    ):
        value = evidence.get(field)
        if value in rejected_values:
            mismatch_found = True
            errors.append(f"INVALID_EVIDENCE: {NOT_CHECKED_PASS_OVERCLAIM_REJECTED}: {field}={value}")

    reported_write_denied = evidence.get("executor_reported_write_denied")
    reported_basis = False
    if isinstance(reported_write_denied, dict):
        reported_basis = reported_write_denied.get("judgment_basis") is True
    elif reported_write_denied is True:
        reported_basis = evidence.get("judgment_basis") in (True, "executor_reported_write_denied")
    if reported_basis:
        mismatch_found = True
        errors.append(
            f"INVALID_EVIDENCE: {REPORTED_ONLY_PROOF_REJECTED}: "
            "executor_reported_write_denied cannot become judgment basis"
        )

    if evidence.get("known_gap_promoted_to_enforced_denial") is True:
        mismatch_found = True
        errors.append(
            f"INVALID_EVIDENCE: {BYPASS_RESULT_MISMATCH_REJECTED}: "
            "known gap baseline cannot be promoted to enforced denial"
        )
    mismatch_found = _verify_bypass_test_result_claims(evidence.get("bypass_test_results"), errors) or mismatch_found

    if not mismatch_found:
        checks.append("Phase 10-E mismatch rejection found no forged overclaim fields")


def _verify_bypass_test_result_claims(value: Any, errors: list[str]) -> bool:
    mismatch_found = False
    if value is None:
        return False
    for result in _bypass_result_records(value):
        wbyp_id = result.get("wbyp_id") or result.get("id") or "UNKNOWN"
        observed = result.get("observed_result") or result.get("result") or result.get("status")
        expected = result.get("expected_result") or result.get("expected_red_marker")
        known_gap = result.get("known_gap_marker")
        if wbyp_id == "WBYP-001" and expected == WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED:
            if observed in {"PASS", "BLOCKED", "ENFORCED"}:
                mismatch_found = True
                errors.append(
                    f"INVALID_EVIDENCE: {BYPASS_RESULT_MISMATCH_REJECTED}: "
                    f"WBYP-001 expected-red result cannot be {observed}"
                )
        if known_gap == WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE:
            if result.get("enforced_denial") is True or observed in {"BLOCKED", "ENFORCED"}:
                mismatch_found = True
                errors.append(
                    f"INVALID_EVIDENCE: {BYPASS_RESULT_MISMATCH_REJECTED}: "
                    "known gap baseline cannot be reported as enforced denial"
                )
    return mismatch_found


def _bypass_result_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if any(key in value for key in ("wbyp_id", "id", "observed_result", "result", "status")):
            return [value]
        return [item for item in value.values() if isinstance(item, dict)]
    return []


def _verify_write_bypass_harness_scaffold(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("write bypass harness replay used recorded scaffold metadata only")
    checks.append("write bypass harness scaffold did not perform filesystem write attempts")

    if evidence.get("write_bypass_harness_scaffold_version") == WRITE_BYPASS_HARNESS_SCAFFOLD_V0:
        checks.append(f"write_bypass_harness_scaffold_version matched: {WRITE_BYPASS_HARNESS_SCAFFOLD_V0}")
    else:
        errors.append(
            "INVALID_EVIDENCE: write_bypass_harness_scaffold_version must be "
            f"{WRITE_BYPASS_HARNESS_SCAFFOLD_V0}"
        )

    for field in (
        "write_bypass_harness_scaffold_status",
        "write_bypass_harness_execution_status",
        "write_bypass_harness_enforcement_status",
        "write_bypass_harness_registry_status",
        "write_bypass_harness_fixture_status",
        "write_bypass_harness_evidence_status",
    ):
        status = evidence.get(field)
        if status in WRITE_BYPASS_HARNESS_PASSLIKE_STATUSES:
            errors.append(f"INVALID_EVIDENCE: {field} cannot claim PASS/SAFE/ENFORCED")
        else:
            checks.append(f"{field} did not claim PASS/SAFE/ENFORCED")

    for field in (
        "write_bypass_harness_scaffold_status",
        "write_bypass_harness_enforcement_status",
        "write_bypass_harness_registry_status",
    ):
        if evidence.get(field) == WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED:
            checks.append(f"{field} remained SCAFFOLD_ONLY_NOT_ENFORCED")
        else:
            errors.append(f"INVALID_EVIDENCE: {field} must remain SCAFFOLD_ONLY_NOT_ENFORCED")

    for field in (
        "write_bypass_harness_execution_status",
        "write_bypass_harness_fixture_status",
        "write_bypass_harness_evidence_status",
    ):
        if evidence.get(field) == NOT_CHECKED:
            checks.append(f"{field} remained NOT_CHECKED")
        else:
            errors.append(f"INVALID_EVIDENCE: {field} must remain NOT_CHECKED")
    checks.append("write bypass harness NOT_CHECKED was not promoted to PASS")

    if evidence.get("write_bypass_harness_expected_wbyp_count") == WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT:
        checks.append("write bypass harness expected WBYP count remained 25")
    else:
        errors.append("INVALID_EVIDENCE: write_bypass_harness_expected_wbyp_count must be 25")

    registry_ids = evidence.get("write_bypass_harness_registry_ids")
    registry = evidence.get("write_bypass_harness_registry")
    if registry_ids == list(WBYP_IDS):
        checks.append("write_bypass_harness_registry_ids contained WBYP-001 through WBYP-025")
    else:
        errors.append("INVALID_EVIDENCE: write_bypass_harness_registry_ids must be WBYP-001 through WBYP-025")
    if isinstance(registry, list):
        entry_ids = [entry.get("id") for entry in registry if isinstance(entry, dict)]
        if entry_ids == list(WBYP_IDS):
            checks.append("WBYP registry contained WBYP-001 through WBYP-025")
        else:
            errors.append("INVALID_EVIDENCE: write_bypass_harness_registry must contain WBYP-001 through WBYP-025")
        if len(registry) == WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT:
            checks.append("WBYP registry entry count matched 25")
        else:
            errors.append("INVALID_EVIDENCE: write_bypass_harness_registry must contain 25 entries")
        _verify_wbyp_registry_entry_scaffold_only(registry, checks, errors)
    else:
        errors.append("INVALID_EVIDENCE: write_bypass_harness_registry must be list")

    for field in (
        "write_bypass_harness_actual_bypass_tests_present",
        "write_bypass_harness_actual_fixtures_present",
        "write_bypass_harness_actual_write_attempts_present",
        "write_bypass_harness_mediator_enforcement_present",
        "write_bypass_harness_external_enforcement_present",
        "write_bypass_harness_executor_self_report_proof_allowed",
        "write_bypass_harness_reported_only_judgment_basis_allowed",
    ):
        if evidence.get(field) is False:
            checks.append(f"{field} remained false")
        else:
            errors.append(f"INVALID_EVIDENCE: {field} must remain false in scaffold v0")

    if evidence.get("write_bypass_harness_executor_self_report_proof_allowed") is False:
        checks.append("executor self-report was not treated as write bypass proof")
    else:
        errors.append("INVALID_EVIDENCE: executor self-report cannot prove write bypass harness results")
    if evidence.get("write_bypass_harness_reported_only_judgment_basis_allowed") is False:
        checks.append("reported_only was not treated as write bypass judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: reported_only cannot be write bypass judgment basis")

    if evidence.get("live_executor_authority_granted") is False:
        checks.append("live executor authority remained ON_HOLD for write bypass harness scaffold")
    else:
        errors.append("INVALID_EVIDENCE: live executor authority cannot be granted by write bypass harness scaffold")

    if evidence.get("write_bypass_harness_registry_hash") == expected_write_bypass_harness_registry_hash(evidence):
        checks.append("write_bypass_harness_registry_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: write_bypass_harness_registry_hash mismatch")

    if evidence.get("write_bypass_harness_metadata_hash") == expected_write_bypass_harness_metadata_hash(evidence):
        checks.append("write_bypass_harness_metadata_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: write_bypass_harness_metadata_hash mismatch")

    if manifest is not None:
        if manifest.get("write_bypass_harness_metadata_hash") == evidence.get("write_bypass_harness_metadata_hash"):
            checks.append("manifest write_bypass_harness_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest write_bypass_harness_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_wbyp_registry_entry_scaffold_only(
    registry: list[Any],
    checks: list[str],
    errors: list[str],
) -> None:
    entries_valid = True
    for entry in registry:
        if not isinstance(entry, dict):
            entries_valid = False
            continue
        entry_id = entry.get("id", "UNKNOWN")
        if entry.get("scaffold_status") != WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED:
            errors.append(f"INVALID_EVIDENCE: {entry_id} scaffold_status must remain SCAFFOLD_ONLY_NOT_ENFORCED")
            entries_valid = False
        if entry.get("execution_status") != NOT_CHECKED:
            errors.append(f"INVALID_EVIDENCE: {entry_id} execution_status must remain NOT_CHECKED")
            entries_valid = False
        if entry.get("enforcement_status") != WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED:
            errors.append(f"INVALID_EVIDENCE: {entry_id} enforcement_status must remain SCAFFOLD_ONLY_NOT_ENFORCED")
            entries_valid = False
        for field in ("scaffold_status", "execution_status", "enforcement_status"):
            if entry.get(field) in WRITE_BYPASS_HARNESS_PASSLIKE_STATUSES:
                errors.append(f"INVALID_EVIDENCE: WBYP registry {field} cannot claim PASS/SAFE/ENFORCED")
                entries_valid = False
        if entry.get("future_only") is not True:
            errors.append(f"INVALID_EVIDENCE: {entry_id} must remain future-only metadata")
            entries_valid = False
        if entry.get("proof_source") != WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED:
            errors.append(f"INVALID_EVIDENCE: {entry_id} proof_source must remain future_harness_not_collected")
            entries_valid = False
        for field in (
            "actual_test_present",
            "fixture_created",
            "actual_write_attempt_present",
            "executor_self_report_proof_allowed",
            "reported_only_judgment_basis_allowed",
            "judgment_basis",
        ):
            if entry.get(field) is not False:
                errors.append(f"INVALID_EVIDENCE: WBYP registry {field} must remain false")
                entries_valid = False
    if entries_valid:
        checks.append("WBYP registry entries remained future-only metadata")
        checks.append("WBYP registry entries did not claim actual tests, fixtures, write attempts, or proof")


def _verify_pre_live_executor_gate(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("pre-live executor gate replay used recorded scaffold metadata only")

    if evidence.get("pre_live_executor_gate_version") == PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0:
        checks.append(f"pre_live_executor_gate_version matched: {PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0}")
    else:
        errors.append(
            "INVALID_EVIDENCE: pre_live_executor_gate_version must be "
            f"{PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0}"
        )

    if evidence.get("pre_live_executor_gate_mode") == PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD:
        checks.append("pre_live_executor_gate_mode remained metadata scaffold")
    else:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_mode must remain metadata scaffold")

    if evidence.get("pre_live_executor_gate_status") == PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD:
        checks.append("pre_live_executor_gate_status remained PRE_LIVE_EXECUTOR_ON_HOLD")
    else:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_status must remain PRE_LIVE_EXECUTOR_ON_HOLD")

    if evidence.get("live_executor_authority_requested") is False:
        checks.append("live_executor_authority_requested remained false")
    else:
        errors.append("INVALID_EVIDENCE: live_executor_authority_requested must remain false")

    if evidence.get("live_executor_authority_granted") is False:
        checks.append("live_executor_authority_granted remained false")
        checks.append("live executor authority remained ON_HOLD")
    else:
        errors.append("INVALID_EVIDENCE: live_executor_authority_granted must remain false")
        errors.append("INVALID_EVIDENCE: live executor authority cannot be granted by pre-live gate scaffold")

    if evidence.get("live_executor_authority_hold_reason") == LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE:
        checks.append("live_executor_authority_hold_reason preserved pre-live gate hold")
    else:
        errors.append("INVALID_EVIDENCE: live_executor_authority_hold_reason must preserve pre-live gate hold")

    ledger_present = (
        evidence.get("requires_tamper_evident_ledger") is True
        and evidence.get("tamper_evident_ledger_present") is True
        and evidence.get("ledger_integrity_version") == LEDGER_INTEGRITY_SCAFFOLD_V0
        and evidence.get("ledger_tamper_evident_enabled") is True
        and evidence.get("ledger_tamper_proof_claimed") is False
    )
    if ledger_present:
        checks.append("required tamper-evident ledger scaffold present")
    else:
        errors.append("INVALID_EVIDENCE: required tamper-evident ledger scaffold is missing")

    denial_present = (
        evidence.get("requires_aeg_state_write_denial") is True
        and evidence.get("aeg_state_write_denial_present") is True
        and evidence.get("aeg_state_write_denial_version") == AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0
        and evidence.get("capability_write_aeg_state_granted") is False
        and evidence.get("capability_write_aeg_state_denied") is True
        and evidence.get("aeg_state_write_denial_enforcement_status")
        == AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED
    )
    if denial_present:
        checks.append("required aeg state write denial scaffold present")
    else:
        errors.append("INVALID_EVIDENCE: required aeg state write denial scaffold is missing")

    gate_result = evidence.get("pre_live_executor_gate_result")
    gate_result_is_hold = gate_result in (
        PRE_LIVE_EXECUTOR_GATE_RESULT_HOLD_CURRENT_STATE,
        PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
    )
    if gate_result_is_hold:
        checks.append(f"pre_live_executor_gate_result remained hold: {gate_result}")
    else:
        errors.append(
            "INVALID_EVIDENCE: pre_live_executor_gate_result must remain HOLD_CURRENT_STATE or "
            "NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR"
        )

    if gate_result in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_result cannot claim PASS/CLEAN/ALLOW")
    else:
        checks.append("pre_live_executor_gate_result did not claim PASS/CLEAN/ALLOW")

    if evidence.get("requires_external_enforcement") is True:
        checks.append("pre-live executor gate requires external enforcement before live executor")
    else:
        errors.append("INVALID_EVIDENCE: pre-live executor gate must require external enforcement before live executor")

    if evidence.get("external_enforcement_present") is False:
        checks.append("external_enforcement_present remained false")
        if gate_result in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS:
            errors.append("INVALID_EVIDENCE: external_enforcement_present=false cannot produce PASS/CLEAN/ALLOW")
        else:
            checks.append("external_enforcement_present=false kept gate result non-pass")
    else:
        errors.append("INVALID_EVIDENCE: external_enforcement_present must remain false in scaffold v0")

    if evidence.get("evidence_store_executor_isolated_required") is True:
        checks.append("pre-live executor gate requires executor-isolated evidence store before live executor")
    else:
        errors.append("INVALID_EVIDENCE: pre-live executor gate must require executor-isolated evidence store")

    if evidence.get("evidence_store_executor_isolated_present") is False:
        checks.append("evidence_store_executor_isolated_present remained false")
        if gate_result in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS:
            errors.append(
                "INVALID_EVIDENCE: evidence_store_executor_isolated_present=false cannot produce PASS/CLEAN/ALLOW"
            )
        else:
            checks.append("evidence_store_executor_isolated_present=false kept gate result non-pass")
    else:
        errors.append("INVALID_EVIDENCE: evidence_store_executor_isolated_present must remain false in scaffold v0")

    if evidence.get("evidence_store_executor_isolated_present") == evidence.get("evidence_store_is_executor_isolated"):
        checks.append("pre-live gate mirrored evidence_store_is_executor_isolated=false")
    else:
        errors.append("INVALID_EVIDENCE: pre-live gate must mirror evidence_store_is_executor_isolated=false")

    if evidence.get("pre_live_executor_gate_reason") == PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY:
        checks.append("pre_live_executor_gate_reason described scaffold-only hold")
    else:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_reason must describe scaffold-only hold")

    if evidence.get("pre_live_executor_gate_metadata_hash") == expected_pre_live_executor_gate_metadata_hash(evidence):
        checks.append("pre_live_executor_gate_metadata_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_metadata_hash mismatch")

    if manifest is not None:
        if manifest.get("pre_live_executor_gate_metadata_hash") == evidence.get(
            "pre_live_executor_gate_metadata_hash"
        ):
            checks.append("manifest pre_live_executor_gate_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest pre_live_executor_gate_metadata_hash mismatch with evidence")

    return checks, errors


def _verify_store_write_mediation(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    replay = verify_store_write_mediation_metadata(evidence)
    if replay.get("accepted") is True:
        checks.append("store write mediation replay accepted")
    else:
        for reason in replay.get("rejection_reasons", []):
            errors.append(f"INVALID_EVIDENCE: {reason}")

    if evidence.get("store_write_mediation_enabled") is True:
        checks.append("store_write_mediation_enabled remained true and bound")
    else:
        errors.append("INVALID_EVIDENCE: store_write_mediation_enabled must remain true")

    if evidence.get("store_write_mediation_binding_present") is True:
        checks.append("store write mediation binding present")
    else:
        errors.append("INVALID_EVIDENCE: store_write_mediation_enabled=true requires binding")

    if evidence.get("trusted_runtime_write_allowed") is True:
        checks.append("trusted runtime write allowed by deterministic call-site")
    else:
        errors.append("INVALID_EVIDENCE: trusted runtime write failed or was not recorded as allowed")

    if evidence.get("executor_attributed_write_blocked") is True:
        checks.append("executor-attributed .aeg write block evidence replay matched")
        if evidence.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED:
            checks.append("write_mediation_result BLOCKED matched executor-attributed block")
    elif evidence.get("blocked_write_target_count") == 0:
        checks.append("no executor-attributed .aeg write attempt was recorded in this run")
    else:
        errors.append("INVALID_EVIDENCE: blocked_write_target_count requires executor_attributed_write_blocked=true")

    if evidence.get("blocked_write_created_files_count") == 0:
        checks.append("blocked_write_created_files_count replay matched zero")
    else:
        errors.append("INVALID_EVIDENCE: blocked_write_created_files_count > 0 cannot support BLOCKED claim")

    if evidence.get("rollback_used") == evidence.get("fallback_to_unwired"):
        checks.append("rollback_used matched fallback_to_unwired")
    else:
        errors.append("INVALID_EVIDENCE: rollback/fallback mismatch")

    if evidence.get("fallback_to_unwired") is True:
        if evidence.get("fallback_evidence_recorded") is True:
            checks.append("fallback-to-unwired evidence recorded")
        else:
            errors.append("INVALID_EVIDENCE: fallback used but evidence was not recorded")
    elif evidence.get("fallback_evidence_recorded") is False:
        checks.append("fallback-to-unwired not used")
    else:
        errors.append("INVALID_EVIDENCE: fallback evidence recorded mismatch")

    if evidence.get("store_write_mediation_metadata_hash") == expected_store_write_mediation_metadata_hash(evidence):
        checks.append("store_write_mediation_metadata_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: store_write_mediation_metadata_hash mismatch")

    if manifest is not None:
        if manifest.get("store_write_mediation_metadata_hash") == evidence.get("store_write_mediation_metadata_hash"):
            checks.append("manifest store_write_mediation_metadata_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest store_write_mediation_metadata_hash mismatch with evidence")
        if manifest.get("store_write_mediation_manifest_hash") == sha256_json(
            store_write_mediation_manifest_fields(manifest)
        ):
            checks.append("store_write_mediation_manifest_hash replay matched")
        else:
            errors.append("INVALID_EVIDENCE: store_write_mediation_manifest_hash mismatch")

    return checks, errors


def _verify_ledger_integrity(
    evidence: dict[str, Any],
    manifest: dict[str, Any] | None,
    ledger_entry: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    checks.append("ledger integrity replay used recorded scaffold metadata only")
    checks.append("ledger scaffold is tamper-evident, not tamper-proof")

    if evidence.get("ledger_integrity_version") == LEDGER_INTEGRITY_SCAFFOLD_V0:
        checks.append(f"ledger_integrity_version matched: {LEDGER_INTEGRITY_SCAFFOLD_V0}")
    else:
        errors.append(f"INVALID_EVIDENCE: ledger_integrity_version must be {LEDGER_INTEGRITY_SCAFFOLD_V0}")

    if evidence.get("ledger_integrity_mode") == LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD:
        checks.append("ledger_integrity_mode remained tamper_evident_scaffold")
    else:
        errors.append("INVALID_EVIDENCE: ledger_integrity_mode must remain tamper_evident_scaffold")

    if evidence.get("ledger_tamper_evident_enabled") is True:
        checks.append("ledger_tamper_evident_enabled default true")
    else:
        errors.append("INVALID_EVIDENCE: ledger_tamper_evident_enabled must be true in scaffold v0")

    if evidence.get("ledger_tamper_proof_claimed") is False:
        checks.append("ledger_tamper_proof_claimed remained false")
    else:
        errors.append("INVALID_EVIDENCE: tamper-evident ledger scaffold cannot claim tamper-proof")

    integrity_status = evidence.get("ledger_integrity_status")
    if integrity_status == LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY:
        checks.append("ledger_integrity_status remained TAMPER_EVIDENT_SCAFFOLD_ONLY")
    else:
        errors.append("INVALID_EVIDENCE: ledger_integrity_status must remain TAMPER_EVIDENT_SCAFFOLD_ONLY")
    if integrity_status in ("CLEAN", "PASS", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: ledger_integrity_status cannot claim CLEAN/PASS")
    else:
        checks.append("ledger_integrity_status did not claim CLEAN/PASS")

    if evidence.get("ledger_integrity_check_status") == LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED:
        checks.append("ledger_integrity_check_status remained NOT_CHECKED")
    else:
        errors.append("INVALID_EVIDENCE: ledger_integrity_check_status must remain NOT_CHECKED")
    if evidence.get("ledger_integrity_check_status") in ("CLEAN", "PASS", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: ledger_integrity_check_status cannot claim CLEAN/PASS")
    else:
        checks.append("ledger_integrity_check_status did not claim CLEAN/PASS")

    if evidence.get("ledger_integrity_check_reason") == LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY:
        checks.append("ledger_integrity_check_reason described scaffold-only detection")
    else:
        errors.append("INVALID_EVIDENCE: ledger_integrity_check_reason must describe scaffold-only tamper evidence")

    sequence = evidence.get("ledger_sequence_number")
    previous_hash = evidence.get("previous_ledger_hash")
    if isinstance(sequence, int) and not isinstance(sequence, bool) and sequence >= 1:
        checks.append(f"ledger_sequence_number valid: {sequence}")
        if sequence == 1 and previous_hash in (LEDGER_PREVIOUS_HASH_GENESIS, LEDGER_PREVIOUS_HASH_NOT_AVAILABLE):
            checks.append("previous_ledger_hash explicit genesis/not_available for first ledger entry")
        elif sequence == 1:
            errors.append("INVALID_EVIDENCE: first ledger entry must use explicit genesis/not_available previous hash")
        elif previous_hash == LEDGER_PREVIOUS_HASH_GENESIS:
            errors.append("INVALID_EVIDENCE: non-genesis ledger entry cannot reuse genesis previous hash")
        elif previous_hash == LEDGER_PREVIOUS_HASH_NOT_AVAILABLE:
            errors.append("INVALID_EVIDENCE: non-genesis ledger entry cannot use unavailable previous hash")
        elif is_sha256_hex(previous_hash):
            checks.append("previous_ledger_hash explicit for non-genesis ledger entry")
        else:
            errors.append("INVALID_EVIDENCE: previous_ledger_hash must be explicit genesis/not_available or sha256")
    else:
        errors.append("INVALID_EVIDENCE: ledger_sequence_number must be positive integer")

    expected_evidence_hash = expected_current_evidence_hash(evidence)
    if evidence.get("current_evidence_hash") == expected_evidence_hash:
        checks.append("current_evidence_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: current_evidence_hash mismatch")

    if manifest is not None:
        expected_manifest_hash = expected_current_manifest_hash(manifest)
        if evidence.get("current_manifest_hash") == expected_manifest_hash:
            checks.append("current_manifest_hash replay matched")
        else:
            errors.append("INVALID_EVIDENCE: current_manifest_hash mismatch")
        if manifest.get("current_manifest_hash") == evidence.get("current_manifest_hash"):
            checks.append("manifest current_manifest_hash matched evidence")
        else:
            errors.append("INVALID_EVIDENCE: manifest current_manifest_hash mismatch with evidence")

        manifest_group_hash = sha256_json(ledger_integrity_manifest_fields(manifest))
        if manifest.get("ledger_integrity_manifest_hash") == manifest_group_hash:
            checks.append("ledger_integrity_manifest_hash replay matched")
        else:
            errors.append("INVALID_EVIDENCE: ledger_integrity_manifest_hash mismatch")
    else:
        errors.append("INVALID_EVIDENCE: ledger integrity requires manifest replay")

    if ledger_entry is not None:
        for field in LEDGER_INTEGRITY_FIELDS:
            _check_equal(checks, errors, f"ledger {field}", ledger_entry.get(field), evidence.get(field))
        expected_entry_hash = expected_ledger_entry_hash(ledger_entry)
        if evidence.get("current_ledger_entry_hash") == expected_entry_hash:
            checks.append("current_ledger_entry_hash replay matched")
        else:
            errors.append("INVALID_EVIDENCE: current_ledger_entry_hash mismatch")
    else:
        errors.append("INVALID_EVIDENCE: ledger integrity requires ledger entry replay")

    expected_chain_hash = expected_ledger_chain_hash(evidence)
    if evidence.get("ledger_chain_hash") == expected_chain_hash:
        checks.append("ledger_chain_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: ledger_chain_hash mismatch")

    expected_metadata_hash = expected_ledger_integrity_metadata_hash(evidence)
    if evidence.get("ledger_integrity_metadata_hash") == expected_metadata_hash:
        checks.append("ledger_integrity_metadata_hash replay matched")
    else:
        errors.append("INVALID_EVIDENCE: ledger_integrity_metadata_hash mismatch")

    if evidence.get("binding_status") == BOUND and evidence.get("ledger_tamper_proof_claimed") is True:
        errors.append("INVALID_EVIDENCE: EVIDENCE_BINDING != LEDGER_TAMPER_PROOF")
    else:
        checks.append("evidence binding was not treated as ledger tamper-proof")

    return checks, errors


def _expected_mutation_boundary_status(
    trusted: bool,
    pre_snapshot: list[dict[str, Any]],
    computed_delta: list[dict[str, Any]],
) -> str:
    if not trusted:
        return MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT
    if computed_delta:
        return MUTATION_BOUNDARY_DELTA_DETECTED
    if pre_snapshot:
        return MUTATION_BOUNDARY_DIRTY_PREEXISTING
    return MUTATION_BOUNDARY_CLEAN


def _dangerous_executor_capability_fields(evidence: dict[str, Any]) -> list[str]:
    return [
        field
        for field in EXECUTOR_CAPABILITY_BOOL_FIELDS
        if field != "capability_shell" and evidence.get(field) is True
    ]


def _check_equal(checks: list[str], errors: list[str], label: str, actual: Any, expected: Any) -> None:
    if actual == expected:
        checks.append(f"{label} matched")
    else:
        errors.append(f"INVALID_EVIDENCE: {label} mismatch: actual={actual} expected={expected}")


def _check_manifest_field_group(
    checks: list[str],
    errors: list[str],
    label: str,
    fields: tuple[str, ...],
    hash_field: str,
    evidence: dict[str, Any],
    manifest: dict[str, Any],
    evidence_fields: dict[str, Any],
    manifest_fields: dict[str, Any],
) -> None:
    for field in fields:
        _check_equal(checks, errors, f"manifest {field}", manifest.get(field), evidence.get(field))
    _check_equal(
        checks,
        errors,
        f"manifest {hash_field}",
        manifest.get(hash_field),
        sha256_json(manifest_fields),
    )
    if evidence_fields == manifest_fields:
        checks.append(f"{label} fields matched manifest")
    else:
        errors.append(f"INVALID_EVIDENCE: {label} fields mismatch")


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_object_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def _string_list(value: Any) -> list[str]:
    if not _is_string_list(value):
        return []
    return list(value)


def _is_under(root: Path, path: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents
