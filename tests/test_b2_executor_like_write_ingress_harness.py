import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    B2_AEG_PROTECTED_TARGET_ROUTED,
    B2_NO_MUTATION_OBSERVATION_BOUND,
    B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE,
    B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    B2_ROUTED_DENIAL,
    DENIED_BY_B1_AEG_INTEGRITY_GUARD,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    NOT_WIRED_TO_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)
from src.evidence import b2_executor_like_ingress_harness
from src.evidence import b2_executor_write_router
from src.evidence.b1_aeg_integrity_verify import verify_b1_aeg_guard_evidence_record
from src.evidence.b2_executor_like_ingress_harness import (
    B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
    B2_NO_LIVE_EXECUTOR_AUTHORITY,
    B2_NOT_PRODUCTION_RUNTIME_INGRESS,
    B2_REMAINS_OPEN_NOT_FULLY_ROUTED,
    B3_NOT_STARTED,
    build_fixture_executor_like_ingress_request,
    route_fixture_executor_like_ingress_through_router,
)


class B2ExecutorLikeIngressFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.work = self.repo / "work"
        self.aeg = self.repo / ".aeg"
        self.ledger = self.aeg / "ledger.jsonl"
        self.manifest = self.aeg / "manifest"
        self.evidence_packet = self.aeg / "runs" / "run-001" / "evidence_packet.json"
        self.verify_basis = self.aeg / "runs" / "run-001" / "verify_basis.json"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.evidence_packet.parent.mkdir(parents=True)
        self.ledger.write_text('{"run_id":"run-001","entry":"baseline"}\n', encoding="utf-8")
        self.manifest.write_text(
            json.dumps({"run_id": "run-001", "basis": "baseline-manifest"}, sort_keys=True),
            encoding="utf-8",
        )
        self.evidence_packet.write_text(
            json.dumps({"run_id": "run-001", "verdict": "baseline"}, sort_keys=True),
            encoding="utf-8",
        )
        self.verify_basis.write_text(
            json.dumps({"run_id": "run-001", "basis": "baseline-verify"}, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class B2ExecutorLikeWriteIngressHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B2ExecutorLikeIngressFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_fixture_ingress_model_records_source_path_operation_digest_and_no_authority(self):
        ingress = build_fixture_executor_like_ingress_request(
            submitted_path=Path(".aeg") / "b2-3-model.txt",
            intended_operation="replace",
            payload="fixture payload that must remain digest-only",
            payload_metadata={"content_type": "text/plain"},
            ingress_id="b2-3-model",
        )

        self.assertEqual(ingress.source, B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE)
        self.assertEqual(ingress.production_runtime_ingress_status, B2_NOT_PRODUCTION_RUNTIME_INGRESS)
        self.assertEqual(ingress.live_authority_note, B2_NO_LIVE_EXECUTOR_AUTHORITY)
        self.assertEqual(ingress.submitted_path, str(Path(".aeg") / "b2-3-model.txt"))
        self.assertEqual(ingress.intended_operation, "replace")
        self.assertEqual(len(ingress.payload_digest), 64)
        self.assertEqual(ingress.payload_metadata["content_type"], "text/plain")
        self.assertFalse(ingress.live_executor_request)
        self.assertFalse(ingress.production_runtime_ingress)
        self.assertEqual(ingress.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertFalse(ingress.live_executor_authority_granted)
        self.assertEqual(ingress.runtime_write_path_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)

    def test_fixture_ingress_routes_aeg_write_request_through_b2_router(self):
        target = self.fixture.aeg / "b2-3-direct.txt"
        observed_requests = []
        original_route = b2_executor_write_router.route_pre_live_executor_write_request

        def observed_route(*, repo_root, request):
            observed_requests.append(request)
            return original_route(repo_root=repo_root, request=request)

        ingress = self._ingress(target, ingress_id="b2-3-direct")
        with patch.object(b2_executor_write_router, "route_pre_live_executor_write_request", observed_route):
            result = route_fixture_executor_like_ingress_through_router(
                repo_root=self.fixture.repo,
                ingress=ingress,
            )

        self.assertEqual(len(observed_requests), 1)
        self.assertIs(observed_requests[0], result.router_request)
        self._assert_routed_denial(result, target)
        self.assertEqual(result.router_request.request_source, B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE)
        self.assertEqual(
            result.router_request.payload_metadata["fixture_ingress_source"],
            B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
        )
        self.assertEqual(result.router_request.payload_metadata["fixture_payload_digest"], ingress.payload_digest)

    def test_traversal_target_resolving_under_aeg_routes_through_b2_router(self):
        target = self.fixture.work / ".." / ".aeg" / "b2-3-traversal.txt"
        resolved_target = self.fixture.aeg / "b2-3-traversal.txt"

        result = self._route(target, ingress_id="b2-3-traversal")

        self._assert_routed_denial(result, resolved_target)
        self.assertEqual(result.router_result.guard_decision.target_class, B1_AEG_TRAVERSAL_TARGET_DENIED)

    def test_harness_observes_no_mutation_for_protected_target(self):
        target = self.fixture.aeg / "b2-3-no-mutation.txt"
        ledger_before = self.fixture.digest(self.fixture.ledger)

        result = self._route(target, ingress_id="b2-3-no-mutation")

        ledger_after = self.fixture.digest(self.fixture.ledger)
        self.assertFalse(target.exists())
        self.assertEqual(ledger_after, ledger_before)
        self.assertTrue(result.no_mutation_observed)
        self.assertFalse(result.router_result.write_performed)
        self.assertFalse(result.router_result.filesystem_mutation_performed)
        self.assertFalse(result.router_result.no_mutation_observation.mutation_observed)
        self.assertTrue(result.router_result.no_mutation_observation.no_mutation_observed)
        self.assertEqual(result.router_result.no_mutation_status, B2_NO_MUTATION_OBSERVATION_BOUND)

    def test_harness_result_records_fixture_only_prelive_and_current_authority_status(self):
        result = self._route(self.fixture.aeg / "b2-3-status.txt", ingress_id="b2-3-status")

        self.assertTrue(result.fixture_only)
        self.assertTrue(result.router_called)
        self.assertFalse(result.production_runtime_wiring_added)
        self.assertFalse(result.production_adapter_added)
        self.assertFalse(result.live_executor_invoked)
        self.assertFalse(result.external_runtime_invoked)
        self.assertFalse(result.command_runner_invoked)
        self.assertFalse(result.broad_write_capability_granted)
        self.assertFalse(result.raw_capability_granted)
        self.assertFalse(result.runtime_write_authority_granted)
        self.assertEqual(result.runtime_write_path_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(result.router_result.runtime_write_path_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(result.router_result.mediator_decision.write_path_status, NOT_WIRED_TO_WRITE_PATH)
        self.assertEqual(result.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(result.phase11a_status, PHASE11A_NOT_STARTED)
        self.assertEqual(result.b2_status, B2_REMAINS_OPEN_NOT_FULLY_ROUTED)
        self.assertEqual(result.b3_status, B3_NOT_STARTED)

    def test_b1_guard_evidence_and_verify_replay_remain_compatible(self):
        result = self._route(self.fixture.aeg / "b2-3-b1-compatible.txt", ingress_id="b2-3-b1")

        verify = verify_b1_aeg_guard_evidence_record(result.router_result.guard_evidence_record)

        self.assertTrue(result.router_result.b1_guard_reused)
        self.assertTrue(result.router_result.b1_evidence_binding_reused)
        self.assertTrue(verify.consistent)
        self.assertEqual(result.router_result.b1_known_gap_baseline_status, B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
        self.assertEqual(
            result.router_result.raw_direct_path_status,
            WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
        )

    def test_harness_module_does_not_connect_production_cli_or_runtime_scope(self):
        source = inspect.getsource(b2_executor_like_ingress_harness)
        forbidden_calls = (
            "src.cli",
            "execute_contract(",
            "save_run(",
            "provider_adapter",
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "subprocess",
            "shutil",
            "socket",
            "requests",
            "urllib",
            "write_" + "file",
            "run_" + "command",
            ".ch" + "mod(",
            ".ch" + "own(",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _ingress(self, target: Path, ingress_id: str):
        return build_fixture_executor_like_ingress_request(
            submitted_path=target,
            intended_operation="replace",
            payload="b2-3 fixture payload that must not be written\n",
            payload_metadata={"payload_profile": "b2_3_digest_only_fixture_payload"},
            ingress_id=ingress_id,
        )

    def _route(self, target: Path, ingress_id: str):
        return route_fixture_executor_like_ingress_through_router(
            repo_root=self.fixture.repo,
            ingress=self._ingress(target, ingress_id=ingress_id),
        )

    def _assert_routed_denial(self, result, expected_resolved_target: Path) -> None:
        self.assertEqual(result.ingress.source, B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE)
        self.assertEqual(result.router_result.routing_status, B2_AEG_PROTECTED_TARGET_ROUTED)
        self.assertEqual(result.router_result.routing_decision, B2_ROUTED_DENIAL)
        self.assertEqual(result.router_result.route_target, B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE)
        self.assertEqual(result.router_result.guard_decision.denial_reason, DENIED_BY_B1_AEG_INTEGRITY_GUARD)
        self.assertEqual(Path(result.router_result.guard_decision.resolved_path), expected_resolved_target.resolve())
        self.assertEqual(result.router_result.mediator_decision.decision_status, MEDIATOR_DECISION_DENY)
        self.assertTrue(result.router_result.b1_guard_reused)
        self.assertTrue(result.router_result.b1_evidence_binding_reused)
        self.assertIsNotNone(result.router_result.guard_evidence_record)
        self.assertFalse(result.router_result.write_performed)
        self.assertFalse(result.router_result.filesystem_mutation_performed)
        self.assertTrue(result.harness_id.startswith("b2-3-executor-like-ingress-harness:"))
        self.assertEqual(len(result.harness_digest), 64)


if __name__ == "__main__":
    unittest.main()
