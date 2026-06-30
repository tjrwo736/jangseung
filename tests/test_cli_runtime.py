import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.state.git as git_state
from src.cli.main import _cmd_run
from src.contracts import (
    CLEAN_CORE,
    GIT_STAGED,
    GIT_WORKING_TREE,
    HIGH,
    LOW,
    MEDIUM,
    NEEDS_USER_GATE,
    NO_CHANGED_FILES,
    NO_CHANGED_FILES_SOURCE,
    NOT_CHECKED,
    NOT_CHECKED_SOURCE,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CliRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init")
        self._git("config", "user.email", "aegis@example.invalid")
        self._git("config", "user.name", "Aegis Test")
        (self.repo / ".gitignore").write_text(".aeg/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test\n", encoding="utf-8")
        (self.repo / "src" / "agents").mkdir(parents=True)
        (self.repo / "src" / "agents" / "executor.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.repo / "src" / "classify").mkdir(parents=True)
        (self.repo / "src" / "classify" / "rules.py").write_text("VALUE = 1\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "init")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_low_run_and_verify(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: CLEAN_CORE", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertEqual(evidence["changed_files"], [])
        self.assertEqual(evidence["changed_files_source"], NO_CHANGED_FILES_SOURCE)
        self.assertEqual(evidence["protected_paths_touched"], [])
        self.assertFalse(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], CLEAN_CORE)
        verify = self._aeg("verify")
        self.assertIn("status: PASS", verify.stdout)
        self.assertIn("LOW risk remained CLEAN_CORE", verify.stdout)

    def test_high_run_and_verify(self):
        self._aeg("init")
        run = self._aeg("run", "merge to main and deploy")
        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], HIGH)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["changed_files_source"], NO_CHANGED_FILES_SOURCE)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertIn("law.high.requires_user_gate", evidence["status_reasons"])
        verify = self._aeg("verify")
        self.assertIn("status: PASS", verify.stdout)
        self.assertIn("HIGH risk remained NEEDS_USER_GATE", verify.stdout)

    def test_protected_working_tree_change_escalates_runtime_risk(self):
        self._aeg("init")
        (self.repo / "src" / "classify" / "rules.py").write_text("VALUE = 2\n", encoding="utf-8")

        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], HIGH)
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["changed_files"], ["src/classify/rules.py"])
        self.assertEqual(evidence["changed_files_source"], GIT_WORKING_TREE)
        self.assertEqual(evidence["protected_paths_touched"], ["src/classify/rules.py"])
        self.assertTrue(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)

        verify = self._aeg("verify")
        self.assertIn("status: PASS", verify.stdout)
        self.assertIn("impact_risk replay matched: HIGH", verify.stdout)
        self.assertIn("risk_escalation_applied replay matched: True", verify.stdout)

    def test_non_protected_working_tree_change_sets_medium_runtime_impact(self):
        self._aeg("init")
        (self.repo / "src" / "agents" / "executor.py").write_text("VALUE = 2\n", encoding="utf-8")

        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: NOT_CHECKED", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], MEDIUM)
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["changed_files"], ["src/agents/executor.py"])
        self.assertEqual(evidence["changed_files_source"], GIT_WORKING_TREE)
        self.assertEqual(evidence["protected_paths_touched"], [])
        self.assertTrue(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], NOT_CHECKED)

        verify = self._aeg("verify")
        self.assertIn("status: PASS", verify.stdout)
        self.assertIn("impact_risk replay matched: MEDIUM", verify.stdout)
        self.assertIn("law status replay matched: NOT_CHECKED", verify.stdout)

    def test_staged_changed_file_uses_staged_source(self):
        self._aeg("init")
        (self.repo / "README.md").write_text("# Test\n\nTypo fix\n", encoding="utf-8")
        self._git("add", "README.md")

        self._aeg("run", "fix typo in README")
        evidence = self._latest_evidence()
        self.assertEqual(evidence["changed_files"], ["README.md"])
        self.assertEqual(evidence["changed_files_source"], GIT_STAGED)
        self.assertEqual(evidence["impact_risk"], LOW)
        self.assertEqual(evidence["risk_level"], LOW)

    def test_changed_files_source_failure_is_not_checked(self):
        self._aeg("init")
        with patch(
            "src.cli.main.git.changed_files_with_source",
            side_effect=git_state.GitError("status unavailable"),
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = _cmd_run(self.repo, "fix typo in README")

        self.assertEqual(exit_code, 0)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["changed_files"], [])
        self.assertEqual(evidence["changed_files_source"], NOT_CHECKED_SOURCE)
        self.assertEqual(evidence["impact_risk"], NOT_CHECKED)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertEqual(evidence["status"], NOT_CHECKED)

    def test_aeg_state_is_ignored_and_no_tracked_mutation(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        tracked_status = self._git("status", "--porcelain=v1").stdout.strip()
        self.assertEqual(tracked_status, "")
        tracked_aeg = self._git("ls-files", ".aeg").stdout.strip()
        self.assertEqual(tracked_aeg, "")

    def test_verify_detects_mismatched_saved_risk_level_for_protected_path(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["changed_files"] = [".github/workflows/ci.yml"]
        evidence["changed_files_source"] = "git_working_tree"
        evidence["impact_risk"] = LOW
        evidence["risk_level"] = LOW
        evidence["protected_paths_touched"] = []
        evidence["risk_escalation_applied"] = False
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("status: FAIL", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: protected path touched but saved risk_level is LOW", verify.stdout)
        self.assertIn("risk_level mismatch", verify.stdout)

    def test_verify_rejects_missing_changed_files_source_as_not_checked(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["changed_files_source"]
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("missing required field: changed_files_source", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: NOT_CHECKED impact cannot be CLEAN_CORE", verify.stdout)

    def _aeg(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
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

    def _latest_evidence(self):
        evidence, _ = self._latest_evidence_with_path()
        return evidence

    def _latest_evidence_with_path(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        entry = json.loads(line)
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "evidence.json"
        return json.loads(path.read_text(encoding="utf-8")), path


if __name__ == "__main__":
    unittest.main()
