import dataclasses
import inspect
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LOW, NOT_CHECKED, SAFE_DEFAULT
from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence import hook_decision_adapter
from src.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    DENY_CANDIDATE,
    EDIT_FILE,
    HOLD_CURRENT_STATE,
    HOLD_CURRENT_STATE_CANDIDATE,
    NORMAL_REPO_PATH,
    PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
    PROTECTED_PATH,
    READ_REPO,
    RUN_COMMAND,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    WRITE_FILE,
    map_pretooluse_input_to_structured_action_candidate,
)
from src.evidence.hook_decision_adapter import (
    ALLOW,
    ASK,
    DEFER,
    DENY,
    HOOK_DECISION_CANDIDATE_ONLY,
    PHASE11C_3_COMPLETE_LABEL,
    adapt_structured_action_candidate_to_hook_decision_candidate,
    build_hook_decision_adapter_contract_evidence,
)


DOC_PATH = Path("docs/phase11c_3_hook_decision_adapter_v0.md")


class Phase11C3HookDecisionAdapterTests(unittest.TestCase):
    def test_read_low_normal_repo_candidate_maps_to_allow_candidate_only(self):
        source = self._source_candidate(
            "Read",
            {"file_path": "src/example.py"},
            "toolu-read-allow-001",
        )

        decision = adapt_structured_action_candidate_to_hook_decision_candidate(source)

        self.assertEqual(decision.decision_candidate, ALLOW)
        self.assertEqual(decision.candidate_status, HOOK_DECISION_CANDIDATE_ONLY)
        self.assertEqual(decision.source_candidate_action_type, READ_REPO)
        self.assertEqual(decision.source_candidate_status, STRUCTURED_ACTION_CANDIDATE)
        self.assertEqual(decision.source_declared_risk, LOW)
        self.assertEqual(decision.source_risk_status, NORMAL_REPO_PATH)
        self._assert_provenance(decision, source)
        self._assert_candidate_only_no_authority(decision)

    def test_write_and_edit_normal_repo_candidates_map_to_ask_not_allow(self):
        cases = (
            (
                "Write",
                {"file_path": "docs/example.md", "content": "contract only"},
                WRITE_FILE,
            ),
            (
                "Edit",
                {
                    "file_path": "src/example.py",
                    "old_string": "old",
                    "new_string": "new",
                },
                EDIT_FILE,
            ),
        )

        for tool_name, tool_input, expected_action in cases:
            with self.subTest(tool_name=tool_name):
                source = self._source_candidate(
                    tool_name,
                    tool_input,
                    f"toolu-{tool_name.lower()}-ask-001",
                )

                decision = adapt_structured_action_candidate_to_hook_decision_candidate(
                    source
                )

                self.assertEqual(decision.decision_candidate, ASK)
                self.assertNotEqual(decision.decision_candidate, ALLOW)
                self.assertEqual(decision.source_candidate_action_type, expected_action)
                self.assertIn(
                    "write_or_edit_not_allowed_by_default",
                    decision.reasons,
                )
                self._assert_provenance(decision, source)
                self._assert_candidate_only_no_authority(decision)

    def test_explicit_deny_candidates_map_to_deny_candidate(self):
        cases = (
            (
                "Read",
                {"file_path": ".env"},
                READ_REPO,
                PROTECTED_PATH,
            ),
            (
                "Write",
                {"file_path": ".aeg/state.json", "content": "data"},
                WRITE_FILE,
                PROTECTED_PATH,
            ),
            (
                "Bash",
                {"command": "rm -rf build"},
                RUN_COMMAND,
                "BASH_DANGEROUS",
            ),
        )

        for tool_name, tool_input, expected_action, expected_risk_status in cases:
            with self.subTest(tool_name=tool_name, tool_input=tool_input):
                source = self._source_candidate(
                    tool_name,
                    tool_input,
                    f"toolu-{tool_name.lower()}-deny-001",
                )

                decision = adapt_structured_action_candidate_to_hook_decision_candidate(
                    source
                )

                self.assertEqual(source.candidate_status, DENY_CANDIDATE)
                self.assertEqual(decision.decision_candidate, DENY)
                self.assertEqual(decision.source_candidate_action_type, expected_action)
                self.assertEqual(decision.source_risk_status, expected_risk_status)
                self._assert_provenance(decision, source)
                self._assert_candidate_only_no_authority(decision)

    def test_run_command_hold_current_state_and_not_checked_defer_never_allow(self):
        commands = (
            "python -m unittest",
            NOT_CHECKED,
            "'unterminated",
        )

        for command in commands:
            with self.subTest(command=command):
                source = self._source_candidate(
                    "Bash",
                    {"command": command},
                    "toolu-bash-defer-001",
                )

                decision = adapt_structured_action_candidate_to_hook_decision_candidate(
                    source
                )

                self.assertEqual(source.candidate_action_type, RUN_COMMAND)
                self.assertEqual(source.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
                self.assertEqual(source.declared_risk, NOT_CHECKED)
                self.assertEqual(decision.decision_candidate, DEFER)
                self.assertNotEqual(decision.decision_candidate, ALLOW)
                self.assertFalse(decision.not_checked_is_allow)
                self.assertFalse(decision.unsupported_unknown_or_not_checked_is_allow)
                self._assert_candidate_only_no_authority(decision)

    def test_unknown_unsupported_invalid_and_invariant_mismatch_defer_never_allow(self):
        unknown_hook_input = ClaudeCodePreToolUseInput(
            tool_name="Task",
            tool_input={},
            tool_use_id="toolu-task-defer-001",
        )
        unknown_source = map_pretooluse_input_to_structured_action_candidate(
            unknown_hook_input
        )
        invalid_shape_source = self._raw_source_candidate(
            "Read",
            {},
            "toolu-read-invalid-001",
        )
        promoted_source = dataclasses.replace(
            self._source_candidate(
                "Read",
                {"file_path": "README.md"},
                "toolu-read-promoted-001",
            ),
            decision=ALLOW,
        )

        cases = (
            (unknown_source, HOLD_CURRENT_STATE, UNKNOWN_TOOL),
            (invalid_shape_source, READ_REPO, "INVALID_TOOL_INPUT"),
            (promoted_source, READ_REPO, NORMAL_REPO_PATH),
            ({"decision": "allow", "reported_only": True}, None, None),
            (None, None, None),
        )

        for source, expected_action, expected_risk_status in cases:
            with self.subTest(source_type=type(source).__name__):
                decision = adapt_structured_action_candidate_to_hook_decision_candidate(
                    source
                )

                self.assertEqual(decision.decision_candidate, DEFER)
                self.assertNotEqual(decision.decision_candidate, ALLOW)
                self.assertFalse(decision.not_checked_is_allow)
                self.assertFalse(decision.unsupported_unknown_or_not_checked_is_allow)
                if expected_action is not None:
                    self.assertEqual(decision.source_candidate_action_type, expected_action)
                    self.assertEqual(decision.source_risk_status, expected_risk_status)
                self._assert_candidate_only_no_authority(decision)

    def test_reported_only_self_reported_allow_is_ignored(self):
        source = self._source_candidate(
            "Write",
            {"file_path": "docs/example.md", "content": "contract only"},
            "toolu-write-report-001",
        )
        reported_source = dataclasses.replace(
            source,
            provenance={
                "source_tool_name": source.provenance["source_tool_name"],
                "source_tool_use_id": source.provenance["source_tool_use_id"],
                "source_contract_version": source.provenance["source_contract_version"],
                "trust_boundary": source.provenance["trust_boundary"],
                "metadata": {},
                "reported_only": {"decision": "allow"},
                "self_reported_decision": "allow",
            },
        )

        decision = adapt_structured_action_candidate_to_hook_decision_candidate(
            reported_source
        )

        self.assertEqual(decision.decision_candidate, ASK)
        self.assertNotEqual(decision.decision_candidate, ALLOW)
        self.assertIn(
            "reported_only_or_self_reported_allow_ignored",
            decision.reasons,
        )
        self.assertIn(
            "provenance.reported_only.decision",
            decision.ignored_reported_only_fields,
        )
        self.assertIn(
            "provenance.self_reported_decision",
            decision.ignored_reported_only_fields,
        )
        self.assertFalse(decision.reported_only_trusted_as_judgment_basis)
        self._assert_candidate_only_no_authority(decision)

    def test_adapter_output_is_frozen_and_preserves_source_provenance(self):
        source = self._source_candidate(
            "Read",
            {"file_path": "README.md"},
            "toolu-freeze-001",
        )

        decision = adapt_structured_action_candidate_to_hook_decision_candidate(source)

        self.assertIsInstance(decision.source_provenance, MappingProxyType)
        self.assertEqual(decision.source_contract_version, PHASE11C_2_TOOL_CALL_MAPPING_VERSION)
        self._assert_provenance(decision, source)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            decision.decision_candidate = DENY
        with self.assertRaises(TypeError):
            decision.source_provenance["source_tool_use_id"] = "mutated"

    def test_adapter_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            source = self._source_candidate(
                "Write",
                {"file_path": "example.md", "content": "data only"},
                "toolu-write-no-mutation",
            )
            decision = adapt_structured_action_candidate_to_hook_decision_candidate(
                source
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(decision.decision_candidate, ASK)
            self.assertFalse(decision.adapter_output_mutates_filesystem)
            self._assert_candidate_only_no_authority(decision)

    def test_evidence_records_contract_only_boundaries(self):
        evidence = build_hook_decision_adapter_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_3_COMPLETE_LABEL)
        self.assertEqual(
            evidence["generic_decision_candidates"],
            (ALLOW, DENY, ASK, DEFER),
        )
        self.assertEqual(evidence["read_repo_low_normal_policy"], ALLOW)
        self.assertEqual(evidence["write_file_normal_policy"], ASK)
        self.assertEqual(evidence["edit_file_normal_policy"], ASK)
        self.assertEqual(evidence["deny_candidate_policy"], DENY)
        self.assertEqual(evidence["run_command_hold_current_state_policy"], DEFER)
        self.assertEqual(evidence["unknown_unsupported_not_checked_policy"], DEFER)
        self.assertEqual(evidence["invalid_input_policy"], DEFER)
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertTrue(evidence["adapter_output_is_hook_decision_candidate_only"])
        self.assertTrue(evidence["source_tool_use_id_and_action_id_provenance_preserved"])
        self.assertTrue(evidence["reported_only_allow_ignored"])
        for field in (
            "adapter_output_is_actual_hook_response",
            "adapter_output_is_execution",
            "adapter_output_is_action_execution_engine",
            "adapter_output_grants_write_authority",
            "adapter_output_applies_patch",
            "adapter_output_mutates_filesystem",
            "adapter_output_emits_real_hook_response",
            "not_checked_is_allow",
            "unsupported_unknown_or_not_checked_is_allow",
            "reported_only_trusted_as_judgment_basis",
            "hook_command_implemented",
            "hook_installation_implemented",
            "claude_code_execution_performed",
            "codex_implementation_added",
            "provider_model_network_implemented",
            "llm_call_implemented",
            "api_key_env_secret_loading_implemented",
            "network_client_implemented",
            "process_execution_implemented",
            "shell_execution_implemented",
            "action_execution_engine_implemented",
            "tool_runtime_implemented",
            "write_authority_granted",
            "state_store_module_changed",
            "filesystem_mutation_by_adapter",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])

    def test_adapter_source_has_no_hook_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(hook_decision_adapter)
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

    def test_doc_records_required_contract_mapping_and_boundaries(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_3_COMPLETE_LABEL,
            "adapter output = hook decision candidate only",
            "adapter output != actual hook response emission",
            "adapter output != execution",
            "adapter output != action execution engine",
            "adapter output != write authority",
            "adapter output != patch application",
            "adapter output does not mutate filesystem",
            "adapter output preserves source tool_use_id and action_id provenance",
            "allow",
            "deny",
            "ask",
            "defer",
            "READ_REPO normal repo path / LOW / STRUCTURED_ACTION_CANDIDATE",
            "-> allow candidate",
            "WRITE_FILE normal repo path / LOW / STRUCTURED_ACTION_CANDIDATE",
            "-> ask candidate",
            "EDIT_FILE normal repo path / LOW / STRUCTURED_ACTION_CANDIDATE",
            "DENY_CANDIDATE",
            "-> deny candidate",
            "RUN_COMMAND with HOLD_CURRENT_STATE_CANDIDATE / NOT_CHECKED",
            "-> defer candidate",
            "safe default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "main merge = NOT_PERFORMED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_not_checked_reported_only_and_non_goals(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            "NOT_CHECKED != allow",
            "unsupported/unknown != allow",
            "unsupported/unknown/NOT_CHECKED != allow",
            "reported_only/self-reported allow is ignored",
            "reported_only != judgment basis",
            "hook command implementation",
            ".claude/settings.json mutation",
            "actual hook installation",
            "actual Claude Code execution",
            "real Claude Code hook response emission",
            "Codex implementation",
            "provider/model/network implementation",
            "OpenAI/Ollama/LLM call",
            "API key/env/secret loading",
            "network client",
            "subprocess/shell execution",
            "action execution engine",
            "write authority",
            "tool runtime",
            "store.py change",
            "filesystem mutation",
            "patch application",
            "public release",
            "universal prompt-injection prevention claim",
            "sandbox/process isolation claim",
            "Bash-safe claim",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def _source_candidate(self, tool_name, tool_input, tool_use_id):
        result = validate_claude_code_pretooluse_input(
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_use_id": tool_use_id,
            }
        )
        self.assertTrue(result.valid, result.reasons)
        return map_pretooluse_input_to_structured_action_candidate(result.hook_input)

    def _raw_source_candidate(self, tool_name, tool_input, tool_use_id):
        hook_input = ClaudeCodePreToolUseInput(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
        )
        return map_pretooluse_input_to_structured_action_candidate(hook_input)

    def _assert_provenance(self, decision, source):
        self.assertEqual(decision.source_tool_use_id, source.source_tool_use_id)
        self.assertEqual(decision.action_id, source.action_id)
        self.assertEqual(decision.source_tool_name, source.source_tool_name)
        self.assertEqual(
            decision.source_provenance["source_tool_use_id"],
            source.source_tool_use_id,
        )
        self.assertEqual(
            decision.source_provenance["source_tool_name"],
            source.source_tool_name,
        )

    def _assert_candidate_only_no_authority(self, decision):
        self.assertTrue(decision.adapter_output_is_hook_decision_candidate_only)
        self.assertFalse(decision.adapter_output_is_actual_hook_response)
        self.assertFalse(decision.adapter_output_is_execution)
        self.assertFalse(decision.adapter_output_is_action_execution_engine)
        self.assertFalse(decision.adapter_output_grants_write_authority)
        self.assertFalse(decision.adapter_output_applies_patch)
        self.assertFalse(decision.adapter_output_mutates_filesystem)
        self.assertFalse(decision.adapter_output_emits_real_hook_response)
        self.assertFalse(decision.action_executed)
        self.assertFalse(decision.execution_allowed)
        self.assertFalse(decision.mutation_allowed)
        self.assertFalse(decision.write_authority_granted)
        self.assertFalse(decision.hook_response_produced)
        self.assertFalse(decision.patch_application_performed)
        self.assertEqual(decision.safe_default, SAFE_DEFAULT)
        self.assertEqual(decision.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)


if __name__ == "__main__":
    unittest.main()
