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
    INVALID_TOOL_INPUT,
    NORMAL_REPO_PATH,
    PHASE11C_2_COMPLETE_LABEL,
    PROTECTED_PATH,
    READ_REPO,
    RUN_COMMAND,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    WRITE_FILE,
    build_tool_call_mapping_contract_evidence,
    extract_apply_patch_targets,
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
            ("Write", {"file_path": ".github/workflows/ci.yml", "content": "data"}, WRITE_FILE),
            ("Write", {"file_path": "Dockerfile", "content": "data"}, WRITE_FILE),
            (
                "Edit",
                {
                    "file_path": "pyproject.toml",
                    "old_string": "old",
                    "new_string": "new",
                },
                EDIT_FILE,
            ),
            ("Write", {"file_path": "deploy/prod.yml", "content": "data"}, WRITE_FILE),
            (
                "Edit",
                {
                    "file_path": "src/law/policy.py",
                    "old_string": "old",
                    "new_string": "new",
                },
                EDIT_FILE,
            ),
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
            "git reset --hard",
            "git clean -fd",
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

    def test_apply_patch_normal_targets_map_to_write_file_candidate(self):
        command = (
            "*** Begin Patch\n"
            "*** Update File: README.md\n"
            "@@\n"
            "+new line\n"
            "*** Update File: src/app.py\n"
            "@@\n"
            "+print('x')\n"
            "*** End Patch"
        )

        candidate = self._candidate(
            "apply_patch",
            {"command": command},
            "toolu-apply-patch-normal",
        )

        self.assertEqual(candidate.candidate_action_type, WRITE_FILE)
        self.assertEqual(candidate.candidate_status, STRUCTURED_ACTION_CANDIDATE)
        self.assertEqual(candidate.risk_status, NORMAL_REPO_PATH)
        self.assertEqual(candidate.target_scope["paths"], ("README.md", "src/app.py"))
        self.assertEqual(candidate.payload["target_paths"], ("README.md", "src/app.py"))
        self.assertIn(
            "apply_patch_targets_extracted_from_structural_directives",
            candidate.reasons,
        )
        self._assert_candidate_only_no_authority(candidate)

    def test_apply_patch_protected_and_out_of_scope_targets_map_to_deny_candidate(self):
        cases = (
            (
                "add_env",
                "*** Begin Patch\n*** Add File: .env\n+API_KEY=x\n*** End Patch",
                ".env",
            ),
            (
                "workflow",
                "*** Begin Patch\n*** Add File: .github/workflows/x.yml\n+name: x\n*** End Patch",
                ".github/workflows/x.yml",
            ),
            (
                "delete_env",
                "*** Begin Patch\n*** Delete File: .env\n*** End Patch",
                ".env",
            ),
            (
                "absolute",
                "*** Begin Patch\n*** Update File: /etc/passwd\n@@\n+x\n*** End Patch",
                "/etc/passwd",
            ),
            (
                "mixed",
                "*** Begin Patch\n*** Update File: README.md\n@@\n+x\n*** Add File: .env\n+K=v\n*** End Patch",
                ".env",
            ),
        )

        for label, command, expected_path in cases:
            with self.subTest(label=label):
                candidate = self._candidate(
                    "apply_patch",
                    {"command": command},
                    f"toolu-apply-patch-{label}",
                )

                self.assertEqual(candidate.candidate_action_type, WRITE_FILE)
                self.assertEqual(candidate.candidate_status, DENY_CANDIDATE)
                self.assertEqual(candidate.declared_risk, HIGH)
                self.assertEqual(candidate.risk_status, PROTECTED_PATH)
                self.assertIn(expected_path, candidate.target_scope["paths"])
                self._assert_candidate_only_no_authority(candidate)

    def test_apply_patch_malformed_command_maps_to_deny_candidate(self):
        cases = (
            {"command": "*** Begin Patch\n*** Update File: README.md\n@@\n+x"},
            {"command": "*** Begin Patch\nREADME.md\n*** End Patch"},
            {"command": ""},
            {},
        )

        for tool_input in cases:
            with self.subTest(tool_input=tool_input):
                candidate = self._candidate(
                    "apply_patch",
                    tool_input,
                    "toolu-apply-patch-invalid",
                )

                self.assertEqual(candidate.candidate_action_type, WRITE_FILE)
                self.assertEqual(candidate.candidate_status, DENY_CANDIDATE)
                self.assertEqual(candidate.risk_status, INVALID_TOOL_INPUT)
                self.assertIn(
                    "apply_patch_unparseable_or_invalid_maps_to_deny_candidate",
                    candidate.reasons,
                )
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
                "apply_patch": WRITE_FILE,
            },
        )
        self.assertEqual(
            evidence["protected_path_policy_source"],
            "src.classify.is_protected_path",
        )
        self.assertEqual(evidence["state_dir_boundary_source"], "src.contracts.STATE_DIR")
        self.assertTrue(evidence["absolute_or_traversal_path_deny_candidate"])
        self.assertTrue(evidence["apply_patch_tool_supported"])
        self.assertTrue(evidence["codex_apply_patch_tool_call_supported"])
        self.assertTrue(evidence["apply_patch_maps_to_write_file_candidate"])
        self.assertTrue(evidence["apply_patch_target_parsing_is_structural_directive_parse"])
        self.assertTrue(evidence["apply_patch_unparseable_maps_to_deny_candidate"])
        self.assertTrue(evidence["git_reset_hard_is_dangerous"])
        self.assertTrue(evidence["git_clean_force_delete_is_dangerous"])
        self.assertNotIn("protected_path_segments", evidence)
        self.assertNotIn("protected_path_filenames", evidence)
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
            "src.classify.is_protected_path",
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
            ".env.* target -> DENY_CANDIDATE",
            ".aeg state dir target -> DENY_CANDIDATE",
            ".github/workflows/ci.yml -> DENY_CANDIDATE",
            "Dockerfile -> DENY_CANDIDATE",
            "pyproject.toml -> DENY_CANDIDATE",
            "deploy/prod.yml -> DENY_CANDIDATE",
            "src/law/policy.py -> DENY_CANDIDATE",
            "rm -rf",
            "git reset --hard",
            "git clean -fd",
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


class BashTargetExtractionTests(unittest.TestCase):
    def _extract(self, command):
        from src.evidence.claude_code_tool_call_mapping import (
            extract_bash_write_delete_targets,
        )

        return extract_bash_write_delete_targets(command)

    def test_redirect_tee_cp_mv_rm_dd_truncate_targets_extracted(self):
        cases = {
            'echo "K=v" > .env': [".env"],
            "echo x >> .env": [".env"],
            "echo x | tee .env": [".env"],
            "cp src/a.py .env": [".env"],
            "mv src/a.py .env": [".env"],
            "rm .env": [".env"],
            "dd of=.env if=/dev/zero": [".env"],
            "truncate -s 0 .env": [".env"],
            "echo x > .github/workflows/ci.yml": [".github/workflows/ci.yml"],
            "echo hi > out.txt && rm .env": ["out.txt", ".env"],
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertFalse(extraction.parse_ambiguous)
                self.assertEqual(list(extraction.write_delete_targets), expected)

    def test_shlex_defeats_quote_splitting_obfuscation(self):
        extraction = self._extract('echo x > .en"v"')
        self.assertFalse(extraction.parse_ambiguous)
        self.assertEqual(list(extraction.write_delete_targets), [".env"])

    def test_fd_duplication_not_treated_as_target(self):
        extraction = self._extract("echo x 2>&1 > .env")
        self.assertEqual(list(extraction.write_delete_targets), [".env"])

    def test_substitution_and_nested_shell_are_ambiguous(self):
        for command in (
            "E=.env; echo x > $E",
            "echo x > $(echo .env)",
            "echo x > `echo .env`",
            "bash -c 'echo x > .env'",
            "sh -c 'rm .env'",
            "echo x | xargs rm",
            "find . -name '*.env' -delete",
        ):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertTrue(extraction.parse_ambiguous)
                self.assertEqual(extraction.write_delete_targets, tuple())

    def test_safe_commands_have_no_targets(self):
        for command in ("pwd", "ls -la", "git status", "cat README.md", "grep foo x.txt"):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertFalse(extraction.parse_ambiguous)
                self.assertEqual(extraction.write_delete_targets, tuple())


class ApplyPatchTargetExtractionTests(unittest.TestCase):
    def test_add_update_delete_and_move_targets_are_extracted_from_directives(self):
        command = (
            "*** Begin Patch\n"
            "*** Add File: docs/new.md\n"
            "+hello\n"
            "*** Update File: README.md\n"
            "@@\n"
            "+new\n"
            "*** Delete File: old.txt\n"
            "*** Update File: src/old.py\n"
            "*** Move to: src/new.py\n"
            "@@\n"
            "-old\n"
            "+new\n"
            "*** End Patch"
        )

        extraction = extract_apply_patch_targets(command)

        self.assertFalse(extraction.parse_ambiguous)
        self.assertEqual(
            extraction.target_paths,
            ("docs/new.md", "README.md", "old.txt", "src/old.py", "src/new.py"),
        )
        self.assertEqual(
            extraction.target_operations,
            (
                ("write", "docs/new.md"),
                ("write", "README.md"),
                ("delete", "old.txt"),
                ("delete", "src/old.py"),
                ("write", "src/new.py"),
            ),
        )

    def test_content_mentions_do_not_create_targets(self):
        command = (
            "*** Begin Patch\n"
            "*** Update File: README.md\n"
            "@@\n"
            "+document .env and .github/workflows/x.yml examples\n"
            "*** End Patch"
        )

        extraction = extract_apply_patch_targets(command)

        self.assertFalse(extraction.parse_ambiguous)
        self.assertEqual(extraction.target_paths, ("README.md",))

    def test_quoted_directive_paths_are_normalized(self):
        command = (
            "*** Begin Patch\n"
            "*** Add File: \".env\"\n"
            "+API_KEY=x\n"
            "*** Update File: 'README.md'\n"
            "@@\n"
            "+x\n"
            "*** End Patch"
        )

        extraction = extract_apply_patch_targets(command)

        self.assertFalse(extraction.parse_ambiguous)
        self.assertEqual(extraction.target_paths, (".env", "README.md"))
        self.assertEqual(
            extraction.target_operations,
            (
                ("write", ".env"),
                ("write", "README.md"),
            ),
        )

    def test_ambiguous_quoted_directive_paths_fail_closed(self):
        cases = (
            "*** Begin Patch\n*** Add File: \".env\n+API_KEY=x\n*** End Patch",
            "*** Begin Patch\n*** Add File: READ\"ME.md\n+x\n*** End Patch",
            "*** Begin Patch\n*** Add File: \"\"\n+x\n*** End Patch",
        )

        for command in cases:
            with self.subTest(command=command):
                extraction = extract_apply_patch_targets(command)
                self.assertTrue(extraction.parse_ambiguous)
                self.assertEqual(extraction.target_paths, tuple())

    def test_malformed_apply_patch_is_ambiguous(self):
        cases = (
            "*** Begin Patch\n*** Update File: README.md\n@@\n+x",
            "*** Begin Patch\n*** Move to: x\n*** End Patch",
            "*** Begin Patch\n*** Add File: x\nnot-added-line\n*** End Patch",
            "*** Begin Patch\n*** Delete File: x\n-body\n*** End Patch",
            "*** Begin Patch\n*** End Patch",
        )

        for command in cases:
            with self.subTest(command=command):
                extraction = extract_apply_patch_targets(command)
                self.assertTrue(extraction.parse_ambiguous)
                self.assertEqual(extraction.target_paths, tuple())


if __name__ == "__main__":
    unittest.main()
