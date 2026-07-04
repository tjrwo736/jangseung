import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence import structured_action_capabilities
from src.evidence.structured_action_capabilities import (
    ALLOWED_LIMITED_ACTION_CAPABILITY_MAPPING,
    CAPABILITY_DENIED,
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    CAPABILITY_STATUS_VOCABULARY,
    DEFAULT_DENIED_CAPABILITIES,
    FUTURE_GATE_REQUIRED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
    SCOPE_LIMIT_REJECTED,
    UNKNOWN_CAPABILITY_REJECTED,
    build_action_capability_gate_evidence,
    evaluate_action_capabilities,
)
from src.evidence.structured_actions import (
    DIRECT_LEDGER_APPEND,
    DIRECT_STORE_WRITE,
    NETWORK_REQUEST,
    NOOP,
    PROCESS_SPAWN,
    PROVIDER_MODEL_CALL,
    RAW_SHELL,
    READ_ENV,
    READ_SECRET,
    REQUEST_EXPLANATION,
    REQUEST_REPO_READ,
    REQUEST_RISK_CLASSIFICATION,
    PROPOSE_PATCH,
    PR_81_DRAFT_RELEASE_NOT_PERFORMED,
    PR_81_MERGE_NOT_PERFORMED,
    PR_81_STATUS_HOLD_OPEN_DRAFT,
    RUN_COMMAND,
    VALID_STRUCTURED_ACTION,
    WRITE_AEG_STATE,
    WRITE_FILE,
    build_structured_action_contract_evidence,
    validate_structured_action,
)


class Phase11bActionCapabilityGateTests(unittest.TestCase):
    def test_noop_and_request_explanation_pass_capability_gate(self):
        for action_type, capabilities in (
            (NOOP, ["noop"]),
            (REQUEST_EXPLANATION, ["explanation"]),
        ):
            with self.subTest(action_type=action_type):
                result = evaluate_action_capabilities(
                    self._valid_noop(
                        action_type=action_type,
                        capability_requirements=capabilities,
                    )
                )

                self.assertEqual(result.gate_result, CAPABILITY_GATE_ALLOWED)
                self.assertEqual(result.schema_validation_status, VALID_STRUCTURED_ACTION)
                self.assertFalse(result.execution_allowed)
                self.assertFalse(result.mutation_allowed)

    def test_request_risk_classification_passes_as_data_only(self):
        result = evaluate_action_capabilities(
            self._valid_noop(
                action_type=REQUEST_RISK_CLASSIFICATION,
                capability_requirements=["risk_classification"],
            )
        )

        self.assertEqual(result.gate_result, CAPABILITY_GATE_ALLOWED)
        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.write_authority_granted)

    def test_propose_patch_passes_as_non_executing_limited_proposal_only(self):
        result = evaluate_action_capabilities(self._valid_propose_patch())

        self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
        self.assertEqual(result.required_capabilities, ("propose_patch", "repo_target_scope"))
        self.assertTrue(all(decision.allowed for decision in result.capability_decisions))
        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.mutation_allowed)
        self.assertFalse(result.write_authority_granted)

    def test_propose_patch_does_not_grant_write_authority(self):
        action = self._valid_propose_patch()
        action["capability_requirements"] = ["propose_patch"]

        result = evaluate_action_capabilities(action)

        self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
        self.assertFalse(result.write_authority_granted)
        self.assertFalse(result.live_executor_ready)

    def test_request_repo_read_limited_scope_passes(self):
        result = evaluate_action_capabilities(self._valid_repo_read(["src/example.py"]))

        self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
        self.assertEqual(result.required_capabilities, ("read_repo",))
        self.assertFalse(result.execution_allowed)

    def test_request_repo_read_targeting_aeg_rejects(self):
        result = evaluate_action_capabilities(self._valid_repo_read([".aeg/ledger.jsonl"]))

        self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)
        self.assertIn(".aeg", result.gate_reason)

    def test_request_repo_read_targeting_env_or_secret_rejects(self):
        for path in (".env", "secrets/provider-token"):
            with self.subTest(path=path):
                result = evaluate_action_capabilities(self._valid_repo_read([path]))

                self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)
                self.assertIn("env/secret", result.gate_reason)

    def test_aeg_state_store_and_ledger_write_actions_reject(self):
        for action_type in (WRITE_AEG_STATE, DIRECT_STORE_WRITE, DIRECT_LEDGER_APPEND):
            with self.subTest(action_type=action_type):
                result = evaluate_action_capabilities(self._valid_noop(action_type=action_type))

                self.assertEqual(result.gate_result, CAPABILITY_DENIED)
                self.assertFalse(result.write_authority_granted)

    def test_write_file_run_command_raw_shell_and_process_spawn_reject(self):
        for action_type in (WRITE_FILE, RUN_COMMAND, RAW_SHELL, PROCESS_SPAWN):
            with self.subTest(action_type=action_type):
                result = evaluate_action_capabilities(self._valid_noop(action_type=action_type))

                self.assertEqual(result.gate_result, CAPABILITY_DENIED)
                self.assertFalse(result.execution_allowed)

    def test_network_and_provider_model_actions_reject_or_future_gate(self):
        network_result = evaluate_action_capabilities(self._valid_noop(action_type=NETWORK_REQUEST))
        provider_result = evaluate_action_capabilities(
            self._valid_noop(action_type=PROVIDER_MODEL_CALL)
        )

        self.assertEqual(network_result.gate_result, CAPABILITY_DENIED)
        self.assertEqual(provider_result.gate_result, FUTURE_GATE_REQUIRED)

    def test_env_and_secret_read_actions_reject(self):
        for action_type in (READ_ENV, READ_SECRET):
            with self.subTest(action_type=action_type):
                result = evaluate_action_capabilities(self._valid_noop(action_type=action_type))

                self.assertEqual(result.gate_result, CAPABILITY_DENIED)

    def test_unknown_capability_rejects_after_schema_validation(self):
        action = self._valid_noop(capability_requirements=["mystery_capability"])
        validation = validate_structured_action(action)

        result = evaluate_action_capabilities(action, validation)

        self.assertTrue(validation.valid)
        self.assertEqual(result.gate_result, UNKNOWN_CAPABILITY_REJECTED)
        self.assertIn("mystery_capability", result.required_capabilities)

    def test_reported_only_grant_rejects_at_capability_gate(self):
        action = self._valid_repo_read(["src/example.py"])
        action["capability_requirements"] = [
            {
                "capability_name": "network",
                "granted": True,
                "grant_source": "reported_only",
            }
        ]
        validation = validate_structured_action(action)

        result = evaluate_action_capabilities(action, validation)

        self.assertTrue(validation.valid)
        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)
        self.assertIn("reported_only capability grant rejected", result.gate_reason)

    def test_executor_self_claimed_authority_rejects_at_capability_gate(self):
        action = self._valid_propose_patch()
        action["payload"]["authority"] = "write_file"
        action["payload"]["approved_by_executor"] = True

        result = evaluate_action_capabilities(action)

        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)
        self.assertIn("executor self-claimed authority rejected", result.gate_reason)

    def test_gate_pass_does_not_execute_or_create_sentinel_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sentinel = Path(tempdir) / "should-not-exist"
            action = self._valid_propose_patch()
            action["payload"]["patch_plan"] = [f"create {sentinel}"]

            result = evaluate_action_capabilities(action)

            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertFalse(sentinel.exists())
            self.assertFalse(result.execution_allowed)

    def test_gate_pass_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = evaluate_action_capabilities(self._valid_propose_patch())

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertEqual(before, after)
            self.assertFalse(result.mutation_allowed)

    def test_gate_result_never_grants_execution_mutation_write_or_live_executor(self):
        result = evaluate_action_capabilities(self._valid_repo_read(["src/example.py"]))

        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.mutation_allowed)
        self.assertFalse(result.write_authority_granted)
        self.assertFalse(result.live_executor_ready)
        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)

    def test_pr_81_remains_hold_open_draft_by_contract(self):
        evidence = build_structured_action_contract_evidence()

        self.assertEqual(evidence["pr_81_status"], PR_81_STATUS_HOLD_OPEN_DRAFT)
        self.assertEqual(evidence["pr_81_draft_release"], PR_81_DRAFT_RELEASE_NOT_PERFORMED)
        self.assertEqual(evidence["pr_81_merge"], PR_81_MERGE_NOT_PERFORMED)

    def test_gate_evidence_records_non_grant_contract(self):
        evidence = build_action_capability_gate_evidence()

        self.assertEqual(
            evidence["capability_gate_function"],
            "evaluate_action_capabilities",
        )
        self.assertEqual(
            set(evidence["capability_status_vocabulary"]),
            CAPABILITY_STATUS_VOCABULARY,
        )
        self.assertEqual(
            set(evidence["default_denied_capabilities"]),
            DEFAULT_DENIED_CAPABILITIES,
        )
        self.assertEqual(
            evidence["allowed_limited_action_capability_mapping"],
            ALLOWED_LIMITED_ACTION_CAPABILITY_MAPPING,
        )
        self.assertTrue(evidence["reported_only_grants_rejected"])
        self.assertFalse(evidence["execution_allowed"])
        self.assertFalse(evidence["mutation_allowed"])
        self.assertFalse(evidence["write_authority_granted"])
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)

    def test_gate_module_has_no_runtime_side_effect_helpers(self):
        source = inspect.getsource(structured_action_capabilities)
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
            "exec(",
            "eval(",
            "__import__(",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

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

    def _valid_repo_read(self, paths):
        return {
            "action_type": REQUEST_REPO_READ,
            "action_id": "action-read-001",
            "declared_intent": "Request bounded repository context.",
            "declared_risk": "LOW",
            "capability_requirements": ["read_repo"],
            "target_scope": {
                "repo_relative": True,
                "paths": list(paths),
            },
            "payload": {
                "paths": list(paths),
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
