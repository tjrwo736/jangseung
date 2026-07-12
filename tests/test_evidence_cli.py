"""Read-only evidence list/show CLI coverage."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.cli.main import _cmd_evidence_list, _cmd_evidence_show
from src.state.evidence_query import REDACTED_CREDENTIAL


class EvidenceCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.state = self.repo / ".aeg"
        self.runs = self.state / "runs"
        self.runs.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_list_is_newest_first_and_honors_limit(self):
        self._write_run("run-001", "2026-07-01T00:00:00Z", "CLEAN_CORE", "LOW")
        self._write_run("run-002", "2026-07-02T00:00:00Z", "NEEDS_USER_GATE", "HIGH")

        exit_code, output = self._capture(_cmd_evidence_list, self.repo, limit=1)

        self.assertEqual(exit_code, 0)
        self.assertIn("status: OK", output)
        self.assertIn("run-002", output)
        self.assertNotIn("run-001", output)
        self.assertIn("run:yes/evidence:yes/manifest:yes", output)

    def test_show_uses_sections_instead_of_flat_evidence_dump(self):
        self._write_run("run-sections", "2026-07-01T00:00:00Z", "CLEAN_CORE", "LOW")

        exit_code, output = self._capture(_cmd_evidence_show, self.repo, "run-sections")

        self.assertEqual(exit_code, 0)
        for section in ("[summary]", "[decision]", "[artifacts]", "[provenance]", "[integrity]"):
            self.assertIn(section, output)
        self.assertIn("status: CLEAN_CORE", output)
        self.assertLess(len(output.splitlines()), 40)

    def test_list_and_show_do_not_modify_state(self):
        self._write_run("run-read-only", "2026-07-01T00:00:00Z", "CLEAN_CORE", "LOW")
        before = self._state_hash()

        self.assertEqual(self._capture(_cmd_evidence_list, self.repo)[0], 0)
        self.assertEqual(self._capture(_cmd_evidence_show, self.repo, "run-read-only")[0], 0)

        self.assertEqual(self._state_hash(), before)

    def test_corrupt_ledger_entry_is_unreadable_and_listing_continues(self):
        self._write_run("run-before-corruption", "2026-07-01T00:00:00Z", "CLEAN_CORE", "LOW")
        with (self.state / "ledger.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{not-json\n")
        self._write_run("run-after-corruption", "2026-07-02T00:00:00Z", "CLEAN_CORE", "LOW")

        exit_code, output = self._capture(_cmd_evidence_list, self.repo)

        self.assertEqual(exit_code, 0)
        self.assertIn("status: DEGRADED", output)
        self.assertIn("run-before-corruption", output)
        self.assertIn("run-after-corruption", output)
        self.assertIn("ledger-line-2", output)
        self.assertIn("UNREADABLE", output)

    def test_show_redacts_credential_shapes_in_human_and_json_output(self):
        secret = "sk-proj-abcdefghijklmnopqrstuv"
        self._write_run(
            "run-secret",
            "2026-07-01T00:00:00Z",
            "CLEAN_CORE",
            "LOW",
            evidence_extra={"task_text": f"debug with {secret}", "provider_api_key": secret},
        )

        human_code, human_output = self._capture(_cmd_evidence_show, self.repo, "run-secret")
        json_code, json_output = self._capture(
            _cmd_evidence_show,
            self.repo,
            "run-secret",
            as_json=True,
        )

        self.assertEqual((human_code, json_code), (0, 0))
        self.assertNotIn(secret, human_output)
        self.assertNotIn(secret, json_output)
        self.assertIn(REDACTED_CREDENTIAL, human_output)
        self.assertIn(REDACTED_CREDENTIAL, json_output)
        parsed = json.loads(json_output)
        self.assertEqual(parsed["evidence"]["provider_api_key"], REDACTED_CREDENTIAL)

    def test_empty_state_is_a_successful_empty_list(self):
        exit_code, output = self._capture(_cmd_evidence_list, self.repo)
        json_code, json_output = self._capture(_cmd_evidence_list, self.repo, as_json=True)

        self.assertEqual((exit_code, json_code), (0, 0))
        self.assertIn("status: EMPTY", output)
        self.assertEqual(json.loads(json_output), {"items": [], "status": "EMPTY"})

    def test_missing_artifact_is_reported_without_crashing(self):
        self._write_run("run-missing", "2026-07-01T00:00:00Z", "CLEAN_CORE", "LOW")
        (self.runs / "run-missing" / "manifest.json").unlink()

        list_code, list_output = self._capture(_cmd_evidence_list, self.repo)
        show_code, show_output = self._capture(_cmd_evidence_show, self.repo, "run-missing")

        self.assertEqual(list_code, 0)
        self.assertIn("manifest:no", list_output)
        self.assertEqual(show_code, 1)
        self.assertIn("status: UNREADABLE", show_output)
        self.assertIn("manifest artifact is missing", show_output)

    def _write_run(
        self,
        run_id: str,
        recorded_at: str,
        status: str,
        risk_level: str,
        *,
        evidence_extra: dict | None = None,
    ) -> None:
        run_dir = self.runs / run_id
        run_dir.mkdir()
        evidence = {
            "run_id": run_id,
            "task_text": "fix typo",
            "status": status,
            "intent_risk": "LOW",
            "impact_risk": "NO_CHANGED_FILES",
            "risk_level": risk_level,
            "status_reasons": ["fixture"],
            "branch": "main",
            "head_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "changed_files": [],
            "changed_files_source": "no_changed_files",
            "safe_default": "HOLD",
            "binding_status": "BOUND",
        }
        evidence.update(evidence_extra or {})
        manifest = {"run_id": run_id, "manifest_hash": "c" * 64}
        (run_dir / "run.json").write_text("{}\n", encoding="utf-8")
        (run_dir / "evidence.json").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
        (run_dir / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        entry = {
            "run_id": run_id,
            "recorded_at": recorded_at,
            "status": status,
            "risk_level": risk_level,
            "task_text": evidence["task_text"],
            "run_path": f".aeg/runs/{run_id}/run.json",
            "evidence_path": f".aeg/runs/{run_id}/evidence.json",
            "manifest_path": f".aeg/runs/{run_id}/manifest.json",
        }
        with (self.state / "ledger.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def _state_hash(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(self.state.rglob("*"), key=lambda item: item.as_posix()):
            digest.update(path.relative_to(self.state).as_posix().encode("utf-8"))
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _capture(function, *args, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = function(*args, **kwargs)
        return exit_code, output.getvalue()


if __name__ == "__main__":
    unittest.main()
