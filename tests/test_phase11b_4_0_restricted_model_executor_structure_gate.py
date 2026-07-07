import unittest
from pathlib import Path


DOC_PATH = Path("docs/phase11b_4_0_restricted_model_executor_structure_gate_v0.md")

COMPLETE_LABEL = (
    "PHASE11B_4_0_RESTRICTED_MODEL_EXECUTOR_STRUCTURE_GATE_COMPLETE_NOT_PROVIDER"
)

REQUIRED_LIMITS = (
    "NOT_MODEL_PROVIDER_INTEGRATION",
    "NOT_PROVIDER_READY",
    "NOT_NETWORK_ENABLED",
    "NOT_ACTION_EXECUTION_ENGINE",
    "NOT_WRITE_AUTHORITY",
    "NOT_TOOL_RUNTIME",
    "NOT_PATCH_APPLY",
    "NOT_LIVE_EXECUTOR_READY",
    "STRUCTURED_EXECUTOR_ASSUMPTION_REQUIRED",
    "PROVIDER_GATE_REQUIRED",
)

REQUIRED_ANSWER_MARKERS = (
    "1. Restricted model executor output type",
    "2. Model output is raw executor output only",
    "3. Non-JSON or malformed JSON fails closed",
    "4. Completed ActionDecisionPacket-shaped output is rejected",
    "5. Tool calls, commands, code blocks, mutation requests, and internal calls are rejected",
    '6. "Model has no tools" is structural',
    "7. Provider and network are a future explicit provider gate",
    "8. Next implementation step",
    "9. Duration of live executor authority hold",
    "10. Conditions required before provider gate can open",
)

REQUIRED_REJECTION_MARKERS = (
    "raw executor output",
    "executor_output_ingress",
    "parse_status = PARSE_FAILED",
    "validation_result = None",
    "capability_result = None",
    "ActionDecisionPacket remains",
    "available_tools = ()",
    "tool_schemas = ()",
    "max_tool_calls = 0",
    "store.py access by model = NOT_GRANTED",
    "trusted context access by model = NOT_GRANTED",
    "runtime internals access by model = NOT_GRANTED",
    "accepted downstream proposal != mutation",
    "metadata-only candidate != store write",
)

FORBIDDEN_LABELS = (
    "LIVE_EXECUTOR_" + "READY",
    "MODEL_EXECUTOR_" + "READY",
    "PROVIDER_" + "READY",
    "NETWORK_" + "READY",
    "ACTION_EXECUTION_" + "READY",
    "WRITE_AUTHORITY_" + "SAFE",
    "MUTATION_AUTHORITY_" + "GRANTED",
    "TOOL_RUNTIME_" + "READY",
    "PATCH_" + "APPLIED",
    "BYPASS_" + "IMPOSSIBLE",
    "TAMPER_" + "PROOF",
    "ARBITRARY_CODE_" + "SAFE",
)


class Phase11B40RestrictedModelExecutorStructureGateTests(unittest.TestCase):
    def test_doc_records_required_label_limits_and_authority_hold(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn(COMPLETE_LABEL, doc)
        for limit in REQUIRED_LIMITS:
            with self.subTest(limit=limit):
                self.assertIn(limit, doc)
        self.assertIn("safe default = hold_current_state", doc)
        self.assertIn(
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            doc,
        )
        self.assertIn("main merge = NOT_PERFORMED", doc)

    def test_doc_answers_required_design_questions(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in REQUIRED_ANSWER_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
        for marker in REQUIRED_REJECTION_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_does_not_claim_forbidden_ready_or_safety_labels(self):
        doc_lines = {line.strip() for line in DOC_PATH.read_text(encoding="utf-8").splitlines()}

        for label in FORBIDDEN_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, doc_lines)


if __name__ == "__main__":
    unittest.main()
