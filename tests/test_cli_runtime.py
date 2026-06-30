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
from src.cli.main import _cmd_doctor, _cmd_run
from src.contracts import (
    BOUND,
    CLEAN_CORE,
    CONTRACT_FIRST_NOOP,
    EVIDENCE_BINDING_V1,
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
    RUN_MANIFEST_V1,
    SAFE_DEFAULT,
)
from src.evidence import (
    manifest_hash,
    validate_completion_contract_v0,
    validate_evidence_binding_v0,
    validate_evidence_binding_v1,
    validate_user_gate_reason_card_v1,
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

    def test_doctor_passes_inside_initialized_repo(self):
        self._aeg("init")

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
        self.assertIn("[PASS] provider not required", doctor.stdout)
        self.assertIn("[PASS] OpenAI / Claude / Gemini not required", doctor.stdout)
        self.assertIn("External provider credentials are not required", doctor.stdout)
        self.assertIn("Network access is not required", doctor.stdout)

    def test_doctor_gives_readable_failure_outside_git_repo(self):
        with tempfile.TemporaryDirectory() as outside:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT)
            doctor = subprocess.run(
                [sys.executable, "-m", "src.cli", "doctor"],
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
        self.assertIn("[PASS] provider not required", doctor.stdout)
        self.assertNotIn("Traceback", combined)

    def test_doctor_warns_when_aeg_state_is_missing_and_suggests_init(self):
        doctor = self._aeg("doctor")

        self.assertEqual(doctor.returncode, 0)
        self.assertIn("status: PASS_WITH_WARNINGS", doctor.stdout)
        self.assertIn("[WARN] .aeg/ exists", doctor.stdout)
        self.assertIn("fix_hint: Run aeg init", doctor.stdout)
        self.assertIn("[PASS] provider not required", doctor.stdout)
        self.assertIn("[PASS] network not required", doctor.stdout)

    def test_doctor_reports_missing_git_command_readably(self):
        with patch("src.state.doctor.git.git_available", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_doctor(self.repo)

        self.assertEqual(exit_code, 1)
        stdout = output.getvalue()
        self.assertIn("status: FAIL", stdout)
        self.assertIn("[FAIL] git command available", stdout)
        self.assertIn("fix_hint: Install Git", stdout)
        self.assertIn("[PASS] provider not required", stdout)
        self.assertIn("[PASS] network not required", stdout)

    def test_doctor_reports_unwritable_aeg_state_readably(self):
        self._aeg("init")

        with patch("src.state.doctor._state_dir_writable", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = _cmd_doctor(self.repo)

        self.assertEqual(exit_code, 1)
        stdout = output.getvalue()
        self.assertIn("status: FAIL", stdout)
        self.assertIn("[FAIL] .aeg/ writable", stdout)
        self.assertIn("Fix filesystem permissions or ownership", stdout)

    def test_doctor_flags_unignored_aeg_state(self):
        (self.repo / ".gitignore").write_text("", encoding="utf-8")
        self._aeg("init")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .aeg/ git ignored", doctor.stdout)
        self.assertIn("fix_hint: Add .aeg/ to .gitignore", doctor.stdout)

    def test_doctor_flags_tracked_aeg_state(self):
        self._aeg("init")
        (self.repo / ".aeg" / "tracked.txt").write_text("runtime\n", encoding="utf-8")
        self._git("add", "-f", ".aeg/tracked.txt")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .aeg/ tracked file count", doctor.stdout)
        self.assertIn("tracked_count: 1", doctor.stdout)
        self.assertIn("git rm --cached -r .aeg", doctor.stdout)

    def test_doctor_flags_tracked_env_file(self):
        self._aeg("init")
        (self.repo / ".env").write_text("PLACEHOLDER=1\n", encoding="utf-8")
        self._git("add", "-f", ".env")

        doctor = self._aeg("doctor", check=False)

        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("status: FAIL", doctor.stdout)
        self.assertIn("[FAIL] .env tracked file count", doctor.stdout)
        self.assertIn("tracked_count: 1", doctor.stdout)
        self.assertIn("keep real secrets out of Git", doctor.stdout)

    def test_low_run_and_verify(self):
        self._aeg("init")
        run = self._aeg("run", "fix typo in README")
        self.assertIn("status: CLEAN_CORE", run.stdout)
        self.assertIn("binding_status: BOUND", run.stdout)
        self.assertIn("binding_version: evidence_binding_v1", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], LOW)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], LOW)
        self.assertEqual(evidence["changed_files"], [])
        self.assertEqual(evidence["changed_files_source"], NO_CHANGED_FILES_SOURCE)
        self.assertEqual(evidence["protected_paths_touched"], [])
        self.assertFalse(evidence["risk_escalation_applied"])
        self.assertEqual(evidence["status"], CLEAN_CORE)
        self.assertEqual(evidence["binding_version"], EVIDENCE_BINDING_V1)
        self.assertEqual(evidence["binding_status"], BOUND)
        self.assertEqual(validate_evidence_binding_v0(evidence), [])
        self.assertEqual(validate_evidence_binding_v1(evidence), [])
        self.assertEqual(validate_completion_contract_v0(evidence), [])
        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: CLEAN_CORE", verify.stdout)
        self.assertIn("binding_status: BOUND", verify.stdout)
        self.assertIn("evidence binding v1 valid", verify.stdout)
        self.assertIn("LOW risk remained CLEAN_CORE", verify.stdout)

    def test_run_creates_manifest_with_deterministic_binding_hash(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")

        evidence, _ = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()

        self.assertTrue(manifest_path.exists())
        self.assertEqual(manifest["manifest_version"], RUN_MANIFEST_V1)
        self.assertEqual(manifest["run_id"], evidence["run_id"])
        self.assertEqual(manifest["repo_root"], evidence["repo_root"])
        self.assertEqual(manifest["branch"], evidence["branch"])
        self.assertEqual(manifest["head_sha"], evidence["head_sha"])
        self.assertEqual(manifest["tree_sha"], evidence["tree_sha"])
        self.assertEqual(manifest["changed_files"], evidence["changed_files"])
        self.assertEqual(manifest["changed_files_source"], evidence["changed_files_source"])
        self.assertEqual(manifest["risk_level"], evidence["risk_level"])
        self.assertEqual(manifest["status"], evidence["status"])
        self.assertEqual(evidence["bound_manifest_path"], f".aeg/runs/{evidence['run_id']}/manifest.json")
        self.assertEqual(evidence["bound_manifest_hash"], manifest_hash(manifest))
        self.assertEqual(manifest_hash(manifest), manifest_hash(json.loads(json.dumps(manifest, sort_keys=True))))

    def test_medium_run_records_not_checked_with_binding_and_completion_contract(self):
        self._aeg("init")
        run = self._aeg("run", "do the thing")
        self.assertIn("intent_risk: MEDIUM", run.stdout)
        self.assertIn("impact_risk: NO_CHANGED_FILES", run.stdout)
        self.assertIn("risk_level: MEDIUM", run.stdout)
        self.assertIn("status: NOT_CHECKED", run.stdout)
        self.assertIn("binding_status: BOUND", run.stdout)
        self.assertNotIn("status: CLEAN_CORE", run.stdout)

        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], MEDIUM)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], MEDIUM)
        self.assertEqual(evidence["status"], NOT_CHECKED)
        self.assertEqual(evidence["binding_status"], BOUND)
        self.assertEqual(validate_evidence_binding_v0(evidence), [])
        self.assertEqual(validate_evidence_binding_v1(evidence), [])
        self.assertEqual(validate_completion_contract_v0(evidence), [])

        executor = evidence["checks"]["executor"]
        completion_contract = executor["completion_contract"]
        self.assertEqual(executor["executor"], CONTRACT_FIRST_NOOP)
        self.assertEqual(completion_contract["executor_mode"], CONTRACT_FIRST_NOOP)
        self.assertTrue(completion_contract["completion_reported"])
        self.assertFalse(completion_contract["completion_satisfied"])
        self.assertNotEqual(completion_contract["completion_reported"], completion_contract["completion_satisfied"])
        self.assertFalse(completion_contract["file_mutation"])
        self.assertFalse(completion_contract["provider_calls"])
        self.assertFalse(completion_contract["network_calls"])

        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NOT_CHECKED", verify.stdout)
        self.assertIn("evidence binding v0 valid", verify.stdout)
        self.assertIn("evidence binding v1 valid", verify.stdout)
        self.assertIn("completion contract v0 valid", verify.stdout)
        self.assertIn("law status replay matched: NOT_CHECKED", verify.stdout)

    def test_high_run_and_verify(self):
        self._aeg("init")
        run = self._aeg("run", "merge to main and deploy")
        self.assertIn("status: NEEDS_USER_GATE", run.stdout)
        self.assertIn("user_gate.why: High-risk task requires an explicit user gate before execution.", run.stdout)
        self.assertIn("user_gate.safe_default: hold_current_state", run.stdout)
        evidence = self._latest_evidence()
        self.assertEqual(evidence["intent_risk"], HIGH)
        self.assertEqual(evidence["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(evidence["risk_level"], HIGH)
        self.assertEqual(evidence["changed_files_source"], NO_CHANGED_FILES_SOURCE)
        self.assertEqual(evidence["status"], NEEDS_USER_GATE)
        self.assertEqual(evidence["binding_version"], EVIDENCE_BINDING_V1)
        self.assertEqual(evidence["binding_status"], BOUND)
        self.assertIn("law.high.requires_user_gate", evidence["status_reasons"])
        self.assertEqual(validate_evidence_binding_v1(evidence), [])
        self.assertEqual(validate_user_gate_reason_card_v1(evidence), [])
        card = evidence["user_gate_reason_card"]
        self.assertEqual(card["risk_level"], HIGH)
        self.assertEqual(card["status"], NEEDS_USER_GATE)
        self.assertIn("explicit user gate", card["why_gate_is_required"])
        self.assertTrue(card["irreversible_action_blocked"])
        self.assertEqual(card["intent_risk"], HIGH)
        self.assertEqual(card["impact_risk"], NO_CHANGED_FILES)
        self.assertEqual(card["protected_paths_touched"], [])
        self.assertEqual(card["safe_default"], SAFE_DEFAULT)
        verify = self._aeg("verify")
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NEEDS_USER_GATE", verify.stdout)
        self.assertIn("binding_status: BOUND", verify.stdout)
        self.assertIn("HIGH risk remained NEEDS_USER_GATE", verify.stdout)
        self.assertIn("HIGH user gate reason card valid", verify.stdout)

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
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NEEDS_USER_GATE", verify.stdout)
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
        self._assert_verify_consistent(verify)
        self.assertIn("evidence_status_value: NOT_CHECKED", verify.stdout)
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
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: changed_files mismatch", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: bound_changed_files_hash mismatch", verify.stdout)

    def test_verify_rejects_saved_risk_level_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["risk_level"] = MEDIUM
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: risk_level mismatch: evidence=MEDIUM replay=LOW", verify.stdout)

    def test_verify_rejects_missing_completion_contract(self):
        self._aeg("init")
        self._aeg("run", "do the thing")
        evidence, path = self._latest_evidence_with_path()
        del evidence["checks"]["executor"]["completion_contract"]
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: missing completion_contract_v0", verify.stdout)
        self.assertNotIn("status: CLEAN_CORE", verify.stdout)

    def test_verify_rejects_not_checked_promoted_to_clean_core(self):
        self._aeg("init")
        self._aeg("run", "do the thing")
        evidence, path = self._latest_evidence_with_path()
        evidence["status"] = CLEAN_CORE
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: law status mismatch: evidence=CLEAN_CORE replay=NOT_CHECKED", verify.stdout)

    def test_verify_rejects_missing_changed_files_source_as_not_checked(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["changed_files_source"]
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("missing required field: changed_files_source", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: missing evidence binding field: changed_files_source", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: manifest changed_files_source mismatch", verify.stdout)

    def test_verify_rejects_missing_manifest(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        _, manifest_path = self._latest_manifest_with_path()
        manifest_path.unlink()

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest missing", verify.stdout)

    def test_verify_rejects_manifest_hash_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["status"] = NOT_CHECKED
        self._write_json(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest hash mismatch", verify.stdout)

    def test_verify_rejects_run_id_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["run_id"] = "tampered-run-id"
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest run_id mismatch", verify.stdout)

    def test_verify_rejects_changed_files_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["changed_files"] = ["README.md"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: changed_files mismatch", verify.stdout)

    def test_verify_rejects_changed_files_hash_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["bound_changed_files_hash"] = "0" * 64
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: bound_changed_files_hash mismatch", verify.stdout)

    def test_verify_rejects_evidence_path_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["evidence_path"] = ".aeg/runs/other/evidence.json"
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest evidence_path mismatch", verify.stdout)

    def test_verify_rejects_run_path_mismatch(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        manifest, manifest_path = self._latest_manifest_with_path()
        manifest["run_path"] = ".aeg/runs/other/run.json"
        self._write_manifest_and_rebind_hash(manifest_path, manifest)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: manifest run_path mismatch", verify.stdout)

    def test_verify_rejects_missing_binding_fields(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        del evidence["binding_version"]
        del evidence["bound_head_sha"]
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: missing evidence binding v1 field: binding_version", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: missing evidence binding v1 field: bound_head_sha", verify.stdout)

    def test_verify_rejects_non_bound_clean_core(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["binding_status"] = NOT_CHECKED
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: binding_status must be BOUND for judgment basis", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: CLEAN_CORE requires binding_status BOUND", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

    def test_verify_rejects_reported_only_as_judgment_basis(self):
        self._aeg("init")
        self._aeg("run", "fix typo in README")
        evidence, path = self._latest_evidence_with_path()
        evidence["reported_only"] = True
        evidence["judgment_basis"] = "reported_only"
        self._write_json(path, evidence)

        verify = self._aeg("verify", check=False)
        self.assertNotEqual(verify.returncode, 0)
        self._assert_verify_failed(verify)
        self.assertIn("INVALID_EVIDENCE: reported_only evidence is not judgment basis", verify.stdout)
        self.assertIn("INVALID_EVIDENCE: reported_only cannot be judgment basis", verify.stdout)

    def _assert_verify_consistent(self, verify):
        self.assertIn("status: REPLAY_CONSISTENT", verify.stdout)
        self.assertIn("verification_scope: deterministic_replay_and_binding_validation", verify.stdout)
        self.assertIn("independent_oracle: false", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

    def _assert_verify_failed(self, verify):
        self.assertIn("status: REPLAY_FAILED", verify.stdout)
        self.assertIn("verification_scope: deterministic_replay_and_binding_validation", verify.stdout)
        self.assertIn("independent_oracle: false", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

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

    def _latest_manifest_with_path(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        entry = json.loads(line)
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8")), path

    def _write_manifest_and_rebind_hash(self, manifest_path, manifest):
        self._write_json(manifest_path, manifest)
        evidence, evidence_path = self._latest_evidence_with_path()
        evidence["bound_manifest_hash"] = manifest_hash(manifest)
        self._write_json(evidence_path, evidence)

    def _write_json(self, path, payload):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
