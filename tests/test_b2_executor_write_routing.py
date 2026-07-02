import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_SYMLINK_TARGET_DENIED,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    B2_AEG_PROTECTED_TARGET_ROUTED,
    B2_EXECUTOR_WRITE_ROUTER,
    B2_NO_MUTATION_OBSERVATION_BOUND,
    B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST,
    B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE,
    B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    B2_ROUTED_DENIAL,
    DENIED_BY_B1_AEG_INTEGRITY_GUARD,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    NOT_WIRED_TO_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)
from src.evidence import b2_executor_write_router
from src.evidence.b1_aeg_integrity_verify import verify_b1_aeg_guard_evidence_record
from src.evidence.b2_executor_write_router import (
    build_pre_live_executor_write_request,
    route_pre_live_executor_write_request,
)


class B2ExecutorWriteRoutingFixture:
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

    def create_aeg_symlink_alias(self) -> Path:
        alias = self.repo / "aeg-state-alias"
        alias.symlink_to(self.aeg, target_is_directory=True)
        return alias

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class B2ExecutorWriteRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B2ExecutorWriteRoutingFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_pre_live_request_model_records_path_operation_payload_and_authority(self):
        request = build_pre_live_executor_write_request(
            submitted_path=Path(".aeg") / "b2-request-model.txt",
            intended_operation="replace",
            payload="payload that is digested but not written",
            payload_metadata={"content_type": "text/plain"},
            request_id="b2-request-model",
        )

        self.assertEqual(request.request_model, B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST)
        self.assertEqual(request.request_source, B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE)
        self.assertEqual(request.submitted_path, str(Path(".aeg") / "b2-request-model.txt"))
        self.assertEqual(request.intended_operation, "replace")
        self.assertEqual(len(request.payload_digest), 64)
        self.assertEqual(request.payload_metadata["content_type"], "text/plain")
        self.assertFalse(request.live_executor_request)
        self.assertEqual(request.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertFalse(request.live_executor_authority_granted)
        self.assertEqual(request.runtime_write_path_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)

    def test_direct_aeg_submitted_path_routes_through_guard_mediator_path(self):
        target = self.fixture.aeg / "b2-direct.txt"

        result = self._route(target, request_id="b2-direct")

        self._assert_routed_denial(result, target)

    def test_traversal_path_resolving_under_aeg_routes_through_guard_mediator_path(self):
        target = self.fixture.work / ".." / ".aeg" / "b2-traversal.txt"
        resolved_target = self.fixture.aeg / "b2-traversal.txt"

        result = self._route(target, request_id="b2-traversal")

        self._assert_routed_denial(result, resolved_target)
        self.assertEqual(result.guard_decision.target_class, B1_AEG_TRAVERSAL_TARGET_DENIED)

    def test_symlink_alias_target_follows_b1_guard_semantics_when_available(self):
        try:
            alias = self.fixture.create_aeg_symlink_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")
        target = alias / "b2-symlink.txt"
        resolved_target = self.fixture.aeg / "b2-symlink.txt"

        result = self._route(target, request_id="b2-symlink")

        self._assert_routed_denial(result, resolved_target)
        self.assertEqual(result.guard_decision.target_class, B1_AEG_SYMLINK_TARGET_DENIED)
        self.assertNotIn(".aeg", target.parts)

    def test_routed_denial_performs_no_target_mutation(self):
        target = self.fixture.aeg / "b2-no-mutation.txt"
        ledger_before = self.fixture.digest(self.fixture.ledger)

        result = self._route(target, request_id="b2-no-mutation")

        ledger_after = self.fixture.digest(self.fixture.ledger)
        self.assertFalse(target.exists())
        self.assertEqual(ledger_after, ledger_before)
        self.assertFalse(result.write_performed)
        self.assertFalse(result.filesystem_mutation_performed)
        self.assertFalse(result.no_mutation_observation.mutation_observed)
        self.assertTrue(result.no_mutation_observation.no_mutation_observed)
        self.assertEqual(result.no_mutation_status, B2_NO_MUTATION_OBSERVATION_BOUND)

    def test_routed_result_records_runtime_path_as_not_live_wired(self):
        result = self._route(self.fixture.aeg / "b2-runtime-status.txt", request_id="b2-runtime-status")

        self.assertEqual(result.runtime_write_path_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(result.guard_decision.wiring_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(result.mediator_decision.write_path_status, NOT_WIRED_TO_WRITE_PATH)
        self.assertEqual(result.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertFalse(result.live_executor_authority_granted)
        self.assertFalse(result.runtime_write_authority_granted)
        self.assertFalse(result.executor_write_path_wired)
        self.assertEqual(result.phase11a_status, PHASE11A_NOT_STARTED)

    def test_b1_guard_evidence_binding_replay_remains_consistent(self):
        result = self._route(self.fixture.aeg / "b2-b1c-binding.txt", request_id="b2-b1c-binding")

        verify = verify_b1_aeg_guard_evidence_record(result.guard_evidence_record)

        self.assertTrue(verify.consistent)
        self.assertEqual(result.b1_known_gap_baseline_status, B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
        self.assertEqual(result.raw_direct_path_status, WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE)

    def test_router_module_does_not_add_mutation_runtime_provider_or_remote_scope(self):
        source = inspect.getsource(b2_executor_write_router)
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
            "shutil",
            "socket",
            "http_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _route(self, target: Path, request_id: str):
        request = build_pre_live_executor_write_request(
            submitted_path=target,
            intended_operation="replace",
            payload="b2 payload that must not be written\n",
            payload_metadata={"payload_profile": "digest_only_test_payload"},
            request_id=request_id,
        )
        return route_pre_live_executor_write_request(repo_root=self.fixture.repo, request=request)

    def _assert_routed_denial(self, result, expected_resolved_target: Path) -> None:
        self.assertEqual(result.component, B2_EXECUTOR_WRITE_ROUTER)
        self.assertEqual(result.routing_status, B2_AEG_PROTECTED_TARGET_ROUTED)
        self.assertEqual(result.routing_decision, B2_ROUTED_DENIAL)
        self.assertEqual(result.route_target, B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE)
        self.assertEqual(result.guard_decision.denial_reason, DENIED_BY_B1_AEG_INTEGRITY_GUARD)
        self.assertEqual(Path(result.guard_decision.resolved_path), expected_resolved_target.resolve())
        self.assertEqual(result.mediator_decision.decision_status, MEDIATOR_DECISION_DENY)
        self.assertTrue(result.b1_guard_reused)
        self.assertTrue(result.b1_evidence_binding_reused)
        self.assertIsNotNone(result.guard_evidence_record)
        self.assertEqual(result.os_enforcement_status, NOT_OS_ENFORCED)
        self.assertEqual(result.filesystem_enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertFalse(result.raw_direct_write_success_claimed)
        self.assertFalse(result.write_performed)
        self.assertFalse(result.filesystem_mutation_performed)
        self.assertTrue(result.route_id.startswith("b2-executor-write-route:"))
        self.assertEqual(len(result.route_digest), 64)


if __name__ == "__main__":
    unittest.main()
