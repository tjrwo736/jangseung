import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.noop import execute_contract as noop_execute_contract
from src.cli.main import _cmd_init, _cmd_run
from src.contracts import (
    B1_AEG_DIRECT_TARGET_DENIED,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    PHASE11B_LIVE_EXECUTOR_NOT_STARTED,
    SAFE_DEFAULT,
    STORE_WRITE_BOUNDARY_STRENGTH_IN_PROCESS_TAMPER_EVIDENT_ONLY,
    STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
    STORE_WRITE_EXECUTOR_CODE_EXECUTION_MODEL_STRUCTURED_ACTIONS_REQUIRED,
    STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED,
    STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED,
    STORE_WRITE_MEDIATION_FIELDS,
    STORE_WRITE_MEDIATION_RESULT_BLOCKED,
    STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT,
    STORE_WRITE_CONTEXT_RESULT_BLOCKED,
    STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
    STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
    STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
    STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
    STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
    STORE_WRITE_PROCESS_ISOLATION_NOT_IMPLEMENTED,
    STORE_WRITE_SINK_APPEND_LEDGER,
    STORE_WRITE_SINK_WRITE_JSON,
    STORE_WRITE_OS_SANDBOX_NOT_IMPLEMENTED,
    STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
)
from src.evidence.binding import (
    manifest_hash,
    sha256_json,
    store_write_mediation_manifest_fields,
)
from src.evidence.store_write_mediation import expected_store_write_mediation_metadata_hash
from src.state.store import (
    StoreWriteMediationBlocked,
    _append_ledger_unmediated,
    _executor_attributed_store_write_context,
    _write_json,
)
from src.evidence.verify import verify_latest


class Phase11BStoreWriteMediationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init")
        self._git("config", "user.email", "aegis@example.invalid")
        self._git("config", "user.name", "Aegis Test")
        (self.repo / ".gitignore").write_text(".aeg/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "init")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_actual_run_blocks_executor_attributed_aeg_direct_and_traversal_writes(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)

        evidence, _ = self._latest_evidence_with_path()
        blocked_events = [
            event
            for event in evidence["store_write_mediation_events"]
            if event["write_provenance_type"] == STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED
        ]

        self.assertTrue(evidence["store_write_mediation_enabled"])
        self.assertEqual(evidence["store_write_mediation_scope"], "executor_attributed_aeg_direct_traversal_writes_only")
        self.assertEqual(evidence["store_write_boundary"], STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED)
        self._assert_reclassification_fields(evidence)
        self.assertEqual(evidence["guarded_sinks"], [STORE_WRITE_SINK_APPEND_LEDGER, STORE_WRITE_SINK_WRITE_JSON])
        self.assertTrue(evidence["write_json_sink_guarded"])
        self.assertTrue(evidence["ledger_append_sink_guarded"])
        self.assertTrue(evidence["trusted_context_required"])
        self.assertEqual(evidence["trusted_context_basis"], STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY)
        self.assertFalse(evidence["call_stack_inference_used_as_judgment_basis"])
        self.assertEqual(evidence["missing_context_result"], STORE_WRITE_CONTEXT_RESULT_BLOCKED)
        self.assertEqual(evidence["omitted_declaration_result"], STORE_WRITE_CONTEXT_RESULT_BLOCKED)
        self.assertEqual(
            evidence["executor_self_report_trusted_result"],
            STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
        )
        self.assertEqual(evidence["write_provenance_source"], STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT)
        self.assertEqual(evidence["write_provenance_basis"], STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY)
        self.assertTrue(evidence["executor_attributed_write_blocked"])
        self.assertEqual(evidence["executor_direct_sink_write_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(evidence["executor_direct_sink_write_created_files_count"], 0)
        self.assertEqual(evidence["executor_direct_ledger_append_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(evidence["executor_direct_ledger_entries_appended_count"], 0)
        self.assertTrue(evidence["trusted_runtime_write_allowed"])
        self.assertTrue(evidence["trusted_runtime_ledger_append_allowed"])
        self.assertTrue(evidence["executor_self_report_ignored"])
        self.assertTrue(evidence["executor_omitted_declaration_rejected"])
        self.assertEqual(evidence["blocked_write_target_count"], 3)
        self.assertEqual(evidence["blocked_write_created_files_count"], 0)
        self.assertEqual(evidence["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(evidence["known_gap_aeg_direct_traversal_status"], STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED)
        self.assertEqual(evidence["known_gap_non_aeg_status"], STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED)
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence["phase11b_live_executor_status"], PHASE11B_LIVE_EXECUTOR_NOT_STARTED)
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)

        self.assertEqual(len(blocked_events), 4)
        write_json_blocked_events = [
            event for event in blocked_events if event["sink_name"] == STORE_WRITE_SINK_WRITE_JSON
        ]
        ledger_blocked_events = [
            event for event in blocked_events if event["sink_name"] == STORE_WRITE_SINK_APPEND_LEDGER
        ]
        self.assertEqual(len(write_json_blocked_events), 3)
        self.assertEqual(len(ledger_blocked_events), 1)
        target_classes = {event["guard_decision"]["target_class"] for event in write_json_blocked_events}
        self.assertEqual(target_classes, {B1_AEG_DIRECT_TARGET_DENIED, B1_AEG_TRAVERSAL_TARGET_DENIED})
        for event in blocked_events:
            self.assertEqual(event["store_write_boundary"], STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED)
            self.assertTrue(event["sink_guarded"])
            self.assertTrue(event["guard_router_invoked"])
            self.assertFalse(event["write_performed"])
            self.assertFalse(event["target_file_created"])
            self.assertFalse(event["fallback_to_unwired"])
            self.assertTrue(event["trusted_context_required"])
            self.assertEqual(event["trusted_context_basis"], STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY)
            self.assertFalse(event["trusted_context_valid"])
            self.assertFalse(event["trusted_capability_runtime_owned"])
            self.assertFalse(event["call_stack_inference_used_as_judgment_basis"])
            self.assertFalse(event["caller_name_match_used_as_judgment_basis"])
            self.assertEqual(event["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
            self.assertEqual(event["write_provenance_type"], STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED)
            if event["sink_name"] == STORE_WRITE_SINK_WRITE_JSON:
                self.assertFalse(Path(event["canonical_target"]).exists())
            if event["sink_name"] == STORE_WRITE_SINK_APPEND_LEDGER:
                self.assertEqual(event["ledger_entries_appended_count"], 0)

        self.assertFalse((self.repo / ".aeg" / "executor-direct-blocked.json").exists())
        self.assertFalse((self.repo / ".aeg" / "executor-traversal-blocked.json").exists())
        self.assertFalse((self.repo / ".aeg" / "executor-omitted-declaration-blocked.json").exists())
        self.assertTrue(verify_latest(self.repo).ok)

    def test_direct_write_json_sink_bypass_is_blocked_before_file_creation(self):
        self._init()
        direct_target = self.repo / ".aeg" / "executor_bypass.json"
        traversal_target = self.repo / ".aeg" / ".." / ".aeg" / "traversal_bypass.json"

        with self.assertRaises(StoreWriteMediationBlocked) as direct:
            with _executor_attributed_store_write_context(
                self.repo,
                "test.executor_direct_write_json",
                executor_claimed_provenance=STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
            ):
                _write_json(direct_target, {"attacker": "executor content"})

        with self.assertRaises(StoreWriteMediationBlocked) as traversal:
            with _executor_attributed_store_write_context(self.repo, "test.executor_direct_write_json_traversal"):
                _write_json(traversal_target, {"attacker": "executor traversal content"})

        self.assertEqual(direct.exception.event["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(traversal.exception.event["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(direct.exception.event["sink_name"], STORE_WRITE_SINK_WRITE_JSON)
        self.assertEqual(traversal.exception.event["sink_name"], STORE_WRITE_SINK_WRITE_JSON)
        self.assertFalse(direct_target.exists())
        self.assertFalse((self.repo / ".aeg" / "traversal_bypass.json").exists())
        self.assertFalse(direct.exception.event["target_file_created"])
        self.assertFalse(traversal.exception.event["target_file_created"])
        self.assertEqual(len(list((self.repo / ".aeg").glob("*bypass.json"))), 0)
        self.assertFalse(direct.exception.event["trusted_context_valid"])
        self.assertFalse(traversal.exception.event["trusted_context_valid"])
        self.assertEqual(
            direct.exception.event["executor_self_report_trusted_result"],
            STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
        )

    def test_direct_ledger_append_sink_bypass_is_blocked_before_append(self):
        self._init()
        ledger_path = self.repo / ".aeg" / "ledger.jsonl"
        before = ledger_path.read_text(encoding="utf-8")

        with self.assertRaises(StoreWriteMediationBlocked) as missing_context_blocked:
            _append_ledger_unmediated(
                ledger_path,
                {
                    "run_id": "forged-missing-context-ledger-entry",
                    "task_text": "forged missing context",
                    "status": "CLEAN_CORE",
                },
            )

        self.assertEqual(before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(
            missing_context_blocked.exception.event["write_mediation_result"],
            STORE_WRITE_MEDIATION_RESULT_BLOCKED,
        )
        self.assertEqual(missing_context_blocked.exception.event["missing_context_result"], STORE_WRITE_CONTEXT_RESULT_BLOCKED)
        self.assertEqual(missing_context_blocked.exception.event["ledger_entries_appended_count"], 0)

        with self.assertRaises(StoreWriteMediationBlocked) as blocked:
            with _executor_attributed_store_write_context(
                self.repo,
                "test.executor_direct_ledger_append",
                executor_claimed_provenance=STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
            ):
                _append_ledger_unmediated(
                    ledger_path,
                    {
                        "run_id": "forged-executor-ledger-entry",
                        "task_text": "forged",
                        "status": "CLEAN_CORE",
                    },
                )

        after = ledger_path.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(blocked.exception.event["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(blocked.exception.event["sink_name"], STORE_WRITE_SINK_APPEND_LEDGER)
        self.assertEqual(blocked.exception.event["ledger_entries_appended_count"], 0)

    def test_omitted_sink_context_is_not_trusted(self):
        self._init()
        target = self.repo / ".aeg" / "omitted_declaration_bypass.json"

        with self.assertRaises(StoreWriteMediationBlocked) as blocked:
            _write_json(target, {"attacker": "omitted declaration"})

        self.assertEqual(blocked.exception.event["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertTrue(blocked.exception.event["executor_omitted_declaration"])
        self.assertEqual(blocked.exception.event["missing_context_result"], STORE_WRITE_CONTEXT_RESULT_BLOCKED)
        self.assertEqual(blocked.exception.event["omitted_declaration_result"], STORE_WRITE_CONTEXT_RESULT_BLOCKED)
        self.assertFalse(blocked.exception.event["trusted_context_valid"])
        self.assertFalse(target.exists())

    def test_trusted_runtime_save_run_still_writes_ledger_evidence_and_manifest(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)

        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        ledger_path = self.repo / ".aeg" / "ledger.jsonl"
        run_path = self.repo / self._ledger_entries()[-1]["run_path"]

        self.assertTrue(run_path.exists())
        self.assertTrue(evidence_path.exists())
        self.assertTrue(manifest_path.exists())
        self.assertTrue(ledger_path.exists())
        self.assertTrue(ledger_path.read_text(encoding="utf-8").strip())
        self.assertTrue(evidence["trusted_runtime_write_allowed"])
        self.assertTrue(evidence["trusted_runtime_ledger_append_allowed"])
        self._assert_reclassification_fields(evidence)
        self.assertEqual(evidence["guarded_sinks"], [STORE_WRITE_SINK_APPEND_LEDGER, STORE_WRITE_SINK_WRITE_JSON])
        self.assertFalse(evidence["executor_attributed_write_blocked"])
        self.assertEqual(evidence["executor_direct_sink_write_result"], STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT)
        self.assertEqual(evidence["executor_direct_ledger_append_result"], STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT)
        self.assertEqual(evidence["blocked_write_created_files_count"], 0)
        trusted_events = [
            event
            for event in evidence["store_write_mediation_events"]
            if event["write_provenance_type"] == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        ]
        self.assertTrue(trusted_events)
        for event in trusted_events:
            self.assertTrue(event["trusted_context_valid"])
            self.assertTrue(event["trusted_capability_runtime_owned"])
            self.assertEqual(event["trusted_context_basis"], STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY)
            self.assertFalse(event["call_stack_inference_used_as_judgment_basis"])
        self.assertEqual(
            evidence["bound_store_write_mediation_metadata_hash"],
            manifest["store_write_mediation_manifest_hash"],
        )
        self.assertTrue(verify_latest(self.repo).ok)

    def test_executor_self_report_cannot_claim_trusted_provenance(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)

        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        spoof_event = next(
            event
            for event in evidence["store_write_mediation_events"]
            if event["write_provenance_type"] == STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED
            and event["executor_claimed_provenance"] == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        )
        self.assertEqual(spoof_event["write_provenance_type"], STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED)
        self.assertFalse(spoof_event["executor_self_report_used"])
        self.assertFalse(spoof_event["trusted_runtime_claim_allowed"])
        self.assertEqual(spoof_event["executor_self_report_trusted_result"], STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED)
        self.assertEqual(evidence["executor_self_report_trusted_result"], STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED)

        evidence["store_write_mediation_events"][0]["executor_self_report_used"] = True
        evidence["store_write_mediation_events"][0]["write_provenance_type"] = STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("executor self-report trusted provenance" in error for error in verify.errors),
            verify.errors,
        )

    def test_runtime_owned_capability_provenance_is_required(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        self.assertEqual(evidence["write_provenance_source"], STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT)
        self.assertEqual(evidence["write_provenance_basis"], STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY)
        self.assertEqual(evidence["trusted_context_basis"], STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY)
        evidence["write_provenance_source"] = "executor_self_report"
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(any("write_provenance_source mismatch" in error for error in verify.errors), verify.errors)

    def test_call_stack_inference_claim_is_rejected(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["call_stack_inference_used_as_judgment_basis"] = True
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("call_stack_inference_used_as_judgment_basis mismatch" in error for error in verify.errors),
            verify.errors,
        )

    def test_missing_or_omitted_context_allowed_claim_is_rejected(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["missing_context_result"] = "ALLOWED"
        evidence["omitted_declaration_result"] = "TRUSTED"
        evidence["executor_self_report_trusted_result"] = "ACCEPTED"
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(any("missing_context_result mismatch" in error for error in verify.errors), verify.errors)
        self.assertTrue(any("omitted_declaration_result mismatch" in error for error in verify.errors), verify.errors)
        self.assertTrue(
            any("executor_self_report_trusted_result mismatch" in error for error in verify.errors),
            verify.errors,
        )

    def test_trusted_runtime_gate_failure_does_not_fallback_to_unwired_write(self):
        self._init()
        with patch("src.state.store._trusted_runtime_store_write_gate", side_effect=RuntimeError("wired route failed")):
            self.assertEqual(self._run("fix typo in README"), 1)

        ledger_path = self.repo / ".aeg" / "ledger.jsonl"

        self.assertTrue(ledger_path.exists())
        self.assertEqual(ledger_path.read_text(encoding="utf-8"), "")
        self.assertEqual(list((self.repo / ".aeg" / "runs").glob("*/run.json")), [])
        self.assertEqual(list((self.repo / ".aeg" / "runs").glob("*/evidence.json")), [])
        self.assertEqual(list((self.repo / ".aeg" / "runs").glob("*/manifest.json")), [])

    def test_blocked_claim_with_created_file_count_is_rejected_even_when_rebound(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["blocked_write_created_files_count"] = 1
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("blocked_write_created_files_count > 0" in error for error in verify.errors),
            verify.errors,
        )

    def test_verify_rejects_blocked_claim_when_target_file_exists(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        write_event = next(
            event
            for event in evidence["store_write_mediation_events"]
            if event["sink_name"] == STORE_WRITE_SINK_WRITE_JSON
            and event["write_mediation_result"] == STORE_WRITE_MEDIATION_RESULT_BLOCKED
        )
        write_event["target_exists_after"] = True
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("blocked executor write target exists after BLOCKED" in error for error in verify.errors),
            verify.errors,
        )

    def test_verify_rejects_blocked_ledger_claim_when_forged_entry_appended(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        ledger_event = next(
            event
            for event in evidence["store_write_mediation_events"]
            if event["sink_name"] == STORE_WRITE_SINK_APPEND_LEDGER
            and event["write_mediation_result"] == STORE_WRITE_MEDIATION_RESULT_BLOCKED
        )
        ledger_event["ledger_entries_after"] = ledger_event["ledger_entries_before"] + 1
        ledger_event["ledger_entries_appended_count"] = 1
        evidence["executor_direct_ledger_entries_appended_count"] = 1
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("forged entry appended" in error for error in verify.errors),
            verify.errors,
        )

    def test_verify_rejects_trusted_runtime_write_preserved_claim_when_target_missing(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        trusted_write_event = next(
            event
            for event in evidence["store_write_mediation_events"]
            if event["sink_name"] == STORE_WRITE_SINK_WRITE_JSON
            and event["write_provenance_type"] == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        )
        trusted_write_event["target_exists_after"] = False
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("trusted runtime write preserved claim rejected because target is missing" in error for error in verify.errors),
            verify.errors,
        )

    def test_verify_rejects_trusted_runtime_ledger_preserved_claim_when_append_failed(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        trusted_ledger_event = next(
            event
            for event in evidence["store_write_mediation_events"]
            if event["sink_name"] == STORE_WRITE_SINK_APPEND_LEDGER
            and event["write_provenance_type"] == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        )
        trusted_ledger_event["ledger_entries_after"] = trusted_ledger_event["ledger_entries_before"]
        trusted_ledger_event["ledger_entries_appended_count"] = 0
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("trusted runtime ledger append preserved claim rejected because append failed" in error for error in verify.errors),
            verify.errors,
        )

    def test_verify_rejects_sink_coverage_overclaim_when_one_sink_event_missing(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["store_write_mediation_events"] = [
            event
            for event in evidence["store_write_mediation_events"]
            if event["sink_name"] != STORE_WRITE_SINK_APPEND_LEDGER
        ]
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(any("guarded_sinks overclaim rejected" in error for error in verify.errors), verify.errors)

    def test_verify_rejects_in_process_boundary_overclaim_fields(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)

        overclaims = (
            ("trusted_context_security_boundary", "trusted_context_security_boundary=true rejected"),
            ("tamper_proof_claimed", "tamper_proof_claimed=true rejected"),
            ("physical_prevention_claimed", "physical_prevention_claimed=true rejected"),
            ("raw_bypass_impossible", "raw_bypass_impossible=true rejected"),
            ("arbitrary_in_process_code_safe", "arbitrary_in_process_code_safe=true rejected"),
            ("live_executor_ready", "live_executor_ready=true rejected"),
            ("write_authority_safe", "write_authority_safe=true rejected"),
        )
        for field, expected_error in overclaims:
            with self.subTest(field=field):
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = True
                self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

                verify = verify_latest(self.repo)

                self.assertFalse(verify.ok)
                self.assertTrue(any(expected_error in error for error in verify.errors), verify.errors)
                evidence[field] = False
                self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

    def test_verify_rejects_forbidden_store_write_overclaim_labels(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        forbidden_labels = (
            "TRUSTED_CONTEXT_SECURITY_BOUNDARY",
            "EXECUTOR_AEG_WRITE_FULLY_BLOCKED",
            "RAW_BYPASS_IMPOSSIBLE",
            "AEG_TAMPER_PROOF",
        )

        for label in forbidden_labels:
            with self.subTest(label=label):
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence["store_write_mediation_events"][0]["forbidden_overclaim_label"] = label
                self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

                verify = verify_latest(self.repo)

                self.assertFalse(verify.ok)
                self.assertTrue(any(f"{label} claim rejected" in error for error in verify.errors), verify.errors)
                del evidence["store_write_mediation_events"][0]["forbidden_overclaim_label"]
                self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

    def _executor_with_aeg_write_attempts(self, task_text, classification, law_result):
        result = noop_execute_contract(task_text, classification, law_result)
        result["executor_attributed_aeg_write_attempts"] = [
            {
                "target": ".aeg/executor-direct-blocked.json",
                "payload": "blocked direct",
                "executor_claimed_provenance": STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
            },
            {
                "target": ".aeg/runs/../executor-traversal-blocked.json",
                "payload": "blocked traversal",
            },
        ]
        return result

    def _init(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return _cmd_init(self.repo)

    def _run(self, task):
        with contextlib.redirect_stdout(io.StringIO()):
            return _cmd_run(self.repo, task)

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def _latest_evidence_with_path(self):
        entry = self._ledger_entries()[-1]
        path = self.repo / entry["evidence_path"]
        return json.loads(path.read_text(encoding="utf-8")), path

    def _latest_manifest_with_path(self):
        entry = self._ledger_entries()[-1]
        path = self.repo / entry["manifest_path"]
        return json.loads(path.read_text(encoding="utf-8")), path

    def _ledger_entries(self):
        ledger_path = self.repo / ".aeg" / "ledger.jsonl"
        return [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _assert_reclassification_fields(self, evidence):
        self.assertEqual(
            evidence["store_write_boundary_strength"],
            STORE_WRITE_BOUNDARY_STRENGTH_IN_PROCESS_TAMPER_EVIDENT_ONLY,
        )
        self.assertFalse(evidence["trusted_context_security_boundary"])
        self.assertTrue(evidence["requires_structured_executor"])
        self.assertTrue(evidence["arbitrary_in_process_code_breaks_boundary"])
        self.assertEqual(evidence["process_isolation_status"], STORE_WRITE_PROCESS_ISOLATION_NOT_IMPLEMENTED)
        self.assertEqual(evidence["os_sandbox_status"], STORE_WRITE_OS_SANDBOX_NOT_IMPLEMENTED)
        self.assertEqual(
            evidence["executor_code_execution_model"],
            STORE_WRITE_EXECUTOR_CODE_EXECUTION_MODEL_STRUCTURED_ACTIONS_REQUIRED,
        )
        self.assertFalse(evidence["tamper_proof_claimed"])
        self.assertFalse(evidence["physical_prevention_claimed"])
        self.assertFalse(evidence["raw_bypass_impossible"])
        self.assertFalse(evidence["arbitrary_in_process_code_safe"])
        self.assertFalse(evidence["live_executor_ready"])
        self.assertFalse(evidence["write_authority_safe"])
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence["phase11b_live_executor_status"], PHASE11B_LIVE_EXECUTOR_NOT_STARTED)

    def _rebind_store_write_mediation(self, evidence, evidence_path, manifest, manifest_path):
        evidence["store_write_mediation_metadata_hash"] = expected_store_write_mediation_metadata_hash(evidence)
        for field in STORE_WRITE_MEDIATION_FIELDS:
            manifest[field] = evidence[field]
        manifest["store_write_mediation_manifest_hash"] = sha256_json(
            store_write_mediation_manifest_fields(manifest)
        )
        evidence["bound_store_write_mediation_metadata_hash"] = manifest["store_write_mediation_manifest_hash"]
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence["bound_manifest_hash"] = manifest_hash(manifest)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
