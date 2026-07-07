import dataclasses
import inspect
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, NOT_CHECKED, SAFE_DEFAULT
from src.evidence import claude_code_pretooluse_input_contract
from src.evidence.claude_code_pretooluse_input_contract import (
    HOOK_COVERAGE_REPORT_UNTRUSTED,
    INVALID_PRETOOLUSE_INPUT_CONTRACT,
    OPTIONAL_HOOK_METADATA_FIELDS,
    PHASE11C_1_COMPLETE_LABEL,
    REQUIRED_HOOK_INPUT_FIELDS,
    SUPPORTED_INITIAL_TARGET,
    SUPPORTED_INITIAL_TARGET_TOOLS,
    UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED,
    VALID_PRETOOLUSE_INPUT_CONTRACT,
    assess_hook_coverage_report,
    build_claude_code_pretooluse_input_contract_evidence,
    validate_claude_code_pretooluse_input,
)


DOC_PATH = Path("docs/phase11c_1_claude_code_pretooluse_input_contract_v0.md")


class Phase11C1ClaudeCodePreToolUseInputContractTests(unittest.TestCase):
    def test_supported_initial_tools_validate_shape_without_authority(self):
        for tool_name in SUPPORTED_INITIAL_TARGET_TOOLS:
            with self.subTest(tool_name=tool_name):
                result = validate_claude_code_pretooluse_input(
                    {
                        "tool_name": tool_name,
                        "tool_input": {},
                        "tool_use_id": f"toolu-{tool_name.lower()}-001",
                    }
                )

                self.assertTrue(result.valid)
                self.assertEqual(result.status, VALID_PRETOOLUSE_INPUT_CONTRACT)
                self.assertEqual(result.tool_support_status, SUPPORTED_INITIAL_TARGET)
                self.assertEqual(result.hook_input.tool_name, tool_name)
                self.assertIsInstance(result.hook_input.tool_input, MappingProxyType)
                self._assert_no_trust_or_authority(result)
                self._assert_no_trust_or_authority(result.hook_input)

    def test_required_fields_missing_fail_closed(self):
        base_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "README.md"},
            "tool_use_id": "toolu-read-001",
        }

        for field_name in REQUIRED_HOOK_INPUT_FIELDS:
            with self.subTest(field_name=field_name):
                raw_input = dict(base_input)
                del raw_input[field_name]

                result = validate_claude_code_pretooluse_input(raw_input)

                self.assertFalse(result.valid)
                self.assertEqual(result.status, INVALID_PRETOOLUSE_INPUT_CONTRACT)
                self.assertIn(f"missing_required_field:{field_name}", result.reasons)
                self.assertIsNone(result.hook_input)
                self._assert_no_trust_or_authority(result)

    def test_invalid_required_field_types_fail_closed(self):
        cases = (
            (
                {
                    "tool_name": "",
                    "tool_input": {},
                    "tool_use_id": "toolu-001",
                },
                "invalid_required_field:tool_name_must_be_non_empty_string",
            ),
            (
                {
                    "tool_name": "Read",
                    "tool_input": "README.md",
                    "tool_use_id": "toolu-001",
                },
                "invalid_required_field:tool_input_must_be_mapping",
            ),
            (
                {
                    "tool_name": "Read",
                    "tool_input": {},
                    "tool_use_id": "",
                },
                "invalid_required_field:tool_use_id_must_be_non_empty_string",
            ),
        )

        for raw_input, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                result = validate_claude_code_pretooluse_input(raw_input)

                self.assertFalse(result.valid)
                self.assertIn(expected_reason, result.reasons)
                self.assertEqual(result.decision, SAFE_DEFAULT)
                self._assert_no_trust_or_authority(result)

    def test_optional_metadata_fields_are_accepted_as_untrusted_context(self):
        raw_input = {
            "tool_name": "Bash",
            "tool_input": {"command": "printf contract-only"},
            "tool_use_id": "toolu-bash-001",
            "cwd": "/repo",
            "session_id": "session-001",
            "transcript_path": "/tmp/transcript.jsonl",
            "substrate_name": "claude-code",
            "substrate_version": "pretooluse-v0",
            "project_root": "/repo",
            "timestamp": "2026-07-07T00:00:00Z",
        }

        result = validate_claude_code_pretooluse_input(raw_input)

        self.assertTrue(result.valid)
        for field_name in OPTIONAL_HOOK_METADATA_FIELDS:
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    getattr(result.hook_input, field_name),
                    raw_input[field_name],
                )
        self._assert_no_trust_or_authority(result)
        self._assert_no_trust_or_authority(result.hook_input)

    def test_invalid_optional_metadata_fails_closed(self):
        raw_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "README.md"},
            "tool_use_id": "toolu-read-001",
            "timestamp": 123,
        }

        result = validate_claude_code_pretooluse_input(raw_input)

        self.assertFalse(result.valid)
        self.assertIn(
            "invalid_optional_metadata_field:timestamp_must_be_string",
            result.reasons,
        )
        self._assert_no_trust_or_authority(result)

    def test_unknown_unsupported_and_not_checked_tools_fail_closed_not_pass(self):
        for tool_name in ("Task", "NotebookEdit", "UNKNOWN", "UNSUPPORTED", NOT_CHECKED):
            with self.subTest(tool_name=tool_name):
                result = validate_claude_code_pretooluse_input(
                    {
                        "tool_name": tool_name,
                        "tool_input": {},
                        "tool_use_id": "toolu-unknown-001",
                    }
                )

                self.assertFalse(result.valid)
                self.assertEqual(
                    result.tool_support_status,
                    UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED,
                )
                self.assertIn(
                    f"unsupported_or_unknown_tool_name:{tool_name}",
                    result.reasons,
                )
                self.assertFalse(result.unsupported_unknown_or_not_checked_is_pass)
                self.assertEqual(result.decision, SAFE_DEFAULT)
                self._assert_no_trust_or_authority(result)

    def test_extra_self_report_fields_are_preserved_only_as_untrusted_extras(self):
        result = validate_claude_code_pretooluse_input(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "README.md", "content": "contract only"},
                "tool_use_id": "toolu-write-001",
                "decision": "allow",
                "capability_granted": True,
                "write_authority_granted": True,
                "coverage_report": "PASS",
            }
        )

        self.assertTrue(result.valid)
        self.assertEqual(
            result.ignored_untrusted_fields,
            (
                "capability_granted",
                "coverage_report",
                "decision",
                "write_authority_granted",
            ),
        )
        self.assertIsInstance(result.hook_input.extra_untrusted_fields, MappingProxyType)
        self.assertEqual(
            result.hook_input.extra_untrusted_fields["decision"],
            "allow",
        )
        self._assert_no_trust_or_authority(result)
        self._assert_no_trust_or_authority(result.hook_input)

    def test_hook_input_contract_is_frozen_and_caller_mutation_does_not_persist(self):
        raw_input = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "README.md", "old_string": "a", "new_string": "b"},
            "tool_use_id": "toolu-edit-001",
        }

        result = validate_claude_code_pretooluse_input(raw_input)
        raw_input["tool_input"]["file_path"] = "mutated.md"

        self.assertEqual(result.hook_input.tool_input["file_path"], "README.md")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.hook_input.tool_name = "Read"
        with self.assertRaises(TypeError):
            result.hook_input.tool_input["file_path"] = "mutated.md"

    def test_hook_coverage_report_is_not_coverage_proof(self):
        for status in (
            SUPPORTED_INITIAL_TARGET,
            "UNSUPPORTED",
            "UNKNOWN",
            NOT_CHECKED,
            "PASS",
            None,
        ):
            with self.subTest(status=status):
                assessment = assess_hook_coverage_report(status)

                self.assertEqual(
                    assessment.assessment_status,
                    HOOK_COVERAGE_REPORT_UNTRUSTED,
                )
                self.assertFalse(assessment.report_is_coverage_proof)
                self.assertFalse(assessment.pass_accepted)
                self.assertFalse(assessment.unsupported_unknown_or_not_checked_is_pass)
                self.assertEqual(assessment.decision, SAFE_DEFAULT)

    def test_evidence_records_contract_only_boundaries(self):
        evidence = build_claude_code_pretooluse_input_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_1_COMPLETE_LABEL)
        self.assertEqual(evidence["required_fields"], REQUIRED_HOOK_INPUT_FIELDS)
        self.assertEqual(
            evidence["optional_metadata_fields"],
            OPTIONAL_HOOK_METADATA_FIELDS,
        )
        self.assertEqual(
            evidence["supported_initial_tools"],
            SUPPORTED_INITIAL_TARGET_TOOLS,
        )
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertFalse(evidence["hook_input_trusted_as_decision"])
        self.assertFalse(evidence["hook_input_trusted_as_capability_grant"])
        self.assertFalse(evidence["hook_coverage_report_is_coverage_proof"])
        self.assertFalse(evidence["unsupported_unknown_or_not_checked_is_pass"])
        self.assertFalse(evidence["hook_command_implemented"])
        self.assertFalse(evidence["hook_installation_implemented"])
        self.assertFalse(evidence["claude_code_execution_performed"])
        self.assertFalse(evidence["codex_implementation_added"])
        self.assertFalse(evidence["provider_model_network_implemented"])
        self.assertFalse(evidence["api_key_env_secret_loading_implemented"])
        self.assertFalse(evidence["network_client_implemented"])
        self.assertFalse(evidence["action_execution_engine_implemented"])
        self.assertFalse(evidence["tool_runtime_implemented"])
        self.assertFalse(evidence["write_authority_granted"])
        self.assertFalse(evidence["filesystem_mutation_by_contract_validation"])
        self.assertFalse(evidence["patch_application_implemented"])
        self.assertFalse(evidence["public_release_performed"])
        self.assertFalse(evidence["safe_default_changed"])
        self.assertFalse(evidence["universal_prompt_injection_prevention_claimed"])
        self.assertFalse(evidence["sandbox_process_isolation_claimed"])
        self.assertFalse(evidence["bash_safe_claimed"])

    def test_contract_validation_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = validate_claude_code_pretooluse_input(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "example.md", "content": "data only"},
                    "tool_use_id": "toolu-write-001",
                }
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertTrue(result.valid)
            self.assertEqual(before, after)
            self._assert_no_trust_or_authority(result)

    def test_contract_source_has_no_hook_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(claude_code_pretooluse_input_contract)
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
            "src.state." + "store",
            "from src.state import " + "store",
            "sto" + "re.",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

    def test_doc_records_required_contract_and_boundaries(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn(PHASE11C_1_COMPLETE_LABEL, doc)
        for marker in (
            "tool_name",
            "tool_input",
            "tool_use_id",
            "cwd",
            "session_id",
            "transcript_path",
            "substrate_name",
            "substrate_version",
            "project_root",
            "timestamp",
            "Bash",
            "Write",
            "Edit",
            "Read",
            "hook input must be treated as untrusted raw executor output",
            "hook input != trusted decision",
            "hook input != capability grant",
            "hook coverage report != coverage proof",
            "unsupported/unknown/NOT_CHECKED != PASS",
            "safe default = hold_current_state",
            "main merge = NOT_PERFORMED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_non_goal_boundaries(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            "hook command implementation",
            ".claude/settings.json mutation",
            "actual hook installation",
            "actual Claude Code execution",
            "Codex implementation",
            "provider/model/network implementation",
            "OpenAI/Ollama/LLM call",
            "API key/env/secret loading",
            "network client",
            "action execution engine",
            "write authority",
            "tool runtime",
            "store.py change",
            "filesystem mutation by hook runtime or action execution",
            "patch application",
            "public release",
            "live_executor_authority change",
            "safe default change",
            "universal prompt-injection prevention claim",
            "sandbox/process isolation claim",
            "Bash-safe claim",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def _assert_no_trust_or_authority(self, result):
        self.assertFalse(result.hook_input_trusted_as_decision)
        self.assertFalse(result.hook_input_trusted_as_capability_grant)
        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.mutation_allowed)
        self.assertFalse(result.write_authority_granted)
        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(result.safe_default, SAFE_DEFAULT)


if __name__ == "__main__":
    unittest.main()
