import unittest

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_CHECKED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    REPORTED_ONLY,
    SAFE_DEFAULT,
)
from src.evidence.b3_capability_policy_contract import (
    CAPABILITY_FIELDS,
    CHECK_STATUS_CHECKED,
    CHECK_STATUS_UNKNOWN,
    GRANT_SOURCE_EVIDENCE,
    GRANT_SOURCE_UNKNOWN,
    INVALID_CONTRACT,
    NOT_GRANTED_BY_POLICY,
    VALID_CONTRACT,
    build_default_capability_policy_contract,
    clone_default_capability_policy_contract,
    validate_capability_policy_contract,
)


class B3CapabilityPolicyContractTests(unittest.TestCase):
    def test_default_contract_records_non_grants_and_current_authority(self):
        contract = build_default_capability_policy_contract()
        result = validate_capability_policy_contract(contract)

        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], VALID_CONTRACT)
        self.assertEqual(contract["default_policy_status"], NOT_GRANTED_BY_POLICY)
        self.assertEqual(contract["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(contract["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(contract["phase11a_status"], PHASE11A_NOT_STARTED)
        self.assertEqual(contract["safe_default"], SAFE_DEFAULT)
        self.assertFalse(result["is_runtime_enforcement"])
        self.assertFalse(result["is_tool_execution_gate"])
        for capability_name in CAPABILITY_FIELDS:
            policy = contract["capabilities"][capability_name]
            self.assertFalse(policy["granted"])
            self.assertEqual(policy["policy_status"], NOT_GRANTED_BY_POLICY)
            self.assertEqual(policy["check_status"], NOT_CHECKED)
            self.assertFalse(policy["evidence_required"])
            self.assertFalse(policy["overclaim_risk"])

    def test_granted_true_without_evidence_is_invalid(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["network_authority"]
        policy["granted"] = True
        policy["grant_source"] = GRANT_SOURCE_EVIDENCE
        policy["check_status"] = CHECK_STATUS_CHECKED

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], INVALID_CONTRACT)
        self.assertIn("network_authority granted=true requires evidence_ref", result["reasons"])

    def test_reported_only_pass_claim_is_invalid(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["raw_shell_authority"]
        policy["grant_source"] = REPORTED_ONLY
        policy["claim_status"] = "PASS"

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertIn(
            "raw_shell_authority reported-only source cannot support PASS-like claim",
            result["reasons"],
        )

    def test_not_checked_pass_claim_is_invalid(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["write_file_authority"]
        policy["claim_status"] = "PASS"

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertIn(
            "write_file_authority unchecked status cannot support PASS-like claim",
            result["reasons"],
        )

    def test_granted_true_with_unknown_source_is_invalid(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["process_spawn_authority"]
        policy["granted"] = True
        policy["grant_source"] = GRANT_SOURCE_UNKNOWN
        policy["check_status"] = CHECK_STATUS_CHECKED
        policy["evidence_ref"] = "future-evidence-placeholder"

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertIn(
            "process_spawn_authority granted=true cannot use unknown grant source",
            result["reasons"],
        )

    def test_reported_only_unchecked_grant_is_overclaim_candidate(self):
        contract = clone_default_capability_policy_contract()
        policy = contract["capabilities"]["remote_write_authority"]
        policy["granted"] = True
        policy["grant_source"] = REPORTED_ONLY
        policy["check_status"] = NOT_CHECKED

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertIn(
            "remote_write_authority:grant_true_reported_only_unchecked",
            result["overclaim_candidates"],
        )
        self.assertIn(
            "remote_write_authority reported-only source cannot support granted=true",
            result["reasons"],
        )

    def test_contract_rejects_overclaim_flags(self):
        for flag, expected in (
            ("physical_impossibility_claimed", "physical impossibility claims are rejected"),
            ("outside_denial_claimed", "outside denial claims are rejected"),
            ("composition_safe_claimed", "composition closure claims are rejected"),
            ("structured_tool_safe_claimed", "structured tool safety claims are rejected"),
            ("live_executor_ready_claimed", "live executor ready claims are rejected"),
            ("phase11a_started_claimed", "Phase 11-A started claims are rejected"),
        ):
            with self.subTest(flag=flag):
                contract = clone_default_capability_policy_contract()
                contract["overclaim_flags"][flag] = True

                result = validate_capability_policy_contract(contract)

                self.assertFalse(result["valid"])
                self.assertIn(expected, result["reasons"])

    def test_contract_rejects_non_contract_scope_flags(self):
        for flag in (
            "runtime_enforcement",
            "tool_execution_gating",
            "os_filesystem_hardening",
            "sandbox_boundary",
            "command_runner_added",
        ):
            with self.subTest(flag=flag):
                contract = clone_default_capability_policy_contract()
                contract["non_enforcement"][flag] = True

                result = validate_capability_policy_contract(contract)

                self.assertFalse(result["valid"])
                self.assertIn(f"{flag} must be false for B3-2 contract-only scope", result["reasons"])

    def test_missing_capability_and_unknown_check_do_not_pass(self):
        contract = clone_default_capability_policy_contract()
        contract["capabilities"].pop("secret_read_authority")
        contract["capabilities"]["env_read_authority"]["check_status"] = CHECK_STATUS_UNKNOWN
        contract["capabilities"]["env_read_authority"]["claim_status"] = "PASS"

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertIn("missing capability policy: secret_read_authority", result["reasons"])
        self.assertIn(
            "env_read_authority unchecked status cannot support PASS-like claim",
            result["reasons"],
        )

    def test_b3_1_and_b3_4_boundaries_are_preserved(self):
        contract = clone_default_capability_policy_contract()
        contract["b3_1_preserved"] = False
        contract["b3_4_path_scope_fixture_started"] = True

        result = validate_capability_policy_contract(contract)

        self.assertFalse(result["valid"])
        self.assertIn("B3-1 inventory and non-grant baseline must be preserved", result["reasons"])
        self.assertIn("B3-4 path and scope fixture work is out of scope for B3-2", result["reasons"])


if __name__ == "__main__":
    unittest.main()
