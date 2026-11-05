"""Regression tests for the faults the first real Codex session showed in 0.1.7."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from jangseung.cli.hook_run import render_hook_response
from jangseung.evidence.claude_code_tool_call_mapping import extract_apply_patch_targets, rewrite_apply_patch_targets

BOTH_SUBSTRATES = ("claude-code", "codex")
FORMS_NAMING_NO_PATH = (
    "git status",
    "git status --short",
    "git log",
    "git log --oneline",
    "git log -p",
    "git diff",
    "git diff --stat",
    "git show",
    "git branch -a",
    "git tag",
    "git remote -v",
    "git rev-parse HEAD",
    "git ls-files",
    "ls",
    "ls -la",
    "pwd",
)


class _Folders(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "project"
        self.other = self.base / "other-repo"
        self.plain = self.base / "plain-folder"
        for folder in (self.root / ".git", self.root / ".aeg", self.other / ".git", self.plain):
            folder.mkdir(parents=True)
        for path in (
            self.root / "notes.md",
            self.root / "sub" / "a.md",
            self.root / ".env",
            self.root / ".github" / "workflows" / "ci.yml",
            self.other / "data.md",
            self.plain / "data.md",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("PLACEHOLDER=dummy\n", encoding="utf-8")

    def judge(self, tool: str, *, cwd: Path | str | None = None, substrate: str = "codex", **tool_input):
        payload = {"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "hook_event_name": "PreToolUse"}
        if cwd is not None:
            payload["cwd"] = str(cwd)
        return render_hook_response(json.dumps(payload), repo_root=self.root, substrate=substrate, working_dir=self.root)

    def link(self, link: Path, target: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError:
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False)
        if not link.is_dir():
            self.skipTest("cannot create a folder link here")


class CommandsInAnotherFolderTests(_Folders):
    def test_a_read_naming_no_path_is_denied_outside_the_project(self) -> None:
        for folder in (self.other, self.plain):
            for command in FORMS_NAMING_NO_PATH:
                for substrate in BOTH_SUBSTRATES:
                    with self.subTest(folder=folder.name, command=command, substrate=substrate):
                        result = self.judge("Bash", cwd=folder, substrate=substrate, command=command)
                        self.assertEqual(result.permission_decision, "deny")

    def test_a_read_with_a_path_is_denied_outside_the_project_as_before(self) -> None:
        for command in ("cat data.md", "git diff data.md", "git blame data.md", "ls data.md", "grep x data.md"):
            with self.subTest(command=command):
                self.assertEqual(self.judge("Bash", cwd=self.other, command=command).permission_decision, "deny")

    def test_powershell_forms_are_denied_outside_the_project(self) -> None:
        for command in ("Get-ChildItem", "git status", "git log -p", "Get-Location"):
            for substrate in BOTH_SUBSTRATES:
                with self.subTest(command=command, substrate=substrate):
                    result = self.judge("PowerShell", cwd=self.other, substrate=substrate, command=command)
                    self.assertNotEqual(result.permission_decision, "allow")

    def test_a_folder_reached_through_dots_is_judged_where_it_lands(self) -> None:
        outside = f"{self.root}{os.sep}..{os.sep}other-repo"
        self.assertEqual(self.judge("Bash", cwd=outside, command="git log -p").permission_decision, "deny")
        inside = f"{self.root}{os.sep}sub{os.sep}.."
        self.assertEqual(self.judge("Bash", cwd=inside, command="git log -p").permission_decision, "allow")

    def test_a_relative_folder_is_read_from_the_folder_the_hook_runs_in(self) -> None:
        self.assertEqual(self.judge("Bash", cwd="../other-repo", command="git status").permission_decision, "deny")
        self.assertEqual(self.judge("Bash", cwd="sub", command="git status").permission_decision, "allow")
        self.assertEqual(self.judge("Bash", cwd=".", command="git status").permission_decision, "allow")

    def test_a_link_in_the_project_to_another_folder_is_outside(self) -> None:
        link = self.root / "linked"
        self.link(link, self.other)
        self.assertEqual(self.judge("Bash", cwd=link, command="git status --short").permission_decision, "deny")

    def test_a_folder_sharing_the_projects_name_as_a_prefix_is_outside(self) -> None:
        neighbour = self.base / "project-other"
        (neighbour / ".git").mkdir(parents=True)
        self.assertEqual(self.judge("Bash", cwd=neighbour, command="git status").permission_decision, "deny")

    def test_a_search_without_a_path_is_denied_outside_the_project(self) -> None:
        self.assertEqual(self.judge("Grep", cwd=self.other, substrate="claude-code", pattern="x").permission_decision, "deny")
        self.assertEqual(self.judge("Glob", cwd=self.other, substrate="claude-code", pattern="*").permission_decision, "deny")

    def test_the_state_folder_as_the_working_folder_is_not_auto_approved(self) -> None:
        for command in ("git status", "ls", "pwd"):
            with self.subTest(command=command):
                folder = self.root / ".aeg"
                self.assertEqual(self.judge("Bash", cwd=folder, command=command).permission_decision, "deny")
                self.assertEqual(self.judge("Bash", cwd=folder, substrate="claude-code", command=command).permission_decision, "ask")

    def test_the_same_reads_still_pass_inside_the_project(self) -> None:
        trailing = f"{self.root}{os.sep}"
        for folder in (None, self.root, trailing, self.root / "sub", self.root / ".github" / "workflows"):
            for command in FORMS_NAMING_NO_PATH:
                for substrate in BOTH_SUBSTRATES:
                    with self.subTest(folder=str(folder), command=command, substrate=substrate):
                        self.assertEqual(self.judge("Bash", cwd=folder, substrate=substrate, command=command).permission_decision, "allow")

    @unittest.skipUnless(os.name == "nt", "Windows folder names ignore case")
    def test_the_project_spelled_in_another_case_is_the_project(self) -> None:
        for folder in (str(self.root).lower(), str(self.root).upper()):
            with self.subTest(folder=folder):
                self.assertEqual(self.judge("Bash", cwd=folder, command="git status --short").permission_decision, "allow")

    def test_a_folder_in_the_project_keeps_its_read_rules(self) -> None:
        sub = self.root / "sub"
        self.assertEqual(self.judge("Bash", cwd=sub, command="cat a.md").permission_decision, "allow")
        self.assertEqual(self.judge("Bash", cwd=sub, command="cat ../.env").permission_decision, "deny")

    def test_git_output_is_still_narrowed_in_the_project(self) -> None:
        result = self.judge("Bash", cwd=self.root / "sub", command="git log -p")
        self.assertEqual(result.permission_decision, "allow")
        self.assertIn(":(top,exclude,glob,icase)", json.loads(result.stdout_json)["hookSpecificOutput"]["updatedInput"]["command"])

    def test_an_approved_command_does_not_follow_into_another_folder(self) -> None:
        (self.root / ".aeg" / "policy.json").write_text(json.dumps({"allow_commands": ["pytest"]}), encoding="utf-8")
        self.assertEqual(self.judge("Bash", cwd=self.root / "sub", command="pytest -q").permission_decision, "allow")
        for folder in (self.other, self.plain, self.root / ".aeg"):
            with self.subTest(folder=folder.name):
                self.assertEqual(self.judge("Bash", cwd=folder, command="pytest -q").permission_decision, "deny")
                self.assertEqual(self.judge("Bash", cwd=folder, substrate="claude-code", command="pytest -q").permission_decision, "ask")


def _patch(path: str, directive: str = "Update File") -> str:
    body = {"Add File": "\n+line", "Delete File": ""}.get(directive, "\n@@\n+line")
    return f"*** Begin Patch\n*** {directive}: {path}{body}\n*** End Patch"


class AbsolutePatchTargetTests(_Folders):
    def decision(self, path: str, directive: str = "Update File") -> str:
        return self.judge("apply_patch", command=_patch(path, directive)).permission_decision

    def test_a_file_in_the_project_passes_however_it_is_written(self) -> None:
        for path in (
            "notes.md",
            str(self.root / "notes.md"),
            (self.root / "notes.md").as_posix(),
            str(self.root / "sub" / "a.md"),
            str(self.root / "sub" / "new.md"),
            f"{self.root}{os.sep}sub{os.sep}..{os.sep}notes.md",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.decision(path), "allow")

    def test_every_directive_gets_the_same_reading(self) -> None:
        self.assertEqual(self.decision(str(self.root / "sub" / "new.md"), "Add File"), "allow")
        self.assertEqual(self.decision(str(self.root / "notes.md"), "Delete File"), "allow")
        move = f"*** Begin Patch\n*** Update File: {self.root / 'notes.md'}\n*** Move to: {self.root / 'sub' / 'moved.md'}\n@@\n+x\n*** End Patch"
        self.assertEqual(self.judge("apply_patch", command=move).permission_decision, "allow")

    @unittest.skipUnless(os.name == "nt", "Windows folder names ignore case")
    def test_the_project_spelled_in_another_case_is_the_project(self) -> None:
        for path in (str(self.root).lower() + "\\notes.md", str(self.root).upper() + "\\NOTES.MD"):
            with self.subTest(path=path):
                self.assertEqual(self.decision(path), "allow")

    def test_protected_files_stay_denied(self) -> None:
        for relative in (
            ".env",
            ".ENV",
            ".env.local",
            ".env::$DATA",
            ".aeg/hook_ledger.jsonl",
            ".git/config",
            ".github/workflows/ci.yml",
            ".GITHUB/workflows/CI.YML",
            ".github//workflows/ci.yml",
            ".codex/config.toml",
            ".claude/settings.json",
            ".mcp.json",
            "sub/../.env",
        ):
            for spelled in (f"{self.root}{os.sep}{relative}", f"{self.root.as_posix()}/{relative}"):
                with self.subTest(path=spelled):
                    self.assertEqual(self.decision(spelled), "deny")

    def test_a_protected_file_is_denied_under_every_directive(self) -> None:
        self.assertEqual(self.decision(str(self.root / ".env"), "Add File"), "deny")
        self.assertEqual(self.decision(str(self.root / ".env"), "Delete File"), "deny")
        move = f"*** Begin Patch\n*** Update File: notes.md\n*** Move to: {self.root / '.env'}\n@@\n+x\n*** End Patch"
        self.assertEqual(self.judge("apply_patch", command=move).permission_decision, "deny")
        away = f"*** Begin Patch\n*** Update File: {self.root / '.env'}\n*** Move to: notes-copy.md\n@@\n+x\n*** End Patch"
        self.assertEqual(self.judge("apply_patch", command=away).permission_decision, "deny")

    def test_one_protected_target_denies_the_whole_patch(self) -> None:
        patch = (
            f"*** Begin Patch\n*** Update File: {self.root / 'notes.md'}\n@@\n+x\n"
            f"*** Update File: {self.root / '.github' / 'workflows' / 'ci.yml'}\n@@\n+x\n*** End Patch"
        )
        self.assertEqual(self.judge("apply_patch", command=patch).permission_decision, "deny")

    def test_paths_outside_the_project_stay_denied(self) -> None:
        for path in (
            str(self.other / "data.md"),
            str(self.base / "project-other" / "x.md"),
            f"{self.root}{os.sep}..{os.sep}other-repo{os.sep}data.md",
            f"{self.root}{os.sep}sub{os.sep}..{os.sep}..{os.sep}outside.md",
            str(self.root),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.decision(path), "deny")

    def test_a_link_in_the_project_is_judged_where_it_lands(self) -> None:
        self.link(self.root / "out", self.other)
        self.link(self.root / "ci", self.root / ".github")
        self.assertEqual(self.decision(str(self.root / "out" / "data.md")), "deny")
        self.assertEqual(self.decision(str(self.root / "ci" / "workflows" / "ci.yml")), "deny")

    @unittest.skipUnless(os.name == "nt", "these are Windows path forms")
    def test_other_windows_forms_of_a_project_path_stay_denied(self) -> None:
        text = str(self.root)
        rest = text[2:].replace("\\", "/")
        for path in (
            "\\\\?\\" + text + "\\notes.md",
            "\\\\.\\" + text + "\\notes.md",
            "\\\\localhost\\" + text[0] + "$" + text[2:] + "\\notes.md",
            "/" + text[0].lower() + rest + "/notes.md",
            text[:2] + "notes.md",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.decision(path), "deny")

    @unittest.skipIf(os.name == "nt", "these are POSIX path forms")
    def test_other_posix_forms_of_a_project_path_stay_denied(self) -> None:
        self.assertEqual(self.decision("/" + str(self.root / "notes.md")), "deny")
        self.assertEqual(self.decision("C:\\project\\notes.md"), "deny")

    def test_the_patch_is_judged_and_never_rewritten_for_the_host(self) -> None:
        result = self.judge("apply_patch", command=_patch(str(self.root / "notes.md")))
        self.assertEqual(result.permission_decision, "allow")
        self.assertNotIn("updatedInput", json.loads(result.stdout_json)["hookSpecificOutput"])

    def test_a_write_and_a_patch_agree_on_the_same_files(self) -> None:
        for relative, expected in (("notes.md", "allow"), (".env", "deny"), (".github/workflows/ci.yml", "deny")):
            absolute = str(self.root / relative)
            with self.subTest(path=relative):
                self.assertEqual(self.judge("Write", file_path=absolute, content="x").permission_decision, expected)
                self.assertEqual(self.decision(absolute), expected)


class RewriteTargetsTests(unittest.TestCase):
    def test_only_directive_paths_change(self) -> None:
        patch = (
            "*** Begin Patch\n*** Update File: a.md\n*** Move to: b.md\n@@\n context\n-old\n+*** Update File: body.md\n"
            "*** Add File: c.md\n+new\n*** Delete File: d.md\n*** End Patch"
        )
        rewritten = rewrite_apply_patch_targets(patch, lambda path: f"x/{path}")
        self.assertEqual(
            extract_apply_patch_targets(rewritten).target_operations,
            (("delete", "x/a.md"), ("write", "x/b.md"), ("write", "x/c.md"), ("delete", "x/d.md")),
        )
        self.assertIn("+*** Update File: body.md", rewritten)

    def test_text_with_nothing_to_replace_comes_back_as_it_was(self) -> None:
        patch = "*** Begin Patch\r\n*** Update File: a.md\r\n@@\r\n+x\r\n*** End Patch\r\n"
        self.assertEqual(rewrite_apply_patch_targets(patch, lambda path: path), patch)


if __name__ == "__main__":
    unittest.main()
