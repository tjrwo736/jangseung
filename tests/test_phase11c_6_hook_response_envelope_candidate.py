import dataclasses
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import hook_response_envelope_candidate
from src.evidence.claude_code_pretooluse_input_contract import (
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    map_pretooluse_input_to_structured_action_candidate,
)
from src.evidence.hook_decision_adapter import (
    ALLOW,
    ASK,
    DEFER,
    DENY,
    adapt_structured_action_candidate_to_hook_decision_candidate,
)
from src.evidence.hook_evidence_binding import (
    HOOK_EVIDENCE_BINDING_REJECTED,
    build_hook_evidence_binding,
)
from src.evidence.hook_evidence_verification_gate import (
    BINDING_HASH_MISMATCH_REJECTED,
    HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
    REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    verify_hook_evidence_binding_candidate,
)
from src.evidence.hook_response_envelope_candidate import (
    ENVELOPE_HASH_ALGORITHM,
    ENVELOPE_REDACTION_POLICY,
    HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES,
    PHASE11C_6_COMPLETE_LABEL,
    RESPONSE_ALLOW,
    RESPONSE_ASK,
    RESPONSE_DEFER,
    RESPONSE_DENY,
    RESPONSE_HOLD_CURRENT_STATE,
    build_hook_response_envelope_candidate,
    build_hook_response_envelope_candidate_contract_evidence,
    hook_response_envelope_candidate_digest,
)


DOC_PATH = Path("docs/phase11c_6_hook_response_envelope_candidate_v0.md")


class Phase11C6HookResponseEnvelopeCandidateTests(unittest.TestCase):
    def test_verified_allow_decision_maps_to_allow_envelope_candidate_only(self):
        binding, verification, decision = self._verified_source(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c6-read.md"},
                "tool_use_id": "toolu-envelope-allow-001",
            }
        )

        envelope = build_hook_response_envelope_candidate(
            verification_result=verification,
            binding_record=binding,
            decision_candidate=decision,
        )

        self.assertEqual(
            verification.verification_output,
            VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        )
        self.assertEqual(envelope.response_candidate_type, RESPONSE_ALLOW)
        self.assertEqual(envelope.source_decision_candidate, ALLOW)
        self.assertEqual(envelope.source_binding_id, binding.binding_id)
        self.assertEqual(envelope.source_binding_hash, binding.binding_hash)
        self.assertIn(
            "source_decision_allow_maps_to_allow_envelope_candidate",
            envelope.response_reason_codes,
        )
        self.assertFalse(envelope.allow_envelope_candidate_is_execution)
        self._assert_envelope_only_no_authority(envelope)

    def test_verified_deny_ask_and_defer_decisions_map_to_matching_candidates(self):
        cases = (
            (
                "deny",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": ".env"},
                    "tool_use_id": "toolu-envelope-deny-001",
                },
                DENY,
                RESPONSE_DENY,
                "deny_envelope_candidate_is_not_real_denial_response",
            ),
            (
                "ask",
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c6-write.md",
                        "content": "contract only",
                    },
                    "tool_use_id": "toolu-envelope-ask-001",
                },
                ASK,
                RESPONSE_ASK,
                "ask_envelope_candidate_is_not_user_prompt_implementation",
            ),
            (
                "defer",
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "printf contract-only"},
                    "tool_use_id": "toolu-envelope-defer-001",
                },
                DEFER,
                RESPONSE_DEFER,
                "defer_envelope_candidate_preserves_safe_default",
            ),
        )

        for name, raw_input, expected_decision, expected_response, expected_reason in cases:
            with self.subTest(name=name):
                binding, verification, decision = self._verified_source(raw_input)

                envelope = build_hook_response_envelope_candidate(
                    verification_result=verification,
                    binding_record=binding.to_record(),
                    decision_candidate=decision,
                )

                self.assertEqual(binding.decision_candidate, expected_decision)
                self.assertEqual(envelope.source_decision_candidate, expected_decision)
                self.assertEqual(envelope.response_candidate_type, expected_response)
                self.assertIn(expected_reason, envelope.response_reason_codes)
                self.assertFalse(envelope.real_hook_response_emitted)
                self.assertFalse(envelope.stdout_stderr_hook_output_written)
                self._assert_envelope_only_no_authority(envelope)

    def test_rejected_binding_candidate_maps_to_hold_not_real_denial_response(self):
        hook_input, action_candidate, _ = self._input_action_decision(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c6-rejected.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-envelope-rejected-001",
            }
        )
        rejected_action = dataclasses.replace(
            action_candidate,
            write_authority_granted=True,
        )
        rejected_decision = adapt_structured_action_candidate_to_hook_decision_candidate(
            rejected_action
        )
        binding = build_hook_evidence_binding(
            hook_input=hook_input,
            action_candidate=rejected_action,
            decision_candidate=rejected_decision,
        )
        verification = verify_hook_evidence_binding_candidate(binding)

        envelope = build_hook_response_envelope_candidate(
            verification_result=verification,
            binding_record=binding,
            decision_candidate=rejected_decision,
        )

        self.assertEqual(binding.binding_status, HOOK_EVIDENCE_BINDING_REJECTED)
        self.assertEqual(
            verification.verification_output,
            REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        )
        self.assertEqual(envelope.response_candidate_type, RESPONSE_HOLD_CURRENT_STATE)
        self.assertIn(
            "rejected_binding_maps_to_hold_current_state_envelope_candidate",
            envelope.response_reason_codes,
        )
        self.assertFalse(envelope.deny_envelope_candidate_is_real_denial_response)
        self._assert_envelope_only_no_authority(envelope)

    def test_hold_verification_and_malformed_inputs_hold_current_state(self):
        record = self._binding(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c6-tamper.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-envelope-hold-001",
            }
        ).to_record()
        record["binding_hash"] = "0" * 64
        hold_verification = verify_hook_evidence_binding_candidate(record)

        hold_envelope = build_hook_response_envelope_candidate(
            verification_result=hold_verification,
            binding_record=record,
        )
        malformed_envelope = build_hook_response_envelope_candidate(
            verification_result={"verification_output": "allow"},
            binding_record={"tool_input": {"content": "PHASE11C6_RAW_SECRET"}},
        )
        unknown_output_envelope = build_hook_response_envelope_candidate(
            verification_result={
                "verification_output": "UNKNOWN_VERIFICATION_OUTPUT",
                "verification_passed": True,
                "binding_id": record["binding_id"],
                "binding_hash": record["binding_hash"],
                "rejection_codes": (),
                "safe_default": SAFE_DEFAULT,
                "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
                "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
            },
            binding_record=record,
        )

        self.assertEqual(
            hold_verification.verification_output,
            HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
        )
        self.assertIn(BINDING_HASH_MISMATCH_REJECTED, hold_verification.rejection_codes)
        self.assertEqual(
            hold_envelope.response_candidate_type,
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertIsNone(hold_envelope.source_binding_id)
        self.assertIn(
            "hold_current_state_verification_maps_to_hold_current_state_envelope_candidate",
            hold_envelope.response_reason_codes,
        )
        self.assertEqual(
            malformed_envelope.response_candidate_type,
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertIsNone(malformed_envelope.source_binding_id)
        self.assertIn(
            "malformed_source_input_maps_to_hold_current_state",
            malformed_envelope.response_reason_codes,
        )
        self.assertEqual(
            unknown_output_envelope.response_candidate_type,
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertIn(
            "unknown_source_verification_output",
            unknown_output_envelope.response_reason_codes,
        )
        self.assertNotIn(
            "PHASE11C6_RAW_SECRET",
            json.dumps(malformed_envelope.to_record(), sort_keys=True),
        )
        self._assert_envelope_only_no_authority(hold_envelope)
        self._assert_envelope_only_no_authority(malformed_envelope)
        self._assert_envelope_only_no_authority(unknown_output_envelope)

    def test_optional_decision_mismatch_holds_current_state(self):
        read_binding, read_verification, _ = self._verified_source(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c6-read-mismatch.md"},
                "tool_use_id": "toolu-envelope-read-mismatch-001",
            }
        )
        _, _, write_decision = self._verified_source(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c6-write-mismatch.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-envelope-write-mismatch-001",
            }
        )

        envelope = build_hook_response_envelope_candidate(
            verification_result=read_verification,
            binding_record=read_binding,
            decision_candidate=write_decision,
        )

        self.assertEqual(envelope.response_candidate_type, RESPONSE_HOLD_CURRENT_STATE)
        self.assertIn(
            "optional_decision_candidate_mismatch",
            envelope.response_reason_codes,
        )
        self.assertIsNone(envelope.source_binding_hash)
        self._assert_envelope_only_no_authority(envelope)

    def test_envelope_hash_redaction_and_immutability(self):
        binding, verification, decision = self._verified_source(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c6-secret-path.md",
                    "content": "token=PHASE11C6_SUPER_SECRET_VALUE",
                },
                "tool_use_id": "toolu-envelope-redaction-001",
            }
        )

        envelope = build_hook_response_envelope_candidate(
            verification_result=verification,
            binding_record=binding,
            decision_candidate=decision,
        )

        self.assertEqual(envelope.envelope_hash_algorithm, ENVELOPE_HASH_ALGORITHM)
        self.assertEqual(envelope.envelope_redaction_policy, ENVELOPE_REDACTION_POLICY)
        self.assertEqual(
            envelope.envelope_hash,
            hook_response_envelope_candidate_digest(envelope),
        )
        self.assertTrue(envelope.envelope_id.endswith(envelope.envelope_hash))
        self.assertIsInstance(envelope.audit_summary, MappingProxyType)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            envelope.response_candidate_type = RESPONSE_ALLOW
        with self.assertRaises(TypeError):
            envelope.audit_summary["raw_full_input_included"] = True

        record_text = json.dumps(envelope.to_record(), sort_keys=True)
        for raw_fragment in (
            "docs/phase11c6-secret-path.md",
            "PHASE11C6_SUPER_SECRET_VALUE",
            "token=PHASE11C6_SUPER_SECRET_VALUE",
            "tool_input",
        ):
            with self.subTest(raw_fragment=raw_fragment):
                self.assertNotIn(raw_fragment, record_text)
        self.assertFalse(envelope.audit_summary["raw_full_input_included"])
        self.assertFalse(
            envelope.audit_summary[
                "raw_secret_bearing_path_content_command_text_included"
            ]
        )
        self._assert_envelope_only_no_authority(envelope)

    def test_contract_evidence_records_mapping_redaction_and_boundaries(self):
        evidence = build_hook_response_envelope_candidate_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_6_COMPLETE_LABEL)
        self.assertEqual(
            evidence["response_candidate_types"],
            HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES,
        )
        self.assertEqual(evidence["verified_allow_policy"], RESPONSE_ALLOW)
        self.assertEqual(evidence["verified_deny_policy"], RESPONSE_DENY)
        self.assertEqual(evidence["verified_ask_policy"], RESPONSE_ASK)
        self.assertEqual(evidence["verified_defer_policy"], RESPONSE_DEFER)
        self.assertEqual(
            evidence["rejected_binding_policy"],
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertEqual(
            evidence["hold_verification_policy"],
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertEqual(
            evidence["unknown_malformed_input_policy"],
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertFalse(evidence["raw_full_input_included"])
        self.assertFalse(evidence["raw_secret_bearing_path_content_command_text_included"])
        self.assertTrue(
            evidence["user_facing_message_uses_redacted_summary_and_reason_codes_only"]
        )
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertEqual(evidence["trust_boundary"], UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        for field in (
            "envelope_candidate_is_real_claude_code_hook_response",
            "envelope_candidate_is_stdout_stderr_emission",
            "envelope_candidate_is_hook_runtime",
            "envelope_candidate_is_execution",
            "envelope_candidate_is_action_execution_engine",
            "envelope_candidate_is_write_authority",
            "envelope_candidate_is_store_write",
            "envelope_candidate_mutates_filesystem",
            "allow_envelope_candidate_is_execution",
            "deny_envelope_candidate_is_real_denial_response",
            "ask_envelope_candidate_is_user_prompt_implementation",
            "reported_only_is_judgment_basis",
            "not_checked_is_pass",
            "hook_command_implemented",
            "hook_installation_implemented",
            "claude_code_execution_performed",
            "real_hook_response_emitted",
            "stdout_stderr_hook_output_written",
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
            "filesystem_mutation_by_envelope",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])
        self.assertTrue(
            evidence["defer_or_hold_envelope_candidate_preserves_safe_default"]
        )

    def test_envelope_candidate_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            binding, verification, decision = self._verified_source(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c6-no-mutation.md",
                        "content": "contract only",
                    },
                    "tool_use_id": "toolu-envelope-no-mutation-001",
                }
            )

            envelope = build_hook_response_envelope_candidate(
                verification_result=verification,
                binding_record=binding,
                decision_candidate=decision,
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse(envelope.filesystem_mutation_by_envelope)
            self.assertFalse(envelope.envelope_candidate_mutates_filesystem)
            self._assert_envelope_only_no_authority(envelope)

    def test_envelope_source_has_no_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(hook_response_envelope_candidate)
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

    def test_doc_records_required_mapping_invariants_and_non_goals(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_6_COMPLETE_LABEL,
            "envelope_id",
            "envelope_hash",
            "envelope_version",
            "source_binding_id",
            "source_binding_hash",
            "source_verification_output",
            "source_decision_candidate",
            "source_tool_use_id",
            "action_id",
            "response_candidate_type",
            "response_reason_codes",
            "redacted_user_message",
            "audit_summary",
            "safe_default",
            "live_executor_authority",
            "trust_boundary",
            "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=allow -> allow envelope candidate only",
            "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=deny -> deny envelope candidate only",
            "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=ask -> ask envelope candidate only",
            "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=defer -> defer envelope candidate",
            "REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE -> hold_current_state envelope candidate",
            "HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE -> hold_current_state envelope candidate",
            "Unknown/malformed input -> hold_current_state envelope candidate",
            "envelope candidate != real Claude Code hook response",
            "envelope candidate != stdout/stderr emission",
            "envelope candidate != hook runtime",
            "envelope candidate != execution",
            "envelope candidate != action execution engine",
            "envelope candidate != write authority",
            "envelope candidate != store write",
            "envelope candidate does not mutate filesystem",
            "allow envelope candidate != execution",
            "deny envelope candidate != real denial response",
            "ask envelope candidate != user prompt implementation",
            "defer/hold envelope candidate preserves safe default",
            "safe default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "reported_only != judgment basis",
            "NOT_CHECKED != PASS",
            "No raw full tool_input in envelope.",
            "No raw secret-bearing path/content/command text in envelope by default.",
            "User-facing/audit message uses redacted summaries and reason codes only.",
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
            "stdout/stderr hook output",
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

    def _verified_source(self, raw_input):
        hook_input, action_candidate, decision_candidate = self._input_action_decision(
            raw_input
        )
        binding = build_hook_evidence_binding(
            hook_input=hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        )
        verification = verify_hook_evidence_binding_candidate(binding)
        self.assertEqual(
            verification.verification_output,
            VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        )
        return binding, verification, decision_candidate

    def _binding(self, raw_input):
        hook_input, action_candidate, decision_candidate = self._input_action_decision(
            raw_input
        )
        return build_hook_evidence_binding(
            hook_input=hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        )

    def _input_action_decision(self, raw_input):
        result = validate_claude_code_pretooluse_input(raw_input)
        self.assertTrue(result.valid, result.reasons)
        action_candidate = map_pretooluse_input_to_structured_action_candidate(
            result.hook_input
        )
        decision_candidate = adapt_structured_action_candidate_to_hook_decision_candidate(
            action_candidate
        )
        return result.hook_input, action_candidate, decision_candidate

    def _assert_envelope_only_no_authority(self, envelope):
        self.assertEqual(envelope.completion_label, PHASE11C_6_COMPLETE_LABEL)
        self.assertEqual(envelope.safe_default, SAFE_DEFAULT)
        self.assertEqual(envelope.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(envelope.trust_boundary, UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        self.assertFalse(envelope.envelope_candidate_is_real_claude_code_hook_response)
        self.assertFalse(envelope.envelope_candidate_is_stdout_stderr_emission)
        self.assertFalse(envelope.envelope_candidate_is_hook_runtime)
        self.assertFalse(envelope.envelope_candidate_is_execution)
        self.assertFalse(envelope.envelope_candidate_is_action_execution_engine)
        self.assertFalse(envelope.envelope_candidate_is_write_authority)
        self.assertFalse(envelope.envelope_candidate_is_store_write)
        self.assertFalse(envelope.envelope_candidate_mutates_filesystem)
        self.assertFalse(envelope.allow_envelope_candidate_is_execution)
        self.assertFalse(envelope.deny_envelope_candidate_is_real_denial_response)
        self.assertFalse(envelope.ask_envelope_candidate_is_user_prompt_implementation)
        self.assertTrue(envelope.defer_or_hold_envelope_candidate_preserves_safe_default)
        self.assertFalse(envelope.reported_only_is_judgment_basis)
        self.assertFalse(envelope.not_checked_is_pass)
        self.assertFalse(envelope.safe_default_changed)
        self.assertFalse(envelope.hook_command_implemented)
        self.assertFalse(envelope.hook_installation_implemented)
        self.assertFalse(envelope.claude_code_execution_performed)
        self.assertFalse(envelope.real_hook_response_emitted)
        self.assertFalse(envelope.stdout_stderr_hook_output_written)
        self.assertFalse(envelope.codex_implementation_added)
        self.assertFalse(envelope.provider_model_network_implemented)
        self.assertFalse(envelope.llm_call_implemented)
        self.assertFalse(envelope.api_key_env_secret_loading_implemented)
        self.assertFalse(envelope.network_client_implemented)
        self.assertFalse(envelope.process_execution_implemented)
        self.assertFalse(envelope.shell_execution_implemented)
        self.assertFalse(envelope.action_execution_engine_implemented)
        self.assertFalse(envelope.tool_runtime_implemented)
        self.assertFalse(envelope.write_authority_granted)
        self.assertFalse(envelope.state_store_module_changed)
        self.assertFalse(envelope.filesystem_mutation_by_envelope)
        self.assertFalse(envelope.patch_application_implemented)
        self.assertFalse(envelope.public_release_performed)
        self.assertFalse(envelope.universal_prompt_injection_prevention_claimed)
        self.assertFalse(envelope.sandbox_process_isolation_claimed)
        self.assertFalse(envelope.bash_safe_claimed)


if __name__ == "__main__":
    unittest.main()
