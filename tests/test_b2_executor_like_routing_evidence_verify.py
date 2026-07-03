import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    B2_AEG_PROTECTED_TARGET_ROUTED,
    B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    B2_ROUTED_DENIAL,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
)
from src.evidence.b2_executor_like_ingress_harness import (
    B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
    B2_REMAINS_OPEN_NOT_FULLY_ROUTED,
    B3_NOT_STARTED,
    build_fixture_executor_like_ingress_request,
    route_fixture_executor_like_ingress_through_router,
)
from src.evidence.b2_executor_like_routing_evidence import (
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_COMPONENT,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_NOT_EXTERNAL_ORACLE,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_REJECTED,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_ONLY_SCOPE,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION,
    B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION,
    B2_ROUTING_B1_REPLAY_REJECTED,
    B2_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED,
    B2_ROUTING_FIELD_MISMATCH_REJECTED,
    B2_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED,
    B2_ROUTING_NO_MUTATION_MISMATCH_REJECTED,
    B2_ROUTING_OVERCLAIM_REJECTED,
    B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED,
    build_b2_executor_like_routing_evidence_record,
    verify_b2_executor_like_routing_evidence_record,
)


class B2RoutingEvidenceFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.work = self.repo / "work"
        self.aeg = self.repo / ".aeg"
        self.ledger = self.aeg / "ledger.jsonl"
        self.evidence_packet = self.aeg / "runs" / "run-001" / "evidence_packet.json"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.evidence_packet.parent.mkdir(parents=True)
        self.ledger.write_text('{"run_id":"run-001","entry":"baseline"}\n', encoding="utf-8")
        self.evidence_packet.write_text(
            json.dumps({"run_id": "run-001", "verdict": "baseline"}, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class B2ExecutorLikeRoutingEvidenceVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B2RoutingEvidenceFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_builds_b2_routing_evidence_record_from_fixture_only_routed_denial(self):
        target = self.fixture.aeg / "b2-4-direct.txt"
        ledger_before = self.fixture.digest(self.fixture.ledger)

        evidence = self._evidence(target, ingress_id="b2-4-direct")

        self.assertFalse(target.exists())
        self.assertEqual(self.fixture.digest(self.fixture.ledger), ledger_before)
        self.assertTrue(evidence.record_id.startswith("b2-4-executor-like-routing-evidence:"))
        self.assertEqual(len(evidence.evidence_record_digest), 64)
        self.assertEqual(evidence.binding_version, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION)
        self.assertEqual(evidence.component, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_COMPONENT)
        self.assertEqual(evidence.record_type, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD)
        self.assertEqual(evidence.binding_status, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND)
        self.assertEqual(evidence.digest_status, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST)
        self.assertEqual(evidence.source, B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE)
        self.assertEqual(evidence.submitted_path, str(target))
        self.assertEqual(Path(evidence.resolved_target), target.resolve())
        self.assertEqual(evidence.routing_status, B2_AEG_PROTECTED_TARGET_ROUTED)
        self.assertEqual(evidence.routing_decision, B2_ROUTED_DENIAL)
        self.assertEqual(evidence.route_target, B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE)
        self.assertTrue(evidence.no_mutation_observed)
        self.assertEqual(evidence.runtime_write_path_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(evidence.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence.phase11a_status, PHASE11A_NOT_STARTED)
        self.assertEqual(evidence.b2_status, B2_REMAINS_OPEN_NOT_FULLY_ROUTED)
        self.assertEqual(evidence.b3_status, B3_NOT_STARTED)
        self.assertFalse(evidence.executor_write_path_wired)
        self.assertFalse(evidence.runtime_write_authority_granted)
        self.assertFalse(evidence.live_executor_authority_granted)

    def test_verify_replay_accepts_untampered_b2_routing_evidence(self):
        evidence = self._evidence(self.fixture.aeg / "b2-4-valid.txt", ingress_id="b2-4-valid")

        verify = verify_b2_executor_like_routing_evidence_record(evidence)

        self.assertTrue(verify.consistent)
        self.assertEqual(verify.status, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT)
        self.assertEqual(verify.component, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION)
        self.assertEqual(verify.scope_status, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_ONLY_SCOPE)
        self.assertEqual(verify.external_oracle_status, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_NOT_EXTERNAL_ORACLE)
        self.assertEqual(verify.rejection_codes, ())
        self.assertIn("B2 remains open; B2-5 status note remains separate", verify.checks)
        self.assertIn("B3 remains not started", verify.checks)

    def test_verify_replay_rejects_top_level_submitted_path_mismatch(self):
        record = self._record(self.fixture.aeg / "b2-4-path.txt", ingress_id="b2-4-path")
        record["submitted_path"] = ".aeg/forged.txt"

        verify = verify_b2_executor_like_routing_evidence_record(record)

        self.assertFalse(verify.consistent)
        self.assertEqual(verify.status, B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_REJECTED)
        self.assertIn(B2_ROUTING_FIELD_MISMATCH_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED, verify.rejection_codes)

    def test_verify_replay_rejects_nested_harness_tamper(self):
        record = self._record(self.fixture.aeg / "b2-4-harness.txt", ingress_id="b2-4-harness")
        record["harness_result"]["router_called"] = False

        verify = verify_b2_executor_like_routing_evidence_record(record)

        self.assertFalse(verify.consistent)
        self.assertIn(B2_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_FIELD_MISMATCH_REJECTED, verify.rejection_codes)

    def test_verify_replay_rejects_nested_route_tamper(self):
        record = self._record(self.fixture.aeg / "b2-4-route.txt", ingress_id="b2-4-route")
        record["harness_result"]["router_result"]["routing_decision"] = "FORGED_ALLOW"

        verify = verify_b2_executor_like_routing_evidence_record(record)

        self.assertFalse(verify.consistent)
        self.assertIn(B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_FIELD_MISMATCH_REJECTED, verify.rejection_codes)

    def test_verify_replay_rejects_no_mutation_overwrite(self):
        record = self._record(self.fixture.aeg / "b2-4-mutation.txt", ingress_id="b2-4-mutation")
        record["harness_result"]["router_result"]["no_mutation_observation"]["no_mutation_observed"] = False
        record["harness_result"]["router_result"]["no_mutation_observation"]["mutation_observed"] = True

        verify = verify_b2_executor_like_routing_evidence_record(record)

        self.assertFalse(verify.consistent)
        self.assertIn(B2_ROUTING_NO_MUTATION_MISMATCH_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_OVERCLAIM_REJECTED, verify.rejection_codes)

    def test_verify_replay_rejects_embedded_b1_evidence_tamper(self):
        record = self._record(self.fixture.aeg / "b2-4-b1.txt", ingress_id="b2-4-b1")
        guard_evidence = record["harness_result"]["router_result"]["guard_evidence_record"]
        guard_evidence["submitted_path"] = ".aeg/forged-b1.txt"

        verify = verify_b2_executor_like_routing_evidence_record(record)

        self.assertFalse(verify.consistent)
        self.assertIn(B2_ROUTING_B1_REPLAY_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED, verify.rejection_codes)

    def test_verify_replay_rejects_b2_closure_or_write_path_overclaim(self):
        record = self._record(self.fixture.aeg / "b2-4-overclaim.txt", ingress_id="b2-4-overclaim")
        record["b2_closure_status"] = "B2_" + "COMPLETE"
        record["harness_result"]["router_result"]["executor_write_path_wired"] = True

        verify = verify_b2_executor_like_routing_evidence_record(record)

        self.assertFalse(verify.consistent)
        self.assertIn(B2_ROUTING_OVERCLAIM_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_FIELD_MISMATCH_REJECTED, verify.rejection_codes)
        self.assertIn(B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED, verify.rejection_codes)

    def _evidence(self, target: Path, ingress_id: str):
        harness_result = self._harness_result(target=target, ingress_id=ingress_id)
        return build_b2_executor_like_routing_evidence_record(harness_result=harness_result)

    def _record(self, target: Path, ingress_id: str) -> dict:
        return copy.deepcopy(self._evidence(target=target, ingress_id=ingress_id).to_record())

    def _harness_result(self, target: Path, ingress_id: str):
        ingress = build_fixture_executor_like_ingress_request(
            submitted_path=target,
            intended_operation="replace",
            payload="b2-4 fixture payload that must not be written\n",
            payload_metadata={"payload_profile": "b2_4_digest_only_fixture_payload"},
            ingress_id=ingress_id,
        )
        return route_fixture_executor_like_ingress_through_router(
            repo_root=self.fixture.repo,
            ingress=ingress,
        )


if __name__ == "__main__":
    unittest.main()
