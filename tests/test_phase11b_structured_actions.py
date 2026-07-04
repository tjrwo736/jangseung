import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence.structured_actions import (
    B3_CAPABILITY_REFERENCE_MISMATCHES,
    DIRECT_LEDGER_APPEND,
    DIRECT_STORE_WRITE,
    EVAL_EXEC,
    FORBIDDEN_ACTION_TYPE_REJECTED,
    FORBIDDEN_PAYLOAD_FIELD_REJECTED,
    FUTURE_GATE_REQUIRED,
    IMPORT_MODULE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD as RESULT_LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NETWORK_REQUEST,
    NOOP,
    PROCESS_SPAWN,
    PROVIDER_MODEL_CALL,
    PYTHON_CODE,
    RAW_SHELL,
    REQUEST_EXPLANATION,
    REQUEST_REPO_READ,
    REQUEST_RISK_CLASSIFICATION,
    PROPOSE_PATCH,
    PR_81_DRAFT_RELEASE_NOT_PERFORMED,
    PR_81_MERGE_NOT_PERFORMED,
    PR_81_STATUS_HOLD_OPEN_DRAFT,
    READ_ENV,
    READ_SECRET,
    RUN_COMMAND,
    STRUCTURED_ACTION_CONTRACT_EVIDENCE,
    UNKNOWN_ACTION_TYPE_REJECTED,
    VALID_STRUCTURED_ACTION,
    WRITE_AEG_STATE,
    WRITE_FILE,
    build_structured_action_contract_evidence,
    validate_structured_action,
)


class Phase11bStructuredActionTests(unittest.TestCase):
    def test_valid_propose_patch_structured_action_passes_schema_validation(self):
        result = validate_structured_action(self._valid_propose_patch())

        self.assertTrue(result.valid)
        self.assertEqual(result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(result.action_type, PROPOSE_PATCH)
        self.assertFalse(result.action_executed)
        self.assertFalse(result.filesystem_mutated)
        self.assertFalse(result.write_authority_granted)

    def test_valid_noop_structured_action_passes_schema_validation(self):
        result = validate_structured_action(self._valid_noop())

        self.assertTrue(result.valid)
        self.assertEqual(result.status, VALID_STRUCTURED_ACTION)
        self.assertEqual(result.action_type, NOOP)

    def test_unknown_action_type_rejected(self):
        action = self._valid_noop(action_type="MAKE_IT_SO")

        result = validate_structured_action(action)

        self.assertFalse(result.valid)
        self.assertEqual(result.status, UNKNOWN_ACTION_TYPE_REJECTED)

    def test_python_code_and_eval_exec_actions_rejected(self):
        for action_type in (PYTHON_CODE, EVAL_EXEC):
            with self.subTest(action_type=action_type):
                result = validate_structured_action(self._valid_noop(action_type=action_type))

                self.assertFalse(result.valid)
                self.assertEqual(result.status, FORBIDDEN_ACTION_TYPE_REJECTED)

    def test_import_module_action_rejected(self):
        result = validate_structured_action(self._valid_noop(action_type=IMPORT_MODULE))

        self.assertFalse(result.valid)
        self.assertEqual(result.status, FORBIDDEN_ACTION_TYPE_REJECTED)

    def test_raw_shell_run_command_and_process_spawn_actions_rejected(self):
        for action_type in (RAW_SHELL, RUN_COMMAND, PROCESS_SPAWN):
            with self.subTest(action_type=action_type):
                result = validate_structured_action(self._valid_noop(action_type=action_type))

                self.assertFalse(result.valid)
                self.assertEqual(result.status, FORBIDDEN_ACTION_TYPE_REJECTED)

    def test_write_file_direct_store_direct_ledger_and_aeg_state_actions_rejected(self):
        for action_type in (WRITE_FILE, DIRECT_STORE_WRITE, DIRECT_LEDGER_APPEND, WRITE_AEG_STATE):
            with self.subTest(action_type=action_type):
                result = validate_structured_action(self._valid_noop(action_type=action_type))

                self.assertFalse(result.valid)
                self.assertEqual(result.status, FORBIDDEN_ACTION_TYPE_REJECTED)

    def test_network_and_provider_model_actions_rejected(self):
        network_result = validate_structured_action(self._valid_noop(action_type=NETWORK_REQUEST))
        provider_result = validate_structured_action(self._valid_noop(action_type=PROVIDER_MODEL_CALL))

        self.assertFalse(network_result.valid)
        self.assertEqual(network_result.status, FORBIDDEN_ACTION_TYPE_REJECTED)
        self.assertFalse(provider_result.valid)
        self.assertEqual(provider_result.status, FUTURE_GATE_REQUIRED)

    def test_env_and_secret_read_actions_rejected(self):
        for action_type in (READ_ENV, READ_SECRET):
            with self.subTest(action_type=action_type):
                result = validate_structured_action(self._valid_noop(action_type=action_type))

                self.assertFalse(result.valid)
                self.assertEqual(result.status, FORBIDDEN_ACTION_TYPE_REJECTED)

    def test_payload_containing_executable_fields_rejected(self):
        for field in ("python_code", "shell_command", "import_path"):
            with self.subTest(field=field):
                action = self._valid_propose_patch()
                action["payload"][field] = "not accepted as data"

                result = validate_structured_action(action)

                self.assertFalse(result.valid)
                self.assertEqual(result.status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)
                self.assertTrue(any(field in reason for reason in result.reasons))

    def test_payload_containing_aeg_target_rejected(self):
        action = self._valid_propose_patch()
        action["payload"]["target_files"] = [".aeg/ledger.jsonl"]

        result = validate_structured_action(action)

        self.assertFalse(result.valid)
        self.assertEqual(result.status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)
        self.assertTrue(any(".aeg target rejected" in reason for reason in result.reasons))

    def test_payload_containing_absolute_write_path_rejected(self):
        action = self._valid_propose_patch()
        action["payload"]["target_files"] = ["/tmp/aegis-outside-repo.txt"]

        result = validate_structured_action(action)

        self.assertFalse(result.valid)
        self.assertEqual(result.status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)
        self.assertTrue(any("absolute path rejected" in reason for reason in result.reasons))

    def test_payload_requesting_env_or_secret_read_rejected(self):
        for field in ("env_key", "secret_key"):
            with self.subTest(field=field):
                action = self._valid_noop(action_type=REQUEST_EXPLANATION, capability_requirements=["explanation"])
                action["payload"][field] = "TOKEN"

                result = validate_structured_action(action)

                self.assertFalse(result.valid)
                self.assertEqual(result.status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)

    def test_reported_only_capability_grant_rejected(self):
        action = self._valid_noop(action_type=REQUEST_REPO_READ, capability_requirements=[])
        action["capability_requirements"] = [
            {
                "capability_name": "network",
                "granted": True,
                "grant_source": "reported_only",
            }
        ]

        result = validate_structured_action(action)

        self.assertFalse(result.valid)
        self.assertIn("reported_only capability grant rejected", result.reasons)
        self.assertIn(
            "capability grant claims are not accepted by the structured action validator",
            result.reasons,
        )

    def test_validator_pass_does_not_execute_action(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sentinel = Path(tempdir) / "should-not-exist"
            action = self._valid_propose_patch()
            action["payload"]["patch_plan"] = [
                f"Do not treat this text as executable: create {sentinel}"
            ]

            result = validate_structured_action(action)

            self.assertTrue(result.valid)
            self.assertFalse(sentinel.exists())
            self.assertFalse(result.action_executed)

    def test_validator_pass_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = validate_structured_action(self._valid_propose_patch())

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertTrue(result.valid)
            self.assertEqual(before, after)
            self.assertFalse(result.filesystem_mutated)

    def test_live_executor_authority_remains_on_hold(self):
        evidence = build_structured_action_contract_evidence()
        result = validate_structured_action(self._valid_noop())

        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(RESULT_LIVE_EXECUTOR_AUTHORITY_ON_HOLD, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertFalse(result.live_executor_ready)

    def test_pr_81_remains_untouched_draft_hold_by_contract(self):
        evidence = build_structured_action_contract_evidence()

        self.assertEqual(evidence["pr_81_status"], PR_81_STATUS_HOLD_OPEN_DRAFT)
        self.assertEqual(evidence["pr_81_draft_release"], PR_81_DRAFT_RELEASE_NOT_PERFORMED)
        self.assertEqual(evidence["pr_81_merge"], PR_81_MERGE_NOT_PERFORMED)

    def test_b3_capability_taxonomy_references_are_connected(self):
        self.assertEqual(B3_CAPABILITY_REFERENCE_MISMATCHES, frozenset())

    def test_contract_evidence_records_data_not_code_and_no_authority(self):
        evidence = build_structured_action_contract_evidence()

        self.assertEqual(
            evidence["structured_action_contract_version"],
            STRUCTURED_ACTION_CONTRACT_EVIDENCE["structured_action_contract_version"],
        )
        self.assertEqual(evidence["executor_output_model"], "DATA_NOT_CODE")
        self.assertTrue(evidence["structured_action_schema_enforced"])
        self.assertFalse(evidence["arbitrary_python_execution_allowed"])
        self.assertFalse(evidence["eval_exec_allowed"])
        self.assertFalse(evidence["import_allowed"])
        self.assertFalse(evidence["raw_shell_allowed"])
        self.assertFalse(evidence["run_command_allowed"])
        self.assertFalse(evidence["process_spawn_allowed"])
        self.assertFalse(evidence["store_sink_direct_access_allowed"])
        self.assertFalse(evidence["aeg_state_write_allowed"])
        self.assertFalse(evidence["general_write_file_allowed"])
        self.assertFalse(evidence["network_allowed"])
        self.assertFalse(evidence["provider_model_call_allowed"])

    def test_allowed_read_risk_and_explanation_actions_pass(self):
        examples = (
            (REQUEST_REPO_READ, ["read_repo"]),
            (REQUEST_RISK_CLASSIFICATION, ["risk_classification"]),
            (REQUEST_EXPLANATION, ["explanation"]),
        )
        for action_type, requirements in examples:
            with self.subTest(action_type=action_type):
                action = self._valid_noop(
                    action_type=action_type,
                    capability_requirements=requirements,
                )

                result = validate_structured_action(action)

                self.assertTrue(result.valid)
                self.assertEqual(result.status, VALID_STRUCTURED_ACTION)

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
