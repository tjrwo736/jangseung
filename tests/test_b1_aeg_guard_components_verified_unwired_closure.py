import re
import unittest
from pathlib import Path

from src.contracts import (
    B1_AEG_COMPONENT_PACKAGE_READY_FOR_B2_B3,
    B1_AEG_GUARD_COMPONENTS_VERIFIED_UNWIRED,
    B1_AEG_GUARD_COMPONENTS_VERIFIED_UNWIRED_VOCABULARY,
    B1_AEG_HARD_BLOCKER_NOT_FULLY_CLOSED,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_EXECUTOR_ISOLATED,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_TAMPER_PROOF,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    SAFE_DEFAULT,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_DOC = REPO_ROOT / "docs" / "b1_aeg_guard_components_verified_unwired_closure_v0.md"


class B1AegGuardComponentsVerifiedUnwiredClosureTests(unittest.TestCase):
    def test_closure_vocabulary_matches_allowed_unwired_status_labels(self):
        expected = (
            B1_AEG_GUARD_COMPONENTS_VERIFIED_UNWIRED,
            B1_AEG_COMPONENT_PACKAGE_READY_FOR_B2_B3,
            B1_AEG_HARD_BLOCKER_NOT_FULLY_CLOSED,
            NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
            PHASE11A_NOT_STARTED,
            NOT_OS_ENFORCED,
            NOT_FILESYSTEM_ENFORCED,
            NOT_EXECUTOR_ISOLATED,
            NOT_TAMPER_PROOF,
            NOT_EXTERNAL_ANCHORED,
        )

        self.assertEqual(B1_AEG_GUARD_COMPONENTS_VERIFIED_UNWIRED_VOCABULARY, expected)

    def test_closure_document_records_required_b1_component_state(self):
        text = CLOSURE_DOC.read_text(encoding="utf-8")

        required_fragments = (
            B1_AEG_GUARD_COMPONENTS_VERIFIED_UNWIRED,
            "B1-A raw `.aeg/` known-gap baseline is preserved",
            "B1-B deny-only guard component is present",
            "B1-C guard decision evidence binding is present",
            "B1-D verify-only mismatch, tamper, reported-only promotion, known-gap",
            B1_AEG_COMPONENT_PACKAGE_READY_FOR_B2_B3,
            NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
            PHASE11A_NOT_STARTED,
            SAFE_DEFAULT,
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_closure_document_records_required_not_claims(self):
        text = CLOSURE_DOC.read_text(encoding="utf-8")

        required_not_claims = (
            "B1 hard blocker fully closed.",
            "Claim that an executor cannot write `.aeg/`.",
            "Claim that raw or direct `.aeg/` writes are blocked.",
            "OS enforcement.",
            "Filesystem enforcement.",
            "Executor isolation.",
            "Tamper-proof evidence store.",
            "External anchor.",
            "Runtime write-path wiring.",
            "Live executor readiness.",
            "Safe-to-run approval.",
        )

        for claim in required_not_claims:
            with self.subTest(claim=claim):
                self.assertIn(claim, text)

    def test_b1_b2_b3_boundary_is_explicit_and_non_authorizing(self):
        text = CLOSURE_DOC.read_text(encoding="utf-8")

        required_boundary = (
            "B1 means `.aeg/` guard components verified unwired.",
            "B2 means executor write routing through mediator and guard paths.",
            "B3 means no capability grant plus worktree scope",
            "B1 green for live executor entry requires B1, B2, and B3 together.",
            "B1 alone must not be treated as live executor entry approval.",
            "This closure does not implement B2 routing or B3 capability denial.",
        )

        for fragment in required_boundary:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_closure_artifacts_do_not_use_forbidden_overclaim_labels(self):
        text = CLOSURE_DOC.read_text(encoding="utf-8")
        tokens = set(re.findall(r"\b[A-Z][A-Z0-9_]*\b", text))
        tokens.update(B1_AEG_GUARD_COMPONENTS_VERIFIED_UNWIRED_VOCABULARY)
        forbidden_labels = {
            "B1_" + "COMPLETE",
            "B1_HARD_" + "BLOCKER_CLOSED",
            "B1_AEG_WRITE_" + "BLOCKED_FOR_EXECUTOR",
            "EXECUTOR_" + "CANNOT_WRITE_AEG",
            "TAMPER_" + "PROOF",
            "EXECUTOR_" + "ISOLATED",
            "FILESYSTEM_" + "ENFORCED",
            "OS_" + "ENFORCED",
            "EXTERNALLY_" + "ENFORCED",
            "EXTERNAL_" + "ANCHOR_ACTIVE",
            "BYPASS_" + "IMPOSSIBLE",
            "LIVE_" + "EXECUTOR_READY",
            "SAFE_" + "TO_RUN",
            "WRITE_" + "AUTHORITY_SAFE",
        }

        self.assertEqual(tokens & forbidden_labels, set())


if __name__ == "__main__":
    unittest.main()
