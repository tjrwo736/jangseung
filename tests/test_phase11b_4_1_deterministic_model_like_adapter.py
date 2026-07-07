import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import deterministic_model_like_adapter
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    bind_action_decision_packet_evidence,
    evaluate_store_adjacent_candidate_gate,
    verify_action_decision_packet_evidence,
)
from src.evidence.deterministic_model_like_adapter import (
    REJECTION_FIXTURE_IDS,
    SAFE_PROPOSAL_FIXTURE_ID,
    build_deterministic_model_like_adapter_evidence,
    build_deterministic_model_like_fixture_input,
    build_no_tool_model_like_adapter_structure,
    produce_deterministic_model_like_raw_output,
)
from src.evidence.executor_output_ingress import (
    PARSE_OK,
    ActionDecisionPacket,
    ingest_executor_output,
    is_runtime_built_action_decision_packet,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_LIMITED_ALLOWED,
)
from src.evidence.structured_actions import (
    PROPOSE_PATCH,
    VALID_STRUCTURED_ACTION,
)


DOC_PATH = Path(
    "docs/phase11b_4_1_deterministic_no_provider_model_like_adapter_v0.md"
)

COMPLETE_LABEL = (
    "PHASE11B_4_1_DETERMINISTIC_NO_PROVIDER_MODEL_LIKE_ADAPTER_COMPLETE_NOT_PROVIDER"
)

REQUIRED_LIMITS = (
    "DETERMINISTIC_NO_PROVIDER_ONLY",
    "NOT_MODEL_PROVIDER_INTEGRATION",
    "NOT_PROVIDER_READY",
    "NOT_NETWORK_ENABLED",
    "NOT_ACTION_EXECUTION_ENGINE",
    "NOT_WRITE_AUTHORITY",
    "NOT_TOOL_RUNTIME",
    "NOT_PATCH_APPLY",
    "NOT_LIVE_EXECUTOR_READY",
    "PROVIDER_GATE_REQUIRED",
)

REQUIRED_DOC_MARKERS = (
    "adapter_is_no_provider = true",
    "adapter_is_deterministic = true",
    "adapter_output_is_raw_executor_output_only = true",
    "adapter_output_is_action_decision_packet = false",
    "provider_network_called = false",
    "tool_runtime_enabled = false",
    "tool_calls_allowed = false",
    "execution_allowed = false",
    "mutation_allowed = false",
    "write_authority_granted = false",
    "store_routing_allowed = false",
    "store_path_reachable = false",
    "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
    "safe_default = hold_current_state",
    "provider_gate_required = true",
    "available_tools = ()",
    "tool_schemas = ()",
    "tool_runtime = disabled",
    "tool_choice = none",
    "max_tool_calls = 0",
    "function_calling_allowed = false",
    "shell_process_allowed = false",
    "filesystem_mutation_allowed = false",
    "provider_network_allowed_by_model_executor = false",
    "runtime_internal_call_handles = ()",
    "trusted_context_handles = ()",
    "store_module_handles = ()",
    "executor_output_ingress",
    "metadata-only",
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


class Phase11B41DeterministicModelLikeAdapterTests(unittest.TestCase):
    def test_adapter_accepts_only_deterministic_fixture_input(self):
        fixture_input = build_deterministic_model_like_fixture_input(
            SAFE_PROPOSAL_FIXTURE_ID
        )

        output = produce_deterministic_model_like_raw_output(fixture_input)

        self.assertEqual(fixture_input, {"fixture_id": SAFE_PROPOSAL_FIXTURE_ID})
        self.assertEqual(output["action_type"], PROPOSE_PATCH)
        self.assertNotIsInstance(output, ActionDecisionPacket)

        with self.assertRaises(ValueError):
            build_deterministic_model_like_fixture_input("unknown")
        with self.assertRaises(ValueError):
            produce_deterministic_model_like_raw_output(
                {"fixture_id": SAFE_PROPOSAL_FIXTURE_ID, "extra": "not allowed"}
            )
        with self.assertRaises(TypeError):
            produce_deterministic_model_like_raw_output("not fixture input")

    def test_safe_fixture_output_flows_through_ingress_only(self):
        output = produce_deterministic_model_like_raw_output(
            build_deterministic_model_like_fixture_input(SAFE_PROPOSAL_FIXTURE_ID)
        )

        packet = ingest_executor_output(output)
        evidence = bind_action_decision_packet_evidence(packet)
        verify = verify_action_decision_packet_evidence(evidence, packet)
        candidate = evaluate_store_adjacent_candidate_gate(packet)

        self.assertNotIsInstance(output, ActionDecisionPacket)
        self.assertEqual(packet.parse_status, PARSE_OK)
        self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(
            packet.capability_result.gate_result,
            CAPABILITY_GATE_LIMITED_ALLOWED,
        )
        self.assertTrue(is_runtime_built_action_decision_packet(packet))
        self.assertEqual(verify.status, ACTION_DECISION_PACKET_VERIFY_ACCEPTED)
        self.assertTrue(verify.accepted)
        self.assertEqual(candidate.gate_status, STORE_ADJACENT_CANDIDATE_ACCEPTED)
        self.assertTrue(candidate.store_adjacent_candidate_gate_metadata_only)
        self._assert_no_execution_mutation_write_or_store_route(packet)
        self._assert_no_execution_mutation_write_or_store_route(candidate)

    def test_required_rejection_fixtures_fail_closed_before_output(self):
        self.assertGreaterEqual(len(REJECTION_FIXTURE_IDS), 30)

        for fixture_id in REJECTION_FIXTURE_IDS:
            with self.subTest(fixture_id=fixture_id):
                fixture_input = build_deterministic_model_like_fixture_input(
                    fixture_id
                )

                with self.assertRaises(ValueError) as raised:
                    produce_deterministic_model_like_raw_output(fixture_input)

                message = str(raised.exception)
                self.assertIn("deterministic fixture rejected closed", message)
                self.assertIn(fixture_id, message)

    def test_safe_output_is_deterministic_and_caller_mutation_does_not_persist(self):
        fixture_input = build_deterministic_model_like_fixture_input(
            SAFE_PROPOSAL_FIXTURE_ID
        )
        first = produce_deterministic_model_like_raw_output(fixture_input)
        first["payload"]["target_files"].append("mutated-by-caller.md")

        second = produce_deterministic_model_like_raw_output(fixture_input)

        self.assertNotIn("mutated-by-caller.md", second["payload"]["target_files"])
        self.assertEqual(
            second["payload"]["target_files"],
            ["docs/example_proposal.md"],
        )

    def test_adapter_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            output = produce_deterministic_model_like_raw_output(
                build_deterministic_model_like_fixture_input(
                    SAFE_PROPOSAL_FIXTURE_ID
                )
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(output["action_type"], PROPOSE_PATCH)
            self.assertEqual(before, after)

    def test_no_tool_structure_records_disabled_surface(self):
        structure = build_no_tool_model_like_adapter_structure()

        self.assertEqual(structure["available_tools"], tuple())
        self.assertEqual(structure["tool_schemas"], tuple())
        self.assertEqual(structure["tool_runtime"], "disabled")
        self.assertEqual(structure["tool_choice"], "none")
        self.assertEqual(structure["max_tool_calls"], 0)
        self.assertFalse(structure["function_calling_allowed"])
        self.assertFalse(structure["shell_process_allowed"])
        self.assertFalse(structure["filesystem_mutation_allowed"])
        self.assertFalse(structure["provider_network_allowed_by_model_executor"])
        self.assertEqual(structure["runtime_internal_call_handles"], tuple())
        self.assertEqual(structure["trusted_context_handles"], tuple())
        self.assertEqual(structure["store_module_handles"], tuple())

    def test_evidence_records_no_provider_no_tool_no_authority_contract(self):
        evidence = build_deterministic_model_like_adapter_evidence()

        self.assertTrue(evidence["adapter_is_no_provider"])
        self.assertTrue(evidence["adapter_is_deterministic"])
        self.assertTrue(evidence["adapter_accepts_fixture_input_only"])
        self.assertTrue(evidence["adapter_output_is_raw_executor_output_only"])
        self.assertFalse(evidence["adapter_output_is_action_decision_packet"])
        self.assertFalse(evidence["adapter_submits_trusted_runtime_packet"])
        self.assertTrue(evidence["executor_output_ingress_required"])
        self.assertTrue(
            evidence["runtime_built_action_decision_packet_created_only_by_ingress"]
        )
        self.assertFalse(evidence["provider_network_called"])
        self.assertFalse(evidence["tool_runtime_enabled"])
        self.assertFalse(evidence["tool_calls_allowed"])
        self.assertFalse(evidence["execution_allowed"])
        self.assertFalse(evidence["mutation_allowed"])
        self.assertFalse(evidence["write_authority_granted"])
        self.assertFalse(evidence["store_routing_allowed"])
        self.assertFalse(evidence["store_path_reachable"])
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertTrue(evidence["provider_gate_required"])
        self.assertEqual(evidence["available_tools"], tuple())
        self.assertEqual(evidence["tool_schemas"], tuple())
        self.assertEqual(evidence["max_tool_calls"], 0)

    def test_adapter_source_has_no_runtime_or_provider_call_surface(self):
        source = inspect.getsource(deterministic_model_like_adapter)
        forbidden_fragments = (
            "Open" + "AI",
            "Oll" + "ama",
            "req" + "uests",
            "sock" + "et",
            "sub" + "process",
            "os." + "system",
            "po" + "pen",
            ".op" + "en(",
            "op" + "en(",
            ".write_" + "text(",
            ".write_" + "bytes(",
            ".to" + "uch(",
            ".mk" + "dir(",
            ".un" + "link(",
            ".re" + "name(",
            ".rep" + "lace(",
            "ex" + "ec(",
            "ev" + "al(",
            "__im" + "port__(",
            "import" + "lib",
            "insp" + "ect.",
            "sys._get" + "frame",
            "glob" + "als(",
            "loc" + "als(",
            "va" + "rs(",
            "src.state." + "store",
            "from src.state import " + "store",
            "sto" + "re.",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

    def test_doc_records_required_label_limits_and_metadata(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn(COMPLETE_LABEL, doc)
        for limit in REQUIRED_LIMITS:
            with self.subTest(limit=limit):
                self.assertIn(limit, doc)
        for marker in REQUIRED_DOC_MARKERS:
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

    def _assert_no_execution_mutation_write_or_store_route(self, result):
        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.mutation_allowed)
        self.assertFalse(result.write_authority_granted)
        self.assertFalse(result.store_routing_allowed)
        self.assertFalse(result.store_path_reachable)
        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(result.safe_default, SAFE_DEFAULT)


if __name__ == "__main__":
    unittest.main()
