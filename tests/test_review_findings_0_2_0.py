"""Regression tests for the defects an independent review found in the 0.2.0 changes.

Each case was a real bypass or leak in the first draft of the release. The numbers
refer to that review's findings.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jangseung.cli.hook_run import render_hook_response, run_aeg_hook_run
from jangseung.classify import is_protected_path, is_review_path
from jangseung.evidence.hook_judgment_engine_alignment import OUTSIDE_PROJECT_TARGET
from jangseung.evidence.shell_command_risk import guard_self_disable
from jangseung.state.hook_ledger import read_hook_ledger
from jangseung.state.session_marks import (
    MAX_SESSIONS,
    mark_secret_naming_write,
    secret_naming_writes,
)


class Case(unittest.TestCase):
    FOLDERS = ("src", "sub/scripts", "scripts", "QQQQQQQQQQQQ", "--", "-", "true", "QQQQQ")

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="jangseung-review-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for folder in self.FOLDERS:
            (self.root / folder).mkdir(parents=True)
        (self.root / ".aeg").mkdir()
        (self.root / "README.md").write_text("x\n", encoding="utf-8")

    def policy(self, **policy):
        (self.root / ".aeg" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    def payload(self, tool, tool_input, mode=None):
        data = {"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "cwd": str(self.root), "session_id": "s"}
        if mode is not None:
            data["permission_mode"] = mode
        return json.dumps(data)

    def judge(self, tool, tool_input, mode=None, substrate=None):
        return render_hook_response(
            self.payload(tool, tool_input, mode), repo_root=self.root, substrate=substrate, working_dir=self.root
        )

    def bash(self, command, tool="Bash"):
        return self.judge(tool, {"command": command}).permission_decision

    def record(self, tool, tool_input):
        run_aeg_hook_run(
            stdin=io.StringIO(self.payload(tool, tool_input)), stdout=io.StringIO(), stderr=io.StringIO(),
            repo_root=self.root, working_dir=self.root,
        )
        return read_hook_ledger(self.root)[-1].record


class LeadingCdTests(Case):
    def setUp(self):
        super().setUp()
        self.policy(allow_commands=["pytest", "python -m pytest", "bash scripts/run.sh", "python tool.py"])

    def test_plain_folder_inside_the_project_is_still_approved(self):
        for command in ("cd src && pytest", "cd ./src && pytest -q", "cd sub/scripts && python -m pytest 2>&1"):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "allow")
                self.assertEqual(self.bash(command, tool="PowerShell"), "allow")

    def test_1_a_quoted_folder_is_not_read_as_its_filler(self):
        for command in ("cd 'C:/Windows' && pytest", "cd '.git/hooks' && pytest", 'cd "C:/Win" && pytest',
                        "cd '/etc' && pytest"):
            with self.subTest(command=command):
                self.assertNotEqual(self.bash(command), "allow")
                self.assertNotEqual(self.bash(command, tool="PowerShell"), "allow")

    def test_2_option_like_and_multi_line_folders_are_refused(self):
        for command in ("cd -- && pytest", "cd - && pytest", "cd\ntrue && pytest", "cd\ttrue\n&& pytest",
                        "cd -P src && pytest", "cd src/.. && pytest", "cd src. && pytest", "cd ~ && pytest",
                        "cd src/../.. && pytest", "cd .git && pytest", "cd src\\..\\.. && pytest"):
            with self.subTest(command=command):
                self.assertNotEqual(self.bash(command), "allow")

    def test_4_cd_does_not_carry_an_approval_that_names_a_file(self):
        self.assertEqual(self.bash("bash scripts/run.sh"), "allow")
        self.assertNotEqual(self.bash("cd sub && bash scripts/run.sh"), "allow")
        self.assertNotEqual(self.bash("cd src && python tool.py"), "allow")
        self.assertEqual(self.bash("cd src && python -m pytest"), "allow")

    def test_cdpath_requires_an_explicit_current_folder(self):
        with mock.patch.dict(os.environ, {"CDPATH": "/somewhere"}):
            self.assertNotEqual(self.bash("cd src && pytest"), "allow")
            self.assertEqual(self.bash("cd ./src && pytest"), "allow")


class ApprovalSuffixAndQuoteTests(Case):
    def test_3_only_a_space_or_tab_separates_the_stream_merge(self):
        self.policy(allow_commands=["python tool.py"], protect_paths=["tool.py"])
        self.assertEqual(self.bash("python tool.py 2>&1"), "allow")
        self.assertEqual(self.bash("python tool.py\t2>&1"), "allow")
        for separator in ("\x0c", "\xa0", "\u2003", "\x0b", "\u3000", "\x1c"):
            with self.subTest(separator=repr(separator)):
                self.assertNotEqual(self.bash(f"python tool.py{separator}2>&1"), "allow")

    def test_6_a_double_quote_inside_single_quotes_is_not_read_through(self):
        self.policy(allow_commands=["npm test", "git commit"])
        self.assertNotEqual(self.bash("npm test 'x\" & echo INJECTED & \"'"), "allow")
        self.assertNotEqual(self.bash("npm test 'a\"|calc|\"'"), "allow")
        self.assertEqual(self.bash("git commit -m 'fix(parser): typo & more'"), "allow")


class ReviewTierRegressionTests(Case):
    def test_5_a_folder_of_requirement_files_stays_protected(self):
        for path in ("requirements/dev.txt", "requirements-dev.txt", "api/requirements.txt", "requirements/prod/base.txt"):
            with self.subTest(path=path):
                self.assertTrue(is_protected_path(path))
                self.assertTrue(is_review_path(path))
                write = {"file_path": path, "content": "x"}
                self.assertEqual(self.judge("Write", write).permission_decision, "deny")
                self.assertEqual(self.judge("Write", write, mode="default").permission_decision, "ask")

    def test_10_an_unhashable_permission_mode_is_just_not_an_asking_mode(self):
        for mode in ([], {}, ["default"], {"default": 1}, 0, True):
            with self.subTest(mode=mode):
                result = self.judge("Write", {"file_path": "package.json", "content": "x"}, mode=mode)
                self.assertEqual(result.permission_decision, "deny")
                self.assertFalse(result.fail_closed)
                self.assertNotIn("internal_judgment_error_fail_closed_deny", result.reason_codes)


class GuardCommandSpellingTests(Case):
    SPELLINGS = (
        "aeg policy add --command bash --yes",
        "python -m jangseung.cli policy add --command bash --yes",
        "python -m jangseung.cli.main policy add --command bash --yes",
        "python -mjangseung.cli policy add --command bash",
        "python -I -m jangseung.cli.main uninstall --yes",
        "python aeg policy add --command bash",
        "python3 /opt/plugin/aeg policy preset python --yes",
        "py -3 -m jangseung policy show",
        "python -m src.cli uninstall",
        "python -Im jangseung.cli policy add --command bash --yes",
        "python -Bm jangseung.cli policy add --command bash",
        "python -W -m aeg policy add --command bash",
        "python -W ignore -m jangseung.cli policy add",
        "python -m runpy jangseung.cli policy add --command bash",
        "python aeg. policy add --command bash",
        "uv run aeg policy add --command bash",
        "uv run python -m jangseung.cli uninstall --yes",
        "pypy3 -m jangseung policy show",
    )

    def test_7_every_known_route_to_the_guard_cli_is_denied_even_when_python_is_approved(self):
        for policy in ({}, {"allow_commands": ["python", "python3", "py", "aeg"]}):
            self.policy(**policy)
            for command in self.SPELLINGS:
                with self.subTest(policy=bool(policy), command=command):
                    self.assertTrue(guard_self_disable(command.split()))
                    self.assertEqual(self.bash(command), "deny")

    def test_other_modules_and_scripts_are_not_mistaken_for_the_guard(self):
        for command in ("python -m pytest policy", "python -m pip install requests", "python tools/policy.py",
                        "python -m mypackage.cli uninstall", "pytest -m policy",
                        "rg aeg policy", "git grep aeg install", "cp aeg policy", "cat aeg policy", "ls aeg policy",
                        "echo aeg install", "git log --oneline -- aeg install", "python tools/check.py aeg install",
                        "python -m src.cli.x install", "python -m jangseung.cli.reason_text policy",
                        "git commit -m jangseung install notes", "python -c pass aeg policy",
                        "uv run pytest policy"):
            with self.subTest(command=command):
                self.assertFalse(guard_self_disable(command.split()))


class RecordContentTests(Case):
    def test_8_strings_arguments_and_home_paths_stay_out_of_the_record(self):
        cases = (
            ("PowerShell", {"command": "'Tr0ub4dor' > notes.txt"}, "commands", ["<other>"]),
            ("PowerShell", {"command": '"Hunter2pw" | Out-File notes.txt'}, "commands", ["<other>", "out-file"]),
            ("Bash", {"command": "$(true) Hunter2pw"}, "commands", ["<dynamic>"]),
            ("Bash", {"command": "`true` Hunter2pw"}, "commands", ["<dynamic>"]),
            ("Bash", {"command": "sk-ant-api03-abcdefgh --flag"}, "commands", ["<other>"]),
            ("Bash", {"command": "'pytest' -q"}, "commands", ["<other>"]),
            ("Bash", {"command": "docker-compose up -d"}, "commands", ["docker-compose"]),
            ("Write", {"file_path": "~/private-name.txt", "content": "x"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("Read", {"file_path": "~"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("Write", {"file_path": "C:private-name.txt", "content": "x"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("Bash", {"command": "echo x > ~/Hunter2pw"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("Bash", {"command": "echo x > ~root/Hunter2pw"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("Bash", {"command": "echo x > C:Hunter2pw"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("PowerShell", {"command": "ni HKCU:\\Hunter2pw"}, "targets", [OUTSIDE_PROJECT_TARGET]),
            ("PowerShell", {"command": "Write-Output Hunter2pw; 'Hunter2pw' > x.txt"}, "commands",
             ["write-output", "<other>"]),
            ("Bash", {"command": "echo Hunter2pw; 'Hunter2pw' --x"}, "commands", ["echo", "<other>"]),
            ("Bash", {"command": "git Hunter-pw"}, "commands", ["git"]),
            ("Bash", {"command": "FOO=1 BAR=2 git status"}, "commands", ["git status"]),
        )
        for tool, tool_input, field, expected in cases:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertEqual(self.record(tool, tool_input)[field], expected)
        text = (self.root / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8").lower()
        for word in ("tr0ub4dor", "hunter2pw", "private-name", "abcdefgh"):
            self.assertNotIn(word, text)


class WrittenTextScanTests(Case):
    def test_a_denied_write_is_not_scanned_and_leaves_no_mark(self):
        body = " ".join(f"open('.env') w{index}" for index in range(2000))
        result = self.judge("Write", {"file_path": ".git/hooks/pre-commit", "content": body})
        self.assertEqual(result.permission_decision, "deny")
        self.assertFalse(result.written_text_names_secret_file)

    def test_too_many_distinct_words_mark_the_write_instead_of_reading_forever(self):
        body = " ".join(f"w{index}" for index in range(45_000))
        result = self.judge("Write", {"file_path": "src/big.py", "content": body})
        self.assertEqual(result.permission_decision, "allow")
        self.assertTrue(result.written_text_names_secret_file)

    def test_repeated_words_are_checked_once(self):
        self.policy(allow_paths=[f"p{index}/*.txt" for index in range(200)])
        result = self.judge("Write", {"file_path": "src/big.py", "content": "a " * 150_000})
        self.assertFalse(result.written_text_names_secret_file)


class SessionMarkEncodingTests(Case):
    def test_permitted_writes_are_marked_and_unencodable_paths_fail_closed(self):
        self.policy(allow_commands=["pytest"])
        for index, path in enumerate(("src/x\ud800.py", "src/\udfff\ud800y.py", "src/\U0001f600.py", "src/한글.py")):
            with self.subTest(path=ascii(path)):
                session = f"enc{index}"
                out = io.StringIO()
                payload = {"tool_name": "Write", "tool_input": {"file_path": path, "content": "open('.env').read()"},
                           "tool_use_id": "t", "cwd": str(self.root), "session_id": session}
                exit_code = run_aeg_hook_run(stdin=io.StringIO(json.dumps(payload)), stdout=out, stderr=io.StringIO(),
                                            repo_root=self.root, working_dir=self.root)
                response = json.loads(out.getvalue())["hookSpecificOutput"]
                reason = response["permissionDecisionReason"]
                self.assertNotIn("session_mark_recording_failed", reason)
                try:
                    os.fsencode(path)
                except UnicodeEncodeError:
                    # POSIX cannot inspect these lone surrogates. The write is
                    # denied before it could create code; no mark is needed.
                    self.assertEqual(response["permissionDecision"], "deny")
                    self.assertEqual(exit_code, 2)
                    self.assertIn("internal_judgment_error_fail_closed_deny", reason)
                    self.assertEqual(secret_naming_writes(self.root, session), ())
                    continue
                self.assertEqual(response["permissionDecision"], "allow")
                self.assertEqual(exit_code, 0)
                self.assertTrue(secret_naming_writes(self.root, session))
                held = render_hook_response(
                    json.dumps({"tool_name": "Bash", "tool_input": {"command": "pytest"}, "tool_use_id": "t",
                                "cwd": str(self.root), "session_id": session}),
                    repo_root=self.root, working_dir=self.root,
                )
                self.assertEqual(held.permission_decision, "ask")
        self.assertEqual([p.name for p in (self.root / ".aeg").iterdir() if p.name.startswith(".session-marks-")], [])

    def test_recorder_preserves_surrogates_even_where_paths_are_unencodable(self):
        self.policy(allow_commands=["pytest"])
        paths = ["src/x\ud800.py", "src/\udfff\ud800y.py", "src/\U0001f600.py", "src/한글.py"]
        mark_secret_naming_write(self.root, "s", paths)
        self.assertEqual(secret_naming_writes(self.root, "s"), tuple(paths))
        # This checks the original ASCII-recorder regression on every OS,
        # separately from whether that OS permits the preceding Write request.
        (self.root / ".aeg/session_marks.json").read_text(encoding="ascii")
        self.assertEqual(self.bash("pytest"), "ask")


class SessionMarkCapacityTests(Case):
    def test_11_marks_within_the_caps_never_reach_the_size_limit(self):
        long_path = "한" * 500 + ".py"
        for index in range(MAX_SESSIONS + 5):
            mark_secret_naming_write(self.root, f"s{index}", [f"{long_path}{n}" for n in range(40)])
        # The newest sessions are all still readable and marked.
        for index in range(5, MAX_SESSIONS + 5):
            self.assertTrue(secret_naming_writes(self.root, f"s{index}"), index)
        # Older ones were dropped, which the module documents.
        self.assertEqual(secret_naming_writes(self.root, "s0"), ())


if __name__ == "__main__":
    unittest.main()
