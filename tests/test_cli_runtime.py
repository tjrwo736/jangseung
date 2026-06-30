import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.contracts import CLEAN_CORE, HIGH, LOW, NEEDS_USER_GATE


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
        self.assertEqual(evidence["risk_level"], LOW)
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
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertIn("law.high.requires_user_gate", evidence["status_reasons"])
        verify = self._aeg("verify")
        self.assertIn("status: PASS", verify.stdout)
        self.assertIn("HIGH risk remained NEEDS_USER_GATE", verify.stdout)

    def test_aeg_state_is_ignored_and_no_tracked_mutation(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        tracked_status = self._git("status", "--porcelain=v1").stdout.strip()
        self.assertEqual(tracked_status, "")
        tracked_aeg = self._git("ls-files", ".aeg").stdout.strip()
        self.assertEqual(tracked_aeg, "")

    def _aeg(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
            cwd=self.repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
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
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        entry = json.loads(line)
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "evidence.json"
        return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
