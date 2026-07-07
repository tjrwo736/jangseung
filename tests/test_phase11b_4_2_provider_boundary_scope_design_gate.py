import unittest
from pathlib import Path


DOC_PATH = Path("docs/phase11b_4_2_provider_boundary_scope_design_gate_v0.md")

COMPLETE_LABEL = (
    "PHASE11B_4_2_PROVIDER_BOUNDARY_SCOPE_DESIGN_GATE_COMPLETE_NOT_PROVIDER"
)

REQUIRED_LIMITS = (
    "NOT_PROVIDER_IMPLEMENTATION",
    "NOT_MODEL_PROVIDER_INTEGRATION",
    "NOT_PROVIDER_READY",
    "NOT_NETWORK_ENABLED",
    "NOT_API_KEY_LOADING",
    "NOT_ENV_SECRET_LOADING",
    "NOT_LIVE_PROVIDER_ADAPTER",
    "NOT_ACTION_EXECUTION_ENGINE",
    "NOT_WRITE_AUTHORITY",
    "NOT_TOOL_RUNTIME",
    "NOT_PATCH_APPLY",
    "NOT_LIVE_EXECUTOR_READY",
    "PROVIDER_GATE_REQUIRED",
    "USER_AUTHORIZATION_REQUIRED",
)

REQUIRED_AUTHORITY_MARKERS = (
    "provider/model/network = NOT_STARTED / NOT_GRANTED",
    "action execution engine = NOT_STARTED",
    "write authority = NOT_GRANTED",
    "tool runtime = NOT_STARTED / NOT_GRANTED",
    "store routing = NOT_GRANTED",
    "store path reachability = NOT_GRANTED",
    "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
    "safe default = hold_current_state",
)

REQUIRED_DESIGN_TOPICS = (
    "1. Explicit user authorization is required before provider work",
    "2. Provider and network remain not started and not granted",
    "3. Provider output is never trusted directly",
    "4. Provider output may only become raw executor output candidate material",
    "5. Provider output must pass through executor_output_ingress",
    "6. ActionDecisionPacket remains runtime-built only",
    "7. Provider cannot submit packet-shaped trusted material",
    "8. Provider cannot access trusted runtime surfaces",
    "9. Secret, environment, and API key loading policy is future-gated",
    "10. Network opt-in policy is future-gated",
    "11. Prompt construction policy is future-gated",
    "12. Raw prompt and raw response retention policy is future-gated",
    "13. Prompt and response redaction policy is future-gated",
    "14. Provider error handling is secret-safe metadata only",
    "15. Provider telemetry and logging cannot leak sensitive content",
    "16. Provider adapter remains separate from action execution",
    "17. Provider gate is not live executor readiness",
    "18. Provider gate is not write authority",
    "19. Provider gate is not tool runtime",
    "20. Provider gate is not an action execution engine",
)

REQUIRED_TRUST_BOUNDARY_MARKERS = (
    "Provider output is never trusted directly",
    "provider output candidate",
    "raw executor output",
    "executor_output_ingress",
    "runtime-built ActionDecisionPacket",
    "metadata-only candidate where applicable",
    "Provider output cannot submit an `ActionDecisionPacket`",
    "store.py",
    "trusted runtime context",
    "runtime internals",
    "filesystem mutation",
    "shell/process surfaces",
    "eval/exec/import execution path",
    "tool runtime",
)

REQUIRED_FUTURE_GATE_MARKERS = (
    "11-B-4-2 = provider boundary scope design only",
    "11-B-4-3 = actual provider adapter only after explicit user/provider gate",
    "provider adapter still outputs raw executor output only",
    "action execution/write/patch/tool runtime remains separate future gate",
    "Secret loading is not implemented.",
    "Environment loading is not implemented.",
    "API key loading is not implemented.",
    "Network opt-in is not implemented.",
    "Prompt construction is not implemented.",
    "Raw prompt retention is not implemented.",
    "Raw response retention is not implemented.",
    "Prompt redaction is not implemented.",
    "Response redaction is not implemented.",
    "secret-safe metadata only",
    "main merge = NOT_PERFORMED",
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


class Phase11B42ProviderBoundaryScopeDesignGateTests(unittest.TestCase):
    def test_doc_records_required_label_limits_and_authority_hold(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn(COMPLETE_LABEL, doc)
        for limit in REQUIRED_LIMITS:
            with self.subTest(limit=limit):
                self.assertIn(limit, doc)
        for marker in REQUIRED_AUTHORITY_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_required_provider_boundary_design_topics(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in REQUIRED_DESIGN_TOPICS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
        for marker in REQUIRED_TRUST_BOUNDARY_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_future_gate_separation_and_unimplemented_policies(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in REQUIRED_FUTURE_GATE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_does_not_claim_forbidden_ready_or_safety_labels(self):
        doc_lines = {
            line.strip()
            for line in DOC_PATH.read_text(encoding="utf-8").splitlines()
        }

        for label in FORBIDDEN_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, doc_lines)


if __name__ == "__main__":
    unittest.main()
