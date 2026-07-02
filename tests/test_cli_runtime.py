import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.state.git as git_state
from src.agents.noop import execute_contract as noop_execute_contract
from src.cli.main import _cmd_doctor, _cmd_run
from src.contracts import (
    ACTION_AUTHORITY_FIELDS,
    ACTION_BOUNDARY_CLEAN,
    ACTION_BOUNDARY_FIELDS,
    ACTION_BOUNDARY_NOT_CHECKED,
    ACTION_BOUNDARY_SCAFFOLD_V0,
    ACTION_LOG_SOURCE_NONE,
    ACTION_LOG_SOURCE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS,
    AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    AEG_STATE_WRITE_DENIAL_FIELDS,
    AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD,
    AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY,
    AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0,
    AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA,
    AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY,
    BOUND,
    CAPABILITY_AUTHORITY_FIELDS,
    CAPABILITY_BOUNDARY_CLEAN,
    CAPABILITY_BOUNDARY_NOT_CHECKED,
    CAPABILITY_BOUNDARY_SOURCE_NONE,
    CAPABILITY_BOUNDARY_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    CAPABILITY_ISOLATION_FIELDS,
    CAPABILITY_ISOLATION_MODE_NOT_IMPLEMENTED,
    CAPABILITY_ISOLATION_SCAFFOLD_V0,
    CLEAN_CORE,
    CONTRACT_FIRST_NOOP,
    CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_MODE_OFF,
    CITIZEN_ONE_MODE_PROPOSE,
    CITIZEN_ONE_NOT_REQUESTED,
    CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE,
    CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED,
    CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED,
    CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED,
    CITIZEN_ONE_PROPOSAL_CONTRACT_V0,
    CITIZEN_ONE_PROPOSAL_RECORDED,
    CITIZEN_ONE_STATUSES,
    DETERMINISTIC_STUB_PROPOSAL_ID,
    DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES,
    DETERMINISTIC_STUB_PROPOSAL_STEPS,
    DETERMINISTIC_STUB_PROPOSAL_SUMMARY,
    EVIDENCE_BINDING_V1,
    EVIDENCE_STORE_CLEAN,
    EVIDENCE_STORE_INTEGRITY_NOT_CHECKED,
    EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED,
    EVIDENCE_STORE_TRUST_FIELDS,
    EVIDENCE_STORE_WRITE_SOURCE_FOLDER_LOCAL_STATE,
    EVIDENCE_STORE_WRITER_AEGIS_RUNTIME,
    EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY,
    EXECUTOR_CAPABILITY_BOOL_FIELDS,
    EXECUTOR_CAPABILITY_EXPOSURE_FIELDS,
    EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0,
    EXECUTOR_CAPABILITY_EXPOSURE_SCOPE_CURRENT_NOOP,
    EXECUTOR_CAPABILITY_EXPOSURE_SOURCE_NOOP_CONTRACT,
    EXECUTOR_CAPABILITY_EXPOSURE_TRUST_BOUNDARY_AEGIS_RUNTIME,
    EXECUTOR_CAPABILITY_TRANSPORT_NONE,
    EXECUTOR_CAPABILITY_TRANSPORT_STRUCTURED_TOOL_CALL,
    FORBIDDEN_RAW_PROMPT_RESPONSE_KEYS,
    GIT_STAGED,
    GIT_WORKING_TREE,
    HIGH,
    LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY,
    LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED,
    LEDGER_INTEGRITY_FIELDS,
    LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD,
    LEDGER_INTEGRITY_SCAFFOLD_V0,
    LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY,
    LEDGER_PREVIOUS_HASH_GENESIS,
    LOW,
    MEDIATED_WRITE_BOUNDARY_FIELDS,
    MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0,
    MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA,
    MEDIATED_WRITE_DIRECT_ALLOW_FIELDS,
    MEDIUM,
    MUTATION_BOUNDARY_CLEAN,
    MUTATION_BOUNDARY_DELTA_DETECTED,
    MUTATION_BOUNDARY_DIRTY_PREEXISTING,
    MUTATION_DELTA_SOURCE_COMPUTED,
    REPORTED_ONLY,
    NEEDS_USER_GATE,
    NO_CHANGED_FILES,
    NO_CHANGED_FILES_SOURCE,
    NOT_CHECKED,
    NOT_CHECKED_SOURCE,
    NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION,
    PROVIDER_ADAPTER_DISABLED_FIELDS,
    PROVIDER_ADAPTER_DISABLED_REQUEST_ID,
    PROVIDER_ENV_LOADING_STATUS_DISABLED,
    PROVIDER_ENV_LOADING_STATUS_NOT_REQUESTED,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_NOT_REQUESTED,
    PROVIDER_MODEL_NONE,
    PROVIDER_NAME_NONE,
    PROVIDER_NETWORK_BLOCK_REASON_NONE,
    PROVIDER_NETWORK_BLOCK_REASON_OPT_IN_NOT_REQUESTED,
    PROVIDER_NETWORK_GUARD_METADATA_FIELDS,
    PROVIDER_NETWORK_STATUS_BLOCKED_NO_OPT_IN,
    PROVIDER_NETWORK_STATUS_NOT_REQUESTED,
    PROVIDER_PROMPT_SOURCE_DISABLED,
    PROVIDER_PROMPT_SOURCE_NONE,
    PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROVIDER_REQUEST_METADATA_FIELDS,
    PROVIDER_REQUEST_STATUS_BLOCKED_PROVIDER_NOT_CONFIGURED,
    PROVIDER_REQUEST_STATUS_NOT_REQUESTED,
    PROVIDER_RESPONSE_ERROR_METADATA_FIELDS,
    PROVIDER_RESPONSE_ERROR_CLASS_NONE,
    PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER,
    PROVIDER_RESPONSE_SOURCE_NONE,
    PROVIDER_RESPONSE_STATUS_NOT_REQUESTED,
    PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_ERROR_CLASS_NONE,
    PROVIDER_RUNTIME_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RUNTIME_HOLD_REASON_NOT_REQUESTED,
    PROVIDER_RUNTIME_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_STATE_FIELDS,
    PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE,
    PROVIDER_RUNTIME_STATUS_HELD_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_STATUS_NOT_REQUESTED,
    PROVIDER_SECRET_ENV_METADATA_FIELDS,
    PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED,
    PROVIDER_SECRET_SOURCE_NONE,
    PROVIDER_SECRET_SOURCE_NOT_REQUESTED,
    PROVIDER_SELECTION_METADATA_FIELDS,
    PROVIDER_SELECTION_SOURCE_DISABLED,
    PROVIDER_SELECTION_SOURCE_NOT_REQUESTED,
    PROVIDER_SELECTION_STATUS_NOT_CONFIGURED,
    PROVIDER_SELECTION_STATUS_NOT_REQUESTED,
    LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE,
    PRE_LIVE_EXECUTOR_GATE_FIELDS,
    PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD,
    PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY,
    PRE_LIVE_EXECUTOR_GATE_RESULT_HOLD_CURRENT_STATE,
    PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
    PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0,
    PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD,
    PROMPT_BUILD_STATUS_NOT_BUILT,
    PROMPT_BUILD_STATUS_PROVIDER_DISABLED,
    PROMPT_REDACTION_METADATA_FIELDS,
    PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED,
    PROMPT_SOURCE_DISABLED,
    PROMPT_SOURCE_NONE,
    PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE,
    PROPOSAL_HOLD_REASON_NONE,
    PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROPOSAL_KIND_DETERMINISTIC_STUB,
    PROPOSAL_KIND_NOT_GENERATED,
    PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROPOSAL_SOURCE_DETERMINISTIC_STUB,
    PROPOSAL_SOURCE_NONE,
    PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED,
    PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED,
    RESPONSE_ERROR_CLASS_NONE,
    RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED,
    RESPONSE_REDACTION_METADATA_FIELDS,
    RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED,
    RESPONSE_SOURCE_DISABLED_ADAPTER,
    RESPONSE_SOURCE_NONE,
    RESPONSE_STATUS_NOT_REQUESTED,
    RESPONSE_STATUS_PROVIDER_DISABLED,
    RUN_MANIFEST_V1,
    SAFE_DEFAULT,
    TOOL_AUTHORITY_GRANT_FIELDS,
    TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0,
    TOOL_SURFACE_CLEAN,
    TOOL_SURFACE_FIELDS,
    TOOL_SURFACE_SCAFFOLD_ONLY,
    TOOL_SURFACE_SOURCE_NONE,
    TOOL_SURFACE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    WBYP_IDS,
    WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT,
    WRITE_BYPASS_HARNESS_FIELDS,
    WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED,
    WRITE_BYPASS_HARNESS_SCAFFOLD_V0,
    WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    WRITE_CLASSES,
    WRITE_CLASS_DEFAULT_MEDIATION_STATUSES,
)
from src.evidence.action_boundary import expected_action_log_hash
from src.evidence.aeg_state_write_denial import expected_aeg_state_write_denial_metadata_hash
from src.evidence.binding import sha256_json
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
)
from src.evidence.mediated_write_boundary import (
    expected_mediated_write_boundary_metadata_hash,
    expected_write_mediation_decision_hash,
)
from src.evidence.pre_live_executor_gate import expected_pre_live_executor_gate_metadata_hash
from src.evidence.tool_surface import (
    expected_tool_authority_grant_hash,
    expected_tool_surface_metadata_hash,
)
from src.evidence.write_bypass_harness import (
    expected_write_bypass_harness_metadata_hash,
    expected_write_bypass_harness_registry_hash,
)
from src.evidence import (
    manifest_hash,
    validate_completion_contract_v0,
    validate_evidence_binding_v0,
    validate_evidence_binding_v1,
    validate_user_gate_reason_card_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CliRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init")
        self._git("config", "user.email", "aegis@example.invalid")
        self._git("config", "user.name", "Aegis Test")
        (self.repo / ".gitignore").write_text(".aeg/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test\n", encoding="utf-8")
        (self.repo / "src" / "agents").mkdir(parents=True)
        (self.repo / "src" / "agents" / "executor.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.repo / "src" / "classify").mkdir(parents=True)
        (self.repo / "src" / "classify" / "rules.py").write_text("VALUE = 1\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "init")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_doctor_passes_inside_initialized_repo(self):
        self._aeg("init")

        doctor = self._aeg("doctor")

        self.assertIn("status: PASS", doctor.stdout)
        self.assertIn("overall_status: PASS", doctor.stdout)
        self.assertIn("repo_root:", doctor.stdout)
        self.assertIn("state_path:", doctor.stdout)
        self.assertIn(f"safe_default: {SAFE_DEFAULT}", doctor.stdout)
        self.assertIn("[PASS] git command available", doctor.stdout)
        self.assertIn("[PASS] inside git repo", doctor.stdout)
        self.assertIn("[PASS] repo root detected", doctor.stdout)
        self.assertIn("[PASS] HEAD SHA readable", doctor.stdout)
        self.assertIn("[PASS] tree SHA readable", doctor.stdout)
        self.assertIn("[PASS] .aeg/ exists", doctor.stdout)
        self.assertIn("[PASS] .aeg/ writable", doctor.stdout)
        self.assertIn("[PASS] .aeg/ git ignored", doctor.stdout)
        self.assertIn("[PASS] .aeg/ tracked file count", doctor.stdout)
        self.assertIn("[PASS] .env tracked file count", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)
        self.assertIn("[PASS] provider not required", doctor.stdout)
        self.assertIn("[PASS] OpenAI / Claude / Gemini not required", doctor.stdout)
        self.assertIn("External provider credentials are not required", doctor.stdout)
        self.assertIn("Network access is not required", doctor.stdout)

    def test_doctor_gives_readable_failure_outside_git_repo(self):
        with tempfile.TemporaryDirectory() as outside:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT)
            doctor = subprocess.run(
                [sys.executable, "-m", "src.cli", "doctor"],
                cwd=outside,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        combined = doctor.stdout + doctor.stderr
        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] inside git repo", doctor.stdout)
        self.assertIn("[FAIL] repo root detected", doctor.stdout)
        self.assertIn("fix_hint: Run aeg doctor from inside a Git repository", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)
        self.assertIn("[PASS] provider not required", doctor.stdout)
        self.assertNotIn("Traceback", combined)

    def test_doctor_warns_when_aeg_state_is_missing_and_suggests_init(self):
        doctor = self._aeg("doctor")

        self.assertEqual(doctor.returncode, 0)
        self.assertIn("status: PASS_WITH_WARNINGS", doctor.stdout)
        self.assertIn("[WARN] .aeg/ exists", doctor.stdout)
        self.assertIn("fix_hint: Run aeg init", doctor.stdout)
        self.assertIn("[PASS] provider not required", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)

    def test_doctor_reports_missing_git_command_readably(self):
        with patch("src.state.doctor.git.git_available", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_doctor(self.repo)

        self.assertEqual(exit_code, 1)
        stdout = output.getvalue()
        self.assertIn("status: FAIL", stdout)
        self.assertIn("[FAIL] git command available", stdout)
        self.assertIn("fix_hint: Install Git", stdout)
        self.assertIn("[PASS] provider not required", stdout)
        self.assertIn("[PASS] network not required", stdout)

    def test_doctor_reports_unwritable_aeg_state_readably(self):
        self._aeg("init")

        with patch("src.state.doctor._state_dir_writable", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_doctor(self.repo)

        self.assertEqual(exit_code, 1)
        stdout = output.getvalue()
        self.assertIn("status: FAIL", stdout)
        self.assertIn("[FAIL] .aeg/ writable", stdout)
        self.assertIn("Fix filesystem permissions or ownership", stdout)

    def test_doctor_flags_unignored_aeg_state(self):
        (self.repo / ".gitignore").write_text("", encoding="utf-8")
        self._aeg("init")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .aeg/ git ignored", doctor.stdout)
        self.assertIn("fix_hint: Add .aeg/ to .gitignore", doctor.stdout)

    def test_doctor_flags_tracked_aeg_state(self):
        self._aeg("init")
        (self.repo / ".aeg" / "tracked.txt").write_text("runtime\n", encoding="utf-8")
        self._git("add", "-f", ".aeg/tracked.txt")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .aeg/ tracked file count", doctor.stdout)
        self.assertIn("tracked_count: 1", doctor.stdout)
        self.assertIn("git rm --cached -r .aeg", doctor.stdout)

    def test_doctor_flags_tracked_env_file(self):
        self._aeg("init")
        (self.repo / ".env").write_text("PLACEHOLDER=1\n", encoding="utf-8")
        self._git("add", "-f", ".env")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .env tracked file count", doctor.stdout)
        self.assertIn("tracked_count: 1", doctor.stdout)
        self.assertIn("keep real secrets out of Git", doctor.stdout)

    def test_low_run_and_verify(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: CLEAN_CORE", run.stdout)
        self.assertIn("binding_status: BOUND", run.stdout)
        self.assertIn("binding_version: evidence_binding_v1", run.stdout)
        self.assertIn("action_boundary_status: ACTION_BOUNDARY_NOT_CHECKED", run.stdout)
        self.assertIn("action_count: 0", run.stdout)
        self.assertIn("expected_action_count: 0", run.stdout)
        self.assertIn("raw_shell_authority_granted: false", run.stdout)
        self.assertIn("capability_isolation_enabled: false", run.stdout)
        self.assertIn("capability_boundary_status: CAPABILITY_BOUNDARY_NOT_CHECKED", run.stdout)
        self.assertIn("process_execution_authority_granted: false", run.stdout)
        self.assertIn("tool_surface_enabled: false", run.stdout)
        self.assertIn("tool_surface_status: TOOL_SURFACE_SCAFFOLD_ONLY", run.stdout)
        self.assertIn("tool_authority_grant_count: 0", run.stdout)
        self.assertIn("expected_tool_authority_grant_count: 0", run.stdout)
        self.assertIn("raw_shell_tool_authority_granted: false", run.stdout)
        self.assertIn("network_tool_authority_granted: false", run.stdout)
        self.assertIn("executor_capability_exposure_version: executor_capability_exposure_scaffold_v0", run.stdout)
        self.assertIn("current_executor_capability_status: NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION", run.stdout)
        self.assertIn("capability_shell: false", run.stdout)
        self.assertIn("capability_network: false", run.stdout)
        self.assertIn("capability_provider_call: false", run.stdout)
        self.assertIn("executor_capability_action_count: 0", run.stdout)
        self.assertIn("executor_capability_expected_action_count: 0", run.stdout)
        self.assertIn("evidence_store_trust_boundary: folder_local_not_executor_isolated", run.stdout)
        self.assertIn("evidence_store_is_executor_isolated: false", run.stdout)
        self.assertIn("evidence_store_integrity_status: NOT_CHECKED", run.stdout)
        self.assertIn("ledger_integrity_version: ledger_integrity_scaffold_v0", run.stdout)
        self.assertIn("ledger_integrity_mode: tamper_evident_scaffold", run.stdout)
        self.assertIn("ledger_integrity_status: TAMPER_EVIDENT_SCAFFOLD_ONLY", run.stdout)
        self.assertIn("ledger_tamper_evident_enabled: true", run.stdout)
        self.assertIn("ledger_tamper_proof_claimed: false", run.stdout)
        self.assertIn("ledger_integrity_check_status: NOT_CHECKED", run.stdout)
        self.assertIn("pre_live_executor_gate_version: pre_live_executor_gate_scaffold_v0", run.stdout)
        self.assertIn("pre_live_executor_gate_status: PRE_LIVE_EXECUTOR_ON_HOLD", run.stdout)
        self.assertIn("live_executor_authority_requested: false", run.stdout)
        self.assertIn("live_executor_authority_granted: false", run.stdout)
        self.assertIn("tamper_evident_ledger_present: true", run.stdout)
        self.assertIn("aeg_state_write_denial_present: true", run.stdout)
        self.assertIn("external_enforcement_present: false", run.stdout)
        self.assertIn("evidence_store_executor_isolated_present: false", run.stdout)
        self.assertIn("pre_live_executor_gate_result: NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR", run.stdout)
        self.assertNotIn("pre_live_executor_gate_result: PASS", run.stdout)
        self.assertNotIn("pre_live_executor_gate_result: CLEAN", run.stdout)
        self.assertNotIn("pre_live_executor_gate_result: ALLOW", run.stdout)
        self.assertIn("mediated_write_boundary_scaffold_status: SCAFFOLD_ONLY_NOT_ENFORCED", run.stdout)
        self.assertIn("mediated_write_boundary_enforcement_status: SCAFFOLD_ONLY_NOT_ENFORCED", run.stdout)
        self.assertIn("write_mediation_enabled: false", run.stdout)
        self.assertIn("write_mediation_enforced: false", run.stdout)
        self.assertIn("write_classes_granted_count: 0", run.stdout)
        self.assertIn("executor_direct_aeg_write_allowed: false", run.stdout)
        self.assertIn("executor_direct_outside_repo_write_allowed: false", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertEqual(evidence["changed_files"], [])
        self.assertEqual(evidence["changed_files_source"], NO_CHANGED_FILES_SOURCE)
        self.assertEqual(evidence["protected_paths_touched"], [])
        self.assertFalse(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], CLEAN_CORE)
        self.assertEqual(evidence["pre_run_changed_files"], [])
        self.assertEqual(evidence["post_run_changed_files"], [])
        self.assertEqual(evidence["pre_existing_dirty_tree"], [])
        self.assertEqual(evidence["computed_mutation_delta"], [])
        self.assertEqual(evidence["executor_created_mutation"], [])
        self.assertFalse(evidence["protected_path_mutation_detected"])
        self.assertEqual(evidence["mutation_delta_source"], MUTATION_DELTA_SOURCE_COMPUTED)
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_CLEAN)
        self._assert_action_boundary_scaffold_contract(evidence)
        self._assert_capability_isolation_scaffold_contract(evidence)
        self._assert_tool_surface_scaffold_contract(evidence)
        self._assert_executor_capability_exposure_contract(evidence)
        self._assert_evidence_store_trust_contract(evidence)
        self._assert_aeg_state_write_denial_scaffold_contract(evidence)
        self._assert_mediated_write_boundary_scaffold_contract(evidence)
        self._assert_pre_live_executor_gate_contract(evidence)
        self._assert_ledger_integrity_scaffold_contract(evidence)
        self.assertEqual(evidence["binding_version"], EVIDENCE_BINDING_V1)
        self.assertEqual(evidence["binding_status"], BOUND)
        self.assertFalse(evidence["citizen_one_requested"])
        self.assertEqual(evidence["citizen_one_mode"], CITIZEN_ONE_MODE_OFF)
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_NOT_REQUESTED)
        self.assertEqual(evidence["citizen_one_provider_status"], CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED)
        self.assertFalse(evidence["citizen_one_output_present"])
        self.assertEqual(evidence["citizen_one_output_trust_boundary"], REPORTED_ONLY)
        self.assertTrue(evidence["citizen_one_reported_only"])
        self.assertEqual(evidence["provider_config_source"], CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED)
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertEqual(evidence["model_output_hash_candidate"], "")
        self._assert_provider_not_requested_contract(evidence)
        self.assertNotIn("proposal_present", evidence)
        self.assertEqual(validate_evidence_binding_v0(evidence), [])
        self.assertEqual(validate_evidence_binding_v1(evidence), [])
        self.assertEqual(validate_completion_contract_v0(evidence), [])
        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: CLEAN_CORE", verify.stdout)
        self.assertIn("binding_status: BOUND", verify.stdout)
        self.assertIn("evidence binding v1 valid", verify.stdout)
        self.assertIn("LOW risk remained CLEAN_CORE", verify.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_NOT_REQUESTED", verify.stdout)
        self.assertIn("citizen one evidence fields matched manifest", verify.stdout)
        self.assertIn("provider adapter disabled fields matched manifest", verify.stdout)
        self.assertIn("action boundary scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("capability isolation scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("capability authority flags default false", verify.stdout)
        self.assertIn("capability boundary status remained CAPABILITY_BOUNDARY_NOT_CHECKED", verify.stdout)
        self.assertIn("tool surface scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("tool authority flags default false", verify.stdout)
        self.assertIn("tool authority grant count replay matched expected zero: 0", verify.stdout)
        self.assertIn("tool surface status remained TOOL_SURFACE_SCAFFOLD_ONLY", verify.stdout)
        self.assertIn("executor capability exposure metadata fields matched manifest", verify.stdout)
        self.assertIn("executor capability exposure fields default false", verify.stdout)
        self.assertIn("current no-op executor has no shell/network/provider/action capability", verify.stdout)
        self.assertIn("structured tool call was not treated as safe capability", verify.stdout)
        self.assertIn("evidence store trust boundary metadata fields matched manifest", verify.stdout)
        self.assertIn("evidence store trust boundary remained folder_local_not_executor_isolated", verify.stdout)
        self.assertIn("evidence_store_is_executor_isolated remained false", verify.stdout)
        self.assertIn("evidence store integrity status remained NOT_CHECKED", verify.stdout)
        self.assertIn("mediated write boundary scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("mediated_write_boundary_scaffold_status remained SCAFFOLD_ONLY_NOT_ENFORCED", verify.stdout)
        self.assertIn("write_mediation_enabled remained false", verify.stdout)
        self.assertIn("write_mediation_enforced remained false", verify.stdout)
        self.assertIn("dangerous direct write grants default false", verify.stdout)
        self.assertIn("metadata denial was not treated as external enforcement", verify.stdout)
        self.assertIn("write mediation NOT_CHECKED was not promoted to PASS", verify.stdout)
        self.assertIn("pre-live executor gate metadata fields matched manifest", verify.stdout)
        self.assertIn("live_executor_authority_granted remained false", verify.stdout)
        self.assertIn("live executor authority remained ON_HOLD", verify.stdout)
        self.assertIn("required tamper-evident ledger scaffold present", verify.stdout)
        self.assertIn("required aeg state write denial scaffold present", verify.stdout)
        self.assertIn("external_enforcement_present=false kept gate result non-pass", verify.stdout)
        self.assertIn("evidence_store_executor_isolated_present=false kept gate result non-pass", verify.stdout)
        self.assertIn("pre_live_executor_gate_metadata_hash replay matched", verify.stdout)
        self.assertIn("ledger integrity scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("ledger_tamper_proof_claimed remained false", verify.stdout)
        self.assertIn("ledger_integrity_status did not claim CLEAN/PASS", verify.stdout)
        self.assertIn("ledger_integrity_check_status remained NOT_CHECKED", verify.stdout)
        self.assertIn("current_evidence_hash replay matched", verify.stdout)
        self.assertIn("current_manifest_hash replay matched", verify.stdout)
        self.assertIn("current_ledger_entry_hash replay matched", verify.stdout)
        self.assertIn("ledger_chain_hash replay matched", verify.stdout)
        self.assertIn("ledger_integrity_metadata_hash replay matched", verify.stdout)
        self.assertIn("action_count replay matched expected no-op count: 0", verify.stdout)
        self.assertIn("mutation boundary clean did not imply action boundary clean", verify.stdout)
        self.assertNotIn("proposal_status:", run.stdout)
        self.assertNotIn("proposal_status:", verify.stdout)

    def test_run_creates_manifest_with_deterministic_binding_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")

        evidence, _ = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()

        self.assertTrue(manifest_path.exists())
        self.assertEqual(manifest["manifest_version"], RUN_MANIFEST_V1)
        self.assertEqual(manifest["run_id"], evidence["run_id"])
        self.assertEqual(manifest["repo_root"], evidence["repo_root"])
        self.assertEqual(manifest["branch"], evidence["branch"])
        self.assertEqual(manifest["head_sha"], evidence["head_sha"])
        self.assertEqual(manifest["tree_sha"], evidence["tree_sha"])
        self.assertEqual(manifest["changed_files"], evidence["changed_files"])
        self.assertEqual(manifest["changed_files_source"], evidence["changed_files_source"])
        self.assertEqual(manifest["pre_run_changed_files"], evidence["pre_run_changed_files"])
        self.assertEqual(manifest["post_run_changed_files"], evidence["post_run_changed_files"])
        self.assertEqual(manifest["computed_mutation_delta"], evidence["computed_mutation_delta"])
        self.assertEqual(manifest["mutation_boundary_status"], evidence["mutation_boundary_status"])
        self.assertEqual(manifest["risk_level"], evidence["risk_level"])
        self.assertEqual(manifest["status"], evidence["status"])
        self.assertEqual(manifest["citizen_one_requested"], evidence["citizen_one_requested"])
        self.assertEqual(manifest["citizen_one_status"], evidence["citizen_one_status"])
        self.assertEqual(manifest["provider_network_used"], evidence["provider_network_used"])
        self.assertEqual(manifest["provider_secret_observed"], evidence["provider_secret_observed"])
        self.assertEqual(manifest["model_output_hash_candidate"], evidence["model_output_hash_candidate"])
        for field in self._provider_adapter_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_runtime_state_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_selection_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_secret_env_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_network_guard_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_request_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_response_error_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._prompt_redaction_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._response_redaction_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._action_boundary_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._capability_isolation_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._tool_surface_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._executor_capability_exposure_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._evidence_store_trust_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._mediated_write_boundary_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._pre_live_executor_gate_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._ledger_integrity_fields():
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["citizen_one_evidence_hash"],
            sha256_json({field: evidence[field] for field in self._citizen_one_fields()}),
        )
        self.assertEqual(
            manifest["provider_adapter_evidence_hash"],
            sha256_json({field: evidence[field] for field in self._provider_adapter_fields()}),
        )
        self.assertEqual(
            manifest["provider_runtime_state_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_runtime_state_fields()}),
        )
        self.assertEqual(
            manifest["provider_selection_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_selection_fields()}),
        )
        self.assertEqual(
            manifest["provider_secret_env_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_secret_env_fields()}),
        )
        self.assertEqual(
            manifest["provider_network_guard_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_network_guard_fields()}),
        )
        self.assertEqual(
            manifest["provider_request_safe_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_request_fields()}),
        )
        self.assertEqual(
            manifest["provider_response_error_safe_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_response_error_fields()}),
        )
        self.assertEqual(
            manifest["prompt_redaction_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._prompt_redaction_fields()}),
        )
        self.assertEqual(
            manifest["response_redaction_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._response_redaction_fields()}),
        )
        self.assertEqual(
            manifest["action_boundary_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._action_boundary_fields()}),
        )
        self.assertEqual(
            manifest["capability_isolation_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._capability_isolation_fields()}),
        )
        self.assertEqual(
            manifest["tool_surface_authority_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._tool_surface_fields()}),
        )
        self.assertEqual(
            manifest["executor_capability_exposure_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._executor_capability_exposure_fields()}),
        )
        self.assertEqual(
            manifest["evidence_store_trust_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._evidence_store_trust_fields()}),
        )
        self.assertEqual(
            manifest["mediated_write_boundary_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._mediated_write_boundary_fields()}),
        )
        self.assertEqual(
            manifest["pre_live_executor_gate_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._pre_live_executor_gate_fields()}),
        )
        self.assertEqual(
            manifest["ledger_integrity_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._ledger_integrity_fields()}),
        )
        self.assertEqual(
            evidence["bound_action_boundary_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._action_boundary_fields()}),
        )
        self.assertEqual(
            evidence["bound_capability_isolation_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._capability_isolation_fields()}),
        )
        self.assertEqual(
            evidence["bound_tool_surface_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._tool_surface_fields()}),
        )
        self.assertEqual(
            evidence["bound_executor_capability_exposure_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._executor_capability_exposure_fields()}),
        )
        self.assertEqual(
            evidence["bound_evidence_store_trust_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._evidence_store_trust_fields()}),
        )
        self.assertEqual(
            evidence["bound_mediated_write_boundary_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._mediated_write_boundary_fields()}),
        )
        self.assertEqual(
            evidence["bound_pre_live_executor_gate_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._pre_live_executor_gate_fields()}),
        )
        self.assertNotIn("proposal_evidence_hash", manifest)
        self.assertEqual(evidence["bound_manifest_path"], f".aeg/runs/{evidence['run_id']}/manifest.json")
        self.assertEqual(evidence["bound_manifest_hash"], manifest_hash(manifest))
        self.assertEqual(manifest_hash(manifest), manifest_hash(json.loads(json.dumps(manifest, sort_keys=True))))

    def test_medium_run_records_not_checked_with_binding_and_completion_contract(self):
        self._aeg("init")
        run = self._aeg("run", "do the thing")
        self.assertIn("intent_risk: MEDIUM", run.stdout)
        self.assertIn("impact_risk: NO_CHANGED_FILES", run.stdout)
        self.assertIn("risk_level: MEDIUM", run.stdout)
        self.assertIn("status: NOT_CHECKED", run.stdout)
        self.assertIn("binding_status: BOUND", run.stdout)
        self.assertNotIn("status: CLEAN_CORE", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], MEDIUM)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["status"], NOT_CHECKED)
        self.assertEqual(evidence["binding_status"], BOUND)
        self.assertFalse(evidence["citizen_one_requested"])
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_NOT_REQUESTED)
        self.assertEqual(validate_evidence_binding_v0(evidence), [])
        self.assertEqual(validate_evidence_binding_v1(evidence), [])
        self.assertEqual(validate_completion_contract_v0(evidence), [])

        executor = evidence["checks"]["executor"]
        completion_contract = executor["completion_contract"]
        self.assertEqual(executor["executor"], CONTRACT_FIRST_NOOP)
        self.assertEqual(completion_contract["executor_mode"], CONTRACT_FIRST_NOOP)
        self.assertTrue(completion_contract["completion_reported"])
        self.assertFalse(completion_contract["completion_satisfied"])
        self.assertNotEqual(completion_contract["completion_reported"], completion_contract["completion_satisfied"])
        self.assertFalse(completion_contract["file_mutation"])
        self.assertFalse(completion_contract["provider_calls"])
        self.assertFalse(completion_contract["network_calls"])
        self.assertEqual(executor["actions"], [])
        self.assertEqual(executor["action_count"], 0)
        self.assertEqual(executor["expected_action_count"], 0)
        self.assertEqual(completion_contract["actions"], [])
        self.assertEqual(completion_contract["action_count"], 0)
        self.assertEqual(completion_contract["expected_action_count"], 0)
        self._assert_action_boundary_scaffold_contract(evidence)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NOT_CHECKED", verify.stdout)
        self.assertIn("evidence binding v0 valid", verify.stdout)
        self.assertIn("evidence binding v1 valid", verify.stdout)
        self.assertIn("completion contract v0 valid", verify.stdout)
        self.assertIn("law status replay matched: NOT_CHECKED", verify.stdout)

    def test_high_run_and_verify(self):
        self._aeg("init")
        run = self._aeg("run", "merge to main and deploy")
        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        self.assertIn("user_gate.why: High-risk task requires an explicit user gate before execution.", run.stdout)
        self.assertIn("user_gate.safe_default: hold_current_state", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], HIGH)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["changed_files_source"], NO_CHANGED_FILES_SOURCE)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertEqual(evidence["binding_version"], EVIDENCE_BINDING_V1)
        self.assertEqual(evidence["binding_status"], BOUND)
        self._assert_action_boundary_scaffold_contract(evidence)
        self.assertFalse(evidence["citizen_one_requested"])
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_NOT_REQUESTED)
        self.assertIn("law.high.requires_user_gate", evidence["status_reasons"])
        self.assertEqual(validate_evidence_binding_v1(evidence), [])
        self.assertEqual(validate_user_gate_reason_card_v1(evidence), [])
        card = evidence["user_gate_reason_card"]
        self.assertEqual(card["risk_level"], HIGH)
        self.assertEqual(card["status"], NEEDS_USER_GATE)
        self.assertIn("explicit user gate", card["why_gate_is_required"])
        self.assertTrue(card["irreversible_action_blocked"])
        self.assertEqual(card["intent_risk"], HIGH)
        self.assertEqual(card["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(card["protected_paths_touched"], [])
        self.assertEqual(card["safe_default"], SAFE_DEFAULT)
        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NEEDS_USER_GATE", verify.stdout)
        self.assertIn("binding_status: BOUND", verify.stdout)
        self.assertIn("HIGH risk remained NEEDS_USER_GATE", verify.stdout)
        self.assertIn("HIGH user gate reason card valid", verify.stdout)

    def test_citizen_one_opt_in_without_provider_holds_without_output_or_mutation(self):
        self._aeg("init")
        run = self._aeg("run", "--citizen-one", "fix typo in README")

        self.assertIn("status: CLEAN_CORE", run.stdout)
        self.assertIn("citizen_one_requested: true", run.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED", run.stdout)
        self.assertIn("provider_network_used: false", run.stdout)
        self.assertIn("provider_secret_observed: false", run.stdout)
        self.assertIn("provider_runtime_state: hold_current_state", run.stdout)
        self.assertIn("provider_runtime_status: held_provider_not_configured", run.stdout)
        self.assertIn("provider_runtime_hold_reason: provider_not_configured", run.stdout)
        self.assertIn("provider_selection_requested: true", run.stdout)
        self.assertIn("provider_selected: false", run.stdout)
        self.assertIn("provider_selection_status: not_configured", run.stdout)
        self.assertIn("provider_secret_required: false", run.stdout)
        self.assertIn("provider_secret_value_recorded: false", run.stdout)
        self.assertIn("provider_env_loading_requested: false", run.stdout)
        self.assertIn("provider_env_loading_status: disabled", run.stdout)
        self.assertIn("provider_network_opt_in_requested: false", run.stdout)
        self.assertIn("provider_network_opt_in_allowed: false", run.stdout)
        self.assertIn("provider_network_status: blocked_no_opt_in", run.stdout)
        self.assertIn("provider_request_requested: false", run.stdout)
        self.assertIn("provider_request_status: blocked_provider_not_configured", run.stdout)
        self.assertIn("provider_request_raw_stored: false", run.stdout)
        self.assertIn("provider_response_raw_stored: false", run.stdout)
        self.assertIn("provider_error_class: provider_not_configured", run.stdout)
        self.assertIn("provider_mode: disabled", run.stdout)
        self.assertIn("provider_prompt_source: disabled", run.stdout)
        self.assertIn("prompt_build_requested: false", run.stdout)
        self.assertIn("prompt_build_status: not_built_provider_disabled", run.stdout)
        self.assertIn("prompt_source: disabled", run.stdout)
        self.assertIn("prompt_redaction_status: no_raw_prompt_stored", run.stdout)
        self.assertIn("prompt_storage_policy: no_raw_prompt_storage", run.stdout)
        self.assertIn("prompt_secret_detected: false", run.stdout)
        self.assertIn("prompt_raw_stored: false", run.stdout)
        self.assertIn("response_present: false", run.stdout)
        self.assertIn("response_status: provider_disabled", run.stdout)
        self.assertIn("response_source: disabled_adapter", run.stdout)
        self.assertIn("response_reported_only: true", run.stdout)
        self.assertIn("response_trust_boundary: reported_only", run.stdout)
        self.assertIn("response_redaction_status: no_raw_response_stored", run.stdout)
        self.assertIn("response_raw_stored: false", run.stdout)
        self.assertIn("response_error_class: provider_not_configured", run.stdout)
        self.assertIn("provider_network_opt_in: false", run.stdout)
        self.assertIn("provider_response_present: false", run.stdout)
        self.assertIn("provider_response_status: provider_not_configured", run.stdout)
        self.assertIn("provider_response_source: disabled_adapter", run.stdout)
        self.assertIn("provider_response_reported_only: true", run.stdout)
        self.assertIn("provider_response_trust_boundary: reported_only", run.stdout)
        self.assertIn("proposal_present: false", run.stdout)
        self.assertIn("proposal_status: provider_not_configured", run.stdout)
        self.assertIn("proposal_reported_only: true", run.stdout)
        self.assertIn("proposal_redaction_status: no_raw_prompt_or_response_stored", run.stdout)
        self.assertNotIn("status: PASS", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["status"], CLEAN_CORE)
        self.assertTrue(evidence["citizen_one_requested"])
        self.assertEqual(evidence["citizen_one_mode"], CITIZEN_ONE_MODE_PROPOSE)
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED)
        self.assertIn(evidence["citizen_one_status"], CITIZEN_ONE_STATUSES)
        self.assertEqual(evidence["citizen_one_provider_status"], CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED)
        self.assertFalse(evidence["citizen_one_output_present"])
        self.assertEqual(evidence["citizen_one_output_trust_boundary"], REPORTED_ONLY)
        self.assertTrue(evidence["citizen_one_reported_only"])
        self.assertEqual(evidence["citizen_one_hold_reason"], CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(evidence["provider_config_source"], CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE)
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertEqual(evidence["model_output_hash_candidate"], "")
        self._assert_provider_disabled_contract(evidence)
        self._assert_proposal_held_contract(evidence, requires_user_gate=False)
        self.assertEqual(evidence["computed_mutation_delta"], [])
        self.assertEqual(evidence["executor_created_mutation"], [])
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_CLEAN)
        self._assert_action_boundary_scaffold_contract(evidence)
        self.assertFalse(evidence["checks"]["executor"]["provider_calls"])
        self.assertFalse(evidence["checks"]["executor"]["network_calls"])
        self.assertFalse(evidence["checks"]["executor"]["file_mutation"])
        self.assertTrue(evidence["checks"]["citizen_one_proposal_contract_v0_required"])
        self.assertTrue(evidence["checks"]["proposal_reported_only_is_not_judgment_basis"])
        self._assert_no_forbidden_raw_storage_keys(evidence)
        self.assertNotIn("fix typo in README", json.dumps({field: evidence[field] for field in self._provider_adapter_fields()}))

        manifest, _ = self._latest_manifest_with_path()
        for field in self._citizen_one_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_adapter_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_runtime_metadata_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._proposal_fields():
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["provider_adapter_evidence_hash"],
            sha256_json({field: evidence[field] for field in self._provider_adapter_fields()}),
        )
        self.assertEqual(
            manifest["provider_runtime_state_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_runtime_state_fields()}),
        )
        self.assertEqual(
            manifest["provider_selection_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_selection_fields()}),
        )
        self.assertEqual(
            manifest["provider_secret_env_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_secret_env_fields()}),
        )
        self.assertEqual(
            manifest["provider_network_guard_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_network_guard_fields()}),
        )
        self.assertEqual(
            manifest["provider_request_safe_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_request_fields()}),
        )
        self.assertEqual(
            manifest["provider_response_error_safe_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_response_error_fields()}),
        )
        self.assertEqual(
            manifest["proposal_evidence_hash"],
            sha256_json({field: evidence[field] for field in self._proposal_fields()}),
        )
        self._assert_no_forbidden_raw_storage_keys(manifest)

        tracked_status = self._git("status", "--porcelain=v1").stdout.strip()
        self.assertEqual(tracked_status, "")

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: CLEAN_CORE", verify.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED", verify.stdout)
        self.assertIn("provider_response_status: provider_not_configured", verify.stdout)
        self.assertIn("prompt redaction metadata fields matched manifest", verify.stdout)
        self.assertIn("response redaction metadata fields matched manifest", verify.stdout)
        self.assertIn("provider adapter disabled fields matched manifest", verify.stdout)
        self.assertIn("provider runtime state metadata fields matched manifest", verify.stdout)
        self.assertIn("provider selection metadata fields matched manifest", verify.stdout)
        self.assertIn("provider secret/env safe metadata fields matched manifest", verify.stdout)
        self.assertIn("provider network opt-in guard metadata fields matched manifest", verify.stdout)
        self.assertIn("provider request safe metadata fields matched manifest", verify.stdout)
        self.assertIn("provider response/error safe metadata fields matched manifest", verify.stdout)
        self.assertIn("provider runtime opt-in guard metadata is not an external oracle", verify.stdout)
        self.assertIn("provider adapter output is reported_only and not an external oracle", verify.stdout)
        self.assertIn("provider/model response remains reported_only and not an external oracle", verify.stdout)
        self.assertIn("proposal_present: false", verify.stdout)
        self.assertIn("proposal_status: provider_not_configured", verify.stdout)
        self.assertIn("citizen one evidence fields matched manifest", verify.stdout)
        self.assertIn("proposal contract fields matched manifest", verify.stdout)
        self.assertIn("proposal contract is reported_only and not an external oracle", verify.stdout)
        self.assertIn("action boundary scaffold metadata fields matched manifest", verify.stdout)

    def test_proposal_stub_requires_citizen_one_opt_in(self):
        self._aeg("init")

        run = self._aeg("run", "--proposal-stub", "fix typo in README", check=False)

        self.assertEqual(run.returncode, 2)
        self.assertIn("status: FAIL", run.stdout)
        self.assertIn("--proposal-stub requires --citizen-one", run.stdout)
        self.assertFalse((self.repo / ".aeg" / "runs").exists() and any((self.repo / ".aeg" / "runs").iterdir()))

    def test_citizen_one_deterministic_proposal_stub_records_bound_reported_only_proposal(self):
        self._aeg("init")
        run = self._aeg("run", "--citizen-one", "--proposal-stub", "fix typo in README")

        self.assertIn("status: CLEAN_CORE", run.stdout)
        self.assertIn("citizen_one_requested: true", run.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_PROPOSAL_RECORDED", run.stdout)
        self.assertIn("citizen_one_provider_status: not_configured", run.stdout)
        self.assertIn("citizen_one_output_present: true", run.stdout)
        self.assertIn("provider_network_used: false", run.stdout)
        self.assertIn("provider_secret_observed: false", run.stdout)
        self.assertIn("provider_mode: disabled", run.stdout)
        self.assertIn("provider_prompt_source: disabled", run.stdout)
        self.assertIn("prompt_raw_stored: false", run.stdout)
        self.assertIn("response_raw_stored: false", run.stdout)
        self.assertIn("response_reported_only: true", run.stdout)
        self.assertIn("provider_response_present: false", run.stdout)
        self.assertIn("provider_response_status: provider_not_configured", run.stdout)
        self.assertIn("provider_response_reported_only: true", run.stdout)
        self.assertIn("proposal_present: true", run.stdout)
        self.assertIn("proposal_status: deterministic_stub_recorded", run.stdout)
        self.assertIn("proposal_source: deterministic_stub", run.stdout)
        self.assertIn("proposal_reported_only: true", run.stdout)
        self.assertIn("proposal_trust_boundary: reported_only", run.stdout)
        self.assertIn("proposal_requires_user_gate: false", run.stdout)
        self.assertIn("proposal_redaction_status: no_raw_prompt_or_response_stored", run.stdout)
        self.assertNotIn("status: PASS", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["status"], CLEAN_CORE)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertTrue(evidence["citizen_one_requested"])
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_PROPOSAL_RECORDED)
        self.assertEqual(evidence["citizen_one_provider_status"], CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED)
        self.assertTrue(evidence["citizen_one_output_present"])
        self.assertEqual(evidence["citizen_one_output_trust_boundary"], REPORTED_ONLY)
        self.assertTrue(evidence["citizen_one_reported_only"])
        self.assertEqual(evidence["citizen_one_hold_reason"], "")
        self.assertEqual(evidence["provider_config_source"], CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE)
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertEqual(evidence["model_output_hash_candidate"], "")
        self._assert_provider_disabled_contract(evidence)
        self._assert_proposal_stub_contract(evidence, requires_user_gate=False)
        self.assertEqual(evidence["computed_mutation_delta"], [])
        self.assertEqual(evidence["executor_created_mutation"], [])
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_CLEAN)
        self._assert_action_boundary_scaffold_contract(evidence)
        self.assertFalse(evidence["checks"]["executor"]["provider_calls"])
        self.assertFalse(evidence["checks"]["executor"]["network_calls"])
        self.assertFalse(evidence["checks"]["executor"]["file_mutation"])
        self.assertTrue(evidence["checks"]["deterministic_proposal_stub_opt_in"])
        self.assertTrue(evidence["checks"]["proposal_reported_only_is_not_judgment_basis"])
        self._assert_no_forbidden_raw_storage_keys(evidence)
        self.assertNotIn("fix typo in README", json.dumps({field: evidence[field] for field in self._provider_adapter_fields()}))
        self.assertNotIn("fix typo in README", json.dumps({field: evidence[field] for field in self._proposal_fields()}))

        manifest, _ = self._latest_manifest_with_path()
        for field in self._citizen_one_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_adapter_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._provider_runtime_metadata_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._proposal_fields():
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["provider_adapter_evidence_hash"],
            sha256_json({field: evidence[field] for field in self._provider_adapter_fields()}),
        )
        self.assertEqual(
            manifest["provider_request_safe_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_request_fields()}),
        )
        self.assertEqual(
            manifest["provider_response_error_safe_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._provider_response_error_fields()}),
        )
        self.assertEqual(
            manifest["proposal_evidence_hash"],
            sha256_json({field: evidence[field] for field in self._proposal_fields()}),
        )
        self._assert_no_forbidden_raw_storage_keys(manifest)

        tracked_status = self._git("status", "--porcelain=v1").stdout.strip()
        self.assertEqual(tracked_status, "")
        tracked_aeg_env = self._git("ls-files", ".aeg", ".env").stdout.strip()
        self.assertEqual(tracked_aeg_env, "")

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: CLEAN_CORE", verify.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_PROPOSAL_RECORDED", verify.stdout)
        self.assertIn("provider_response_status: provider_not_configured", verify.stdout)
        self.assertIn("prompt redaction metadata fields matched manifest", verify.stdout)
        self.assertIn("response redaction metadata fields matched manifest", verify.stdout)
        self.assertIn("provider adapter disabled fields matched manifest", verify.stdout)
        self.assertIn("provider request safe metadata fields matched manifest", verify.stdout)
        self.assertIn("provider response/error safe metadata fields matched manifest", verify.stdout)
        self.assertIn("proposal_present: true", verify.stdout)
        self.assertIn("proposal_status: deterministic_stub_recorded", verify.stdout)
        self.assertIn("proposal_source: deterministic_stub", verify.stdout)
        self.assertIn("citizen one evidence fields matched manifest", verify.stdout)
        self.assertIn("proposal contract fields matched manifest", verify.stdout)
        self.assertIn("proposal contract is reported_only and not an external oracle", verify.stdout)
        self.assertIn("law status replay matched: CLEAN_CORE", verify.stdout)
        self.assertIn("action boundary scaffold metadata fields matched manifest", verify.stdout)

    def test_deterministic_proposal_stub_does_not_call_network_or_require_api_key(self):
        self._aeg("init")
        dummy_provider_value = "DUMMY_PROVIDER_VALUE_SHOULD_NOT_APPEAR"

        with patch.dict(os.environ, {"OPENAI_API_KEY": dummy_provider_value}, clear=False):
            with patch("socket.socket", side_effect=AssertionError("network call attempted")):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    exit_code = _cmd_run(
                        self.repo,
                        "fix typo in README",
                        citizen_one_requested=True,
                        proposal_stub_requested=True,
                    )

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_PROPOSAL_RECORDED)
        self.assertEqual(evidence["proposal_source"], PROPOSAL_SOURCE_DETERMINISTIC_STUB)
        self._assert_provider_disabled_contract(evidence)
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertNotIn(dummy_provider_value, output.getvalue())
        self.assertNotIn(dummy_provider_value, json.dumps(evidence, sort_keys=True))
        for artifact in (self.repo / ".aeg").rglob("*"):
            if artifact.is_file():
                self.assertNotIn(dummy_provider_value, artifact.read_text(encoding="utf-8"))

    def test_citizen_one_opt_in_without_provider_does_not_call_network(self):
        self._aeg("init")

        with patch("socket.socket", side_effect=AssertionError("network call attempted")):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README", citizen_one_requested=True)

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_network_opt_in"])
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED)
        self._assert_provider_disabled_contract(evidence)

    def test_citizen_one_opt_in_without_provider_does_not_require_api_key(self):
        self._aeg("init")
        provider_keys = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")

        with patch.dict(os.environ, {}, clear=False):
            for key in provider_keys:
                os.environ.pop(key, None)
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README", citizen_one_requested=True)

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(evidence["provider_config_source"], CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE)
        self.assertEqual(evidence["provider_secret_source"], PROVIDER_SECRET_SOURCE_NONE)
        self.assertFalse(evidence["provider_secret_observed"])
        self._assert_provider_disabled_contract(evidence)

    def test_citizen_one_opt_in_without_provider_logs_no_secret(self):
        self._aeg("init")
        dummy_provider_value = "DUMMY_PROVIDER_VALUE_SHOULD_NOT_APPEAR"

        with patch.dict(os.environ, {"OPENAI_API_KEY": dummy_provider_value}, clear=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_run(self.repo, "fix typo in README", citizen_one_requested=True)

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertNotIn(dummy_provider_value, output.getvalue())
        self.assertNotIn(dummy_provider_value, json.dumps(evidence, sort_keys=True))
        for artifact in (self.repo / ".aeg").rglob("*"):
            if artifact.is_file():
                self.assertNotIn(dummy_provider_value, artifact.read_text(encoding="utf-8"))
        self.assertFalse(evidence["provider_secret_observed"])
        self._assert_provider_disabled_contract(evidence)

    def test_citizen_one_opt_in_high_remains_user_gated(self):
        self._aeg("init")
        run = self._aeg("run", "--citizen-one", "merge to main and deploy")

        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED", run.stdout)
        self.assertIn("proposal_requires_user_gate: true", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertTrue(evidence["citizen_one_requested"])
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED)
        self._assert_provider_disabled_contract(evidence)
        self._assert_proposal_held_contract(evidence, requires_user_gate=True)
        self.assertIn("law.high.requires_user_gate", evidence["status_reasons"])

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("HIGH risk remained NEEDS_USER_GATE", verify.stdout)
        self.assertIn("law status replay matched: NEEDS_USER_GATE", verify.stdout)

    def test_deterministic_proposal_stub_high_remains_user_gated(self):
        self._aeg("init")
        run = self._aeg("run", "--citizen-one", "--proposal-stub", "merge to main and deploy")

        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        self.assertIn("citizen_one_status: CITIZEN_ONE_PROPOSAL_RECORDED", run.stdout)
        self.assertIn("proposal_present: true", run.stdout)
        self.assertIn("proposal_requires_user_gate: true", run.stdout)
        self.assertNotIn("status: PASS", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertEqual(evidence["citizen_one_status"], CITIZEN_ONE_PROPOSAL_RECORDED)
        self._assert_provider_disabled_contract(evidence)
        self._assert_proposal_stub_contract(evidence, requires_user_gate=True)
        self.assertIn("law.high.requires_user_gate", evidence["status_reasons"])
        self.assertEqual(evidence["computed_mutation_delta"], [])
        self.assertEqual(evidence["executor_created_mutation"], [])

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("HIGH risk remained NEEDS_USER_GATE", verify.stdout)
        self.assertIn("law status replay matched: NEEDS_USER_GATE", verify.stdout)
        self.assertIn("proposal_requires_user_gate: true", verify.stdout)

    def test_citizen_one_proposal_does_not_promote_not_checked_or_replace_law_status(self):
        self._aeg("init")
        run = self._aeg("run", "--citizen-one", "do the thing")

        self.assertIn("risk_level: MEDIUM", run.stdout)
        self.assertIn("status: NOT_CHECKED", run.stdout)
        self.assertIn("proposal_present: false", run.stdout)
        self.assertNotIn("status: PASS", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["status"], NOT_CHECKED)
        self._assert_provider_disabled_contract(evidence)
        self._assert_proposal_held_contract(evidence, requires_user_gate=False)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NOT_CHECKED", verify.stdout)
        self.assertIn("law status replay matched: NOT_CHECKED", verify.stdout)
        self.assertIn("NOT_CHECKED was not promoted to PASS", verify.stdout)

    def test_deterministic_proposal_stub_does_not_promote_not_checked_or_replace_law_status(self):
        self._aeg("init")
        run = self._aeg("run", "--citizen-one", "--proposal-stub", "do the thing")

        self.assertIn("risk_level: MEDIUM", run.stdout)
        self.assertIn("status: NOT_CHECKED", run.stdout)
        self.assertIn("proposal_present: true", run.stdout)
        self.assertIn("proposal_status: deterministic_stub_recorded", run.stdout)
        self.assertNotIn("status: PASS", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["status"], NOT_CHECKED)
        self.assertEqual(evidence["proposal_source"], PROPOSAL_SOURCE_DETERMINISTIC_STUB)
        self._assert_provider_disabled_contract(evidence)
        self._assert_proposal_stub_contract(evidence, requires_user_gate=False)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NOT_CHECKED", verify.stdout)
        self.assertIn("law status replay matched: NOT_CHECKED", verify.stdout)
        self.assertIn("NOT_CHECKED was not promoted to PASS", verify.stdout)

    def test_verify_rejects_tampered_citizen_one_fields(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["provider_network_used"] = True
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("Citizen One provider_network_used must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest provider_network_used mismatch", verify.stdout)

    def test_verify_rejects_tampered_provider_adapter_disabled_fields(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["provider_network_opt_in"] = True
        evidence["provider_response_status"] = "completed"
        evidence["provider_response_error_safe_summary"] = "tampered external answer"
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: provider_network_opt_in must be false in disabled contract", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: invalid provider_response_status: completed", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider response status must be provider_not_configured", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider response safe summary mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest provider_network_opt_in mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest provider_response_status mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider adapter disabled fields mismatch", verify.stdout)

    def test_prompt_response_redaction_metadata_is_bound_without_raw_storage(self):
        self._aeg("init")
        dummy_provider_value = "DUMMY_PROVIDER_SECRET_SHOULD_NOT_APPEAR"

        with patch.dict(os.environ, {"OPENAI_API_KEY": dummy_provider_value}, clear=False):
            run = self._aeg("run", "--citizen-one", "fix typo in README")

        self.assertIn("prompt_raw_stored: false", run.stdout)
        self.assertIn("response_raw_stored: false", run.stdout)
        self.assertNotIn(dummy_provider_value, run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_prompt_redaction_disabled_contract(evidence)
        self._assert_response_redaction_disabled_contract(evidence)
        for field in self._prompt_redaction_fields():
            self.assertEqual(manifest[field], evidence[field])
        for field in self._response_redaction_fields():
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["prompt_redaction_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._prompt_redaction_fields()}),
        )
        self.assertEqual(
            manifest["response_redaction_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._response_redaction_fields()}),
        )
        self.assertNotIn("fix typo in README", json.dumps({field: evidence[field] for field in self._prompt_redaction_fields()}))
        self.assertNotIn("fix typo in README", json.dumps({field: evidence[field] for field in self._response_redaction_fields()}))
        self._assert_no_forbidden_raw_storage_keys(evidence)
        self._assert_no_forbidden_raw_storage_keys(manifest)
        self._assert_artifacts_do_not_store_forbidden_raw_keys_or_secret(dummy_provider_value)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("prompt redaction metadata fields matched manifest", verify.stdout)
        self.assertIn("response redaction metadata fields matched manifest", verify.stdout)
        self.assertIn("provider/model response remains reported_only and not an external oracle", verify.stdout)
        self.assertNotIn(dummy_provider_value, verify.stdout)

    def test_provider_runtime_opt_in_guard_metadata_is_bound_without_raw_or_secret_storage(self):
        self._aeg("init")
        dummy_provider_value = "DUMMY_PROVIDER_RUNTIME_SECRET_SHOULD_NOT_APPEAR"

        with patch.dict(os.environ, {"OPENAI_API_KEY": dummy_provider_value}, clear=False):
            run = self._aeg("run", "--citizen-one", "fix typo in README")

        self.assertIn("provider_runtime_state: hold_current_state", run.stdout)
        self.assertIn("provider_selection_requested: true", run.stdout)
        self.assertIn("provider_secret_value_recorded: false", run.stdout)
        self.assertIn("provider_env_loading_requested: false", run.stdout)
        self.assertIn("provider_network_opt_in_allowed: false", run.stdout)
        self.assertIn("provider_request_raw_stored: false", run.stdout)
        self.assertIn("provider_response_raw_stored: false", run.stdout)
        self.assertNotIn(dummy_provider_value, run.stdout)

        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()
        self._assert_provider_disabled_contract(evidence)
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_value_recorded"])
        self.assertFalse(evidence["provider_env_loading_requested"])
        self.assertFalse(evidence["provider_request_raw_stored"])
        self.assertFalse(evidence["provider_response_raw_stored"])

        for fields, hash_field in (
            (self._provider_runtime_state_fields(), "provider_runtime_state_metadata_hash"),
            (self._provider_selection_fields(), "provider_selection_metadata_hash"),
            (self._provider_secret_env_fields(), "provider_secret_env_metadata_hash"),
            (self._provider_network_guard_fields(), "provider_network_guard_metadata_hash"),
            (self._provider_request_fields(), "provider_request_safe_metadata_hash"),
            (self._provider_response_error_fields(), "provider_response_error_safe_metadata_hash"),
        ):
            with self.subTest(hash_field=hash_field):
                for field in fields:
                    self.assertEqual(manifest[field], evidence[field])
                self.assertEqual(manifest[hash_field], sha256_json({field: evidence[field] for field in fields}))

        self._assert_no_forbidden_raw_storage_keys(evidence)
        self._assert_no_forbidden_raw_storage_keys(manifest)
        self._assert_artifacts_do_not_store_forbidden_raw_keys_or_secret(dummy_provider_value)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("provider runtime state metadata fields matched manifest", verify.stdout)
        self.assertIn("provider selection metadata fields matched manifest", verify.stdout)
        self.assertIn("provider secret/env safe metadata fields matched manifest", verify.stdout)
        self.assertIn("provider network opt-in guard metadata fields matched manifest", verify.stdout)
        self.assertIn("provider request safe metadata fields matched manifest", verify.stdout)
        self.assertIn("provider response/error safe metadata fields matched manifest", verify.stdout)
        self.assertNotIn(dummy_provider_value, verify.stdout)

    def test_verify_rejects_tampered_provider_runtime_opt_in_guard_metadata(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["provider_selected"] = True
        evidence["provider_secret_value_recorded"] = True
        evidence["provider_env_loading_requested"] = True
        evidence["provider_network_opt_in_allowed"] = True
        evidence["provider_request_raw_stored"] = True
        evidence["provider_response_raw_stored"] = True
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: provider_selected must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider_secret_value_recorded must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider_env_loading_requested must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider_network_opt_in_allowed must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider_request_raw_stored must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider_response_raw_stored must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider selection metadata fields mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider secret/env safe metadata fields mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider network opt-in guard metadata fields mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider request safe metadata fields mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: provider response/error safe metadata fields mismatch", verify.stdout)

    def test_verify_rejects_tampered_prompt_response_redaction_metadata(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["prompt_raw_stored"] = True
        evidence["response_raw_stored"] = True
        evidence["response_status"] = "completed"
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: prompt_raw_stored must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: response_raw_stored must be false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: invalid response_status: completed", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: requested response_status must be provider_disabled", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest prompt_raw_stored mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest response_status mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: prompt redaction metadata fields mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: response redaction metadata fields mismatch", verify.stdout)

    def test_verify_rejects_forbidden_raw_keys_in_evidence(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        original, path = self._latest_evidence_with_path()
        forbidden_value = "RAW_PROMPT_RESPONSE_VALUE_SHOULD_NOT_APPEAR_IN_VERIFY_OUTPUT"

        for key in FORBIDDEN_RAW_PROMPT_RESPONSE_KEYS:
            with self.subTest(key=key):
                tampered = dict(original)
                tampered[key] = forbidden_value
                self._write_json(path, tampered)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn(f"forbidden raw/secret storage key in evidence: {key}", verify.stdout)
                self.assertNotIn(forbidden_value, verify.stdout)

    def test_verify_rejects_forbidden_raw_key_in_manifest_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        forbidden_value = "RAW_RESPONSE_VALUE_SHOULD_NOT_APPEAR_IN_VERIFY_OUTPUT"
        manifest["metadata"] = {"response_text": forbidden_value}
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("forbidden raw/secret storage key in manifest: metadata.response_text", verify.stdout)
        self.assertNotIn(forbidden_value, verify.stdout)

    def test_verify_rejects_forbidden_secret_key_in_manifest_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        forbidden_value = "SECRET_VALUE_SHOULD_NOT_APPEAR_IN_VERIFY_OUTPUT"
        manifest["metadata"] = {"api_key": forbidden_value}
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("forbidden raw/secret storage key in manifest: metadata.api_key", verify.stdout)
        self.assertNotIn(forbidden_value, verify.stdout)

    def test_verify_rejects_tampered_proposal_fields(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["proposal_status"] = "generated"
        evidence["proposal_summary"] = "safe to execute"
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: proposal_summary must be empty when proposal is not generated", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: invalid proposal_status: generated", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest proposal_status mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: proposal contract fields mismatch", verify.stdout)

    def test_verify_rejects_tampered_deterministic_proposal_stub_fields(self):
        self._aeg("init")
        self._aeg("run", "--citizen-one", "--proposal-stub", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["proposal_steps"] = ["tampered external recommendation"]
        evidence["proposal_output_hash_candidate"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: deterministic proposal stub steps mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: deterministic proposal stub output hash candidate mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest proposal_steps mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: proposal contract fields mismatch", verify.stdout)

    def test_action_boundary_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("action_boundary_status: ACTION_BOUNDARY_NOT_CHECKED", run.stdout)
        self.assertIn("action_interception_enabled: false", run.stdout)
        self.assertIn("action_count: 0", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_action_boundary_scaffold_contract(evidence)
        for field in self._action_boundary_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["action_boundary_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._action_boundary_fields()}),
        )
        self.assertEqual(evidence["bound_action_boundary_metadata_hash"], manifest["action_boundary_metadata_hash"])

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("computed_action_log_hash replay matched", verify.stdout)
        self.assertIn("action_count replay matched expected no-op count: 0", verify.stdout)
        self.assertIn("action authority flags default false", verify.stdout)
        self.assertIn("executor_reported_actions remains reported_only context, not judgment basis", verify.stdout)
        self.assertIn("command enumeration alone grants no authority", verify.stdout)

    def test_capability_isolation_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("capability_isolation_enabled: false", run.stdout)
        self.assertIn("capability_isolation_mode: not_implemented", run.stdout)
        self.assertIn("capability_boundary_status: CAPABILITY_BOUNDARY_NOT_CHECKED", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_capability_isolation_scaffold_contract(evidence)
        for field in self._capability_isolation_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["capability_isolation_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._capability_isolation_fields()}),
        )
        self.assertEqual(
            evidence["bound_capability_isolation_metadata_hash"],
            manifest["capability_isolation_metadata_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("capability_matrix_hash replay matched", verify.stdout)
        self.assertIn("capability_isolation_proof_hash replay matched scaffold unavailable proof", verify.stdout)
        self.assertIn("capability authority flags default false", verify.stdout)
        self.assertIn("executor_reported_capabilities remains reported_only context, not judgment basis", verify.stdout)
        self.assertIn("capability not implemented did not claim CLEAN", verify.stdout)

    def test_tool_surface_authority_grant_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("tool_surface_enabled: false", run.stdout)
        self.assertIn("tool_surface_status: TOOL_SURFACE_SCAFFOLD_ONLY", run.stdout)
        self.assertIn("tool_authority_grant_count: 0", run.stdout)
        self.assertIn("expected_tool_authority_grant_count: 0", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_tool_surface_scaffold_contract(evidence)
        self.assertEqual(evidence["requested_tool_capabilities"], [])
        self.assertEqual(evidence["granted_tool_capabilities"], [])
        self.assertEqual(evidence["denied_tool_capabilities"], [])
        for field in self._tool_surface_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["tool_surface_authority_metadata_hash"],
            sha256_json({field: evidence[field] for field in self._tool_surface_fields()}),
        )
        self.assertEqual(
            evidence["bound_tool_surface_metadata_hash"],
            manifest["tool_surface_authority_metadata_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("tool_authority_grant_hash replay matched", verify.stdout)
        self.assertIn("tool_surface_metadata_hash replay matched scaffold unavailable proof", verify.stdout)
        self.assertIn("tool authority grant count replay matched expected zero: 0", verify.stdout)
        self.assertIn("no granted tool authority by default", verify.stdout)
        self.assertIn("tool authority flags default false", verify.stdout)
        self.assertIn("executor_reported_tool_usage remains reported_only context, not judgment basis", verify.stdout)
        self.assertIn("tool surface not implemented did not claim CLEAN", verify.stdout)
        self.assertIn("command denylist alone grants no tool authority", verify.stdout)

    def test_executor_capability_exposure_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("current_executor_capability_status: NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION", run.stdout)
        self.assertIn("capability_shell: false", run.stdout)
        self.assertIn("capability_network: false", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_executor_capability_exposure_contract(evidence)
        for field in self._executor_capability_exposure_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["executor_capability_exposure_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._executor_capability_exposure_fields()}),
        )
        self.assertEqual(
            evidence["bound_executor_capability_exposure_metadata_hash"],
            manifest["executor_capability_exposure_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("executor_capability_exposure_hash replay matched", verify.stdout)
        self.assertIn("executor capability exposure fields default false", verify.stdout)
        self.assertIn("current no-op executor capability status matched: NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION", verify.stdout)
        self.assertIn("current no-op executor has no shell/network/provider/action capability", verify.stdout)
        self.assertIn("no raw shell was not treated as proof of no dangerous capability", verify.stdout)
        self.assertIn("structured tool call was not treated as safe capability", verify.stdout)

    def test_evidence_store_trust_boundary_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("evidence_store_trust_boundary: folder_local_not_executor_isolated", run.stdout)
        self.assertIn("evidence_store_is_executor_isolated: false", run.stdout)
        self.assertIn("executor_can_write_evidence_store: NOT_CHECKED_SAME_USER_AUTHORITY", run.stdout)
        self.assertIn("evidence_store_integrity_status: NOT_CHECKED", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_evidence_store_trust_contract(evidence)
        for field in self._evidence_store_trust_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["evidence_store_trust_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._evidence_store_trust_fields()}),
        )
        self.assertEqual(
            evidence["bound_evidence_store_trust_metadata_hash"],
            manifest["evidence_store_trust_manifest_hash"],
        )
        self.assertEqual(
            evidence["bound_ledger_integrity_metadata_hash"],
            manifest["ledger_integrity_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_store_trust_metadata_hash replay matched folder-local scaffold", verify.stdout)
        self.assertIn("evidence store trust boundary remained folder_local_not_executor_isolated", verify.stdout)
        self.assertIn("evidence_store_is_executor_isolated remained false", verify.stdout)
        self.assertIn("evidence store integrity status remained NOT_CHECKED", verify.stdout)
        self.assertIn(".aeg folder-local state was not treated as executor-isolated", verify.stdout)
        self.assertIn("evidence binding was not treated as evidence store tamper-proof", verify.stdout)

    def test_aeg_state_write_denial_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("aeg_state_write_denial_status: DENIAL_SCAFFOLD_ONLY", run.stdout)
        self.assertIn("capability_write_aeg_state_requested: false", run.stdout)
        self.assertIn("capability_write_aeg_state_granted: false", run.stdout)
        self.assertIn("capability_write_aeg_state_denied: true", run.stdout)
        self.assertIn("aeg_state_write_denial_enforcement_status: SCAFFOLD_ONLY_NOT_ENFORCED", run.stdout)
        self.assertNotIn("aeg_state_write_denial_status: CLEAN", run.stdout)
        self.assertNotIn("aeg_state_write_denial_status: PASS", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_aeg_state_write_denial_scaffold_contract(evidence)
        for field in self._aeg_state_write_denial_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["aeg_state_write_denial_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._aeg_state_write_denial_fields()}),
        )
        self.assertEqual(
            evidence["bound_aeg_state_write_denial_metadata_hash"],
            manifest["aeg_state_write_denial_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("aeg_state_write_denial_metadata_hash replay matched", verify.stdout)
        self.assertIn("capability_write_aeg_state_granted remained false", verify.stdout)
        self.assertIn("capability_write_aeg_state_denied remained explicit true", verify.stdout)
        self.assertIn("aeg_state_write_denial_enforcement_status remained SCAFFOLD_ONLY_NOT_ENFORCED", verify.stdout)
        self.assertIn("aeg state write bypass flags default false", verify.stdout)
        self.assertIn("executor self-report was not treated as aeg state write denial proof", verify.stdout)
        self.assertIn("capability_write_aeg_state denied metadata was not treated as external enforcement", verify.stdout)

    def test_capability_write_aeg_state_grant_cannot_pass_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["capability_write_aeg_state_requested"] = True
        evidence["capability_write_aeg_state_granted"] = True
        evidence["capability_write_aeg_state_denied"] = False
        evidence["aeg_state_write_denial_metadata_hash"] = expected_aeg_state_write_denial_metadata_hash(evidence)
        self._sync_aeg_state_write_denial_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: capability_write_aeg_state_requested must remain false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: capability_write_aeg_state_granted must remain false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: capability_write_aeg_state_denied must be explicit true", verify.stdout)

    def test_aeg_state_write_denial_enforced_or_clean_claim_fails_even_when_rebound(self):
        self._aeg("init")
        for field, value in (
            ("aeg_state_write_denial_status", "CLEAN"),
            ("aeg_state_write_denial_enforcement_status", "ENFORCED"),
        ):
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = value
                evidence["aeg_state_write_denial_metadata_hash"] = expected_aeg_state_write_denial_metadata_hash(evidence)
                self._sync_aeg_state_write_denial_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                if field == "aeg_state_write_denial_status":
                    self.assertIn(
                        "INVALID_EVIDENCE: aeg_state_write_denial_status cannot claim CLEAN/PASS/ENFORCED",
                        verify.stdout,
                    )
                    self.assertIn(
                        "INVALID_EVIDENCE: aeg_state_write_denial_status must remain DENIAL_SCAFFOLD_ONLY",
                        verify.stdout,
                    )
                else:
                    self.assertIn(
                        "INVALID_EVIDENCE: aeg_state_write_denial_enforcement_status cannot claim ENFORCED/CLEAN/PASS",
                        verify.stdout,
                    )
                    self.assertIn(
                        "INVALID_EVIDENCE: aeg_state_write_denial_enforcement_status must remain "
                        "SCAFFOLD_ONLY_NOT_ENFORCED",
                        verify.stdout,
                    )

    def test_aeg_state_write_denial_bypass_flags_cannot_pass_even_when_rebound(self):
        self._aeg("init")
        for field in AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS:
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = True
                evidence["aeg_state_write_denial_metadata_hash"] = expected_aeg_state_write_denial_metadata_hash(evidence)
                self._sync_aeg_state_write_denial_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {field} must remain false", verify.stdout)
                self.assertIn("INVALID_EVIDENCE: aeg state write bypass flags must default false", verify.stdout)

    def test_executor_self_report_cannot_become_aeg_state_write_denial_proof(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["aeg_state_write_denial_source"] = "executor_self_report"
        evidence["executor_reported_aeg_state_write_denial"] = {
            "capability_write_aeg_state_denied": True,
            "trust_boundary": REPORTED_ONLY,
            "judgment_basis": True,
        }
        evidence["judgment_basis"] = "executor_reported_aeg_state_write_denial"
        evidence["aeg_state_write_denial_metadata_hash"] = expected_aeg_state_write_denial_metadata_hash(evidence)
        self._sync_aeg_state_write_denial_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: aeg_state_write_denial_source must be aegis runtime scaffold metadata", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: executor self-report cannot prove aeg state write denial", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: executor_reported_aeg_state_write_denial cannot become judgment basis",
            verify.stdout,
        )

    def test_verify_rejects_tampered_aeg_state_write_denial_metadata_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["aeg_state_write_denial_metadata_hash"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: aeg_state_write_denial_metadata_hash mismatch", verify.stdout)

    def test_verify_rejects_tampered_aeg_state_write_denial_manifest_metadata_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["raw_shell_can_write_aeg_state"] = True
        manifest["aeg_state_write_denial_metadata_hash"] = expected_aeg_state_write_denial_metadata_hash(manifest)
        manifest["aeg_state_write_denial_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._aeg_state_write_denial_fields()}
        )
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest raw_shell_can_write_aeg_state mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: aeg state write denial metadata fields mismatch", verify.stdout)

    def test_verify_rejects_missing_aeg_state_write_denial_fields(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["aeg_state_write_denial_version"]
        del evidence["bound_aeg_state_write_denial_metadata_hash"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: aeg_state_write_denial_version", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: missing evidence binding v1 field: bound_aeg_state_write_denial_metadata_hash",
            verify.stdout,
        )

    def test_mediated_write_boundary_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("mediated_write_boundary_scaffold_status: SCAFFOLD_ONLY_NOT_ENFORCED", run.stdout)
        self.assertIn("mediated_write_boundary_enforcement_status: SCAFFOLD_ONLY_NOT_ENFORCED", run.stdout)
        self.assertIn("write_mediation_enabled: false", run.stdout)
        self.assertIn("write_mediation_enforced: false", run.stdout)
        self.assertIn("write_classes_declared_count: 13", run.stdout)
        self.assertIn("write_classes_granted_count: 0", run.stdout)
        self.assertIn("write_classes_denied_count: 13", run.stdout)
        self.assertIn("write_mediation_evidence_status: NOT_CHECKED", run.stdout)
        self.assertNotIn("mediated_write_boundary_scaffold_status: SAFE_TO_RUN", run.stdout)
        self.assertNotIn("mediated_write_boundary_enforcement_status: ENFORCED", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_mediated_write_boundary_scaffold_contract(evidence)
        self._assert_pre_live_executor_gate_contract(evidence)
        for field in self._mediated_write_boundary_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["mediated_write_boundary_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._mediated_write_boundary_fields()}),
        )
        self.assertEqual(
            evidence["bound_mediated_write_boundary_metadata_hash"],
            manifest["mediated_write_boundary_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("mediated write boundary scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("mediated write scaffold did not perform OS/filesystem write mediation", verify.stdout)
        self.assertIn("mediated_write_boundary_scaffold_status remained SCAFFOLD_ONLY_NOT_ENFORCED", verify.stdout)
        self.assertIn("write_mediation_enabled remained false", verify.stdout)
        self.assertIn("write_mediation_enforced remained false", verify.stdout)
        self.assertIn("write_classes_granted remained empty", verify.stdout)
        self.assertIn("dangerous direct write grants default false", verify.stdout)
        self.assertIn("write mediation NOT_CHECKED was not promoted to PASS", verify.stdout)
        self.assertIn("metadata denial was not treated as external enforcement", verify.stdout)
        self.assertIn("live executor authority remained ON_HOLD", verify.stdout)

    def test_mediated_write_boundary_rejects_dangerous_direct_write_grants_even_when_rebound(self):
        self._aeg("init")
        for field in MEDIATED_WRITE_DIRECT_ALLOW_FIELDS:
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = True
                evidence["mediated_write_boundary_metadata_hash"] = (
                    expected_mediated_write_boundary_metadata_hash(evidence)
                )
                self._sync_mediated_write_boundary_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {field} must remain false in scaffold v0", verify.stdout)
                self.assertIn("INVALID_EVIDENCE: dangerous direct write grants must default false", verify.stdout)

    def test_mediated_write_boundary_rejects_unknown_write_class_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["write_classes_declared"] = [*evidence["write_classes_declared"], "unknown_write_class"]
        evidence["write_mediation_decision_hash"] = expected_write_mediation_decision_hash(evidence)
        evidence["mediated_write_boundary_metadata_hash"] = expected_mediated_write_boundary_metadata_hash(evidence)
        self._sync_mediated_write_boundary_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: unknown write class in write_classes_declared: unknown_write_class", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: write_classes_declared must match Phase 10 scaffold vocabulary", verify.stdout)

    def test_mediated_write_boundary_rejects_unknown_mediation_status_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        write_class = WRITE_CLASSES[0]
        evidence["write_class_mediation_statuses"] = dict(evidence["write_class_mediation_statuses"])
        evidence["write_class_mediation_statuses"][write_class] = "MAGIC_ALLOW"
        evidence["write_mediation_decision_hash"] = expected_write_mediation_decision_hash(evidence)
        evidence["mediated_write_boundary_metadata_hash"] = expected_mediated_write_boundary_metadata_hash(evidence)
        self._sync_mediated_write_boundary_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn(f"INVALID_EVIDENCE: unknown mediation status for {write_class}: MAGIC_ALLOW", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: write_class_mediation_statuses must match scaffold default decisions", verify.stdout)

    def test_mediated_write_boundary_rejects_scaffold_overclaim_even_when_rebound(self):
        self._aeg("init")
        for field, value, message in (
            (
                "mediated_write_boundary_scaffold_status",
                "SAFE_TO_RUN",
                "mediated_write_boundary_scaffold_status cannot claim PASS/SAFE/ENFORCED",
            ),
            (
                "mediated_write_boundary_enforcement_status",
                "ENFORCED",
                "mediated_write_boundary_enforcement_status cannot claim PASS/SAFE/ENFORCED",
            ),
            (
                "write_mediation_evidence_status",
                "PASS",
                "write_mediation_evidence_status cannot claim PASS/SAFE/ENFORCED",
            ),
        ):
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = value
                evidence["mediated_write_boundary_metadata_hash"] = (
                    expected_mediated_write_boundary_metadata_hash(evidence)
                )
                self._sync_mediated_write_boundary_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                if field == "write_mediation_evidence_status":
                    self.assertIn("status: REPLAY_FAILED", verify.stdout)
                    self.assertNotIn("Traceback", verify.stdout + verify.stderr)
                else:
                    self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {message}", verify.stdout)

    def test_write_bypass_harness_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("write_bypass_harness_scaffold_status: SCAFFOLD_ONLY_NOT_ENFORCED", run.stdout)
        self.assertIn("write_bypass_harness_execution_status: NOT_CHECKED", run.stdout)
        self.assertIn("write_bypass_harness_expected_wbyp_count: 25", run.stdout)
        self.assertIn("write_bypass_harness_registry_id_count: 25", run.stdout)
        self.assertIn("write_bypass_harness_registry_entry_count: 25", run.stdout)
        self.assertIn("write_bypass_harness_actual_bypass_tests_present: false", run.stdout)
        self.assertIn("write_bypass_harness_actual_fixtures_present: false", run.stdout)
        self.assertIn("write_bypass_harness_actual_write_attempts_present: false", run.stdout)
        self.assertNotIn("write_bypass_harness_execution_status: PASS", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_write_bypass_harness_scaffold_contract(evidence)
        for field in self._write_bypass_harness_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["write_bypass_harness_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._write_bypass_harness_fields()}),
        )
        self.assertEqual(
            evidence["bound_write_bypass_harness_metadata_hash"],
            manifest["write_bypass_harness_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("write bypass harness scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("write bypass harness scaffold did not perform filesystem write attempts", verify.stdout)
        self.assertIn("WBYP registry contained WBYP-001 through WBYP-025", verify.stdout)
        self.assertIn("WBYP registry entries remained future-only metadata", verify.stdout)
        self.assertIn("write bypass harness NOT_CHECKED was not promoted to PASS", verify.stdout)
        self.assertIn("executor self-report was not treated as write bypass proof", verify.stdout)
        self.assertIn("reported_only was not treated as write bypass judgment basis", verify.stdout)
        self.assertIn("live executor authority remained ON_HOLD for write bypass harness scaffold", verify.stdout)

    def test_write_bypass_harness_rejects_missing_wbyp_registry_id_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["write_bypass_harness_registry_ids"] = evidence["write_bypass_harness_registry_ids"][:-1]
        evidence["write_bypass_harness_registry"] = evidence["write_bypass_harness_registry"][:-1]
        evidence["write_bypass_harness_registry_hash"] = expected_write_bypass_harness_registry_hash(evidence)
        evidence["write_bypass_harness_metadata_hash"] = expected_write_bypass_harness_metadata_hash(evidence)
        self._sync_write_bypass_harness_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_registry_ids must be WBYP-001 through WBYP-025",
            verify.stdout,
        )
        self.assertIn("INVALID_EVIDENCE: write_bypass_harness_registry must contain 25 entries", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_registry must contain WBYP-001 through WBYP-025",
            verify.stdout,
        )

    def test_write_bypass_harness_rejects_pass_safe_enforced_overclaims_even_when_rebound(self):
        self._aeg("init")
        for field, value, message in (
            (
                "write_bypass_harness_scaffold_status",
                "SAFE",
                "write_bypass_harness_scaffold_status cannot claim PASS/SAFE/ENFORCED",
            ),
            (
                "write_bypass_harness_execution_status",
                "PASS",
                "write_bypass_harness_execution_status cannot claim PASS/SAFE/ENFORCED",
            ),
            (
                "write_bypass_harness_enforcement_status",
                "ENFORCED",
                "write_bypass_harness_enforcement_status cannot claim PASS/SAFE/ENFORCED",
            ),
        ):
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = value
                evidence["write_bypass_harness_metadata_hash"] = expected_write_bypass_harness_metadata_hash(evidence)
                self._sync_write_bypass_harness_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                if field == "write_bypass_harness_execution_status":
                    self.assertIn("status: REPLAY_FAILED", verify.stdout)
                    self.assertNotIn("Traceback", verify.stdout + verify.stderr)
                else:
                    self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {message}", verify.stdout)

    def test_write_bypass_harness_rejects_actual_present_and_reported_only_proof_claims(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["write_bypass_harness_actual_bypass_tests_present"] = True
        evidence["write_bypass_harness_actual_fixtures_present"] = True
        evidence["write_bypass_harness_actual_write_attempts_present"] = True
        evidence["write_bypass_harness_mediator_enforcement_present"] = True
        evidence["write_bypass_harness_external_enforcement_present"] = True
        evidence["write_bypass_harness_executor_self_report_proof_allowed"] = True
        evidence["write_bypass_harness_reported_only_judgment_basis_allowed"] = True
        evidence["judgment_basis"] = "write_bypass_harness_reported_only"
        evidence["write_bypass_harness_metadata_hash"] = expected_write_bypass_harness_metadata_hash(evidence)
        self._sync_write_bypass_harness_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_actual_bypass_tests_present must remain false in scaffold v0",
            verify.stdout,
        )
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_actual_fixtures_present must remain false in scaffold v0",
            verify.stdout,
        )
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_actual_write_attempts_present must remain false in scaffold v0",
            verify.stdout,
        )
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_mediator_enforcement_present must remain false in scaffold v0",
            verify.stdout,
        )
        self.assertIn(
            "INVALID_EVIDENCE: write_bypass_harness_external_enforcement_present must remain false in scaffold v0",
            verify.stdout,
        )
        self.assertIn(
            "INVALID_EVIDENCE: write bypass reported_only/self-report cannot be judgment basis",
            verify.stdout,
        )
        self.assertIn("INVALID_EVIDENCE: executor self-report cannot prove write bypass harness results", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: reported_only cannot be write bypass judgment basis", verify.stdout)

    def test_pre_live_executor_gate_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("pre_live_executor_gate_status: PRE_LIVE_EXECUTOR_ON_HOLD", run.stdout)
        self.assertIn("live_executor_authority_granted: false", run.stdout)
        self.assertIn("pre_live_executor_gate_result: NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR", run.stdout)
        self.assertNotIn("pre_live_executor_gate_result: PASS", run.stdout)
        self.assertNotIn("pre_live_executor_gate_result: CLEAN", run.stdout)
        self.assertNotIn("pre_live_executor_gate_result: ALLOW", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()

        self._assert_pre_live_executor_gate_contract(evidence)
        for field in self._pre_live_executor_gate_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
        self.assertEqual(
            manifest["pre_live_executor_gate_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._pre_live_executor_gate_fields()}),
        )
        self.assertEqual(
            evidence["bound_pre_live_executor_gate_metadata_hash"],
            manifest["pre_live_executor_gate_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("pre-live executor gate metadata fields matched manifest", verify.stdout)
        self.assertIn("pre_live_executor_gate_status remained PRE_LIVE_EXECUTOR_ON_HOLD", verify.stdout)
        self.assertIn("live_executor_authority_granted remained false", verify.stdout)
        self.assertIn("required tamper-evident ledger scaffold present", verify.stdout)
        self.assertIn("required aeg state write denial scaffold present", verify.stdout)
        self.assertIn("pre_live_executor_gate_result did not claim PASS/CLEAN/ALLOW", verify.stdout)
        self.assertIn("pre_live_executor_gate_metadata_hash replay matched", verify.stdout)

    def test_live_executor_authority_grant_fails_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["live_executor_authority_requested"] = True
        evidence["live_executor_authority_granted"] = True
        evidence["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(evidence)
        self._sync_pre_live_executor_gate_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: live_executor_authority_requested must remain false", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: live_executor_authority_granted must remain false", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: live executor authority cannot be granted by pre-live gate scaffold",
            verify.stdout,
        )

    def test_pre_live_executor_gate_result_cannot_claim_pass_clean_allow_even_when_rebound(self):
        self._aeg("init")
        for result in ("PASS", "CLEAN", "ALLOW"):
            with self.subTest(result=result):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence["pre_live_executor_gate_result"] = result
                evidence["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(evidence)
                self._sync_pre_live_executor_gate_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn("INVALID_EVIDENCE: pre_live_executor_gate_result cannot claim PASS/CLEAN/ALLOW", verify.stdout)
                self.assertIn("INVALID_EVIDENCE: invalid pre_live_executor_gate_result", verify.stdout)
                self.assertIn("INVALID_EVIDENCE: external_enforcement_present=false cannot produce PASS/CLEAN/ALLOW", verify.stdout)
                self.assertIn(
                    "INVALID_EVIDENCE: evidence_store_executor_isolated_present=false cannot produce PASS/CLEAN/ALLOW",
                    verify.stdout,
                )

    def test_pre_live_executor_gate_requires_candidate_e_scaffolds_even_when_rebound(self):
        self._aeg("init")
        for field, message in (
            ("tamper_evident_ledger_present", "tamper-evident ledger scaffold must be present before live executor"),
            ("aeg_state_write_denial_present", "aeg state write denial scaffold must be present before live executor"),
        ):
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = False
                evidence["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(evidence)
                self._sync_pre_live_executor_gate_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {message}", verify.stdout)

    def test_external_enforcement_absence_prevents_gate_pass_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["external_enforcement_present"] = False
        evidence["pre_live_executor_gate_result"] = "PASS"
        evidence["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(evidence)
        self._sync_pre_live_executor_gate_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: external_enforcement_present=false cannot produce PASS/CLEAN/ALLOW", verify.stdout)

    def test_evidence_store_executor_isolation_absence_prevents_gate_clean_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["evidence_store_executor_isolated_present"] = False
        evidence["pre_live_executor_gate_result"] = "CLEAN"
        evidence["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(evidence)
        self._sync_pre_live_executor_gate_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn(
            "INVALID_EVIDENCE: evidence_store_executor_isolated_present=false cannot produce PASS/CLEAN/ALLOW",
            verify.stdout,
        )

    def test_verify_rejects_tampered_pre_live_executor_gate_metadata_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["pre_live_executor_gate_metadata_hash"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: pre_live_executor_gate_metadata_hash mismatch", verify.stdout)

    def test_verify_rejects_tampered_pre_live_executor_gate_manifest_metadata_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["live_executor_authority_granted"] = True
        manifest["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(manifest)
        manifest["pre_live_executor_gate_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._pre_live_executor_gate_fields()}
        )
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest live_executor_authority_granted mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: pre-live executor gate metadata fields mismatch", verify.stdout)

    def test_verify_rejects_missing_pre_live_executor_gate_fields(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["pre_live_executor_gate_version"]
        del evidence["bound_pre_live_executor_gate_metadata_hash"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: pre_live_executor_gate_version", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: missing evidence binding v1 field: bound_pre_live_executor_gate_metadata_hash",
            verify.stdout,
        )

    def test_pre_live_executor_gate_fails_when_required_ledger_scaffold_is_missing(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["ledger_integrity_version"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: ledger_integrity_version", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: required tamper-evident ledger scaffold is missing", verify.stdout)

    def test_pre_live_executor_gate_fails_when_required_denial_scaffold_is_missing(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["aeg_state_write_denial_version"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: aeg_state_write_denial_version", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: required aeg state write denial scaffold is missing", verify.stdout)

    def test_ledger_integrity_scaffold_defaults_are_bound_and_replayed(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")

        self.assertIn("ledger_tamper_evident_enabled: true", run.stdout)
        self.assertIn("ledger_tamper_proof_claimed: false", run.stdout)
        self.assertIn("ledger_integrity_status: TAMPER_EVIDENT_SCAFFOLD_ONLY", run.stdout)
        self.assertIn("ledger_integrity_check_status: NOT_CHECKED", run.stdout)
        self.assertNotIn("ledger_integrity_status: CLEAN", run.stdout)
        self.assertNotIn("ledger_integrity_status: PASS", run.stdout)
        evidence = self._latest_evidence()
        manifest, _ = self._latest_manifest_with_path()
        ledger_entry = self._latest_ledger_entry()

        self._assert_ledger_integrity_scaffold_contract(evidence)
        for field in self._ledger_integrity_fields():
            self.assertIn(field, evidence)
            self.assertEqual(manifest[field], evidence[field])
            self.assertEqual(ledger_entry[field], evidence[field])
        self.assertEqual(
            manifest["ledger_integrity_manifest_hash"],
            sha256_json({field: evidence[field] for field in self._ledger_integrity_fields()}),
        )
        self.assertEqual(
            evidence["bound_ledger_integrity_metadata_hash"],
            manifest["ledger_integrity_manifest_hash"],
        )

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("ledger integrity scaffold metadata fields matched manifest", verify.stdout)
        self.assertIn("ledger scaffold is tamper-evident, not tamper-proof", verify.stdout)
        self.assertIn("ledger_tamper_proof_claimed remained false", verify.stdout)
        self.assertIn("current_evidence_hash replay matched", verify.stdout)
        self.assertIn("current_manifest_hash replay matched", verify.stdout)
        self.assertIn("current_ledger_entry_hash replay matched", verify.stdout)
        self.assertIn("ledger_chain_hash replay matched", verify.stdout)
        self.assertIn("ledger_integrity_metadata_hash replay matched", verify.stdout)

    def test_ledger_hashes_are_deterministic_and_genesis_previous_hash_is_explicit(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        first_evidence = self._latest_evidence()
        first_manifest, _ = self._latest_manifest_with_path()
        first_ledger_entry = self._latest_ledger_entry()

        self.assertEqual(first_evidence["ledger_sequence_number"], 1)
        self.assertEqual(first_evidence["previous_ledger_hash"], LEDGER_PREVIOUS_HASH_GENESIS)
        self.assertEqual(first_evidence["current_evidence_hash"], expected_current_evidence_hash(first_evidence))
        self.assertEqual(first_evidence["current_manifest_hash"], expected_current_manifest_hash(first_manifest))
        self.assertEqual(first_evidence["current_ledger_entry_hash"], expected_ledger_entry_hash(first_ledger_entry))
        self.assertEqual(first_evidence["ledger_chain_hash"], expected_ledger_chain_hash(first_evidence))
        self.assertEqual(
            first_evidence["ledger_integrity_metadata_hash"],
            expected_ledger_integrity_metadata_hash(first_evidence),
        )
        self.assertEqual(first_evidence["current_evidence_hash"], expected_current_evidence_hash(first_evidence))
        self.assertEqual(first_evidence["current_manifest_hash"], expected_current_manifest_hash(first_manifest))

        first_chain_hash = first_evidence["ledger_chain_hash"]
        self._aeg("run", "fix typo in README")
        second_evidence = self._latest_evidence()

        self.assertEqual(second_evidence["ledger_sequence_number"], 2)
        self.assertEqual(second_evidence["previous_ledger_hash"], first_chain_hash)

    def test_verify_rejects_tamper_proof_ledger_overclaim(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["ledger_tamper_proof_claimed"] = True
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: tamper-evident ledger scaffold cannot claim tamper-proof", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger_chain_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger_integrity_metadata_hash mismatch", verify.stdout)

    def test_verify_rejects_tampered_ledger_entry_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        ledger_entry = self._latest_ledger_entry()
        ledger_entry["current_ledger_entry_hash"] = "0" * 64
        self._replace_latest_ledger_entry(ledger_entry)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger current_ledger_entry_hash mismatch", verify.stdout)

    def test_verify_rejects_tampered_ledger_chain_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["ledger_chain_hash"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger_chain_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger_integrity_metadata_hash mismatch", verify.stdout)

    def test_verify_rejects_tampered_ledger_manifest_hash_linkage(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["current_manifest_hash"] = "0" * 64
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest current_manifest_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest current_manifest_hash mismatch with evidence", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger integrity scaffold metadata fields mismatch", verify.stdout)

    def test_verify_rejects_historical_ledger_entry_field_tamper(self):
        entries = self._create_three_ledger_runs()
        entries[1]["risk_level"] = HIGH
        entries[1]["status"] = NEEDS_USER_GATE
        self._write_ledger_entries(entries)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("ledger full-chain walk", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 2 manifest risk_level mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 2 current_ledger_entry_hash mismatch", verify.stdout)

    def test_verify_rejects_middle_ledger_entry_deletion(self):
        entries = self._create_three_ledger_runs()
        del entries[1]
        self._write_ledger_entries(entries)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger line 2 ledger_sequence_number mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 2 previous_ledger_hash mismatch", verify.stdout)

    def test_verify_rejects_ledger_entry_reorder(self):
        entries = self._create_three_ledger_runs()
        entries[0], entries[1] = entries[1], entries[0]
        self._write_ledger_entries(entries)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 ledger_sequence_number mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 first entry previous hash invalid", verify.stdout)

    def test_verify_rejects_historical_manifest_tamper(self):
        entries = self._create_three_ledger_runs()
        manifest_path = self.repo / entries[0]["manifest_path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = NOT_CHECKED
        self._write_json(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 manifest_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 manifest status mismatch", verify.stdout)

    def test_verify_rejects_ledger_path_substitution(self):
        entries = self._create_three_ledger_runs()
        entries[0]["manifest_path"] = entries[1]["manifest_path"]
        self._write_ledger_entries(entries)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 manifest_path mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 manifest run_id mismatch", verify.stdout)

    def test_verify_rejects_ledger_null_and_type_mismatch(self):
        entries = self._create_three_ledger_runs()
        entries[0]["manifest_hash"] = None
        entries[0]["run_id"] = []
        entries[0]["ledger_position"] = "1"
        self._write_ledger_entries(entries)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 run_id must be non-empty string", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 manifest_hash must be non-empty string", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 ledger_position must be integer", verify.stdout)

    def test_run_refuses_to_append_after_broken_latest_ledger_chain_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        entries = self._ledger_entries()
        entries[-1]["ledger_chain_hash"] = "not-a-sha"
        self._write_ledger_entries(entries)

        run = self._aeg("run", "fix typo in README", check=False)

        self.assertNotEqual(run.returncode, 0)
        self.assertIn("status: FAIL", run.stdout)
        self.assertIn("refusing to append after invalid ledger_chain_hash", run.stdout)
        self.assertEqual(len(self._ledger_entries()), 1)

        verify = self._aeg("verify", check=False)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: ledger line 1 ledger_chain_hash must be sha256 hex", verify.stdout)

    def test_verify_rejects_tampered_executor_capability_exposure_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["capability_network"] = True
        evidence["executor_capability_exposure_hash"] = expected_executor_capability_exposure_hash(evidence)
        evidence["executor_capability_exposure_metadata_hash"] = expected_executor_capability_exposure_metadata_hash(evidence)
        self._sync_executor_capability_exposure_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: capability_network must default false for current no-op executor", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: executor capability exposure fields must default false", verify.stdout)

    def test_structured_tool_capability_exposure_cannot_be_treated_as_safe(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["executor_capability_transport"] = EXECUTOR_CAPABILITY_TRANSPORT_STRUCTURED_TOOL_CALL
        evidence["capability_write_repo"] = True
        evidence["capability_shell"] = False
        evidence["executor_capability_exposure_hash"] = expected_executor_capability_exposure_hash(evidence)
        evidence["executor_capability_exposure_metadata_hash"] = expected_executor_capability_exposure_metadata_hash(evidence)
        self._sync_executor_capability_exposure_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: STRUCTURED_TOOL_CALL != SAFE_CAPABILITY", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: current no-op executor must not expose structured tool transport", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: capability_write_repo must default false for current no-op executor", verify.stdout)

    def test_executor_reported_capability_exposure_cannot_become_judgment_basis(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["executor_reported_capability_exposure"] = {
            "capabilities": ["network"],
            "tools": ["http_request"],
            "reported_capability_count": 1,
            "reported_tool_count": 1,
            "trust_boundary": REPORTED_ONLY,
            "judgment_basis": True,
        }
        evidence["executor_capability_exposure_metadata_hash"] = expected_executor_capability_exposure_metadata_hash(evidence)
        self._sync_executor_capability_exposure_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: executor_reported_capability_exposure cannot become judgment basis", verify.stdout)

    def test_verify_rejects_tampered_evidence_store_isolated_claim_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["evidence_store_is_executor_isolated"] = True
        evidence["evidence_store_trust_metadata_hash"] = expected_evidence_store_trust_metadata_hash(evidence)
        self._sync_evidence_store_trust_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: AEG_FOLDER_LOCAL_STATE != EXECUTOR_ISOLATED_EVIDENCE_STORE", verify.stdout)

    def test_verify_rejects_tampered_executor_can_write_evidence_store_false_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["executor_can_write_evidence_store"] = False
        evidence["evidence_store_trust_metadata_hash"] = expected_evidence_store_trust_metadata_hash(evidence)
        self._sync_evidence_store_trust_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn(
            "INVALID_EVIDENCE: executor_can_write_evidence_store must remain NOT_CHECKED_SAME_USER_AUTHORITY",
            verify.stdout,
        )

    def test_verify_rejects_evidence_store_clean_claim_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["evidence_store_integrity_status"] = EVIDENCE_STORE_CLEAN
        evidence["evidence_store_trust_metadata_hash"] = expected_evidence_store_trust_metadata_hash(evidence)
        self._sync_evidence_store_trust_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: evidence_store_integrity_status must remain NOT_CHECKED", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: evidence_store_is_executor_isolated=false cannot claim EVIDENCE_STORE_CLEAN", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: EVIDENCE_BINDING != EVIDENCE_STORE_TAMPER_PROOF", verify.stdout)

    def test_verify_rejects_tampered_tool_authority_flags_even_when_rebound(self):
        self._aeg("init")
        authority_fields = (
            "raw_shell_tool_authority_granted",
            "network_tool_authority_granted",
            "provider_tool_authority_granted",
            "file_mutation_tool_authority_granted",
        )
        for field in authority_fields:
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = True
                evidence["tool_authority_grant_hash"] = expected_tool_authority_grant_hash(evidence)
                evidence["tool_surface_metadata_hash"] = expected_tool_surface_metadata_hash(evidence)
                self._sync_tool_surface_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {field} must be false in tool surface scaffold v0", verify.stdout)
                self.assertIn(
                    f"INVALID_EVIDENCE: authority_granted=true without implemented tool surface proof/source/trust boundary: {field}",
                    verify.stdout,
                )
                self.assertIn("INVALID_EVIDENCE: tool authority flags must default false", verify.stdout)

    def test_verify_rejects_tampered_tool_authority_grant_hash_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["tool_authority_grant_hash"] = "0" * 64
        self._sync_tool_surface_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: tool_authority_grant_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: tool_surface_metadata_hash mismatch", verify.stdout)

    def test_tool_surface_status_cannot_claim_clean_even_when_rebound(self):
        self._aeg("init")
        clean_statuses = (TOOL_SURFACE_CLEAN, ACTION_BOUNDARY_CLEAN, CAPABILITY_BOUNDARY_CLEAN)
        for status in clean_statuses:
            with self.subTest(status=status):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence["tool_surface_status"] = status
                evidence["tool_surface_metadata_hash"] = expected_tool_surface_metadata_hash(evidence)
                self._sync_tool_surface_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn("INVALID_EVIDENCE: tool_surface_status cannot claim CLEAN before tool surface proof", verify.stdout)
                self.assertIn(
                    "INVALID_EVIDENCE: tool_surface_status must remain TOOL_SURFACE_SCAFFOLD_ONLY",
                    verify.stdout,
                )
                self.assertIn("INVALID_EVIDENCE: tool surface not implemented cannot be CLEAN", verify.stdout)

    def test_executor_reported_tool_usage_cannot_become_judgment_basis(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["executor_reported_tool_usage"] = {
            "tools": ["raw_shell", "network"],
            "reported_tool_count": 2,
            "trust_boundary": REPORTED_ONLY,
            "judgment_basis": True,
        }
        evidence["tool_surface_metadata_hash"] = expected_tool_surface_metadata_hash(evidence)
        self._sync_tool_surface_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: executor_reported_tool_usage cannot become judgment basis", verify.stdout)

    def test_verify_rejects_missing_tool_surface_fields(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["tool_surface_version"]
        del evidence["bound_tool_surface_metadata_hash"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: tool_surface_version", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: missing evidence binding v1 field: bound_tool_surface_metadata_hash",
            verify.stdout,
        )

    def test_verify_rejects_tampered_tool_surface_manifest_metadata_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["network_tool_authority_granted"] = True
        manifest["tool_authority_grant_hash"] = expected_tool_authority_grant_hash(manifest)
        manifest["tool_surface_metadata_hash"] = expected_tool_surface_metadata_hash(manifest)
        manifest["tool_surface_authority_metadata_hash"] = sha256_json(
            {field: manifest[field] for field in self._tool_surface_fields()}
        )
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest network_tool_authority_granted mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: tool surface scaffold metadata fields mismatch", verify.stdout)

    def test_verify_rejects_tampered_capability_authority_flags_even_when_rebound(self):
        self._aeg("init")
        authority_fields = (
            "raw_shell_authority_granted",
            "network_authority_granted",
            "provider_authority_granted",
        )
        for field in authority_fields:
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = True
                evidence["capability_matrix_hash"] = expected_capability_matrix_hash(evidence)
                evidence["capability_isolation_proof_hash"] = expected_capability_isolation_proof_hash(evidence)
                self._sync_action_boundary_manifest(evidence, manifest)
                self._sync_capability_isolation_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn(f"INVALID_EVIDENCE: {field} must be false in capability isolation scaffold v0", verify.stdout)
                self.assertIn(
                    f"INVALID_EVIDENCE: authority_granted=true without implemented capability isolation proof: {field}",
                    verify.stdout,
                )
                self.assertIn("INVALID_EVIDENCE: capability authority flags must default false", verify.stdout)

    def test_verify_rejects_tampered_capability_matrix_hash_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["capability_matrix_hash"] = "0" * 64
        self._sync_capability_isolation_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: capability_matrix_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: capability_isolation_proof_hash mismatch", verify.stdout)

    def test_capability_boundary_status_cannot_claim_clean_even_when_rebound(self):
        self._aeg("init")
        clean_statuses = (CAPABILITY_BOUNDARY_CLEAN, ACTION_BOUNDARY_CLEAN)
        for status in clean_statuses:
            with self.subTest(status=status):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence["capability_boundary_status"] = status
                evidence["capability_isolation_proof_hash"] = expected_capability_isolation_proof_hash(evidence)
                self._sync_capability_isolation_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn("INVALID_EVIDENCE: capability_boundary_status cannot claim CLEAN before isolation proof", verify.stdout)
                self.assertIn(
                    "INVALID_EVIDENCE: capability_boundary_status must remain CAPABILITY_BOUNDARY_NOT_CHECKED",
                    verify.stdout,
                )
                self.assertIn("INVALID_EVIDENCE: capability not implemented cannot be CLEAN", verify.stdout)

    def test_executor_reported_capabilities_cannot_become_judgment_basis(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["executor_reported_capabilities"] = {
            "capabilities": ["raw_shell", "network"],
            "reported_capability_count": 2,
            "trust_boundary": REPORTED_ONLY,
            "judgment_basis": True,
        }
        self._sync_capability_isolation_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: executor_reported_capabilities cannot be judgment basis", verify.stdout)

    def test_verify_rejects_missing_capability_isolation_fields(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["capability_isolation_version"]
        del evidence["bound_capability_isolation_metadata_hash"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: capability_isolation_version", verify.stdout)
        self.assertIn(
            "INVALID_EVIDENCE: missing evidence binding v1 field: bound_capability_isolation_metadata_hash",
            verify.stdout,
        )

    def test_verify_rejects_tampered_capability_manifest_metadata_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["process_execution_authority_granted"] = True
        manifest["capability_matrix_hash"] = expected_capability_matrix_hash(manifest)
        manifest["capability_isolation_proof_hash"] = expected_capability_isolation_proof_hash(manifest)
        manifest["capability_isolation_metadata_hash"] = sha256_json(
            {field: manifest[field] for field in self._capability_isolation_fields()}
        )
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest process_execution_authority_granted mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: capability isolation scaffold metadata fields mismatch", verify.stdout)

    def test_verify_rejects_tampered_action_count_and_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["action_count"] = 1
        evidence["computed_action_log_hash"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: action_count must equal intercepted_actions length", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: action_count must equal expected_action_count", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: computed_action_log_hash mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest action_count mismatch", verify.stdout)

    def test_verify_rejects_tampered_action_manifest_metadata_even_when_rebound(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["action_count"] = 1
        manifest["action_boundary_metadata_hash"] = sha256_json(
            {field: manifest[field] for field in self._action_boundary_fields()}
        )
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest action_count mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: action boundary scaffold metadata fields mismatch", verify.stdout)

    def test_fake_push_deploy_release_publish_cannot_be_action_boundary_clean(self):
        self._aeg("init")
        high_action_kinds = ("push", "deploy", "release", "publish")
        for kind in high_action_kinds:
            with self.subTest(kind=kind):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence["intercepted_actions"] = [{"action_type": kind, "risk": HIGH}]
                evidence["action_count"] = 1
                evidence["expected_action_count"] = 1
                evidence["action_risk"] = HIGH
                evidence["action_boundary_status"] = ACTION_BOUNDARY_CLEAN
                evidence["computed_action_log_hash"] = expected_action_log_hash(evidence)
                self._sync_action_boundary_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self.assertNotEqual(verify.returncode, 0)
                self._assert_verify_failed(verify)
                self.assertIn("INVALID_EVIDENCE: HIGH action cannot be ACTION_BOUNDARY_CLEAN", verify.stdout)
                self.assertIn("INVALID_EVIDENCE: ACTION_BOUNDARY_CLEAN is unavailable", verify.stdout)
                self.assertIn("INVALID_EVIDENCE: action boundary status must not claim ACTION_BOUNDARY_CLEAN", verify.stdout)

    def test_command_enumeration_only_cannot_produce_action_boundary_clean(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["command_enumeration_only"] = True
        evidence["action_boundary_status"] = ACTION_BOUNDARY_CLEAN
        self._sync_action_boundary_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: command_enumeration_only cannot produce ACTION_BOUNDARY_CLEAN", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ACTION_BOUNDARY_CLEAN is unavailable", verify.stdout)

    def test_no_matched_dangerous_command_cannot_produce_action_boundary_clean(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["no_matched_dangerous_command"] = True
        evidence["action_boundary_status"] = ACTION_BOUNDARY_CLEAN
        self._sync_action_boundary_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: ACTION_BOUNDARY_CLEAN is unavailable", verify.stdout)

    def test_executor_reported_actions_cannot_become_judgment_basis(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["executor_reported_actions"] = {
            "actions": [{"action_type": "deploy", "risk": HIGH}],
            "reported_action_count": 1,
            "trust_boundary": REPORTED_ONLY,
            "judgment_basis": True,
        }
        self._sync_action_boundary_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: executor_reported_actions cannot be judgment basis", verify.stdout)

    def test_protected_working_tree_change_escalates_runtime_risk(self):
        self._aeg("init")
        (self.repo / "src" / "classify" / "rules.py").write_text("VALUE = 2\n", encoding="utf-8")

        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], HIGH)
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["changed_files"], ["src/classify/rules.py"])
        self.assertEqual(evidence["changed_files_source"], GIT_WORKING_TREE)
        self.assertEqual(evidence["protected_paths_touched"], ["src/classify/rules.py"])
        self.assertTrue(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NEEDS_USER_GATE", verify.stdout)
        self.assertIn("impact_risk replay matched: HIGH", verify.stdout)
        self.assertIn("risk_escalation_applied replay matched: True", verify.stdout)

    def test_non_protected_working_tree_change_sets_medium_runtime_impact(self):
        self._aeg("init")
        (self.repo / "src" / "agents" / "executor.py").write_text("VALUE = 2\n", encoding="utf-8")

        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: NOT_CHECKED", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], MEDIUM)
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["changed_files"], ["src/agents/executor.py"])
        self.assertEqual(evidence["changed_files_source"], GIT_WORKING_TREE)
        self.assertEqual(evidence["protected_paths_touched"], [])
        self.assertTrue(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], NOT_CHECKED)

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NOT_CHECKED", verify.stdout)
        self.assertIn("impact_risk replay matched: MEDIUM", verify.stdout)
        self.assertIn("law status replay matched: NOT_CHECKED", verify.stdout)

    def test_staged_changed_file_uses_staged_source(self):
        self._aeg("init")
        (self.repo / "README.md").write_text("# Test\n\nTypo fix\n", encoding="utf-8")
        self._git("add", "README.md")

        self._aeg("run", "fix typo in README")
        evidence = self._latest_evidence()
        self.assertEqual(evidence["changed_files"], ["README.md"])
        self.assertEqual(evidence["changed_files_source"], GIT_STAGED)
        self.assertEqual(evidence["impact_risk"], LOW)
        self.assertEqual(evidence["risk_level"], LOW)

    def test_changed_files_source_failure_is_not_checked(self):
        self._aeg("init")
        with patch(
            "src.evidence.mutation_boundary.git.changed_file_snapshot",
            side_effect=git_state.GitError("status unavailable"),
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README")

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["changed_files"], [])
        self.assertEqual(evidence["changed_files_source"], NOT_CHECKED_SOURCE)
        self.assertEqual(evidence["impact_risk"], NOT_CHECKED)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertEqual(evidence["status"], NOT_CHECKED)

    def test_dirty_pre_tree_noop_records_preexisting_without_executor_mutation(self):
        self._aeg("init")
        (self.repo / "README.md").write_text("# Test\n\nTypo fix\n", encoding="utf-8")

        self._aeg("run", "fix typo in README")

        evidence = self._latest_evidence()
        self.assertEqual(evidence["changed_files"], ["README.md"])
        self.assertEqual(evidence["pre_existing_dirty_tree"][0]["path"], "README.md")
        self.assertEqual(evidence["pre_run_changed_files"], evidence["post_run_changed_files"])
        self.assertEqual(evidence["computed_mutation_delta"], [])
        self.assertEqual(evidence["executor_created_mutation"], [])
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_DIRTY_PREEXISTING)

    def test_post_run_new_tracked_diff_detects_computed_mutation_delta(self):
        self._aeg("init")

        def mutating_executor(task_text, classification, law_result):
            (self.repo / "src" / "agents" / "executor.py").write_text("VALUE = 2\n", encoding="utf-8")
            return noop_execute_contract(task_text, classification, law_result)

        with patch("src.cli.main.execute_contract", side_effect=mutating_executor):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README")

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_DELTA_DETECTED)
        self.assertEqual(evidence["computed_mutation_delta"][0]["path"], "src/agents/executor.py")
        self.assertEqual(evidence["executor_created_mutation"], evidence["computed_mutation_delta"])
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["status"], NOT_CHECKED)

    def test_post_run_protected_path_mutation_escalates_low_task(self):
        self._aeg("init")

        def mutating_executor(task_text, classification, law_result):
            (self.repo / "src" / "classify" / "rules.py").write_text("VALUE = 2\n", encoding="utf-8")
            return noop_execute_contract(task_text, classification, law_result)

        with patch("src.cli.main.execute_contract", side_effect=mutating_executor):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README")

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_DELTA_DETECTED)
        self.assertTrue(evidence["protected_path_mutation_detected"])
        self.assertEqual(evidence["protected_paths_touched"], ["src/classify/rules.py"])

    def test_executor_reported_mutation_is_reported_only_not_judgment_basis(self):
        self._aeg("init")

        def reporting_executor(task_text, classification, law_result):
            result = noop_execute_contract(task_text, classification, law_result)
            result["changed_files"] = ["src/classify/rules.py"]
            result["mutation_delta"] = [{"path": "src/classify/rules.py"}]
            return result

        with patch("src.cli.main.execute_contract", side_effect=reporting_executor):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README")

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["executor_reported_changed_files"], ["src/classify/rules.py"])
        self.assertEqual(evidence["executor_reported_changed_files_source"], REPORTED_ONLY)
        self.assertEqual(evidence["executor_reported_mutation_delta"], [{"path": "src/classify/rules.py"}])
        self.assertEqual(evidence["executor_reported_mutation_delta_source"], REPORTED_ONLY)
        self.assertEqual(evidence["computed_mutation_delta"], [])
        self.assertEqual(evidence["mutation_boundary_status"], MUTATION_BOUNDARY_CLEAN)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertEqual(evidence["status"], CLEAN_CORE)

    def test_aeg_state_is_ignored_and_no_tracked_mutation(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence = self._latest_evidence()
        self.assertEqual(evidence["computed_mutation_delta"], [])
        for field in ("pre_run_changed_files", "post_run_changed_files"):
            self.assertFalse(any(entry["path"].startswith(".aeg/") for entry in evidence[field]))
        tracked_status = self._git("status", "--porcelain=v1").stdout.strip()
        self.assertEqual(tracked_status, "")
        tracked_aeg = self._git("ls-files", ".aeg").stdout.strip()
        self.assertEqual(tracked_aeg, "")

    def test_verify_detects_mismatched_saved_risk_level_for_protected_path(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["changed_files"] = [".github/workflows/ci.yml"]
        evidence["changed_files_source"] = "git_working_tree"
        evidence["impact_risk"] = LOW
        evidence["risk_level"] = LOW
        evidence["protected_paths_touched"] = []
        evidence["risk_escalation_applied"] = False
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: changed_files mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: bound_changed_files_hash mismatch", verify.stdout)

    def test_verify_rejects_saved_risk_level_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["risk_level"] = MEDIUM
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: risk_level mismatch: evidence=MEDIUM replay=LOW", verify.stdout)

    def test_verify_rejects_missing_completion_contract(self):
        self._aeg("init")
        self._aeg("run", "do the thing")
        evidence, path = self._latest_evidence_with_path()
        del evidence["checks"]["executor"]["completion_contract"]
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: missing completion_contract_v0", verify.stdout)
        self.assertNotIn("status: CLEAN_CORE", verify.stdout)

    def test_verify_rejects_not_checked_promoted_to_clean_core(self):
        self._aeg("init")
        self._aeg("run", "do the thing")
        evidence, path = self._latest_evidence_with_path()
        evidence["status"] = CLEAN_CORE
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: law status mismatch: evidence=CLEAN_CORE replay=NOT_CHECKED", verify.stdout)

    def test_verify_rejects_missing_changed_files_source_as_not_checked(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["changed_files_source"]
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: changed_files_source", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: missing evidence binding field: changed_files_source", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest changed_files_source mismatch", verify.stdout)

    def test_verify_rejects_missing_manifest(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        _, manifest_path = self._latest_manifest_with_path()
        manifest_path.unlink()

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest missing", verify.stdout)

    def test_verify_rejects_manifest_hash_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["status"] = NOT_CHECKED
        self._write_json(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest hash mismatch", verify.stdout)

    def test_verify_rejects_run_id_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["run_id"] = "tampered-run-id"
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest run_id mismatch", verify.stdout)

    def test_verify_rejects_changed_files_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["changed_files"] = ["README.md"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: changed_files mismatch", verify.stdout)

    def test_verify_rejects_changed_files_hash_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["bound_changed_files_hash"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: bound_changed_files_hash mismatch", verify.stdout)

    def test_verify_rejects_evidence_path_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["evidence_path"] = ".aeg/runs/other/evidence.json"
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest evidence_path mismatch", verify.stdout)

    def test_verify_rejects_run_path_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["run_path"] = ".aeg/runs/other/run.json"
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest run_path mismatch", verify.stdout)

    def test_verify_rejects_missing_binding_fields(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["binding_version"]
        del evidence["bound_head_sha"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: missing evidence binding v1 field: binding_version", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: missing evidence binding v1 field: bound_head_sha", verify.stdout)

    def test_verify_rejects_non_bound_clean_core(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["binding_status"] = NOT_CHECKED
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: binding_status must be BOUND for judgment basis", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: CLEAN_CORE requires binding_status BOUND", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

    def test_verify_rejects_reported_only_as_judgment_basis(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["reported_only"] = True
        evidence["judgment_basis"] = "reported_only"
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: reported_only evidence is not judgment basis", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: reported_only cannot be judgment basis", verify.stdout)

    def test_verify_rejects_untrusted_snapshot_collector(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["snapshot_collector"] = "executor_controlled_collector"
        manifest["snapshot_collector"] = evidence["snapshot_collector"]
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("invalid snapshot_collector", verify.stdout)
        self.assertIn("mutation boundary snapshot trust not satisfied", verify.stdout)

    def test_verify_recomputes_mutation_delta_from_snapshots_not_executor_report(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        fake_delta = [{"path": "src/classify/rules.py", "transition": "executor_reported_only"}]
        evidence["executor_reported_mutation_delta"] = fake_delta
        evidence["computed_mutation_delta"] = fake_delta
        evidence["bound_computed_mutation_delta_hash"] = sha256_json(fake_delta)
        manifest["computed_mutation_delta"] = fake_delta
        manifest["computed_mutation_delta_hash"] = sha256_json(fake_delta)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("computed_mutation_delta mismatch", verify.stdout)

    def _assert_verify_consistent(self, verify):
        self.assertIn("status: REPLAY_CONSISTENT", verify.stdout)
        self.assertIn("verification_scope: deterministic_replay_and_binding_validation", verify.stdout)
        self.assertIn("independent_oracle: false", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

    def _assert_verify_failed(self, verify):
        self.assertIn("status: REPLAY_FAILED", verify.stdout)
        self.assertIn("verification_scope: deterministic_replay_and_binding_validation", verify.stdout)
        self.assertIn("independent_oracle: false", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

    def _aeg(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
            cwd=self.repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def _latest_evidence(self):
        evidence, _ = self._latest_evidence_with_path()
        return evidence

    def _latest_evidence_with_path(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        entry = json.loads(line)
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "evidence.json"
        return json.loads(path.read_text(encoding="utf-8")), path

    def _latest_manifest_with_path(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        entry = json.loads(line)
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8")), path

    def _latest_ledger_entry(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        return json.loads(line)

    def _ledger_entries(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line]

    def _write_ledger_entries(self, entries):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        lines = [json.dumps(entry, sort_keys=True) for entry in entries]
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _create_three_ledger_runs(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        self._aeg("run", "fix typo in README")
        self._aeg("run", "fix typo in README")
        return self._ledger_entries()

    def _replace_latest_ledger_entry(self, entry):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        lines = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line]
        lines[-1] = json.dumps(entry, sort_keys=True)
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_manifest_and_rebind_hash(self, manifest_path, manifest):
        self._write_json(manifest_path, manifest)
        evidence, evidence_path = self._latest_evidence_with_path()
        evidence["bound_manifest_hash"] = manifest_hash(manifest)
        self._write_json(evidence_path, evidence)

    def _write_evidence_and_manifest_with_bound_hash(self, evidence_path, evidence, manifest_path, manifest):
        self._write_json(manifest_path, manifest)
        evidence["bound_manifest_hash"] = manifest_hash(manifest)
        self._write_json(evidence_path, evidence)

    def _sync_action_boundary_manifest(self, evidence, manifest):
        for field in self._action_boundary_fields():
            manifest[field] = evidence[field]
        manifest["action_boundary_metadata_hash"] = sha256_json(
            {field: manifest[field] for field in self._action_boundary_fields()}
        )
        evidence["bound_action_boundary_metadata_hash"] = manifest["action_boundary_metadata_hash"]

    def _sync_capability_isolation_manifest(self, evidence, manifest):
        for field in self._capability_isolation_fields():
            manifest[field] = evidence[field]
        manifest["capability_isolation_metadata_hash"] = sha256_json(
            {field: manifest[field] for field in self._capability_isolation_fields()}
        )
        evidence["bound_capability_isolation_metadata_hash"] = manifest["capability_isolation_metadata_hash"]

    def _sync_tool_surface_manifest(self, evidence, manifest):
        for field in self._tool_surface_fields():
            manifest[field] = evidence[field]
        manifest["tool_surface_authority_metadata_hash"] = sha256_json(
            {field: manifest[field] for field in self._tool_surface_fields()}
        )
        evidence["bound_tool_surface_metadata_hash"] = manifest["tool_surface_authority_metadata_hash"]

    def _sync_executor_capability_exposure_manifest(self, evidence, manifest):
        for field in self._executor_capability_exposure_fields():
            manifest[field] = evidence[field]
        manifest["executor_capability_exposure_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._executor_capability_exposure_fields()}
        )
        evidence["bound_executor_capability_exposure_metadata_hash"] = manifest[
            "executor_capability_exposure_manifest_hash"
        ]

    def _sync_evidence_store_trust_manifest(self, evidence, manifest):
        for field in self._evidence_store_trust_fields():
            manifest[field] = evidence[field]
        manifest["evidence_store_trust_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._evidence_store_trust_fields()}
        )
        evidence["bound_evidence_store_trust_metadata_hash"] = manifest["evidence_store_trust_manifest_hash"]

    def _sync_aeg_state_write_denial_manifest(self, evidence, manifest):
        for field in self._aeg_state_write_denial_fields():
            manifest[field] = evidence[field]
        manifest["aeg_state_write_denial_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._aeg_state_write_denial_fields()}
        )
        evidence["bound_aeg_state_write_denial_metadata_hash"] = manifest["aeg_state_write_denial_manifest_hash"]

    def _sync_mediated_write_boundary_manifest(self, evidence, manifest):
        for field in self._mediated_write_boundary_fields():
            manifest[field] = evidence[field]
        manifest["mediated_write_boundary_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._mediated_write_boundary_fields()}
        )
        evidence["bound_mediated_write_boundary_metadata_hash"] = manifest[
            "mediated_write_boundary_manifest_hash"
        ]

    def _sync_write_bypass_harness_manifest(self, evidence, manifest):
        for field in self._write_bypass_harness_fields():
            manifest[field] = evidence[field]
        manifest["write_bypass_harness_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._write_bypass_harness_fields()}
        )
        evidence["bound_write_bypass_harness_metadata_hash"] = manifest[
            "write_bypass_harness_manifest_hash"
        ]

    def _sync_pre_live_executor_gate_manifest(self, evidence, manifest):
        for field in self._pre_live_executor_gate_fields():
            manifest[field] = evidence[field]
        manifest["pre_live_executor_gate_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._pre_live_executor_gate_fields()}
        )
        evidence["bound_pre_live_executor_gate_metadata_hash"] = manifest["pre_live_executor_gate_manifest_hash"]

    def _sync_ledger_integrity_manifest(self, evidence, manifest):
        for field in self._ledger_integrity_fields():
            manifest[field] = evidence[field]
        manifest["ledger_integrity_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in self._ledger_integrity_fields()}
        )
        evidence["bound_ledger_integrity_metadata_hash"] = manifest["ledger_integrity_manifest_hash"]

    def _write_json(self, path, payload):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _citizen_one_fields(self):
        return (
            "citizen_one_requested",
            "citizen_one_mode",
            "citizen_one_status",
            "citizen_one_provider_status",
            "citizen_one_output_present",
            "citizen_one_output_trust_boundary",
            "citizen_one_reported_only",
            "citizen_one_hold_reason",
            "provider_config_source",
            "provider_network_used",
            "provider_secret_observed",
            "model_output_hash_candidate",
        )

    def _provider_adapter_fields(self):
        return PROVIDER_ADAPTER_DISABLED_FIELDS

    def _provider_runtime_state_fields(self):
        return PROVIDER_RUNTIME_STATE_FIELDS

    def _provider_selection_fields(self):
        return PROVIDER_SELECTION_METADATA_FIELDS

    def _provider_secret_env_fields(self):
        return PROVIDER_SECRET_ENV_METADATA_FIELDS

    def _provider_network_guard_fields(self):
        return PROVIDER_NETWORK_GUARD_METADATA_FIELDS

    def _provider_request_fields(self):
        return PROVIDER_REQUEST_METADATA_FIELDS

    def _provider_response_error_fields(self):
        return PROVIDER_RESPONSE_ERROR_METADATA_FIELDS

    def _provider_runtime_metadata_fields(self):
        return (
            *PROVIDER_RUNTIME_STATE_FIELDS,
            *PROVIDER_SELECTION_METADATA_FIELDS,
            *PROVIDER_SECRET_ENV_METADATA_FIELDS,
            *PROVIDER_NETWORK_GUARD_METADATA_FIELDS,
            *PROVIDER_REQUEST_METADATA_FIELDS,
            *PROVIDER_RESPONSE_ERROR_METADATA_FIELDS,
        )

    def _prompt_redaction_fields(self):
        return PROMPT_REDACTION_METADATA_FIELDS

    def _response_redaction_fields(self):
        return RESPONSE_REDACTION_METADATA_FIELDS

    def _action_boundary_fields(self):
        return ACTION_BOUNDARY_FIELDS

    def _capability_isolation_fields(self):
        return CAPABILITY_ISOLATION_FIELDS

    def _tool_surface_fields(self):
        return TOOL_SURFACE_FIELDS

    def _executor_capability_exposure_fields(self):
        return EXECUTOR_CAPABILITY_EXPOSURE_FIELDS

    def _evidence_store_trust_fields(self):
        return EVIDENCE_STORE_TRUST_FIELDS

    def _aeg_state_write_denial_fields(self):
        return AEG_STATE_WRITE_DENIAL_FIELDS

    def _mediated_write_boundary_fields(self):
        return MEDIATED_WRITE_BOUNDARY_FIELDS

    def _write_bypass_harness_fields(self):
        return WRITE_BYPASS_HARNESS_FIELDS

    def _pre_live_executor_gate_fields(self):
        return PRE_LIVE_EXECUTOR_GATE_FIELDS

    def _ledger_integrity_fields(self):
        return LEDGER_INTEGRITY_FIELDS

    def _proposal_fields(self):
        return (
            "proposal_id",
            "proposal_version",
            "proposal_kind",
            "proposal_summary",
            "proposal_steps",
            "proposal_risk_notes",
            "proposal_requires_user_gate",
            "proposal_trust_boundary",
            "proposal_reported_only",
            "proposal_source",
            "proposal_output_hash_candidate",
            "proposal_redaction_status",
            "proposal_status",
            "proposal_present",
            "proposal_hold_reason",
        )

    def _assert_action_boundary_scaffold_contract(self, evidence):
        self.assertEqual(evidence["action_boundary_version"], ACTION_BOUNDARY_SCAFFOLD_V0)
        self.assertFalse(evidence["action_interception_enabled"])
        self.assertEqual(evidence["action_boundary_status"], ACTION_BOUNDARY_NOT_CHECKED)
        self.assertNotEqual(evidence["action_boundary_status"], ACTION_BOUNDARY_CLEAN)
        self.assertEqual(evidence["action_log_source"], ACTION_LOG_SOURCE_NONE)
        self.assertEqual(
            evidence["action_log_source_trust_boundary"],
            ACTION_LOG_SOURCE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
        )
        self.assertEqual(evidence["intercepted_actions"], [])
        self.assertEqual(evidence["action_count"], 0)
        self.assertEqual(evidence["expected_action_count"], 0)
        self.assertEqual(evidence["action_risk"], NOT_CHECKED)
        self.assertFalse(evidence["command_enumeration_only"])
        self.assertFalse(evidence["no_matched_dangerous_command"])
        for field in ACTION_AUTHORITY_FIELDS:
            self.assertFalse(evidence[field])
        self.assertEqual(evidence["computed_action_log_hash"], expected_action_log_hash(evidence))
        self.assertEqual(
            evidence["executor_reported_actions"],
            {
                "actions": [],
                "reported_action_count": 0,
                "trust_boundary": REPORTED_ONLY,
                "judgment_basis": False,
            },
        )
        self.assertTrue(evidence["checks"]["action_boundary_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["action_boundary_clean_claim_forbidden"])
        self.assertTrue(evidence["checks"]["mutation_boundary_clean_does_not_imply_action_boundary_clean"])
        self.assertTrue(evidence["checks"]["git_diff_clean_does_not_imply_action_clean"])
        self.assertTrue(evidence["checks"]["no_matched_dangerous_command_is_not_action_boundary_clean"])
        self.assertTrue(evidence["checks"]["executor_reported_actions_is_reported_only"])
        self.assertTrue(evidence["checks"]["reported_only_is_not_judgment_basis"])
        self.assertTrue(evidence["checks"]["command_enumeration_only_grants_no_authority"])

    def _assert_capability_isolation_scaffold_contract(self, evidence):
        self.assertEqual(evidence["capability_isolation_version"], CAPABILITY_ISOLATION_SCAFFOLD_V0)
        self.assertFalse(evidence["capability_isolation_enabled"])
        self.assertEqual(evidence["capability_isolation_mode"], CAPABILITY_ISOLATION_MODE_NOT_IMPLEMENTED)
        self.assertEqual(evidence["capability_boundary_status"], CAPABILITY_BOUNDARY_NOT_CHECKED)
        self.assertNotEqual(evidence["capability_boundary_status"], CAPABILITY_BOUNDARY_CLEAN)
        self.assertEqual(evidence["capability_boundary_source"], CAPABILITY_BOUNDARY_SOURCE_NONE)
        self.assertEqual(
            evidence["capability_boundary_trust_boundary"],
            CAPABILITY_BOUNDARY_TRUST_BOUNDARY_NOT_IMPLEMENTED,
        )
        for field in CAPABILITY_AUTHORITY_FIELDS:
            self.assertFalse(evidence[field])
        self.assertEqual(evidence["capability_matrix_hash"], expected_capability_matrix_hash(evidence))
        self.assertEqual(
            evidence["capability_isolation_proof_hash"],
            expected_capability_isolation_proof_hash(evidence),
        )
        self.assertEqual(
            evidence["executor_reported_capabilities"],
            {
                "capabilities": [],
                "reported_capability_count": 0,
                "trust_boundary": REPORTED_ONLY,
                "judgment_basis": False,
            },
        )
        self.assertTrue(evidence["checks"]["capability_isolation_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["capability_boundary_clean_claim_forbidden"])
        self.assertTrue(evidence["checks"]["capability_not_implemented_is_not_clean"])
        self.assertTrue(evidence["checks"]["capability_not_observed_is_not_clean"])
        self.assertTrue(evidence["checks"]["missing_isolation_proof_is_not_clean"])
        self.assertTrue(evidence["checks"]["unavailable_capability_proof_is_not_checked"])
        self.assertTrue(evidence["checks"]["executor_reported_capabilities_is_reported_only"])
        self.assertTrue(evidence["checks"]["capability_reported_only_is_not_judgment_basis"])
        self.assertTrue(evidence["checks"]["no_live_executor_authority_before_capability_isolation"])
        self.assertTrue(evidence["checks"]["capability_isolation_manifest_binding_required"])

    def _assert_tool_surface_scaffold_contract(self, evidence):
        self.assertEqual(evidence["tool_surface_version"], TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0)
        self.assertFalse(evidence["tool_surface_enabled"])
        self.assertEqual(evidence["tool_surface_status"], TOOL_SURFACE_SCAFFOLD_ONLY)
        self.assertNotEqual(evidence["tool_surface_status"], TOOL_SURFACE_CLEAN)
        self.assertEqual(evidence["tool_surface_source"], TOOL_SURFACE_SOURCE_NONE)
        self.assertEqual(
            evidence["tool_surface_trust_boundary"],
            TOOL_SURFACE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
        )
        self.assertEqual(evidence["requested_tool_capabilities"], [])
        self.assertEqual(evidence["granted_tool_capabilities"], [])
        self.assertEqual(evidence["denied_tool_capabilities"], [])
        self.assertEqual(evidence["tool_authority_grant_count"], 0)
        self.assertEqual(evidence["expected_tool_authority_grant_count"], 0)
        for field in TOOL_AUTHORITY_GRANT_FIELDS:
            self.assertFalse(evidence[field])
        self.assertEqual(evidence["tool_authority_grant_hash"], expected_tool_authority_grant_hash(evidence))
        self.assertEqual(evidence["tool_surface_metadata_hash"], expected_tool_surface_metadata_hash(evidence))
        self.assertEqual(
            evidence["executor_reported_tool_usage"],
            {
                "tools": [],
                "reported_tool_count": 0,
                "trust_boundary": REPORTED_ONLY,
                "judgment_basis": False,
            },
        )
        self.assertTrue(evidence["checks"]["tool_surface_authority_grant_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["tool_surface_clean_claim_forbidden"])
        self.assertTrue(evidence["checks"]["tool_surface_not_implemented_is_not_clean"])
        self.assertTrue(evidence["checks"]["no_requested_tool_is_not_clean"])
        self.assertTrue(evidence["checks"]["no_granted_tool_is_not_external_proof"])
        self.assertTrue(evidence["checks"]["tool_authority_grant_count_expected_zero"])
        self.assertTrue(evidence["checks"]["tool_authority_flags_default_false"])
        self.assertTrue(evidence["checks"]["executor_reported_tool_usage_is_reported_only"])
        self.assertTrue(evidence["checks"]["tool_usage_reported_only_is_not_judgment_basis"])
        self.assertTrue(evidence["checks"]["command_denylist_alone_grants_no_tool_authority"])
        self.assertTrue(evidence["checks"]["no_live_executor_authority_before_tool_surface"])
        self.assertTrue(evidence["checks"]["tool_surface_manifest_binding_required"])

    def _assert_executor_capability_exposure_contract(self, evidence):
        self.assertEqual(evidence["executor_capability_exposure_version"], EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0)
        self.assertEqual(evidence["executor_capability_exposure_scope"], EXECUTOR_CAPABILITY_EXPOSURE_SCOPE_CURRENT_NOOP)
        self.assertEqual(
            evidence["executor_capability_exposure_source"],
            EXECUTOR_CAPABILITY_EXPOSURE_SOURCE_NOOP_CONTRACT,
        )
        self.assertEqual(
            evidence["executor_capability_exposure_trust_boundary"],
            EXECUTOR_CAPABILITY_EXPOSURE_TRUST_BOUNDARY_AEGIS_RUNTIME,
        )
        self.assertEqual(evidence["executor_capability_transport"], EXECUTOR_CAPABILITY_TRANSPORT_NONE)
        self.assertEqual(
            evidence["current_executor_capability_status"],
            NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION,
        )
        for field in EXECUTOR_CAPABILITY_BOOL_FIELDS:
            self.assertFalse(evidence[field])
        self.assertFalse(evidence["executor_capability_file_mutation"])
        self.assertFalse(evidence["executor_capability_provider_calls"])
        self.assertFalse(evidence["executor_capability_network_calls"])
        self.assertEqual(evidence["executor_capability_actions"], [])
        self.assertEqual(evidence["executor_capability_action_count"], 0)
        self.assertEqual(evidence["executor_capability_expected_action_count"], 0)
        self.assertEqual(
            evidence["executor_capability_exposure_hash"],
            expected_executor_capability_exposure_hash(evidence),
        )
        self.assertEqual(
            evidence["executor_capability_exposure_metadata_hash"],
            expected_executor_capability_exposure_metadata_hash(evidence),
        )
        self.assertEqual(
            evidence["executor_reported_capability_exposure"],
            {
                "capabilities": [],
                "tools": [],
                "reported_capability_count": 0,
                "reported_tool_count": 0,
                "trust_boundary": REPORTED_ONLY,
                "judgment_basis": False,
            },
        )
        self.assertTrue(evidence["checks"]["executor_capability_exposure_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["executor_capability_exposure_current_noop_only"])
        self.assertTrue(evidence["checks"]["executor_capability_fields_default_false"])
        self.assertTrue(evidence["checks"]["current_noop_executor_has_no_shell_network_provider_action"])
        self.assertTrue(evidence["checks"]["no_raw_shell_is_not_no_dangerous_capability"])
        self.assertTrue(evidence["checks"]["structured_tool_call_is_not_safe_capability"])
        self.assertTrue(evidence["checks"]["executor_capability_exposure_reported_only_is_not_judgment_basis"])
        self.assertTrue(evidence["checks"]["executor_capability_exposure_manifest_binding_required"])

    def _assert_evidence_store_trust_contract(self, evidence):
        self.assertEqual(
            evidence["evidence_store_trust_boundary"],
            EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED,
        )
        self.assertEqual(evidence["evidence_store_writer"], EVIDENCE_STORE_WRITER_AEGIS_RUNTIME)
        self.assertEqual(
            evidence["executor_can_write_evidence_store"],
            EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY,
        )
        self.assertFalse(evidence["evidence_store_is_executor_isolated"])
        self.assertEqual(evidence["evidence_store_write_source"], EVIDENCE_STORE_WRITE_SOURCE_FOLDER_LOCAL_STATE)
        self.assertEqual(evidence["evidence_store_integrity_status"], EVIDENCE_STORE_INTEGRITY_NOT_CHECKED)
        self.assertEqual(
            evidence["evidence_store_trust_metadata_hash"],
            expected_evidence_store_trust_metadata_hash(evidence),
        )
        self.assertTrue(evidence["checks"]["evidence_store_trust_boundary_metadata_required"])
        self.assertTrue(evidence["checks"]["aeg_folder_local_state_is_not_executor_isolated"])
        self.assertTrue(evidence["checks"]["evidence_binding_is_not_evidence_store_tamper_proof"])
        self.assertTrue(evidence["checks"]["evidence_store_integrity_not_checked_is_not_clean"])
        self.assertTrue(evidence["checks"]["executor_can_write_evidence_store_not_checked_is_not_clean"])
        self.assertTrue(evidence["checks"]["evidence_store_trust_manifest_binding_required"])

    def _assert_aeg_state_write_denial_scaffold_contract(self, evidence):
        self.assertEqual(evidence["aeg_state_write_denial_version"], AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0)
        self.assertEqual(evidence["aeg_state_write_denial_mode"], AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD)
        self.assertEqual(evidence["aeg_state_write_denial_status"], AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY)
        self.assertNotIn(evidence["aeg_state_write_denial_status"], ("CLEAN", "PASS", "ENFORCED"))
        self.assertFalse(evidence["capability_write_aeg_state_requested"])
        self.assertFalse(evidence["capability_write_aeg_state_granted"])
        self.assertTrue(evidence["capability_write_aeg_state_denied"])
        for field in AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS:
            self.assertFalse(evidence[field])
        self.assertEqual(
            evidence["aeg_state_write_denial_enforcement_status"],
            AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        )
        self.assertNotIn(evidence["aeg_state_write_denial_enforcement_status"], ("CLEAN", "PASS", "ENFORCED"))
        self.assertEqual(
            evidence["aeg_state_write_denial_source"],
            AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA,
        )
        self.assertEqual(evidence["aeg_state_write_denial_reason"], AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY)
        self.assertEqual(
            evidence["aeg_state_write_denial_metadata_hash"],
            expected_aeg_state_write_denial_metadata_hash(evidence),
        )
        self.assertTrue(evidence["checks"]["aeg_state_write_denial_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["capability_write_aeg_state_granted_default_false"])
        self.assertTrue(evidence["checks"]["capability_write_aeg_state_denied_explicit"])
        self.assertTrue(evidence["checks"]["aeg_state_write_denial_enforcement_not_claimed"])
        self.assertTrue(evidence["checks"]["aeg_state_write_denial_metadata_is_not_external_proof"])
        self.assertTrue(evidence["checks"]["executor_self_report_is_not_aeg_state_denial_proof"])
        self.assertTrue(evidence["checks"]["raw_shell_write_aeg_state_bypass_forbidden"])
        self.assertTrue(evidence["checks"]["write_file_write_aeg_state_bypass_forbidden"])
        self.assertTrue(evidence["checks"]["repo_outside_write_aeg_state_bypass_forbidden"])
        self.assertTrue(evidence["checks"]["executor_controlled_recorder_write_aeg_state_bypass_forbidden"])
        self.assertTrue(evidence["checks"]["no_live_executor_authority_before_aeg_state_write_denial_enforcement"])
        self.assertTrue(evidence["checks"]["aeg_state_write_denial_manifest_binding_required"])

    def _assert_mediated_write_boundary_scaffold_contract(self, evidence):
        self.assertEqual(
            evidence["mediated_write_boundary_scaffold_version"],
            MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0,
        )
        self.assertEqual(
            evidence["mediated_write_boundary_scaffold_status"],
            MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        )
        self.assertEqual(
            evidence["mediated_write_boundary_enforcement_status"],
            MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        )
        self.assertNotIn(evidence["mediated_write_boundary_scaffold_status"], ("PASS", "SAFE_TO_RUN", "ENFORCED"))
        self.assertNotIn(evidence["mediated_write_boundary_enforcement_status"], ("PASS", "SAFE_TO_RUN", "ENFORCED"))
        self.assertFalse(evidence["write_mediation_enabled"])
        self.assertFalse(evidence["write_mediation_enforced"])
        self.assertEqual(evidence["write_classes_declared"], list(WRITE_CLASSES))
        self.assertEqual(evidence["write_classes_granted"], [])
        self.assertEqual(evidence["write_classes_denied"], list(WRITE_CLASSES))
        self.assertEqual(evidence["write_class_mediation_statuses"], dict(WRITE_CLASS_DEFAULT_MEDIATION_STATUSES))
        self.assertEqual(
            evidence["write_mediation_decision_source"],
            MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA,
        )
        self.assertEqual(evidence["write_mediation_evidence_status"], NOT_CHECKED)
        for field in MEDIATED_WRITE_DIRECT_ALLOW_FIELDS:
            self.assertFalse(evidence[field])
        self.assertEqual(evidence["write_mediation_decision_hash"], expected_write_mediation_decision_hash(evidence))
        self.assertEqual(
            evidence["mediated_write_boundary_metadata_hash"],
            expected_mediated_write_boundary_metadata_hash(evidence),
        )
        self.assertTrue(evidence["checks"]["mediated_write_boundary_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["mediated_write_boundary_scaffold_only_not_enforced"])
        self.assertTrue(evidence["checks"]["mediation_design_is_not_implementation"])
        self.assertTrue(evidence["checks"]["mediation_scaffold_is_not_enforcement"])
        self.assertTrue(evidence["checks"]["no_actual_mediated_write_enforcement"])
        self.assertTrue(evidence["checks"]["write_mediation_enabled_default_false"])
        self.assertTrue(evidence["checks"]["write_mediation_enforced_default_false"])
        self.assertTrue(evidence["checks"]["write_classes_declared_vocabulary_required"])
        self.assertTrue(evidence["checks"]["write_classes_granted_default_empty"])
        self.assertTrue(evidence["checks"]["dangerous_direct_write_grants_default_false"])
        self.assertTrue(evidence["checks"]["scaffold_only_not_safe_to_run"])
        self.assertTrue(evidence["checks"]["write_mediation_not_checked_is_not_pass"])
        self.assertTrue(evidence["checks"]["denied_by_metadata_is_not_external_enforcement"])
        self.assertTrue(evidence["checks"]["executor_self_report_is_not_write_mediation_proof"])
        self.assertTrue(evidence["checks"]["no_live_executor_authority_before_mediated_write_boundary"])
        self.assertTrue(evidence["checks"]["mediated_write_boundary_manifest_binding_required"])

    def _assert_write_bypass_harness_scaffold_contract(self, evidence):
        self.assertEqual(evidence["write_bypass_harness_scaffold_version"], WRITE_BYPASS_HARNESS_SCAFFOLD_V0)
        self.assertEqual(
            evidence["write_bypass_harness_scaffold_status"],
            WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        )
        self.assertEqual(evidence["write_bypass_harness_execution_status"], NOT_CHECKED)
        self.assertEqual(
            evidence["write_bypass_harness_enforcement_status"],
            WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        )
        self.assertEqual(
            evidence["write_bypass_harness_registry_status"],
            WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        )
        self.assertEqual(evidence["write_bypass_harness_expected_wbyp_count"], WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT)
        self.assertEqual(evidence["write_bypass_harness_registry_ids"], list(WBYP_IDS))
        self.assertEqual(evidence["write_bypass_harness_fixture_status"], NOT_CHECKED)
        self.assertEqual(evidence["write_bypass_harness_evidence_status"], NOT_CHECKED)
        self.assertFalse(evidence["write_bypass_harness_actual_bypass_tests_present"])
        self.assertFalse(evidence["write_bypass_harness_actual_fixtures_present"])
        self.assertFalse(evidence["write_bypass_harness_actual_write_attempts_present"])
        self.assertFalse(evidence["write_bypass_harness_mediator_enforcement_present"])
        self.assertFalse(evidence["write_bypass_harness_external_enforcement_present"])
        self.assertFalse(evidence["write_bypass_harness_executor_self_report_proof_allowed"])
        self.assertFalse(evidence["write_bypass_harness_reported_only_judgment_basis_allowed"])
        self.assertNotIn(evidence["write_bypass_harness_scaffold_status"], ("PASS", "SAFE", "ENFORCED"))
        self.assertNotIn(evidence["write_bypass_harness_execution_status"], ("PASS", "SAFE", "ENFORCED"))
        registry = evidence["write_bypass_harness_registry"]
        self.assertEqual([entry["id"] for entry in registry], list(WBYP_IDS))
        self.assertEqual(len(registry), 25)
        for entry in registry:
            self.assertTrue(entry["future_only"])
            self.assertEqual(entry["scaffold_status"], WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED)
            self.assertEqual(entry["execution_status"], NOT_CHECKED)
            self.assertEqual(entry["enforcement_status"], WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED)
            self.assertFalse(entry["actual_test_present"])
            self.assertFalse(entry["fixture_created"])
            self.assertFalse(entry["actual_write_attempt_present"])
            self.assertEqual(entry["proof_source"], WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED)
            self.assertFalse(entry["executor_self_report_proof_allowed"])
            self.assertFalse(entry["reported_only_judgment_basis_allowed"])
            self.assertFalse(entry["judgment_basis"])
            self.assertNotIn(entry["scaffold_status"], ("PASS", "SAFE", "ENFORCED"))
            self.assertNotIn(entry["execution_status"], ("PASS", "SAFE", "ENFORCED"))
            self.assertNotIn(entry["enforcement_status"], ("PASS", "SAFE", "ENFORCED"))
        self.assertEqual(
            evidence["write_bypass_harness_registry_hash"],
            expected_write_bypass_harness_registry_hash(evidence),
        )
        self.assertEqual(
            evidence["write_bypass_harness_metadata_hash"],
            expected_write_bypass_harness_metadata_hash(evidence),
        )
        self.assertTrue(evidence["checks"]["write_bypass_harness_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_registry_metadata_only"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_wbyp_001_through_025_required"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_scaffold_only_not_enforced"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_execution_not_checked"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_not_checked_is_not_pass"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_has_no_actual_bypass_tests"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_has_no_actual_fixtures"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_has_no_actual_write_attempts"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_has_no_mediator_enforcement"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_has_no_external_enforcement"])
        self.assertTrue(evidence["checks"]["executor_self_report_is_not_write_bypass_proof"])
        self.assertTrue(evidence["checks"]["reported_only_is_not_write_bypass_judgment_basis"])
        self.assertTrue(evidence["checks"]["no_live_executor_authority_before_write_bypass_harness"])
        self.assertTrue(evidence["checks"]["write_bypass_harness_manifest_binding_required"])

    def _assert_pre_live_executor_gate_contract(self, evidence):
        self.assertEqual(evidence["pre_live_executor_gate_version"], PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0)
        self.assertEqual(evidence["pre_live_executor_gate_mode"], PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD)
        self.assertEqual(evidence["pre_live_executor_gate_status"], PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD)
        self.assertFalse(evidence["live_executor_authority_requested"])
        self.assertFalse(evidence["live_executor_authority_granted"])
        self.assertEqual(
            evidence["live_executor_authority_hold_reason"],
            LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE,
        )
        self.assertTrue(evidence["requires_tamper_evident_ledger"])
        self.assertTrue(evidence["tamper_evident_ledger_present"])
        self.assertTrue(evidence["requires_aeg_state_write_denial"])
        self.assertTrue(evidence["aeg_state_write_denial_present"])
        self.assertTrue(evidence["requires_external_enforcement"])
        self.assertFalse(evidence["external_enforcement_present"])
        self.assertTrue(evidence["evidence_store_executor_isolated_required"])
        self.assertFalse(evidence["evidence_store_executor_isolated_present"])
        self.assertFalse(evidence["evidence_store_is_executor_isolated"])
        self.assertIn(
            evidence["pre_live_executor_gate_result"],
            (PRE_LIVE_EXECUTOR_GATE_RESULT_HOLD_CURRENT_STATE, PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT),
        )
        self.assertNotIn(evidence["pre_live_executor_gate_result"], ("PASS", "CLEAN", "ALLOW"))
        self.assertEqual(evidence["pre_live_executor_gate_reason"], PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY)
        self.assertEqual(
            evidence["pre_live_executor_gate_metadata_hash"],
            expected_pre_live_executor_gate_metadata_hash(evidence),
        )
        self.assertTrue(evidence["checks"]["pre_live_executor_gate_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["pre_live_executor_gate_candidate_e_requires_ledger"])
        self.assertTrue(evidence["checks"]["pre_live_executor_gate_candidate_e_requires_aeg_state_write_denial"])
        self.assertTrue(evidence["checks"]["live_executor_authority_granted_default_false"])
        self.assertTrue(evidence["checks"]["pre_live_executor_gate_pass_clean_allow_forbidden"])
        self.assertTrue(evidence["checks"]["external_enforcement_absent_keeps_live_executor_on_hold"])
        self.assertTrue(evidence["checks"]["evidence_store_executor_isolation_absent_keeps_live_executor_on_hold"])
        self.assertTrue(evidence["checks"]["pre_live_executor_gate_manifest_binding_required"])

    def _assert_ledger_integrity_scaffold_contract(self, evidence):
        self.assertEqual(evidence["ledger_integrity_version"], LEDGER_INTEGRITY_SCAFFOLD_V0)
        self.assertEqual(evidence["ledger_integrity_mode"], LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD)
        self.assertEqual(
            evidence["ledger_integrity_status"],
            LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY,
        )
        self.assertTrue(evidence["ledger_tamper_evident_enabled"])
        self.assertFalse(evidence["ledger_tamper_proof_claimed"])
        self.assertNotIn(evidence["ledger_integrity_status"], ("CLEAN", "PASS"))
        self.assertIsInstance(evidence["ledger_sequence_number"], int)
        self.assertGreaterEqual(evidence["ledger_sequence_number"], 1)
        self.assertIsInstance(evidence["previous_ledger_hash"], str)
        self.assertTrue(evidence["previous_ledger_hash"])
        self.assertEqual(evidence["current_evidence_hash"], expected_current_evidence_hash(evidence))
        self.assertEqual(evidence["ledger_chain_hash"], expected_ledger_chain_hash(evidence))
        self.assertEqual(
            evidence["ledger_integrity_metadata_hash"],
            expected_ledger_integrity_metadata_hash(evidence),
        )
        self.assertEqual(evidence["ledger_integrity_check_status"], LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED)
        self.assertNotIn(evidence["ledger_integrity_check_status"], ("CLEAN", "PASS"))
        self.assertEqual(
            evidence["ledger_integrity_check_reason"],
            LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY,
        )
        self.assertTrue(evidence["checks"]["ledger_integrity_scaffold_v0_required"])
        self.assertTrue(evidence["checks"]["ledger_tamper_evident_is_not_tamper_proof"])
        self.assertTrue(evidence["checks"]["ledger_tamper_proof_claim_forbidden"])
        self.assertTrue(evidence["checks"]["ledger_integrity_clean_claim_forbidden"])
        self.assertTrue(evidence["checks"]["ledger_integrity_check_not_checked_is_not_pass"])
        self.assertTrue(evidence["checks"]["ledger_integrity_manifest_binding_required"])

    def _assert_prompt_redaction_not_requested_contract(self, evidence):
        self.assertFalse(evidence["prompt_build_requested"])
        self.assertEqual(evidence["prompt_build_status"], PROMPT_BUILD_STATUS_NOT_BUILT)
        self.assertEqual(evidence["prompt_source"], PROMPT_SOURCE_NONE)
        self.assertEqual(evidence["prompt_input_summary"], "")
        self.assertEqual(evidence["prompt_redaction_status"], PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED)
        self.assertEqual(evidence["prompt_hash_candidate"], "")
        self.assertEqual(evidence["prompt_storage_policy"], PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE)
        self.assertFalse(evidence["prompt_secret_detected"])
        self.assertFalse(evidence["prompt_raw_stored"])

    def _assert_prompt_redaction_disabled_contract(self, evidence):
        self.assertFalse(evidence["prompt_build_requested"])
        self.assertEqual(evidence["prompt_build_status"], PROMPT_BUILD_STATUS_PROVIDER_DISABLED)
        self.assertEqual(evidence["prompt_source"], PROMPT_SOURCE_DISABLED)
        self.assertEqual(evidence["prompt_input_summary"], "")
        self.assertEqual(evidence["prompt_redaction_status"], PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED)
        self.assertEqual(evidence["prompt_hash_candidate"], "")
        self.assertEqual(evidence["prompt_storage_policy"], PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE)
        self.assertFalse(evidence["prompt_secret_detected"])
        self.assertFalse(evidence["prompt_raw_stored"])

    def _assert_response_redaction_not_requested_contract(self, evidence):
        self.assertFalse(evidence["response_present"])
        self.assertEqual(evidence["response_status"], RESPONSE_STATUS_NOT_REQUESTED)
        self.assertEqual(evidence["response_source"], RESPONSE_SOURCE_NONE)
        self.assertTrue(evidence["response_reported_only"])
        self.assertEqual(evidence["response_trust_boundary"], REPORTED_ONLY)
        self.assertEqual(evidence["response_redaction_status"], RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED)
        self.assertEqual(evidence["response_hash_candidate"], "")
        self.assertFalse(evidence["response_raw_stored"])
        self.assertEqual(evidence["response_error_class"], RESPONSE_ERROR_CLASS_NONE)
        self.assertEqual(evidence["response_error_safe_summary"], RESPONSE_ERROR_SAFE_SUMMARY_NONE)

    def _assert_response_redaction_disabled_contract(self, evidence):
        self.assertFalse(evidence["response_present"])
        self.assertEqual(evidence["response_status"], RESPONSE_STATUS_PROVIDER_DISABLED)
        self.assertEqual(evidence["response_source"], RESPONSE_SOURCE_DISABLED_ADAPTER)
        self.assertTrue(evidence["response_reported_only"])
        self.assertEqual(evidence["response_trust_boundary"], REPORTED_ONLY)
        self.assertEqual(evidence["response_redaction_status"], RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED)
        self.assertEqual(evidence["response_hash_candidate"], "")
        self.assertFalse(evidence["response_raw_stored"])
        self.assertEqual(evidence["response_error_class"], RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(evidence["response_error_safe_summary"], RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED)

    def _assert_provider_runtime_not_requested_contract(self, evidence):
        self.assertEqual(evidence["provider_runtime_state"], PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE)
        self.assertEqual(evidence["provider_runtime_status"], PROVIDER_RUNTIME_STATUS_NOT_REQUESTED)
        self.assertEqual(evidence["provider_runtime_hold_reason"], PROVIDER_RUNTIME_HOLD_REASON_NOT_REQUESTED)
        self.assertEqual(evidence["provider_runtime_error_class"], PROVIDER_RUNTIME_ERROR_CLASS_NONE)
        self.assertEqual(evidence["provider_runtime_error_safe_summary"], PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NONE)
        self.assertFalse(evidence["provider_selection_requested"])
        self.assertFalse(evidence["provider_selected"])
        self.assertEqual(evidence["provider_selection_source"], PROVIDER_SELECTION_SOURCE_NOT_REQUESTED)
        self.assertEqual(evidence["provider_selection_status"], PROVIDER_SELECTION_STATUS_NOT_REQUESTED)
        self.assertFalse(evidence["provider_secret_required"])
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertFalse(evidence["provider_secret_value_recorded"])
        self.assertEqual(
            evidence["provider_secret_redaction_status"],
            PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED,
        )
        self.assertFalse(evidence["provider_env_loading_requested"])
        self.assertEqual(evidence["provider_env_loading_status"], PROVIDER_ENV_LOADING_STATUS_NOT_REQUESTED)
        self.assertFalse(evidence["provider_network_opt_in_requested"])
        self.assertFalse(evidence["provider_network_opt_in_allowed"])
        self.assertFalse(evidence["provider_network_used"])
        self.assertEqual(evidence["provider_network_status"], PROVIDER_NETWORK_STATUS_NOT_REQUESTED)
        self.assertEqual(evidence["provider_network_block_reason"], PROVIDER_NETWORK_BLOCK_REASON_NONE)
        self.assertFalse(evidence["provider_request_requested"])
        self.assertEqual(evidence["provider_request_status"], PROVIDER_REQUEST_STATUS_NOT_REQUESTED)
        self.assertEqual(len(evidence["provider_request_metadata_hash"]), 64)
        self.assertFalse(evidence["provider_request_raw_stored"])
        self.assertEqual(len(evidence["provider_response_metadata_hash"]), 64)
        self.assertFalse(evidence["provider_response_raw_stored"])
        self.assertEqual(evidence["provider_error_class"], PROVIDER_RESPONSE_ERROR_CLASS_NONE)
        self.assertEqual(evidence["provider_error_safe_summary"], PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE)

    def _assert_provider_runtime_disabled_contract(self, evidence):
        self.assertEqual(evidence["provider_runtime_state"], PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE)
        self.assertEqual(evidence["provider_runtime_status"], PROVIDER_RUNTIME_STATUS_HELD_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(
            evidence["provider_runtime_hold_reason"],
            PROVIDER_RUNTIME_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
        )
        self.assertEqual(evidence["provider_runtime_error_class"], PROVIDER_RUNTIME_ERROR_CLASS_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(
            evidence["provider_runtime_error_safe_summary"],
            PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
        )
        self.assertTrue(evidence["provider_selection_requested"])
        self.assertFalse(evidence["provider_selected"])
        self.assertEqual(evidence["provider_selection_source"], PROVIDER_SELECTION_SOURCE_DISABLED)
        self.assertEqual(evidence["provider_selection_status"], PROVIDER_SELECTION_STATUS_NOT_CONFIGURED)
        self.assertFalse(evidence["provider_secret_required"])
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertFalse(evidence["provider_secret_value_recorded"])
        self.assertEqual(
            evidence["provider_secret_redaction_status"],
            PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED,
        )
        self.assertFalse(evidence["provider_env_loading_requested"])
        self.assertEqual(evidence["provider_env_loading_status"], PROVIDER_ENV_LOADING_STATUS_DISABLED)
        self.assertFalse(evidence["provider_network_opt_in_requested"])
        self.assertFalse(evidence["provider_network_opt_in_allowed"])
        self.assertFalse(evidence["provider_network_used"])
        self.assertEqual(evidence["provider_network_status"], PROVIDER_NETWORK_STATUS_BLOCKED_NO_OPT_IN)
        self.assertEqual(
            evidence["provider_network_block_reason"],
            PROVIDER_NETWORK_BLOCK_REASON_OPT_IN_NOT_REQUESTED,
        )
        self.assertFalse(evidence["provider_request_requested"])
        self.assertEqual(
            evidence["provider_request_status"],
            PROVIDER_REQUEST_STATUS_BLOCKED_PROVIDER_NOT_CONFIGURED,
        )
        self.assertEqual(len(evidence["provider_request_metadata_hash"]), 64)
        self.assertFalse(evidence["provider_request_raw_stored"])
        self.assertEqual(len(evidence["provider_response_metadata_hash"]), 64)
        self.assertFalse(evidence["provider_response_raw_stored"])
        self.assertEqual(evidence["provider_error_class"], PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(evidence["provider_error_safe_summary"], PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED)

    def _assert_provider_not_requested_contract(self, evidence):
        self._assert_provider_runtime_not_requested_contract(evidence)
        self._assert_prompt_redaction_not_requested_contract(evidence)
        self._assert_response_redaction_not_requested_contract(evidence)
        self.assertEqual(evidence["provider_request_id"], "")
        self.assertEqual(evidence["provider_mode"], PROVIDER_MODE_NOT_REQUESTED)
        self.assertEqual(evidence["provider_name"], PROVIDER_NAME_NONE)
        self.assertEqual(evidence["provider_model"], PROVIDER_MODEL_NONE)
        self.assertEqual(evidence["provider_prompt_source"], PROVIDER_PROMPT_SOURCE_NONE)
        self.assertEqual(evidence["provider_prompt_hash_candidate"], "")
        self.assertEqual(
            evidence["provider_request_redaction_status"],
            PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        )
        self.assertFalse(evidence["provider_network_opt_in"])
        self.assertEqual(evidence["provider_secret_source"], PROVIDER_SECRET_SOURCE_NOT_REQUESTED)
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertFalse(evidence["provider_response_present"])
        self.assertEqual(evidence["provider_response_status"], PROVIDER_RESPONSE_STATUS_NOT_REQUESTED)
        self.assertEqual(evidence["provider_response_source"], PROVIDER_RESPONSE_SOURCE_NONE)
        self.assertTrue(evidence["provider_response_reported_only"])
        self.assertEqual(evidence["provider_response_trust_boundary"], REPORTED_ONLY)
        self.assertEqual(evidence["provider_response_hash_candidate"], "")
        self.assertEqual(
            evidence["provider_response_redaction_status"],
            PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        )
        self.assertEqual(evidence["provider_response_error_class"], PROVIDER_RESPONSE_ERROR_CLASS_NONE)
        self.assertEqual(evidence["provider_response_error_safe_summary"], PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE)

    def _assert_provider_disabled_contract(self, evidence):
        self._assert_provider_runtime_disabled_contract(evidence)
        self._assert_prompt_redaction_disabled_contract(evidence)
        self._assert_response_redaction_disabled_contract(evidence)
        self.assertEqual(evidence["provider_request_id"], PROVIDER_ADAPTER_DISABLED_REQUEST_ID)
        self.assertEqual(evidence["provider_mode"], PROVIDER_MODE_DISABLED)
        self.assertEqual(evidence["provider_name"], PROVIDER_NAME_NONE)
        self.assertEqual(evidence["provider_model"], PROVIDER_MODEL_NONE)
        self.assertEqual(evidence["provider_prompt_source"], PROVIDER_PROMPT_SOURCE_DISABLED)
        self.assertEqual(evidence["provider_prompt_hash_candidate"], "")
        self.assertEqual(
            evidence["provider_request_redaction_status"],
            PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        )
        self.assertFalse(evidence["provider_network_opt_in"])
        self.assertEqual(evidence["provider_secret_source"], PROVIDER_SECRET_SOURCE_NONE)
        self.assertFalse(evidence["provider_secret_observed"])
        self.assertFalse(evidence["provider_response_present"])
        self.assertEqual(evidence["provider_response_status"], PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(evidence["provider_response_source"], PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER)
        self.assertTrue(evidence["provider_response_reported_only"])
        self.assertEqual(evidence["provider_response_trust_boundary"], REPORTED_ONLY)
        self.assertEqual(evidence["provider_response_hash_candidate"], "")
        self.assertEqual(
            evidence["provider_response_redaction_status"],
            PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        )
        self.assertEqual(
            evidence["provider_response_error_class"],
            PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
        )
        self.assertEqual(
            evidence["provider_response_error_safe_summary"],
            PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
        )

    def _assert_proposal_held_contract(self, evidence, requires_user_gate):
        self.assertEqual(evidence["proposal_id"], "")
        self.assertEqual(evidence["proposal_version"], CITIZEN_ONE_PROPOSAL_CONTRACT_V0)
        self.assertEqual(evidence["proposal_kind"], PROPOSAL_KIND_NOT_GENERATED)
        self.assertEqual(evidence["proposal_summary"], "")
        self.assertEqual(evidence["proposal_steps"], [])
        self.assertEqual(evidence["proposal_risk_notes"], [])
        self.assertEqual(evidence["proposal_requires_user_gate"], requires_user_gate)
        self.assertEqual(evidence["proposal_trust_boundary"], REPORTED_ONLY)
        self.assertTrue(evidence["proposal_reported_only"])
        self.assertEqual(evidence["proposal_source"], PROPOSAL_SOURCE_NONE)
        self.assertEqual(evidence["proposal_output_hash_candidate"], "")
        self.assertEqual(
            evidence["proposal_redaction_status"],
            PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        )
        self.assertEqual(evidence["proposal_status"], PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED)
        self.assertFalse(evidence["proposal_present"])
        self.assertEqual(evidence["proposal_hold_reason"], PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED)
        self.assertEqual(evidence["model_output_hash_candidate"], "")
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_observed"])
        self._assert_provider_disabled_contract(evidence)

    def _assert_proposal_stub_contract(self, evidence, requires_user_gate):
        self.assertEqual(evidence["proposal_id"], DETERMINISTIC_STUB_PROPOSAL_ID)
        self.assertEqual(evidence["proposal_version"], CITIZEN_ONE_PROPOSAL_CONTRACT_V0)
        self.assertEqual(evidence["proposal_kind"], PROPOSAL_KIND_DETERMINISTIC_STUB)
        self.assertEqual(evidence["proposal_summary"], DETERMINISTIC_STUB_PROPOSAL_SUMMARY)
        self.assertEqual(evidence["proposal_steps"], list(DETERMINISTIC_STUB_PROPOSAL_STEPS))
        self.assertEqual(evidence["proposal_risk_notes"], list(DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES))
        self.assertEqual(evidence["proposal_requires_user_gate"], requires_user_gate)
        self.assertEqual(evidence["proposal_trust_boundary"], REPORTED_ONLY)
        self.assertTrue(evidence["proposal_reported_only"])
        self.assertEqual(evidence["proposal_source"], PROPOSAL_SOURCE_DETERMINISTIC_STUB)
        self.assertEqual(len(evidence["proposal_output_hash_candidate"]), 64)
        self.assertTrue(all(char in "0123456789abcdef" for char in evidence["proposal_output_hash_candidate"]))
        self.assertEqual(
            evidence["proposal_redaction_status"],
            PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        )
        self.assertEqual(evidence["proposal_status"], PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED)
        self.assertTrue(evidence["proposal_present"])
        self.assertEqual(evidence["proposal_hold_reason"], PROPOSAL_HOLD_REASON_NONE)
        self.assertEqual(evidence["model_output_hash_candidate"], "")
        self.assertFalse(evidence["provider_network_used"])
        self.assertFalse(evidence["provider_secret_observed"])
        self._assert_provider_disabled_contract(evidence)

    def _assert_no_forbidden_raw_storage_keys(self, payload):
        forbidden = set(FORBIDDEN_RAW_PROMPT_RESPONSE_KEYS)
        self.assertFalse(forbidden.intersection(self._all_keys(payload)))

    def _assert_artifacts_do_not_store_forbidden_raw_keys_or_secret(self, secret_value):
        for artifact in (self.repo / ".aeg").rglob("*"):
            if not artifact.is_file():
                continue
            text = artifact.read_text(encoding="utf-8")
            self.assertNotIn(secret_value, text)
            if artifact.name == "ledger.jsonl":
                payloads = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                payloads = [json.loads(text)]
            for payload in payloads:
                self._assert_no_forbidden_raw_storage_keys(payload)

    def _all_keys(self, value):
        keys = set()
        if isinstance(value, dict):
            for key, child in value.items():
                keys.add(key)
                keys.update(self._all_keys(child))
        elif isinstance(value, list):
            for child in value:
                keys.update(self._all_keys(child))
        return keys


if __name__ == "__main__":
    unittest.main()
