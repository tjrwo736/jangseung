import dataclasses
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, NOT_CHECKED, SAFE_DEFAULT
from src.evidence import hook_evidence_binding
from src.evidence.claude_code_pretooluse_input_contract import (
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    DENY_CANDIDATE,
    HOLD_CURRENT_STATE_CANDIDATE,
    PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
    RUN_COMMAND,
    STRUCTURED_ACTION_CANDIDATE,
    WRITE_FILE,
    map_pretooluse_input_to_structured_action_candidate,
)
from src.evidence.hook_decision_adapter import (
    ASK,
    DEFER,
    PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
    adapt_structured_action_candidate_to_hook_decision_candidate,
)
from src.evidence.hook_evidence_binding import (
    HOOK_EVIDENCE_BOUND,
    PHASE11C_4_COMPLETE_LABEL,
    TOOL_INPUT_HASH_ALGORITHM,
    TOOL_INPUT_REDACTION_POLICY,
    build_hook_evidence_binding,
    build_hook_evidence_binding_contract_evidence,
    hash_hook_tool_input,
    hook_evidence_binding_digest,
)


DOC_PATH = Path("docs/phase11c_4_hook_evidence_binding_v0.md")


class Phase11C4HookEvidenceBindingTests(unittest.TestCase):
    def test_binding_records_required_fields_without_raw_tool_input(self):
        binding = self._binding(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/example.md",
                    "content": "token=PHASE11C4_SUPER_SECRET_VALUE",
                },
                "tool_use_id": "toolu-write-bind-001",
                "session_id": "session-001",
            }
        )

        self.assertEqual(binding.binding_status, HOOK_EVIDENCE_BOUND)
        self.assertEqual(binding.completion_label, PHASE11C_4_COMPLETE_LABEL)
        self.assertEqual(binding.tool_name, "Write")
        self.assertEqual(binding.tool_use_id, "toolu-write-bind-001")
        self.assertEqual(binding.source_tool_use_id, "toolu-write-bind-001")
        self.assertEqual(binding.action_id, "pretooluse:toolu-write-bind-001")
        self.assertEqual(binding.candidate_action_type, WRITE_FILE)
        self.assertEqual(binding.candidate_status, STRUCTURED_ACTION_CANDIDATE)
        self.assertEqual(binding.decision_candidate, ASK)
        self.assertIn("write_or_edit_not_allowed_by_default", binding.decision_reasons)
        self.assertEqual(binding.tool_input_hash_algorithm, TOOL_INPUT_HASH_ALGORITHM)
        self.assertEqual(binding.tool_input_redaction_policy, TOOL_INPUT_REDACTION_POLICY)
        self.assertFalse(binding.tool_input_raw_stored)
        self.assertIn("content", binding.tool_input_redacted_metadata["redacted_paths"])
        self.assertIn("content", binding.tool_input_redacted_metadata["secret_like_paths"])
        self.assertIsInstance(binding.tool_input_redacted_metadata, MappingProxyType)
        self.assertIsInstance(binding.provenance, MappingProxyType)
        self._assert_no_secret_or_raw_tool_input(binding)
        self._assert_binding_only_no_authority(binding)

    def test_env_and_api_key_like_values_are_redacted_in_metadata(self):
        binding = self._binding(
            {
                "tool_name": "Read",
                "tool_input": {
                    "file_path": ".env.local",
                    "api_key": "PHASE11C4_API_KEY_VALUE",
                },
                "tool_use_id": "toolu-read-env-001",
                "extra_api_token": "PHASE11C4_EXTRA_TOKEN_VALUE",
            }
        )

        self.assertEqual(binding.candidate_status, DENY_CANDIDATE)
        self.assertIn("file_path", binding.tool_input_redacted_metadata["redacted_paths"])
        self.assertIn("api_key", binding.tool_input_redacted_metadata["redacted_paths"])
        self.assertIn(
            "extra_api_token",
            binding.provenance["hook_input"]["extra_untrusted_fields"]["redacted_paths"],
        )
        record_text = json.dumps(binding.to_record(), sort_keys=True)
        for secret_fragment in (
            ".env.local",
            "PHASE11C4_API_KEY_VALUE",
            "PHASE11C4_EXTRA_TOKEN_VALUE",
        ):
            with self.subTest(secret_fragment=secret_fragment):
                self.assertNotIn(secret_fragment, record_text)
        self._assert_binding_only_no_authority(binding)

    def test_tool_input_hash_is_deterministic_and_binding_digest_replays(self):
        first = {
            "file_path": "docs/example.md",
            "content": "token=PHASE11C4_REPEATABLE_SECRET",
        }
        second = {
            "content": "token=PHASE11C4_REPEATABLE_SECRET",
            "file_path": "docs/example.md",
        }
        first_binding = self._binding(
            {
                "tool_name": "Write",
                "tool_input": first,
                "tool_use_id": "toolu-digest-001",
            }
        )
        second_input_hash = hash_hook_tool_input(second)

        self.assertEqual(first_binding.tool_input_hash, second_input_hash)
        self.assertEqual(
            first_binding.binding_hash,
            hook_evidence_binding_digest(first_binding),
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first_binding.tool_name = "Read"
        with self.assertRaises(TypeError):
            first_binding.provenance["hook_input"] = {}

    def test_reported_only_and_not_checked_remain_non_judgment_basis(self):
        raw_result = validate_claude_code_pretooluse_input(
            {
                "tool_name": "Bash",
                "tool_input": {"command": NOT_CHECKED},
                "tool_use_id": "toolu-bash-not-checked-001",
            }
        )
        self.assertTrue(raw_result.valid, raw_result.reasons)
        source = map_pretooluse_input_to_structured_action_candidate(
            raw_result.hook_input
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
            },
        )
        decision = adapt_structured_action_candidate_to_hook_decision_candidate(
            reported_source
        )
        binding = build_hook_evidence_binding(
            hook_input=raw_result.hook_input,
            action_candidate=reported_source,
            decision_candidate=decision,
        )

        self.assertEqual(binding.candidate_action_type, RUN_COMMAND)
        self.assertEqual(binding.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
        self.assertEqual(binding.decision_candidate, DEFER)
        self.assertFalse(binding.reported_only_trusted_as_judgment_basis)
        self.assertFalse(binding.reported_only_is_judgment_basis)
        self.assertFalse(binding.not_checked_is_pass)
        self.assertIn(
            "provenance.reported_only.decision",
            binding.provenance["hook_decision_candidate"]["ignored_reported_only_fields"],
        )
        self._assert_binding_only_no_authority(binding)

    def test_binding_preserves_provenance_versions_and_trust_boundary(self):
        binding = self._binding(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/provenance.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-provenance-001",
                "cwd": "/repo",
                "substrate_name": "claude-code",
            }
        )

        self.assertEqual(binding.trust_boundary, "untrusted_raw_executor_output")
        self.assertEqual(
            binding.provenance["structured_action_candidate"]["contract_version"],
            PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
        )
        self.assertEqual(
            binding.provenance["hook_decision_candidate"]["contract_version"],
            PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
        )
        self.assertEqual(
            binding.provenance["hook_input"]["tool_input_hash"],
            binding.tool_input_hash,
        )
        self.assertFalse(binding.provenance["hook_input"]["tool_input_raw_stored"])
        self.assertEqual(binding.safe_default, SAFE_DEFAULT)
        self.assertEqual(
            binding.live_executor_authority,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )

    def test_binding_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            binding = self._binding(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "example.md",
                        "content": "data only",
                    },
                    "tool_use_id": "toolu-no-mutation-001",
                }
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse(binding.filesystem_mutation_by_binding)
            self.assertFalse(binding.evidence_binding_mutates_filesystem)
            self._assert_binding_only_no_authority(binding)

    def test_contract_evidence_records_boundaries(self):
        evidence = build_hook_evidence_binding_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_4_COMPLETE_LABEL)
        self.assertEqual(evidence["tool_input_hash_algorithm"], TOOL_INPUT_HASH_ALGORITHM)
        self.assertEqual(evidence["tool_input_redaction_policy"], TOOL_INPUT_REDACTION_POLICY)
        self.assertFalse(evidence["raw_tool_input_stored_by_default"])
        self.assertTrue(evidence["secret_like_values_redacted"])
        self.assertTrue(evidence["preserves_metadata_without_raw_secret_retention"])
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        for field in (
            "evidence_binding_is_judgment_basis",
            "evidence_binding_is_execution",
            "evidence_binding_is_hook_response",
            "evidence_binding_is_write_authority",
            "evidence_binding_is_store_write",
            "evidence_binding_mutates_filesystem",
            "reported_only_is_judgment_basis",
            "not_checked_is_pass",
            "hook_command_implemented",
            "hook_installation_implemented",
            "claude_code_execution_performed",
            "real_hook_response_emitted",
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
            "filesystem_mutation_by_binding",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])

    def test_binding_source_has_no_hook_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(hook_evidence_binding)
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

    def test_doc_records_required_binding_redaction_and_non_goals(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_4_COMPLETE_LABEL,
            "tool_name",
            "tool_use_id",
            "tool_input_hash",
            "source_tool_use_id",
            "action_id",
            "candidate_action_type",
            "candidate_status",
            "decision_candidate",
            "decision reasons",
            "declared_risk",
            "risk_status",
            "capability_requirements",
            "provenance",
            "safe default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "trust boundary",
            "Raw full `tool_input` is not stored by default.",
            "tool_input_hash = sha256_canonical_json_v0(tool_input)",
            ".env path/value -> redacted",
            "api_key-like key/value -> redacted",
            "token-like key/value -> redacted",
            "secret-like key/value -> redacted",
            "evidence binding != judgment basis by itself",
            "evidence binding != execution",
            "evidence binding != hook response",
            "evidence binding != write authority",
            "evidence binding != store write",
            "evidence binding does not mutate filesystem",
            "reported_only != judgment basis",
            "NOT_CHECKED != PASS",
            "main merge = NOT_PERFORMED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_records_forbidden_runtime_boundaries(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
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

    def _binding(self, raw_input):
        result = validate_claude_code_pretooluse_input(raw_input)
        self.assertTrue(result.valid, result.reasons)
        action_candidate = map_pretooluse_input_to_structured_action_candidate(
            result.hook_input
        )
        decision_candidate = adapt_structured_action_candidate_to_hook_decision_candidate(
            action_candidate
        )
        return build_hook_evidence_binding(
            hook_input=result.hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        )

    def _assert_no_secret_or_raw_tool_input(self, binding):
        record_text = json.dumps(binding.to_record(), sort_keys=True)
        for raw_fragment in (
            "PHASE11C4_SUPER_SECRET_VALUE",
            "token=PHASE11C4_SUPER_SECRET_VALUE",
            "docs/example.md",
        ):
            with self.subTest(raw_fragment=raw_fragment):
                self.assertNotIn(raw_fragment, record_text)

    def _assert_binding_only_no_authority(self, binding):
        self.assertFalse(binding.evidence_binding_is_judgment_basis)
        self.assertFalse(binding.evidence_binding_is_execution)
        self.assertFalse(binding.evidence_binding_is_hook_response)
        self.assertFalse(binding.evidence_binding_is_write_authority)
        self.assertFalse(binding.evidence_binding_is_store_write)
        self.assertFalse(binding.evidence_binding_mutates_filesystem)
        self.assertFalse(binding.reported_only_trusted_as_judgment_basis)
        self.assertFalse(binding.reported_only_is_judgment_basis)
        self.assertFalse(binding.not_checked_is_pass)
        self.assertFalse(binding.safe_default_changed)
        self.assertFalse(binding.hook_command_implemented)
        self.assertFalse(binding.hook_installation_implemented)
        self.assertFalse(binding.claude_code_execution_performed)
        self.assertFalse(binding.real_hook_response_emitted)
        self.assertFalse(binding.codex_implementation_added)
        self.assertFalse(binding.provider_model_network_implemented)
        self.assertFalse(binding.llm_call_implemented)
        self.assertFalse(binding.api_key_env_secret_loading_implemented)
        self.assertFalse(binding.network_client_implemented)
        self.assertFalse(binding.process_execution_implemented)
        self.assertFalse(binding.shell_execution_implemented)
        self.assertFalse(binding.action_execution_engine_implemented)
        self.assertFalse(binding.tool_runtime_implemented)
        self.assertFalse(binding.write_authority_granted)
        self.assertFalse(binding.state_store_module_changed)
        self.assertFalse(binding.filesystem_mutation_by_binding)
        self.assertFalse(binding.patch_application_implemented)
        self.assertFalse(binding.public_release_performed)
        self.assertFalse(binding.universal_prompt_injection_prevention_claimed)
        self.assertFalse(binding.sandbox_process_isolation_claimed)
        self.assertFalse(binding.bash_safe_claimed)
        self.assertEqual(binding.safe_default, SAFE_DEFAULT)
        self.assertEqual(binding.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)


if __name__ == "__main__":
    unittest.main()
