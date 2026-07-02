import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    DENIED_BY_MEDIATOR_SKELETON,
    DENY_ONLY_MEDIATOR_SKELETON_PRESENT,
    ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATOR_DECISION_DENY,
    NOT_WIRED_TO_WRITE_PATH,
    WRITE_BYPASS_HARNESS_KNOWN_GAP_RESULT_VOCABULARY,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
    WRITE_CLASSES,
)
from src.evidence import deny_only_mediator
from src.evidence.deny_only_mediator import (
    DenyOnlyWriteMediator,
    WriteMediationRequest,
    decide_write_request,
    decision_id_for_request,
)


class Phase10E2DenyOnlyMediatorSkeletonTests(unittest.TestCase):
    def test_deny_only_mediator_returns_deny_for_every_declared_write_class(self):
        mediator = DenyOnlyWriteMediator()

        for write_class in WRITE_CLASSES:
            with self.subTest(write_class=write_class):
                request = WriteMediationRequest(
                    request_id=f"request-{write_class}",
                    actor="phase10-e2-test",
                    operation="write",
                    write_class=write_class,
                    submitted_target=f"target/{write_class}.txt",
                )

                decision = mediator.decide(request)

                self.assertEqual(decision.request_id, request.request_id)
                self.assertEqual(decision.decision_status, MEDIATOR_DECISION_DENY)
                self.assertEqual(decision.decision_reason, DENIED_BY_MEDIATOR_SKELETON)
                self.assertEqual(decision.mediator_status, DENY_ONLY_MEDIATOR_SKELETON_PRESENT)
                self.assertEqual(decision.write_path_status, NOT_WIRED_TO_WRITE_PATH)
                self.assertEqual(decision.enforcement_status, ENFORCEMENT_NOT_IMPLEMENTED)
                self.assertTrue(decision.skeleton_local_decision_only)
                self.assertFalse(decision.write_performed)
                self.assertFalse(decision.filesystem_interception_present)
                self.assertFalse(decision.permission_hardening_present)

    def test_unknown_write_class_is_still_denied_by_skeleton(self):
        request = WriteMediationRequest(
            request_id="request-unknown-write-class",
            actor="phase10-e2-test",
            operation="write",
            write_class="unknown_write_class",
            submitted_target="unknown-target.txt",
        )

        decision = decide_write_request(request)

        self.assertEqual(decision.decision_status, MEDIATOR_DECISION_DENY)
        self.assertEqual(decision.decision_reason, DENIED_BY_MEDIATOR_SKELETON)
        self.assertEqual(decision.write_path_status, NOT_WIRED_TO_WRITE_PATH)
        self.assertEqual(decision.enforcement_status, ENFORCEMENT_NOT_IMPLEMENTED)

    def test_decide_write_request_is_pure_decision_only_and_does_not_write_target(self):
        with tempfile.TemporaryDirectory() as tempdir:
            target = Path(tempdir) / ".aeg" / "e2-skeleton-target.txt"
            request = WriteMediationRequest(
                request_id="request-direct-aeg-write",
                actor="phase10-e2-test",
                operation="write",
                write_class="aeg_state_write",
                submitted_target=str(target),
                canonical_target=str(target),
                aeg_boundary="under_aeg",
            )

            decision = decide_write_request(request)

            self.assertEqual(decision.decision_status, MEDIATOR_DECISION_DENY)
            self.assertFalse(target.exists())

    def test_existing_file_is_not_changed_by_decision(self):
        with tempfile.TemporaryDirectory() as tempdir:
            target = Path(tempdir) / "existing.txt"
            target.write_text("baseline\n", encoding="utf-8")
            before = target.read_text(encoding="utf-8")
            request = WriteMediationRequest(
                request_id="request-existing-file",
                actor="phase10-e2-test",
                operation="replace",
                write_class="repo_tracked_write",
                submitted_target=str(target),
            )

            decision = decide_write_request(request)
            after = target.read_text(encoding="utf-8")

            self.assertEqual(decision.decision_status, MEDIATOR_DECISION_DENY)
            self.assertEqual(after, before)

    def test_decision_id_is_deterministic_and_bound_to_request(self):
        request = WriteMediationRequest(
            request_id="request-deterministic",
            actor="phase10-e2-test",
            operation="append",
            write_class="outside_repo_write",
            submitted_target="../outside.txt",
        )

        first = decision_id_for_request(request)
        second = decide_write_request(request).decision_id

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("deny-only-mediator-skeleton:"))

    def test_known_gap_baseline_vocabulary_remains_unchanged(self):
        self.assertEqual(
            WRITE_BYPASS_HARNESS_KNOWN_GAP_RESULT_VOCABULARY,
            (
                WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
                WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
                WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
            ),
        )

    def test_mediator_module_has_no_write_or_permission_api_calls(self):
        source = inspect.getsource(deny_only_mediator)
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
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
