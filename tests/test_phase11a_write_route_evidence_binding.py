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
from src.evidence import phase11a_write_route_evidence_binding
from src.evidence.phase11a_known_gap_blocked_transition import (
    KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE,
    KNOWN_GAP_EXPECTED_RED_BASELINE,
    VERIFY_REPLAY_ACCEPTED as KNOWN_GAP_VERIFY_REPLAY_ACCEPTED,
    build_phase11a_known_gap_blocked_transition_evidence,
    phase11a_known_gap_transition_evidence_digest,
    verify_phase11a_known_gap_blocked_transition_evidence,
)
from src.evidence.phase11a_rollback_kill_path import (
    CandidateWiredPathResult,
    VERIFY_REPLAY_ACCEPTED as ROLLBACK_VERIFY_REPLAY_ACCEPTED,
    execute_phase11a_rollback_kill_path,
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
from src.evidence.phase11a_write_route_evidence_binding import (
    BINDING_BASIS_PHASE11A_PRELIVE_CROSS_DIGEST_REPLAY,
    EVIDENCE_BINDING_ACCEPTED,
    PHASE11A_STEP,
    PHASE11A_WRITE_ROUTE_EVIDENCE_BINDING_KIND,
    PHASE11A_WRITE_ROUTE_EVIDENCE_BINDING_VERSION,
    PHASE11B_STATUS_NOT_STARTED,
    SOURCE_EVIDENCE_VERIFY_REJECTED,
    SOURCE_VERIFY_RECOMPUTED_INTERNAL_REPLAY,
    build_phase11a_write_route_evidence_binding,
    phase11a_write_route_evidence_binding_digest,
    verify_phase11a_write_route_evidence_binding,
)


class Phase11aWriteRouteEvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_valid_11a0_11a1_11a2_chain_binds_and_verifies(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        verify = self._verify(record, source0, source1, source2)

        self.assertTrue(verify["accepted"])
        self.assertEqual(verify["status"], EVIDENCE_BINDING_ACCEPTED)
        self.assertEqual(record["phase11a_step"], PHASE11A_STEP)
        self.assertEqual(record["binding_record_kind"], PHASE11A_WRITE_ROUTE_EVIDENCE_BINDING_KIND)
        self.assertEqual(record["binding_version"], PHASE11A_WRITE_ROUTE_EVIDENCE_BINDING_VERSION)
        self.assertEqual(record["binding_basis"], BINDING_BASIS_PHASE11A_PRELIVE_CROSS_DIGEST_REPLAY)
        self.assertEqual(record["phase11a0_verify_status"], ROLLBACK_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(record["phase11a1_verify_status"], SAVE_RUN_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(record["phase11a2_verify_status"], KNOWN_GAP_VERIFY_REPLAY_ACCEPTED)
        self.assertTrue(record["source_verify_recomputed"])
        self.assertEqual(record["source_verify_source"], SOURCE_VERIFY_RECOMPUTED_INTERNAL_REPLAY)
        self.assertFalse(record["supplied_verify_trusted"])
        self.assertTrue(record["cross_digest_binding_valid"])
        self.assertTrue(record["deterministic_attribution_preserved"])
        self.assertTrue(record["known_gap_blocked_transition_preserved"])
        self.assertTrue(record["fallback_preserved"])
        self.assertEqual(record["runtime_write_path_status"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["phase11b_status"], PHASE11B_STATUS_NOT_STARTED)
        self.assertEqual(record["safe_default"], SAFE_DEFAULT)
        self.assertFalse(record["actual_runtime_write_performed"])
        self.assertFalse(record["actual_enforcement_activated"])

    def test_source_11a0_tamper_rejects(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        tampered0 = deepcopy(source0)
        tampered0["fallback_result"]["write_performed"] = True

        verify = self._verify(record, tampered0, source1, source2)

        self.assert_rejected_with(verify, "source 11-A-0 evidence digest mismatch")
        self.assert_rejected_with(verify, "source 11-A-0 evidence verify rejected")

    def test_source_11a1_tamper_rejects(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        tampered1 = deepcopy(source1)
        tampered1["save_run_route_target"] = "other_route"

        verify = self._verify(record, source0, tampered1, source2)

        self.assert_rejected_with(verify, "source 11-A-1 evidence digest mismatch")
        self.assert_rejected_with(verify, "source 11-A-1 evidence verify rejected")

    def test_source_11a2_tamper_rejects(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        tampered2 = deepcopy(source2)
        tampered2["known_gap_transition_status"] = "OTHER_TRANSITION"

        verify = self._verify(record, source0, source1, tampered2)

        self.assert_rejected_with(verify, "source 11-A-2 evidence digest mismatch")
        self.assert_rejected_with(verify, "source 11-A-2 evidence verify rejected")

    def test_source_digest_mismatch_rejects(self):
        source0, source1, source2 = self._chain()
        record = deepcopy(self._binding(source0, source1, source2))
        record["source_phase11a1_digest"] = "bad-digest"
        record["deterministic_evidence_digest"] = phase11a_write_route_evidence_binding_digest(record)

        verify = self._verify(record, source0, source1, source2)

        self.assert_rejected_with(verify, "source 11-A-1 evidence digest mismatch")

    def test_supplied_verify_object_is_not_trusted(self):
        source0, source1, source2 = self._chain()
        supplied0 = verify_phase11a_rollback_kill_path_evidence(source0)
        supplied1 = verify_phase11a_save_run_write_routing_evidence(source1)
        supplied2 = verify_phase11a_known_gap_blocked_transition_evidence(
            source2,
            save_run_route_evidence=source1,
        )

        record = self._binding(
            source0,
            source1,
            source2,
            supplied_phase11a0_verify=supplied0,
            supplied_phase11a1_verify=supplied1,
            supplied_phase11a2_verify=supplied2,
        )
        verify = self._verify(
            record,
            source0,
            source1,
            source2,
            supplied_phase11a0_verify=supplied0,
            supplied_phase11a1_verify=supplied1,
            supplied_phase11a2_verify=supplied2,
        )

        self.assertTrue(verify["accepted"])
        self.assertFalse(record["supplied_verify_trusted"])
        self.assertTrue(record["source_verify_recomputed"])

    def test_fake_source_verify_accepted_object_cannot_pass_invalid_source_evidence(self):
        source0, source1, source2 = self._chain()
        tampered1 = deepcopy(source1)
        tampered1["deterministic_evidence_digest"] = "bad-digest"
        fake_accepted = self._fake_verify(status=SAVE_RUN_VERIFY_REPLAY_ACCEPTED)

        record = self._binding(
            source0,
            tampered1,
            source2,
            supplied_phase11a1_verify=fake_accepted,
        )
        verify = self._verify(
            record,
            source0,
            tampered1,
            source2,
            supplied_phase11a1_verify=fake_accepted,
        )

        self.assertEqual(record["binding_status"], SOURCE_EVIDENCE_VERIFY_REJECTED)
        self.assert_rejected_with(verify, "source 11-A-1 evidence verify rejected")
        self.assert_rejected_with(verify, "supplied verify mismatch rejected")

    def test_11a2_supplied_verify_bypass_remains_rejected(self):
        source0, source1, _source2 = self._chain()
        tampered1 = deepcopy(source1)
        tampered1["deterministic_evidence_digest"] = "bad-digest"
        fake_accepted = self._fake_verify(status=SAVE_RUN_VERIFY_REPLAY_ACCEPTED)
        source2 = build_phase11a_known_gap_blocked_transition_evidence(
            prior_known_gap_status=KNOWN_GAP_EXPECTED_RED_BASELINE,
            save_run_route_evidence=tampered1,
            save_run_route_verify=fake_accepted,
        )

        record = self._binding(
            source0,
            tampered1,
            source2,
            supplied_phase11a1_verify=fake_accepted,
        )
        verify = self._verify(
            record,
            source0,
            tampered1,
            source2,
            supplied_phase11a1_verify=fake_accepted,
        )

        self.assert_rejected_with(verify, "source 11-A-1 evidence verify rejected")
        self.assert_rejected_with(verify, "source 11-A-2 evidence verify rejected")
        self.assert_rejected_with(verify, "supplied verify mismatch rejected")

    def test_deterministic_attribution_mismatch_rejects(self):
        source0, source1, _source2 = self._chain()
        tampered1 = self._source1_with(source1, write_attribution_basis="caller_payload")
        source2 = self._transition(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "deterministic attribution missing or mismatch")

    def test_self_reported_attribution_accepted_state_rejects(self):
        source0, source1, _source2 = self._chain()
        tampered1 = self._source1_with(source1, write_attribution_is_self_reported=True)
        source2 = self._transition(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "deterministic attribution missing or mismatch")
        self.assert_rejected_with(verify, "self-reported attribution accepted state rejected")

    def test_trusted_runtime_self_claim_accepted_state_rejects(self):
        source0, source1, _source2 = self._chain()
        tampered1 = self._source1_with(source1, trusted_runtime_claim_allowed=True)
        source2 = self._transition(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "deterministic attribution missing or mismatch")
        self.assert_rejected_with(verify, "trusted runtime self-claim accepted state rejected")

    def test_request_source_spoof_acceptance_rejects(self):
        source0, source1, _source2 = self._chain()
        tampered1 = deepcopy(source1)
        tampered1["request"]["request_source"] = "caller_supplied_source"
        tampered1["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered1)
        source2 = self._transition(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "deterministic attribution missing or mismatch")
        self.assert_rejected_with(verify, "request_source spoof accepted state rejected")

    def test_mediator_actor_mismatch_acceptance_rejects(self):
        source0, source1, _source2 = self._chain()
        tampered1 = deepcopy(source1)
        tampered1["mediator_request"]["actor"] = "caller_supplied_actor"
        tampered1["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered1)
        source2 = self._transition(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "deterministic attribution missing or mismatch")
        self.assert_rejected_with(verify, "mediator actor mismatch accepted state rejected")

    def test_candidate_success_accepted_as_11a0_rollback_evidence_rejects(self):
        _source0, source1, _source2 = self._chain()
        source0 = execute_phase11a_rollback_kill_path(
            candidate_wired_path=lambda: CandidateWiredPathResult(
                success=True,
                reason="candidate success must remain outside 11-A-0 proof",
            )
        )
        tampered1 = deepcopy(source1)
        tampered1["fallback_evidence"] = deepcopy(source0)
        tampered1["fallback_verify"] = {
            "accepted": True,
            "status": ROLLBACK_VERIFY_REPLAY_ACCEPTED,
            "verification_scope": "phase11a_rollback_kill_path_replay_only",
        }
        tampered1["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered1)
        source2 = self._transition(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "candidate success accepted as 11-A-0 rollback evidence rejected")
        self.assert_rejected_with(verify, "source 11-A-0 evidence verify rejected")

    def test_known_gap_transition_mismatch_rejects(self):
        source0, source1, source2 = self._chain()
        tampered2 = deepcopy(source2)
        tampered2["known_gap_transition_status"] = "KNOWN_GAP_TRANSITION_REJECTED"
        tampered2["deterministic_evidence_digest"] = phase11a_known_gap_transition_evidence_digest(tampered2)
        verify = self._verify(self._binding(source0, source1, tampered2), source0, source1, tampered2)

        self.assert_rejected_with(verify, "known-gap blocked transition missing or mismatch")
        self.assert_rejected_with(verify, "source 11-A-2 evidence verify rejected")

    def test_runtime_write_authority_grant_claim_rejects(self):
        source0, source1, source2 = self._chain()
        grant_key = "runtime_write_authority_" + "granted"
        tampered1 = self._source1_with(source1, **{grant_key: True})
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "runtime write authority grant claim rejected")

    def test_live_executor_authority_grant_claim_rejects(self):
        source0, source1, source2 = self._chain()
        grant_key = "live_executor_authority_" + "granted"
        tampered1 = self._source1_with(source1, live_executor_authority="PROMOTED", **{grant_key: True})
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "live executor authority grant claim rejected")

    def test_phase11b_claim_rejects(self):
        source0, source1, source2 = self._chain()
        tampered2 = deepcopy(source2)
        tampered2["phase11b_status"] = "STARTED"
        tampered2["phase11b_started"] = True
        tampered2["deterministic_evidence_digest"] = phase11a_known_gap_transition_evidence_digest(tampered2)
        verify = self._verify(self._binding(source0, source1, tampered2), source0, source1, tampered2)

        self.assert_rejected_with(verify, "Phase 11-B start claim rejected")

    def test_actual_runtime_write_claim_rejects(self):
        source0, source1, source2 = self._chain()
        tampered1 = deepcopy(source1)
        tampered1["route_result"]["write_performed"] = True
        tampered1["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered1)
        verify = self._verify(self._binding(source0, tampered1, source2), source0, tampered1, source2)

        self.assert_rejected_with(verify, "actual runtime write claim rejected")

    def test_actual_enforcement_claim_rejects(self):
        source0, source1, source2 = self._chain()
        tampered2 = deepcopy(source2)
        tampered2["actual_enforcement_activated"] = True
        tampered2["deterministic_evidence_digest"] = phase11a_known_gap_transition_evidence_digest(tampered2)
        verify = self._verify(self._binding(source0, source1, tampered2), source0, source1, tampered2)

        self.assert_rejected_with(verify, "actual enforcement claim rejected")

    def test_os_filesystem_sandbox_container_hardening_claim_rejects(self):
        source0, source1, source2 = self._chain()
        record = deepcopy(self._binding(source0, source1, source2))
        record["os_filesystem_sandbox_container_hardening_claimed"] = True
        record["deterministic_evidence_digest"] = phase11a_write_route_evidence_binding_digest(record)

        verify = self._verify(record, source0, source1, source2)

        self.assert_rejected_with(verify, "OS/filesystem/sandbox/container hardening claim rejected")

    def test_11a0_preservation_test_passes(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        rollback_verify = verify_phase11a_rollback_kill_path_evidence(source0)

        self.assertEqual(rollback_verify["status"], ROLLBACK_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(source0["fallback_result"]["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertTrue(record["fallback_preserved"])

    def test_11a1_preservation_test_passes(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        route_verify = verify_phase11a_save_run_write_routing_evidence(source1)

        self.assertEqual(route_verify["status"], SAVE_RUN_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(source1["save_run_route_status"], SAVE_RUN_ROUTE_ACCEPTED_PRELIVE)
        self.assertEqual(source1["save_run_route_target"], SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE)
        self.assertEqual(source1["guard_decision_status"], GUARD_DECISION_DENIED)
        self.assertEqual(source1["write_attribution_basis"], WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT)
        self.assertTrue(record["deterministic_attribution_preserved"])

    def test_11a2_preservation_test_passes(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)
        transition_verify = verify_phase11a_known_gap_blocked_transition_evidence(
            source2,
            save_run_route_evidence=source1,
        )

        self.assertEqual(transition_verify["status"], KNOWN_GAP_VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(source2["known_gap_transition_status"], KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE)
        self.assertTrue(record["known_gap_blocked_transition_preserved"])

    def test_binding_digest_is_bound(self):
        source0, source1, source2 = self._chain()
        record = self._binding(source0, source1, source2)

        self.assertEqual(
            record["deterministic_evidence_digest"],
            phase11a_write_route_evidence_binding_digest(record),
        )

        tampered = deepcopy(record)
        tampered["binding_basis"] = "other_basis"
        verify = self._verify(tampered, source0, source1, source2)

        self.assert_rejected_with(verify, "deterministic evidence digest mismatch")

    def test_module_does_not_add_runtime_side_effect_helpers(self):
        source = inspect.getsource(phase11a_write_route_evidence_binding)
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

    def _chain(self):
        source1 = self._route()
        source0 = deepcopy(source1["fallback_evidence"])
        source2 = self._transition(source1)
        return source0, source1, source2

    def _route(self):
        request = build_save_run_write_request(
            run_id="run-11a3",
            target_filename="run.json",
            payload='{"status":"fixture only"}',
            payload_metadata={"source": "phase11a3_test_double"},
            request_id="phase11a-write-route-binding-test-request",
        )
        return route_save_run_write_request(repo_root=self.repo, request=request)

    def _transition(self, route):
        return build_phase11a_known_gap_blocked_transition_evidence(
            prior_known_gap_status=KNOWN_GAP_EXPECTED_RED_BASELINE,
            save_run_route_evidence=route,
        )

    def _binding(self, source0, source1, source2, **kwargs):
        return build_phase11a_write_route_evidence_binding(
            phase11a0_evidence=source0,
            phase11a1_evidence=source1,
            phase11a2_evidence=source2,
            **kwargs,
        )

    def _verify(self, record, source0, source1, source2, **kwargs):
        return verify_phase11a_write_route_evidence_binding(
            record,
            phase11a0_evidence=source0,
            phase11a1_evidence=source1,
            phase11a2_evidence=source2,
            **kwargs,
        )

    def _source1_with(self, source1, **changes):
        tampered = deepcopy(source1)
        tampered.update(changes)
        tampered["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(tampered)
        return tampered

    def _fake_verify(self, *, accepted=True, status=SAVE_RUN_VERIFY_REPLAY_ACCEPTED):
        return {
            "accepted": accepted,
            "status": status,
            "verification_scope": "caller_supplied",
            "safe_default": SAFE_DEFAULT,
        }

    def assert_rejected_with(self, verify, expected):
        self.assertFalse(verify["accepted"])
        self.assertIn(expected, verify["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
