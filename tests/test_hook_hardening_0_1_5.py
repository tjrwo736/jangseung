"""Regression tests for the bypasses and false denies fixed in 0.1.5."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jangseung.cli.hook_run import render_hook_response

REPO_ROOT = Path(__file__).resolve().parents[1]


def _child_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONUTF8", "PYTHONIOENCODING", "CLAUDE_PROJECT_DIR"}}
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run_hook(raw: bytes, cwd: Path, *args: str, env: dict[str, str] | None = None) -> tuple[int, str | None]:
    completed = subprocess.run(
        [sys.executable, "-m", "jangseung.cli", "hook-run", *args],
        input=raw,
        capture_output=True,
        cwd=str(cwd),
        env=env or _child_env(),
        timeout=120,
    )
    try:
        decision = json.loads(completed.stdout.decode("utf-8"))["hookSpecificOutput"]["permissionDecision"]
    except (ValueError, KeyError):
        decision = None
    return completed.returncode, decision


class _Fixture(unittest.TestCase):
    FILES = (
        ".env", ".env.example", "README.md", "app.py", "keep.txt", "docs/a.md", "api/.env",
        "pyproject.toml", "Dockerfile", "requirements.txt", ".github/workflows/ci.yml",
        "src/state/store.ts", "src/cli/index.ts", "src/components/Button.tsx", "id_rsa",
        "server.pem", ".aws/credentials", ".npmrc", "credentials.json", "jangseung/cli/x.py",
        ".claude/settings.json", ".claude/commands/x.md", ".codex/config.toml",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.root = Path(cls._tmp.name).resolve() / "project"
        (cls.root / ".git" / "hooks").mkdir(parents=True)
        (cls.root / ".aeg").mkdir()
        (cls.root / "deploy").mkdir()
        (cls.root / "build").mkdir()
        for relative in cls.FILES:
            path = cls.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")

    def judge(self, tool: str, *, substrate: str = "claude-code", working_dir: Path | None = None, **tool_input):
        raw = json.dumps(
            {"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "hook_event_name": "PreToolUse"}
        )
        kwargs = {} if working_dir is None else {"working_dir": working_dir}
        return render_hook_response(raw, repo_root=self.root, substrate=substrate, **kwargs)

    def assertDecisions(self, expected: str, tool: str, cases, **kwargs) -> None:
        for case in cases:
            tool_input = dict(case) if isinstance(case, dict) else {"command": case}
            with self.subTest(tool=tool, case=case):
                result = self.judge(tool, **tool_input, **kwargs)
                self.assertEqual(result.permission_decision, expected, result.reason_codes)

    @staticmethod
    def patch(path: str, kind: str = "Update") -> dict[str, str]:
        body = {
            "Update": f"*** Update File: {path}\n@@\n-a\n+b",
            "Delete": f"*** Delete File: {path}",
            "Add": f"*** Add File: {path}\n+x",
        }[kind]
        return {"command": f"*** Begin Patch\n{body}\n*** End Patch"}


class PowerShellBypassTests(_Fixture):
    def test_commands_hidden_behind_a_read_are_denied(self):
        self.assertDecisions("deny", "PowerShell", (
            "Get-ChildItem\nRemove-Item .env",
            "Get-ChildItem\r\nRemove-Item .env",
            "Test-Path (Remove-Item .env)",
            "dir (rm .env)",
            "ls & Remove-Item .env",
            "ls # note\nRemove-Item .env",
            "gc (Invoke-Expression 'Set-Content .env overwritten')",
        ))

    def test_unproven_powershell_is_never_auto_allowed(self):
        self.assertDecisions("ask", "PowerShell", (
            ".\\cat",
            "./ls",
            "C:/tmp/type",
            "ls & whoami",
            "Get-Content README.md\nrm keep.txt -Force",
            "Remove-Item build",
        ))

    def test_secret_and_outside_reads_are_denied(self):
        self.assertDecisions("deny", "PowerShell", (
            "Get-Content .env",
            "gc .env",
            "type .env",
            "cat .env",
            "cat .aeg/hook_ledger.jsonl",
            "Get-Content C:/Users/x/.ssh/id_rsa",
            "Get-Content ~/.ssh/id_rsa",
            "Get-Content .env > docs/leak.txt",
            "Get-Content .env | Out-File docs/leak.txt",
            "Get-ChildItem C:/Windows",
            "Get-ChildItem /etc",
        ))

    def test_provable_reads_stay_allowed_without_the_old_branch(self):
        self.assertDecisions("allow", "PowerShell", (
            "Get-Content README.md",
            "gc README.md",
            "type README.md",
            "cat README.md",
            "Get-Content pyproject.toml",
            "Get-ChildItem",
            "Get-ChildItem docs",
            "gci -Recurse docs",
            "dir",
            "ls",
            "Test-Path README.md",
            "Test-Path .env",
            r"Get-ChildItem .github\workflows\ ",
            "Get-Content README.md | Select-Object -First 5",
            "git status",
        ))
        for command in ("Get-ChildItem", "Get-Content README.md"):
            result = self.judge("PowerShell", command=command)
            self.assertNotIn("powershell_read_only_maps_to_allow_without_path_deny", result.reason_codes)

    def test_write_aliases_and_dangerous_commands_are_denied(self):
        self.assertDecisions("deny", "PowerShell", (
            "ri .env",
            "erase .env",
            "sc .env x",
            "ac .env x",
            "Add-Content .env x",
            "Clear-Content .env",
            "New-Item .env",
            "Rename-Item .env y",
            "mv .env y",
            "cp docs/a.md .env",
            "Remove-Item -Recurse -Force build",
            "rm -r -fo build",
            "git push",
            "git reset --hard",
            "iwr http://example.invalid",
            "pwsh -EncodedCommand abc",
            "Get-ChildItem env:",
        ))


class GuardSelfProtectionTests(_Fixture):
    PROTECTED = (
        ".claude/settings.json", ".claude/settings.local.json", ".claude/hooks/x.py",
        ".codex/config.toml", ".mcp.json", ".git/hooks/pre-commit", ".git/config", ".husky/pre-commit",
    )

    def test_guard_configuration_cannot_be_rewritten(self):
        for path in self.PROTECTED:
            with self.subTest(path=path):
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "deny")
                self.assertEqual(
                    self.judge("Edit", file_path=str(self.root / path), old_string="a", new_string="b").permission_decision,
                    "deny",
                )
                self.assertEqual(self.judge("apply_patch", substrate="codex", **self.patch(path)).permission_decision, "deny")
        self.assertEqual(
            self.judge("apply_patch", substrate="codex", **self.patch(".codex/config.toml", "Delete")).permission_decision,
            "deny",
        )

    def test_agent_authored_claude_content_stays_editable(self):
        for path in (".claude/commands/x.md", ".claude/agents/y.md", ".claude/skills/z/SKILL.md"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "allow")

    def test_guard_commands_cannot_disable_it(self):
        self.assertDecisions("deny", "Bash", (
            "aeg uninstall --yes",
            "aeg evidence repair-hooks --yes",
            "python -m jangseung.cli uninstall --yes",
            "pip uninstall -y jangseung",
            "git config core.hooksPath x",
        ))

    def test_runtime_inside_project_is_protected(self):
        with mock.patch("jangseung.evidence.hook_judgment_engine_alignment._guard_runtime_roots",
                        return_value=(self.root / "venv",)):
            self.assertEqual(self.judge("Write", file_path="venv/Scripts/aeg.py", content="x").permission_decision, "deny")
            self.assertEqual(self.judge("Bash", command="echo x > venv/Scripts/aeg.py").permission_decision, "deny")


class WorkingDirectoryTests(_Fixture):
    def test_protected_paths_stay_protected_from_a_subdirectory(self):
        workflows = self.root / ".github" / "workflows"
        self.assertEqual(self.judge("Write", file_path="ci.yml", content="x", working_dir=workflows).permission_decision, "deny")
        self.assertEqual(self.judge("Write", file_path="workflows/ci.yml", content="x", working_dir=self.root / ".github").permission_decision, "deny")
        self.assertEqual(self.judge("Write", file_path="cli/y.py", content="x", working_dir=self.root / "jangseung").permission_decision, "deny")
        self.assertEqual(self.judge("Bash", command="echo x > ci.yml", working_dir=workflows).permission_decision, "deny")
        self.assertEqual(self.judge("PowerShell", command="Set-Content ci.yml x", working_dir=workflows).permission_decision, "deny")
        self.assertEqual(self.judge("apply_patch", substrate="codex", working_dir=workflows, **self.patch("ci.yml")).permission_decision, "deny")
        self.assertEqual(self.judge("Bash", command="cat .env", working_dir=self.root / "api").permission_decision, "deny")

    def test_absolute_read_from_subdirectory_is_not_a_false_deny(self):
        result = self.judge("Read", file_path=str(self.root / "README.md"), working_dir=self.root / "docs")
        self.assertEqual(result.permission_decision, "allow", result.reason_codes)

    def test_relative_read_resolves_against_working_directory(self):
        self.assertEqual(self.judge("Read", file_path="a.md", working_dir=self.root / "docs").permission_decision, "allow")
        self.assertEqual(self.judge("Bash", command="cat a.md", working_dir=self.root / "docs").permission_decision, "allow")

    def test_payload_cwd_is_used_for_relative_targets(self):
        raw = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": "ci.yml", "content": "x"},
            "tool_use_id": "t",
            "cwd": str(self.root / ".github" / "workflows"),
        })
        self.assertEqual(render_hook_response(raw, repo_root=self.root).permission_decision, "deny")

    def test_project_root_resolution(self):
        from jangseung.cli.hook_run import resolve_hook_project_root

        workflows = self.root / ".github" / "workflows"
        self.assertEqual(resolve_hook_project_root(workflows, environ={}), self.root)
        self.assertEqual(resolve_hook_project_root(workflows, environ={"CLAUDE_PROJECT_DIR": str(self.root)}), self.root)
        self.assertEqual(resolve_hook_project_root(self.root.parent, environ={"CLAUDE_PROJECT_DIR": str(self.root)}), self.root)
        self.assertEqual(resolve_hook_project_root(workflows, environ={"CLAUDE_PROJECT_DIR": "relative/path"}), self.root)
        with tempfile.TemporaryDirectory() as plain:
            resolved = Path(plain).resolve()
            self.assertEqual(resolve_hook_project_root(resolved, environ={}), resolved)

    def test_cli_uses_project_root_for_decision_and_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / ".git").mkdir()
            (root / ".aeg").mkdir()
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            raw = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "ci.yml", "content": "x"}, "tool_use_id": "t"}).encode()
            self.assertEqual(_run_hook(raw, workflows), (2, "deny"))
            env = {**_child_env(), "CLAUDE_PROJECT_DIR": str(root)}
            self.assertEqual(_run_hook(raw, workflows, env=env), (2, "deny"))
            ledger = (root / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(ledger), 2)
            self.assertFalse((workflows / ".aeg").exists())

    def test_codex_substrate_ignores_the_claude_project_variable(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root = Path(tmp).resolve()
            (root / ".git").mkdir()
            (root / ".aeg").mkdir()
            (root / "README.md").write_text("x\n", encoding="utf-8")
            raw = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "t"}).encode()
            env = {**_child_env(), "CLAUDE_PROJECT_DIR": str(Path(other).resolve())}
            self.assertEqual(_run_hook(raw, root, "--substrate", "codex", env=env), (0, "allow"))
            self.assertEqual(_run_hook(raw, root, env=env), (2, "deny"))


class FailClosedBoundaryTests(_Fixture):
    DEEP = b'{"tool_name":"Write","tool_input":{"file_path":".env","content":"x","a":' + b"[" * 200_000 + b"]" * 200_000 + b'},"tool_use_id":"t"}'

    def test_deeply_nested_input_is_denied(self):
        result = render_hook_response(self.DEEP.decode(), repo_root=self.root)
        self.assertEqual(result.permission_decision, "deny")
        self.assertTrue(result.fail_closed)

    def test_process_boundary_denies_deep_input(self):
        self.assertEqual(_run_hook(self.DEEP, self.root), (2, "deny"))
        self.assertEqual(_run_hook(self.DEEP, self.root, "--substrate", "codex"), (0, "deny"))

    def test_unexpected_render_failure_is_denied(self):
        import io

        from jangseung.cli import hook_run

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(hook_run, "render_hook_response", side_effect=RuntimeError("boom")):
            code = hook_run.run_aeg_hook_run(
                stdin=io.StringIO("{}"), stdout=stdout, stderr=stderr, repo_root=self.root,
            )
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_unwritable_stderr_does_not_change_the_decision(self):
        import io

        from jangseung.cli import hook_run

        class Broken(io.StringIO):
            def write(self, _text):
                raise UnicodeEncodeError("cp949", "x", 0, 1, "boom")

        stdout = io.StringIO()
        raw = json.dumps({"tool_name": "Write", "tool_input": {"file_path": ".env", "content": "x"}, "tool_use_id": "t"})
        code = hook_run.run_aeg_hook_run(stdin=io.StringIO(raw), stdout=stdout, stderr=Broken(), repo_root=self.root)
        self.assertEqual(code, 2)
        self.assertIn("deny", stdout.getvalue())

    def test_entrypoint_denies_when_the_cli_cannot_load(self):
        import contextlib
        import io

        from jangseung.cli import entry

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(entry, "_load_hook_main", side_effect=ImportError("broken install")), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = entry.main(["hook-run"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny")

        stdout = io.StringIO()
        with mock.patch.object(entry, "_load_hook_main", side_effect=ImportError("broken install")), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = entry.main(["hook-run", "--substrate", "codex"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_hook_path_does_not_load_the_run_evidence_modules(self):
        script = (
            "import sys; import jangseung.cli.hook_run; "
            "loaded = [name for name in ('jangseung.state.store', 'jangseung.evidence.verify', 'jangseung.evidence.schema', "
            "'jangseung.cli.main', 'jangseung.agents') if name in sys.modules]; print(loaded)"
        )
        completed = subprocess.run([sys.executable, "-c", script], env=_child_env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(completed.stdout.strip(), "[]", completed.stderr)

    def test_invalid_substrate_argument_blocks(self):
        raw = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "t"}).encode()
        code, decision = _run_hook(raw, self.root, "--substrate", "unknown")
        self.assertEqual((code, decision), (2, None))

    def test_installed_claude_hook_blocks_on_failure(self):
        from jangseung.cli.install import build_installed_settings

        settings, already = build_installed_settings({}, "aeg", args=["hook-run"])
        self.assertFalse(already)
        hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]
        self.assertEqual(hook["onFailure"], "block")


class PathAliasTests(_Fixture):
    ALIASES = (
        ".github/./workflows/ci.yml",
        ".github//workflows/ci.yml",
        ".GITHUB/WORKFLOWS/ci.yml",
        r".github\workflows\ci.yml",
        ".ENV",
        ".env.",
        ".env ",
        ".env::$DATA",
        "./.env",
        "DOCKERFILE",
        "Dockerfile.",
        ".AEG/hook_ledger.jsonl",
        "docs/../.env",
    )

    def test_apply_patch_aliases_are_denied(self):
        for path in (".github/./workflows/ci.yml", ".github//workflows/ci.yml", ".GITHUB/WORKFLOWS/ci.yml",
                     ".ENV", "DOCKERFILE", ".env::$DATA", ".env.", "./.env", "docs/../.env", ".AEG/hook_ledger.jsonl"):
            with self.subTest(path=path):
                result = self.judge("apply_patch", substrate="codex", **self.patch(path))
                self.assertEqual(result.permission_decision, "deny", result.reason_codes)

    def test_write_edit_aliases_are_denied(self):
        for path in self.ALIASES:
            with self.subTest(path=path):
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "deny")
                self.assertEqual(self.judge("Edit", file_path=path, old_string="a", new_string="b").permission_decision, "deny")

    def test_secret_read_aliases_are_denied(self):
        for path in (".ENV", ".env.", ".env::$DATA", "./.env", "API/.ENV", ".AEG/hook_ledger.jsonl"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Read", file_path=path).permission_decision, "deny")

    def test_symlink_alias_is_denied(self):
        link = self.root / "link_to_workflows"
        try:
            link.symlink_to(self.root / ".github" / "workflows", target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        self.addCleanup(link.unlink)
        self.assertEqual(self.judge("Write", file_path="link_to_workflows/ci.yml", content="x").permission_decision, "deny")
        self.assertEqual(self.judge("apply_patch", substrate="codex", **self.patch("link_to_workflows/ci.yml")).permission_decision, "deny")

    def test_policy_helpers_normalize_aliases(self):
        from jangseung.classify import is_protected_path, is_secret_path

        for path in (".env", ".ENV", ".env.", ".env ", ".env::$DATA", "api/.env", r"api\.env", "a/./b/.env.local"):
            self.assertTrue(is_secret_path(path), path)
        for path in (".env.example", "api/.env.sample", "environment.md", "id_rsa.pub", "keys.py", "cert.crt"):
            self.assertFalse(is_secret_path(path), path)
        for path in (".github//workflows/a.yml", ".GITHUB/./WORKFLOWS/a.yml", "DOCKERFILE", ".claude/worktrees/w/.github/workflows/a.yml"):
            self.assertTrue(is_protected_path(path), path)


class SecretCoverageTests(_Fixture):
    def test_secret_files_are_denied_at_any_depth(self):
        for path in ("id_rsa", "server.pem", ".aws/credentials", ".npmrc", "credentials.json", "api/.env", "a/b/.env.prod", "certs/tls.key", "x.p12", ".netrc", ".ssh/config", "secrets/db.txt"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Read", file_path=path).permission_decision, "deny")
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "deny")
                self.assertEqual(self.judge("apply_patch", substrate="codex", **self.patch(path)).permission_decision, "deny")

    def test_secret_files_are_denied_through_shell_reads(self):
        self.assertDecisions("deny", "Bash", (
            "cat .env", "cat api/.env", "cat id_rsa", "head -n 1 server.pem", "cat .aws/credentials",
            "cat /etc/passwd", "cat .aeg/hook_ledger.jsonl", "wc -l .env", "grep x .env",
            "git diff .env", "git show HEAD:.env", "git log -p -- api/.env",
            "base64 .env", "cp .env docs/leak.txt", "less id_rsa", "cat ~/.ssh/id_rsa", "tar czf x.tgz .env",
            "python read.py --env-file=.env", "source .env",
        ))

    def test_mentioning_secrets_as_text_is_not_a_read(self):
        self.assertDecisions("allow", "Bash", (
            "grep .env README.md",
            "grep secret README.md",
            "echo .env",
            "ls -la .env",
            "test -f .env",
            "git check-ignore .env",
            "git status .env",
        ))
        self.assertDecisions("ask", "Bash", (
            "grep -r secret docs",
            "git commit -m 'stop reading .env directly'",
        ))


class FalseDenyTests(_Fixture):
    def test_other_projects_source_layout_is_not_protected(self):
        for path in ("src/state/store.ts", "src/cli/index.ts", "src/classify/a.py", "src/evidence/b.py", "src/law/c.py", "src/components/Button.tsx"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Read", file_path=path).permission_decision, "allow")
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "allow")

    def test_reading_build_configuration_is_allowed_but_writing_is_not(self):
        for path in ("pyproject.toml", "requirements.txt", "Dockerfile", ".github/workflows/ci.yml"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Read", file_path=path).permission_decision, "allow")
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "deny")
                self.assertEqual(self.judge("Bash", command=f"cat {path}").permission_decision, "allow")
        self.assertEqual(self.judge("Read", file_path=".env.example").permission_decision, "allow")
        self.assertEqual(self.judge("Write", file_path=".env.example", content="x").permission_decision, "allow")

    def test_dangerous_words_as_arguments_are_not_commands(self):
        self.assertDecisions("allow", "Bash", (
            "ls deploy",
            "grep curl README.md",
            "echo git push",
            "echo rm -rf x",
            "cat README.md",
        ))
        self.assertDecisions("ask", "Bash", (
            "python -m venv env",
            "mkdir deploy",
            "git add deploy",
            "pip install curl",
        ))


class NormalCommandTests(_Fixture):
    ALLOWED = (
        "ls", "ls -la", "ls docs", "pwd", "git status", "git status --short", "git diff", "git diff --stat",
        "git diff --cached", "git diff HEAD~1 -- docs", "git log", "git log --oneline -5", "git log -n 5",
        "git show HEAD", "git show --stat HEAD", "git branch", "git branch -a", "git rev-parse HEAD",
        "git remote -v", "git ls-files", "git blame README.md", "wc -l README.md", "grep -n x README.md",
        "git log --oneline | head -5", "cat README.md | wc -l",
    )

    def test_read_only_commands_are_allowed_on_both_substrates(self):
        self.assertDecisions("allow", "Bash", self.ALLOWED)
        self.assertDecisions("allow", "Bash", self.ALLOWED, substrate="codex")

    def test_lookalikes_are_not_allowed(self):
        self.assertDecisions("ask", "Bash", (
            "git branch new-branch",
            "git -c core.pager=x log",
            "git diff --ext-diff",
            "git log --output=x",
            "git diff --output=x",
            "git tag v1",
            "ls; touch x",
            "ls > x",
            "git status && touch x",
            "ls $(touch x)",
            "ls\ntouch x",
            "pytest",
            "npm test",
            "grep -f x README.md",
            "grep -r x .",
        ))

    def test_code_execution_stays_gated_on_codex(self):
        self.assertDecisions("deny", "Bash", ("pytest", "npm test"), substrate="codex")


class ProtectedTreeTests(_Fixture):
    def test_deleting_a_directory_holding_protected_paths_is_denied(self):
        self.assertDecisions("deny", "Bash", ("rm -r .github", "rm -r .github/workflows", "rmdir deploy", "mv .github x", "rm -r .", "git rm -r .github"))
        self.assertDecisions("deny", "PowerShell", ("rd .github", "rmdir .github", "Remove-Item .github", "Remove-Item .", "mv .github x"))
        self.assertDecisions("ask", "Bash", ("rm -r docs", "cp app.py .", "cp app.py docs", "mv app.py docs/"))

    def test_directory_change_inside_a_command_is_followed(self):
        self.assertDecisions("deny", "Bash", (
            "cd .github && echo x > workflows/ci.yml",
            "cd .github; rm workflows/ci.yml",
            "cd docs && cd .. && echo x > .env",
            "cd docs && rm ../Dockerfile",
        ))
        self.assertDecisions("deny", "PowerShell", (
            "cd .github; Set-Content workflows/ci.yml x",
            "Set-Location .github; Remove-Item workflows/ci.yml",
        ))
        self.assertDecisions("ask", "Bash", ("cd docs && echo x > a.md",))
        self.assertDecisions("ask", "PowerShell", ("cd docs; Set-Content a.md x",))

    def test_other_ci_and_container_files_are_protected(self):
        for path in (".gitlab-ci.yml", "Jenkinsfile", ".travis.yml", ".circleci/config.yml", "azure-pipelines.yml",
                     "services/api/Dockerfile", "Dockerfile.dev", "docker/app.dockerfile", "ops/docker-compose.prod.yml"):
            with self.subTest(path=path):
                self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "deny")
                self.assertEqual(self.judge("Read", file_path=path).permission_decision, "allow")

    def test_secret_names_inside_inline_code_are_denied(self):
        self.assertDecisions("deny", "Bash", (
            "python -c \"print(open('.env').read())\"",
            "python3 -c \"open('api/.env','w')\"",
            "node -e \"require('fs').readFileSync('.env')\"",
            "ruby -e 'puts File.read(\"id_rsa\")'",
        ))
        self.assertDecisions("deny", "PowerShell", ("python -c \"print(open('.env').read())\"",))
        self.assertDecisions("ask", "Bash", ("python -c \"print(1)\"", "python script.py"))


class ReadGrammarBoundaryTests(_Fixture):
    """Options that write, run programs or read other files must not get automatic allow."""

    BASH = (
        "git diff --no-index a b", "git diff --output=x", "git diff --ext-diff", "git diff -O/etc/passwd",
        "git log --output=x", "git log --ext-diff", "git show --textconv", "git show --output=x",
        "git -c core.pager=x log", "git -C . log", "git --git-dir=x log", "git grep x",
        "git blame --contents=x README.md", "git branch -a x", "git branch new", "git remote add x y",
        "git tag -d x", "git tag v1", "git stash", "git stash pop", "git worktree add x", "git rev-parse --parseopt",
        "git status --help", "git ls-files --with-tree=x", "git describe --help",
        "grep -f x README.md", "grep -r x .", "grep --include=x y README.md", "grep --file=x README.md",
        "wc --files0-from=x", "ls --help", "ls --time=x", "tail -f README.md", "head --unknown README.md",
        "sed -i 1p README.md", "sed -n 1w README.md", "sed -n 1e README.md", "sed -f x README.md",
        "rg --no-config --pre x y README.md", "rg --no-config --files", "rg x README.md",
        "cat README.md | sh", "cat README.md | python", "ls | xargs touch", "echo x | tee y",
        "test -f README.md -a -f app.py", "pwd -x", "cat -", "cat", "grep x",
    )
    POWERSHELL = (
        "Get-Content README.md -Stream x", "gc README.md -Delimiter x", "Get-Content README.md -OutVariable x",
        "gci -Exclude x", "dir -Attributes H", "ls --% x", "ls -la", "Get-ChildItem a b",
        "Get-Content Function:prompt", "Get-Content variable:x", "Get-ChildItem Cert:", "Get-ChildItem HKLM:/",
        "Get-Content .en?", "Get-Content *", "Test-Path a b", "Test-Path -IsValid x",
        "Select-String x README.md | Out-File y", "Get-Content README.md | Select-Object -ExpandProperty x",
        "Get-Content README.md | Measure-Object -Property x", "Get-Content README.md | ForEach-Object x",
        "Get-Location -Stack", "pwd x", "git log --output=x", "git -c a=b status",
    )

    def assertNeverAllowed(self, tool: str, cases, **kwargs) -> None:
        for command in cases:
            with self.subTest(tool=tool, command=command):
                self.assertNotEqual(self.judge(tool, command=command, **kwargs).permission_decision, "allow")

    def test_bash_options_outside_the_grammar_are_not_allowed(self):
        self.assertNeverAllowed("Bash", self.BASH)
        self.assertNeverAllowed("Bash", self.BASH, substrate="codex")

    def test_powershell_options_outside_the_grammar_are_not_allowed(self):
        self.assertNeverAllowed("PowerShell", self.POWERSHELL)

    def test_case_and_qualified_names_do_not_reach_a_secret(self):
        self.assertDecisions("deny", "PowerShell", (
            "GET-CONTENT .ENV",
            r"Microsoft.PowerShell.Management\Get-Content .env",
            "Get-Content ./.env",
            r"Get-Content .\.env",
            "Select-String x .env",
            "Get-Content -LiteralPath .env",
            "Get-Content -Path README.md -Path .env",
        ))
        self.assertDecisions("deny", "Bash", ("cat README.md .env", "cat ./.env", "grep x -- .env", "rg --no-config x .env", "cat /dev/stdin"))


class ToolCoverageTests(_Fixture):
    def test_search_tools_are_judged(self):
        self.assertDecisions("allow", "Grep", (
            {"pattern": "x"}, {"pattern": "x", "path": "docs"}, {"pattern": "x", "glob": "*.py"},
            {"pattern": "x", "path": ".github/workflows"},
        ))
        self.assertDecisions("deny", "Grep", (
            {"pattern": "x", "path": ".env"}, {"pattern": "x", "path": "api/.env"},
            {"pattern": "x", "glob": ".env*"}, {"pattern": "x", "glob": "**/*.pem"},
            {"pattern": "x", "path": "/etc"}, {"pattern": "x", "path": ".aeg"},
        ))
        self.assertDecisions("allow", "Glob", ({"pattern": "**/*.py"}, {"pattern": "*.md", "path": "docs"}, {"pattern": ".env*"}))
        self.assertDecisions("deny", "Glob", ({"pattern": "*", "path": "/etc"}, {"pattern": "../**"}, {"pattern": "/etc/*"}))

    def test_notebook_and_multi_edit_are_judged_as_writes(self):
        self.assertEqual(self.judge("NotebookEdit", notebook_path="nb.ipynb", new_source="x").permission_decision, "allow")
        self.assertEqual(self.judge("NotebookEdit", notebook_path=".github/workflows/a.ipynb", new_source="x").permission_decision, "deny")
        self.assertEqual(self.judge("MultiEdit", file_path="app.py", edits=[]).permission_decision, "allow")
        self.assertEqual(self.judge("MultiEdit", file_path=".env", edits=[]).permission_decision, "deny")

    def test_installed_matchers_cover_the_tools(self):
        from jangseung.cli.install import AEGIS_HOOK_MATCHER, CODEX_AEGIS_HOOK_MATCHER, WINDOWS_AEGIS_HOOK_MATCHER

        for matcher in (AEGIS_HOOK_MATCHER, WINDOWS_AEGIS_HOOK_MATCHER):
            self.assertTrue({"Write", "Edit", "MultiEdit", "NotebookEdit", "Read", "Grep", "Glob", "Bash"} <= set(matcher.split("|")))
        self.assertIn("PowerShell", WINDOWS_AEGIS_HOOK_MATCHER.split("|"))
        self.assertIn("apply_patch", CODEX_AEGIS_HOOK_MATCHER.split("|"))

    def test_unknown_tools_are_still_denied(self):
        result = self.judge("SomeNewTool", anything="x")
        self.assertEqual(result.permission_decision, "deny")
        self.assertTrue(result.fail_closed)


class DangerousCommandTests(_Fixture):
    def test_obfuscated_and_compound_forms_are_denied(self):
        self.assertDecisions("deny", "Bash", (
            "echo x>.env",
            "rm .env;ls",
            "ls\nrm .env",
            "ls && rm .env",
            "ls | tee .env",
            "sed -i s/a/b/ .env",
            "mv .env y",
            "mv Dockerfile y",
            "cp .env docs/leak.txt",
            "/bin/rm -rf x",
            "rm -fr x",
            "git -C . reset --hard",
            "git -c a=b push",
            "/usr/bin/git push",
            "bash -c 'rm -rf x'",
            "sh -c \"git push\"",
            "bash -c 'echo x > .env'",
            "eval 'rm -rf x'",
            "xargs rm -rf",
            "find . -name x -delete",
            "find . -exec rm -rf {} +",
            "git checkout -- .",
            "git clean -f",
            "git restore .",
            "git stash drop",
            "git branch -D old",
            "npm publish",
            "twine upload dist/x",
            "docker push x",
            "gh release create v1",
            "gh pr merge 1",
            "kubectl apply -f x.yml",
            "helm upgrade x y",
            "terraform apply",
            "terraform destroy",
            "npm run deploy",
            "make deploy",
            "./scripts/deploy.sh",
            "curl http://example.invalid",
            "sudo ls",
            "env",
            "printenv",
        ))

    def test_heredoc_body_is_not_a_command(self):
        command = "cat > notes.md <<'EOF'\nrm -rf x\ngit push\n.env\nEOF"
        self.assertEqual(self.judge("Bash", command=command).permission_decision, "ask")
        command = "cat > .env <<'EOF'\nx\nEOF"
        self.assertEqual(self.judge("Bash", command=command).permission_decision, "deny")

    def test_dynamic_commands_are_asked_unless_a_target_is_provable(self):
        self.assertDecisions("ask", "Bash", ("rm $X", "echo $(date)", "cat `which x`", "bash script.sh"))
        self.assertDecisions("deny", "Bash", ("echo $X > .env", "echo $(rm -rf x)"))


class EncodingTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / "한글프로젝트"
        (self.root / ".git").mkdir(parents=True)
        (self.root / ".aeg").mkdir()
        for name in ("README.md", "app.py", "보고서.md"):
            (self.root / name).write_text("x\n", encoding="utf-8")

    def _judge(self, tool: str, **tool_input) -> tuple[int, str | None]:
        raw = json.dumps({"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t"}, ensure_ascii=False).encode("utf-8")
        return _run_hook(raw, self.root)

    def test_raw_utf8_input_is_decoded_as_utf8(self):
        self.assertEqual(self._judge("Read", file_path=str(self.root / "README.md")), (0, "allow"))
        self.assertEqual(self._judge("Write", file_path=str(self.root / "app.py"), content="내용"), (0, "allow"))
        self.assertEqual(self._judge("Edit", file_path=str(self.root / "app.py"), old_string="a", new_string="b"), (0, "allow"))
        self.assertEqual(self._judge("Bash", command="cat 보고서.md"), (0, "allow"))

    def test_invalid_utf8_input_fails_closed(self):
        self.assertEqual(_run_hook(b'{"tool_name":"Read","tool_input":{"file_path":"\xff"},"tool_use_id":"t"}', self.root), (2, "deny"))

    def test_byte_order_mark_is_accepted(self):
        raw = b"\xef\xbb\xbf" + json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "t"}).encode()
        self.assertEqual(_run_hook(raw, self.root), (0, "allow"))


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".aeg").mkdir()
        self.ledger = self.root / ".aeg" / "hook_ledger.jsonl"

    def _append(self):
        from jangseung.state.hook_ledger import append_hook_decision_record

        return append_hook_decision_record(
            self.root, substrate="claude-code", tool_name="Read", hook_decision="allow",
            permission_decision="allow", fail_closed=False, reason_codes=("r",), exit_code=0,
        )

    def test_append_does_not_rescan_the_whole_chain(self):
        from jangseung.state import hook_ledger

        first = self._append()
        with mock.patch.object(hook_ledger, "verify_hook_ledger", side_effect=AssertionError("full scan")):
            second = self._append()
        self.assertEqual(second["sequence_number"], 2)
        self.assertEqual(second["previous_record_hash"], first["record_hash"])
        self.assertTrue(hook_ledger.verify_hook_ledger(self.root).ok)

    def test_damaged_tail_refuses_append_until_repaired(self):
        from jangseung.state import hook_ledger

        self._append()
        with self.ledger.open("ab") as handle:
            handle.write(b'{"record_version":"torn')
        with self.assertRaises(ValueError):
            self._append()
        report = hook_ledger.repair_hook_ledger(self.root)
        self.assertEqual(report.kept_records, 1)
        self.assertEqual(report.quarantined_lines, 1)
        self.assertTrue(Path(report.quarantine_path).is_file())
        self.assertIn(b"torn", Path(report.quarantine_path).read_bytes())
        verification = hook_ledger.verify_hook_ledger(self.root)
        self.assertTrue(verification.ok, verification.errors)
        self.assertIn("hook_ledger_repaired", verification.records[-1]["reason_codes"])
        self.assertEqual(self._append()["sequence_number"], 3)
        self.assertTrue(hook_ledger.verify_hook_ledger(self.root).ok)

    def test_middle_tampering_is_still_detected_and_quarantined(self):
        from jangseung.state import hook_ledger

        for _ in range(3):
            self._append()
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        lines[1] = lines[1].replace('"Read"', '"Edit"')
        self.ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertFalse(hook_ledger.verify_hook_ledger(self.root).ok)
        report = hook_ledger.repair_hook_ledger(self.root)
        self.assertEqual(report.kept_records, 1)
        self.assertEqual(report.quarantined_lines, 2)
        self.assertTrue(hook_ledger.verify_hook_ledger(self.root).ok)

    def test_repair_of_a_healthy_ledger_changes_nothing(self):
        from jangseung.state import hook_ledger

        self._append()
        before = self.ledger.read_bytes()
        report = hook_ledger.repair_hook_ledger(self.root)
        self.assertEqual(report.quarantined_lines, 0)
        self.assertIsNone(report.quarantine_path)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_recording_failure_keeps_the_decision(self):
        import io

        from jangseung.cli.hook_run import run_aeg_hook_run

        self.ledger.write_bytes(b"not json\n")
        stdout = io.StringIO()
        raw = json.dumps({"tool_name": "Write", "tool_input": {"file_path": ".env", "content": "x"}, "tool_use_id": "t"})
        code = run_aeg_hook_run(stdin=io.StringIO(raw), stdout=stdout, stderr=io.StringIO(), repo_root=self.root)
        self.assertEqual(code, 2)
        self.assertIn("hook_decision_recording_failed", stdout.getvalue())


class PolicyFileTests(_Fixture):
    def setUp(self) -> None:
        self.policy = self.root / ".aeg" / "policy.json"
        self.addCleanup(lambda: self.policy.unlink(missing_ok=True))

    def _write(self, **data) -> None:
        self.policy.write_text(json.dumps(data), encoding="utf-8")

    def test_allow_commands_approves_exact_prefixes_only(self):
        self._write(allow_commands=["pytest", "npm test"])
        self.assertDecisions("allow", "Bash", ("pytest", "pytest tests -q", "npm test"), substrate="codex")
        self.assertDecisions("deny", "Bash", (
            "npm publish", "pytest; rm .env", "pytest && touch x", "pytest $(touch x)", "pytest .env",
            "pytest\ntouch x", "pytest > x", "pytester",
        ), substrate="codex")

    def test_allow_commands_can_lift_a_dangerous_command_but_not_self_disable(self):
        self._write(allow_commands=["git push", "aeg uninstall", "pip uninstall"])
        self.assertEqual(self.judge("Bash", command="git push origin main").permission_decision, "allow")
        self.assertEqual(self.judge("Bash", command="aeg uninstall --yes").permission_decision, "deny")
        self.assertEqual(self.judge("Bash", command="pip uninstall -y jangseung").permission_decision, "deny")
        self.assertEqual(self.judge("Bash", command="git push > .env").permission_decision, "deny")

    def test_allow_paths_lifts_soft_protection_only(self):
        self._write(allow_paths=["pyproject.toml", "requirements*.txt", "deploy/", "tests/fixtures/*.pem", ".claude/settings.json", ".aeg/"])
        self.assertEqual(self.judge("Write", file_path="pyproject.toml", content="x").permission_decision, "allow")
        self.assertEqual(self.judge("Read", file_path="tests/fixtures/a.pem").permission_decision, "allow")
        self.assertEqual(self.judge("Write", file_path="tests/fixtures/a.pem", content="x").permission_decision, "allow")
        self.assertEqual(self.judge("Read", file_path="real.pem").permission_decision, "deny")
        self.assertEqual(self.judge("Write", file_path="requirements-dev.txt", content="x").permission_decision, "allow")
        self.assertEqual(self.judge("Write", file_path="deploy/a.yml", content="x").permission_decision, "allow")
        self.assertEqual(self.judge("Bash", command="echo x > deploy/a.yml").permission_decision, "ask")
        for path in (".env", ".claude/settings.json", ".aeg/policy.json", "Dockerfile"):
            self.assertEqual(self.judge("Write", file_path=path, content="x").permission_decision, "deny", path)

    def test_protect_paths_adds_protection(self):
        self._write(protect_paths=["infra/", "*.tfstate"])
        self.assertEqual(self.judge("Write", file_path="infra/a.tf", content="x").permission_decision, "deny")
        self.assertEqual(self.judge("Write", file_path="prod.tfstate", content="x").permission_decision, "deny")
        self.assertEqual(self.judge("Write", file_path="app.py", content="x").permission_decision, "allow")

    def test_invalid_policy_is_ignored_and_reported(self):
        from jangseung.classify.hook_policy import load_hook_policy

        for text in ("not json", "[]", '{"allow_paths": "x"}', '{"unknown": []}', '{"allow_commands": [""]}', '{"allow_commands": ["a; b"]}'):
            self.policy.write_text(text, encoding="utf-8")
            policy = load_hook_policy(self.root)
            self.assertIsNotNone(policy.error, text)
            self.assertEqual(policy.allow_commands, ())
            self.assertEqual(self.judge("Write", file_path="pyproject.toml", content="x").permission_decision, "deny")

    def test_agent_cannot_write_the_policy(self):
        self.assertEqual(self.judge("Write", file_path=".aeg/policy.json", content="{}").permission_decision, "deny")
        self.assertEqual(self.judge("Bash", command="echo {} > .aeg/policy.json").permission_decision, "deny")
        self.assertEqual(self.judge("PowerShell", command="Set-Content .aeg/policy.json x").permission_decision, "deny")


class InstallerTests(unittest.TestCase):
    def test_module_fallback_is_isolated_from_the_project(self):
        from jangseung.cli import install

        with mock.patch.object(install, "_installed_console_script", return_value=None):
            self.assertEqual(install.resolve_hook_command_parts(), (sys.executable, ("-I", "-m", "jangseung.cli", "hook-run")))
            self.assertEqual(install.resolve_windows_hook_command_parts(), (sys.executable, ("-I", "-m", "jangseung.cli", "hook-run")))

    def test_legacy_src_hooks_are_recognized_for_upgrade_and_removal(self):
        from jangseung.cli import install

        legacy = {"type": "command", "command": sys.executable, "args": ["-m", "src.cli", "hook-run"]}
        self.assertTrue(install.is_aegis_hook(legacy))
        self.assertTrue(install.is_aegis_hook({"type": "command", "command": "/venv/bin/python -m src.cli hook-run"}))
        self.assertTrue(install.is_aegis_hook({"type": "command", "command": sys.executable, "args": ["-I", "-m", "jangseung.cli", "hook-run"]}))
        self.assertFalse(install.is_aegis_hook({"type": "command", "command": "python -m other.cli hook-run"}))

    def test_reinstall_upgrades_a_stale_hook_in_place(self):
        from jangseung.cli.install import AEGIS_HOOK_MATCHER, build_installed_settings

        stale = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|Bash|Read", "hooks": [
            {"type": "command", "command": "/venv/bin/python -m src.cli hook-run", "timeout": 5},
            {"type": "command", "command": "other-hook"},
        ]}]}}
        settings, already = build_installed_settings(stale, "/venv/bin/aeg hook-run", matcher=AEGIS_HOOK_MATCHER)
        self.assertFalse(already)
        entry = settings["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], AEGIS_HOOK_MATCHER)
        self.assertEqual(entry["hooks"][0]["command"], "/venv/bin/aeg hook-run")
        self.assertEqual(entry["hooks"][0]["onFailure"], "block")
        self.assertEqual(entry["hooks"][0]["timeout"], 5)
        self.assertEqual(entry["hooks"][1], {"type": "command", "command": "other-hook"})
        again, already = build_installed_settings(settings, "/venv/bin/aeg hook-run", matcher=AEGIS_HOOK_MATCHER)
        self.assertTrue(already)
        self.assertEqual(again, settings)

    def test_project_src_package_is_no_longer_shadowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            (project / "src" / "foo.py").write_text("VALUE = 1\n", encoding="utf-8")
            env = _child_env()
            completed = subprocess.run(
                [sys.executable, "-c", "import jangseung, src.foo; print(src.foo.VALUE)"],
                cwd=project, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), "1")


class UpgradeFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()

    def test_claude_install_rewrites_a_legacy_hook_and_keeps_a_backup(self):
        import io

        from jangseung.cli.install import cmd_install

        settings = self.root / ".claude" / "settings.json"
        settings.parent.mkdir()
        legacy = {"model": "x", "hooks": {"PreToolUse": [{"matcher": "Write|Edit|Bash|Read", "hooks": [
            {"type": "command", "command": sys.executable, "args": ["-m", "src.cli", "hook-run"]},
        ]}]}}
        settings.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertEqual(cmd_install(self.root, assume_yes=True, output_stream=io.StringIO()), 0)
        data = json.loads(settings.read_text(encoding="utf-8"))
        hook = data["hooks"]["PreToolUse"][0]["hooks"][0]
        self.assertEqual(data["model"], "x")
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)
        self.assertEqual(hook["onFailure"], "block")
        self.assertNotIn("src.cli", json.dumps(hook))
        self.assertIn("Grep", data["hooks"]["PreToolUse"][0]["matcher"])
        self.assertTrue(list(settings.parent.glob("settings.json.aegis-backup-*")))

    def test_codex_install_rewrites_a_legacy_hook_and_keeps_other_settings(self):
        from jangseung.cli.install import build_installed_codex_config_text

        legacy = (
            '# keep me\nmodel = "x"\n\n[[hooks.PreToolUse]]\nmatcher = "Write|Edit|Bash|Read|apply_patch"\n\n'
            '[[hooks.PreToolUse.hooks]]\ntype = "command"\ncommand = "/venv/bin/python -m src.cli hook-run --substrate codex"\n'
        )
        updated, already = build_installed_codex_config_text(legacy, "/venv/bin/aeg hook-run --substrate codex")
        self.assertFalse(already)
        self.assertIn("# keep me", updated)
        self.assertIn('command = "/venv/bin/aeg hook-run --substrate codex"', updated)
        self.assertNotIn("src.cli", updated)
        again, already = build_installed_codex_config_text(updated, "/venv/bin/aeg hook-run --substrate codex")
        self.assertTrue(already)
        self.assertEqual(again, updated)

    def test_repair_command_quarantines_damage(self):
        import contextlib
        import io

        from jangseung.cli.main import main
        from jangseung.state.hook_ledger import append_hook_decision_record, verify_hook_ledger

        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".aeg").mkdir()
        append_hook_decision_record(
            self.root, substrate="claude-code", tool_name="Read", hook_decision="allow",
            permission_decision="allow", fail_closed=False, reason_codes=("r",), exit_code=0,
        )
        ledger = self.root / ".aeg" / "hook_ledger.jsonl"
        with ledger.open("ab") as handle:
            handle.write(b'{"torn')
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["evidence", "repair-hooks", "--yes"]), 0)
        self.assertIn("quarantined 1 line(s)", output.getvalue())
        self.assertTrue(verify_hook_ledger(self.root).ok)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["evidence", "repair-hooks", "--yes"]), 0)
        self.assertIn("nothing to repair", output.getvalue())


class DoctorTests(unittest.TestCase):
    def test_stale_hooks_are_reported(self):
        from jangseung.cli.hook_doctor import _config_checks

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
                {"matcher": "Write|Edit|Bash|Read", "hooks": [{"type": "command", "command": sys.executable, "args": ["-m", "src.cli", "hook-run"]}]}
            ]}}), encoding="utf-8")
            checks = {check.name: check for check in _config_checks(repo, "claude-code")}
        self.assertEqual(checks["claude-code hook 1 executable"].status, "FAIL")
        self.assertEqual(checks["claude-code hook 1 failure mode"].status, "WARN")
        self.assertEqual(checks["claude-code hook 1 matcher"].status, "WARN")


if __name__ == "__main__":
    unittest.main()
