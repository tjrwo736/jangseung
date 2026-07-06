import unittest
from pathlib import Path

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    SAFE_DEFAULT,
    STORE_ADJACENT_PACKET_ORIGIN_BASIS_RUNTIME_BUILD_PATH,
    STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_LABEL,
    STORE_ADJACENT_RUNTIME_SEAL_LIMITS,
)
from src.evidence.store_adjacent_runtime_seal import (
    STORE_ADJACENT_RUNTIME_SEAL_VERIFY_ACCEPTED,
    STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED,
    build_store_adjacent_runtime_seal_metadata,
    expected_store_adjacent_runtime_seal_metadata_hash,
    verify_store_adjacent_runtime_seal_metadata,
)


class Phase11BStoreAdjacentRuntimeSealTests(unittest.TestCase):
    def test_runtime_seal_evidence_accepts_only_metadata_only_store_adjacent_candidate(self):
        evidence = build_store_adjacent_runtime_seal_metadata(
            raw_store_sink_bypass_rejected=True,
            direct_write_json_bypass_created_files_count=0,
            direct_ledger_bypass_appended_count=0,
            trusted_runtime_write_preserved=True,
            trusted_runtime_ledger_preserved=True,
            fallback_to_unwired=False,
        )

        verify = verify_store_adjacent_runtime_seal_metadata(evidence)

        self.assertTrue(verify["accepted"])
        self.assertEqual(verify["status"], STORE_ADJACENT_RUNTIME_SEAL_VERIFY_ACCEPTED)
        self.assertEqual(
            evidence["phase11b_3_6_store_adjacent_runtime_seal_label"],
            STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_LABEL,
        )
        self.assertEqual(
            tuple(evidence["phase11b_3_6_store_adjacent_runtime_seal_limits"]),
            STORE_ADJACENT_RUNTIME_SEAL_LIMITS,
        )
        self.assertTrue(evidence["store_adjacent_runtime_seal_enabled"])
        self.assertTrue(evidence["runtime_build_packet_only_enforced"])
        self.assertEqual(
            evidence["packet_origin_basis"],
            STORE_ADJACENT_PACKET_ORIGIN_BASIS_RUNTIME_BUILD_PATH,
        )
        self.assertTrue(evidence["direct_packet_submission_rejected"])
        self.assertTrue(evidence["executor_built_packet_rejected"])
        self.assertTrue(evidence["created_by_text_ownership_rejected"])
        self.assertTrue(evidence["packet_id_text_ownership_rejected"])
        self.assertTrue(evidence["capability_gate_result_self_report_rejected"])
        self.assertTrue(evidence["execution_self_report_rejected"])
        self.assertTrue(evidence["mutation_self_report_rejected"])
        self.assertTrue(evidence["write_authority_self_report_rejected"])
        self.assertTrue(evidence["store_routing_self_report_rejected"])
        self.assertTrue(evidence["store_path_self_report_rejected"])
        self.assertTrue(evidence["live_executor_self_report_rejected"])
        self.assertTrue(evidence["authority_promotion_rejected"])
        self.assertTrue(evidence["raw_store_adjacent_path_rejected"])
        self.assertTrue(evidence["unvalidated_store_adjacent_path_rejected"])
        self.assertTrue(evidence["denied_store_adjacent_path_rejected"])
        self.assertTrue(evidence["reported_only_store_adjacent_path_rejected"])
        self.assertTrue(evidence["accepted_store_adjacent_candidate_metadata_only"])
        self.assertFalse(evidence["accepted_store_adjacent_candidate_store_routing_allowed"])
        self.assertFalse(evidence["accepted_store_adjacent_candidate_store_path_reachable"])
        self.assertFalse(evidence["accepted_store_adjacent_candidate_execution_allowed"])
        self.assertFalse(evidence["accepted_store_adjacent_candidate_mutation_allowed"])
        self.assertFalse(evidence["accepted_store_adjacent_candidate_write_authority_granted"])
        self.assertEqual(evidence["direct_write_json_bypass_created_files_count"], 0)
        self.assertEqual(evidence["direct_ledger_bypass_appended_count"], 0)
        self.assertTrue(evidence["trusted_runtime_write_preserved"])
        self.assertTrue(evidence["trusted_runtime_ledger_preserved"])
        self.assertEqual(evidence.get("live_executor_authority"), None)
        self.assertEqual(verify["safe_default"], SAFE_DEFAULT)

    def test_runtime_seal_verify_rejects_rehashed_overclaims(self):
        base = build_store_adjacent_runtime_seal_metadata(
            raw_store_sink_bypass_rejected=True,
            direct_write_json_bypass_created_files_count=0,
            direct_ledger_bypass_appended_count=0,
            trusted_runtime_write_preserved=True,
            trusted_runtime_ledger_preserved=True,
            fallback_to_unwired=False,
        )
        cases = (
            ("executor_built_packet_rejected", False, "executor_built_packet_rejected must be true"),
            ("packet_origin_basis", "packet_id_text", "packet_origin_basis mismatch"),
            (
                "direct_write_json_bypass_created_files_count",
                1,
                "direct write_json bypass created files count must be 0",
            ),
            (
                "direct_ledger_bypass_appended_count",
                1,
                "direct ledger bypass appended count must be 0",
            ),
            (
                "accepted_store_adjacent_candidate_store_path_reachable",
                True,
                "accepted_store_adjacent_candidate_store_path_reachable=true rejected",
            ),
            ("live_executor_authority", "PROMOTED", "live executor authority promotion rejected"),
            ("safe_default", "changed", "safe_default must remain hold_current_state"),
        )

        for field, value, expected_reason in cases:
            with self.subTest(field=field):
                tampered = dict(base)
                tampered[field] = value
                tampered["store_adjacent_runtime_seal_metadata_hash"] = (
                    expected_store_adjacent_runtime_seal_metadata_hash(tampered)
                )

                verify = verify_store_adjacent_runtime_seal_metadata(tampered)

                self.assertFalse(verify["accepted"])
                self.assertEqual(verify["status"], STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED)
                self.assertTrue(
                    any(expected_reason in reason for reason in verify["rejection_reasons"]),
                    verify["rejection_reasons"],
                )

    def test_fallback_used_cannot_claim_success(self):
        evidence = build_store_adjacent_runtime_seal_metadata(
            raw_store_sink_bypass_rejected=True,
            direct_write_json_bypass_created_files_count=0,
            direct_ledger_bypass_appended_count=0,
            trusted_runtime_write_preserved=True,
            trusted_runtime_ledger_preserved=True,
            fallback_to_unwired=True,
        )
        evidence["fallback_to_unwired"] = True
        evidence["fallback_success_claimed"] = True
        evidence["store_adjacent_runtime_seal_metadata_hash"] = (
            expected_store_adjacent_runtime_seal_metadata_hash(evidence)
        )

        verify = verify_store_adjacent_runtime_seal_metadata(evidence)

        self.assertFalse(verify["accepted"])
        self.assertEqual(verify["status"], STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED)
        self.assertIn("fallback used but success claimed", verify["rejection_reasons"])
        self.assertEqual(verify["safe_default"], SAFE_DEFAULT)
        self.assertEqual(LIVE_EXECUTOR_AUTHORITY_ON_HOLD, "LIVE_EXECUTOR_AUTHORITY_ON_HOLD")

    def test_phase_doc_records_label_limits_and_hold_status(self):
        doc = Path("docs/phase11b_3_6_store_adjacent_runtime_seal_v0.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_LABEL, doc)
        for limit in STORE_ADJACENT_RUNTIME_SEAL_LIMITS:
            self.assertIn(limit, doc)
        self.assertIn("packet_origin_basis = runtime_build_path", doc)
        self.assertIn("direct_write_json_bypass_created_files_count = 0", doc)
        self.assertIn("direct_ledger_bypass_appended_count = 0", doc)
        self.assertIn("trusted_runtime_write_preserved = true", doc)
        self.assertIn("trusted_runtime_ledger_preserved = true", doc)
        self.assertIn("live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD", doc)
        self.assertIn("safe default = hold_current_state", doc)

        forbidden_labels = (
            "LIVE_EXECUTOR_" + "READY",
            "MODEL_EXECUTOR_" + "READY",
            "WRITE_AUTHORITY_" + "SAFE",
            "ACTION_EXECUTION_" + "READY",
            "MUTATION_AUTHORITY_" + "GRANTED",
            "PROVIDER_" + "READY",
            "STORE_WRITE_" + "READY",
            "PATCH_" + "APPLIED",
            "BYPASS_" + "IMPOSSIBLE",
            "TAMPER_" + "PROOF",
            "ARBITRARY_CODE_" + "SAFE",
        )
        doc_lines = {line.strip() for line in doc.splitlines()}
        for label in forbidden_labels:
            with self.subTest(label=label):
                self.assertNotIn(label, doc_lines)


if __name__ == "__main__":
    unittest.main()
