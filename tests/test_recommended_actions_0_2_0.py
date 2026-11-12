"""0.2.0: review tier, sturdier approvals, session marks, richer records, policy command."""

from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jangseung.cli import install as install_module
from jangseung.cli.hook_run import ensure_recording_directory, render_hook_response, run_aeg_hook_run
from jangseung.cli.install import SCOPE_LOCAL, cmd_install, cmd_uninstall, settings_path
from jangseung.cli.policy import PRESETS, cmd_policy_add, cmd_policy_show, policy_path
from jangseung.classify import is_protected_path, is_review_path, names_secret_file
from jangseung.evidence.hook_judgment_engine_alignment import (
    APPROVAL_HELD_REASON,
    OUTSIDE_PROJECT_TARGET,
    REVIEW_TIER_REASON,
)
from jangseung.state.hook_ledger import (
    HOOK_LEDGER_FILE,
    append_hook_decision_record,
    read_hook_ledger,
    verify_hook_ledger,
)
from jangseung.state.session_marks import SESSION_MARKS_FILE, secret_naming_writes

REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="jangseung-020-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for relative, text in {
            "README.md": "# demo\n",
            ".env": "KEY=dummy\n",
            "pyproject.toml": "[project]\n",
            "package.json": "{}\n",
            "Makefile": "test:\n",
            "src/app.py": "print(1)\n",
            "tests/conftest.py": "",
            "packages/api/pyproject.toml": "",
            "jangseung/cli/x.py": "",
        }.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        (self.root / ".aeg").mkdir()

    def write_policy(self, **policy):
        (self.root / ".aeg" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    def payload(self, tool, tool_input, *, mode="default", session="s1"):
        data = {"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t1", "cwd": str(self.root)}
        if mode is not None:
            data["permission_mode"] = mode
        if session is not None:
            data["session_id"] = session
        return json.dumps(data)

    def judge(self, tool, tool_input, *, mode="default", session="s1", substrate=None):
        return render_hook_response(
            self.payload(tool, tool_input, mode=mode, session=session),
            repo_root=self.root, substrate=substrate, working_dir=self.root,
        )

    def run_hook(self, tool, tool_input, *, mode="default", session="s1", substrate=None):
        out = io.StringIO()
        code = run_aeg_hook_run(
            stdin=io.StringIO(self.payload(tool, tool_input, mode=mode, session=session)),
            stdout=out, stderr=io.StringIO(), repo_root=self.root, substrate=substrate, working_dir=self.root,
        )
        return code, json.loads(out.getvalue())["hookSpecificOutput"]

    def edit(self, path):
        return {"file_path": path, "old_string": "a", "new_string": "b"}


class ReviewTierTests(ProjectCase):
    REVIEW_FILES = (
        "pyproject.toml", "package.json", "Makefile", "tests/conftest.py", "packages/api/pyproject.toml",
        "requirements-dev.txt", "Dockerfile", ".github/workflows/ci.yml", ".pre-commit-config.yaml",
    )

    def test_review_files_ask_where_a_person_is_asked(self):
        for mode in ("default", "acceptEdits"):
            for path in self.REVIEW_FILES:
                with self.subTest(mode=mode, path=path):
                    result = self.judge("Edit", self.edit(path), mode=mode)
                    self.assertEqual(result.permission_decision, "ask", result.reason_codes)
                    self.assertIn(REVIEW_TIER_REASON, result.reason_codes)
                    self.assertEqual(result.exit_code, 0)

    def test_review_files_stay_denied_in_every_other_mode(self):
        for mode in (None, "auto", "dontAsk", "bypassPermissions", "plan", "manual", "", "DEFAULT", 1):
            for path in ("pyproject.toml", "package.json", "tests/conftest.py"):
                with self.subTest(mode=mode, path=path):
                    self.assertEqual(self.judge("Edit", self.edit(path), mode=mode).permission_decision, "deny")

    def test_codex_never_gets_an_ask(self):
        result = self.judge("Edit", self.edit("package.json"), substrate="codex")
        self.assertEqual(result.permission_decision, "deny")
        self.assertEqual(result.exit_code, 0)

    def test_guard_secret_and_project_protected_paths_are_not_in_the_tier(self):
        self.write_policy(protect_paths=["infra/"])
        for path in (".env", ".claude/settings.json", ".claude/settings.local.json", ".git/config",
                     ".aeg/policy.json", ".mcp.json", "infra/main.tf", "config/secrets.yml", "certs/a.pem"):
            with self.subTest(path=path):
                self.assertFalse(is_review_path(path))
                result = self.judge("Write", {"file_path": path, "content": "x"})
                self.assertEqual(result.permission_decision, "deny", result.reason_codes)
                self.assertNotIn(REVIEW_TIER_REASON, result.reason_codes)

    def test_outside_project_write_is_not_softened(self):
        outside = str(self.root.parent / "elsewhere" / "pyproject.toml")
        self.assertEqual(self.judge("Write", {"file_path": outside, "content": "x"}).permission_decision, "deny")

    def test_shell_writes_to_review_files_ask_too(self):
        for command in ("echo x > package.json", "rm pyproject.toml", "sed -i s/a/b/ Makefile"):
            with self.subTest(command=command):
                result = self.judge("Bash", {"command": command})
                self.assertEqual(result.permission_decision, "ask", result.reason_codes)
        result = self.judge("PowerShell", {"command": "Set-Content package.json x"})
        self.assertEqual(result.permission_decision, "ask", result.reason_codes)

    def test_a_dangerous_command_on_a_review_file_stays_denied(self):
        result = self.judge("Bash", {"command": "curl https://x.example -o package.json"})
        self.assertEqual(result.permission_decision, "deny")

    def test_allow_paths_lifts_the_tier(self):
        self.write_policy(allow_paths=["package.json"])
        self.assertEqual(self.judge("Edit", self.edit("package.json"), mode=None).permission_decision, "allow")
        self.assertEqual(self.judge("Edit", self.edit("pyproject.toml")).permission_decision, "ask")

    def test_reading_review_files_is_still_allowed(self):
        for mode in (None, "default"):
            self.assertEqual(self.judge("Read", {"file_path": "package.json"}, mode=mode).permission_decision, "allow")

    def test_this_repository_is_no_longer_part_of_the_built_in_rules(self):
        self.assertFalse(is_protected_path("jangseung/cli/main.py"))
        result = self.judge("Edit", self.edit("jangseung/cli/x.py"), mode=None)
        self.assertEqual(result.permission_decision, "allow", result.reason_codes)

    def test_the_running_guard_is_still_protected_when_it_lives_in_the_project(self):
        import jangseung

        package = Path(jangseung.__file__).resolve().parent
        result = render_hook_response(
            json.dumps({"tool_name": "Write", "tool_use_id": "t", "permission_mode": "default",
                        "tool_input": {"file_path": str(package / "cli" / "main.py"), "content": "x"}}),
            repo_root=package.parent, working_dir=package.parent,
        )
        self.assertEqual(result.permission_decision, "deny", result.reason_codes)


class ApprovalMatchingTests(ProjectCase):
    def setUp(self):
        super().setUp()
        self.write_policy(allow_commands=["pytest", "git commit"])

    def decision(self, command, tool="Bash"):
        return self.judge(tool, {"command": command}, mode=None).permission_decision

    def test_spellings_that_do_not_change_what_runs_are_approved(self):
        for command in (
            "pytest",
            "pytest tests -q",
            "pytest 2>&1",
            "pytest -q   2>&1  ",
            "cd src && pytest",
            "cd src && pytest -q 2>&1",
            "git commit -m 'fix(parser): typo'",
            "git commit -m 'close #12; see {notes} & <more>'",
            'git commit -m "fix(parser): typo"',
            "pytest -k 'a and (b or c)'",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), "allow")

    def test_powershell_tool_gets_the_same_reading(self):
        self.assertEqual(self.decision("pytest 2>&1", tool="PowerShell"), "allow")
        self.assertEqual(self.decision("git commit -m 'fix(parser): typo'", tool="PowerShell"), "allow")

    def test_anything_a_shell_would_act_on_is_not_approved(self):
        for command in (
            "pytest; rm -rf .",
            "pytest && rm -rf .",
            "pytest | tail -5",
            "pytest > out.txt",
            "pytest 2>&1 | tee log",
            "pytest 2> err.txt",
            "pytest $(cat x)",
            "pytest `cat x`",
            'git commit -m "a $(rm -rf .)"',
            'git commit -m "a `rm -rf .`"',
            "git commit -m 'x ’ ; rm -rf . ; ‘ y'",
            "git commit -m 'unterminated",
            "pytest --% 'a | b'",
            "pytest -k'a;b'",
            "pytest 'a'b;c",
            "pytest 'a\\'; rm -rf .; echo '",
            "git commit -m 'line one\nrm -rf .'",
            "cd missing && pytest",
            "cd .. && pytest",
            "cd .git && pytest",
            "cd src && pytest && rm -rf .",
            "cd src; pytest",
            "cd 'src' && pytest",
            "# pytest",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(self.decision(command), "allow")

    def test_an_absolute_folder_outside_the_project_is_refused(self):
        outside = self.root.parent.as_posix()
        self.assertNotEqual(self.decision(f"cd {outside} && pytest"), "allow")

    def test_guard_commands_cannot_be_approved_or_run_by_an_agent(self):
        self.write_policy(allow_commands=["aeg policy", "aeg"])
        for command in ("aeg policy add --command pytest", "aeg policy preset python --yes",
                        "python -m jangseung.cli policy add --command x"):
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), "deny")


class SecretNamingWriteTests(ProjectCase):
    LEAK = {"file_path": "scripts/leak.py", "content": "print(open('.env').read())\n"}

    def setUp(self):
        super().setUp()
        self.write_policy(allow_commands=["pytest"])

    def test_names_are_recognized_without_flagging_ordinary_code(self):
        for token in (".env", "config/.env.local", "~/.aws/credentials", "server.pem", ".ssh/id_rsa", ".npmrc"):
            self.assertTrue(names_secret_file(token), token)
        for token in ("event.key", "os.environ", ".env.example", "credentials", "secrets", "app.py", "self.credentials"):
            self.assertFalse(names_secret_file(token), token)

    def test_write_naming_a_secret_holds_approved_commands_for_that_session(self):
        self.assertEqual(self.run_hook("Bash", {"command": "pytest"}, mode=None)[1]["permissionDecision"], "allow")
        code, output = self.run_hook("Write", self.LEAK)
        self.assertEqual((code, output["permissionDecision"]), (0, "allow"))
        self.assertEqual(secret_naming_writes(self.root, "s1"), ("scripts/leak.py",))

        held = self.judge("Bash", {"command": "pytest"}, mode=None)
        self.assertEqual(held.permission_decision, "ask")
        self.assertIn(APPROVAL_HELD_REASON, held.reason_codes)
        self.assertIn("Jangseung:", held.reason)
        # Codex cannot ask, so the hold is a stop there.
        self.assertEqual(self.judge("Bash", {"command": "pytest"}, mode=None, substrate="codex").permission_decision, "deny")
        # Reads stay automatic, and another session is not held.
        self.assertEqual(self.judge("Bash", {"command": "git status"}, mode=None).permission_decision, "ask")
        self.assertEqual(self.judge("Bash", {"command": "cat README.md"}, mode=None).permission_decision, "allow")
        self.assertEqual(self.judge("Bash", {"command": "pytest"}, mode=None, session="s2").permission_decision, "allow")

    def test_edits_patches_and_notebooks_are_read_too(self):
        cases = (
            ("Edit", {"file_path": "src/app.py", "old_string": "a", "new_string": "open('.env')"}),
            ("MultiEdit", {"file_path": "src/app.py", "edits": [{"old_string": "a", "new_string": "x = '.aws/credentials'"}]}),
            ("NotebookEdit", {"notebook_path": "nb.ipynb", "new_source": "open('id_rsa')"}),
        )
        for index, (tool, tool_input) in enumerate(cases):
            with self.subTest(tool=tool):
                session = f"edit{index}"
                self.run_hook(tool, tool_input, session=session)
                self.assertTrue(secret_naming_writes(self.root, session))
        patch = "*** Begin Patch\n*** Add File: tool.py\n+print(open('.env').read())\n*** End Patch\n"
        self.run_hook("apply_patch", {"command": patch}, session="patch", substrate="codex", mode=None)
        self.assertEqual(secret_naming_writes(self.root, "patch"), ("tool.py",))

    def test_documentation_ordinary_code_and_denied_writes_leave_no_mark(self):
        self.run_hook("Write", {"file_path": "README.md", "content": "copy .env.example to .env"})
        self.run_hook("Write", {"file_path": ".gitignore", "content": ".env\n*.pem\n"})
        self.run_hook("Write", {"file_path": "src/keys.py", "content": "event.key; os.environ.get('X'); '.env.example'"})
        self.run_hook("Write", {"file_path": ".env", "content": "open('.env')"})
        self.assertEqual(secret_naming_writes(self.root, "s1"), ())
        self.assertFalse((self.root / ".aeg" / SESSION_MARKS_FILE).exists())

    def test_policy_allowed_secret_names_do_not_mark(self):
        self.write_policy(allow_commands=["pytest"], allow_paths=[".env"])
        self.run_hook("Write", self.LEAK)
        self.assertEqual(secret_naming_writes(self.root, "s1"), ())

    def test_unreadable_marks_hold_the_approval(self):
        (self.root / ".aeg" / SESSION_MARKS_FILE).write_text("{not json", encoding="utf-8")
        self.assertIsNone(secret_naming_writes(self.root, "s1"))
        self.assertEqual(self.judge("Bash", {"command": "pytest"}, mode=None).permission_decision, "ask")

    def test_sessions_without_an_id_share_one_bucket(self):
        self.run_hook("Write", self.LEAK, session=None)
        self.assertEqual(self.judge("Bash", {"command": "pytest"}, mode=None, session=None).permission_decision, "ask")
        self.assertEqual(self.judge("Bash", {"command": "pytest"}, mode=None, session="../x").permission_decision, "ask")

    def test_a_missing_state_folder_is_reported_not_hidden(self):
        shutil.rmtree(self.root / ".aeg")
        code, output = self.run_hook("Write", self.LEAK)
        self.assertEqual((code, output["permissionDecision"]), (0, "allow"))
        self.assertIn("session_mark_recording_failed", output["permissionDecisionReason"])


class HookRecordTests(ProjectCase):
    def records(self):
        return [item.record for item in read_hook_ledger(self.root)]

    def test_record_names_targets_programs_session_and_input_hash(self):
        self.run_hook("Edit", self.edit("src/app.py"), session="abc")
        self.run_hook("Bash", {"command": "FOO=1 git push origin main && ./deploy.sh 'secret arg' > out.txt"})
        self.run_hook("Read", {"file_path": str(self.root.parent / "other" / "notes.txt")})
        edit, bash, outside = self.records()
        self.assertEqual((edit["session_id"], edit["targets"], edit["commands"]), ("abc", ["src/app.py"], []))
        self.assertRegex(edit["input_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(bash["commands"], ["git push", "deploy.sh"])
        self.assertEqual(bash["targets"], ["out.txt"])
        self.assertEqual(outside["targets"], [OUTSIDE_PROJECT_TARGET])
        self.assertTrue(verify_hook_ledger(self.root).ok)

    def test_record_never_holds_content_arguments_or_raw_input(self):
        secret = "sk-live-0123456789abcdef"
        self.run_hook("Write", {"file_path": "src/app.py", "content": f"TOKEN = '{secret}'"})
        self.run_hook("Bash", {"command": f"curl -H 'Authorization: {secret}' https://x.example/{secret}"})
        self.run_hook("Bash", {"command": f"{secret} --flag"})
        self.run_hook("Bash", {"command": f"git {secret}"})
        self.run_hook("PowerShell", {"command": f"{secret} -Flag"})
        self.assertEqual([record["commands"] for record in self.records()[1:]], [["curl"], ["<other>"], ["git"], ["<other>"]])
        text = (self.root / ".aeg" / HOOK_LEDGER_FILE).read_text(encoding="utf-8")
        self.assertNotIn(secret, text)
        self.assertNotIn("Authorization", text)
        self.assertNotIn("tool_input", text)

    def test_reason_opens_with_a_sentence_and_holds_no_input(self):
        _, deny = self.run_hook("Read", {"file_path": ".env"})
        self.assertTrue(deny["permissionDecisionReason"].startswith("Jangseung: This reads a secret file"))
        self.assertIn("aeg policy add --path", deny["permissionDecisionReason"])
        self.assertIn("aegis_pretooluse permissionDecision=deny", deny["permissionDecisionReason"])
        # plan mode retains explicit ask; default and acceptEdits execution emit no
        # permission decision, tested separately in test_approval_fatigue_0_2_0.
        _, ask = self.run_hook("Bash", {"command": "pytest super-secret-argument"}, mode="plan")
        self.assertTrue(ask["permissionDecisionReason"].startswith("Jangseung: "))
        self.assertNotIn("super-secret-argument", ask["permissionDecisionReason"])
        _, allow = self.run_hook("Read", {"file_path": "README.md"})
        self.assertTrue(allow["permissionDecisionReason"].startswith("aegis_pretooluse permissionDecision=allow"))

    def test_records_written_before_0_2_0_still_verify_and_chain(self):
        ledger = self.root / ".aeg" / HOOK_LEDGER_FILE
        first = append_hook_decision_record(
            self.root, substrate="claude-code", tool_name="Read", hook_decision="allow",
            permission_decision="allow", fail_closed=False, reason_codes=("x",), exit_code=0,
        )
        old = {key: value for key, value in first.items()
               if key not in {"session_id", "targets", "commands", "input_hash", "record_hash"}}
        from jangseung.state.hook_ledger import compute_hook_record_hash

        old["record_hash"] = compute_hook_record_hash(old)
        ledger.write_text(json.dumps(old, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        self.run_hook("Read", {"file_path": "README.md"})
        verification = verify_hook_ledger(self.root)
        self.assertTrue(verification.ok, verification.errors)
        self.assertEqual(len(verification.records), 2)

    def test_malformed_audit_fields_fail_verification(self):
        self.run_hook("Read", {"file_path": "README.md"})
        ledger = self.root / ".aeg" / HOOK_LEDGER_FILE
        record = json.loads(ledger.read_text(encoding="utf-8"))
        record["targets"] = "README.md"
        ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")
        self.assertFalse(verify_hook_ledger(self.root).ok)


class PolicyCommandTests(ProjectCase):
    def add(self, answer="y\n", **kwargs):
        out = io.StringIO()
        code = cmd_policy_add(self.root, input_stream=io.StringIO(answer), output_stream=out, **kwargs)
        return code, out.getvalue()

    def stored(self):
        return json.loads(policy_path(self.root).read_text(encoding="utf-8"))

    def test_add_shows_a_diff_and_writes_after_confirmation(self):
        code, text = self.add(commands=["pytest  -q"], allow_paths=["package.json"])
        self.assertEqual(code, 0, text)
        self.assertIn('+    "pytest -q"', text)
        self.assertIn("run the project's own", text)
        self.assertEqual(self.stored(), {"allow_paths": ["package.json"], "allow_commands": ["pytest -q"]})
        self.assertEqual(self.judge("Bash", {"command": "pytest -q tests"}, mode=None).permission_decision, "allow")

    def test_declining_writes_nothing(self):
        code, text = self.add(answer="n\n", commands=["pytest"])
        self.assertEqual(code, 0)
        self.assertIn("cancelled", text)
        self.assertFalse(policy_path(self.root).exists())

    def test_existing_entries_are_kept_and_not_duplicated(self):
        self.write_policy(allow_commands=["pytest"], protect_paths=["infra/"])
        self.add(commands=["pytest", "npm test"], assume_yes=True)
        self.assertEqual(self.stored(), {"protect_paths": ["infra/"], "allow_commands": ["pytest", "npm test"]})
        code, text = self.add(commands=["pytest"], assume_yes=True)
        self.assertIn("no changes", text)

    def test_a_value_the_hook_would_ignore_is_refused(self):
        for kwargs in ({"commands": ["pytest; rm -rf ."]}, {"commands": ["echo $HOME"]}, {"mcp_tools": ["mcp__*"]}):
            with self.subTest(kwargs=kwargs):
                code, text = self.add(assume_yes=True, **kwargs)
                self.assertEqual(code, 2, text)
                self.assertFalse(policy_path(self.root).exists())

    def test_a_broken_file_is_not_overwritten(self):
        policy_path(self.root).write_text('{"unknown_key": []}', encoding="utf-8")
        code, text = self.add(commands=["pytest"], assume_yes=True)
        self.assertEqual(code, 1)
        self.assertEqual(policy_path(self.root).read_text(encoding="utf-8"), '{"unknown_key": []}')

    def test_presets_parse_and_apply(self):
        for name in PRESETS:
            with self.subTest(preset=name):
                code, text = self.add(preset=name, assume_yes=True)
                self.assertEqual(code, 0, text)
        self.assertEqual(self.judge("Bash", {"command": "npm test"}, mode=None).permission_decision, "allow")
        self.assertEqual(self.add(preset="nope", assume_yes=True)[0], 2)

    def test_state_folder_is_created_with_its_ignore_file(self):
        shutil.rmtree(self.root / ".aeg")
        self.add(commands=["pytest"], assume_yes=True)
        self.assertEqual((self.root / ".aeg" / ".gitignore").read_text(encoding="utf-8"), "*\n")

    def test_show_reports_content_and_errors(self):
        out = io.StringIO()
        self.assertEqual(cmd_policy_show(self.root, output_stream=out), 0)
        self.assertIn("No policy file yet", out.getvalue())
        self.write_policy(allow_commands=["pytest"])
        out = io.StringIO()
        cmd_policy_show(self.root, as_json=True, output_stream=out)
        self.assertEqual(json.loads(out.getvalue())["policy"]["allow_commands"], ["pytest"])
        policy_path(self.root).write_text("[]", encoding="utf-8")
        out = io.StringIO()
        self.assertEqual(cmd_policy_show(self.root, output_stream=out), 1)


class InstallScopeTests(ProjectCase):
    def install(self, **kwargs):
        out = io.StringIO()
        code = cmd_install(self.root, assume_yes=True, output_stream=out, **kwargs)
        return code, out.getvalue()

    def test_local_scope_writes_the_personal_settings_file_only(self):
        code, text = self.install(scope=SCOPE_LOCAL)
        self.assertEqual(code, 0, text)
        local = settings_path(self.root, SCOPE_LOCAL)
        self.assertEqual(local.name, "settings.local.json")
        self.assertTrue(local.is_file())
        self.assertFalse(settings_path(self.root).exists())
        self.assertIn("hook-run", local.read_text(encoding="utf-8"))
        self.assertEqual(self.judge("Edit", self.edit(".claude/settings.local.json")).permission_decision, "deny")

    def test_project_scope_says_the_file_is_shared(self):
        code, text = self.install()
        self.assertEqual(code, 0, text)
        self.assertIn("aeg install --scope local", text)
        code, text = self.install(scope=SCOPE_LOCAL)
        self.assertIn("Both would judge every call", text)

    def test_uninstall_follows_the_scope(self):
        self.install(scope=SCOPE_LOCAL)
        out = io.StringIO()
        self.assertEqual(cmd_uninstall(self.root, assume_yes=True, scope=SCOPE_LOCAL, output_stream=out), 0)
        self.assertNotIn("hook-run", settings_path(self.root, SCOPE_LOCAL).read_text(encoding="utf-8"))

    def test_doctor_reads_the_personal_file_and_flags_a_double_registration(self):
        from jangseung.cli.hook_doctor import _claude_code_checks

        self.install(scope=SCOPE_LOCAL)
        names = {check.name: check.status for check in _claude_code_checks(self.root)}
        self.assertEqual(names["claude-code local hook registration"], "PASS")
        self.assertNotIn("claude-code hook config", names)
        self.install()
        names = {check.name: check.status for check in _claude_code_checks(self.root)}
        self.assertEqual(names["claude-code duplicate registration"], "WARN")
        self.assertEqual(names["claude-code hook registration"], "PASS")

    def test_scope_is_refused_for_codex(self):
        self.assertEqual(self.install(target="codex", scope=SCOPE_LOCAL)[0], 2)
        self.assertFalse((self.root / ".codex").exists())

    def test_the_installing_interpreter_wins_over_path(self):
        scripts = self.root / "venv-scripts"
        scripts.mkdir()
        name = "aeg.exe" if install_module.os.name == "nt" else "aeg"
        (scripts / name).write_text("", encoding="utf-8")
        other = self.root / "elsewhere" / name
        other.parent.mkdir()
        other.write_text("", encoding="utf-8")
        with mock.patch.object(install_module.sysconfig, "get_path", return_value=str(scripts)), \
                mock.patch.object(install_module.shutil, "which", return_value=str(other)):
            self.assertEqual(install_module._installed_console_script(), str(scripts / name))
        with mock.patch.object(install_module.sysconfig, "get_path", return_value=str(self.root / "none")), \
                mock.patch.object(install_module.shutil, "which", return_value=str(other)):
            self.assertEqual(install_module._installed_console_script(), str(other))


class PluginPackagingTests(unittest.TestCase):
    def test_plugin_version_matches_the_package(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        # tomllib needs Python 3.11; the one line is enough to read here.
        package = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE).group(1)
        plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], package)
        self.assertEqual(plugin["name"], "jangseung")
        market = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual([entry["name"] for entry in market["plugins"]], ["jangseung"])

    def test_plugin_hook_blocks_on_failure_and_prepares_state(self):
        hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
        self.assertEqual(len(hooks), 1)
        hook = hooks[0]["hooks"][0]
        self.assertEqual(hook["onFailure"], "block")
        self.assertEqual(hook["command"].count("hook-run --ensure-state"), 2)
        self.assertIn("-I", hook["command"])
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/aeg", hook["command"])
        self.assertEqual(hooks[0]["matcher"], install_module.WINDOWS_AEGIS_HOOK_MATCHER)

    def test_ensure_recording_directory_creates_once_and_never_rewrites(self):
        root = Path(tempfile.mkdtemp(prefix="jangseung-state-")).resolve()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.assertTrue(ensure_recording_directory(root))
        ignore = root / ".aeg" / ".gitignore"
        self.assertEqual(ignore.read_text(encoding="utf-8"), "*\n")
        ignore.write_text("kept\n", encoding="utf-8")
        self.assertTrue(ensure_recording_directory(root))
        self.assertEqual(ignore.read_text(encoding="utf-8"), "kept\n")
        blocked = Path(tempfile.mkdtemp(prefix="jangseung-state-")).resolve()
        self.addCleanup(shutil.rmtree, blocked, ignore_errors=True)
        (blocked / ".aeg").write_text("a file, not a folder", encoding="utf-8")
        self.assertFalse(ensure_recording_directory(blocked))


if __name__ == "__main__":
    unittest.main()
