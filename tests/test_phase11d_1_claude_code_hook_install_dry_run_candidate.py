"""Tests for Phase 11-D-1 Claude Code hook install dry-run / settings candidate."""

from __future__ import annotations

import inspect
from pathlib import Path
import unittest

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import claude_code_hook_install_dry_run_candidate as dry_run_candidate
from src.evidence.claude_code_hook_install_dry_run_candidate import (
    FORBIDDEN_GLOBAL_SETTINGS_PATH,
    HOOK_COMMAND_ENTRYPOINT_SUBCOMMAND,
    HOOK_EVENT_NAME_PRETOOLUSE,
    HOOK_MATCHER_TARGET_TOOLS,
    INVALID_SETTINGS_CANDIDATE,
    PHASE11D_1_COMPLETE_LABEL,
    SETTINGS_CANDIDATE_PATH_IF_INSTALLED,
    SETTINGS_CANDIDATE_SCOPE_PROJECT_LOCAL,
    VALID_SETTINGS_CANDIDATE,
    build_claude_code_settings_candidate,
    build_hook_install_dry_run_candidate_evidence,
    diagnose_hook_entrypoint_stdin_stdout_wiring,
    validate_claude_code_settings_candidate,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = REPO_ROOT / "docs" / "phase11d_1_claude_code_hook_install_dry_run_settings_candidate_v0.md"

REQUIRED_DOC_MARKERS = (
    PHASE11D_1_COMPLETE_LABEL,
    "settings_json_modified = False",
    "hook_installed = False",
    "claude_code_execution_performed = False",
    "real_hook_response_emitted = False",
    "stdout_stderr_hook_output_written = False",
)


class Phase11D1HookInstallDryRunCandidateTests(unittest.TestCase):
    def test_settings_candidate_is_project_local_not_global(self):
        self.assertEqual(SETTINGS_CANDIDATE_SCOPE_PROJECT_LOCAL, "project_local")
        self.assertEqual(SETTINGS_CANDIDATE_PATH_IF_INSTALLED, ".claude/settings.json")
        self.assertFalse(SETTINGS_CANDIDATE_PATH_IF_INSTALLED.startswith("~"))
        self.assertTrue(FORBIDDEN_GLOBAL_SETTINGS_PATH.startswith("~"))

    def test_settings_candidate_shape_matches_pretooluse_hook_contract(self):
        candidate = build_claude_code_settings_candidate()
        pretooluse_entries = candidate["hooks"][HOOK_EVENT_NAME_PRETOOLUSE]
        self.assertTrue(pretooluse_entries)
        entry = pretooluse_entries[0]
        for tool in HOOK_MATCHER_TARGET_TOOLS:
            with self.subTest(tool=tool):
                self.assertIn(tool, entry["matcher"])
        nested_hook = entry["hooks"][0]
        self.assertEqual(nested_hook["type"], "command")
        self.assertIn("aeg", nested_hook["command"])
        self.assertIn(HOOK_COMMAND_ENTRYPOINT_SUBCOMMAND, nested_hook["command"])

    def test_settings_candidate_validates_as_valid(self):
        candidate = build_claude_code_settings_candidate()
        result = validate_claude_code_settings_candidate(candidate)
        self.assertTrue(result.valid)
        self.assertEqual(result.status, VALID_SETTINGS_CANDIDATE)
        self.assertEqual(result.reasons, tuple())
        self.assertTrue(result.matcher_covers_target_tools)
        self.assertTrue(result.command_references_aeg_entrypoint)

    def test_missing_hooks_section_is_rejected(self):
        result = validate_claude_code_settings_candidate({})
        self.assertFalse(result.valid)
        self.assertEqual(result.status, INVALID_SETTINGS_CANDIDATE)
        self.assertIn("missing_or_invalid_hooks_section", result.reasons)

    def test_matcher_missing_a_target_tool_is_rejected(self):
        candidate = {
            "hooks": {
                HOOK_EVENT_NAME_PRETOOLUSE: [
                    {
                        "matcher": "Write|Edit",
                        "hooks": [{"type": "command", "command": "aeg hook-run"}],
                    }
                ]
            }
        }
        result = validate_claude_code_settings_candidate(candidate)
        self.assertFalse(result.valid)
        self.assertIn("matcher_does_not_cover_write_edit_bash_read", result.reasons)

    def test_non_command_hook_type_is_rejected(self):
        candidate = {
            "hooks": {
                HOOK_EVENT_NAME_PRETOOLUSE: [
                    {
                        "matcher": "Write|Edit|Bash|Read",
                        "hooks": [{"type": "not_command", "command": "aeg hook-run"}],
                    }
                ]
            }
        }
        result = validate_claude_code_settings_candidate(candidate)
        self.assertFalse(result.valid)
        self.assertIn("nested_hook_type_must_be_command", result.reasons)

    def test_command_not_referencing_aeg_entrypoint_is_rejected(self):
        candidate = {
            "hooks": {
                HOOK_EVENT_NAME_PRETOOLUSE: [
                    {
                        "matcher": "Write|Edit|Bash|Read",
                        "hooks": [{"type": "command", "command": "some-other-tool"}],
                    }
                ]
            }
        }
        result = validate_claude_code_settings_candidate(candidate)
        self.assertFalse(result.valid)
        self.assertIn("command_does_not_reference_aeg_entrypoint", result.reasons)

    def test_stdin_stdout_exit_wiring_now_present(self):
        # As of Phase 11-D-2 the aeg hook-run stdin/stdout/exit-code wiring
        # exists; the diagnostic honestly reports it. (Prior to 11-D-2 this
        # asserted the wiring was absent -- that pre-wiring state is now
        # historical.)
        diagnosis = diagnose_hook_entrypoint_stdin_stdout_wiring()
        self.assertTrue(diagnosis.entrypoint_stdin_stdout_exit_wired)
        self.assertIn("src/cli/hook_run.py", diagnosis.files_with_stdin_stdout_exit_io)
        self.assertEqual(
            diagnosis.diagnosis,
            "stdin_stdout_exit_wiring_present_somewhere_in_src",
        )

    def test_hook_run_subcommand_now_exists(self):
        diagnosis = diagnose_hook_entrypoint_stdin_stdout_wiring()
        self.assertTrue(diagnosis.hook_run_subcommand_exists)

    def test_diagnostic_module_source_excludes_itself_from_scan_without_false_positive(self):
        # The diagnostic module's own source contains the token fragments
        # (split to avoid self-matching); confirm the split defeats a naive
        # substring scan so the diagnosis is not corrupted by its own file.
        source = inspect.getsource(dry_run_candidate)
        self.assertNotIn("sys.stdin", source)
        self.assertNotIn("sys.stdout", source)
        self.assertNotIn("sys.exit(", source)

    def test_evidence_records_no_install_no_execution_no_mutation(self):
        evidence = build_hook_install_dry_run_candidate_evidence()
        self.assertEqual(evidence["completion_label"], PHASE11D_1_COMPLETE_LABEL)
        self.assertFalse(evidence["settings_json_modified"])
        self.assertFalse(evidence["settings_json_modified_global"])
        self.assertFalse(evidence["hook_installed"])
        self.assertFalse(evidence["claude_code_execution_performed"])
        self.assertFalse(evidence["real_hook_response_emitted"])
        self.assertFalse(evidence["stdout_stderr_hook_output_written"])
        self.assertFalse(evidence["tool_execution_performed"])
        self.assertFalse(evidence["filesystem_mutation_by_dry_run"])
        self.assertTrue(evidence["dry_run_only"])
        self.assertFalse(evidence["global_settings_path_referenced_by_candidate"])
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertIn("settings_candidate_validation", evidence)
        self.assertTrue(evidence["settings_candidate_validation"]["valid"])
        self.assertIn("entrypoint_stdin_stdout_diagnosis", evidence)
        # The dry-run evidence still records no install/execution/mutation; the
        # stdin/stdout wiring itself now exists as of Phase 11-D-2.
        self.assertTrue(
            evidence["entrypoint_stdin_stdout_diagnosis"]["entrypoint_stdin_stdout_exit_wired"]
        )

    def test_no_real_settings_json_exists_anywhere_in_repo(self):
        matches = list(REPO_ROOT.rglob(".claude"))
        matches = [path for path in matches if ".git" not in path.parts]
        self.assertEqual(matches, [])

    def test_doc_records_required_markers(self):
        self.assertTrue(DOC_PATH.exists())
        doc = DOC_PATH.read_text(encoding="utf-8")
        for marker in REQUIRED_DOC_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_doc_does_not_claim_installed_or_live(self):
        doc_lines = {
            line.strip() for line in DOC_PATH.read_text(encoding="utf-8").splitlines()
        }
        forbidden_positive_claims = (
            "hook_installed = True",
            "claude_code_execution_performed = True",
            "real_hook_response_emitted = True",
            "settings_json_modified = True",
            "entrypoint_stdin_stdout_exit_wired = True",
        )
        for claim in forbidden_positive_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, doc_lines)


if __name__ == "__main__":
    unittest.main()
