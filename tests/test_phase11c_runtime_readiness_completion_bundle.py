import dataclasses
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import (
    claude_code_pretooluse_response_schema_candidate,
    hook_runtime_entrypoint_dry_candidate,
)
from src.evidence.claude_code_pretooluse_input_contract import (
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_pretooluse_response_schema_candidate import (
    CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
    DOCS_CHECKED_DATE,
    DOCS_SOURCE_STATUS,
    DOCS_SOURCE_TYPE,
    PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
    RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME,
    build_claude_code_pretooluse_response_schema_candidate,
    build_claude_code_pretooluse_response_schema_candidate_contract_evidence,
    claude_code_pretooluse_response_schema_candidate_digest,
)
from src.evidence.claude_code_tool_call_mapping import (
    BASH_NOT_CHECKED,
    HOLD_CURRENT_STATE_CANDIDATE,
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
    RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
    build_hook_response_serialization_candidate,
    hook_response_serialization_candidate_digest,
)
from src.evidence.hook_runtime_entrypoint_dry_candidate import (
    PHASE11C_DRY_RUNTIME_ENTRYPOINT_CANDIDATE_VERSION,
    build_hook_runtime_entrypoint_dry_candidate_contract_evidence,
    hook_runtime_dry_run_result_candidate_digest,
    run_pretooluse_dry_runtime_entrypoint_candidate,
)


RUNTIME_DOC_PATH = Path("docs/phase11c_runtime_readiness_completion_bundle_v0.md")
BASELINE_DOC_PATH = Path("docs/phase11c_completion_baseline_not_installed_v0.md")


class Phase11CRuntimeReadinessCompletionBundleTests(unittest.TestCase):
    def test_pretooluse_schema_candidate_maps_serialization_to_hook_specific_output(self):
        cases = (
            (
                "allow",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": "docs/phase11c-runtime-allow.md"},
                    "tool_use_id": "toolu-runtime-allow-001",
                },
                RESPONSE_ALLOW,
                ALLOW,
            ),
            (
                "deny",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": ".env"},
                    "tool_use_id": "toolu-runtime-deny-001",
                },
                RESPONSE_DENY,
                DENY,
            ),
            (
                "ask",
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c-runtime-ask.md",
                        "content": "candidate only",
                    },
                    "tool_use_id": "toolu-runtime-ask-001",
                },
                RESPONSE_ASK,
                ASK,
            ),
            (
                "defer",
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "printf candidate-only"},
                    "tool_use_id": "toolu-runtime-defer-001",
                },
                RESPONSE_DEFER,
                DEFER,
            ),
        )

        for name, raw_input, expected_response, expected_permission in cases:
            with self.subTest(name=name):
                serialization, _, _, _ = self._serialization_chain(raw_input)

                schema_candidate = build_claude_code_pretooluse_response_schema_candidate(
                    serialization
                )
                hook_specific = schema_candidate.hook_specific_output_candidate

                self.assertEqual(
                    schema_candidate.source_serialization_id,
                    serialization.serialization_id,
                )
                self.assertEqual(
                    schema_candidate.source_serialization_hash,
                    serialization.serialization_hash,
                )
                self.assertEqual(
                    schema_candidate.source_response_candidate_type,
                    expected_response,
                )
                self.assertEqual(
                    schema_candidate.response_schema_candidate_type,
                    expected_response,
                )
                self.assertEqual(
                    schema_candidate.permission_decision_candidate,
                    expected_permission,
                )
                self.assertEqual(set(hook_specific), {"hookSpecificOutput"})
                self.assertNotIn("decision", hook_specific)
                self.assertNotIn("reason", hook_specific)
                self.assertEqual(
                    hook_specific["hookSpecificOutput"],
                    {
                        "hookEventName": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
                        "permissionDecision": expected_permission,
                        "permissionDecisionReason": (
                            schema_candidate.permission_decision_reason_redacted
                        ),
                    },
                )
                self.assertIn(
                    "redacted_phase11c_pretooluse_candidate",
                    schema_candidate.permission_decision_reason_redacted,
                )
                self.assertNotIn(
                    raw_input["tool_use_id"],
                    schema_candidate.permission_decision_reason_redacted,
                )
                self._assert_schema_hashes(schema_candidate)
                self._assert_schema_candidate_only_no_authority(schema_candidate)

    def test_valid_hold_serialization_maps_to_conservative_deny_candidate(self):
        hold_serialization = build_hook_response_serialization_candidate(
            envelope_candidate={"malformed": True}
        )

        schema_candidate = build_claude_code_pretooluse_response_schema_candidate(
            hold_serialization
        )

        self.assertIsNone(hold_serialization.source_envelope_id)
        self.assertEqual(
            schema_candidate.source_serialization_id,
            hold_serialization.serialization_id,
        )
        self.assertEqual(
            schema_candidate.source_serialization_hash,
            hold_serialization.serialization_hash,
        )
        self.assertIsNone(schema_candidate.source_response_candidate_type)
        self.assertEqual(
            schema_candidate.response_schema_candidate_type,
            RESPONSE_HOLD_CURRENT_STATE,
        )
        self.assertEqual(schema_candidate.permission_decision_candidate, DENY)
        self.assertEqual(
            schema_candidate.hook_specific_output_candidate["hookSpecificOutput"][
                "permissionDecision"
            ],
            DENY,
        )
        self.assertIn(
            "safe_default=hold_current_state",
            schema_candidate.permission_decision_reason_redacted,
        )
        self._assert_schema_candidate_only_no_authority(schema_candidate)

    def test_malformed_hash_mismatched_and_runtime_flagged_serialization_holds(self):
        serialization, _, _, _ = self._serialization_chain(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c-runtime-mismatch.md"},
                "tool_use_id": "toolu-runtime-mismatch-001",
            }
        )

        hash_mismatch = serialization.to_record()
        hash_mismatch["serialization_hash"] = "0" * 64

        payload_hash_mismatch = serialization.to_record()
        payload_hash_mismatch["serialized_payload_hash"] = "1" * 64
        self._rebind_serialization_record(payload_hash_mismatch)

        runtime_flag = serialization.to_record()
        runtime_flag["real_hook_response_emitted"] = True

        cases = (
            ("malformed", {"raw": "PHASE11C_RUNTIME_SECRET"}, "malformed"),
            ("hash_mismatch", hash_mismatch, "source_serialization_hash_mismatch"),
            (
                "payload_hash_mismatch",
                payload_hash_mismatch,
                "source_serialized_payload_hash_mismatch",
            ),
            (
                "runtime_flag",
                runtime_flag,
                "source_serialization_runtime_emission_authority_or_store_write_flag_mismatch",
            ),
        )

        for name, source, reason in cases:
            with self.subTest(name=name):
                schema_candidate = (
                    build_claude_code_pretooluse_response_schema_candidate(source)
                )
                record_text = json.dumps(schema_candidate.to_record(), sort_keys=True)

                self.assertIsNone(schema_candidate.source_serialization_id)
                self.assertIsNone(schema_candidate.source_serialization_hash)
                self.assertIsNone(schema_candidate.source_response_candidate_type)
                self.assertEqual(
                    schema_candidate.response_schema_candidate_type,
                    RESPONSE_HOLD_CURRENT_STATE,
                )
                self.assertEqual(schema_candidate.permission_decision_candidate, DENY)
                self.assertIn(
                    "malformed_or_mismatched_serialization_maps_to_hold_current_state_schema_candidate",
                    schema_candidate.permission_decision_reason_redacted,
                )
                self.assertIn(reason, schema_candidate.permission_decision_reason_redacted)
                self.assertNotIn("PHASE11C_RUNTIME_SECRET", record_text)
                self._assert_schema_candidate_only_no_authority(schema_candidate)

    def test_dry_entrypoint_end_to_end_paths_from_11c1_through_runtime_candidate(self):
        cases = (
            (
                "read_normal",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": "docs/phase11c-runtime-read.md"},
                    "tool_use_id": "toolu-runtime-read-normal-001",
                },
                RESPONSE_ALLOW,
                RESPONSE_ALLOW,
            ),
            (
                "write_normal",
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c-runtime-write.md",
                        "content": "candidate only",
                    },
                    "tool_use_id": "toolu-runtime-write-normal-001",
                },
                RESPONSE_ASK,
                RESPONSE_ASK,
            ),
            (
                "read_env",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": ".env"},
                    "tool_use_id": "toolu-runtime-read-env-001",
                },
                RESPONSE_DENY,
                RESPONSE_DENY,
            ),
            (
                "bash_dangerous",
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "rm -rf build"},
                    "tool_use_id": "toolu-runtime-bash-danger-001",
                },
                RESPONSE_DENY,
                RESPONSE_DENY,
            ),
            (
                "bash_not_checked",
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "NOT_CHECKED"},
                    "tool_use_id": "toolu-runtime-bash-not-checked-001",
                },
                RESPONSE_DEFER,
                RESPONSE_HOLD_CURRENT_STATE,
            ),
        )

        for name, raw_input, expected_schema_type, expected_dry_type in cases:
            with self.subTest(name=name):
                serialization, schema_candidate, action_candidate, decision_candidate = (
                    self._schema_chain(raw_input)
                )
                dry_result = run_pretooluse_dry_runtime_entrypoint_candidate(raw_input)

                self.assertEqual(
                    schema_candidate.response_schema_candidate_type,
                    expected_schema_type,
                )
                self.assertEqual(dry_result.resulting_candidate_type, expected_dry_type)
                self.assertEqual(dry_result.source_tool_use_id, raw_input["tool_use_id"])
                self.assertEqual(
                    dry_result.response_schema_candidate_hash,
                    schema_candidate.response_schema_candidate_hash,
                )
                if name == "bash_not_checked":
                    self.assertEqual(
                        action_candidate.candidate_status,
                        HOLD_CURRENT_STATE_CANDIDATE,
                    )
                    self.assertEqual(action_candidate.risk_status, BASH_NOT_CHECKED)
                    self.assertEqual(decision_candidate.decision_candidate, DEFER)
                    self.assertEqual(serialization.source_response_candidate_type, DEFER)
                self._assert_dry_run_result_only_no_runtime(dry_result)

    def test_malformed_and_runtime_flagged_dry_inputs_hold_without_source_ids(self):
        cases = (
            (
                "malformed",
                {
                    "tool_name": "Read",
                    "tool_input": "PHASE11C_RUNTIME_RAW_SECRET",
                    "tool_use_id": "toolu-runtime-malformed-001",
                },
            ),
            (
                "runtime_flag",
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": "docs/phase11c-runtime-flag.md"},
                    "tool_use_id": "toolu-runtime-flag-001",
                    "metadata": {"runtime_enabled": True},
                },
            ),
        )

        for name, raw_input in cases:
            with self.subTest(name=name):
                dry_result = run_pretooluse_dry_runtime_entrypoint_candidate(raw_input)
                record_text = json.dumps(dry_result.to_record(), sort_keys=True)

                self.assertIsNone(dry_result.source_tool_use_id)
                self.assertEqual(
                    dry_result.resulting_candidate_type,
                    RESPONSE_HOLD_CURRENT_STATE,
                )
                self.assertNotIn("PHASE11C_RUNTIME_RAW_SECRET", record_text)
                self._assert_dry_run_result_only_no_runtime(dry_result)

    def test_raw_secret_path_content_and_command_fragments_are_not_in_final_records(self):
        probes = (
            (
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/PHASE11C_RUNTIME_SECRET_PATH.md",
                        "content": "token=PHASE11C_RUNTIME_SECRET_CONTENT",
                    },
                    "tool_use_id": "toolu-runtime-redaction-write-001",
                },
                (
                    "PHASE11C_RUNTIME_SECRET_PATH",
                    "PHASE11C_RUNTIME_SECRET_CONTENT",
                    "token=PHASE11C_RUNTIME_SECRET_CONTENT",
                ),
            ),
            (
                {
                    "tool_name": "Bash",
                    "tool_input": {
                        "command": "printf PHASE11C_RUNTIME_SECRET_COMMAND"
                    },
                    "tool_use_id": "toolu-runtime-redaction-bash-001",
                },
                ("PHASE11C_RUNTIME_SECRET_COMMAND",),
            ),
        )

        for raw_input, raw_fragments in probes:
            with self.subTest(tool=raw_input["tool_name"]):
                _, schema_candidate, _, _ = self._schema_chain(raw_input)
                dry_result = run_pretooluse_dry_runtime_entrypoint_candidate(raw_input)
                final_record_text = json.dumps(
                    {
                        "schema": schema_candidate.to_record(),
                        "dry_result": dry_result.to_record(),
                    },
                    sort_keys=True,
                )

                self.assertNotIn("tool_input", final_record_text)
                for raw_fragment in raw_fragments:
                    with self.subTest(raw_fragment=raw_fragment):
                        self.assertNotIn(raw_fragment, final_record_text)
                self.assertIn("redacted_phase11c_pretooluse_candidate", final_record_text)
                self._assert_schema_candidate_only_no_authority(schema_candidate)
                self._assert_dry_run_result_only_no_runtime(dry_result)

    def test_schema_and_dry_result_hashes_are_deterministic_and_immutable(self):
        _, schema_candidate, _, _ = self._schema_chain(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c-runtime-hash.md"},
                "tool_use_id": "toolu-runtime-hash-001",
            }
        )
        dry_result = run_pretooluse_dry_runtime_entrypoint_candidate(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "docs/phase11c-runtime-hash.md"},
                "tool_use_id": "toolu-runtime-hash-001",
            }
        )

        self.assertEqual(
            schema_candidate.response_schema_candidate_hash,
            claude_code_pretooluse_response_schema_candidate_digest(schema_candidate),
        )
        self.assertTrue(
            schema_candidate.response_schema_candidate_id.endswith(
                schema_candidate.response_schema_candidate_hash
            )
        )
        self.assertIsInstance(
            schema_candidate.hook_specific_output_candidate,
            MappingProxyType,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            schema_candidate.source_serialization_hash = None
        with self.assertRaises(TypeError):
            schema_candidate.hook_specific_output_candidate["decision"] = "allow"

        self.assertEqual(
            dry_result.dry_run_result_hash,
            hook_runtime_dry_run_result_candidate_digest(dry_result),
        )
        self.assertTrue(
            dry_result.dry_run_result_id.endswith(dry_result.dry_run_result_hash)
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            dry_result.execution_performed = True

    def test_contract_evidence_records_runtime_readiness_boundaries(self):
        schema_evidence = (
            build_claude_code_pretooluse_response_schema_candidate_contract_evidence()
        )
        dry_evidence = build_hook_runtime_entrypoint_dry_candidate_contract_evidence()

        self.assertEqual(
            schema_evidence["completion_label"],
            PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        )
        self.assertEqual(schema_evidence["docs_checked_date"], DOCS_CHECKED_DATE)
        self.assertEqual(schema_evidence["docs_source_type"], DOCS_SOURCE_TYPE)
        self.assertEqual(schema_evidence["docs_source_status"], DOCS_SOURCE_STATUS)
        self.assertEqual(
            schema_evidence["response_transport_candidate"],
            RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        )
        self.assertEqual(
            schema_evidence["response_schema_status"],
            RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME,
        )
        self.assertFalse(schema_evidence["deprecated_top_level_decision_reason_used"])
        self.assertEqual(
            schema_evidence["hold_current_state_serialization_policy"],
            RESPONSE_DENY,
        )
        self.assertFalse(
            schema_evidence["unknown_malformed_serialization_copies_source_ids"]
        )

        self.assertEqual(
            dry_evidence["contract_version"],
            PHASE11C_DRY_RUNTIME_ENTRYPOINT_CANDIDATE_VERSION,
        )
        self.assertEqual(dry_evidence["would_emit_stdout"], False)
        self.assertIsNone(dry_evidence["stdout_payload"])
        self.assertIsNone(dry_evidence["stderr_payload"])
        self.assertEqual(dry_evidence["install_performed"], False)
        self.assertEqual(dry_evidence["execution_performed"], False)
        self.assertEqual(dry_evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            dry_evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )

        for evidence in (schema_evidence, dry_evidence):
            for field in (
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
                "patch_application_implemented",
                "public_release_performed",
                "universal_prompt_injection_prevention_claimed",
                "sandbox_process_isolation_claimed",
                "bash_safe_claimed",
            ):
                with self.subTest(field=field):
                    self.assertFalse(evidence[field])

    def test_dry_entrypoint_candidate_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            dry_result = run_pretooluse_dry_runtime_entrypoint_candidate(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "docs/phase11c-runtime-no-mutation.md",
                        "content": "candidate only",
                    },
                    "tool_use_id": "toolu-runtime-no-mutation-001",
                }
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse(dry_result.filesystem_mutation_by_dry_entrypoint)
            self.assertFalse(dry_result.dry_runtime_entrypoint_mutates_filesystem)
            self._assert_dry_run_result_only_no_runtime(dry_result)

    def test_new_source_has_no_runtime_install_provider_store_process_or_cli_surface(self):
        sources = (
            inspect.getsource(claude_code_pretooluse_response_schema_candidate),
            inspect.getsource(hook_runtime_entrypoint_dry_candidate),
        )
        forbidden_fragments = (
            "import os",
            "os.environ",
            "import sys",
            "sys.stdin",
            "sys.stdout",
            "sys.stderr",
            "sys.exit",
            "print(",
            "builtins.input",
            "import subprocess",
            "subprocess.",
            "Popen(",
            "run(",
            "requests",
            "socket",
            "urllib",
            "http.client",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "__import__(",
            "importlib",
            "src.state.store",
            "from src.state import store",
            "store.",
        )

        for source in sources:
            for forbidden_fragment in forbidden_fragments:
                with self.subTest(forbidden_fragment=forbidden_fragment):
                    self.assertNotIn(forbidden_fragment, source)

    def test_docs_record_completion_labels_template_and_non_goals(self):
        runtime_doc = RUNTIME_DOC_PATH.read_text(encoding="utf-8")
        baseline_doc = BASELINE_DOC_PATH.read_text(encoding="utf-8")

        runtime_markers = (
            "PHASE11C_RUNTIME_READINESS_COMPLETION_BUNDLE_COMPLETE_NOT_INSTALLED_NOT_LIVE_RUNTIME",
            "docs checked date: 2026-07-07",
            "source type: Claude Code Hooks reference",
            "schema status: current_docs_checked_but_runtime_not_executed",
            "hookSpecificOutput",
            'hookEventName = "PreToolUse"',
            'permissionDecision = "allow" | "deny" | "ask" | "defer"',
            "permissionDecisionReason = redacted reason string",
            "Deprecated top-level `decision` / `reason` fields are not used",
            "response_transport_candidate = data_only_not_stdout",
            "response_schema_status = claude_code_pretooluse_candidate_not_runtime",
            "allow serialization candidate -> permissionDecision allow candidate only",
            "deny serialization candidate -> permissionDecision deny candidate only",
            "ask serialization candidate -> permissionDecision ask candidate only",
            "defer serialization candidate -> permissionDecision defer candidate only",
            "hold_current_state serialization candidate -> permissionDecision deny candidate by default",
            "malformed/unknown/mismatched serialization candidate -> hold_current_state candidate and no source ids copied",
            "allow candidate != execution",
            "allow candidate != write authority",
            "allow candidate != installed hook output",
            "allow candidate must not be emitted to stdout in this PR",
            "NOT_INSTALLED",
            "DO_NOT_COPY_WITHOUT_USER_APPROVAL",
            "EXAMPLE_ONLY",
            "/NON_EXISTING/PATH/PHASE11C_RUNTIME_READINESS_PLACEHOLDER_NOT_INSTALLED",
            "runtime readiness candidate != real Claude Code hook response",
            "response schema candidate != stdout/stderr emission",
            "dry runtime entrypoint candidate != hook runtime",
            "dry runtime entrypoint candidate != installed hook",
            "dry runtime entrypoint candidate != execution",
            "dry runtime entrypoint candidate != action execution engine",
            "dry runtime entrypoint candidate != write authority",
            "dry runtime entrypoint candidate != store write",
            "dry runtime entrypoint candidate does not mutate filesystem",
            "deny candidate != actual denial response unless emitted by later runtime phase",
            "ask candidate != user prompt implementation",
            "defer candidate != actual subprocess defer behavior",
            "hold candidate preserves safe default",
            "safe_default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "reported_only != judgment basis",
            "NOT_CHECKED != PASS",
            "final Claude Code hook response schema claim",
            "universal prompt-injection prevention claim",
            "sandbox/process isolation claim",
            "Bash-safe claim",
        )
        for marker in runtime_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, runtime_doc)

        baseline_markers = (
            "PHASE11C_COMPLETION_BASELINE_NOT_INSTALLED_NOT_LIVE_RUNTIME",
            "Phase 11-C = COMPLETE_AS_CLAUDE_CODE_PRETOOLUSE_RUNTIME_READINESS_BUNDLE_NOT_INSTALLED_NOT_LIVE_RUNTIME",
            "11-C runtime-readiness response schema candidate = complete as candidate",
            "11-C dry entrypoint candidate = complete as candidate",
            "main merge = NOT_PERFORMED",
            "Read normal path -> allow candidate chain",
            "Write normal path -> ask candidate chain",
            "Read .env or protected path -> deny candidate chain",
            "Bash dangerous command -> deny candidate chain",
            "Bash NOT_CHECKED/unknown -> hold_current_state candidate chain",
            "malformed input -> hold_current_state candidate chain",
            "source hash mismatch at 11-C-7 -> hold_current_state candidate chain",
            "runtime flag true anywhere -> hold_current_state candidate chain",
            "raw secret/path/content/command probe -> not present in final candidate records",
            "final dry-run result -> no stdout/stderr/install/runtime/write/store/provider/process flags",
            ".claude/settings.json mutation = NOT_PERFORMED",
            ".claude/settings.local.json mutation = NOT_PERFORMED",
            "store.py change = NOT_PERFORMED",
            "src/state/store.py change = NOT_PERFORMED",
        )
        for marker in baseline_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, baseline_doc)

    def _schema_chain(self, raw_input):
        serialization, action_candidate, decision_candidate, _ = (
            self._serialization_chain(raw_input)
        )
        schema_candidate = build_claude_code_pretooluse_response_schema_candidate(
            serialization
        )
        return serialization, schema_candidate, action_candidate, decision_candidate

    def _serialization_chain(self, raw_input):
        result = validate_claude_code_pretooluse_input(raw_input)
        self.assertTrue(result.valid, result.reasons)
        action_candidate = map_pretooluse_input_to_structured_action_candidate(
            result.hook_input
        )
        decision_candidate = adapt_structured_action_candidate_to_hook_decision_candidate(
            action_candidate
        )
        binding = build_hook_evidence_binding(
            hook_input=result.hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        )
        verification = verify_hook_evidence_binding_candidate(binding)
        envelope = build_hook_response_envelope_candidate(
            verification_result=verification,
            binding_record=binding,
            decision_candidate=decision_candidate,
        )
        serialization = build_hook_response_serialization_candidate(
            envelope_candidate=envelope
        )
        return serialization, action_candidate, decision_candidate, envelope

    def _assert_schema_hashes(self, schema_candidate):
        self.assertEqual(
            schema_candidate.response_schema_candidate_hash,
            claude_code_pretooluse_response_schema_candidate_digest(schema_candidate),
        )
        self.assertTrue(
            schema_candidate.response_schema_candidate_id.endswith(
                schema_candidate.response_schema_candidate_hash
            )
        )

    def _rebind_serialization_record(self, record):
        serialization_hash = hook_response_serialization_candidate_digest(record)
        record["serialization_hash"] = serialization_hash
        record["serialization_id"] = (
            f"phase11c-7-hook-response-serialization:{serialization_hash}"
        )

    def _assert_schema_candidate_only_no_authority(self, schema_candidate):
        self.assertEqual(
            schema_candidate.completion_label,
            PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        )
        self.assertEqual(schema_candidate.safe_default, SAFE_DEFAULT)
        self.assertEqual(
            schema_candidate.live_executor_authority,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertEqual(schema_candidate.trust_boundary, UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        self.assertEqual(
            schema_candidate.claude_code_hook_event_name,
            CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
        )
        self.assertEqual(
            schema_candidate.response_transport_candidate,
            RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        )
        self.assertEqual(
            schema_candidate.response_schema_status,
            RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME,
        )
        self.assertEqual(schema_candidate.docs_checked_date, DOCS_CHECKED_DATE)
        self.assertEqual(schema_candidate.docs_source_status, DOCS_SOURCE_STATUS)
        for field in (
            "response_schema_candidate_is_real_claude_code_hook_response",
            "response_schema_candidate_is_stdout_stderr_emission",
            "response_schema_candidate_is_hook_runtime",
            "response_schema_candidate_is_hook_command",
            "response_schema_candidate_is_execution",
            "response_schema_candidate_is_action_execution_engine",
            "response_schema_candidate_is_write_authority",
            "response_schema_candidate_is_store_write",
            "response_schema_candidate_mutates_filesystem",
            "allow_candidate_is_execution",
            "allow_candidate_is_write_authority",
            "allow_candidate_is_installed_hook_output",
            "deny_candidate_is_actual_denial_response",
            "ask_candidate_is_user_prompt_implementation",
            "defer_candidate_is_actual_subprocess_defer_behavior",
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
            "filesystem_mutation_by_response_schema_candidate",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(getattr(schema_candidate, field))
        self.assertTrue(schema_candidate.hold_candidate_preserves_safe_default)

    def _assert_dry_run_result_only_no_runtime(self, dry_result):
        self.assertEqual(
            dry_result.completion_label,
            PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        )
        self.assertEqual(dry_result.safe_default, SAFE_DEFAULT)
        self.assertEqual(
            dry_result.live_executor_authority,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertFalse(dry_result.would_emit_stdout)
        self.assertIsNone(dry_result.stdout_payload)
        self.assertIsNone(dry_result.stderr_payload)
        self.assertFalse(dry_result.install_performed)
        self.assertFalse(dry_result.execution_performed)
        self.assertEqual(
            dry_result.dry_run_result_hash,
            hook_runtime_dry_run_result_candidate_digest(dry_result),
        )
        for field in (
            "dry_runtime_entrypoint_candidate_is_hook_runtime",
            "dry_runtime_entrypoint_candidate_is_installed_hook",
            "dry_runtime_entrypoint_candidate_is_execution",
            "dry_runtime_entrypoint_candidate_is_action_execution_engine",
            "dry_runtime_entrypoint_candidate_is_write_authority",
            "dry_runtime_entrypoint_candidate_is_store_write",
            "dry_runtime_entrypoint_mutates_filesystem",
            "dry_runtime_entrypoint_reads_stdin",
            "dry_runtime_entrypoint_writes_stdout",
            "dry_runtime_entrypoint_writes_stderr",
            "dry_runtime_entrypoint_calls_exit",
            "dry_runtime_entrypoint_executes_claude_code",
            "dry_runtime_entrypoint_executes_tools",
            "dry_runtime_entrypoint_calls_provider_model_network",
            "dry_runtime_entrypoint_loads_api_keys_env_secrets",
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
            "filesystem_mutation_by_dry_entrypoint",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(getattr(dry_result, field))
