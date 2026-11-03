"""The hook command registered by versions up to 0.1.4 must keep protecting after an upgrade."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_MODULE = ("-m", "src.cli")


def _env(*first_on_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONUTF8", "PYTHONIOENCODING", "CLAUDE_PROJECT_DIR"}}
    env["PYTHONPATH"] = os.pathsep.join([*(str(path) for path in first_on_path), str(REPO_ROOT)])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _payload(tool_name: str, **tool_input: str) -> bytes:
    return json.dumps(
        {"tool_name": tool_name, "tool_input": tool_input, "tool_use_id": "t", "hook_event_name": "PreToolUse"}
    ).encode("utf-8")


def _legacy(cwd: Path, *args: str, raw: bytes = b"", env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *LEGACY_MODULE, *args],
        input=raw,
        capture_output=True,
        cwd=str(cwd),
        env=env or _env(),
        timeout=120,
    )


def _decision(completed: subprocess.CompletedProcess) -> str | None:
    try:
        return json.loads(completed.stdout.decode("utf-8"))["hookSpecificOutput"]["permissionDecision"]
    except (ValueError, KeyError):
        return None


class _Project(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.project = self.root / "project"
        (self.project / ".aeg").mkdir(parents=True)
        (self.project / ".env").write_text("PLACEHOLDER=1\n", encoding="utf-8")
        (self.project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    def _write_source(self, relative: str, body: str = "VALUE = 1\n") -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


class LegacyHookCommandTests(_Project):
    def test_protected_write_is_denied_on_claude_code(self):
        completed = _legacy(self.project, "hook-run", raw=_payload("Write", file_path=".env", content="x"))
        self.assertEqual((completed.returncode, _decision(completed)), (2, "deny"))
        self.assertIn("aeg install", completed.stderr.decode("utf-8"))

    def test_regular_write_is_allowed(self):
        completed = _legacy(self.project, "hook-run", raw=_payload("Write", file_path="app.py", content="x"))
        self.assertEqual((completed.returncode, _decision(completed)), (0, "allow"))

    def test_codex_form_denies_in_json(self):
        raw = _payload("Write", file_path=".env", content="x")
        completed = _legacy(self.project, "hook-run", "--substrate", "codex", raw=raw)
        self.assertEqual((completed.returncode, _decision(completed)), (0, "deny"))

    def test_decision_is_recorded_like_any_other_hook_call(self):
        _legacy(self.project, "hook-run", raw=_payload("Write", file_path=".env", content="x"))
        records = (self.project / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0])["permission_decision"], "deny")

    def test_invalid_input_is_denied(self):
        completed = _legacy(self.project, "hook-run", raw=b'{"tool_name":"\xff"}')
        self.assertEqual((completed.returncode, _decision(completed)), (2, "deny"))

    def test_broken_guard_blocks_the_tool_call(self):
        broken = self.root / "broken"
        (broken / "jangseung").mkdir(parents=True)
        (broken / "jangseung" / "__init__.py").write_text("raise RuntimeError('simulated broken install')\n", encoding="utf-8")
        raw = _payload("Write", file_path="app.py", content="x")
        completed = _legacy(self.project, "hook-run", raw=raw, env=_env(broken))
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b"")
        self.assertIn("blocked", completed.stderr.decode("utf-8"))

    def test_other_commands_are_refused(self):
        settings = self.project / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text('{"hooks": {}}', encoding="utf-8")
        for args in (("uninstall", "--yes"), ("install", "--yes"), ("--help",), ()):
            with self.subTest(args=args):
                completed = _legacy(self.project, *args)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, b"")
                self.assertIn("aeg", completed.stderr.decode("utf-8"))
        self.assertEqual(settings.read_text(encoding="utf-8"), '{"hooks": {}}')


class ProjectSrcTests(_Project):
    def _import(self, statement: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-c", statement], capture_output=True, text=True, cwd=str(self.project), env=_env(), timeout=60
        )

    def test_project_regular_src_package_is_not_shadowed(self):
        self._write_source("src/__init__.py", "")
        self._write_source("src/foo.py")
        completed = self._import("import jangseung, src, src.foo; print(src.__file__); print(src.foo.VALUE)")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        location, value = completed.stdout.split()
        self.assertEqual(Path(location).resolve(), self.project / "src" / "__init__.py")
        self.assertEqual(value, "1")

    def test_project_namespace_src_merges_with_the_compat_module(self):
        self._write_source("src/foo.py")
        self._write_source("src/cli/helper.py")
        completed = self._import("import jangseung, src.foo, src.cli.helper; print(src.foo.VALUE + src.cli.helper.VALUE)")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "2")
        hook = _legacy(self.project, "hook-run", raw=_payload("Write", file_path=".env", content="x"))
        self.assertEqual((hook.returncode, _decision(hook)), (2, "deny"))

    def test_project_module_named_src_or_src_cli_hides_the_compat_module(self):
        # The limit the release notes state: these projects need aeg install.
        for relative in ("src/__init__.py", "src/cli/__init__.py", "src/cli.py", "src.py"):
            with self.subTest(relative=relative):
                self._write_source(relative, "print('project code')\n")
                # -S keeps the finder of an editable install from resolving src.cli, which a wheel has no finder for.
                completed = subprocess.run(
                    [sys.executable, "-S", *LEGACY_MODULE, "hook-run"],
                    input=_payload("Write", file_path=".env", content="x"),
                    capture_output=True,
                    cwd=str(self.project),
                    env=_env(),
                    timeout=120,
                )
                self.assertIsNone(_decision(completed))
                shutil.rmtree(self.project / "src", ignore_errors=True)
                (self.project / "src.py").unlink(missing_ok=True)


class CompatModuleLayoutTests(unittest.TestCase):
    def test_compat_module_stays_a_namespace_package_with_one_file(self):
        src = REPO_ROOT / "src"
        self.assertEqual(sorted(path.relative_to(src).as_posix() for path in src.rglob("*.py")), ["cli/__main__.py"])


if __name__ == "__main__":
    unittest.main()
