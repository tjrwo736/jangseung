"""Plain ``aeg doctor``: Git, the ``.aeg`` directory and ignore rules."""

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jangseung.cli.install import _prepare_recording
from jangseung.cli.main import _cmd_doctor, main
from jangseung.contracts import SAFE_DEFAULT


REPO_ROOT = Path(__file__).resolve().parents[1]


class DoctorCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init")
        self._git("config", "user.email", "aegis@example.invalid")
        self._git("config", "user.name", "Aegis Test")
        (self.repo / ".gitignore").write_text(".aeg/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "init")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_doctor_passes_inside_prepared_repo(self):
        _prepare_recording(self.repo)

        doctor = self._aeg("doctor")

        self.assertIn("status: PASS", doctor.stdout)
        self.assertIn("overall_status: PASS", doctor.stdout)
        self.assertIn("repo_root:", doctor.stdout)
        self.assertIn("state_path:", doctor.stdout)
        self.assertIn(f"safe_default: {SAFE_DEFAULT}", doctor.stdout)
        self.assertIn("[PASS] git command available", doctor.stdout)
        self.assertIn("[PASS] inside git repo", doctor.stdout)
        self.assertIn("[PASS] repo root detected", doctor.stdout)
        self.assertIn("[PASS] HEAD SHA readable", doctor.stdout)
        self.assertIn("[PASS] tree SHA readable", doctor.stdout)
        self.assertIn("[PASS] .aeg/ exists", doctor.stdout)
        self.assertIn("[PASS] .aeg/ writable", doctor.stdout)
        self.assertIn("[PASS] .aeg/ git ignored", doctor.stdout)
        self.assertIn("[PASS] .aeg/ tracked file count", doctor.stdout)
        self.assertIn("[PASS] .env tracked file count", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)
        self.assertIn("Network access is not required", doctor.stdout)

    def test_doctor_gives_readable_failure_outside_git_repo(self):
        with tempfile.TemporaryDirectory() as outside:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT)
            doctor = subprocess.run(
                [sys.executable, "-m", "jangseung.cli", "doctor"],
                cwd=outside,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        combined = doctor.stdout + doctor.stderr
        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] inside git repo", doctor.stdout)
        self.assertIn("[FAIL] repo root detected", doctor.stdout)
        self.assertIn("fix_hint: Run aeg doctor from inside a Git repository", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)
        self.assertNotIn("Traceback", combined)

    def test_doctor_warns_when_aeg_state_is_missing_and_suggests_install(self):
        doctor = self._aeg("doctor")

        self.assertEqual(doctor.returncode, 0)
        self.assertIn("status: PASS_WITH_WARNINGS", doctor.stdout)
        self.assertIn("[WARN] .aeg/ exists", doctor.stdout)
        self.assertIn("fix_hint: Run aeg install", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)
        self.assertFalse((self.repo / ".aeg").exists())

    def test_doctor_reports_missing_git_command_readably(self):
        with patch("jangseung.state.doctor.git.git_available", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_doctor(self.repo)

        self.assertEqual(exit_code, 1)
        stdout = output.getvalue()
        self.assertIn("status: FAIL", stdout)
        self.assertIn("[FAIL] git command available", stdout)
        self.assertIn("fix_hint: Install Git", stdout)
        self.assertIn("[PASS] network not required", stdout)

    def test_doctor_reports_unwritable_aeg_state_readably(self):
        _prepare_recording(self.repo)

        with patch("jangseung.state.doctor._state_dir_writable", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_doctor(self.repo)

        self.assertEqual(exit_code, 1)
        stdout = output.getvalue()
        self.assertIn("status: FAIL", stdout)
        self.assertIn("[FAIL] .aeg/ writable", stdout)
        self.assertIn("Fix filesystem permissions or ownership", stdout)

    def test_doctor_flags_unignored_aeg_state(self):
        (self.repo / ".gitignore").write_text("", encoding="utf-8")
        (self.repo / ".aeg").mkdir()

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .aeg/ git ignored", doctor.stdout)
        self.assertIn("fix_hint: Add .aeg/ to .gitignore", doctor.stdout)

    def test_doctor_flags_tracked_aeg_state(self):
        _prepare_recording(self.repo)
        (self.repo / ".aeg" / "tracked.txt").write_text("runtime\n", encoding="utf-8")
        self._git("add", "-f", ".aeg/tracked.txt")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .aeg/ tracked file count", doctor.stdout)
        self.assertIn("tracked_count: 1", doctor.stdout)
        self.assertIn("git rm --cached -r .aeg", doctor.stdout)

    def test_doctor_flags_tracked_env_file(self):
        _prepare_recording(self.repo)
        (self.repo / ".env").write_text("PLACEHOLDER=1\n", encoding="utf-8")
        self._git("add", "-f", ".env")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .env tracked file count", doctor.stdout)
        self.assertIn("tracked_count: 1", doctor.stdout)
        self.assertIn("keep real secrets out of Git", doctor.stdout)

    def test_doctor_does_not_mention_or_touch_legacy_run_state(self):
        _prepare_recording(self.repo)
        state = self.repo / ".aeg"
        (state / "config.json").write_text('{"legacy": true}\n', encoding="utf-8")
        (state / "ledger.jsonl").write_text('{"run_id": "legacy-run"}\n', encoding="utf-8")
        (state / "runs" / "legacy-run").mkdir(parents=True)
        (state / "runs" / "legacy-run" / "evidence.json").write_text("{}\n", encoding="utf-8")
        before = self._state_hash()

        human = self._aeg("doctor")
        as_json = self._aeg("doctor", "--json")

        self.assertIn("status: PASS", human.stdout)
        self.assertEqual(json.loads(as_json.stdout)["status"], "PASS")
        removed_commands = tuple(f"aeg {name}" for name in ("init", "run", "verify"))
        for output in (human.stdout, as_json.stdout):
            for removed in ("config.json", "ledger.jsonl", "runs/", "provider", *removed_commands):
                self.assertNotIn(removed, output.replace("hook_ledger.jsonl", ""))
        self.assertEqual(self._state_hash(), before)

    def test_removed_runtime_commands_are_rejected_as_usage_errors(self):
        for command in (["init"], ["run", "fix typo in README"], ["verify"]):
            with self.subTest(command=command[0]):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    with self.assertRaises(SystemExit) as raised:
                        main(command)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("invalid choice", stderr.getvalue())

    def _state_hash(self) -> str:
        digest = hashlib.sha256()
        state = self.repo / ".aeg"
        for path in sorted(state.rglob("*"), key=lambda item: item.as_posix()):
            digest.update(path.relative_to(state).as_posix().encode("utf-8"))
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def _aeg(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "jangseung.cli", *args],
            cwd=self.repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
