import dataclasses
import inspect
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import HIGH, LOW, NOT_CHECKED, SAFE_DEFAULT
from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence import claude_code_tool_call_mapping
from src.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    BASH_DANGEROUS,
    BASH_NOT_CHECKED,
    DENY_CANDIDATE,
    EDIT_FILE,
    HOLD_CURRENT_STATE,
    HOLD_CURRENT_STATE_CANDIDATE,
    NORMAL_REPO_PATH,
    PHASE11C_2_COMPLETE_LABEL,
    PROTECTED_PATH,
    READ_REPO,
    RUN_COMMAND,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    WRITE_FILE,
    build_tool_call_mapping_contract_evidence,
    map_pretooluse_input_to_structured_action_candidate,
)


DOC_PATH = Path("docs/phase11c_2_tool_call_to_structured_action_mapping_v0.md")


class Phase11C2ToolCallToStructuredActionMappingTests(unittest.TestCase):
    def test_read_normal_repo_path_maps_to_read_repo_candidate_only(self):
        candidate = self._candidate(
            "Read",
            {"file_path": "src/example.py"},
            "toolu-read-001",
        )

        self.assertEqual(candidate.candidate_action_type, READ_REPO)
        self.assertEqual(candidate.candidate_status, STRUCTURED_ACTION_CANDIDATE)
        self.assertEqual(candidate.declared_risk, LOW)
        self.assertEqual(candidate.risk_status, NORMAL_REPO_PATH)
        self.assertEqual(candidate.payload["file_path"], "src/example.py")
        self.assertEqual(candidate.capability_requirements, ("read_repo",))
        self._assert_provenance(candidate, "Read", "toolu-read-001")
        self._assert_candidate_only_no_authority(candidate)

    def test_write_and_edit_normal_repo_paths_map_to_candidates_without_authority(self):
        cases = (
            (
                "Write",
                {"file_path": "docs/example.md", "content": "contract only"},
                WRITE_FILE,
                "write_file",
            ),
            (
                "Edit",
                {
                    "file_path": "src/example.py",
                    "old_string": "old",
                    "new_string": "new",
                },
                EDIT_FILE,
                "edit_file",
            ),
        )

        for tool_name, tool_input, expected_action, expected_capability in cases:
            with self.subTest(tool_name=tool_name):
                candidate = self._candidate(tool_name, tool_input, f"toolu-{tool_name}")

                self.assertEqual(candidate.candidate_action_type, expected_action)
                self.assertEqual(candidate.candidate_status, STRUCTURED_ACTION_CANDIDATE)
                self.assertEqual(candidate.risk_status, NORMAL_REPO_PATH)
                self.assertEqual(candidate.capability_requirements, (expected_capability,))
                self._assert_candidate_only_no_authority(candidate)

    def test_protected_paths_map_to_deny_candidates_without_decision_or_authority(self):
        cases = (
            ("Read", {"file_path": ".env"}, READ_REPO),
            ("Read", {"file_path": ".env.local"}, READ_REPO),
            ("Write", {"file_path": ".aeg/state.json", "content": "data"}, WRITE_FILE),
            (
                "Edit",
                {
                    "file_path": "secrets/token.txt",
                    "old_string": "old",
                    "new_string": "new",
                },
                EDIT_FILE,
            ),
            ("Write", {"file_path": "protected/config.json", "content": "data"}, WRITE_FILE),
            ("Read", {"file_path": "/tmp/outside.txt"}, READ_REPO),
            ("Read", {"file_path": "../outside.txt"}, READ_REPO),
        )

        for tool_name, tool_input, expected_action in cases:
            with self.subTest(tool_name=tool_name, tool_input=tool_input):
                candidate = self._candidate(tool_name, tool_input, f"toolu-{tool_name}")

                self.assertEqual(candidate.candidate_action_type, expected_action)
                self.assertEqual(candidate.candidate_status, DENY_CANDIDATE)
                self.assertEqual(candidate.declared_risk, HIGH)
                self.assertEqual(candidate.risk_status, PROTECTED_PATH)
                self.assertEqual(candidate.decision, SAFE_DEFAULT)
                self._assert_candidate_only_no_authority(candidate)

    def test_bash_dangerous_commands_map_to_run_command_deny_candidates(self):
        commands = (
            "rm -rf build",
            "git push origin main",
            "npm run deploy",
            "curl https://example.invalid",
            "wget https://example.invalid/file",
            "env",
            "printenv",
            "chmod 777 script.sh",
            "chown root file",
            "sudo make install",
        )

        for command in commands:
            with self.subTest(command=command):
                candidate = self._candidate(
                    "Bash",
                    {"command": command},
                    "toolu-bash-danger",
                )

                self.assertEqual(candidate.candidate_action_type, RUN_COMMAND)
                self.assertEqual(candidate.candidate_status, DENY_CANDIDATE)
                self.assertEqual(candidate.declared_risk, HIGH)
                self.assertEqual(candidate.risk_status, BASH_DANGEROUS)
                self.assertEqual(candidate.payload["command"], command)
                self.assertEqual(candidate.capability_requirements, ("run_command",))
                self._assert_candidate_only_no_authority(candidate)

    def test_bash_unknown_not_checked_and_unparsed_commands_hold_current_state(self):
        commands = (
            "python -m unittest",
            NOT_CHECKED,
            "'unterminated",
        )

        for command in commands:
            with self.subTest(command=command):
                candidate = self._candidate("Bash", {"command": command}, "toolu-bash-hold")

                self.assertEqual(candidate.candidate_action_type, RUN_COMMAND)
                self.assertEqual(candidate.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
                self.assertEqual(candidate.declared_risk, NOT_CHECKED)
                self.assertEqual(candidate.risk_status, BASH_NOT_CHECKED)
                self.assertFalse(candidate.unsupported_unknown_or_not_checked_is_pass)
                self.assertEqual(candidate.decision, SAFE_DEFAULT)
                self._assert_candidate_only_no_authority(candidate)

    def test_unknown_tool_maps_to_hold_current_state_not_pass(self):
        hook_input = ClaudeCodePreToolUseInput(
            tool_name="Task",
            tool_input={},
            tool_use_id="toolu-task-001",
        )

        candidate = map_pretooluse_input_to_structured_action_candidate(hook_input)

        self.assertEqual(candidate.candidate_action_type, HOLD_CURRENT_STATE)
        self.assertEqual(candidate.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
        self.assertEqual(candidate.declared_risk, NOT_CHECKED)
        self.assertEqual(candidate.risk_status, UNKNOWN_TOOL)
        self.assertFalse(candidate.unsupported_unknown_or_not_checked_is_pass)
        self._assert_provenance(candidate, "Task", "toolu-task-001")
        self._assert_candidate_only_no_authority(candidate)

    def test_invalid_tool_input_shape_holds_current_state(self):
        cases = (
            ("Read", {}, READ_REPO),
            ("Write", {"file_path": "README.md"}, WRITE_FILE),
            ("Edit", {"file_path": "README.md", "old_string": "old"}, EDIT_FILE),
            ("Bash", {}, RUN_COMMAND),
        )

        for tool_name, tool_input, expected_action in cases:
            with self.subTest(tool_name=tool_name):
                hook_input = ClaudeCodePreToolUseInput(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_use_id=f"toolu-invalid-{tool_name}",
                )

                candidate = map_pretooluse_input_to_structured_action_candidate(hook_input)

                self.assertEqual(candidate.candidate_action_type, expected_action)
                self.assertEqual(candidate.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
                self.assertEqual(candidate.declared_risk, NOT_CHECKED)
                self.assertEqual(candidate.decision, SAFE_DEFAULT)
                self._assert_candidate_only_no_authority(candidate)

    def test_mapping_output_is_frozen_and_caller_mutation_does_not_persist(self):
        raw_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "README.md"},
            "tool_use_id": "toolu-freeze-001",
            "session_id": "session-001",
        }
        result = validate_claude_code_pretooluse_input(raw_input)
        candidate = map_pretooluse_input_to_structured_action_candidate(result.hook_input)
        raw_input["tool_input"]["file_path"] = ".env"

        self.assertEqual(candidate.payload["file_path"], "README.md")
        self.assertIsInstance(candidate.payload, MappingProxyType)
        self.assertIsInstance(candidate.provenance, MappingProxyType)
        self.assertEqual(candidate.provenance["metadata"]["session_id"], "session-001")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            candidate.candidate_status = DENY_CANDIDATE
        with self.assertRaises(TypeError):
            candidate.payload["file_path"] = ".env"

    def test_mapping_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            candidate = self._candidate(
                "Write",
                {"file_path": "example.md", "content": "data only"},
                "toolu-write-no-mutation",
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(candidate.candidate_action_type, WRITE_FILE)
            self.assertEqual(before, after)
            self._assert_candidate_only_no_authority(candidate)

    def test_evidence_records_contract_only_boundaries(self):
        evidence = build_tool_call_mapping_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_2_COMPLETE_LABEL)
        self.assertEqual(
            evidence["supported_tool_mappings"],
            {
                "Read": READ_REPO,
                "Write": WRITE_FILE,
                "Edit": EDIT_FILE,
                "Bash": RUN_COMMAND,
            },
        )
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertTrue(evidence["mapping_output_is_structured_action_candidate_only"])
        for field in (
            "mapping_output_is_execution",
            "mapping_output_is_permission_decision",
            "mapping_output_is_hook_response",
            "mapping_output_grants_write_authority",
            "mapping_output_applies_patch",
            "hook_input_trusted_as_decision",
            "hook_input_trusted_as_capability_grant",
            "unsupported_unknown_or_not_checked_is_pass",
            "hook_command_implemented",
            "hook_installation_implemented",
            "claude_code_execution_performed",
            "codex_implementation_added",
            "provider_model_network_implemented",
            "api_key_env_secret_loading_implemented",
            "network_client_implemented",
            "action_execution_engine_implemented",
            "tool_runtime_implemented",
            "write_authority_granted",
            "filesystem_mutation_by_mapping",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])

    def test_mapping_source_has_no_hook_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(claude_code_tool_call_mapping)
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

    def test_doc_records_required_mapping_and_boundaries(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_2_COMPLETE_LABEL,
            "Read(file_path)",
            "-> READ_REPO candidate",
            "Write(file_path, content)",
            "-> WRITE_FILE candidate",
            "Edit(file_path, old_string, new_string)",
            "-> EDIT_FILE candidate",
            "Bash(command)",
            "-> RUN_COMMAND candidate",
            "mapping output is structured action candidate only",
            "mapping output != execution",
            "mapping output != permission decision",
            "mapping output != hook response",
            "mapping output != write authority",
            "mapping output != patch application",
            "mapping output preserves tool_use_id provenance",
            "hook input remains untrusted raw executor output",
            "unsupported/unknown/NOT_CHECKED != PASS",
            "safe default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "main merge = NOT_PERFORMED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_policy_handling_and_non_goals(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            ".env target -> DENY_CANDIDATE",
            ".aeg path segment -> DENY_CANDIDATE",
            "secret path segment -> DENY_CANDIDATE",
            "protected path segment -> DENY_CANDIDATE",
            "rm -rf",
            "git push",
            "deploy",
            "curl",
            "wget",
            "env",
            "printenv",
            "chmod",
            "chown",
            "sudo",
            "unknown Bash = hold_current_state",
            "NOT_CHECKED Bash = hold_current_state",
            "Unknown, unsupported, or NOT_CHECKED tool names",
            "hook command implementation",
            ".claude/settings.json mutation",
            "actual hook installation",
            "actual Claude Code execution",
            "Codex implementation",
            "provider/model/network implementation",
            "OpenAI/Ollama/LLM call",
            "API key/env/secret loading",
            "network client",
            "subprocess execution",
            "shell execution",
            "action execution engine",
            "write authority",
            "tool runtime",
            "store.py change",
            "filesystem mutation by hook runtime or action execution",
            "patch application",
            "public release",
            "universal prompt-injection prevention claim",
            "sandbox/process isolation claim",
            "Bash-safe claim",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def _candidate(self, tool_name, tool_input, tool_use_id):
        result = validate_claude_code_pretooluse_input(
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_use_id": tool_use_id,
            }
        )
        self.assertTrue(result.valid, result.reasons)
        return map_pretooluse_input_to_structured_action_candidate(result.hook_input)

    def _assert_provenance(self, candidate, tool_name, tool_use_id):
        self.assertEqual(candidate.source_tool_name, tool_name)
        self.assertEqual(candidate.source_tool_use_id, tool_use_id)
        self.assertEqual(candidate.action_id, f"pretooluse:{tool_use_id}")
        self.assertEqual(candidate.provenance["source_tool_name"], tool_name)
        self.assertEqual(candidate.provenance["source_tool_use_id"], tool_use_id)
        self.assertEqual(
            candidate.provenance["trust_boundary"],
            "untrusted_raw_executor_output",
        )

    def _assert_candidate_only_no_authority(self, candidate):
        self.assertTrue(candidate.mapping_output_is_structured_action_candidate_only)
        self.assertFalse(candidate.mapping_output_is_execution)
        self.assertFalse(candidate.mapping_output_is_permission_decision)
        self.assertFalse(candidate.mapping_output_is_hook_response)
        self.assertFalse(candidate.mapping_output_grants_write_authority)
        self.assertFalse(candidate.mapping_output_applies_patch)
        self.assertFalse(candidate.hook_input_trusted_as_decision)
        self.assertFalse(candidate.hook_input_trusted_as_capability_grant)
        self.assertFalse(candidate.execution_allowed)
        self.assertFalse(candidate.mutation_allowed)
        self.assertFalse(candidate.write_authority_granted)
        self.assertFalse(candidate.hook_response_produced)
        self.assertFalse(candidate.patch_application_performed)
        self.assertEqual(candidate.decision, SAFE_DEFAULT)
        self.assertEqual(candidate.safe_default, SAFE_DEFAULT)
        self.assertEqual(candidate.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)


if __name__ == "__main__":
    unittest.main()
