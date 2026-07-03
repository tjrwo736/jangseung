import inspect
from pathlib import Path
import unittest

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
)
from src.evidence import b2_executor_write_router


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "b2_executor_write_routing_integration_boundary_v0.md"


class B2ExecutorWriteRoutingIntegrationBoundaryTests(unittest.TestCase):
    def test_boundary_doc_records_current_authority_without_completion_claim(self):
        text = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn("B2-2 is an investigation and boundary definition step only", text)
        self.assertIn("B2 state: open, not fully wired", text)
        self.assertIn(NOT_WIRED_TO_EXECUTOR_WRITE_PATH, text)
        self.assertIn(LIVE_EXECUTOR_AUTHORITY_ON_HOLD, text)
        self.assertIn(PHASE11A_NOT_STARTED, text)
        self.assertIn("B2-2 adds no production wiring", text)
        self.assertIn("B2-2 makes no B3 claim", text)

        forbidden_completion_claims = (
            "LIVE_" + "EXECUTOR_READY",
            "SAFE_" + "TO_RUN",
            "WRITE_" + "AUTHORITY_SAFE",
            "EXECUTOR_" + "CANNOT_WRITE_AEG",
            "B1_" + "HARD_BLOCKER_CLOSED",
            "B2_" + "COMPLETE",
            "B2_" + "WIRED",
            "WRITE_PATH_" + "WIRED",
            "FILESYSTEM_" + "ENFORCED",
            "OS_" + "ENFORCED",
            "EXECUTOR_" + "ISOLATED",
            "EXTERNALLY_" + "ENFORCED",
            "BYPASS_" + "IMPOSSIBLE",
            "EXTERNAL_" + "ANCHOR_ACTIVE",
            "TAMPER_" + "PROOF",
        )
        for claim in forbidden_completion_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)

    def test_boundary_doc_distinguishes_state_recorder_from_executor_write_ingress(self):
        text = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn("`save_run` is a state recorder", text)
        self.assertIn("not the executor write path", text)
        self.assertIn("no current runtime write path feeds such requests into", text)
        self.assertIn("router", text)

    def test_router_module_remains_unwired_and_non_mutating(self):
        source = inspect.getsource(b2_executor_write_router)

        self.assertIn("route_pre_live_executor_write_request", source)
        self.assertIn("write_performed", source)
        self.assertIn("executor_write_path_wired", source)
        self.assertNotIn("save_run(", source)
        self.assertNotIn("execute_contract(", source)
        self.assertNotIn("subprocess", source)

        forbidden_mutation_calls = (
            ".write_text(",
            ".write_bytes(",
            ".open(",
            "open(",
            ".mkdir(",
            ".touch(",
            ".unlink(",
            ".rename(",
            ".replace(",
            ".ch" + "mod(",
            ".ch" + "own(",
        )
        for call in forbidden_mutation_calls:
            with self.subTest(call=call):
                self.assertNotIn(call, source)


if __name__ == "__main__":
    unittest.main()
