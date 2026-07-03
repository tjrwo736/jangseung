from copy import deepcopy
import inspect
import unittest

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    SAFE_DEFAULT,
)
from src.evidence import phase11a_rollback_kill_path
from src.evidence.phase11a_rollback_kill_path import (
    AUTHORITY_SNAPSHOT,
    CandidateWiredPathResult,
    FALLBACK_TARGET_EXISTING_UNWIRED_PATH,
    PHASE11A1_WIRING_STATUS_NOT_STARTED,
    PHASE11A_ROLLBACK_KILL_PATH_KIND,
    PHASE11A_ROLLBACK_KILL_PATH_VERSION,
    PHASE11A_STEP,
    PHASE11B_STATUS_NOT_STARTED,
    Phase11aKillPathConfig,
    VERIFY_REPLAY_ACCEPTED,
    VERIFY_REPLAY_REJECTED,
    WRITE_PATH_RUNTIME_MODE_NOT_WIRED,
    WRITE_PATH_STATUS_FALLBACK_USED,
    WRITE_PATH_STATUS_NOT_WIRED,
    WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED,
    execute_phase11a_rollback_kill_path,
    phase11a_rollback_evidence_digest,
    verify_phase11a_rollback_kill_path_evidence,
)


class Phase11aRollbackKillPathTests(unittest.TestCase):
    def test_simulated_wired_path_exception_triggers_fallback_without_crash(self):
        def candidate():
            raise RuntimeError("simulated candidate failure")

        record = execute_phase11a_rollback_kill_path(candidate_wired_path=candidate)

        self.assertEqual(record["record_kind"], PHASE11A_ROLLBACK_KILL_PATH_KIND)
        self.assertEqual(record["record_version"], PHASE11A_ROLLBACK_KILL_PATH_VERSION)
        self.assertTrue(record["write_path_wiring_attempted"])
        self.assertTrue(record["write_path_fallback_triggered"])
        self.assertEqual(record["write_path_wiring_status"], WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED)
        self.assertEqual(record["write_path_fallback_target"], FALLBACK_TARGET_EXISTING_UNWIRED_PATH)
        self.assertEqual(record["candidate_wired_path_result"]["status"], "raised_exception")
        self.assertEqual(record["candidate_wired_path_result"]["exception_type"], "RuntimeError")
        self.assertEqual(record["fallback_result"]["behavior"], "existing_unwired_behavior")
        self.assertEqual(record["fallback_result"]["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertFalse(record["fallback_result"]["write_performed"])

        verify = verify_phase11a_rollback_kill_path_evidence(record)
        self.assertTrue(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_ACCEPTED)

    def test_simulated_wired_path_failure_records_fallback_reason(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(
                success=False,
                reason="candidate returned failure for 11-A-0 simulation",
            )
        )

        self.assertTrue(record["write_path_wiring_attempted"])
        self.assertTrue(record["write_path_fallback_triggered"])
        self.assertEqual(record["write_path_fallback_reason"], "candidate_wired_path_returned_failure")
        self.assertEqual(record["candidate_wired_path_result"]["status"], "returned_failure")
        self.assertEqual(record["candidate_wired_path_result"]["success"], False)
        self.assertEqual(verify_phase11a_rollback_kill_path_evidence(record)["status"], VERIFY_REPLAY_ACCEPTED)

    def test_candidate_wired_path_success_evidence_is_rejected(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(
                success=True,
                reason="candidate returned success outside 11-A-0 scope",
            )
        )

        self.assertTrue(record["write_path_wiring_attempted"])
        self.assertFalse(record["write_path_fallback_triggered"])
        self.assertEqual(record["candidate_wired_path_result"]["success"], True)
        self.assertEqual(record["candidate_wired_path_result"]["status"], "returned_success")

        verify = verify_phase11a_rollback_kill_path_evidence(record)

        self.assert_rejected_with(verify, "candidate wired path success is outside 11-A-0 scope")
        self.assert_rejected_with(verify, "candidate wired path returned success in 11-A-0")

    def test_candidate_success_replay_returns_rejected_for_legacy_fallback_reason(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(success=False, reason="simulated")
        )
        tampered = deepcopy(record)
        tampered["candidate_wired_path_result"] = {
            "attempted": True,
            "success": True,
            "status": "returned_success",
            "reason": "candidate returned success outside 11-A-0 scope",
            "result": {},
        }
        tampered["write_path_fallback_reason"] = "candidate_wired_path_success_not_activated_in_11a0"
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "candidate wired path success is outside 11-A-0 scope")
        self.assert_rejected_with(verify, "candidate wired path returned success in 11-A-0")

    def test_candidate_success_like_status_replay_is_rejected_without_success_bool(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(success=False, reason="simulated")
        )
        tampered = deepcopy(record)
        tampered["candidate_wired_path_result"] = {
            "attempted": True,
            "success": False,
            "status": "returned_success",
            "reason": "status claims success outside 11-A-0 scope",
            "result": {},
        }
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "candidate wired path returned success in 11-A-0")

    def test_fallback_preserves_existing_unwired_behavior(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: {"success": False, "reason": "simulated failure"}
        )

        self.assertEqual(record["write_path_runtime_mode"], WRITE_PATH_RUNTIME_MODE_NOT_WIRED)
        self.assertEqual(record["safe_default"], SAFE_DEFAULT)
        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["fallback_result"]["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertFalse(record["fallback_result"]["write_performed"])

    def test_fallback_evidence_fields_are_present_and_digest_bound(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(success=False, reason="simulated")
        )

        for field in (
            "write_path_mode",
            "write_path_wiring_attempted",
            "write_path_wiring_status",
            "write_path_fallback_triggered",
            "write_path_fallback_reason",
            "write_path_fallback_target",
            "write_path_runtime_mode",
            "safe_default",
            "live_executor_authority",
            "phase11a_step",
            "deterministic_evidence_digest",
        ):
            with self.subTest(field=field):
                self.assertIn(field, record)
        self.assertEqual(record["deterministic_evidence_digest"], phase11a_rollback_evidence_digest(record))

    def test_fallback_evidence_tamper_causes_verify_failure(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(success=False, reason="simulated")
        )
        tampered = deepcopy(record)
        tampered["write_path_fallback_reason"] = "forged"

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "deterministic evidence digest mismatch")

    def test_fallback_target_mismatch_causes_verify_failure_even_when_rebound(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(success=False, reason="simulated")
        )
        tampered = deepcopy(record)
        tampered["write_path_fallback_target"] = "new_runtime_path"
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "write_path_fallback_target mismatch")
        self.assert_rejected_with(verify, "fallback target must remain existing_unwired_path")

    def test_write_path_wiring_status_overclaim_is_rejected(self):
        record = execute_phase11a_rollback_kill_path()
        tampered = deepcopy(record)
        tampered["write_path_wiring_status"] = "ACTIVE"
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "invalid write_path_wiring_status: ACTIVE")

    def test_default_no_wiring_path_remains_not_wired_to_executor_write_path(self):
        record = execute_phase11a_rollback_kill_path()

        self.assertFalse(record["write_path_wiring_attempted"])
        self.assertFalse(record["write_path_fallback_triggered"])
        self.assertEqual(record["write_path_wiring_status"], WRITE_PATH_STATUS_NOT_WIRED)
        self.assertEqual(record["write_path_runtime_mode"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(record["fallback_result"]["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(verify_phase11a_rollback_kill_path_evidence(record)["status"], VERIFY_REPLAY_ACCEPTED)

    def test_known_gap_expected_red_status_is_preserved(self):
        record = execute_phase11a_rollback_kill_path()

        self.assertEqual(record["known_gap_status"], B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)

    def test_live_executor_authority_remains_on_hold(self):
        record = execute_phase11a_rollback_kill_path()

        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["authority_snapshot"]["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)

    def test_phase11a1_wiring_and_phase11b_are_not_started(self):
        record = execute_phase11a_rollback_kill_path()

        self.assertEqual(record["phase11a_step"], PHASE11A_STEP)
        self.assertEqual(record["phase11a1_wiring_status"], PHASE11A1_WIRING_STATUS_NOT_STARTED)
        self.assertEqual(record["phase11b_status"], PHASE11B_STATUS_NOT_STARTED)

    def test_runtime_write_path_active_claim_is_rejected(self):
        record = execute_phase11a_rollback_kill_path()
        tampered = deepcopy(record)
        tampered["write_path_runtime_mode"] = "ACTIVE"
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "write_path_runtime_mode mismatch")

    def test_live_executor_authority_grant_claim_is_rejected(self):
        record = execute_phase11a_rollback_kill_path()
        tampered = deepcopy(record)
        grant_key = "live_executor_authority_" + "granted"
        tampered["live_executor_authority"] = "AUTHORITY_PROMOTED"
        tampered[grant_key] = True
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, f"unexpected evidence record field: {grant_key}")
        self.assert_rejected_with(verify, "live_executor_authority mismatch")
        self.assert_rejected_with(verify, "live executor authority grant claim rejected")

    def test_phase11b_claim_is_rejected(self):
        record = execute_phase11a_rollback_kill_path()
        tampered = deepcopy(record)
        tampered["phase11b_status"] = "STARTED"
        tampered["phase11b_started"] = True
        tampered["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(tampered)

        verify = verify_phase11a_rollback_kill_path_evidence(tampered)

        self.assert_rejected_with(verify, "unexpected evidence record field: phase11b_started")
        self.assert_rejected_with(verify, "phase11b_status mismatch")
        self.assert_rejected_with(verify, "Phase 11-B start claim rejected")

    def test_manual_config_kill_path_uses_existing_unwired_fallback(self):
        record = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(success=False, reason="should be skipped"),
            config=Phase11aKillPathConfig(manual_kill_path_triggered=True),
        )

        self.assertFalse(record["write_path_wiring_attempted"])
        self.assertTrue(record["write_path_fallback_triggered"])
        self.assertEqual(record["write_path_wiring_status"], WRITE_PATH_STATUS_FALLBACK_USED)
        self.assertEqual(record["write_path_fallback_reason"], "manual_kill_path_requested")
        self.assertEqual(record["candidate_wired_path_result"]["status"], "skipped_by_manual_kill_path")
        self.assertEqual(record["fallback_result"]["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(verify_phase11a_rollback_kill_path_evidence(record)["status"], VERIFY_REPLAY_ACCEPTED)

    def test_authority_snapshot_is_current_11a0_snapshot(self):
        self.assertEqual(
            AUTHORITY_SNAPSHOT,
            {
                "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
                "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
                "safe_default": SAFE_DEFAULT,
                "phase11a_step": PHASE11A_STEP,
                "phase11a1_wiring_status": PHASE11A1_WIRING_STATUS_NOT_STARTED,
                "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
            },
        )

    def test_module_has_no_runtime_side_effect_helpers(self):
        source = inspect.getsource(phase11a_rollback_kill_path)
        forbidden_calls = (
            "." + "open(",
            "op" + "en(",
            ".write" + "_text(",
            ".write" + "_bytes(",
            ".to" + "uch(",
            ".mk" + "dir(",
            ".ch" + "mod(",
            "ch" + "mod(",
            ".ch" + "own(",
            "ch" + "own(",
            ".un" + "link(",
            ".re" + "name(",
            ".rep" + "lace(",
            "sub" + "process",
            "socket",
            "requests",
            "http_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def assert_rejected_with(self, verify, expected):
        self.assertFalse(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_REJECTED)
        self.assertIn(expected, verify["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
