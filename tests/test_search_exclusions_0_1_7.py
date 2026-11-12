"""Regression tests for the secret reads through folder searches fixed in 0.1.7."""

from __future__ import annotations

import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from fnmatch import fnmatchcase
from pathlib import Path
from unittest import mock

from jangseung.classify import (
    PathPolicy,
    git_exclusion_pathspecs,
    is_host_resolved_path,
    is_protected_path,
    is_read_protected_path,
    is_secret_path,
    search_exclusion_globs,
    strip_path_decorations,
)
from jangseung.classify.git_program_paths import config_entries, git_program_paths
from jangseung.classify.hook_policy import load_hook_policy
from jangseung.classify.rules import SECRET_DIRECTORY_NAMES, SECRET_FILE_GLOBS, SECRET_FILE_NAMES, SECRET_SUBPATHS
from jangseung.cli import hook_run
from jangseung.cli.hook_doctor import _executable_check
from jangseung.cli.hook_run import OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON, render_hook_response, run_aeg_hook_run
from jangseung.evidence.shell_read_only import classify_shell_read

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUSIONS = search_exclusion_globs()


def _excluded(path: str, globs: tuple[str, ...] = EXCLUSIONS) -> bool:
    """Apply globs the way ripgrep does: a slashless one matches any path component."""

    parts = path.split("/")
    for glob in globs:
        pattern = glob[1:]
        if pattern.startswith("**/"):
            tail = pattern[3:]
            if fnmatchcase("/".join(parts[-(tail.count("/") + 1) :]), tail):
                return True
        elif any(fnmatchcase(part, pattern) for part in parts):
            return True
    return False


def _protected_samples() -> tuple[str, ...]:
    samples = [".aeg/hook_ledger.jsonl", ".env.local", ".env.production", "api/.env.staging"]
    for name in SECRET_DIRECTORY_NAMES:
        samples += [f"{name}/x.txt", f"deep/{name}/x.txt"]
    for name in SECRET_FILE_NAMES:
        samples += [name, f"deep/{name}"]
    samples += [glob.replace("*", "sample") for glob in SECRET_FILE_GLOBS]
    for parts in SECRET_SUBPATHS:
        samples += ["/".join(parts), "deep/" + "/".join(parts)]
    return tuple(samples)


class ExclusionGlobTests(unittest.TestCase):
    def test_every_read_protected_name_is_excluded_in_any_casing(self) -> None:
        for sample in _protected_samples():
            for spelling in (sample, sample.upper(), sample.title()):
                with self.subTest(spelling=spelling):
                    self.assertTrue(is_read_protected_path(spelling), "the sample must be protected")
                    self.assertTrue(_excluded(spelling))

    def test_ordinary_names_stay_searchable(self) -> None:
        for path in (
            "README.md", "src/app.py", ".envoy", ".env_notes.txt", ".environment", "environment.yml",
            "config.json", "docker/config.json", "secretary.md", "credentials.py", "id_rsa.pub", "keys.txt",
            ".github/workflows/ci.yml", "pyproject.toml",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_read_protected_path(path), "the sample must be readable")
                self.assertFalse(_excluded(path))

    def test_env_templates_are_skipped_but_stay_readable_by_name(self) -> None:
        self.assertFalse(is_read_protected_path(".env.example"))
        self.assertTrue(_excluded(".env.example"))

    def test_globs_survive_the_way_claude_code_splits_the_field(self) -> None:
        # Its Grep tool splits ``glob`` on whitespace, then on commas unless braces are present.
        for glob in EXCLUSIONS:
            with self.subTest(glob=glob):
                self.assertTrue(glob.startswith("!"))
                self.assertFalse(set(glob) & set(" \t\n,{}"))

    def test_policy_reopens_only_a_whole_rule(self) -> None:
        lifted = search_exclusion_globs(PathPolicy(allow_paths=(".env",)))
        self.assertFalse(_excluded(".env", lifted))
        self.assertFalse(_excluded("api/.env", lifted))
        self.assertTrue(_excluded(".env.local", lifted))

        self.assertFalse(_excluded(".env.local", search_exclusion_globs(PathPolicy(allow_paths=(".env.*",)))))
        self.assertFalse(_excluded("a.pem", search_exclusion_globs(PathPolicy(allow_paths=("*.pem",)))))
        # A folder rule stays: approving ``secrets`` opens one folder, not ``deep/secrets``.
        self.assertEqual(search_exclusion_globs(PathPolicy(allow_paths=("secrets", ".docker"))), EXCLUSIONS)

        member_only = search_exclusion_globs(PathPolicy(allow_paths=("tests/fixtures/*.pem", ".env.local")))
        self.assertEqual(member_only, EXCLUSIONS)

    def test_policy_cannot_reopen_the_guard_state(self) -> None:
        self.assertTrue(_excluded(".aeg/policy.json", search_exclusion_globs(PathPolicy(allow_paths=(".aeg", "*")))))


class _Project(unittest.TestCase):
    FILES = (".env", ".env.example", "README.md", "app.py", "docs/a.md", "api/.env")

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / "project"
        (self.root / ".git").mkdir(parents=True)
        (self.root / ".aeg").mkdir()
        for relative in self.FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("PLACEHOLDER=dummy\n", encoding="utf-8")

    def raw(self, tool: str, **tool_input) -> str:
        return json.dumps({"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "hook_event_name": "PreToolUse"})

    def judge(self, tool: str, *, substrate: str = "claude-code", working_dir: Path | None = None, **tool_input):
        return render_hook_response(
            self.raw(tool, **tool_input),
            repo_root=self.root,
            substrate=substrate,
            working_dir=self.root if working_dir is None else working_dir,
        )

    @staticmethod
    def output(result) -> dict:
        return json.loads(result.stdout_json)["hookSpecificOutput"]


class GrepUpdatedInputTests(_Project):
    def test_a_search_that_walks_a_directory_runs_with_the_exclusions_last(self) -> None:
        for tool_input in (
            {}, {"path": "."}, {"path": "docs"}, {"path": str(self.root)}, {"type": "py"}, {"output_mode": "content", "-n": True},
            {"glob": "*"}, {"glob": "**"}, {"glob": ".*"}, {"glob": ".en*"}, {"glob": "?env"}, {"glob": ".e[n]v"},
            {"glob": ".E*"}, {"glob": "*env"}, {"glob": "{.e*,x}"}, {"glob": "*.p?m"}, {"glob": "**/.en?"},
            {"glob": "*.py"}, {"glob": "*.{py,md}"},
        ):
            with self.subTest(tool_input=tool_input):
                result = self.judge("Grep", pattern="PLACEHOLDER", **tool_input)
                output = self.output(result)
                self.assertEqual(output["permissionDecision"], "allow")
                updated = output["updatedInput"]
                words = updated["glob"].split()
                self.assertEqual(tuple(words[-len(EXCLUSIONS) :]), EXCLUSIONS)
                own = tool_input.get("glob")
                self.assertEqual(words[: -len(EXCLUSIONS)], [own] if own else [])
                # The whole input is replaced, so everything else must come back unchanged.
                self.assertEqual({k: v for k, v in updated.items() if k != "glob"}, {"pattern": "PLACEHOLDER", **{k: v for k, v in tool_input.items() if k != "glob"}})
                self.assertIn(OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON, result.reason_codes)

    def test_a_named_file_also_carries_the_exclusions(self) -> None:
        # The hook must not have to tell a file from a directory the way the host would.
        for path, working_dir in (("README.md", self.root), (str(self.root / "README.md"), self.root), ("a.md", self.root / "docs"), ("not-there-yet", self.root)):
            with self.subTest(path=path):
                output = self.output(self.judge("Grep", pattern="x", path=path, working_dir=working_dir))
                self.assertEqual(output["permissionDecision"], "allow")
                self.assertEqual(output["updatedInput"]["path"], path)
                self.assertEqual(tuple(output["updatedInput"]["glob"].split()), EXCLUSIONS)

    def test_a_decoy_file_named_like_a_drive_does_not_remove_the_exclusions(self) -> None:
        (self.root / "C").write_text("decoy\n", encoding="utf-8")
        self.assertIn("updatedInput", self.output(self.judge("Grep", pattern="x", path="C")))
        for path in ("C:", "C:."):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Grep", pattern="x", path=path).permission_decision, "deny")

    def test_a_denied_search_is_not_rewritten(self) -> None:
        for tool_input in ({"path": ".env"}, {"path": "api/.env"}, {"glob": ".env*"}, {"glob": "**/*.pem"}, {"path": "/etc"}, {"path": ".aeg"}, {"path": ".."}):
            with self.subTest(tool_input=tool_input):
                output = self.output(self.judge("Grep", pattern="x", **tool_input))
                self.assertEqual(output["permissionDecision"], "deny")
                self.assertNotIn("updatedInput", output)

    def test_other_tools_are_not_rewritten(self) -> None:
        for tool, tool_input in (("Glob", {"pattern": "**/*"}), ("Read", {"file_path": "README.md"}), ("Write", {"file_path": "a.txt", "content": "x"})):
            with self.subTest(tool=tool):
                output = self.output(self.judge(tool, **tool_input))
                self.assertEqual(output["permissionDecision"], "allow")
                self.assertNotIn("updatedInput", output)

    def test_policy_approvals_reach_the_search(self) -> None:
        (self.root / ".aeg" / "policy.json").write_text(json.dumps({"allow_paths": [".env", ".env.example"]}), encoding="utf-8")
        words = self.output(self.judge("Grep", pattern="x"))["updatedInput"]["glob"].split()
        self.assertFalse(_excluded(".env", tuple(words)))
        self.assertTrue(_excluded(".env.local", tuple(words)))
        for path in (".env.example", ".env"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Grep", pattern="x", path=path).permission_decision, "allow")

    def test_a_partly_approved_rule_stays_excluded_but_the_file_can_be_named(self) -> None:
        (self.root / "tests" / "fixtures").mkdir(parents=True)
        (self.root / "tests" / "fixtures" / "a.pem").write_text("x\n", encoding="utf-8")
        (self.root / ".aeg" / "policy.json").write_text(json.dumps({"allow_paths": ["tests/fixtures/*.pem"]}), encoding="utf-8")
        walked = self.output(self.judge("Grep", pattern="x", path="tests/fixtures"))
        self.assertEqual(tuple(walked["updatedInput"]["glob"].split()), EXCLUSIONS)
        self.assertEqual(self.judge("Grep", pattern="x", path="tests/fixtures/a.pem").permission_decision, "allow")

    def test_tool_input_stays_out_of_the_reason_and_the_ledger(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run_aeg_hook_run(
            stdin=io.StringIO(self.raw("Grep", pattern="dummy-pattern-text")),
            stdout=stdout,
            stderr=stderr,
            repo_root=self.root,
            working_dir=self.root,
        )
        self.assertEqual(code, 0)
        output = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(output["updatedInput"]["pattern"], "dummy-pattern-text")
        self.assertNotIn("dummy-pattern-text", output["permissionDecisionReason"])
        ledger = (self.root / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("dummy-pattern-text", ledger)
        self.assertIn(OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON, ledger)

    def test_a_recording_failure_keeps_the_exclusions(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(hook_run, "append_hook_decision_record", side_effect=OSError("disk full")):
            code = run_aeg_hook_run(
                stdin=io.StringIO(self.raw("Grep", pattern="x")),
                stdout=stdout,
                stderr=io.StringIO(),
                repo_root=self.root,
                working_dir=self.root,
            )
        self.assertEqual(code, 0)
        output = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertIn("updatedInput", output)
        self.assertIn(hook_run.HOOK_DECISION_RECORDING_FAILED_REASON, output["permissionDecisionReason"])

    def test_codex_gets_the_same_input_when_a_search_reaches_it(self) -> None:
        result = self.judge("Grep", pattern="x", substrate="codex")
        self.assertEqual(result.permission_decision, "allow")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("updatedInput", self.output(result))

    def test_the_cli_writes_the_update_to_stdout(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONUTF8", "PYTHONIOENCODING", "CLAUDE_PROJECT_DIR"}}
        env["PYTHONPATH"] = str(REPO_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        done = subprocess.run(
            [sys.executable, "-m", "jangseung.cli", "hook-run"],
            input=self.raw("Grep", pattern="한글", glob="*.py").encode("utf-8"),
            capture_output=True,
            cwd=self.root,
            env=env,
            timeout=120,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        output = json.loads(done.stdout.decode("utf-8"))["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "allow")
        self.assertEqual(output["updatedInput"]["pattern"], "한글")
        self.assertTrue(output["updatedInput"]["glob"].startswith("*.py !"))


@unittest.skipUnless(shutil.which("rg"), "ripgrep is not installed")
class RipgrepBehaviourTests(_Project):
    def search(self, **tool_input) -> set[str]:
        glob = self.output(self.judge("Grep", pattern="PLACEHOLDER", **tool_input))["updatedInput"]["glob"]
        args = ["rg", "--no-config", "--hidden", "--glob", "!.git", "-l", "--null", "PLACEHOLDER"]
        for part in glob.split():
            args += ["--glob", part]
        done = subprocess.run(args, cwd=self.root, capture_output=True, timeout=60)
        # ripgrep exits 2 when the globs leave it nothing to search; Claude Code shows no matches.
        self.assertTrue(done.returncode in (0, 1) or b"No files were searched" in done.stderr, done.stderr)
        return {os.path.relpath(name, ".").replace("\\", "/") for name in done.stdout.decode("utf-8").split("\0") if name}

    def test_ripgrep_leaves_the_protected_files_out(self) -> None:
        (self.root / ".gitignore").write_text(".env\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], capture_output=True, check=False)
        (self.root / ".aws").mkdir()
        (self.root / ".aws" / "credentials").write_text("PLACEHOLDER=dummy\n", encoding="utf-8")
        for tool_input in ({}, {"glob": "*"}, {"glob": ".en*"}, {"glob": "?env"}, {"glob": ".*"}):
            with self.subTest(tool_input=tool_input):
                found = self.search(**tool_input)
                self.assertFalse({".env", "api/.env", ".aws/credentials", ".env.example"} & found, found)
        self.assertTrue({"README.md", "app.py", "docs/a.md"} <= self.search())

    def test_ripgrep_still_searches_a_file_it_is_handed(self) -> None:
        # What lets a person's approved file and a template be searched by naming them.
        glob = self.output(self.judge("Grep", pattern="x"))["updatedInput"]["glob"]
        args = ["rg", "--no-config", "--hidden", "-l", "PLACEHOLDER"]
        for part in glob.split():
            args += ["--glob", part]
        done = subprocess.run([*args, ".env.example"], cwd=self.root, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(b".env.example", done.stdout)


class PathSpellingTests(_Project):
    """Claude Code hands Grep's ``path`` over raw and resolves it after the hook has judged it."""

    HOST_RESOLVED = (
        "~", "~/", "~/x", "~\\x", " ~", "\ufeff~", "~/README.md",
        "C:", "C:.", "C:..", "C:docs", "c:docs", "Z:", "Z:notes.txt", "C:..\\..\\x", "\ufeffC:docs",
    )
    SECRET_SPELLINGS = (
        "C:.env", "c:.env", "C:.aws", "C:.aws/config", "C:api/.env", "C:.ssh/known_hosts", "C:secrets/token.txt",
        "\ufeff.env", ".env\ufeff", "\ufeff.aws/config", "\ufeffapi/.env", " .env ", "\u3000.env", "\xa0.env",
        ".env.", ".env ", ".env::$DATA", ".ENV", "./.env", ".\\.env",
    )

    def test_rules_see_through_the_spelling(self) -> None:
        self.assertEqual(strip_path_decorations("C:.env"), ".env")
        self.assertEqual(strip_path_decorations("\ufeffC:.aws/config"), ".aws/config")
        self.assertEqual(strip_path_decorations("C:/x/.env"), "C:/x/.env")
        self.assertEqual(strip_path_decorations(".env\ufeff"), ".env")
        for path in ("C:.env", "\ufeff.env", "C:.aws/config", "c:secrets/token.txt"):
            with self.subTest(path=path):
                self.assertTrue(is_secret_path(path))
                self.assertTrue(is_read_protected_path(path))
                self.assertTrue(is_protected_path(path))

    def test_host_resolved_spellings_are_told_apart(self) -> None:
        for path in self.HOST_RESOLVED:
            with self.subTest(path=path):
                self.assertTrue(is_host_resolved_path(path))
        for path in ("~name", "docs/~", "README.md", ".", "C:/x", "C:\\x", "/etc", "b/c.txt", ""):
            with self.subTest(path=path):
                self.assertFalse(is_host_resolved_path(path))

    def test_every_path_tool_denies_them(self) -> None:
        for spelling in (*self.HOST_RESOLVED, *self.SECRET_SPELLINGS):
            for tool, tool_input in (
                ("Grep", {"pattern": "x", "path": spelling}),
                ("Glob", {"pattern": "*", "path": spelling}),
                ("Read", {"file_path": spelling}),
                ("Write", {"file_path": spelling, "content": "x"}),
                ("Edit", {"file_path": spelling, "old_string": "a", "new_string": "b"}),
                ("MultiEdit", {"file_path": spelling, "edits": []}),
                ("NotebookEdit", {"notebook_path": spelling, "new_source": "x"}),
            ):
                with self.subTest(tool=tool, spelling=spelling):
                    self.assertEqual(self.judge(tool, **tool_input).permission_decision, "deny")

    def test_a_home_glob_is_denied(self) -> None:
        self.assertEqual(self.judge("Glob", pattern="~/*").permission_decision, "deny")

    def test_shell_targets_use_the_same_rule(self) -> None:
        for tool, command in (
            ("PowerShell", "Get-Content C:.env"),
            ("PowerShell", "Remove-Item C:.env"),
            ("PowerShell", "Remove-Item Z:notes.txt"),
            ("PowerShell", "Set-Content C:.aws/config x"),
            ("Bash", "rm C:.env"),
            ("Bash", "cat C:.env"),
            ("Bash", "echo x > C:.env"),
        ):
            with self.subTest(tool=tool, command=command):
                self.assertEqual(self.judge(tool, command=command).permission_decision, "deny")

    def test_a_codex_patch_cannot_use_them(self) -> None:
        for path in ("C:.env", "C:.codex/config.toml", "\ufeff.env", "~/x", "Z:notes.txt"):
            with self.subTest(path=path):
                patch = f"*** Begin Patch\n*** Update File: {path}\n@@\n-a\n+b\n*** End Patch"
                self.assertEqual(self.judge("apply_patch", command=patch, substrate="codex").permission_decision, "deny")

    def test_ordinary_paths_still_work(self) -> None:
        for path in ("README.md", "docs", "docs/a.md", ".", str(self.root), str(self.root / "README.md"), ".env.example", " README.md "):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Grep", pattern="x", path=path).permission_decision, "allow")
        for path in ("README.md", "docs/a.md", str(self.root / "README.md"), ".env.example"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Read", file_path=path).permission_decision, "allow")


class ShellWordingTests(_Project):
    """The read grammar must not allow what the shell would read differently."""

    def test_powershell_unicode_spaces_do_not_hide_an_argument(self) -> None:
        for space in ("\u00a0", "\u0085", "\u000b", "\u000c", "\u1680", "\u2003", "\u2028", "\u202f", "\u205f", "\u3000"):
            with self.subTest(space=space):
                command = f"Select-String x{space}.env{space}-Exclude README.md"
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, "deny")
                self.assertEqual(self.judge("Bash", command=f"Select-String x{space}.env{space}-Exclude README.md", substrate="codex").permission_decision, "deny")
                self.assertNotEqual(self.judge("PowerShell", command=f"Select-String x{space}README.md").permission_decision, "allow")
                self.assertNotEqual(self.judge("Bash", command=f"cat README.md{space}app.py").permission_decision, "allow")

    def test_powershell_quote_joins_do_not_hide_an_argument(self) -> None:
        (self.root / ".env-Raw").write_text("decoy\n", encoding="utf-8")
        (self.root / "README.mdapp.py").write_text("decoy\n", encoding="utf-8")
        for command in (
            "Get-Content '.env'-Raw",
            'Get-Content ".env"-Raw',
            "Get-Content '.env'.txt",
            "Get-Content 'README.md'app.py",
            "Get-Content README.md'x'",
            "Get-Content 'a''b'",
            "Select-String 'x'.env README.md",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(self.judge("PowerShell", command=command).permission_decision, "allow")
        self.assertEqual(self.judge("PowerShell", command="Get-Content '.env'-Raw").permission_decision, "deny")
        self.assertEqual(self.judge("PowerShell", command="Remove-Item '.env'-Force").permission_decision, "deny")

    def test_powershell_typographic_forms_are_not_allowed(self) -> None:
        for command in (
            "Select-String 'x\u2019 .env -Exclude' README.md",
            "Select-String \u201cx\u201d README.md",
            "Get-Content \u2018README.md\u2019",
            "Get-Content \u2013Raw README.md",
            "Get-Content \u2014Raw README.md",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(self.judge("PowerShell", command=command).permission_decision, "allow")

    def test_bash_expands_an_unquoted_glob_in_the_pattern(self) -> None:
        for command in (
            "grep -v .* README.md",
            "grep -v -e .* README.md",
            "grep -v -h .* README.md",
            "grep -v * README.md",
            "grep .e?v README.md",
            "grep [.]env README.md",
            "rg --no-config -e .* README.md",
            "grep x README.md | grep -v .*",
            "git log --grep=.*",
            "echo *",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(self.judge("Bash", command=command).permission_decision, "allow")
                self.assertEqual(self.judge("Bash", command=command, substrate="codex").permission_decision, "deny")

    def test_a_quoted_pattern_stays_allowed(self) -> None:
        for command in (
            "grep '.*' README.md",
            'grep ".*" README.md',
            "grep -v 'a*b' README.md",
            "grep -e '[.]env' README.md",
            "rg --no-config -e '.*' README.md",
            "grep x README.md",
            "git log --oneline -n 5",
            "git diff HEAD~1",
            "git show HEAD^",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.judge("Bash", command=command).permission_decision, "allow")
        for command in ("Select-String '.*' README.md", "Select-String .* README.md", "Get-Content 'README.md'", 'Select-String "a b" README.md', "Get-Content README.md | Select-String 'x'"):
            with self.subTest(command=command):
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, "allow")


class GitRepositoryTests(_Project):
    """A read-only git form proves nothing unless git uses a repository agents cannot write."""

    READ_ONLY = ("git status", "git status --short", "git diff", "git log --oneline", "git ls-files", "git --no-pager diff", "git status | Select-String x")

    def without_git_directory(self) -> None:
        (self.root / ".git").rmdir()

    def assembled_git_directory(self, where: Path) -> None:
        # Every one of these writes is ordinary to the guard outside ``.git``.
        (where / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (where / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tfsmonitor = ./run.sh\n", encoding="utf-8")
        for folder in ("objects", "refs"):
            (where / folder).mkdir()
            (where / folder / "x").write_text("x\n", encoding="utf-8")

    def test_writing_the_assembled_files_stays_allowed(self) -> None:
        self.without_git_directory()
        for path in ("HEAD", "config", "objects/x", "refs/x", "run.sh"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "allow")

    def test_git_is_not_allowed_outside_a_repository(self) -> None:
        self.without_git_directory()
        for command in self.READ_ONLY:
            with self.subTest(command=command):
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, "ask")
                self.assertEqual(self.judge("PowerShell", command=command, substrate="codex").permission_decision, "deny")
                if "Select-String" not in command:
                    self.assertEqual(self.judge("Bash", command=command).permission_decision, "ask")
                    self.assertEqual(self.judge("Bash", command=command, substrate="codex").permission_decision, "deny")

    def test_git_is_not_allowed_in_an_assembled_git_directory(self) -> None:
        self.without_git_directory()
        self.assembled_git_directory(self.root)
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                self.assertEqual(self.judge(tool, command="git status").permission_decision, "ask")

    def test_git_is_not_allowed_in_a_git_directory_assembled_below_the_repository(self) -> None:
        self.assembled_git_directory(self.root / "docs")
        self.assertEqual(self.judge("Bash", command="git status", working_dir=self.root / "docs").permission_decision, "ask")
        self.assertEqual(self.judge("Bash", command="git status").permission_decision, "allow")
        (self.root / "api" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (self.root / "api" / "commondir").write_text("../docs\n", encoding="utf-8")
        self.assertEqual(self.judge("Bash", command="git status", working_dir=self.root / "api").permission_decision, "ask")

    def test_a_head_file_beside_a_real_git_directory_changes_nothing(self) -> None:
        (self.root / "HEAD").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.judge("Bash", command="git status").permission_decision, "allow")

    def test_a_repository_above_the_working_folder_counts(self) -> None:
        self.assertEqual(self.judge("Bash", command="git status", working_dir=self.root / "docs").permission_decision, "allow")

    def test_other_read_commands_do_not_need_a_repository(self) -> None:
        self.without_git_directory()
        for tool, command in (("Bash", "ls -la"), ("Bash", "pwd"), ("Bash", "cat README.md"), ("Bash", "grep x README.md"), ("PowerShell", "Get-Content README.md"), ("PowerShell", "Get-ChildItem")):
            with self.subTest(command=command):
                self.assertEqual(self.judge(tool, command=command).permission_decision, "allow")

    def test_comparing_a_directory_is_not_allowed_even_with_a_git_directory(self) -> None:
        # git falls back to comparing paths when it refuses a repository over ownership.
        for command in (
            "git diff docs .",
            "git diff . docs",
            "git diff -- docs .",
            "git --no-pager diff docs .",
            "git diff --stat docs .",
            "git diff README.md docs",
            "git diff docs README.md",
            "git diff docs . .",
            "git diff . docs .",
            "git diff -- docs . .",
            "git --no-pager diff docs . .",
            "git diff --stat . docs README.md",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.judge("Bash", command=command).permission_decision, "ask")
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, "ask")
                self.assertEqual(self.judge("Bash", command=command, substrate="codex").permission_decision, "deny")

    def test_comparing_a_secret_is_denied(self) -> None:
        for command in ("git diff README.md .env", "git diff .env README.md", "git diff docs .aws", "git diff .aeg docs"):
            with self.subTest(command=command):
                self.assertEqual(self.judge("Bash", command=command).permission_decision, "deny")

    def test_revisions_and_plain_files_stay_allowed(self) -> None:
        for command in (
            "git diff",
            "git diff --cached",
            "git diff docs",
            "git diff main feature",
            "git diff HEAD~1 HEAD",
            "git diff HEAD -- docs",
            "git diff main -- .",
            "git diff README.md app.py",
            "git diff HEAD README.md app.py",
            "git log --oneline -n 5",
            "git show HEAD",
            "git status",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.judge("Bash", command=command).permission_decision, "allow")

    def test_the_grammar_reports_what_the_gate_needs(self) -> None:
        self.assertTrue(classify_shell_read("git status", tool_name="Bash").runs_git)
        self.assertTrue(classify_shell_read("git status | grep x", tool_name="Bash").runs_git)
        self.assertFalse(classify_shell_read("cat README.md", tool_name="Bash").runs_git)
        pair = classify_shell_read("git diff docs .", tool_name="Bash")
        self.assertEqual(pair.compared_paths, ("docs", "."))
        self.assertEqual(pair.tree_paths, ())
        self.assertEqual(classify_shell_read("git diff docs", tool_name="Bash").tree_paths, ("docs",))
        self.assertEqual(classify_shell_read("git diff a b c", tool_name="Bash").compared_paths, ("a", "b", "c"))


class GitProgramPathTests(_Project):
    """What a person's git configuration runs must not be an agent's to write."""

    def config(self, text: str) -> None:
        (self.root / ".git" / "config").write_text(text, encoding="utf-8")

    def write_decision(self, path: str) -> str:
        return self.judge("Write", file_path=path, content="x").permission_decision

    def assertProtected(self, *paths: str) -> None:
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.write_decision(path), "deny")

    def assertOrdinary(self, *paths: str) -> None:
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.write_decision(path), "allow")

    def setUp(self) -> None:
        super().setUp()
        home = self.root.parent / "home"
        home.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home), "XDG_CONFIG_HOME": str(home / "xdg")})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("GIT_CONFIG_GLOBAL", None)
        self.home = home

    def test_a_hook_folder_in_the_project_cannot_be_written(self) -> None:
        for line in ("hooksPath = .githooks", "HOOKSPATH=.githooks", 'hooksPath = ".githooks" # note', "hooksPath = .githooks/"):
            with self.subTest(line=line):
                self.config(f"[core]\n\t{line}\n")
                self.assertProtected(".githooks/post-index-change", ".githooks/sub/x", ".GITHOOKS/x")
                self.assertOrdinary("githooks/x", "README.md")
                self.assertEqual(self.judge("Read", file_path=".githooks/x").permission_decision, "allow")
        self.config("[core] hooksPath = hooks\n")
        self.assertProtected("hooks/x")
        self.config(f"[core]\n\thooksPath = {(self.root / 'tools/hooks').as_posix()}\n")
        self.assertProtected("tools/hooks/x")

    def test_shell_writes_to_a_hook_folder_are_denied(self) -> None:
        self.config("[core]\n\thooksPath = .githooks\n")
        for tool, command in (
            ("Bash", "echo x > .githooks/post-index-change"),
            ("Bash", "cp README.md .githooks/post-index-change"),
            ("PowerShell", "Set-Content .githooks/post-index-change x"),
            ("PowerShell", "Copy-Item README.md .githooks/post-index-change"),
        ):
            with self.subTest(command=command):
                self.assertEqual(self.judge(tool, command=command).permission_decision, "deny")
        patch = "*** Begin Patch\n*** Add File: .githooks/x\n+x\n*** End Patch"
        self.assertEqual(self.judge("apply_patch", command=patch, substrate="codex").permission_decision, "deny")

    def test_a_hook_folder_elsewhere_changes_nothing(self) -> None:
        for value in (".git/hooks", ".husky/_", "~/global-hooks", str(self.root.parent / "elsewhere"), "../elsewhere"):
            with self.subTest(value=value):
                self.config(f"[core]\n\thooksPath = {Path(value).as_posix()}\n")
                self.assertOrdinary("README.md", "hooks/x")

    def test_an_included_config_cannot_be_written_and_is_followed(self) -> None:
        (self.root / "dev").mkdir()
        (self.root / "dev" / "git.conf").write_text("[include]\n\tpath = more.conf\n[core]\n\tfsmonitor = ./run.sh\n", encoding="utf-8")
        (self.root / "dev" / "more.conf").write_text("[core]\n\thooksPath = dev-hooks\n", encoding="utf-8")
        self.config("[include]\n\tpath = ../dev/git.conf\n")
        self.assertProtected("dev/git.conf", "dev/more.conf", "run.sh", "dev-hooks/x")
        self.assertOrdinary("dev/other.conf")
        self.config('[includeIf "gitdir:~/work/"]\n\tpath = ../dev/more.conf\n')
        self.assertProtected("dev/more.conf", "dev-hooks/x")
        self.config("[include]\n\tpath = ../not-written-yet.conf\n")
        self.assertProtected("not-written-yet.conf")

    def test_a_program_named_in_the_config_cannot_be_written(self) -> None:
        for text, protected in (
            ("[core]\n\tfsmonitor = ./run.sh\n", "run.sh"),
            ('[filter "x"]\n\tclean = python tools/clean.py %f\n', "tools/clean.py"),
            ('[diff "x"]\n\ttextconv = ./conv.sh\n', "conv.sh"),
            ('[diff "x"]\n\tcommand = sh scripts/ext.sh\n', "scripts/ext.sh"),
            ("[diff]\n\texternal = tools/ext.sh\n", "tools/ext.sh"),
        ):
            with self.subTest(text=text):
                self.config(text)
                self.assertProtected(protected)

    def test_more_spellings_of_a_program_are_found(self) -> None:
        for text, protected in (
            ("\ufeff[core]\n\thooksPath = .githooks\n", ".githooks/x"),
            ("[foo] [core] hooksPath = .githooks\n", ".githooks/x"),
            ('[x "a]b"] [core] hooksPath = .githooks\n', ".githooks/x"),
            ("[core]\n\thooksPath = .gith\\\nooks\n", ".githooks/x"),
            ("[core]\n# note\x0c hooksPath = no\n\thooksPath = .githooks\n", ".githooks/x"),
            ('[core]\n\tfsmonitor = "sh ./run.sh"\n', "run.sh"),
            ("[core]\n\tfsmonitor = sh run.sh\n", "run.sh"),
            ('[filter "x"]\n\tclean = sh clean.sh\n', "clean.sh"),
            ("[gpg]\n\tprogram = tools/gpg.sh\n", "tools/gpg.sh"),
            ('[gpg "openpgp"]\n\tprogram = tools/gpg.sh\n', "tools/gpg.sh"),
            ("[gpg.ssh]\n\tprogram = tools/gpg.sh\n", "tools/gpg.sh"),
        ):
            with self.subTest(text=text):
                self.config(text)
                self.assertProtected(protected)
        self.config("[core]\n\thooksPath = '.githooks'\n")
        self.assertProtected("'.githooks'/x")
        self.assertOrdinary(".githooks/x")

    def test_values_that_name_no_project_file_change_nothing(self) -> None:
        self.config(
            "[core]\n\tfsmonitor = true\n\tautocrlf = input\n"
            '[filter "lfs"]\n\tclean = git-lfs clean -- %f\n\tprocess = git-lfs filter-process\n'
            '[remote "origin"]\n\turl = https://example.invalid/README.md\n'
            "[user]\n\tname = a/README.md\n"
        )
        self.assertOrdinary("README.md", "app.py")

    def test_a_linked_worktree_uses_the_shared_config(self) -> None:
        common = self.root.parent / "main.git"
        linked = common / "worktrees" / "w"
        linked.mkdir(parents=True)
        (common / "config").write_text("[core]\n\thooksPath = shared-hooks\n", encoding="utf-8")
        (linked / "config.worktree").write_text("[core]\n\tfsmonitor = ./own.sh\n", encoding="utf-8")
        (linked / "commondir").write_text("../..\n", encoding="utf-8")
        (self.root / ".git").rmdir()
        (self.root / ".git").write_text(f"gitdir: {linked.as_posix()}\n", encoding="utf-8")
        self.assertProtected("shared-hooks/x", "own.sh")

    def test_a_repository_above_and_one_in_the_working_folder_are_found(self) -> None:
        nested = self.root / "docs"
        (nested / ".git").mkdir()
        (nested / ".git" / "config").write_text("[core]\n\thooksPath = inner-hooks\n", encoding="utf-8")
        self.config("[core]\n\thooksPath = outer-hooks\n")
        self.assertEqual(git_program_paths(self.root), ("outer-hooks",))
        self.assertEqual(git_program_paths(self.root, nested), ("docs/inner-hooks",))
        self.assertEqual(git_program_paths(self.root, self.root / "api"), ("outer-hooks",))

    def test_hooks_linked_out_of_the_git_folder_cannot_be_written(self) -> None:
        (self.root / "shared-hooks").mkdir()
        (self.root / "one-hook").write_text("x\n", encoding="utf-8")
        hooks = self.root / ".git" / "hooks"
        try:
            hooks.symlink_to(self.root / "shared-hooks", target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlinks are not available: {error}")
        self.assertProtected("shared-hooks/post-index-change")
        hooks.unlink()
        hooks.mkdir()
        (hooks / "pre-commit.sample").write_text("x\n", encoding="utf-8")
        (hooks / "post-index-change").symlink_to(self.root / "one-hook")
        self.assertProtected("one-hook")
        self.assertOrdinary("shared-hooks/post-index-change")

    def test_user_level_config_counts(self) -> None:
        (self.home / ".gitconfig").write_text(f"[core]\n\thooksPath = {(self.root / 'global-hooks').as_posix()}\n", encoding="utf-8")
        self.assertProtected("global-hooks/x")
        (self.home / ".gitconfig").unlink()
        (self.home / "xdg" / "git").mkdir(parents=True)
        (self.home / "xdg" / "git" / "config").write_text(f'[includeIf "gitdir:x"]\n\tpath = {(self.root / "dev.conf").as_posix()}\n', encoding="utf-8")
        self.assertProtected("dev.conf")

    def test_nothing_is_protected_without_a_repository(self) -> None:
        (self.root / ".git").rmdir()
        self.assertEqual(git_program_paths(self.root), ())

    def test_damaged_or_huge_config_changes_nothing(self) -> None:
        for text in ("\x00\xff not config", "[core\n\thooksPath", "[core]\n\thooksPath =\n", "[core]\n\thooksPath = 'unclosed .githooks\n"):
            with self.subTest(text=text):
                self.config(text)
                self.assertEqual(self.write_decision("README.md"), "allow")
        self.config("[core]\n\thooksPath = big-hooks\n" + "# padding\n" * 200_000)
        self.assertEqual(git_program_paths(self.root), ())

    def test_a_config_include_loop_ends(self) -> None:
        (self.root / "a.conf").write_text("[include]\n\tpath = b.conf\n", encoding="utf-8")
        (self.root / "b.conf").write_text("[include]\n\tpath = a.conf\n", encoding="utf-8")
        self.config("[include]\n\tpath = ../a.conf\n")
        self.assertProtected("a.conf", "b.conf")

    def test_a_person_cannot_open_them_through_the_policy(self) -> None:
        self.config("[core]\n\thooksPath = .githooks\n")
        (self.root / ".aeg" / "policy.json").write_text(json.dumps({"allow_paths": [".githooks"]}), encoding="utf-8")
        self.assertProtected(".githooks/x")

    def test_a_broken_policy_file_keeps_the_protection(self) -> None:
        self.config("[core]\n\thooksPath = .githooks\n")
        (self.root / ".aeg" / "policy.json").write_text("{", encoding="utf-8")
        self.assertProtected(".githooks/x")
        self.assertIsNotNone(load_hook_policy(self.root).error)


class GitOutputTests(_Project):
    """What ``git diff``, ``git show`` and ``git log -p`` print cannot be judged from the request."""

    TAIL = " ".join(f"'{spec}'" for spec in git_exclusion_pathspecs())

    def updated(self, command: str, tool: str = "Bash", **kwargs) -> str | None:
        output = self.output(self.judge(tool, command=command, **kwargs))
        self.assertEqual(output["permissionDecision"], "allow", command)
        return output.get("updatedInput", {}).get("command")

    def test_commands_that_can_print_files_get_the_exclusions(self) -> None:
        for command, rebuilt in (
            ("git diff", "git diff"),
            ("git diff --cached", "git diff --cached"),
            ("git diff -q", "git diff -q"),
            ("git --no-pager diff", "git --no-pager diff"),
            ("git diff -U3", "git diff -U3"),
            ("git diff --unified=3", "git diff --unified=3"),
            ("git diff --word-diff", "git diff --word-diff"),
            ("git diff --check", "git diff --check"),
            ("git diff --stat -p", "git diff --stat -p"),
            ("git diff HEAD~1", "git diff HEAD~1"),
            ("git diff main..feature", "git diff main..feature"),
            ("git diff main...feature", "git diff main...feature"),
            ("git diff main feature", "git diff main feature"),
        ):
            with self.subTest(command=command):
                self.assertEqual(self.updated(command), f"{rebuilt} -- ':/' {self.TAIL}")
                self.assertEqual(self.updated(command, "PowerShell"), f"{rebuilt} -- ':/' {self.TAIL}")

    def test_log_and_show_keep_every_commit_when_no_path_was_asked_for(self) -> None:
        for command, rebuilt in (
            ("git show", "git show --full-history --sparse"),
            ("git show HEAD", "git show --full-history --sparse HEAD"),
            ("git show --format=%h HEAD", "git show --format=%h --full-history --sparse HEAD"),
            ("git log -p", "git log -p --full-history --sparse"),
            ("git log --patch", "git log --patch --full-history --sparse"),
            ("git log -p -n 3", "git log -p -n 3 --full-history --sparse"),
            ("git log -p -3 --all", "git log -p -3 --all --full-history --sparse"),
            ("git log --word-diff", "git log --word-diff --full-history --sparse"),
            ("git log --color-words", "git log --color-words --full-history --sparse"),
            ("git log --check", "git log --check --full-history --sparse"),
            ("git log --patience", "git log --patience --full-history --sparse"),
        ):
            with self.subTest(command=command):
                self.assertEqual(self.updated(command), f"{rebuilt} -- ':/' {self.TAIL}")
        self.assertEqual(self.updated("git log -p docs"), f"git log -p -- docs {self.TAIL}")

    def test_other_fields_come_back_unchanged(self) -> None:
        output = self.output(self.judge("Bash", command="git diff", description="show changes", timeout=5000))
        self.assertEqual(output["updatedInput"]["description"], "show changes")
        self.assertEqual(output["updatedInput"]["timeout"], 5000)

    def test_commands_that_print_only_names_are_left_alone(self) -> None:
        for command in (
            "git diff --stat", "git diff --stat=80", "git diff --numstat", "git diff --shortstat", "git diff --name-only",
            "git diff --name-status", "git diff --summary", "git diff --raw", "git diff --no-patch", "git diff --quiet",
            "git show --stat", "git show --stat HEAD", "git show --no-patch", "git show --name-only HEAD",
            "git log", "git log --oneline", "git log --stat", "git log --raw", "git log --name-only", "git log --format=%h", "git log --oneline -n 5",
            "git log --follow --oneline README.md",
            "git status", "git status --short", "git blame README.md", "git ls-files", "git branch", "git rev-parse HEAD",
        ):
            with self.subTest(command=command):
                self.assertIsNone(self.updated(command))

    def test_paths_are_told_from_revisions_by_what_exists(self) -> None:
        self.assertEqual(self.updated("git diff docs"), f"git diff -- docs {self.TAIL}")
        self.assertEqual(self.updated("git diff HEAD docs"), f"git diff HEAD -- docs {self.TAIL}")
        self.assertEqual(self.updated("git diff HEAD -- docs"), f"git diff HEAD -- docs {self.TAIL}")
        self.assertEqual(self.updated("git diff -- docs"), f"git diff -- docs {self.TAIL}")
        self.assertEqual(self.updated("git diff not-a-path"), f"git diff not-a-path -- ':/' {self.TAIL}")

    def test_a_named_file_keeps_the_exclusions_for_its_past(self) -> None:
        # A regular file today can be a folder of secrets in history.
        self.assertEqual(self.updated("git diff README.md"), f"git diff -- README.md {self.TAIL}")
        self.assertEqual(self.updated("git log -p -- README.md"), f"git log -p -- README.md {self.TAIL}")
        self.assertEqual(self.updated("git show HEAD -- README.md"), f"git show HEAD -- README.md {self.TAIL}")

    def test_a_named_template_is_not_hidden_by_its_own_rule(self) -> None:
        command = self.updated("git diff .env.example")
        self.assertTrue(command.startswith("git diff -- .env.example "), command)
        self.assertNotIn("**/.env.*'", command)
        self.assertIn("**/.env'", command)
        self.assertIn("**/*.pem'", command)

    def test_follow_cannot_be_narrowed_when_it_prints_files(self) -> None:
        for command in ("git log --follow -p README.md", "git log --follow -p -- README.md", "git log -p --follow docs"):
            with self.subTest(command=command):
                self.assertEqual(self.judge("Bash", command=command).permission_decision, "ask")
                self.assertEqual(self.judge("Bash", command=command, substrate="codex").permission_decision, "deny")

    def test_an_object_id_must_be_a_commit(self) -> None:
        for command, rebuilt in (
            ("git show e5943a1", "git show --full-history --sparse 'e5943a1^{commit}'"),
            ("git show E5943A1", "git show --full-history --sparse 'E5943A1^{commit}'"),
            ("git show x-1-ge5943a1", "git show --full-history --sparse 'x-1-ge5943a1^{commit}'"),
            ("git show v1.0-3-ge5943a1", "git show --full-history --sparse 'v1.0-3-ge5943a1^{commit}'"),
            ("git diff e5943a1 8be3e04", "git diff 'e5943a1^{commit}' '8be3e04^{commit}'"),
            ("git diff x-1-ge5943a1 HEAD", "git diff 'x-1-ge5943a1^{commit}' HEAD"),
            ("git diff e5943a1..8be3e04", "git diff 'e5943a1^{commit}..8be3e04^{commit}'"),
            ("git diff e5943a1...8be3e04", "git diff 'e5943a1^{commit}...8be3e04^{commit}'"),
            ("git diff x-1-ge5943a1..HEAD", "git diff 'x-1-ge5943a1^{commit}..HEAD'"),
            ("git show e5943a1~1", "git show --full-history --sparse 'e5943a1^{commit}~1'"),
            ("git show e5943a1^", "git show --full-history --sparse 'e5943a1^{commit}^'"),
            ("git diff ..e5943a1", "git diff '..e5943a1^{commit}'"),
            ("git diff e5943a1..", "git diff 'e5943a1^{commit}..'"),
            ("git log -p ^e5943a1 HEAD", "git log -p --full-history --sparse '^e5943a1^{commit}' HEAD"),
            ("git log -p e5943a1", "git log -p --full-history --sparse 'e5943a1^{commit}'"),
        ):
            with self.subTest(command=command):
                self.assertEqual(self.updated(command), f"{rebuilt} -- ':/' {self.TAIL}")
        self.assertEqual(self.updated("git show e5943a1 -- README.md"), f"git show 'e5943a1^{{commit}}' -- README.md {self.TAIL}")
        for name in ("HEAD~1", "v1.2.3", "release-2024", "feature/abcd", "main", "abc", "ghijk", "main..feature", "tag-gxyz"):
            with self.subTest(name=name):
                self.assertEqual(self.updated(f"git diff {name}"), f"git diff {name} -- ':/' {self.TAIL}")

    def test_git_show_peels_an_object_id_whatever_its_options(self) -> None:
        for command, rebuilt in (
            ("git show --stat e5943a1", "git show --stat 'e5943a1^{commit}'"),
            ("git show --stat x-1-ge5943a1", "git show --stat 'x-1-ge5943a1^{commit}'"),
            ("git show --no-patch e5943a1", "git show --no-patch 'e5943a1^{commit}'"),
            ("git show --name-only e5943a1 | head -n 1", "git show --name-only 'e5943a1^{commit}' | head -n 1"),
        ):
            with self.subTest(command=command):
                self.assertEqual(self.updated(command), rebuilt)
        self.assertEqual(self.updated("git show --stat docs"), "git show --stat -- docs")

    def test_git_show_does_not_take_every_ref(self) -> None:
        for flag in ("--all", "--branches", "--tags", "--remotes"):
            with self.subTest(flag=flag):
                self.assertEqual(self.judge("Bash", command=f"git show {flag}").permission_decision, "ask")
        self.assertIsNotNone(self.updated("git log -p --all"))

    def test_a_pipeline_keeps_its_other_segments(self) -> None:
        self.assertEqual(self.updated("git diff | head -n 5"), f"git diff -- ':/' {self.TAIL} | head -n 5")
        self.assertEqual(self.updated("git log -p | grep x"), f"git log -p --full-history --sparse -- ':/' {self.TAIL} | grep x")
        self.assertEqual(
            self.updated("git diff | Select-Object -First 5", "PowerShell"),
            f"git diff -- ':/' {self.TAIL} | Select-Object -First 5",
        )

    def test_a_word_that_cannot_be_quoted_is_not_allowed(self) -> None:
        self.assertEqual(self.judge("Bash", command="git log -p \"--format=a'b\"").permission_decision, "ask")
        self.assertEqual(self.judge("Bash", command="git log -p '--format=a\"b'").permission_decision, "ask")

    def test_a_named_secret_is_still_denied(self) -> None:
        for command in ("git diff .env", "git diff -- .env", "git log -p -- .env", "git show HEAD -- api/.env", "git diff HEAD .aeg"):
            with self.subTest(command=command):
                output = self.output(self.judge("Bash", command=command))
                self.assertEqual(output["permissionDecision"], "deny")
                self.assertNotIn("updatedInput", output)

    def test_no_repository_or_a_compared_folder_stays_with_a_person(self) -> None:
        output = self.output(self.judge("Bash", command="git diff docs ."))
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertNotIn("updatedInput", output)
        (self.root / ".git").rmdir()
        output = self.output(self.judge("Bash", command="git diff"))
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertNotIn("updatedInput", output)

    def test_codex_gets_the_same_command(self) -> None:
        result = self.judge("Bash", command="git diff", substrate="codex")
        self.assertEqual(result.permission_decision, "allow")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(self.output(result)["updatedInput"]["command"], f"git diff -- ':/' {self.TAIL}")

    def test_a_word_opened_by_a_quote_must_end_at_the_closing_quote(self) -> None:
        # In PowerShell, which runs Codex's Bash tool on Windows, this is two words.
        for command in ("git log '--format=%h'-p", "git log \"--format=%h\"-p", "git show '--format=%h'x HEAD", "cat 'README.md'x", "grep 'x'y README.md", "git log '--format=%h''-p'"):
            with self.subTest(command=command):
                self.assertNotEqual(self.judge("Bash", command=command).permission_decision, "allow")
        for command in ("git show '--format=%h\u2019 HEAD:.env \u2018HEAD'", "git log \u2018--format=%h\u2019 -p", "cat \u201cREADME.md\u201d"):
            with self.subTest(command=command):
                self.assertNotEqual(self.judge("Bash", command=command).permission_decision, "allow")

    def test_quotes_inside_a_word_stay_allowed_in_bash(self) -> None:
        self.assertIsNone(self.updated("git log --format='%h %s'"))
        self.assertIsNone(self.updated('git log --format="%h %s"'))
        self.assertIsNone(self.updated("git log --format='%h %s' | head -n 3"))
        self.assertIsNone(self.updated("grep 'x y' README.md"))

    def test_the_reason_names_it_and_the_command_stays_out_of_the_ledger(self) -> None:
        self.assertIn(OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON, self.judge("Bash", command="git diff").reason_codes)
        stdout = io.StringIO()
        code = run_aeg_hook_run(
            stdin=io.StringIO(self.raw("Bash", command="git log -p --author=dummy-author-text")),
            stdout=stdout,
            stderr=io.StringIO(),
            repo_root=self.root,
            working_dir=self.root,
        )
        self.assertEqual(code, 0)
        self.assertIn("dummy-author-text", json.loads(stdout.getvalue())["hookSpecificOutput"]["updatedInput"]["command"])
        self.assertNotIn("dummy-author-text", (self.root / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8"))

    def test_the_pathspecs_cover_the_rules(self) -> None:
        specs = git_exclusion_pathspecs()
        self.assertEqual(len(specs), len(set(specs)))
        for rule in (*SECRET_FILE_NAMES, *SECRET_FILE_GLOBS, ".env.*"):
            with self.subTest(rule=rule):
                self.assertIn(f":(top,exclude,glob,icase)**/{rule}", specs)
        for name in (*SECRET_DIRECTORY_NAMES, ".aeg", "/".join(SECRET_SUBPATHS[0])):
            with self.subTest(name=name):
                self.assertIn(f":(top,exclude,glob,icase)**/{name}", specs)
                self.assertIn(f":(top,exclude,glob,icase)**/{name}/**", specs)
        for word in specs:
            self.assertNotIn("'", word)

    def test_policy_reopens_a_whole_file_rule_only(self) -> None:
        (self.root / ".aeg" / "policy.json").write_text(json.dumps({"allow_paths": [".env", ".env.local"]}), encoding="utf-8")
        command = self.updated("git diff")
        self.assertNotIn("**/.env'", command)
        self.assertIn("**/.env.*'", command)
        self.assertIn("**/.aeg'", command)

    def test_policy_does_not_reopen_a_folder_rule(self) -> None:
        for approved in ("secrets", ".aws", ".docker", ".docker/config.json"):
            with self.subTest(approved=approved):
                (self.root / ".aeg" / "policy.json").write_text(json.dumps({"allow_paths": [approved]}), encoding="utf-8")
                self.assertEqual(self.updated("git diff"), f"git diff -- ':/' {self.TAIL}")
                self.assertEqual(self.output(self.judge("Grep", pattern="x"))["updatedInput"]["glob"], " ".join(EXCLUSIONS))


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GitOutputWithRealGitTests(_Project):
    MARK = "dummy-marker-7f3a"

    def git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
            cwd=cwd or self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(self.root.parent / "no-global-config")},
            timeout=60,
        )

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def setUp(self) -> None:
        super().setUp()
        self.git("init", "-q")
        secret = f"S={self.MARK}\n"
        for relative in (".env", "api/.ENV.local", ".env.production", "keys/server.PEM", ".aws/credentials", "deep/secrets/x.txt", ".docker/config.json", "id_rsa"):
            self.write(relative, secret)
        for relative in ("README.md", "docs/a.md", "src/.envoy", "docker/config.json", "src/secretary.md"):
            self.write(relative, "v1 visible-note\n")
        self.git("add", "-A", "--force")
        self.git("commit", "-q", "-m", "first")
        # In history only: added, then untracked and gone from the working tree.
        self.write("old.pem", secret)
        self.git("add", "old.pem")
        self.git("commit", "-q", "-m", "second")
        self.git("rm", "-q", "old.pem")
        self.write("README.md", "v2 visible-note\n")
        self.write(".env", f"S={self.MARK}\nT={self.MARK}\n")
        self.git("add", "README.md", ".env")
        self.git("commit", "-q", "-m", "third")
        # Changed, staged and unstaged.
        self.write(".env", f"S={self.MARK}\nT={self.MARK}\nU={self.MARK}\n")
        self.write("README.md", "v3 visible-note\n")
        self.write("api/.ENV.local", f"S={self.MARK}\nV={self.MARK}\n")
        self.git("add", "api/.ENV.local")

    def rewritten(self, command: str, working_dir: Path | None = None) -> str:
        return self.output(self.judge("Bash", command=command, working_dir=working_dir or self.root))["updatedInput"]["command"]

    def run_rewritten(self, command: str, working_dir: Path | None = None) -> subprocess.CompletedProcess:
        return self.git(*shlex.split(self.rewritten(command, working_dir))[1:], cwd=working_dir)

    def subjects(self, done: subprocess.CompletedProcess) -> list[str]:
        return [line.strip() for line in done.stdout.splitlines() if line.startswith("    ")]

    def test_the_commands_print_secrets_without_the_exclusions(self) -> None:
        # The control: this repository really does put the value in each output.
        for args in (("diff",), ("diff", "--cached"), ("diff", "HEAD~2"), ("show", "HEAD~2"), ("log", "-p")):
            with self.subTest(args=args):
                self.assertIn(self.MARK, self.git(*args).stdout)

    def test_secrets_stay_out_of_the_output_and_other_files_stay_in(self) -> None:
        for command, visible in (
            ("git diff", True),
            ("git diff -q", True),
            ("git diff HEAD", True),
            ("git diff HEAD~2", True),
            ("git diff HEAD~2 HEAD", True),
            ("git diff HEAD~2..HEAD", True),
            ("git show", True),
            ("git show HEAD", True),
            ("git log -p", True),
            ("git log -p -n 2", True),
            ("git log -p --all", True),
            ("git log -p --word-diff", True),
            ("git diff --cached", False),
            ("git show HEAD~1", False),
        ):
            with self.subTest(command=command):
                done = self.run_rewritten(command)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertNotIn(self.MARK, done.stdout)
                self.assertEqual("visible-note" in done.stdout, visible, done.stdout)

    def test_the_rewrite_keeps_every_commit(self) -> None:
        self.git("checkout", "-q", "-b", "side")
        self.write(".env.staging", f"S={self.MARK}\n")
        self.git("add", "--force", ".env.staging")
        self.git("commit", "-q", "-m", "side secret only")
        self.git("checkout", "-q", "-")
        self.write("docs/b.md", "v1 visible-note\n")
        self.git("add", "docs/b.md")
        self.git("commit", "-q", "-m", "main change")
        self.git("merge", "-q", "--no-ff", "-m", "the merge", "side")
        for command, args in (("git log -p", ("log", "-p")), ("git log -p -n 2", ("log", "-p", "-n", "2")), ("git log -p --all", ("log", "-p", "--all"))):
            with self.subTest(command=command):
                self.assertEqual(self.subjects(self.run_rewritten(command)), self.subjects(self.git(*args)))
        for revision in ("HEAD", "HEAD^2", "side"):
            with self.subTest(revision=revision):
                done = self.run_rewritten(f"git show {revision}")
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(self.subjects(done), self.subjects(self.git("show", revision)))
                self.assertNotIn(self.MARK, done.stdout)

    def test_a_tag_keeps_its_header(self) -> None:
        self.git("tag", "-a", "v1.0", "-m", "the tag message")
        done = self.run_rewritten("git show v1.0")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("the tag message", done.stdout)
        self.assertNotIn(self.MARK, done.stdout)

    def test_the_whole_repository_is_covered_from_a_subfolder(self) -> None:
        done = self.run_rewritten("git diff", working_dir=self.root / "docs")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("v3 visible-note", done.stdout)
        self.assertNotIn(self.MARK, done.stdout)

    def test_a_folder_argument_keeps_its_meaning(self) -> None:
        self.write("docs/a.md", "v2 visible-note\n")
        self.write("docs/.env", f"S={self.MARK}\n")
        self.git("add", "--force", "docs/.env")
        self.write("docs/.env", f"S={self.MARK}\nT={self.MARK}\n")
        done = self.run_rewritten("git diff docs")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("docs/a.md", done.stdout)
        self.assertNotIn("README.md", done.stdout)
        self.assertNotIn(self.MARK, done.stdout)

    def test_a_named_file_still_works(self) -> None:
        for command in ("git diff README.md", "git log -p -- README.md", "git show HEAD -- README.md"):
            with self.subTest(command=command):
                done = self.run_rewritten(command)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("visible-note", done.stdout)

    def test_a_named_template_still_works(self) -> None:
        self.git("add", "--force", ".env.example")
        self.git("commit", "-q", "-m", "template")
        self.write(".env.example", "v2 visible-note\n")
        done = self.run_rewritten("git diff .env.example")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("v2 visible-note", done.stdout)

    def test_a_file_where_a_secret_folder_used_to_be_does_not_print_it(self) -> None:
        self.write("old-config/.env", f"S={self.MARK}\n")
        self.git("add", "--force", "old-config/.env")
        self.git("commit", "-q", "-m", "old folder")
        self.git("rm", "-q", "-r", "old-config")
        self.git("commit", "-q", "-m", "gone")
        self.write("old-config", "now a file\n")
        self.assertIn(self.MARK, self.git("log", "-p", "--", "old-config").stdout, "the control")
        done = self.run_rewritten("git log -p -- old-config")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(self.MARK, done.stdout)

    def test_a_subpath_rule_that_became_a_folder_is_excluded(self) -> None:
        self.git("rm", "-q", "--cached", ".docker/config.json")
        (self.root / ".docker" / "config.json").unlink()
        self.write(".docker/config.json/inner.txt", f"S={self.MARK}\n")
        self.git("add", "--force", ".docker")
        self.git("commit", "-q", "-m", "folder")
        done = self.run_rewritten("git show HEAD")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(self.MARK, done.stdout)

    @unittest.skipIf(os.name == "nt", "bash may be the WSL launcher on Windows")
    def test_a_pipeline_runs_in_bash(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not installed")
        done = subprocess.run([bash, "-c", self.rewritten("git diff | grep -c visible-note")], cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stdout.strip(), "2", done.stderr)

    def test_an_object_id_cannot_print_a_blob(self) -> None:
        blob = self.git("rev-parse", "--short", "HEAD~2:.env").stdout.strip()
        other = self.git("rev-parse", "--short", "HEAD:.env").stdout.strip()
        self.assertIn(self.MARK, self.git("show", blob).stdout, "the control")
        self.assertIn(self.MARK, self.git("diff", blob, other).stdout, "the control")
        self.assertIn(self.MARK, self.git("show", "--stat", blob).stdout, "the control")
        self.assertIn(self.MARK, self.git("show", f"x-1-g{blob}").stdout, "the control")
        for command in (
            f"git show {blob}",
            f"git diff {blob} {other}",
            f"git diff {blob}..{other}",
            f"git diff {blob}...{other}",
            f"git show {blob} -- README.md",
            f"git log -p {blob}",
            f"git show --stat {blob}",
            f"git show --no-patch {blob}",
            f"git show --name-only {blob}",
            f"git show --raw {blob}",
            f"git show x-1-g{blob}",
            f"git show --stat x-1-g{blob}",
            f"git show --no-patch v1.0-3-g{blob}",
            f"git diff x-1-g{blob} -- README.md",
            f"git diff x-1-g{blob}..y-2-g{other}",
        ):
            with self.subTest(command=command):
                done = self.run_rewritten(command)
                self.assertNotEqual(done.returncode, 0)
                self.assertNotIn(self.MARK, done.stdout)

    def test_a_commit_id_still_works(self) -> None:
        commit = self.git("rev-parse", "--short", "HEAD").stdout.strip()
        first = self.git("rev-parse", "--short", "HEAD~2").stdout.strip()
        for command in (f"git show {commit}", f"git log -p {commit}", f"git diff {first} {commit}", f"git diff {first}..{commit}", f"git show x-1-g{commit}"):
            with self.subTest(command=command):
                done = self.run_rewritten(command)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("visible-note", done.stdout)
                self.assertNotIn(self.MARK, done.stdout)


class GitConfigReaderTests(unittest.TestCase):
    """The reader must agree with git, or a path git honours stays writable."""

    SAMPLES = (
        "[core]\n\thooksPath = .githooks\n",
        "\ufeff[core]\n\thooksPath = .githooks\n",
        "[CORE]\n\tHOOKSPATH = .githooks\n",
        "[core] hooksPath = .githooks\n",
        "[foo] [core] hooksPath = .githooks\n",
        "[foo][core] hooksPath = .githooks\n",
        '[x "a]b"] [core] hooksPath = .githooks\n',
        '[diff "a]b"] textconv = ./conv.sh\n',
        '[diff "a\\"b"] textconv = ./conv.sh\n',
        "[core]\n\thooksPath = .gith\\\nooks\n",
        "[core]\n\thooksPath = \".githooks\"\n",
        "[core]\n\thooksPath = \".git hooks\"\n",
        "[core]\n\thooksPath = .git  hooks\n",
        "[core]\n\thooksPath = .githooks # comment\n",
        "[core]\n\thooksPath = .githooks ; comment\n",
        "[core]\n\thooksPath = '.githooks'\n",
        "[core]\n\thooksPath = \".git#hooks\"\n",
        "# comment [core]\n[core]\n\t; hooksPath = no\n\thooksPath = yes\n",
        "[core]\n# comment\x0c hooksPath = no\n\thooksPath = yes\n",
        "[core]\n# comment\u0085 hooksPath = no\n\thooksPath = yes\n",
        "[core]\r\n\thooksPath = .githooks\r\n",
        "[core]\n\tbare\n\thooksPath = yes\n",
        "[core]\n\thooksPath\n",
        "[core]\n\thooksPath =\n",
        '[core "x"]\n\thooksPath = other\n',
        "[core.x]\n\thooksPath = other\n",
        '[includeIf "gitdir:~/work/"]\n\tpath = ../x.conf\n',
        '[filter "lfs"]\n\tclean = git-lfs clean -- %f\n\tprocess = git-lfs filter-process\n\trequired = true\n',
        "[core]\n\tfsmonitor = \"sh ./run.sh\"\n",
        "[core]\n\tfsmonitor = \"tab\\there\"\n",
        "[gpg]\n\tprogram = tools/gpg.sh\n",
        "[a]\nb=1\n[a]\nb=2\n",
    )

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_it_reads_what_git_reads(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config"
            for sample in self.SAMPLES:
                with self.subTest(sample=sample):
                    config.write_bytes(sample.encode("utf-8"))
                    done = subprocess.run(["git", "config", "--file", str(config), "--list", "-z"], capture_output=True, timeout=60)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    expected = []
                    for item in done.stdout.decode("utf-8").split("\0"):
                        if item:
                            name, separator, value = item.partition("\n")
                            expected.append((name, value if separator else None))
                    read = [(name.lower() if "." not in name.rpartition(".")[0] else name, value) for name, value in config_entries(sample)]
                    self.assertEqual(read, expected)

    def test_it_stops_where_git_refuses_the_file(self) -> None:
        for sample, kept in (
            ("[core]\n\ta = 1\n1bad = 2\n\tb = 3\n", [("core.a", "1")]),
            ("[core]\n\ta = \"open\n\tb = 3\n", []),
            ("[core\n\ta = 1\n", []),
            ('[core "x\n\ta = 1\n', []),
            ("[core]\n\ta = bad\\q\n", []),
            ("[core]\n\ta b = 1\n", []),
        ):
            with self.subTest(sample=sample):
                self.assertEqual(list(config_entries(sample)), kept)

    def test_it_takes_linear_time(self) -> None:
        started = time.perf_counter()
        list(config_entries("[" * 1024 * 1024))
        list(config_entries("[core]\n" + "a = 1 # note\n" * 80_000))
        self.assertLess(time.perf_counter() - started, 5)


class PowerShellFileSearchTests(_Project):
    def test_select_string_fed_by_a_listing_is_not_allowed(self) -> None:
        for command in (
            "Get-ChildItem -Recurse | Select-String x",
            "Get-ChildItem | Select-String x",
            "get-childitem -force | select-string x",
            "gci -Recurse | sls x",
            "dir | sls x",
            "ls | Select-String x",
            "Get-ChildItem -Filter .e* | Select-String x",
            "Get-ChildItem -Recurse | Select-Object -First 5 | Select-String x",
            "Get-ChildItem -Name | Select-String x",
        ):
            with self.subTest(command=command):
                # Since 0.2.2 a wildcard that hands an existing secret file to a reading
                # command is denied outright; the others still go to a person.
                expected = "deny" if ".e*" in command else "ask"
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, expected)
                self.assertEqual(self.judge("PowerShell", command=command, substrate="codex").permission_decision, "deny")

    def test_select_string_fed_by_a_listing_that_names_a_secret_is_denied(self) -> None:
        for command in ("Get-ChildItem .aws | Select-String x", "Get-ChildItem -Filter *.pem | Select-String x"):
            with self.subTest(command=command):
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, "deny")

    def test_the_text_filters_and_listings_stay_allowed(self) -> None:
        for command in (
            "Get-Content README.md | Select-String x",
            "Select-String x README.md",
            "git status | Select-String x",
            "Get-ChildItem -Recurse",
            "Get-ChildItem -Recurse -Force",
            "Get-ChildItem | Select-Object -First 5",
            "Get-ChildItem | Measure-Object -Line",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.judge("PowerShell", command=command).permission_decision, "allow")


class LegacyDoctorMessageTests(unittest.TestCase):
    def test_the_old_command_warning_names_the_project_file_risk(self) -> None:
        check = _executable_check("claude-code hook 1", {"command": sys.executable, "args": ["-m", "src.cli", "hook-run"]})
        self.assertEqual(check.status, "FAIL")
        for word in ("src/cli.py", "src/__init__.py", "agent"):
            self.assertIn(word, check.message)
        self.assertIn("aeg install", check.fix_hint)


if __name__ == "__main__":
    unittest.main()
