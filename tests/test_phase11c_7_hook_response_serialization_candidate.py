import dataclasses
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import hook_response_serialization_candidate
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
from src.evidence.hook_evidence_binding import build_hook_evidence_binding
from src.evidence.hook_evidence_verification_gate import (
    VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    verify_hook_evidence_binding_candidate,
)
from src.evidence.hook_response_envelope_candidate import (
    RESPONSE_ALLOW,
    RESPONSE_ASK,
    RESPONSE_DEFER,
    RESPONSE_DENY,
    RESPONSE_HOLD_CURRENT_STATE,
    build_hook_response_envelope_candidate,
)
from src.evidence.hook_response_serialization_candidate import (
    PHASE11C_7_COMPLETE_LABEL,
    RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME,
    RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
    SERIALIZATION_HASH_ALGORITHM,
    SERIALIZATION_REDACTION_POLICY,
    SERIALIZED_PAYLOAD_HASH_ALGORITHM,
    build_hook_response_serialization_candidate,
    build_hook_response_serialization_candidate_contract_evidence,
    hook_response_serialization_candidate_digest,
    serialized_payload_candidate_digest,
)


DOC_PATH = Path("docs/phase11c_7_hook_response_serialization_candidate_v0.md")


class Phase11C7HookResponseSerializationCandidateTests(unittest.TestCase):
    def test_allow_envelope_maps_to_data_only_allow_serialization_candidate(self):
        envelope, binding, verification, _ = self._envelope(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c7-allow.md"},
                "tool_use_id": "toolu-serialization-allow-001",
            }
        )

        serialization = build_hook_response_serialization_candidate(
            envelope_candidate=envelope
        )
        payload = self._payload(serialization)

        self.assertEqual(binding.decision_candidate, ALLOW)
        self.assertEqual(
            verification.verification_output,
            VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        )
        self.assertEqual(envelope.response_candidate_type, RESPONSE_ALLOW)
        self.assertEqual(serialization.source_envelope_id, envelope.envelope_id)
        self.assertEqual(serialization.source_envelope_hash, envelope.envelope_hash)
        self.assertEqual(serialization.source_response_candidate_type, RESPONSE_ALLOW)
        self.assertEqual(payload["response_candidate_type"], RESPONSE_ALLOW)
        self.assertEqual(payload["source_envelope_hash"], envelope.envelope_hash)
        self.assertEqual(
            serialization.response_transport_candidate,
            RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        )
        self.assertEqual(
            serialization.response_schema_status,
            RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME,
        )
        self.assertIn(
            "allow_envelope_candidate_maps_to_allow_serialization_candidate_only",
            serialization.reason_codes,
        )
        self.assertIn(
            "allow_serialization_candidate_is_not_execution",
            serialization.reason_codes,
        )
        self._assert_hashes(serialization)
        self._assert_serialization_only_no_authority(serialization)

    def test_deny_ask_defer_and_hold_envelopes_map_to_matching_payload_candidates(self):
        cases = (
            (
                "deny",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": ".env"},
                    "tool_use_id": "toolu-serialization-deny-001",
                },
                DENY,
                RESPONSE_DENY,
                "deny_serialization_candidate_is_not_real_denial_response",
            ),
            (
                "ask",
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c7-ask.md",
                        "content": "contract only",
                    },
                    "tool_use_id": "toolu-serialization-ask-001",
                },
                ASK,
                RESPONSE_ASK,
                "ask_serialization_candidate_is_not_user_prompt_implementation",
            ),
            (
                "defer",
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "printf contract-only"},
                    "tool_use_id": "toolu-serialization-defer-001",
                },
                DEFER,
                RESPONSE_DEFER,
                "defer_or_hold_serialization_candidate_preserves_safe_default",
            ),
        )

        for name, raw_input, decision, expected_response, expected_reason in cases:
            with self.subTest(name=name):
                envelope, binding, _, _ = self._envelope(raw_input)

                serialization = build_hook_response_serialization_candidate(
                    envelope_candidate=envelope.to_record()
                )
                payload = self._payload(serialization)

                self.assertEqual(binding.decision_candidate, decision)
                self.assertEqual(envelope.response_candidate_type, expected_response)
                self.assertEqual(
                    serialization.source_response_candidate_type,
                    expected_response,
                )
                self.assertEqual(payload["response_candidate_type"], expected_response)
                self.assertIn(expected_reason, serialization.reason_codes)
                self._assert_serialization_only_no_authority(serialization)

        hold_envelope = self._rejected_hold_envelope()
        hold_serialization = build_hook_response_serialization_candidate(
            envelope_candidate=hold_envelope
        )
        hold_payload = self._payload(hold_serialization)

        self.assertEqual(hold_envelope.response_candidate_type, RESPONSE_HOLD_CURRENT_STATE)
        self.assertEqual(
            hold_serialization.source_response_candidate_type,
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertEqual(
            hold_payload["response_candidate_type"],
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertIn(
            "hold_current_state_envelope_candidate_maps_to_hold_current_state_serialization_candidate",
            hold_serialization.reason_codes,
        )
        self.assertIn("safe_default_hold_current_state", hold_serialization.reason_codes)
        self._assert_serialization_only_no_authority(hold_serialization)

    def test_malformed_unknown_and_mismatched_source_envelopes_hold_without_source_ids(self):
        valid_envelope, _, _, _ = self._envelope(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c7-mismatch.md"},
                "tool_use_id": "toolu-serialization-mismatch-001",
            }
        )

        hash_mismatch = valid_envelope.to_record()
        hash_mismatch["envelope_hash"] = "0" * 64

        unknown_response = valid_envelope.to_record()
        unknown_response["response_candidate_type"] = "unknown_response_candidate"
        self._rebind_source_envelope_record(unknown_response)

        runtime_flag = valid_envelope.to_record()
        runtime_flag["real_hook_response_emitted"] = True
        self._rebind_source_envelope_record(runtime_flag)

        cases = (
            (
                "malformed",
                {"tool_input": {"content": "PHASE11C7_RAW_SECRET_VALUE"}},
                "malformed_source_envelope",
            ),
            ("hash_mismatch", hash_mismatch, "source_envelope_hash_mismatch"),
            (
                "unknown_response",
                unknown_response,
                "unknown_source_response_candidate_type",
            ),
            (
                "runtime_flag",
                runtime_flag,
                "source_envelope_runtime_emission_authority_or_store_write_flag_mismatch",
            ),
        )

        for name, source, expected_reason in cases:
            with self.subTest(name=name):
                serialization = build_hook_response_serialization_candidate(
                    envelope_candidate=source
                )
                payload = self._payload(serialization)

                self.assertIsNone(serialization.source_envelope_id)
                self.assertIsNone(serialization.source_envelope_hash)
                self.assertIsNone(serialization.source_response_candidate_type)
                self.assertEqual(
                    payload["response_candidate_type"],
                    RESPONSE_HOLD_CURRENT_STATE,
                )
                self.assertIsNone(payload["source_envelope_hash"])
                self.assertIsNone(payload["source_response_candidate_type"])
                self.assertIn(expected_reason, serialization.reason_codes)
                self.assertIn(
                    "malformed_or_mismatched_source_envelope_maps_to_hold_current_state_serialization_candidate",
                    serialization.reason_codes,
                )
                self.assertNotIn(
                    "PHASE11C7_RAW_SECRET_VALUE",
                    json.dumps(serialization.to_record(), sort_keys=True),
                )
                self._assert_serialization_only_no_authority(serialization)

    def test_redaction_omits_raw_tool_input_secrets_and_source_metadata_from_payload(self):
        envelope, _, _, _ = self._envelope(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "cat /tmp/PHASE11C7_SECRET_PATH && "
                        "printf token=PHASE11C7_SUPER_SECRET_VALUE"
                    )
                },
                "tool_use_id": "toolu-serialization-redaction-001",
            }
        )
        source = envelope.to_record()
        source["tool_input"] = {
            "command": "printf token=PHASE11C7_SUPER_SECRET_VALUE"
        }
        source["phase11c4_target_scope_metadata"] = {
            "path": "/tmp/PHASE11C7_SECRET_PATH"
        }
        source["phase11c4_payload_metadata"] = {
            "content": "token=PHASE11C7_SUPER_SECRET_VALUE"
        }
        source["phase11c4_provenance_metadata"] = {
            "raw_decision_reason": "raw decision PHASE11C7_SECRET_REASON"
        }
        source["decision_reasons"] = ("raw decision PHASE11C7_SECRET_REASON",)

        serialization = build_hook_response_serialization_candidate(
            envelope_candidate=source
        )
        payload = self._payload(serialization)
        serialized_text = serialization.serialized_payload_candidate
        record_text = json.dumps(serialization.to_record(), sort_keys=True)

        self.assertEqual(
            set(payload),
            {
                "serialized_payload_version",
                "response_candidate_type",
                "source_envelope_hash",
                "source_response_candidate_type",
                "response_transport_candidate",
                "response_schema_status",
                "redacted_user_message",
                "reason_codes",
                "audit_summary",
                "safe_default",
                "live_executor_authority",
                "trust_boundary",
            },
        )
        for raw_fragment in (
            "tool_input",
            "PHASE11C7_SECRET_PATH",
            "PHASE11C7_SUPER_SECRET_VALUE",
            "token=PHASE11C7_SUPER_SECRET_VALUE",
            "phase11c4_target_scope_metadata",
            "phase11c4_payload_metadata",
            "phase11c4_provenance_metadata",
            "raw decision PHASE11C7_SECRET_REASON",
        ):
            with self.subTest(raw_fragment=raw_fragment):
                self.assertNotIn(raw_fragment, serialized_text)
                self.assertNotIn(raw_fragment, record_text)
        self.assertFalse(payload["audit_summary"]["raw_full_input_included"])
        self.assertFalse(
            payload["audit_summary"][
                "raw_secret_bearing_path_content_command_text_included"
            ]
        )
        self.assertFalse(
            payload["audit_summary"]["target_scope_payload_provenance_metadata_copied"]
        )
        self.assertFalse(payload["audit_summary"]["raw_decision_reason_strings_copied"])
        self._assert_serialization_only_no_authority(serialization)

    def test_hashes_are_deterministic_and_candidate_is_immutable(self):
        envelope, _, _, _ = self._envelope(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c7-hash.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-serialization-hash-001",
            }
        )

        serialization = build_hook_response_serialization_candidate(
            envelope_candidate=envelope
        )
        payload = self._payload(serialization)

        self.assertEqual(
            serialization.serialized_payload_candidate,
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        self.assertEqual(serialization.serialization_hash_algorithm, SERIALIZATION_HASH_ALGORITHM)
        self.assertEqual(
            serialization.serialized_payload_hash_algorithm,
            SERIALIZED_PAYLOAD_HASH_ALGORITHM,
        )
        self.assertEqual(
            serialization.serialization_redaction_policy,
            SERIALIZATION_REDACTION_POLICY,
        )
        self._assert_hashes(serialization)
        self.assertIsInstance(serialization.audit_summary, MappingProxyType)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            serialization.source_envelope_hash = None
        with self.assertRaises(TypeError):
            serialization.audit_summary["raw_full_tool_input_included"] = True

    def test_source_envelope_consistency_requires_expected_boundary_and_false_flags(self):
        envelope, _, _, _ = self._envelope(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c7-consistency.md"},
                "tool_use_id": "toolu-serialization-consistency-001",
            }
        )
        cases = (
            (
                "safe_default",
                lambda record: record.update({"safe_default": "allow"}),
                "source_envelope_safe_default_mismatch",
            ),
            (
                "live_executor_authority",
                lambda record: record.update({"live_executor_authority": "LIVE"}),
                "source_envelope_live_executor_authority_not_on_hold",
            ),
            (
                "trust_boundary",
                lambda record: record.update({"trust_boundary": "trusted"}),
                "source_envelope_trust_boundary_mismatch",
            ),
            (
                "stdout_stderr_hook_output_written",
                lambda record: record.update({"stdout_stderr_hook_output_written": True}),
                "source_envelope_runtime_emission_authority_or_store_write_flag_mismatch",
            ),
            (
                "state_store_module_changed",
                lambda record: record.update({"state_store_module_changed": True}),
                "source_envelope_runtime_emission_authority_or_store_write_flag_mismatch",
            ),
        )

        for name, mutate, expected_reason in cases:
            with self.subTest(name=name):
                record = envelope.to_record()
                mutate(record)
                self._rebind_source_envelope_record(record)

                serialization = build_hook_response_serialization_candidate(
                    envelope_candidate=record
                )

                self.assertIsNone(serialization.source_envelope_id)
                self.assertIsNone(serialization.source_envelope_hash)
                self.assertIsNone(serialization.source_response_candidate_type)
                self.assertEqual(
                    self._payload(serialization)["response_candidate_type"],
                    RESPONSE_HOLD_CURRENT_STATE,
                )
                self.assertIn(expected_reason, serialization.reason_codes)
                self._assert_serialization_only_no_authority(serialization)

    def test_contract_evidence_records_mapping_redaction_hashes_and_boundaries(self):
        evidence = build_hook_response_serialization_candidate_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_7_COMPLETE_LABEL)
        self.assertEqual(
            evidence["response_transport_candidate"],
            RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        )
        self.assertEqual(
            evidence["response_schema_status"],
            RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME,
        )
        self.assertEqual(evidence["allow_envelope_policy"], RESPONSE_ALLOW)
        self.assertEqual(evidence["deny_envelope_policy"], RESPONSE_DENY)
        self.assertEqual(evidence["ask_envelope_policy"], RESPONSE_ASK)
        self.assertEqual(evidence["defer_envelope_policy"], RESPONSE_DEFER)
        self.assertEqual(
            evidence["hold_current_state_envelope_policy"],
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertEqual(
            evidence["unknown_malformed_envelope_policy"],
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertTrue(evidence["serialization_hash_recomputes_deterministically"])
        self.assertTrue(
            evidence["serialized_payload_hash_recomputes_deterministically"]
        )
        self.assertTrue(evidence["serialization_id_matches_serialization_hash"])
        self.assertTrue(evidence["source_envelope_hash_must_match_envelope_hash"])
        self.assertFalse(evidence["mismatched_source_envelope_copies_source_ids"])
        self.assertFalse(
            evidence["raw_full_tool_input_in_serialized_payload_candidate"]
        )
        self.assertFalse(
            evidence[
                "raw_secret_bearing_path_content_command_text_in_serialized_payload_candidate"
            ]
        )
        self.assertFalse(evidence["target_scope_payload_provenance_metadata_copied"])
        self.assertFalse(evidence["raw_decision_reason_strings_copied"])
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertEqual(evidence["trust_boundary"], UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        for field in (
            "serialization_candidate_is_real_claude_code_hook_response",
            "serialization_candidate_is_stdout_stderr_emission",
            "serialization_candidate_is_hook_runtime",
            "serialization_candidate_is_hook_command",
            "serialization_candidate_is_execution",
            "serialization_candidate_is_action_execution_engine",
            "serialization_candidate_is_write_authority",
            "serialization_candidate_is_store_write",
            "serialization_candidate_mutates_filesystem",
            "allow_serialization_candidate_is_execution",
            "deny_serialization_candidate_is_real_denial_response",
            "ask_serialization_candidate_is_user_prompt_implementation",
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
            "filesystem_mutation_by_serialization",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])
        self.assertTrue(
            evidence["defer_or_hold_serialization_candidate_preserves_safe_default"]
        )

    def test_serialization_candidate_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            envelope, _, _, _ = self._envelope(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c7-no-mutation.md",
                        "content": "contract only",
                    },
                    "tool_use_id": "toolu-serialization-no-mutation-001",
                }
            )

            serialization = build_hook_response_serialization_candidate(
                envelope_candidate=envelope
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse(serialization.filesystem_mutation_by_serialization)
            self.assertFalse(serialization.serialization_candidate_mutates_filesystem)
            self._assert_serialization_only_no_authority(serialization)

    def test_serialization_source_has_no_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(hook_response_serialization_candidate)
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

    def test_doc_records_required_fields_mapping_invariants_and_non_goals(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_7_COMPLETE_LABEL,
            "serialization_id",
            "serialization_hash",
            "serialization_version",
            "source_envelope_id",
            "source_envelope_hash",
            "source_response_candidate_type",
            "serialized_payload_candidate",
            "serialized_payload_hash",
            "response_transport_candidate = data_only_not_stdout",
            "response_schema_status = generic_candidate_not_substrate_runtime",
            "redacted_user_message",
            "reason_codes",
            "audit_summary",
            "safe_default",
            "live_executor_authority",
            "trust_boundary",
            "allow envelope candidate -> allow serialization candidate only",
            "deny envelope candidate -> deny serialization candidate only",
            "ask envelope candidate -> ask serialization candidate only",
            "defer envelope candidate -> defer serialization candidate only",
            "hold_current_state envelope candidate -> hold_current_state serialization candidate",
            "malformed/unknown envelope -> hold_current_state serialization candidate",
            "serialization candidate != real Claude Code hook response",
            "serialization candidate != stdout/stderr emission",
            "serialization candidate != hook runtime",
            "serialization candidate != hook command",
            "serialization candidate != execution",
            "serialization candidate != action execution engine",
            "serialization candidate != write authority",
            "serialization candidate != store write",
            "serialization candidate does not mutate filesystem",
            "allow serialization candidate != execution",
            "deny serialization candidate != real denial response",
            "ask serialization candidate != user prompt implementation",
            "defer/hold serialization candidate preserves safe default",
            "safe default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "reported_only != judgment basis",
            "NOT_CHECKED != PASS",
            "No raw full tool_input in serialized payload candidate.",
            "No raw secret-bearing path/content/command text in serialized payload candidate by default.",
            "Do not copy 11-C-4 target scope, payload, provenance metadata, or raw decision reason strings.",
            "serialization_hash recomputes deterministically",
            "serialized_payload_hash recomputes deterministically",
            "serialization_id matches serialization_hash",
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

    def _envelope(self, raw_input):
        hook_input, action_candidate, decision_candidate = self._input_action_decision(
            raw_input
        )
        binding = build_hook_evidence_binding(
            hook_input=hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        )
        verification = verify_hook_evidence_binding_candidate(binding)
        envelope = build_hook_response_envelope_candidate(
            verification_result=verification,
            binding_record=binding,
            decision_candidate=decision_candidate,
        )
        return envelope, binding, verification, decision_candidate

    def _rejected_hold_envelope(self):
        hook_input, action_candidate, _ = self._input_action_decision(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c7-rejected.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-serialization-rejected-001",
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
        return build_hook_response_envelope_candidate(
            verification_result=verification,
            binding_record=binding,
            decision_candidate=rejected_decision,
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

    def _payload(self, serialization):
        return json.loads(serialization.serialized_payload_candidate)

    def _assert_hashes(self, serialization):
        self.assertEqual(
            serialization.serialized_payload_hash,
            serialized_payload_candidate_digest(
                serialization.serialized_payload_candidate
            ),
        )
        self.assertEqual(
            serialization.serialization_hash,
            hook_response_serialization_candidate_digest(serialization),
        )
        self.assertTrue(
            serialization.serialization_id.endswith(serialization.serialization_hash)
        )

    def _rebind_source_envelope_record(self, record):
        envelope_hash = (
            hook_response_serialization_candidate._source_envelope_hash_from_record(
                record
            )
        )
        record["envelope_hash"] = envelope_hash
        record["envelope_id"] = f"phase11c-6-hook-response-envelope:{envelope_hash}"

    def _assert_serialization_only_no_authority(self, serialization):
        self.assertEqual(serialization.completion_label, PHASE11C_7_COMPLETE_LABEL)
        self.assertEqual(serialization.safe_default, SAFE_DEFAULT)
        self.assertEqual(
            serialization.live_executor_authority,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertEqual(serialization.trust_boundary, UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        self.assertFalse(
            serialization.serialization_candidate_is_real_claude_code_hook_response
        )
        self.assertFalse(serialization.serialization_candidate_is_stdout_stderr_emission)
        self.assertFalse(serialization.serialization_candidate_is_hook_runtime)
        self.assertFalse(serialization.serialization_candidate_is_hook_command)
        self.assertFalse(serialization.serialization_candidate_is_execution)
        self.assertFalse(
            serialization.serialization_candidate_is_action_execution_engine
        )
        self.assertFalse(serialization.serialization_candidate_is_write_authority)
        self.assertFalse(serialization.serialization_candidate_is_store_write)
        self.assertFalse(serialization.serialization_candidate_mutates_filesystem)
        self.assertFalse(serialization.allow_serialization_candidate_is_execution)
        self.assertFalse(
            serialization.deny_serialization_candidate_is_real_denial_response
        )
        self.assertFalse(
            serialization.ask_serialization_candidate_is_user_prompt_implementation
        )
        self.assertTrue(
            serialization.defer_or_hold_serialization_candidate_preserves_safe_default
        )
        self.assertFalse(serialization.reported_only_is_judgment_basis)
        self.assertFalse(serialization.not_checked_is_pass)
        self.assertFalse(serialization.safe_default_changed)
        self.assertFalse(serialization.hook_command_implemented)
        self.assertFalse(serialization.hook_installation_implemented)
        self.assertFalse(serialization.claude_code_execution_performed)
        self.assertFalse(serialization.real_hook_response_emitted)
        self.assertFalse(serialization.stdout_stderr_hook_output_written)
        self.assertFalse(serialization.codex_implementation_added)
        self.assertFalse(serialization.provider_model_network_implemented)
        self.assertFalse(serialization.llm_call_implemented)
        self.assertFalse(serialization.api_key_env_secret_loading_implemented)
        self.assertFalse(serialization.network_client_implemented)
        self.assertFalse(serialization.process_execution_implemented)
        self.assertFalse(serialization.shell_execution_implemented)
        self.assertFalse(serialization.action_execution_engine_implemented)
        self.assertFalse(serialization.tool_runtime_implemented)
        self.assertFalse(serialization.write_authority_granted)
        self.assertFalse(serialization.state_store_module_changed)
        self.assertFalse(serialization.filesystem_mutation_by_serialization)
        self.assertFalse(serialization.patch_application_implemented)
        self.assertFalse(serialization.public_release_performed)
        self.assertFalse(serialization.universal_prompt_injection_prevention_claimed)
        self.assertFalse(serialization.sandbox_process_isolation_claimed)
        self.assertFalse(serialization.bash_safe_claimed)


if __name__ == "__main__":
    unittest.main()
