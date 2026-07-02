import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    AEG_WRITE_DENIED_BY_MEDIATED_PATH,
    DENIED_BY_MEDIATOR,
    DENIED_BY_PATH_POLICY,
    EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATED_WRITE_DENIED,
    MEDIATOR_DECISION_DENY,
    NOT_FILESYSTEM_ENFORCED,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
)
from src.evidence import mediated_aeg_write_path
from src.evidence.mediated_aeg_write_path import (
    request_mediated_aeg_write_text,
    resolve_aeg_path,
)


class Phase10E3MediatedAegWriteFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.aeg = self.repo / ".aeg"
        self.work = self.repo / "work"
        self.evidence = self.aeg / "runs" / "run-001" / "evidence.json"
        self.manifest = self.aeg / "manifests" / "run-001" / "manifest.json"
        self.ledger = self.aeg / "ledger.jsonl"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.evidence.parent.mkdir(parents=True)
        self.manifest.parent.mkdir(parents=True)
        self.evidence.write_text(
            json.dumps({"run_id": "run-001", "marker": "baseline"}, sort_keys=True),
            encoding="utf-8",
        )
        self.manifest.write_text(
            json.dumps({"run_id": "run-001", "evidence_path": str(self.evidence)}, sort_keys=True),
            encoding="utf-8",
        )
        self.ledger.write_text('{"run_id":"run-001","entry":"baseline"}\n', encoding="utf-8")

    def create_aeg_alias(self) -> Path:
        alias = self.repo / "runtime-state-alias"
        alias.symlink_to(self.aeg, target_is_directory=True)
        return alias

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase10E3MediatedAegWriteDenialTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = Phase10E3MediatedAegWriteFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_mediated_direct_aeg_write_is_denied_and_target_is_not_created(self):
        target = self.fixture.aeg / "e3-direct-write.txt"

        result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=target,
            payload="phase10-e3 direct write should not be written\n",
            actor="phase10-e3-test",
            request_id="e3-direct-aeg-write",
        )

        self._assert_mediated_aeg_denial(result, target)
        self.assertFalse(target.exists())

    def test_mediated_traversal_aeg_write_is_denied_and_target_is_not_created(self):
        target = self.fixture.work / ".." / ".aeg" / "e3-traversal-write.txt"
        resolved_target = self.fixture.aeg / "e3-traversal-write.txt"

        result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=target,
            payload="phase10-e3 traversal write should not be written\n",
            actor="phase10-e3-test",
            request_id="e3-traversal-aeg-write",
        )

        self._assert_mediated_aeg_denial(result, resolved_target)
        self.assertFalse(resolved_target.exists())

    def test_mediated_symlink_alias_aeg_write_is_denied_and_target_is_not_created(self):
        try:
            alias = self.fixture.create_aeg_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")
        target = alias / "e3-symlink-write.txt"
        resolved_target = self.fixture.aeg / "e3-symlink-write.txt"

        result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=target,
            payload="phase10-e3 symlink write should not be written\n",
            actor="phase10-e3-test",
            request_id="e3-symlink-aeg-write",
        )

        self._assert_mediated_aeg_denial(result, resolved_target)
        self.assertFalse(resolved_target.exists())
        self.assertNotIn(".aeg", target.parts)

    def test_mediated_evidence_manifest_and_ledger_tamper_writes_are_denied_without_mutation(self):
        cases = (
            (
                "evidence-overwrite",
                self.fixture.evidence,
                json.dumps({"run_id": "run-001", "marker": "tampered-evidence"}, sort_keys=True),
                "replace",
            ),
            (
                "manifest-overwrite",
                self.fixture.manifest,
                json.dumps({"run_id": "run-001", "marker": "tampered-manifest"}, sort_keys=True),
                "replace",
            ),
            (
                "ledger-append",
                self.fixture.ledger,
                '{"run_id":"run-001","entry":"tamper-append"}\n',
                "append",
            ),
            (
                "ledger-overwrite",
                self.fixture.ledger,
                '{"run_id":"run-001","entry":"tamper-overwrite"}\n',
                "replace",
            ),
        )

        for case_name, target, payload, operation in cases:
            with self.subTest(case_name=case_name):
                before_digest = self.fixture.digest(target)

                result = request_mediated_aeg_write_text(
                    repo_root=self.fixture.repo,
                    submitted_target=target,
                    payload=payload,
                    actor="phase10-e3-test",
                    operation=operation,
                    request_id=f"e3-{case_name}",
                )

                after_digest = self.fixture.digest(target)
                self._assert_mediated_aeg_denial(result, target)
                self.assertEqual(after_digest, before_digest)

    def test_resolve_aeg_path_canonicalizes_relative_traversal_and_symlink_alias(self):
        try:
            alias = self.fixture.create_aeg_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")

        direct = resolve_aeg_path(repo_root=self.fixture.repo, submitted_target=".aeg/direct.txt")
        traversal = resolve_aeg_path(
            repo_root=self.fixture.repo,
            submitted_target=Path("work") / ".." / ".aeg" / "traversal.txt",
        )
        symlink_alias = resolve_aeg_path(
            repo_root=self.fixture.repo,
            submitted_target=alias / "symlink.txt",
        )

        self.assertTrue(direct.target_under_aeg)
        self.assertTrue(traversal.target_under_aeg)
        self.assertTrue(symlink_alias.target_under_aeg)
        self.assertTrue(Path(direct.canonical_target).is_absolute())
        self.assertTrue(Path(traversal.canonical_target).is_absolute())
        self.assertTrue(Path(symlink_alias.canonical_target).is_absolute())

    def test_e1_known_gap_vocabulary_remains_currently_bypassable(self):
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE, "CURRENTLY_BYPASSABLE")
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED, "EXPECTED_RED")
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE, "KNOWN_GAP_BASELINE")

    def test_mediated_path_module_does_not_add_permission_or_external_scope(self):
        source = inspect.getsource(mediated_aeg_write_path)
        forbidden_calls = (
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".chmod(",
            "chmod(",
            ".chown(",
            "chown(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "subprocess",
            "shutil",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _assert_mediated_aeg_denial(self, result, expected_target: Path) -> None:
        self.assertEqual(result.decision_status, MEDIATED_WRITE_DENIED)
        self.assertEqual(result.decision_reason, AEG_WRITE_DENIED_BY_MEDIATED_PATH)
        self.assertEqual(result.mediator_status, DENIED_BY_MEDIATOR)
        self.assertEqual(result.path_policy_status, DENIED_BY_PATH_POLICY)
        self.assertEqual(result.enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(result.external_enforcement_status, EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED)
        self.assertEqual(result.raw_direct_write_status, RAW_DIRECT_WRITE_STILL_BYPASSABLE)
        self.assertEqual(result.mediator_decision.decision_status, MEDIATOR_DECISION_DENY)
        self.assertFalse(result.write_performed)
        self.assertFalse(result.filesystem_interception_present)
        self.assertFalse(result.permission_hardening_present)
        self.assertFalse(result.outside_repo_denial_implemented)
        self.assertFalse(result.live_executor_authority_granted)
        self.assertTrue(result.target_under_aeg)
        self.assertTrue(result.path_resolution.target_under_aeg)
        self.assertEqual(Path(result.path_resolution.canonical_target), expected_target.resolve())


if __name__ == "__main__":
    unittest.main()
