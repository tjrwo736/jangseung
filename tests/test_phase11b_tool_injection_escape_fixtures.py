import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence import structured_action_injection_fixtures
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_LIMITED_ALLOWED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
    SCOPE_LIMIT_REJECTED,
    evaluate_action_capabilities,
)
from src.evidence.structured_action_injection_fixtures import (
    ACTION_TYPE_CONFUSION_REJECTED,
    AEG_SCOPE_ESCAPE_REJECTED,
    ALIAS_EXECUTABLE_PAYLOAD_FIELDS,
    ALIAS_EXECUTABLE_PAYLOAD_REJECTED,
    CAPABILITY_SMUGGLING_REJECTED,
    CATEGORY_ACTION_TYPE_CONFUSION,
    CATEGORY_ALIAS_EXECUTABLE_PAYLOAD,
    CATEGORY_EXECUTABLE_PAYLOAD,
    CATEGORY_NESTED_EXECUTABLE_PAYLOAD,
    CATEGORY_PATH_ESCAPE,
    ENV_SECRET_ACCESS_REJECTED,
    EXECUTABLE_PAYLOAD_FIELD_FIXTURES,
    EXECUTABLE_PAYLOAD_REJECTED,
    NESTED_EXECUTABLE_PAYLOAD_FIXTURES,
    NESTED_EXECUTABLE_PAYLOAD_REJECTED,
    PATH_ESCAPE_REJECTED,
    PR_81_DRAFT_RELEASE_NOT_PERFORMED,
    PR_81_MERGE_NOT_PERFORMED,
    PR_81_STATUS_HOLD_OPEN_DRAFT,
    REPORTED_ONLY_AUTHORITY_REJECTED,
    SYMLINK_ESCAPE_FUTURE_FIXTURE,
    TOOL_INJECTION_FIXTURE_SET_VERSION,
    build_tool_injection_fixture_summary,
    evaluate_tool_injection_fixtures,
    inert_propose_patch_action,
    verify_tool_injection_fixture_summary,
)
from src.evidence.structured_actions import (
    FORBIDDEN_PAYLOAD_FIELD_REJECTED,
    REQUEST_REPO_READ,
    VALID_STRUCTURED_ACTION,
    validate_structured_action,
)


class Phase11bToolInjectionEscapeFixtureTests(unittest.TestCase):
    def test_executable_payload_field_rejected(self):
        results = self._results_by_category(CATEGORY_EXECUTABLE_PAYLOAD)
        expected_fields = {field for field, _value in EXECUTABLE_PAYLOAD_FIELD_FIXTURES}

        self.assertEqual(
            {result.case_id.removeprefix("executable_payload_") for result in results},
            expected_fields,
        )
        for result in results:
            with self.subTest(case_id=result.case_id):
                self.assertTrue(result.rejected)
                self.assertFalse(result.allowed)
                self.assertTrue(result.expectation_met)
                self.assertEqual(result.fixture_status, EXECUTABLE_PAYLOAD_REJECTED)
                self.assertEqual(result.schema_status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)
                self.assertFalse(result.execution_allowed)
                self.assertFalse(result.mutation_allowed)

    def test_nested_executable_payload_field_rejected(self):
        results = self._results_by_category(CATEGORY_NESTED_EXECUTABLE_PAYLOAD)
        expected_names = {name for name, _payload in NESTED_EXECUTABLE_PAYLOAD_FIXTURES}

        self.assertEqual(
            {
                result.case_id.removeprefix("nested_executable_payload_")
                for result in results
            },
            expected_names,
        )
        for result in results:
            with self.subTest(case_id=result.case_id):
                self.assertTrue(result.rejected)
                self.assertTrue(result.expectation_met)
                self.assertEqual(result.fixture_status, NESTED_EXECUTABLE_PAYLOAD_REJECTED)
                self.assertEqual(result.schema_status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)

    def test_alias_command_field_rejected(self):
        results = self._results_by_category(CATEGORY_ALIAS_EXECUTABLE_PAYLOAD)

        self.assertEqual(
            {result.case_id.removeprefix("alias_executable_payload_") for result in results},
            set(ALIAS_EXECUTABLE_PAYLOAD_FIELDS),
        )
        for result in results:
            with self.subTest(case_id=result.case_id):
                self.assertTrue(result.rejected)
                self.assertTrue(result.expectation_met)
                self.assertEqual(result.fixture_status, ALIAS_EXECUTABLE_PAYLOAD_REJECTED)

    def test_propose_patch_with_shell_command_metadata_rejected(self):
        result = self._result("executable_payload_shell_command")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, EXECUTABLE_PAYLOAD_REJECTED)
        self.assertEqual(result.schema_status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)

    def test_propose_patch_with_inert_patch_diff_remains_non_executing_and_non_mutating(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sentinel = Path(tempdir) / "should-not-exist"
            action = inert_propose_patch_action()
            action["payload"]["patch_diff"] += f"\n# text mentions {sentinel} only\n"

            validation = validate_structured_action(action)
            result = evaluate_action_capabilities(action, validation)

            self.assertTrue(validation.valid)
            self.assertEqual(validation.status, VALID_STRUCTURED_ACTION)
            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertFalse(result.execution_allowed)
            self.assertFalse(result.mutation_allowed)
            self.assertFalse(result.write_authority_granted)
            self.assertFalse(sentinel.exists())

    def test_propose_patch_targeting_aeg_rejected(self):
        result = self._result("path_escape_aeg_direct_path")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, AEG_SCOPE_ESCAPE_REJECTED)
        self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)

    def test_propose_patch_targeting_env_rejected(self):
        result = self._result("path_escape_env_file")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, ENV_SECRET_ACCESS_REJECTED)
        self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)

    def test_request_repo_read_targeting_aeg_rejected(self):
        result = evaluate_action_capabilities(self._repo_read([".aeg/ledger.jsonl"]))

        self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)
        self.assertIn(".aeg", result.gate_reason)

    def test_request_repo_read_targeting_env_rejected(self):
        result = evaluate_action_capabilities(self._repo_read([".env"]))

        self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)
        self.assertIn("env/secret", result.gate_reason)

    def test_request_repo_read_targeting_secret_or_env_path_rejected(self):
        for path in ("secrets.json", "secrets/provider-token", "config/.env.local"):
            with self.subTest(path=path):
                result = evaluate_action_capabilities(self._repo_read([path]))

                self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)
                self.assertIn("env/secret", result.gate_reason)

    def test_absolute_path_target_rejected(self):
        result = self._result("path_escape_absolute_path")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, PATH_ESCAPE_REJECTED)
        self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)

    def test_parent_traversal_target_rejected(self):
        for case_id in (
            "path_escape_aeg_parent_traversal",
            "path_escape_outside_repo_parent_traversal",
        ):
            with self.subTest(case_id=case_id):
                result = self._result(case_id)

                self.assertTrue(result.rejected)
                self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)

    def test_symlink_escape_candidate_classified_as_future_fixture(self):
        result = self._result("path_escape_symlink_to_aeg_future_fixture")

        self.assertTrue(result.future_fixture)
        self.assertFalse(result.allowed)
        self.assertFalse(result.rejected)
        self.assertEqual(result.fixture_status, SYMLINK_ESCAPE_FUTURE_FIXTURE)

    def test_noop_with_hidden_action_payload_rejected(self):
        result = self._result("action_type_confusion_noop_hidden_action")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, ACTION_TYPE_CONFUSION_REJECTED)
        self.assertEqual(result.schema_status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)

    def test_request_explanation_with_executable_payload_rejected(self):
        result = self._result("action_type_confusion_request_explanation_shell_command")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, ACTION_TYPE_CONFUSION_REJECTED)
        self.assertEqual(result.schema_status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)

    def test_reported_only_capability_granted_true_rejected(self):
        result = self._result("capability_smuggling_capability_granted")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, CAPABILITY_SMUGGLING_REJECTED)
        self.assertEqual(result.schema_status, VALID_STRUCTURED_ACTION)
        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)

    def test_self_reported_trusted_true_rejected(self):
        result = self._result("capability_smuggling_trusted")

        self.assertTrue(result.rejected)
        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)

    def test_self_reported_execution_allowed_true_rejected(self):
        result = self._result("capability_smuggling_execution_allowed")

        self.assertTrue(result.rejected)
        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)

    def test_self_reported_mutation_allowed_true_rejected(self):
        result = self._result("capability_smuggling_mutation_allowed")

        self.assertTrue(result.rejected)
        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)

    def test_reported_only_requirement_claim_rejected(self):
        result = self._result("capability_smuggling_reported_only_requirement")

        self.assertTrue(result.rejected)
        self.assertEqual(result.fixture_status, REPORTED_ONLY_AUTHORITY_REJECTED)
        self.assertEqual(result.gate_result, REPORTED_ONLY_CAPABILITY_GRANT_REJECTED)

    def test_action_type_confusion_rejected(self):
        results = self._results_by_category(CATEGORY_ACTION_TYPE_CONFUSION)

        self.assertGreaterEqual(len(results), 4)
        for result in results:
            with self.subTest(case_id=result.case_id):
                self.assertTrue(result.rejected)
                self.assertTrue(result.expectation_met)
                self.assertEqual(result.fixture_status, ACTION_TYPE_CONFUSION_REJECTED)

    def test_capability_gate_pass_does_not_execute_action(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sentinel = Path(tempdir) / "gate-pass-should-not-exist"
            action = inert_propose_patch_action()
            action["payload"]["patch_plan"].append(f"Text-only sentinel mention: {sentinel}")

            result = evaluate_action_capabilities(action)

            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertFalse(result.execution_allowed)
            self.assertFalse(sentinel.exists())

    def test_capability_gate_pass_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = evaluate_action_capabilities(inert_propose_patch_action())

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertEqual(before, after)
            self.assertFalse(result.mutation_allowed)

    def test_fixture_evaluation_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            results = evaluate_tool_injection_fixtures()

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertGreater(len(results), 0)
            self.assertEqual(before, after)
            self.assertTrue(all(not result.execution_allowed for result in results))
            self.assertTrue(all(not result.mutation_allowed for result in results))

    def test_live_executor_authority_remains_on_hold(self):
        summary = build_tool_injection_fixture_summary()

        self.assertEqual(summary["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertFalse(summary["live_executor_ready"])

    def test_pr_81_remains_untouched_draft_hold_by_contract(self):
        summary = build_tool_injection_fixture_summary()

        self.assertEqual(summary["pr_81_status"], PR_81_STATUS_HOLD_OPEN_DRAFT)
        self.assertEqual(summary["pr_81_draft_release"], PR_81_DRAFT_RELEASE_NOT_PERFORMED)
        self.assertEqual(summary["pr_81_merge"], PR_81_MERGE_NOT_PERFORMED)

    def test_fixture_summary_evidence_records_zero_adversarial_allowed(self):
        summary = build_tool_injection_fixture_summary()

        self.assertEqual(
            summary["tool_injection_fixture_set_version"],
            TOOL_INJECTION_FIXTURE_SET_VERSION,
        )
        self.assertTrue(summary["tool_injection_fixtures_evaluated"])
        self.assertEqual(summary["tool_injection_allowed_count"], 0)
        self.assertEqual(summary["escape_fixture_allowed_count"], 0)
        self.assertGreater(summary["tool_injection_rejected_count"], 0)
        self.assertGreater(summary["escape_fixture_rejected_count"], 0)
        self.assertEqual(summary["future_fixture_count"], 1)
        self.assertTrue(summary["capability_smuggling_rejected"])
        self.assertTrue(summary["action_type_confusion_rejected"])
        self.assertFalse(summary["execution_allowed"])
        self.assertFalse(summary["mutation_allowed"])

    def test_fixture_summary_verify_rejects_pass_overclaims(self):
        summary = build_tool_injection_fixture_summary()
        verification = verify_tool_injection_fixture_summary(summary)

        self.assertTrue(verification.ok)
        tampered = dict(summary)
        tampered["tool_injection_allowed_count"] = 1
        tampered["execution_allowed"] = True
        tampered_verification = verify_tool_injection_fixture_summary(tampered)

        self.assertFalse(tampered_verification.ok)
        self.assertTrue(
            any("allowed count" in error for error in tampered_verification.errors)
        )
        self.assertTrue(any("execution_allowed" in error for error in tampered_verification.errors))

    def test_fixture_harness_has_no_dynamic_fuzzing_or_runtime_helpers(self):
        source = inspect.getsource(structured_action_injection_fixtures)
        forbidden_source_terms = (
            "random.",
            "import secrets",
            "hypothesis",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            "subprocess.",
            "socket.",
            "requests.",
            "httpx.",
            "exec(",
            "eval(",
            "__import__(",
        )

        for term in forbidden_source_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def _result(self, case_id):
        results = {result.case_id: result for result in evaluate_tool_injection_fixtures()}
        self.assertIn(case_id, results)
        return results[case_id]

    def _results_by_category(self, category):
        return tuple(
            result
            for result in evaluate_tool_injection_fixtures()
            if result.category == category
        )

    def _repo_read(self, paths):
        return {
            "action_type": REQUEST_REPO_READ,
            "action_id": "test-phase11b-1d-repo-read",
            "declared_intent": "Request bounded repository context.",
            "declared_risk": "LOW",
            "capability_requirements": ["read_repo"],
            "target_scope": {"repo_relative": True, "paths": list(paths)},
            "payload": {"paths": list(paths)},
        }


if __name__ == "__main__":
    unittest.main()
