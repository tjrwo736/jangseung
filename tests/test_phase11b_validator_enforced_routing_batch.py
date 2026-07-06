import dataclasses
import inspect
import unittest

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import action_decision_routing
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    ACTION_DECISION_PACKET_VERIFY_REJECTED,
    DENIED_CAPABILITY_STORE_PATH_REJECTED,
    PACKET_EVIDENCE_STORE_PATH_REJECTED,
    RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
    REPORTED_ONLY_STORE_PATH_REJECTED,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    STORE_ADJACENT_CANDIDATE_GATE_VERSION,
    STORE_PATH_REJECTION_FIXTURES_VERSION,
    UNVALIDATED_ACTION_STORE_PATH_REJECTED,
    bind_action_decision_packet_evidence,
    build_store_path_rejection_fixture_results,
    build_validator_enforced_routing_batch_evidence,
    evaluate_store_adjacent_candidate_gate,
    expected_action_decision_packet_evidence_hash,
    verify_action_decision_packet_evidence,
)
from src.evidence.executor_output_ingress import (
    PARSE_OK,
    RUNTIME_INGRESS_ADAPTER,
    ingest_executor_output,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_DENIED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
)
from src.evidence.structured_actions import (
    NOOP,
    PROCESS_SPAWN,
    PROPOSE_PATCH,
    VALID_STRUCTURED_ACTION,
)


class Phase11bValidatorEnforcedRoutingBatchTests(unittest.TestCase):
    def test_action_decision_packet_evidence_binding_verifies_valid_packet(self):
        packet = ingest_executor_output(self._valid_propose_patch())

        evidence = bind_action_decision_packet_evidence(packet)
        verify = verify_action_decision_packet_evidence(evidence, packet)

        self.assertEqual(packet.parse_status, PARSE_OK)
        self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(packet.capability_result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
        self.assertTrue(verify.accepted)
        self.assertEqual(verify.status, ACTION_DECISION_PACKET_VERIFY_ACCEPTED)
        self.assertEqual(evidence["packet_id"], packet.packet_id)
        self.assertEqual(evidence["packet_created_by"], RUNTIME_INGRESS_ADAPTER)
        self.assertTrue(evidence["packet_runtime_owned"])
        self.assertTrue(evidence["validator_enforced_routing_required"])
        self.assertTrue(evidence["executor_output_ingress_required"])
        self.assertTrue(evidence["structured_action_validation_required"])
        self.assertTrue(evidence["capability_gate_required"])
        self.assertTrue(evidence["store_path_accepts_only_runtime_owned_decision"])
        self.assertTrue(evidence["store_adjacent_candidate_eligible"])
        self.assertEqual(
            evidence["action_decision_packet_evidence_hash"],
            expected_action_decision_packet_evidence_hash(evidence),
        )
        self._assert_no_execution_or_store_route(evidence)

    def test_evidence_verify_rejects_store_and_authority_overclaims(self):
        packet = ingest_executor_output(self._valid_propose_patch())
        evidence = bind_action_decision_packet_evidence(packet)
        overclaim_fields = (
            "raw_executor_output_reaches_store",
            "unvalidated_action_reaches_store",
            "denied_capability_reaches_store",
            "reported_only_authority_reaches_store",
            "execution_allowed",
            "mutation_allowed",
            "write_authority_granted",
            "live_executor_ready",
        )

        for field in overclaim_fields:
            with self.subTest(field=field):
                tampered = dict(evidence)
                tampered[field] = True
                tampered["action_decision_packet_evidence_hash"] = (
                    expected_action_decision_packet_evidence_hash(tampered)
                )

                verify = verify_action_decision_packet_evidence(tampered, packet)

                self.assertFalse(verify.accepted)
                self.assertEqual(verify.status, ACTION_DECISION_PACKET_VERIFY_REJECTED)
                self.assertTrue(
                    any(field in reason for reason in verify.rejection_reasons),
                    verify.rejection_reasons,
                )

    def test_evidence_verify_rejects_runtime_packet_mismatch_after_rehash(self):
        packet = ingest_executor_output(self._valid_propose_patch())
        evidence = bind_action_decision_packet_evidence(packet)
        tampered = dict(evidence)
        tampered["capability_gate_result"] = "CAPABILITY_GATE_ALLOWED"
        tampered["store_adjacent_candidate_eligible"] = True
        tampered["action_decision_packet_evidence_hash"] = (
            expected_action_decision_packet_evidence_hash(tampered)
        )

        verify = verify_action_decision_packet_evidence(tampered, packet)

        self.assertFalse(verify.accepted)
        self.assertTrue(
            any("capability_gate_result mismatch" in reason for reason in verify.rejection_reasons),
            verify.rejection_reasons,
        )

    def test_store_adjacent_guard_accepts_only_metadata_candidate_for_valid_packet(self):
        packet = ingest_executor_output(self._valid_propose_patch())

        result = evaluate_store_adjacent_candidate_gate(packet)

        self.assertTrue(result.candidate_accepted)
        self.assertEqual(result.gate_status, STORE_ADJACENT_CANDIDATE_ACCEPTED)
        self.assertEqual(result.packet_id, packet.packet_id)
        self.assertEqual(result.evidence_verification_status, ACTION_DECISION_PACKET_VERIFY_ACCEPTED)
        self.assertEqual(
            result.store_adjacent_candidate_gate_version,
            STORE_ADJACENT_CANDIDATE_GATE_VERSION,
        )
        self.assertTrue(result.store_adjacent_candidate)
        self.assertTrue(result.store_adjacent_candidate_gate_metadata_only)
        self._assert_no_execution_or_store_route(dataclasses.asdict(result))

    def test_store_adjacent_guard_rejects_raw_and_unsupported_executor_output(self):
        cases = (
            self._valid_noop("raw-direct-action"),
            '{"action_type": "NOOP"}',
            ("opaque", "executor", "output"),
        )

        for candidate in cases:
            with self.subTest(candidate_type=type(candidate).__name__):
                result = evaluate_store_adjacent_candidate_gate(candidate)

                self.assertFalse(result.candidate_accepted)
                self.assertEqual(result.gate_status, RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED)
                self.assertFalse(result.store_adjacent_candidate)
                self._assert_no_execution_or_store_route(dataclasses.asdict(result))

    def test_store_adjacent_guard_rejects_unvalidated_denied_and_reported_only_packets(self):
        cases = (
            (
                "unvalidated",
                ingest_executor_output(
                    {
                        "action_type": NOOP,
                        "action_id": "missing-required-fields",
                    }
                ),
                UNVALIDATED_ACTION_STORE_PATH_REJECTED,
            ),
            (
                "forbidden_action",
                ingest_executor_output(self._valid_noop("forbidden", action_type=PROCESS_SPAWN)),
                UNVALIDATED_ACTION_STORE_PATH_REJECTED,
            ),
            (
                "denied_capability",
                ingest_executor_output(
                    self._valid_noop(
                        "denied-capability",
                        capability_requirements=("network",),
                    )
                ),
                DENIED_CAPABILITY_STORE_PATH_REJECTED,
            ),
            (
                "reported_only",
                ingest_executor_output(
                    self._valid_noop(
                        "reported-only",
                        payload={
                            "authority": "write_file",
                            "approved_by_executor": True,
                        },
                    )
                ),
                REPORTED_ONLY_STORE_PATH_REJECTED,
            ),
        )

        for label, packet, expected_status in cases:
            with self.subTest(label=label):
                result = evaluate_store_adjacent_candidate_gate(packet)

                self.assertFalse(result.candidate_accepted)
                self.assertEqual(result.gate_status, expected_status)
                self.assertFalse(result.store_adjacent_candidate)
                self._assert_no_execution_or_store_route(dataclasses.asdict(result))

        denied = cases[2][1]
        reported = cases[3][1]
        self.assertEqual(denied.validation_result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(denied.capability_result.gate_result, CAPABILITY_DENIED)
        self.assertEqual(
            reported.capability_result.gate_result,
            REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
        )

    def test_store_adjacent_guard_rejects_tampered_packet_authority_flags(self):
        packet = ingest_executor_output(self._valid_propose_patch())
        tampered_packets = (
            dataclasses.replace(packet, execution_allowed=True),
            dataclasses.replace(packet, mutation_allowed=True),
            dataclasses.replace(packet, write_authority_granted=True),
            dataclasses.replace(packet, store_routing_allowed=True),
            dataclasses.replace(packet, store_path_reachable=True),
            dataclasses.replace(packet, created_by="executor_self_report"),
            dataclasses.replace(packet, live_executor_authority="LIVE_EXECUTOR_AUTHORITY_GRANTED"),
        )

        for tampered in tampered_packets:
            with self.subTest(packet=tampered):
                result = evaluate_store_adjacent_candidate_gate(tampered)

                self.assertFalse(result.candidate_accepted)
                self.assertEqual(result.gate_status, PACKET_EVIDENCE_STORE_PATH_REJECTED)
                self._assert_no_execution_or_store_route(dataclasses.asdict(result))

    def test_rejection_fixture_builder_records_raw_unvalidated_denied_reported_only(self):
        records = build_store_path_rejection_fixture_results()
        by_name = {record["fixture_name"]: record for record in records}

        self.assertEqual(
            set(by_name),
            {
                "raw_executor_output",
                "unsupported_executor_output",
                "unvalidated_action_packet",
                "denied_capability_packet",
                "reported_only_authority_packet",
            },
        )
        self.assertEqual(
            by_name["raw_executor_output"]["actual_gate_status"],
            RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
        )
        self.assertEqual(
            by_name["unsupported_executor_output"]["actual_gate_status"],
            RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
        )
        self.assertEqual(
            by_name["unvalidated_action_packet"]["actual_gate_status"],
            UNVALIDATED_ACTION_STORE_PATH_REJECTED,
        )
        self.assertEqual(
            by_name["denied_capability_packet"]["actual_gate_status"],
            DENIED_CAPABILITY_STORE_PATH_REJECTED,
        )
        self.assertEqual(
            by_name["reported_only_authority_packet"]["actual_gate_status"],
            REPORTED_ONLY_STORE_PATH_REJECTED,
        )

        for record in records:
            with self.subTest(fixture=record["fixture_name"]):
                self.assertEqual(record["fixture_set_version"], STORE_PATH_REJECTION_FIXTURES_VERSION)
                self.assertEqual(record["expected_gate_status"], record["actual_gate_status"])
                self.assertFalse(record["candidate_accepted"])
                self._assert_no_execution_or_store_route(record)

    def test_batch_evidence_records_required_flow_and_safe_default(self):
        evidence = build_validator_enforced_routing_batch_evidence()

        self.assertEqual(
            evidence["phase11b_2_2_action_decision_packet_evidence_binding"],
            "COMPLETE",
        )
        self.assertEqual(evidence["phase11b_2_3_store_adjacent_routing_guard"], "COMPLETE")
        self.assertEqual(evidence["phase11b_2_4_rejection_fixtures"], "COMPLETE")
        self.assertEqual(
            evidence["flow"],
            (
                "raw_executor_output",
                "executor_output_ingress_adapter",
                "parse_normalize",
                "validate_structured_action",
                "evaluate_action_capabilities",
                "runtime_owned_action_decision_packet",
                "action_decision_packet_evidence_binding",
                "verify_action_decision_packet_evidence",
                "store_adjacent_candidate_gate_metadata_only",
                "stop",
            ),
        )
        self.assertEqual(evidence["store_path_rejection_fixture_count"], 5)
        self.assertTrue(evidence["store_path_accepts_only_runtime_owned_decision"])
        self.assertTrue(evidence["store_adjacent_candidate_gate_metadata_only"])
        self._assert_no_execution_or_store_route(evidence)

    def test_guard_module_has_no_runtime_execution_or_mutation_surface(self):
        source = inspect.getsource(action_decision_routing)
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
            ".chmod(",
            ".chown(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "exec(",
            "eval(",
            "__import__(",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

    def _assert_no_execution_or_store_route(self, record):
        self.assertFalse(record["execution_allowed"])
        self.assertFalse(record["mutation_allowed"])
        self.assertFalse(record["write_authority_granted"])
        self.assertFalse(record["store_routing_allowed"])
        self.assertFalse(record["store_path_reachable"])
        self.assertFalse(record["live_executor_ready"])
        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["safe_default"], SAFE_DEFAULT)

    def _valid_propose_patch(self):
        return {
            "action_type": PROPOSE_PATCH,
            "action_id": "action-propose-patch",
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
        action_id,
        *,
        action_type=NOOP,
        capability_requirements=("noop",),
        payload=None,
    ):
        return {
            "action_type": action_type,
            "action_id": action_id,
            "declared_intent": "No operation.",
            "declared_risk": "LOW",
            "capability_requirements": list(capability_requirements),
            "target_scope": {"repo_relative": True, "paths": []},
            "payload": dict(payload or {}),
        }


if __name__ == "__main__":
    unittest.main()
