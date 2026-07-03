from copy import deepcopy
import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    SAFE_DEFAULT,
)
from src.evidence import phase11a_known_gap_blocked_transition
from src.evidence.phase11a_known_gap_blocked_transition import (
    KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE,
    KNOWN_GAP_EXPECTED_RED_BASELINE,
    PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_KIND,
    PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_VERSION,
    PHASE11A_STEP,
    PHASE11B_STATUS_NOT_STARTED,
    SAVE_RUN_ROUTE_VERIFY_SOURCE_RECOMPUTED_INTERNAL_REPLAY,
    TRANSITION_BASIS_PRELIVE_SAVE_RUN_ROUTE,
    TRANSITION_SOURCE_PHASE,
    VERIFY_REPLAY_ACCEPTED,
    VERIFY_REPLAY_REJECTED,
    build_phase11a_known_gap_blocked_transition_evidence,
    phase11a_known_gap_transition_evidence_digest,
    verify_phase11a_known_gap_blocked_transition_evidence,
)
from src.evidence.phase11a_rollback_kill_path import (
    VERIFY_REPLAY_ACCEPTED as ROLLBACK_VERIFY_REPLAY_ACCEPTED,
    phase11a_rollback_evidence_digest,
    verify_phase11a_rollback_kill_path_evidence,
)
from src.evidence.phase11a_save_run_write_routing import (
    GUARD_DECISION_DENIED,
    SAVE_RUN_ROUTE_ACCEPTED_PRELIVE,
    SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE,
    VERIFY_REPLAY_ACCEPTED as SAVE_RUN_VERIFY_REPLAY_ACCEPTED,
    WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT,
    build_save_run_write_request,
    phase11a_save_run_routing_evidence_digest,
    route_save_run_write_request,
    verify_phase11a_save_run_write_routing_evidence,
)


class Phase11aKnownGapBlockedTransitionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_valid_11a1_route_transitions_expected_red_to_blocked_evidence(self):
        route = self._route()
        record = self._transition(route)

        self.assertEqual(record["record_kind"], PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_KIND)
        self.assertEqual(record["record_version"], PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_VERSION)
        self.assertEqual(record["phase11a_step"], PHASE11A_STEP)
        self.assertEqual(record["prior_known_gap_status"], KNOWN_GAP_EXPECTED_RED_BASELINE)
        self.assertEqual(record["known_gap_transition_status"], KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE)
        self.assertEqual(record["transition_basis"], TRANSITION_BASIS_PRELIVE_SAVE_RUN_ROUTE)
        self.assertEqual(record["transition_source_phase"], TRANSITION_SOURCE_PHASE)
        self.assertTrue(record["save_run_route_evidence_verified"])
        self.assertEqual(record["save_run_route_verify_status"], SAVE_RUN_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(
            record["save_run_route_verify_source"],
            SAVE_RUN_ROUTE_VERIFY_SOURCE_RECOMPUTED_INTERNAL_REPLAY,
        )
        self.assertFalse(record["supplied_route_verify_trusted"])
        self.assertTrue(record["supplied_route_verify_mismatch_rejected"])
        self.assertTrue(record["route_verify_recomputed"])
        self.assertTrue(record["deterministic_attribution_verified"])
        self.assertTrue(record["self_reported_attribution_rejected"])
        self.assertTrue(record["trusted_runtime_self_claim_rejected"])
        self.assertTrue(record["request_source_spoof_rejected"])
        self.assertTrue(record["mediator_actor_mismatch_rejected"])
        self.assertTrue(record["fallback_preserved"])
        self.assertFalse(record["actual_runtime_write_performed"])
        self.assertFalse(record["actual_enforcement_activated"])

    def test_transition_evidence_verifies(self):
        route = self._route()
        record = self._transition(route)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assertTrue(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_ACCEPTED)
        self.assertFalse(verify["is_runtime_wiring"])
        self.assertFalse(verify["is_runtime_enforcement"])
        self.assertEqual(verify["safe_default"], SAFE_DEFAULT)

    def test_invalid_route_with_fake_supplied_accepted_verify_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["deterministic_evidence_digest"] = "bad-digest"
        fake_accepted = self._fake_route_verify(
            accepted=True,
            status=SAVE_RUN_VERIFY_REPLAY_ACCEPTED,
        )
        record = self._transition(tampered, save_run_route_verify=fake_accepted)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
            save_run_route_verify=fake_accepted,
        )

        self.assertFalse(record["save_run_route_evidence_verified"])
        self.assertEqual(record["save_run_route_verify_status"], VERIFY_REPLAY_REJECTED)
        self.assert_rejected_with(verify, "save_run route evidence verify rejected")
        self.assertIn("supplied route verify mismatch rejected", verify["rejection_reasons"])

    def test_invalid_route_without_supplied_verify_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["deterministic_evidence_digest"] = "bad-digest"
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "save_run route evidence verify rejected")

    def test_valid_route_uses_recomputed_internal_verify(self):
        route = self._route()
        record = self._transition(route)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assertTrue(verify["accepted"])
        self.assertEqual(
            record["save_run_route_verify_source"],
            SAVE_RUN_ROUTE_VERIFY_SOURCE_RECOMPUTED_INTERNAL_REPLAY,
        )
        self.assertEqual(record["source_route_verify"]["status"], SAVE_RUN_VERIFY_REPLAY_ACCEPTED)

    def test_valid_route_with_fake_supplied_rejected_verify_rejects_as_mismatch(self):
        route = self._route()
        fake_rejected = self._fake_route_verify(
            accepted=False,
            status=VERIFY_REPLAY_REJECTED,
        )
        record = self._transition(route, save_run_route_verify=fake_rejected)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
            save_run_route_verify=fake_rejected,
        )

        self.assertFalse(record["supplied_route_verify_trusted"])
        self.assert_rejected_with(verify, "supplied route verify mismatch rejected")

    def test_embedded_route_verify_tamper_rejects(self):
        route = self._route()
        record = self._record_with(
            self._transition(route),
            source_route_verify={
                "accepted": True,
                "status": VERIFY_REPLAY_REJECTED,
                "verification_scope": "caller_supplied",
                "safe_default": SAFE_DEFAULT,
            },
        )

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "source_route_verify mismatch")

    def test_save_run_route_verify_source_mismatch_rejects(self):
        route = self._route()
        record = self._record_with(
            self._transition(route),
            save_run_route_verify_source="caller_supplied",
        )

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "save_run_route_verify_source mismatch")

    def test_supplied_route_verify_trusted_true_rejects(self):
        route = self._route()
        record = self._record_with(self._transition(route), supplied_route_verify_trusted=True)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "supplied_route_verify_trusted mismatch")

    def test_route_verify_recomputed_false_rejects(self):
        route = self._route()
        record = self._record_with(self._transition(route), route_verify_recomputed=False)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "route_verify_recomputed mismatch")

    def test_supplied_route_verify_mismatch_rejected_false_rejects(self):
        route = self._route()
        record = self._record_with(
            self._transition(route),
            supplied_route_verify_mismatch_rejected=False,
        )

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "supplied_route_verify_mismatch_rejected mismatch")

    def test_prior_known_gap_mismatch_rejects(self):
        route = self._route()
        record = self._transition(route, prior_known_gap_status="OTHER_BASELINE")

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "prior known-gap status mismatch")

    def test_missing_deterministic_attribution_rejects(self):
        route = self._route()
        tampered = self._route_with(route, write_attribution_basis="request_payload")
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "deterministic attribution missing or mismatch")

    def test_self_reported_attribution_accepted_state_rejects(self):
        route = self._route()
        tampered = self._route_with(route, write_attribution_is_self_reported=True)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "self-reported attribution accepted state rejected")

    def test_trusted_runtime_self_claim_accepted_state_rejects(self):
        route = self._route()
        tampered = self._route_with(route, trusted_runtime_claim_allowed=True)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "trusted runtime self-claim accepted state rejected")

    def test_request_source_spoof_acceptance_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["request"]["request_source"] = "caller_supplied_source"
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "request_source spoof accepted state rejected")

    def test_mediator_actor_mismatch_acceptance_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["mediator_request"]["actor"] = "caller_supplied_actor"
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "mediator actor mismatch accepted state rejected")

    def test_invalid_11a1_route_evidence_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["deterministic_evidence_digest"] = "bad-digest"
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "save_run route evidence verify rejected")

    def test_route_target_mismatch_rejects(self):
        route = self._route()
        tampered = self._route_with(route, save_run_route_target="other_target")
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "route target mismatch")

    def test_guard_decision_mismatch_rejects(self):
        route = self._route()
        tampered = self._route_with(route, guard_decision_status="ALLOW")
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "guard decision mismatch")

    def test_fallback_invalid_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["fallback_evidence"]["fallback_result"]["write_performed"] = True
        tampered["fallback_evidence"]["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(
            tampered["fallback_evidence"]
        )
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "fallback evidence invalid")

    def test_candidate_success_accepted_as_rollback_evidence_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["fallback_evidence"]["candidate_wired_path_result"] = {
            "attempted": True,
            "success": True,
            "status": "returned_success",
            "reason": "candidate success must not prove 11-A-0 rollback",
            "result": {},
        }
        tampered["fallback_evidence"]["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(
            tampered["fallback_evidence"]
        )
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "candidate success accepted as 11-A-0 rollback evidence rejected")

    def test_runtime_write_authority_grant_claim_rejects(self):
        route = self._route()
        grant_key = "runtime_write_authority_" + "granted"
        tampered = self._route_with(route, **{grant_key: True})
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "runtime write authority grant claim rejected")

    def test_live_executor_authority_grant_claim_rejects(self):
        route = self._route()
        grant_key = "live_executor_authority_" + "granted"
        tampered = self._route_with(route, live_executor_authority="PROMOTED", **{grant_key: True})
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "live executor authority grant claim rejected")

    def test_phase11b_claim_rejects(self):
        route = self._route()
        tampered = self._route_with(route, phase11b_status="STARTED", phase11b_started=True)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "Phase 11-B start claim rejected")

    def test_actual_enforcement_claim_rejects(self):
        route = self._route()
        tampered = self._route_with(route, actual_enforcement_active=True)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "actual enforcement activation claim rejected")

    def test_actual_runtime_write_claim_rejects(self):
        route = self._route()
        tampered = deepcopy(route)
        tampered["route_result"]["write_performed"] = True
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        record = self._transition(tampered)

        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            record,
            save_run_route_evidence=tampered,
        )

        self.assert_rejected_with(verify, "actual runtime write claim rejected")

    def test_11a0_preservation_still_passes(self):
        route = self._route()

        fallback_verify = verify_phase11a_rollback_kill_path_evidence(route["fallback_evidence"])

        self.assertEqual(fallback_verify["status"], ROLLBACK_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(
            route["fallback_evidence"]["fallback_result"]["runtime_write_path"],
            NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        )

    def test_11a1_preservation_still_passes(self):
        route = self._route()

        route_verify = verify_phase11a_save_run_write_routing_evidence(route)

        self.assertEqual(route_verify["status"], SAVE_RUN_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(route["save_run_route_status"], SAVE_RUN_ROUTE_ACCEPTED_PRELIVE)
        self.assertEqual(route["save_run_route_target"], SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE)
        self.assertEqual(route["guard_decision_status"], GUARD_DECISION_DENIED)
        self.assertEqual(route["write_attribution_basis"], WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT)

    def test_authority_statuses_remain_held(self):
        route = self._route()
        record = self._transition(route)

        self.assertEqual(record["runtime_write_path_status"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["phase11b_status"], PHASE11B_STATUS_NOT_STARTED)
        self.assertEqual(record["safe_default"], SAFE_DEFAULT)
        self.assertFalse(record["live_executor_implemented"])
        self.assertFalse(record["tool_authority_granted"])
        self.assertFalse(record["provider_model_network_authority_granted"])

    def test_transition_evidence_digest_is_bound(self):
        route = self._route()
        record = self._transition(route)

        self.assertEqual(
            record["deterministic_evidence_digest"],
            phase11a_known_gap_transition_evidence_digest(record),
        )

        tampered = deepcopy(record)
        tampered["transition_basis"] = "other_basis"
        verify = verify_phase11a_known_gap_blocked_transition_evidence(
            tampered,
            save_run_route_evidence=route,
        )

        self.assert_rejected_with(verify, "deterministic evidence digest mismatch")

    def test_module_does_not_add_runtime_side_effect_helpers(self):
        source = inspect.getsource(phase11a_known_gap_blocked_transition)
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

    def _route(self):
        request = build_save_run_write_request(
            run_id="run-11a2",
            target_filename="run.json",
            payload='{"status":"fixture only"}',
            payload_metadata={"source": "phase11a2_test_double"},
            request_id="phase11a-known-gap-transition-test-request",
        )
        return route_save_run_write_request(repo_root=self.repo, request=request)

    def _transition(
        self,
        route,
        prior_known_gap_status=KNOWN_GAP_EXPECTED_RED_BASELINE,
        save_run_route_verify=None,
    ):
        return build_phase11a_known_gap_blocked_transition_evidence(
            prior_known_gap_status=prior_known_gap_status,
            save_run_route_evidence=route,
            save_run_route_verify=save_run_route_verify,
        )

    def _route_with(self, route, **changes):
        tampered = deepcopy(route)
        tampered.update(changes)
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        return tampered

    def _record_with(self, record, **changes):
        tampered = deepcopy(record)
        tampered.update(changes)
        tampered["deterministic_evidence_digest"] = phase11a_known_gap_transition_evidence_digest(tampered)
        return tampered

    def _fake_route_verify(self, *, accepted, status):
        return {
            "accepted": accepted,
            "status": status,
            "rejection_reasons": [],
            "verification_scope": "phase11a_save_run_write_routing_replay_only",
            "is_runtime_wiring": False,
            "is_runtime_enforcement": False,
            "safe_default": SAFE_DEFAULT,
        }

    def assert_rejected_with(self, verify, expected):
        self.assertFalse(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_REJECTED)
        self.assertIn(expected, verify["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
