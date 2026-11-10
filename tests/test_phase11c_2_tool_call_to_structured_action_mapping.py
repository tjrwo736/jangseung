import dataclasses
import inspect
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from jangseung.contracts import HIGH, LOW, NOT_CHECKED, SAFE_DEFAULT
from jangseung.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from jangseung.evidence import claude_code_tool_call_mapping
from jangseung.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    validate_claude_code_pretooluse_input,
)
from jangseung.evidence.claude_code_tool_call_mapping import (
    BASH_DANGEROUS,
    BASH_NOT_CHECKED,
    DENY_CANDIDATE,
    EDIT_FILE,
    HOLD_CURRENT_STATE,
    HOLD_CURRENT_STATE_CANDIDATE,
    INVALID_TOOL_INPUT,
    NORMAL_REPO_PATH,
    POWERSHELL_NOT_CHECKED,
    POWERSHELL_SAFE_READ_ONLY,
    POWERSHELL_TARGETS_EXTRACTED,
    PROTECTED_PATH,
    READ_REPO,
    RUN_COMMAND,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    WRITE_FILE,
    extract_apply_patch_targets,
    extract_powershell_write_delete_targets,
    map_pretooluse_input_to_structured_action_candidate,
)


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
                    "file_path": "scripts/release_notes.sh",
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

    def test_powershell_tool_maps_to_run_command_candidate(self):
        candidate = self._candidate(
            "PowerShell",
            {"command": "Remove-Item .env"},
            "toolu-powershell-target",
        )

        self.assertEqual(candidate.candidate_action_type, RUN_COMMAND)
        self.assertEqual(candidate.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
        self.assertEqual(candidate.declared_risk, NOT_CHECKED)
        self.assertEqual(candidate.risk_status, POWERSHELL_TARGETS_EXTRACTED)
        self.assertEqual(candidate.payload["target_paths"], (".env",))
        self.assertEqual(candidate.payload["target_operations"], (("delete", ".env"),))
        self.assertEqual(candidate.capability_requirements, ("run_command",))
        self._assert_candidate_only_no_authority(candidate)

    def test_powershell_read_only_maps_to_candidate_without_write_target(self):
        candidate = self._candidate(
            "PowerShell",
            {"command": "Get-Content .env"},
            "toolu-powershell-read",
        )

        self.assertEqual(candidate.candidate_action_type, RUN_COMMAND)
        self.assertEqual(candidate.candidate_status, STRUCTURED_ACTION_CANDIDATE)
        self.assertEqual(candidate.declared_risk, LOW)
        self.assertEqual(candidate.risk_status, POWERSHELL_SAFE_READ_ONLY)
        self.assertEqual(candidate.payload["target_paths"], tuple())
        self._assert_candidate_only_no_authority(candidate)

    def test_powershell_ambiguous_command_holds_current_state(self):
        candidate = self._candidate(
            "PowerShell",
            {"command": '$p = ".env"; Remove-Item $p'},
            "toolu-powershell-ambiguous",
        )

        self.assertEqual(candidate.candidate_action_type, RUN_COMMAND)
        self.assertEqual(candidate.candidate_status, HOLD_CURRENT_STATE_CANDIDATE)
        self.assertEqual(candidate.declared_risk, NOT_CHECKED)
        self.assertEqual(candidate.risk_status, POWERSHELL_NOT_CHECKED)
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
            ("PowerShell", {}, RUN_COMMAND),
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
            "jangseung.state." + "store",
            "from jangseung.state import " + "store",
            "sto" + "re.",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

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
        from jangseung.evidence.claude_code_tool_call_mapping import (
            extract_bash_write_delete_targets,
        )

        return extract_bash_write_delete_targets(command)

    def test_redirect_tee_cp_mv_rm_dd_truncate_targets_extracted(self):
        cases = {
            'echo "K=v" > .env': [".env"],
            "echo x >> .env": [".env"],
            "echo x | tee .env": [".env"],
            "cp src/a.py .env": [".env"],
            "mv src/a.py .env": ["src/a.py", ".env"],
            "mv .env backup": [".env", "backup"],
            "sed -i s/a/b/ .env": [".env"],
            "echo x>.env": [".env"],
            "rm .env;ls": [".env"],
            "ls\nrm .env": [".env"],
            "git rm .env": [".env"],
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
            "echo x | xargs rm",
            "find . -name '*.env' -delete",
        ):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertTrue(extraction.parse_ambiguous)
                self.assertEqual(extraction.write_delete_targets, tuple())

    def test_literal_targets_inside_a_nested_shell_are_still_reported(self):
        for command in ("bash -c 'echo x > .env'", "sh -c 'rm .env'", "echo $X > .env"):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertTrue(extraction.parse_ambiguous)
                self.assertEqual(extraction.write_delete_targets, (".env",))

    def test_safe_commands_have_no_targets(self):
        for command in ("pwd", "ls -la", "git status", "cat README.md", "grep foo x.txt"):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertFalse(extraction.parse_ambiguous)
                self.assertEqual(extraction.write_delete_targets, tuple())


class PowerShellTargetExtractionTests(unittest.TestCase):
    def _extract(self, command):
        return extract_powershell_write_delete_targets(command)

    def test_remove_set_outfile_redirect_copy_move_targets_extracted(self):
        cases = {
            'Remove-Item -Path ".env" -Confirm:$false': [("delete", ".env")],
            'Remove-Item ".env"': [("delete", ".env")],
            "rm .env": [("delete", ".env")],
            "del .env": [("delete", ".env")],
            'Set-Content -Path ".env" -Value "x"': [("write", ".env")],
            'Set-Content -LiteralPath ".env" -Value "x"': [("write", ".env")],
            'Out-File -FilePath ".env"': [("write", ".env")],
            '"x" | Out-File ".env"': [("write", ".env")],
            '"x" > .env': [("write", ".env")],
            'Move-Item -Path "x" -Destination ".env"': [("delete", "x"), ("write", ".env")],
            'Move-Item .env y': [("delete", ".env"), ("write", "y")],
            'Rename-Item .env y': [("delete", ".env"), ("write", "y")],
            'ri .env': [("delete", ".env")],
            'erase .env': [("delete", ".env")],
            'Add-Content .env x': [("write", ".env")],
            'Clear-Content .env': [("write", ".env")],
            'New-Item .env': [("write", ".env")],
            'cp a .env': [("write", ".env")],
            'Get-ChildItem\nRemove-Item .env': [("delete", ".env")],
            'ls & Remove-Item .env': [("delete", ".env")],
            'ls # note\nRemove-Item .env': [("delete", ".env")],
            'Test-Path (Remove-Item .env)': [("delete", ".env")],
            'pwsh -c "Remove-Item .env"': [("delete", ".env")],
            'Copy-Item -Path "x" -Destination ".env"': [("write", ".env")],
            'Copy-Item "x" ".env"': [("write", ".env")],
        }

        for command, expected in cases.items():
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertEqual(list(extraction.target_operations), expected)
                self.assertEqual(
                    list(extraction.write_delete_targets),
                    [path for _, path in expected],
                )

    def test_tokenizer_handles_quotes_and_backtick_escapes(self):
        cases = {
            'Remove-Item .en"v"': ".env",
            "Remove-Item '.env'": ".env",
            "Remove-Item .en`v": ".env",
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertFalse(extraction.parse_ambiguous)
                self.assertEqual(extraction.write_delete_targets, (expected,))

    def test_comma_separated_path_argument_lists_are_extracted(self):
        cases = {
            'Remove-Item -Path ".env",".env.local"': (
                ("delete", ".env"),
                ("delete", ".env.local"),
            ),
            'Set-Content -Path ".env",".env.local" -Value x': (
                ("write", ".env"),
                ("write", ".env.local"),
            ),
            "Remove-Item .env,.env.local": (
                ("delete", ".env"),
                ("delete", ".env.local"),
            ),
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertFalse(extraction.parse_ambiguous)
                self.assertEqual(extraction.target_operations, expected)

    def test_read_only_commands_have_no_write_delete_targets(self):
        for command in (
            "Get-ChildItem .github\\workflows\\",
            "Get-Content .env",
            "Test-Path .env",
            "ls .github\\workflows\\",
        ):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertFalse(extraction.parse_ambiguous)
                self.assertTrue(extraction.read_only)
                self.assertEqual(extraction.write_delete_targets, tuple())

    def test_variables_dynamic_commands_and_unknown_cmdlets_are_ambiguous(self):
        for command in (
            "Remove-Item $target",
            '$p = ".env"; Remove-Item $p',
            "& $cmd .env",
            "Invoke-Expression 'Remove-Item .env'",
            "Get-Content x | Where-Object { $_ }",
        ):
            with self.subTest(command=command):
                extraction = self._extract(command)
                self.assertTrue(extraction.parse_ambiguous)


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
