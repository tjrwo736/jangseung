import dataclasses
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import hook_evidence_verification_gate
from src.evidence.claude_code_pretooluse_input_contract import (
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    map_pretooluse_input_to_structured_action_candidate,
)
from src.evidence.hook_decision_adapter import (
    ASK,
    HOOK_DECISION_CANDIDATES,
    adapt_structured_action_candidate_to_hook_decision_candidate,
)
from src.evidence.hook_evidence_binding import (
    HOOK_EVIDENCE_BINDING_REJECTED,
    HOOK_EVIDENCE_BOUND,
    PHASE11C_4_COMPLETE_LABEL,
    PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
    TOOL_INPUT_HASH_ALGORITHM,
    build_hook_evidence_binding,
)
from src.evidence.hook_evidence_verification_gate import (
    BINDING_AUTHORITY_FLAG_REJECTED,
    BINDING_DECISION_CANDIDATE_MISMATCH_REJECTED,
    BINDING_HASH_MISMATCH_REJECTED,
    BINDING_ID_MISMATCH_REJECTED,
    BINDING_NOT_CHECKED_PROMOTION_REJECTED,
    BINDING_PROVENANCE_MISMATCH_REJECTED,
    BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED,
    BINDING_REPORTED_ONLY_PROMOTION_REJECTED,
    BINDING_RUNTIME_FLAG_REJECTED,
    BINDING_SECRET_FRAGMENT_RETAINED_REJECTED,
    BINDING_STORE_WRITE_FLAG_REJECTED,
    HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
    PHASE11C_5_COMPLETE_LABEL,
    REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    build_hook_evidence_verification_gate_contract_evidence,
    hook_evidence_binding_candidate_digest_from_mapping,
    verify_hook_evidence_binding_candidate,
)


DOC_PATH = Path("docs/phase11c_5_hook_evidence_verification_gate_v0.md")


class Phase11C5HookEvidenceVerificationGateTests(unittest.TestCase):
    def test_bound_binding_verifies_as_inert_verified_candidate(self):
        binding = self._binding(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c5-example.md",
                    "content": "token=PHASE11C5_SUPER_SECRET_VALUE",
                },
                "tool_use_id": "toolu-verify-bound-001",
            }
        )

        result = verify_hook_evidence_binding_candidate(
            binding,
            known_secret_fragments=(
                "PHASE11C5_SUPER_SECRET_VALUE",
                "token=PHASE11C5_SUPER_SECRET_VALUE",
                "docs/phase11c5-example.md",
            ),
        )

        self.assertEqual(binding.binding_status, HOOK_EVIDENCE_BOUND)
        self.assertEqual(
            result.verification_output,
            VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        )
        self.assertEqual(result.completion_label, PHASE11C_5_COMPLETE_LABEL)
        self.assertTrue(result.verification_passed)
        self.assertTrue(result.binding_verified)
        self.assertFalse(result.binding_rejected)
        self.assertEqual(result.rejection_codes, ())
        self.assertEqual(result.binding_hash, result.recomputed_binding_hash)
        self.assertEqual(
            result.binding_hash,
            hook_evidence_binding_candidate_digest_from_mapping(binding.to_record()),
        )
        self.assertEqual(result.safe_default, SAFE_DEFAULT)
        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(result.trust_boundary, UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        self.assertIn("binding_hash replay is deterministic", result.checks)
        self.assertIn("binding_id matched binding_hash", result.checks)
        self.assertIn("raw full tool_input is not retained by default", result.checks)
        self.assertIn(
            "known secret probe fragments absent from serialized record",
            result.checks,
        )
        self._assert_verification_only_no_authority(result)

    def test_rejected_binding_candidate_verifies_as_rejected_not_hook_response(self):
        hook_input, action_candidate, _ = self._input_action_decision(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/rejected.md",
                    "content": "rejected",
                },
                "tool_use_id": "toolu-reject-consistent-001",
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

        result = verify_hook_evidence_binding_candidate(binding.to_record())

        self.assertEqual(binding.binding_status, HOOK_EVIDENCE_BINDING_REJECTED)
        self.assertIn(
            "action_candidate_write_authority_granted_must_remain_false",
            binding.binding_reasons,
        )
        self.assertEqual(
            result.verification_output,
            REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        )
        self.assertTrue(result.verification_passed)
        self.assertFalse(result.binding_verified)
        self.assertTrue(result.binding_rejected)
        self.assertFalse(result.rejected_candidate_is_real_claude_code_hook_response)
        self._assert_verification_only_no_authority(result)

    def test_hash_and_binding_id_mismatch_hold_current_state(self):
        cases = (
            (
                "binding_hash",
                lambda record: record.update({"binding_hash": "0" * 64}),
                BINDING_HASH_MISMATCH_REJECTED,
            ),
            (
                "binding_id",
                lambda record: record.update(
                    {"binding_id": "phase11c-4-hook-evidence:" + ("f" * 64)}
                ),
                BINDING_ID_MISMATCH_REJECTED,
            ),
        )

        for name, mutate, expected_code in cases:
            with self.subTest(name=name):
                record = self._binding_record()
                mutate(record)

                result = verify_hook_evidence_binding_candidate(record)

                self.assertEqual(
                    result.verification_output,
                    HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
                )
                self.assertFalse(result.verification_passed)
                self.assertIn(expected_code, result.rejection_codes)
                self._assert_verification_only_no_authority(result)

    def test_rebound_tamper_still_holds_for_provenance_decision_and_flags(self):
        cases = (
            (
                "decision_candidate",
                lambda record: record.update({"decision_candidate": "respond"}),
                BINDING_DECISION_CANDIDATE_MISMATCH_REJECTED,
            ),
            (
                "provenance_action_id",
                lambda record: record["provenance"]["hook_decision_candidate"].update(
                    {"action_id": "pretooluse:tampered"}
                ),
                BINDING_PROVENANCE_MISMATCH_REJECTED,
            ),
            (
                "write_authority_granted",
                lambda record: record.update({"write_authority_granted": True}),
                BINDING_AUTHORITY_FLAG_REJECTED,
            ),
            (
                "real_hook_response_emitted",
                lambda record: record.update({"real_hook_response_emitted": True}),
                BINDING_RUNTIME_FLAG_REJECTED,
            ),
            (
                "state_store_module_changed",
                lambda record: record.update({"state_store_module_changed": True}),
                BINDING_STORE_WRITE_FLAG_REJECTED,
            ),
            (
                "reported_only_is_judgment_basis",
                lambda record: record.update({"reported_only_is_judgment_basis": True}),
                BINDING_REPORTED_ONLY_PROMOTION_REJECTED,
            ),
            (
                "not_checked_is_pass",
                lambda record: record.update({"not_checked_is_pass": True}),
                BINDING_NOT_CHECKED_PROMOTION_REJECTED,
            ),
        )

        for name, mutate, expected_code in cases:
            with self.subTest(name=name):
                record = self._binding_record()
                mutate(record)
                self._rebind_record(record)

                result = verify_hook_evidence_binding_candidate(record)

                self.assertEqual(
                    result.verification_output,
                    HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
                )
                self.assertFalse(result.verification_passed)
                self.assertEqual(result.binding_hash, result.recomputed_binding_hash)
                self.assertIn(expected_code, result.rejection_codes)
                self._assert_verification_only_no_authority(result)

    def test_raw_retention_and_secret_fragment_probe_hold_even_when_rebound(self):
        record = self._binding_record()
        record["tool_input_raw_stored"] = True
        record["tool_input"] = {"content": "PHASE11C5_RAW_SECRET_VALUE"}
        record["tool_input_redacted_metadata"]["raw_values_stored"] = True
        self._rebind_record(record)

        result = verify_hook_evidence_binding_candidate(
            record,
            known_secret_fragments=("PHASE11C5_RAW_SECRET_VALUE",),
        )

        self.assertEqual(
            result.verification_output,
            HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
        )
        self.assertFalse(result.verification_passed)
        self.assertIn(
            BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED,
            result.rejection_codes,
        )
        self.assertIn(
            BINDING_SECRET_FRAGMENT_RETAINED_REJECTED,
            result.rejection_codes,
        )
        self.assertIn("PHASE11C5_RAW_SECRET_VALUE", json.dumps(record, sort_keys=True))
        self._assert_verification_only_no_authority(result)

    def test_contract_evidence_records_gate_boundaries(self):
        evidence = build_hook_evidence_verification_gate_contract_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_5_COMPLETE_LABEL)
        self.assertEqual(
            evidence["input_contract_version"],
            PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
        )
        self.assertEqual(evidence["input_completion_label"], PHASE11C_4_COMPLETE_LABEL)
        self.assertEqual(
            evidence["verification_outputs"],
            (
                VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
                REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
                HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
            ),
        )
        self.assertTrue(evidence["binding_hash_recomputed"])
        self.assertTrue(evidence["binding_id_matches_binding_hash"])
        self.assertEqual(evidence["tool_input_hash_algorithm"], TOOL_INPUT_HASH_ALGORITHM)
        self.assertFalse(evidence["tool_input_raw_stored_required"])
        self.assertFalse(evidence["raw_tool_input_retained_by_default"])
        self.assertFalse(evidence["secret_fragments_retained_for_known_probes"])
        self.assertEqual(evidence["decision_candidates"], HOOK_DECISION_CANDIDATES)
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        self.assertEqual(evidence["trust_boundary"], UNTRUSTED_RAW_EXECUTOR_OUTPUT)
        for field in (
            "reported_only_is_judgment_basis",
            "not_checked_is_pass",
            "verification_output_is_judgment_basis",
            "verification_output_is_execution",
            "verification_output_is_hook_response",
            "verification_output_is_write_authority",
            "verification_output_is_store_write",
            "verification_output_mutates_filesystem",
            "verified_candidate_is_real_claude_code_hook_response",
            "rejected_candidate_is_real_claude_code_hook_response",
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
            "filesystem_mutation_by_verification",
            "patch_application_implemented",
            "public_release_performed",
            "universal_prompt_injection_prevention_claimed",
            "sandbox_process_isolation_claimed",
            "bash_safe_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])

    def test_verification_gate_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = verify_hook_evidence_binding_candidate(self._binding_record())

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(
                result.verification_output,
                VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
            )
            self.assertFalse(result.filesystem_mutation_by_verification)

    def test_verification_source_has_no_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(hook_evidence_verification_gate)
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

    def test_doc_records_required_checks_outputs_and_non_goals(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_5_COMPLETE_LABEL,
            PHASE11C_4_COMPLETE_LABEL,
            "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE",
            "REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE",
            "HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE",
            "binding_hash recomputes deterministically",
            "binding_id matches binding_hash",
            "binding_status is either HOOK_EVIDENCE_BOUND or HOOK_EVIDENCE_BINDING_REJECTED",
            "tool_input_raw_stored = false",
            "tool_input_hash_algorithm = sha256_canonical_json_v0",
            "safe_default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
            "trust_boundary = untrusted_raw_executor_output",
            "source_tool_use_id/action_id provenance is internally consistent",
            "decision_candidate is one of allow/deny/ask/defer",
            "reported_only != judgment basis",
            "NOT_CHECKED != PASS",
            "no authority flags are true",
            "no runtime flags are true",
            "no store-write flags are true",
            "no raw secret fragments appear in serialized record for known probes",
            "raw full tool_input is not retained by default",
            "verification output != judgment basis by itself",
            "verification output != execution",
            "verification output != hook response",
            "verification output != write authority",
            "verification output != store write",
            "verification output does not mutate filesystem",
            "verified evidence binding candidate != real Claude Code hook response",
            "rejected evidence binding candidate != real Claude Code hook response",
            "main merge = NOT_PERFORMED",
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
        hook_input, action_candidate, decision_candidate = self._input_action_decision(
            raw_input
        )
        return build_hook_evidence_binding(
            hook_input=hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        )

    def _binding_record(self):
        return self._binding(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "docs/phase11c5-default.md",
                    "content": "contract only",
                },
                "tool_use_id": "toolu-verify-default-001",
            }
        ).to_record()

    def _input_action_decision(self, raw_input):
        hook_input = self._contract_input(raw_input)
        action_candidate = map_pretooluse_input_to_structured_action_candidate(
            hook_input
        )
        decision_candidate = adapt_structured_action_candidate_to_hook_decision_candidate(
            action_candidate
        )
        return hook_input, action_candidate, decision_candidate

    def _contract_input(self, raw_input):
        result = validate_claude_code_pretooluse_input(raw_input)
        self.assertTrue(result.valid, result.reasons)
        return result.hook_input

    def _rebind_record(self, record):
        digest = hook_evidence_binding_candidate_digest_from_mapping(record)
        record["binding_hash"] = digest
        record["binding_id"] = f"phase11c-4-hook-evidence:{digest}"

    def _assert_verification_only_no_authority(self, result):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.verification_output = ASK
        self.assertFalse(result.verification_output_is_judgment_basis)
        self.assertFalse(result.verification_output_is_execution)
        self.assertFalse(result.verification_output_is_hook_response)
        self.assertFalse(result.verification_output_is_write_authority)
        self.assertFalse(result.verification_output_is_store_write)
        self.assertFalse(result.verification_output_mutates_filesystem)
        self.assertFalse(result.verified_candidate_is_real_claude_code_hook_response)
        self.assertFalse(result.rejected_candidate_is_real_claude_code_hook_response)
        self.assertFalse(result.safe_default_changed)
        self.assertFalse(result.hook_command_implemented)
        self.assertFalse(result.hook_installation_implemented)
        self.assertFalse(result.claude_code_execution_performed)
        self.assertFalse(result.real_hook_response_emitted)
        self.assertFalse(result.codex_implementation_added)
        self.assertFalse(result.provider_model_network_implemented)
        self.assertFalse(result.llm_call_implemented)
        self.assertFalse(result.api_key_env_secret_loading_implemented)
        self.assertFalse(result.network_client_implemented)
        self.assertFalse(result.process_execution_implemented)
        self.assertFalse(result.shell_execution_implemented)
        self.assertFalse(result.action_execution_engine_implemented)
        self.assertFalse(result.tool_runtime_implemented)
        self.assertFalse(result.write_authority_granted)
        self.assertFalse(result.state_store_module_changed)
        self.assertFalse(result.filesystem_mutation_by_verification)
        self.assertFalse(result.patch_application_implemented)
        self.assertFalse(result.public_release_performed)
        self.assertFalse(result.universal_prompt_injection_prevention_claimed)
        self.assertFalse(result.sandbox_process_isolation_claimed)
        self.assertFalse(result.bash_safe_claimed)
        self.assertEqual(result.safe_default, SAFE_DEFAULT)
        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)


if __name__ == "__main__":
    unittest.main()
