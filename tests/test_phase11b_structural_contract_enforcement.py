import dataclasses
import unittest

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    ACTION_DECISION_PACKET_VERIFY_REJECTED,
    DENIED_CAPABILITY_STORE_PATH_REJECTED,
    DIRECT_PACKET_SUBMISSION_STORE_PATH_REJECTED,
    DIRECT_STORE_ADJACENT_CANDIDATE_STORE_PATH_REJECTED,
    PACKET_EVIDENCE_STORE_PATH_REJECTED,
    RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
    REPORTED_ONLY_STORE_PATH_REJECTED,
    SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    STRUCTURAL_CONTRACT_ENFORCEMENT_VERSION,
    STRUCTURAL_CONTRACT_REJECTION_FIXTURES_VERSION,
    UNVALIDATED_ACTION_STORE_PATH_REJECTED,
    bind_action_decision_packet_evidence,
    build_structural_contract_rejection_fixture_results,
    build_validator_enforced_routing_batch_evidence,
    evaluate_store_adjacent_candidate_gate,
    expected_action_decision_packet_evidence_hash,
    verify_action_decision_packet_evidence,
)
from src.evidence.executor_output_ingress import (
    ActionDecisionPacket,
    DIRECT_PACKET_EVIDENCE_SUBMISSION_PARSE_REJECTED,
    DIRECT_PACKET_SUBMISSION_PARSE_REJECTED,
    DIRECT_STORE_ADJACENT_CANDIDATE_PARSE_REJECTED,
    PARSE_FAILED,
    RUNTIME_INGRESS_ADAPTER,
    ingest_executor_output,
    is_runtime_built_action_decision_packet,
)
from src.evidence.structured_action_capabilities import CAPABILITY_GATE_ALLOWED
from src.evidence.structured_actions import NOOP, PROPOSE_PATCH


class Phase11bStructuralContractEnforcementTests(unittest.TestCase):
    def test_packet_evidence_requires_runtime_built_packet_argument(self):
        packet = ingest_executor_output(self._valid_propose_patch())
        evidence = bind_action_decision_packet_evidence(packet)

        verified = verify_action_decision_packet_evidence(evidence, packet)
        missing_packet = verify_action_decision_packet_evidence(evidence)

        self.assertTrue(is_runtime_built_action_decision_packet(packet))
        self.assertTrue(evidence["packet_runtime_built_by_ingress"])
        self.assertTrue(verified.accepted)
        self.assertEqual(verified.status, ACTION_DECISION_PACKET_VERIFY_ACCEPTED)
        self.assertFalse(missing_packet.accepted)
        self.assertEqual(missing_packet.status, ACTION_DECISION_PACKET_VERIFY_REJECTED)
        self.assertIn(
            "runtime-built ActionDecisionPacket required for evidence verification",
            missing_packet.rejection_reasons,
        )

    def test_direct_action_decision_packet_shaped_dict_is_rejected(self):
        packet = ingest_executor_output(self._valid_noop("direct-packet-source"))
        direct_submission = {
            "packet_id": packet.packet_id,
            "raw_output_hash": packet.raw_output_hash,
            "parse_status": packet.parse_status,
            "parse_error": packet.parse_error,
            "normalized_action": dict(packet.normalized_action),
            "decision_basis": tuple(packet.decision_basis),
            "adapter_version": packet.adapter_version,
            "created_by": RUNTIME_INGRESS_ADAPTER,
            "execution_allowed": True,
        }

        parsed = ingest_executor_output(direct_submission)
        gate = evaluate_store_adjacent_candidate_gate(direct_submission)
        verify = verify_action_decision_packet_evidence(direct_submission)

        self.assertEqual(parsed.parse_status, PARSE_FAILED)
        self.assertEqual(parsed.parse_error, DIRECT_PACKET_SUBMISSION_PARSE_REJECTED)
        self.assertFalse(gate.candidate_accepted)
        self.assertEqual(gate.gate_status, DIRECT_PACKET_SUBMISSION_STORE_PATH_REJECTED)
        self.assertFalse(verify.accepted)
        self.assertEqual(verify.status, ACTION_DECISION_PACKET_VERIFY_REJECTED)
        self._assert_no_execution_or_store_route(dataclasses.asdict(gate))

    def test_direct_packet_evidence_and_candidate_dicts_are_rejected(self):
        packet = ingest_executor_output(self._valid_propose_patch())
        evidence = bind_action_decision_packet_evidence(packet)
        candidate = dataclasses.asdict(evaluate_store_adjacent_candidate_gate(packet))

        parsed_evidence = ingest_executor_output(evidence)
        parsed_candidate = ingest_executor_output(candidate)
        gate = evaluate_store_adjacent_candidate_gate(candidate)

        self.assertEqual(parsed_evidence.parse_status, PARSE_FAILED)
        self.assertEqual(
            parsed_evidence.parse_error,
            DIRECT_PACKET_EVIDENCE_SUBMISSION_PARSE_REJECTED,
        )
        self.assertEqual(parsed_candidate.parse_status, PARSE_FAILED)
        self.assertEqual(
            parsed_candidate.parse_error,
            DIRECT_STORE_ADJACENT_CANDIDATE_PARSE_REJECTED,
        )
        self.assertFalse(gate.candidate_accepted)
        self.assertEqual(
            gate.gate_status,
            DIRECT_STORE_ADJACENT_CANDIDATE_STORE_PATH_REJECTED,
        )
        self._assert_no_execution_or_store_route(dataclasses.asdict(gate))

    def test_forged_packet_with_runtime_created_by_spoof_is_rejected(self):
        packet = ingest_executor_output(self._valid_noop("forged-packet-source"))
        forged = ActionDecisionPacket(
            packet_id=packet.packet_id,
            raw_output_hash=packet.raw_output_hash,
            parse_status=packet.parse_status,
            parse_error=packet.parse_error,
            normalized_action=dict(packet.normalized_action),
            validation_result=packet.validation_result,
            capability_result=packet.capability_result,
            decision_basis=tuple(packet.decision_basis),
            ignored_reported_only_fields=tuple(packet.ignored_reported_only_fields),
            created_by=RUNTIME_INGRESS_ADAPTER,
        )

        evidence = bind_action_decision_packet_evidence(forged)
        verify = verify_action_decision_packet_evidence(evidence, forged)
        gate = evaluate_store_adjacent_candidate_gate(forged)

        self.assertFalse(is_runtime_built_action_decision_packet(forged))
        self.assertTrue(evidence["packet_runtime_owned"])
        self.assertFalse(evidence["packet_runtime_built_by_ingress"])
        self.assertFalse(verify.accepted)
        self.assertIn(
            "packet was not built by runtime ingress adapter",
            verify.rejection_reasons,
        )
        self.assertFalse(gate.candidate_accepted)
        self.assertEqual(gate.gate_status, PACKET_EVIDENCE_STORE_PATH_REJECTED)
        self._assert_no_execution_or_store_route(dataclasses.asdict(gate))

    def test_self_report_fields_do_not_make_store_adjacent_candidate(self):
        cases = (
            ("created_by", RUNTIME_INGRESS_ADAPTER),
            ("packet_id", "action-decision-packet-forged"),
            ("capability_gate_result", CAPABILITY_GATE_ALLOWED),
            ("execution_allowed", True),
            ("mutation_allowed", True),
            ("write_authority_granted", True),
            ("store_routing_allowed", True),
            ("store_path_reachable", True),
        )

        for field, value in cases:
            with self.subTest(field=field):
                packet = ingest_executor_output(
                    {
                        "action": self._valid_noop(f"self-report-{field}"),
                        field: value,
                    }
                )
                evidence = bind_action_decision_packet_evidence(packet)
                gate = evaluate_store_adjacent_candidate_gate(packet)

                self.assertIn(f"raw_output.{field}", packet.ignored_reported_only_fields)
                self.assertFalse(evidence["store_adjacent_candidate_eligible"])
                self.assertFalse(gate.candidate_accepted)
                self.assertEqual(
                    gate.gate_status,
                    SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
                )
                self._assert_no_execution_or_store_route(dataclasses.asdict(gate))

    def test_evidence_verify_rejects_store_field_self_report_after_rehash(self):
        packet = ingest_executor_output(self._valid_noop("evidence-overclaim"))
        evidence = bind_action_decision_packet_evidence(packet)

        for field in ("store_routing_allowed", "store_path_reachable"):
            with self.subTest(field=field):
                tampered = dict(evidence)
                tampered[field] = True
                tampered["store_adjacent_candidate_eligible"] = False
                tampered["action_decision_packet_evidence_hash"] = (
                    expected_action_decision_packet_evidence_hash(tampered)
                )

                verify = verify_action_decision_packet_evidence(tampered, packet)

                self.assertFalse(verify.accepted)
                self.assertTrue(
                    any(field in reason for reason in verify.rejection_reasons),
                    verify.rejection_reasons,
                )

    def test_store_adjacent_rejects_raw_unvalidated_denied_and_reported_only(self):
        cases = (
            (
                "raw_output_skipping_ingress",
                self._valid_noop("raw-skips-ingress"),
                RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
            ),
            (
                "unvalidated_action",
                ingest_executor_output({"action_type": NOOP, "action_id": "missing"}),
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
                "reported_only_authority",
                ingest_executor_output(
                    self._valid_noop(
                        "reported-only-authority",
                        payload={
                            "authority": "write_file",
                            "approved_by_executor": True,
                        },
                    )
                ),
                REPORTED_ONLY_STORE_PATH_REJECTED,
            ),
        )

        for label, candidate, expected_status in cases:
            with self.subTest(label=label):
                gate = evaluate_store_adjacent_candidate_gate(candidate)

                self.assertFalse(gate.candidate_accepted)
                self.assertEqual(gate.gate_status, expected_status)
                self._assert_no_execution_or_store_route(dataclasses.asdict(gate))

    def test_structural_rejection_fixture_builder_covers_required_cases(self):
        records = build_structural_contract_rejection_fixture_results()
        by_name = {record["fixture_name"]: record for record in records}

        self.assertEqual(
            set(by_name),
            {
                "direct_action_decision_packet_shaped_dict",
                "created_by_runtime_ingress_adapter_spoof",
                "packet_id_spoof",
                "capability_gate_allowed_self_report",
                "execution_allowed_true",
                "mutation_allowed_true",
                "write_authority_granted_true",
                "store_routing_allowed_true",
                "store_path_reachable_true",
                "raw_output_skipping_ingress",
                "unvalidated_action_reaching_store_adjacent_path",
                "denied_capability_reaching_store_adjacent_path",
                "reported_only_authority_reaching_store_adjacent_path",
                "direct_store_adjacent_candidate_submission",
            },
        )

        expected_statuses = {
            "direct_action_decision_packet_shaped_dict": (
                DIRECT_PACKET_SUBMISSION_STORE_PATH_REJECTED
            ),
            "created_by_runtime_ingress_adapter_spoof": (
                SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED
            ),
            "packet_id_spoof": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
            "capability_gate_allowed_self_report": (
                SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED
            ),
            "execution_allowed_true": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
            "mutation_allowed_true": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
            "write_authority_granted_true": (
                SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED
            ),
            "store_routing_allowed_true": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
            "store_path_reachable_true": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
            "raw_output_skipping_ingress": RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
            "unvalidated_action_reaching_store_adjacent_path": (
                UNVALIDATED_ACTION_STORE_PATH_REJECTED
            ),
            "denied_capability_reaching_store_adjacent_path": (
                DENIED_CAPABILITY_STORE_PATH_REJECTED
            ),
            "reported_only_authority_reaching_store_adjacent_path": (
                REPORTED_ONLY_STORE_PATH_REJECTED
            ),
            "direct_store_adjacent_candidate_submission": (
                DIRECT_STORE_ADJACENT_CANDIDATE_STORE_PATH_REJECTED
            ),
        }

        for name, expected_status in expected_statuses.items():
            with self.subTest(name=name):
                record = by_name[name]
                self.assertEqual(
                    record["fixture_set_version"],
                    STRUCTURAL_CONTRACT_REJECTION_FIXTURES_VERSION,
                )
                self.assertEqual(record["expected_gate_status"], expected_status)
                self.assertEqual(record["actual_gate_status"], expected_status)
                self.assertFalse(record["candidate_accepted"])
                self._assert_no_execution_or_store_route(record)

    def test_batch_evidence_records_structural_contract_rules(self):
        evidence = build_validator_enforced_routing_batch_evidence()

        self.assertEqual(
            evidence["structural_contract_enforcement_version"],
            STRUCTURAL_CONTRACT_ENFORCEMENT_VERSION,
        )
        self.assertEqual(
            evidence["phase11b_3_1_structural_contract_enforcement"],
            "COMPLETE",
        )
        self.assertEqual(evidence["structural_contract_rejection_fixture_count"], 14)
        self.assertTrue(evidence["action_decision_packet_runtime_built_only"])
        self.assertTrue(evidence["direct_action_decision_packet_submission_rejected"])
        self.assertTrue(evidence["direct_packet_evidence_submission_rejected"])
        self.assertTrue(evidence["direct_store_adjacent_candidate_submission_rejected"])
        self.assertFalse(evidence["executor_self_report_is_authority"])
        self.assertFalse(evidence["capability_gate_self_report_is_authority"])
        self.assertFalse(evidence["valid_structured_action_is_authorized_capability"])
        self.assertFalse(evidence["authorized_capability_is_action_executed"])
        self.assertFalse(evidence["propose_patch_is_write"])
        self.assertFalse(evidence["propose_patch_is_mutation"])
        self.assertFalse(evidence["metadata_only_candidate_is_store_write"])
        self.assertFalse(evidence["store_adjacent_metadata_is_store_path_reachability"])
        self._assert_no_execution_or_store_route(evidence)

    def test_valid_runtime_built_propose_patch_still_yields_metadata_only_candidate(self):
        packet = ingest_executor_output(self._valid_propose_patch())

        gate = evaluate_store_adjacent_candidate_gate(packet)

        self.assertTrue(gate.candidate_accepted)
        self.assertEqual(gate.gate_status, STORE_ADJACENT_CANDIDATE_ACCEPTED)
        self._assert_no_execution_or_store_route(dataclasses.asdict(gate))

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
        capability_requirements=("noop",),
        payload=None,
    ):
        return {
            "action_type": NOOP,
            "action_id": action_id,
            "declared_intent": "No operation.",
            "declared_risk": "LOW",
            "capability_requirements": list(capability_requirements),
            "target_scope": {"repo_relative": True, "paths": []},
            "payload": dict(payload or {}),
        }


if __name__ == "__main__":
    unittest.main()
