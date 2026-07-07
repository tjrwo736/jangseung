import unittest
from pathlib import Path


DOC_PATH = Path("docs/phase11b_4_pre_provider_completion_baseline_v0.md")

COMPLETE_LABEL = "PHASE11B_4_PRE_PROVIDER_BASELINE_COMPLETE_NOT_PROVIDER"

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

REQUIRED_PHASE_STATUS = (
    "11-B-4-0 = COMPLETE_AS_RESTRICTED_MODEL_EXECUTOR_NO_TOOL_PROPOSE_ONLY_DESIGN_GATE",
    "11-B-4-1 = COMPLETE_AS_DETERMINISTIC_NO_PROVIDER_MODEL_LIKE_ADAPTER_DRY_STRUCTURE",
    "11-B-4-2 = COMPLETE_AS_PROVIDER_BOUNDARY_SCOPE_DESIGN_GATE_NOT_PROVIDER",
    "Phase 11-B-4 pre-provider line = COMPLETE_AS_PRE_PROVIDER_NO_TOOL_RAW_OUTPUT_BASELINE",
)

REQUIRED_AUTHORITY_STATUS = (
    "provider/model/network = NOT_STARTED / NOT_GRANTED",
    "actual provider adapter = NOT_STARTED",
    "OpenAI/Ollama/LLM call = NOT_STARTED / NOT_GRANTED",
    "API key/env/secret loading = NOT_STARTED / NOT_GRANTED",
    "network client = NOT_STARTED / NOT_GRANTED",
    "provider response parser for live calls = NOT_STARTED",
    "action execution engine = NOT_STARTED",
    "write authority = NOT_GRANTED",
    "tool runtime = NOT_STARTED / NOT_GRANTED",
    "store routing = NOT_GRANTED",
    "store path reachability = NOT_GRANTED",
    "patch application = NOT_STARTED",
    "autonomous loop = NOT_STARTED",
    "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
    "safe default = hold_current_state",
)

REQUIRED_NON_EQUIVALENCES = (
    "no-provider adapter != provider adapter",
    "provider boundary scope != provider implementation",
    "provider gate != live executor ready",
    "provider gate != write authority",
    "provider output != trusted decision",
    "provider output != ActionDecisionPacket",
    "raw executor output != runtime-built packet",
    "accepted metadata-only candidate != action execution",
    "accepted proposal != patch application",
    "valid structured action != authority grant",
)

REQUIRED_FUTURE_GATE_MARKERS = (
    "explicit user/provider gate required",
    "secret/env/API key policy approved",
    "network opt-in policy approved",
    "prompt construction policy approved",
    "raw prompt/response retention policy approved or explicitly denied",
    "prompt/response redaction policy approved",
    "provider error handling as secret-safe metadata",
    "provider output remains raw executor output only",
    "forced executor_output_ingress routing preserved",
    "ActionDecisionPacket remains runtime-built only",
    "no tools unless a separate future tool-runtime gate exists",
    "no action execution/write/patch unless separate future gates exist",
)

REQUIRED_FORBIDDEN_SCOPE_MARKERS = (
    "actual provider/model/network call",
    "OpenAI/Ollama/LLM call",
    "provider SDK import",
    "network client implementation",
    "API key loading",
    "environment secret loading",
    "credential loading",
    "live provider adapter",
    "live provider response parser",
    "action execution engine",
    "write authority grant",
    "file mutation by executor output",
    "shell/process/write_file/run_command/process_spawn authority",
    "eval/exec/import execution path",
    "tool runtime",
    "store.py mutation",
    "direct store access",
    "runtime introspection/internal access implementation",
    "patch application",
    "autonomous loop",
    "public release material",
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
    "LIVE-" + "READY",
    "WRITE-" + "SAFE",
    "ARBITRARY-CODE-" + "SAFE",
)


class Phase11B4PreProviderCompletionBaselineTests(unittest.TestCase):
    def test_doc_records_required_label_limits_and_phase_status(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn(COMPLETE_LABEL, doc)
        for limit in REQUIRED_LIMITS:
            with self.subTest(limit=limit):
                self.assertIn(limit, doc)
        for marker in REQUIRED_PHASE_STATUS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_authority_hold_and_safe_default(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in REQUIRED_AUTHORITY_STATUS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
        self.assertIn("main merge = NOT_PERFORMED", doc)

    def test_doc_records_non_equivalences_and_future_provider_gates(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in REQUIRED_NON_EQUIVALENCES:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
        for marker in REQUIRED_FUTURE_GATE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_forbidden_scope_as_not_implemented(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn("This baseline does not implement or authorize:", doc)
        for marker in REQUIRED_FORBIDDEN_SCOPE_MARKERS:
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
