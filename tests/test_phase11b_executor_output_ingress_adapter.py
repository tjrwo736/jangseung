import dataclasses
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import executor_output_ingress
from src.evidence.executor_output_ingress import (
    PARSE_FAILED,
    PARSE_OK,
    RUNTIME_INGRESS_ADAPTER,
    build_executor_output_ingress_adapter_evidence,
    build_predefined_raw_output_sample,
    ingest_executor_output,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_DENIED,
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    FUTURE_GATE_REQUIRED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
    USER_GATE_REQUIRED,
)
from src.evidence.structured_actions import (
    FORBIDDEN_ACTION_TYPE_REJECTED,
    FORBIDDEN_PAYLOAD_FIELD_REJECTED,
    NOOP,
    PROCESS_SPAWN,
    PROPOSE_PATCH,
    PROVIDER_MODEL_CALL,
    REQUEST_EXPLANATION,
    VALID_STRUCTURED_ACTION,
)


class Phase11bExecutorOutputIngressAdapterTests(unittest.TestCase):
    def test_fixture_dict_parse_creates_runtime_owned_noop_packet(self):
        packet = ingest_executor_output(self._valid_noop())

        self.assertEqual(packet.parse_status, PARSE_OK)
        self.assertIsNone(packet.parse_error)
        self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_ALLOWED)
        self.assertEqual(packet.created_by, RUNTIME_INGRESS_ADAPTER)
        self.assertTrue(packet.packet_id.startswith("action-decision-packet-"))
        self.assertTrue(packet.raw_output_hash.startswith("sha256:"))
        self.assertEqual(packet.safe_default, SAFE_DEFAULT)
        self.assertEqual(packet.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self._assert_packet_never_grants_authority(packet)

    def test_fixture_json_parse_creates_request_explanation_packet(self):
        raw_output = json.dumps(
            self._valid_noop(
                action_type=REQUEST_EXPLANATION,
                capability_requirements=["explanation"],
            )
        )

        packet = ingest_executor_output(raw_output)

        self.assertEqual(packet.parse_status, PARSE_OK)
        self.assertEqual(packet.normalized_action["action_type"], REQUEST_EXPLANATION)
        self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_ALLOWED)
        self._assert_packet_never_grants_authority(packet)

    def test_malformed_json_returns_hold_packet_without_validation_or_capability(self):
        packet = ingest_executor_output('{"action_type":')

        self.assertEqual(packet.parse_status, PARSE_FAILED)
        self.assertIsNotNone(packet.parse_error)
        self.assertIsNone(packet.normalized_action)
        self.assertIsNone(packet.validation_result)
        self.assertIsNone(packet.capability_result)
        self.assertIn(
            "validation_status=VALIDATION_NOT_RUN_PARSE_FAILED",
            packet.decision_basis,
        )
        self.assertIn(
            "capability_gate_result=CAPABILITY_NOT_RUN_PARSE_FAILED",
            packet.decision_basis,
        )
        self._assert_packet_never_grants_authority(packet)

    def test_predefined_raw_output_sample_is_allowed_fixture_input(self):
        packet = ingest_executor_output(build_predefined_raw_output_sample())

        self.assertEqual(packet.parse_status, PARSE_OK)
        self.assertEqual(packet.normalized_action["action_type"], NOOP)
        self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_ALLOWED)

    def test_valid_noop_request_explanation_and_propose_patch_packet_creation(self):
        actions = (
            self._valid_noop(),
            self._valid_noop(
                action_type=REQUEST_EXPLANATION,
                capability_requirements=["explanation"],
            ),
            self._valid_propose_patch(),
        )

        for action in actions:
            with self.subTest(action_type=action["action_type"]):
                packet = ingest_executor_output(action)

                self.assertEqual(packet.parse_status, PARSE_OK)
                self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
                self.assertIn(
                    packet.capability_result.gate_result,
                    (CAPABILITY_GATE_ALLOWED, CAPABILITY_GATE_LIMITED_ALLOWED),
                )
                self._assert_packet_never_grants_authority(packet)

    def test_propose_patch_packet_is_not_execution_mutation_or_write_authority(self):
        packet = ingest_executor_output(self._valid_propose_patch())

        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
        self.assertFalse(packet.execution_allowed)
        self.assertFalse(packet.mutation_allowed)
        self.assertFalse(packet.write_authority_granted)
        self.assertFalse(packet.capability_result.execution_allowed)
        self.assertFalse(packet.capability_result.mutation_allowed)
        self.assertFalse(packet.capability_result.write_authority_granted)

    def test_forbidden_action_rejected_without_authority(self):
        packet = ingest_executor_output(self._valid_noop(action_type=PROCESS_SPAWN))

        self.assertEqual(packet.validation_result.status, FORBIDDEN_ACTION_TYPE_REJECTED)
        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_DENIED)
        self._assert_packet_never_grants_authority(packet)

    def test_executable_payload_rejected_without_authority(self):
        action = self._valid_propose_patch()
        action["payload"]["python_code"] = "print('not executable')"

        packet = ingest_executor_output(action)

        self.assertEqual(packet.validation_result.status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)
        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_DENIED)
        self._assert_packet_never_grants_authority(packet)

    def test_denied_future_and_user_gated_capability_rejections(self):
        denied = self._valid_noop(capability_requirements=["network"])
        future = self._valid_noop(
            action_type=PROVIDER_MODEL_CALL,
            capability_requirements=["provider_model_call"],
        )
        user_gated = self._valid_noop(capability_requirements=["user_gate"])

        cases = (
            (denied, CAPABILITY_DENIED),
            (future, FUTURE_GATE_REQUIRED),
            (user_gated, USER_GATE_REQUIRED),
        )

        for action, expected_gate in cases:
            with self.subTest(expected_gate=expected_gate):
                packet = ingest_executor_output(action)

                self.assertEqual(packet.capability_result.gate_result, expected_gate)
                self._assert_packet_never_grants_authority(packet)

    def test_reported_only_wrapper_fields_are_ignored_not_trusted(self):
        raw_output = {
            "action": self._valid_noop(),
            "created_by": "executor_self_report",
            "execution_allowed": True,
            "reported_only": {"write_authority_granted": True},
            "live_executor_authority": "EXECUTOR_CLAIMS_READY",
        }

        packet = ingest_executor_output(raw_output)

        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_ALLOWED)
        self.assertIn("raw_output.created_by", packet.ignored_reported_only_fields)
        self.assertIn("raw_output.execution_allowed", packet.ignored_reported_only_fields)
        self.assertIn("raw_output.reported_only", packet.ignored_reported_only_fields)
        self.assertIn(
            "raw_output.reported_only.write_authority_granted",
            packet.ignored_reported_only_fields,
        )
        self.assertIn(
            "raw_output.live_executor_authority",
            packet.ignored_reported_only_fields,
        )
        self.assertEqual(packet.created_by, RUNTIME_INGRESS_ADAPTER)
        self.assertEqual(packet.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self._assert_packet_never_grants_authority(packet)

    def test_self_report_inside_action_is_rejected_not_trusted(self):
        action = self._valid_propose_patch()
        action["payload"]["authority"] = "write_file"
        action["payload"]["approved_by_executor"] = True

        packet = ingest_executor_output(action)

        self.assertEqual(
            packet.capability_result.gate_result,
            REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
        )
        self.assertFalse(packet.write_authority_granted)
        self.assertIn(
            "executor self-claimed authority rejected",
            packet.capability_result.gate_reason,
        )

    def test_runtime_owned_packet_ignores_executor_authored_packet_fields(self):
        action = self._valid_noop()
        action["packet_id"] = "executor-packet-id"
        action["created_by"] = "executor"

        packet = ingest_executor_output(action)

        self.assertNotEqual(packet.packet_id, "executor-packet-id")
        self.assertEqual(packet.created_by, RUNTIME_INGRESS_ADAPTER)
        self.assertIn("action.packet_id", packet.ignored_reported_only_fields)
        self.assertIn("action.created_by", packet.ignored_reported_only_fields)
        self.assertNotIn("packet_id", packet.normalized_action)
        self.assertNotIn("created_by", packet.normalized_action)
        self.assertIsInstance(packet.normalized_action, MappingProxyType)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            packet.created_by = "executor"
        with self.assertRaises(TypeError):
            packet.normalized_action["action_type"] = "MUTATED"

    def test_store_path_is_not_reachable_and_store_module_is_not_called(self):
        packet = ingest_executor_output(self._valid_noop())
        source = inspect.getsource(executor_output_ingress)

        self.assertFalse(packet.store_routing_allowed)
        self.assertFalse(packet.store_path_reachable)
        self.assertNotIn("src.state.store", source)
        self.assertNotIn("from src.state import store", source)
        self.assertNotIn("store.", source)

    def test_adapter_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            packet = ingest_executor_output(self._valid_propose_patch())

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertEqual(before, after)
            self.assertFalse(packet.mutation_allowed)

    def test_adapter_source_has_no_provider_network_shell_or_process_surface(self):
        source = inspect.getsource(executor_output_ingress)
        forbidden_fragments = (
            "OpenAI",
            "Ollama",
            "requests",
            "socket",
            "subprocess",
            "os.system",
            "popen",
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            "exec(",
            "eval(",
            "__import__(",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

    def test_evidence_records_on_hold_non_execution_contract(self):
        evidence = build_executor_output_ingress_adapter_evidence()

        self.assertEqual(evidence["created_by"], RUNTIME_INGRESS_ADAPTER)
        self.assertTrue(evidence["executor_output_is_data_not_code"])
        self.assertFalse(evidence["raw_output_trusted_as_decision"])
        self.assertFalse(evidence["validator_pass_is_execution"])
        self.assertFalse(evidence["capability_gate_pass_is_execution"])
        self.assertFalse(evidence["execution_allowed"])
        self.assertFalse(evidence["mutation_allowed"])
        self.assertFalse(evidence["write_authority_granted"])
        self.assertFalse(evidence["store_routing_allowed"])
        self.assertFalse(evidence["store_path_reachable"])
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)

    def test_packet_decision_basis_records_parse_validate_capability_summary(self):
        packet = ingest_executor_output(self._valid_propose_patch())

        self.assertIn("executor_output_is_data_not_code", packet.decision_basis)
        self.assertIn("raw_output_is_not_trusted_decision_or_authority", packet.decision_basis)
        self.assertIn("validator_pass_is_not_execution", packet.decision_basis)
        self.assertIn(
            "capability_gate_pass_is_not_execution_mutation_or_write_authority",
            packet.decision_basis,
        )
        self.assertIn("parse_status=PARSE_OK", packet.decision_basis)
        self.assertIn("validation_status=VALID_STRUCTURED_ACTION", packet.decision_basis)
        self.assertIn(
            "capability_gate_result=CAPABILITY_GATE_LIMITED_ALLOWED",
            packet.decision_basis,
        )
        self.assertIn("safe_default=hold_current_state", packet.decision_basis)

    def _assert_packet_never_grants_authority(self, packet):
        self.assertFalse(packet.execution_allowed)
        self.assertFalse(packet.mutation_allowed)
        self.assertFalse(packet.write_authority_granted)
        self.assertFalse(packet.store_routing_allowed)
        self.assertFalse(packet.store_path_reachable)
        self.assertEqual(packet.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)

    def _valid_propose_patch(self):
        return {
            "action_type": PROPOSE_PATCH,
            "action_id": "action-001",
            "declared_intent": "Propose a reviewable patch.",
            "declared_risk": "LOW",
            "capability_requirements": ["propose_patch"],
            "target_scope": {
                "repo_relative": True,
                "paths": ["src/example.py"],
            },
            "payload": {
                "target_files": ["src/example.py"],
                "patch_summary": "Change is proposed as data only.",
                "patch_plan": ["Edit src/example.py through future mediated review."],
            },
        }

    def _valid_noop(
        self,
        action_type=NOOP,
        capability_requirements=None,
    ):
        requirements = ["noop"] if capability_requirements is None else capability_requirements
        return {
            "action_type": action_type,
            "action_id": "action-noop-001",
            "declared_intent": "No operation.",
            "declared_risk": "LOW",
            "capability_requirements": list(requirements),
            "target_scope": {"repo_relative": True, "paths": []},
            "payload": {},
        }


if __name__ == "__main__":
    unittest.main()
