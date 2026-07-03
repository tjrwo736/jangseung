from copy import deepcopy
import inspect
import unittest

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_CHECKED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    REPORTED_ONLY,
    SAFE_DEFAULT,
)
from src.evidence import b3_capability_policy_evidence
from src.evidence.b3_capability_policy_contract import (
    CAPABILITY_FIELDS,
    CHECK_STATUS_CHECKED,
    GRANT_SOURCE_EVIDENCE,
    GRANT_SOURCE_UNKNOWN,
    VALID_CONTRACT,
    build_default_capability_policy_contract,
    clone_default_capability_policy_contract,
    validate_capability_policy_contract,
)
from src.evidence.b3_capability_policy_evidence import (
    AUTHORITY_SNAPSHOT,
    B3_CAPABILITY_POLICY_EVIDENCE_KIND,
    B3_CAPABILITY_POLICY_EVIDENCE_VERSION,
    VERIFY_REPLAY_ACCEPTED,
    VERIFY_REPLAY_REJECTED,
    build_capability_policy_evidence_record,
    capability_policy_digest,
    capability_policy_evidence_digest,
    verify_capability_policy_evidence_record,
)


class B3CapabilityPolicyEvidenceVerifyTests(unittest.TestCase):
    def test_default_contract_builds_deterministic_evidence_record(self):
        contract = build_default_capability_policy_contract()
        validation = validate_capability_policy_contract(contract)

        first = build_capability_policy_evidence_record(contract, validation)
        second = build_capability_policy_evidence_record(contract, validation)

        self.assertEqual(first, second)
        self.assertEqual(first["record_kind"], B3_CAPABILITY_POLICY_EVIDENCE_KIND)
        self.assertEqual(first["record_version"], B3_CAPABILITY_POLICY_EVIDENCE_VERSION)
        self.assertEqual(first["claim_type"], "policy_validation_evidence_not_capability_grant")
        self.assertEqual(first["capability_policy_digest"], capability_policy_digest(contract))
        self.assertEqual(first["policy_validation_outcome"]["status"], VALID_CONTRACT)
        self.assertEqual(first["authority_snapshot"], AUTHORITY_SNAPSHOT)
        self.assertEqual(len(first["deterministic_evidence_digest"]), 64)
        self.assertEqual(first["deterministic_evidence_digest"], capability_policy_evidence_digest(first))
        self.assertEqual(
            first["source_contract_module_version_note"]["module"],
            "src.evidence.b3_capability_policy_contract",
        )
        for capability_name in CAPABILITY_FIELDS:
            summary = first["capability_fields_summary"][capability_name]
            self.assertFalse(summary["granted"])
            self.assertEqual(summary["check_status"], NOT_CHECKED)
        self.assertIn("no live executor", first["non_claim_caveats"])

    def test_verify_replay_accepts_untampered_record(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)

        verify = verify_capability_policy_evidence_record(record, contract)

        self.assertTrue(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_ACCEPTED)
        self.assertEqual(verify["rejection_reasons"], [])
        self.assertFalse(verify["is_runtime_enforcement"])
        self.assertFalse(verify["is_tool_execution_gate"])
        self.assertEqual(verify["safe_default"], SAFE_DEFAULT)

    def test_verify_replay_rejects_capability_field_mismatch_even_when_rebound(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)
        tampered = deepcopy(record)
        tampered["capability_fields_summary"]["network_authority"]["granted"] = True
        tampered["deterministic_evidence_digest"] = capability_policy_evidence_digest(tampered)

        verify = verify_capability_policy_evidence_record(tampered, contract)

        self.assert_rejected_with(verify, "capability_fields_summary mismatch")

    def test_verify_replay_rejects_policy_digest_mismatch_even_when_rebound(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)
        tampered = deepcopy(record)
        tampered["capability_policy_digest"] = "0" * 64
        tampered["deterministic_evidence_digest"] = capability_policy_evidence_digest(tampered)

        verify = verify_capability_policy_evidence_record(tampered, contract)

        self.assert_rejected_with(verify, "capability_policy_digest mismatch")

    def test_verify_replay_rejects_evidence_digest_tamper(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)
        tampered = deepcopy(record)
        tampered["capability_fields_summary"]["raw_shell_authority"]["claim_status"] = "PASS"

        verify = verify_capability_policy_evidence_record(tampered, contract)

        self.assert_rejected_with(verify, "deterministic evidence digest mismatch")

    def test_verify_replay_rejects_authority_snapshot_mismatch_even_when_rebound(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)
        tampered = deepcopy(record)
        tampered["authority_snapshot"]["safe_default"] = "promoted"
        tampered["deterministic_evidence_digest"] = capability_policy_evidence_digest(tampered)

        verify = verify_capability_policy_evidence_record(tampered, contract)

        self.assert_rejected_with(verify, "authority_snapshot mismatch")
        self.assert_rejected_with(verify, "authority snapshot mismatch")

    def test_verify_replay_rejects_validation_outcome_mismatch_even_when_rebound(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)
        tampered = deepcopy(record)
        tampered["policy_validation_outcome"]["status"] = "FORGED"
        tampered["deterministic_evidence_digest"] = capability_policy_evidence_digest(tampered)

        verify = verify_capability_policy_evidence_record(tampered, contract)

        self.assert_rejected_with(verify, "policy_validation_outcome mismatch")

    def test_verify_replay_rejects_granted_true_missing_evidence(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["network_authority"]
        policy["granted"] = True
        policy["grant_source"] = GRANT_SOURCE_EVIDENCE
        policy["check_status"] = CHECK_STATUS_CHECKED
        record = build_capability_policy_evidence_record(contract)

        verify = verify_capability_policy_evidence_record(record, contract)

        self.assert_rejected_with(verify, "policy replay rejected: network_authority granted=true requires evidence_ref")
        self.assert_rejected_with(verify, "network_authority granted=true missing evidence rejected")

    def test_verify_replay_rejects_reported_only_pass_like_claim(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["raw_shell_authority"]
        policy["grant_source"] = REPORTED_ONLY
        policy["claim_status"] = "PASS"
        record = build_capability_policy_evidence_record(contract)

        verify = verify_capability_policy_evidence_record(record, contract)

        self.assert_rejected_with(
            verify,
            "policy replay rejected: raw_shell_authority reported-only source cannot support PASS-like claim",
        )
        self.assert_rejected_with(verify, "raw_shell_authority reported_only PASS-like claim rejected")

    def test_verify_replay_rejects_not_checked_pass_like_claim(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["write_file_authority"]
        policy["claim_status"] = "PASS"
        record = build_capability_policy_evidence_record(contract)

        verify = verify_capability_policy_evidence_record(record, contract)

        self.assert_rejected_with(
            verify,
            "policy replay rejected: write_file_authority unchecked status cannot support PASS-like claim",
        )
        self.assert_rejected_with(verify, "write_file_authority unchecked PASS-like claim rejected")

    def test_verify_replay_rejects_unknown_grant_source_with_granted_true(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["process_spawn_authority"]
        policy["granted"] = True
        policy["grant_source"] = GRANT_SOURCE_UNKNOWN
        policy["check_status"] = CHECK_STATUS_CHECKED
        policy["evidence_ref"] = "future-evidence-placeholder"
        record = build_capability_policy_evidence_record(contract)

        verify = verify_capability_policy_evidence_record(record, contract)

        self.assert_rejected_with(
            verify,
            "policy replay rejected: process_spawn_authority granted=true cannot use unknown grant source",
        )
        self.assert_rejected_with(verify, "process_spawn_authority granted=true unknown source rejected")

    def test_verify_replay_rejects_contract_and_evidence_overclaim_cases(self):
        cases = (
            ("physical_impossibility_claimed", "physical impossibility claim rejected"),
            ("outside_denial_claimed", "outside denial claim rejected"),
            ("externally_enforced_denial_claimed", "external denial claim rejected"),
            ("composition_safe_claimed", "composition closure claim rejected"),
            ("bypass_impossible_claimed", "bypass impossibility claim rejected"),
            ("structured_tool_safe_claimed", "structured tool safety claim rejected"),
            ("live_executor_ready_claimed", "live executor ready claim rejected"),
            ("phase11a_started_claimed", "Phase 11-A started claim rejected"),
            ("b3_closure_claimed", "B3 closure claim rejected"),
            ("runtime_enforcement_claimed", "runtime enforcement claim rejected"),
            ("tool_execution_gating_claimed", "tool execution gating claim rejected"),
            ("runtime_write_path_wired_claimed", "runtime write path wiring claim rejected"),
        )

        for flag, expected in cases:
            with self.subTest(flag=flag):
                contract = clone_default_capability_policy_contract()
                contract["overclaim_flags"][flag] = True
                record = build_capability_policy_evidence_record(contract)

                verify = verify_capability_policy_evidence_record(record, contract)

                self.assert_rejected_with(verify, expected)

    def test_verify_replay_rejects_unexpected_evidence_overclaim_field(self):
        contract = build_default_capability_policy_contract()
        record = build_capability_policy_evidence_record(contract)
        tampered = deepcopy(record)
        tampered["b3_closure_claimed"] = True
        tampered["deterministic_evidence_digest"] = capability_policy_evidence_digest(tampered)

        verify = verify_capability_policy_evidence_record(tampered, contract)

        self.assert_rejected_with(verify, "unexpected evidence record field: b3_closure_claimed")
        self.assert_rejected_with(verify, "B3 closure claim rejected")

    def test_current_authority_snapshot_is_preserved(self):
        self.assertEqual(
            AUTHORITY_SNAPSHOT,
            {
                "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
                "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
                "phase11a_status": PHASE11A_NOT_STARTED,
                "safe_default": SAFE_DEFAULT,
            },
        )

    def test_module_has_no_runtime_side_effect_helpers(self):
        source = inspect.getsource(b3_capability_policy_evidence)
        forbidden_calls = (
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".chmod(",
            "chmod(",
            ".chown(",
            "chown(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "subprocess",
            "socket",
            "requests",
            "http_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def assert_rejected_with(self, verify, expected):
        self.assertFalse(verify["accepted"])
        self.assertEqual(verify["status"], VERIFY_REPLAY_REJECTED)
        self.assertIn(expected, verify["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
