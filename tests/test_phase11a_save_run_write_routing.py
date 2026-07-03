from copy import deepcopy
import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    NOT_WIRED_TO_WRITE_PATH,
    SAFE_DEFAULT,
)
from src.evidence import phase11a_save_run_write_routing
from src.evidence.phase11a_rollback_kill_path import (
    VERIFY_REPLAY_REJECTED as ROLLBACK_VERIFY_REPLAY_REJECTED,
    verify_phase11a_rollback_kill_path_evidence,
)
from src.evidence.phase11a_save_run_write_routing import (
    GUARD_DECISION_DENIED,
    PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND,
    PHASE11A_SAVE_RUN_WRITE_ROUTING_VERSION,
    PHASE11A_STEP,
    PHASE11B_STATUS_NOT_STARTED,
    RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY,
    SAVE_RUN_ROUTE_ACCEPTED_PRELIVE,
    SAVE_RUN_ROUTE_FAILED_FALLBACK_USED,
    SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK,
    SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE,
    VERIFY_REPLAY_ACCEPTED,
    VERIFY_REPLAY_REJECTED,
    build_save_run_write_request,
    phase11a_save_run_routing_evidence_digest,
    route_save_run_write_request,
    verify_phase11a_save_run_write_routing_evidence,
)


class Phase11aSaveRunWriteRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_save_run_request_routes_through_guard_mediator_compatible_adapter(self):
        record = self._route()

        self.assertEqual(record["record_kind"], PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND)
        self.assertEqual(record["record_version"], PHASE11A_SAVE_RUN_WRITE_ROUTING_VERSION)
        self.assertEqual(record["phase11a_step"], PHASE11A_STEP)
        self.assertTrue(record["save_run_route_attempted"])
        self.assertEqual(record["save_run_route_status"], SAVE_RUN_ROUTE_ACCEPTED_PRELIVE)
        self.assertEqual(record["save_run_route_target"], SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE)
        self.assertTrue(record["mediator_route_used"])
        self.assertEqual(record["guard_decision_status"], GUARD_DECISION_DENIED)
        self.assertEqual(record["mediator_decision"]["decision_status"], MEDIATOR_DECISION_DENY)
        self.assertEqual(record["mediator_decision"]["write_path_status"], NOT_WIRED_TO_WRITE_PATH)
        self.assertFalse(record["fallback_triggered"])
        self.assertFalse(record["mediator_decision"]["write_performed"])

    def test_route_evidence_fields_are_present(self):
        record = self._route()

        for field in (
            "phase11a_step",
            "save_run_route_attempted",
            "save_run_route_status",
            "save_run_route_target",
            "mediator_route_used",
            "guard_decision_status",
            "fallback_available",
            "fallback_triggered",
            "fallback_reason",
            "runtime_write_path_status",
            "live_executor_authority",
            "phase11b_status",
            "safe_default",
            "deterministic_evidence_digest",
        ):
            with self.subTest(field=field):
                self.assertIn(field, record)
        self.assertEqual(
            record["deterministic_evidence_digest"],
            phase11a_save_run_routing_evidence_digest(record),
        )

    def test_valid_pre_live_accepted_route_verifies(self):
        record = self._route()

        verify = verify_phase11a_save_run_write_routing_evidence(record)

        self.assertTrue(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_ACCEPTED)
        self.assertFalse(verify["is_runtime_wiring"])
        self.assertFalse(verify["is_runtime_enforcement"])
        self.assertEqual(verify["safe_default"], SAFE_DEFAULT)

    def test_route_target_mismatch_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        tampered["save_run_route_target"] = "other_route"
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, "save_run_route_target mismatch")

    def test_guard_decision_mismatch_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        tampered["guard_decision_status"] = "ALLOW"
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, "guard_decision_status mismatch")

    def test_route_status_overclaim_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        tampered["save_run_route_status"] = "WRITE_" + "PATH_WIRED"
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, f"invalid save_run_route_status: {'WRITE_' + 'PATH_WIRED'}")
        self.assert_rejected_with(verify, "save_run routing overclaim rejected")

    def test_simulated_route_failure_triggers_11a0_fallback(self):
        record = self._route(mediator_route=lambda request: {"status": "failed", "success": False})

        self.assertEqual(record["save_run_route_status"], SAVE_RUN_ROUTE_FAILED_FALLBACK_USED)
        self.assertEqual(record["save_run_route_target"], SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK)
        self.assertTrue(record["fallback_triggered"])
        self.assertEqual(record["fallback_reason"], "save_run_route_failed")
        self.assertEqual(record["fallback_verify"]["status"], VERIFY_REPLAY_ACCEPTED)

        verify = verify_phase11a_save_run_write_routing_evidence(
            record,
            expected_route_target=SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK,
            expected_fallback_triggered=True,
        )
        self.assertEqual(verify["status"], VERIFY_REPLAY_ACCEPTED)

    def test_simulated_route_exception_triggers_11a0_fallback(self):
        def raises(_request):
            raise RuntimeError("simulated route exception")

        record = self._route(mediator_route=raises)

        self.assertEqual(record["save_run_route_status"], SAVE_RUN_ROUTE_FAILED_FALLBACK_USED)
        self.assertTrue(record["fallback_triggered"])
        self.assertEqual(record["fallback_reason"], "save_run_route_exception")
        self.assertEqual(record["route_result"]["status"], "raised_exception")
        self.assertEqual(record["fallback_verify"]["status"], VERIFY_REPLAY_ACCEPTED)

        verify = verify_phase11a_save_run_write_routing_evidence(
            record,
            expected_route_target=SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK,
            expected_fallback_triggered=True,
        )
        self.assertEqual(verify["status"], VERIFY_REPLAY_ACCEPTED)

    def test_fallback_evidence_remains_valid(self):
        record = self._route(mediator_route=lambda request: {"status": "failed", "success": False})

        fallback_verify = verify_phase11a_rollback_kill_path_evidence(record["fallback_evidence"])

        self.assertTrue(fallback_verify["accepted"])
        self.assertEqual(fallback_verify["status"], VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(
            record["fallback_evidence"]["fallback_result"]["runtime_write_path"],
            NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        )

    def test_candidate_wired_success_is_not_accepted_as_11a0_rollback_evidence(self):
        record = self._route()

        rollback_verify = verify_phase11a_rollback_kill_path_evidence(record)

        self.assertFalse(rollback_verify["accepted"])
        self.assertEqual(rollback_verify["status"], ROLLBACK_VERIFY_REPLAY_REJECTED)

    def test_known_gap_expected_red_status_remains_preserved(self):
        record = self._route()

        self.assertEqual(record["known_gap_status"], B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
        self.assertEqual(
            record["fallback_evidence"]["known_gap_status"],
            B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
        )

    def test_runtime_authority_is_not_granted(self):
        record = self._route()

        self.assertEqual(record["runtime_write_path_status"], RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY)
        self.assertEqual(record["runtime_write_path_status"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertFalse(record["request"]["write_performed"])
        self.assertFalse(record["guard_decision"]["write_performed"])
        self.assertFalse(record["mediator_decision"]["write_performed"])

    def test_live_executor_authority_remains_on_hold(self):
        record = self._route()

        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["authority_snapshot"]["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)

    def test_phase11b_remains_not_started(self):
        record = self._route()

        self.assertEqual(record["phase11b_status"], PHASE11B_STATUS_NOT_STARTED)
        self.assertEqual(record["authority_snapshot"]["phase11b_status"], PHASE11B_STATUS_NOT_STARTED)

    def test_fallback_field_mismatch_rejects(self):
        record = self._route(mediator_route=lambda request: {"status": "failed", "success": False})
        tampered = deepcopy(record)
        tampered["fallback_triggered"] = False
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(
            tampered,
            expected_route_target=SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK,
            expected_fallback_triggered=True,
        )

        self.assert_rejected_with(verify, "fallback_triggered mismatch")
        self.assert_rejected_with(verify, "FAILED_FALLBACK_USED status requires attempted mediator route and fallback")

    def test_runtime_authority_overclaim_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        grant_key = "runtime_write_authority_" + "granted"
        tampered[grant_key] = bool(1)
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, f"unexpected evidence record field: {grant_key}")
        self.assert_rejected_with(verify, "runtime write authority grant claim rejected")

    def test_live_executor_authority_grant_claim_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        tampered["live_executor_authority"] = "PROMOTED"
        grant_key = "live_executor_authority_" + "granted"
        tampered[grant_key] = bool(1)
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, "live_executor_authority mismatch")
        self.assert_rejected_with(verify, "live executor authority grant claim rejected")

    def test_phase11b_claim_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        tampered["phase11b_status"] = "STARTED"
        tampered["phase11b_started"] = True
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, "phase11b_status mismatch")
        self.assert_rejected_with(verify, "Phase 11-B start claim rejected")

    def test_save_run_routing_overclaim_rejects(self):
        record = self._route()
        tampered = deepcopy(record)
        wired_key = "save_run_write_path_" + "wired"
        tampered[wired_key] = bool(1)
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)

        verify = verify_phase11a_save_run_write_routing_evidence(tampered)

        self.assert_rejected_with(verify, "save_run routing overclaim rejected")

    def test_module_does_not_add_runtime_side_effect_helpers(self):
        source = inspect.getsource(phase11a_save_run_write_routing)
        forbidden_calls = (
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".chmod(",
            "chmod(",
            ".chown(",
            "chown(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "subprocess",
            "socket",
            "requests",
            "http_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _route(self, mediator_route=None):
        request = build_save_run_write_request(
            run_id="run-11a1",
            target_filename="run.json",
            payload='{"status":"fixture only"}',
            payload_metadata={"source": "phase11a_test_double"},
            request_id="phase11a-save-run-test-request",
        )
        return route_save_run_write_request(
            repo_root=self.repo,
            request=request,
            mediator_route=mediator_route,
        )

    def assert_rejected_with(self, verify, expected):
        self.assertFalse(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_REJECTED)
        self.assertIn(expected, verify["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
