import hashlib
import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    DENIED_BY_MEDIATOR,
    DENIED_BY_REPO_BOUNDARY_POLICY,
    EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATED_WRITE_DENIED,
    MEDIATOR_DECISION_DENY,
    NOT_FILESYSTEM_ENFORCED,
    OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    REPO_BOUNDARY_WRITE_DENIED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
)
from src.evidence import mediated_repo_boundary_write_path
from src.evidence.mediated_repo_boundary_write_path import (
    request_mediated_outside_repo_write_text,
    resolve_repo_boundary_path,
)


class Phase10E4OutsideRepoFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.work = self.repo / "work"
        self.sibling_outside = root / "outside-sibling"
        self.absolute_outside = (root / "absolute-outside").resolve()
        self.existing_outside = self.sibling_outside / "existing-outside.txt"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.sibling_outside.mkdir(parents=True)
        self.absolute_outside.mkdir(parents=True)
        self.existing_outside.write_text("phase10-e4 baseline outside content\n", encoding="utf-8")

    def create_outside_alias_inside_repo(self) -> Path:
        alias = self.repo / "outside-sibling-alias"
        alias.symlink_to(self.sibling_outside, target_is_directory=True)
        return alias

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase10E4MediatedOutsideRepoWriteDenialTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = Phase10E4OutsideRepoFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_mediated_sibling_outside_repo_write_is_denied_and_target_is_not_created(self):
        submitted = Path("..") / "outside-sibling" / "e4-sibling-outside.txt"
        expected_target = self.fixture.sibling_outside / "e4-sibling-outside.txt"

        result = request_mediated_outside_repo_write_text(
            repo_root=self.fixture.repo,
            submitted_target=submitted,
            payload="phase10-e4 sibling outside write should not be written\n",
            actor="phase10-e4-test",
            request_id="e4-sibling-outside-write",
        )

        self._assert_mediated_outside_repo_denial(result, expected_target)
        self.assertFalse(expected_target.exists())

    def test_mediated_absolute_outside_repo_write_is_denied_and_target_is_not_created(self):
        target = self.fixture.absolute_outside / "e4-absolute-outside.txt"

        result = request_mediated_outside_repo_write_text(
            repo_root=self.fixture.repo,
            submitted_target=target,
            payload="phase10-e4 absolute outside write should not be written\n",
            actor="phase10-e4-test",
            request_id="e4-absolute-outside-write",
        )

        self._assert_mediated_outside_repo_denial(result, target)
        self.assertTrue(Path(result.path_resolution.submitted_target).is_absolute())
        self.assertFalse(target.exists())

    def test_mediated_traversal_escaping_repo_write_is_denied_and_target_is_not_created(self):
        submitted = Path("work") / ".." / ".." / "outside-sibling" / "e4-traversal-outside.txt"
        expected_target = self.fixture.sibling_outside / "e4-traversal-outside.txt"

        result = request_mediated_outside_repo_write_text(
            repo_root=self.fixture.repo,
            submitted_target=submitted,
            payload="phase10-e4 traversal outside write should not be written\n",
            actor="phase10-e4-test",
            request_id="e4-traversal-outside-write",
        )

        self._assert_mediated_outside_repo_denial(result, expected_target)
        self.assertFalse(expected_target.exists())

    def test_mediated_symlink_alias_escaping_repo_write_is_denied_and_target_is_not_created(self):
        try:
            alias = self.fixture.create_outside_alias_inside_repo()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")
        submitted = alias / "e4-symlink-outside.txt"
        expected_target = self.fixture.sibling_outside / "e4-symlink-outside.txt"

        result = request_mediated_outside_repo_write_text(
            repo_root=self.fixture.repo,
            submitted_target=submitted,
            payload="phase10-e4 symlink outside write should not be written\n",
            actor="phase10-e4-test",
            request_id="e4-symlink-outside-write",
        )

        self._assert_mediated_outside_repo_denial(result, expected_target)
        self.assertTrue(self._is_relative_to(Path(result.path_resolution.absolute_target), self.fixture.repo.resolve()))
        self.assertFalse(expected_target.exists())

    def test_denied_existing_outside_repo_write_does_not_modify_target(self):
        before_digest = self.fixture.digest(self.fixture.existing_outside)

        result = request_mediated_outside_repo_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.existing_outside,
            payload="phase10-e4 outside overwrite should not be written\n",
            actor="phase10-e4-test",
            operation="replace",
            request_id="e4-existing-outside-overwrite",
        )

        after_digest = self.fixture.digest(self.fixture.existing_outside)
        self._assert_mediated_outside_repo_denial(result, self.fixture.existing_outside)
        self.assertEqual(after_digest, before_digest)

    def test_resolve_repo_boundary_path_canonicalizes_outside_repo_cases(self):
        try:
            alias = self.fixture.create_outside_alias_inside_repo()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")

        sibling = resolve_repo_boundary_path(
            repo_root=self.fixture.repo,
            submitted_target=Path("..") / "outside-sibling" / "sibling.txt",
        )
        absolute = resolve_repo_boundary_path(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.absolute_outside / "absolute.txt",
        )
        traversal = resolve_repo_boundary_path(
            repo_root=self.fixture.repo,
            submitted_target=Path("work") / ".." / ".." / "outside-sibling" / "traversal.txt",
        )
        symlink_alias = resolve_repo_boundary_path(
            repo_root=self.fixture.repo,
            submitted_target=alias / "symlink.txt",
        )

        for path_resolution in (sibling, absolute, traversal, symlink_alias):
            with self.subTest(canonical_target=path_resolution.canonical_target):
                self.assertFalse(path_resolution.target_under_repo)
                self.assertTrue(path_resolution.target_outside_repo)
                self.assertTrue(Path(path_resolution.canonical_target).is_absolute())

    def test_resolve_repo_boundary_path_handles_windows_absolute_paths_cross_platform(self):
        repo_root = r"C:\Users\test\repo"

        internal_backslash = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=r"C:\Users\test\repo\src\app.py",
        )
        internal_forward_slash = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target="C:/Users/test/repo/src/app.py",
        )
        protected_inside = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=r"C:\Users\test\repo\.env",
        )
        prefix_sibling = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=r"C:\Users\test\repo.env",
        )
        windows_outside = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=r"C:\Windows\System32\config",
        )
        other_drive = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=r"D:\other\path\file.txt",
        )
        traversal_outside = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=r"C:\Users\test\repo\..\outside.txt",
        )

        for path_resolution in (internal_backslash, internal_forward_slash, protected_inside):
            with self.subTest(canonical_target=path_resolution.canonical_target):
                self.assertTrue(path_resolution.target_under_repo)
                self.assertFalse(path_resolution.target_outside_repo)

        for path_resolution in (prefix_sibling, windows_outside, other_drive, traversal_outside):
            with self.subTest(canonical_target=path_resolution.canonical_target):
                self.assertFalse(path_resolution.target_under_repo)
                self.assertTrue(path_resolution.target_outside_repo)

    def test_repo_internal_target_is_not_accepted_by_e4_outside_repo_helper(self):
        with self.assertRaisesRegex(ValueError, "outside-repo"):
            request_mediated_outside_repo_write_text(
                repo_root=self.fixture.repo,
                submitted_target=Path("work") / "inside-repo.txt",
                payload="phase10-e4 inside repo request is out of scope\n",
                actor="phase10-e4-test",
                request_id="e4-inside-repo-out-of-scope",
            )

    def test_e1_known_gap_vocabulary_remains_currently_bypassable(self):
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE, "CURRENTLY_BYPASSABLE")
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED, "EXPECTED_RED")
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE, "KNOWN_GAP_BASELINE")

    def test_mediated_repo_boundary_module_does_not_add_permission_or_external_scope(self):
        source = inspect.getsource(mediated_repo_boundary_write_path)
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

    def _assert_mediated_outside_repo_denial(self, result, expected_target: Path) -> None:
        self.assertEqual(result.decision_status, MEDIATED_WRITE_DENIED)
        self.assertEqual(result.decision_reason, OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH)
        self.assertEqual(result.mediator_status, DENIED_BY_MEDIATOR)
        self.assertEqual(result.path_policy_status, REPO_BOUNDARY_WRITE_DENIED)
        self.assertEqual(result.repo_boundary_policy_status, DENIED_BY_REPO_BOUNDARY_POLICY)
        self.assertEqual(result.enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(result.external_enforcement_status, EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED)
        self.assertEqual(result.raw_direct_write_status, RAW_DIRECT_WRITE_STILL_BYPASSABLE)
        self.assertEqual(result.mediator_decision.decision_status, MEDIATOR_DECISION_DENY)
        self.assertFalse(result.write_performed)
        self.assertFalse(result.filesystem_interception_present)
        self.assertFalse(result.permission_hardening_present)
        self.assertTrue(result.mediated_outside_repo_denial_present)
        self.assertFalse(result.live_executor_authority_granted)
        self.assertTrue(result.target_outside_repo)
        self.assertTrue(result.path_resolution.target_outside_repo)
        self.assertFalse(result.path_resolution.target_under_repo)
        self.assertEqual(Path(result.path_resolution.canonical_target), expected_target.resolve())

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True


if __name__ == "__main__":
    unittest.main()
