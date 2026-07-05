import os
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_LIMITED_ALLOWED,
    SCOPE_LIMIT_REJECTED,
)
from src.evidence.structured_action_symlink_realpath_fixtures import (
    AEG_SCOPE_ESCAPE_REJECTED,
    CATEGORY_INERT_DATA,
    CATEGORY_SYMLINK_REALPATH_ESCAPE,
    ENV_SECRET_ACCESS_REJECTED,
    INERT_PROPOSE_PATCH_DATA_ONLY,
    NOT_CHECKED_PLATFORM_PERMISSION_LIMIT,
    NOT_CHECKED_SYMLINK_UNSUPPORTED,
    OUTSIDE_REPO_ESCAPE_REJECTED,
    SYMLINK_REALPATH_FIXTURES_CHECKED,
    SYMLINK_SUPPORTED,
    SymlinkRealpathFixture,
    build_symlink_realpath_fixture_summary,
    evaluate_symlink_realpath_fixture,
    inert_propose_patch_action,
    propose_patch_for_paths,
    repo_read_for_paths,
    verify_symlink_realpath_fixture_summary,
)
from src.evidence.structured_actions import (
    FORBIDDEN_PAYLOAD_FIELD_REJECTED,
    PROPOSE_PATCH,
    REQUEST_REPO_READ,
    VALID_STRUCTURED_ACTION,
)


class Phase11bSymlinkRealpathEscapeFixtureTests(unittest.TestCase):
    def test_symlink_resolving_to_aeg_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="symlink_to_aeg",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=propose_patch_for_paths(["link_to_aeg/evil.json"]),
                    expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
                ),
            )

            self._assert_rejected(result, AEG_SCOPE_ESCAPE_REJECTED)
            self.assertEqual(result.schema_status, FORBIDDEN_PAYLOAD_FIELD_REJECTED)
            self.assertEqual(result.gate_result, SCOPE_LIMIT_REJECTED)

    def test_symlink_resolving_outside_repo_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="symlink_to_outside_repo",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=propose_patch_for_paths(["link_to_outside/outside.txt"]),
                    expected_fixture_status=OUTSIDE_REPO_ESCAPE_REJECTED,
                ),
            )

            self._assert_rejected(result, OUTSIDE_REPO_ESCAPE_REJECTED)

    def test_symlink_resolving_to_env_or_secret_target_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="symlink_to_env",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=propose_patch_for_paths(["link_to_env"]),
                    expected_fixture_status=ENV_SECRET_ACCESS_REJECTED,
                ),
            )

            self._assert_rejected(result, ENV_SECRET_ACCESS_REJECTED)

    def test_nested_symlink_chain_resolving_to_aeg_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="nested_symlink_chain_to_aeg",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=propose_patch_for_paths(["link_a/evil.json"]),
                    expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
                ),
            )

            self._assert_rejected(result, AEG_SCOPE_ESCAPE_REJECTED)

    def test_traversal_plus_symlink_combination_resolving_to_aeg_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="traversal_plus_symlink_to_aeg",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=propose_patch_for_paths(["safe_dir/../link_to_aeg/evil.json"]),
                    expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
                ),
            )

            self._assert_rejected(result, AEG_SCOPE_ESCAPE_REJECTED)

    def test_propose_patch_with_symlink_target_resolving_to_aeg_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            action = propose_patch_for_paths(["link_to_aeg/evil.json"])
            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="propose_patch_symlink_target_to_aeg",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=action,
                    expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
                ),
            )

            self.assertEqual(action["action_type"], PROPOSE_PATCH)
            self._assert_rejected(result, AEG_SCOPE_ESCAPE_REJECTED)

    def test_request_repo_read_with_symlink_target_resolving_to_aeg_is_rejected(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            action = repo_read_for_paths(["link_to_aeg/ledger.jsonl"])
            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="request_repo_read_symlink_target_to_aeg",
                    category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                    action=action,
                    expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
                ),
            )

            self.assertEqual(action["action_type"], REQUEST_REPO_READ)
            self._assert_rejected(result, AEG_SCOPE_ESCAPE_REJECTED)

    def test_inert_propose_patch_with_normal_target_remains_data_only(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            sentinel = fixture.repo / "should-not-exist-from-patch-diff"
            action = inert_propose_patch_action("src/normal.py")
            action["payload"]["patch_diff"] += f"\n# text-only mention: {sentinel}\n"
            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="inert_propose_patch_normal_target",
                    category=CATEGORY_INERT_DATA,
                    action=action,
                    expected_fixture_status=INERT_PROPOSE_PATCH_DATA_ONLY,
                ),
            )

            self.assertTrue(result.allowed)
            self.assertFalse(result.rejected)
            self.assertTrue(result.expectation_met)
            self.assertEqual(result.fixture_status, INERT_PROPOSE_PATCH_DATA_ONLY)
            self.assertEqual(result.schema_status, VALID_STRUCTURED_ACTION)
            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertFalse(result.execution_allowed)
            self.assertFalse(result.mutation_allowed)
            self.assertFalse(result.write_authority_granted)
            self.assertFalse(sentinel.exists())

    def test_fixture_evaluation_does_not_execute_action(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            sentinel = fixture.repo / "execution-sentinel"
            action = inert_propose_patch_action("src/normal.py")
            action["payload"]["patch_plan"].append(f"Text only: create {sentinel}")

            result = self._evaluate(
                fixture,
                SymlinkRealpathFixture(
                    case_id="non_execution_sentinel",
                    category=CATEGORY_INERT_DATA,
                    action=action,
                    expected_fixture_status=INERT_PROPOSE_PATCH_DATA_ONLY,
                ),
            )

            self.assertEqual(result.gate_result, CAPABILITY_GATE_LIMITED_ALLOWED)
            self.assertFalse(result.execution_allowed)
            self.assertFalse(sentinel.exists())

    def test_fixture_evaluation_does_not_mutate_repo_filesystem(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            before = snapshot_tree(fixture.repo)
            results = tuple(self._evaluate(fixture, case) for case in self._fixture_cases())
            after = snapshot_tree(fixture.repo)

            self.assertEqual(before, after)
            self.assertTrue(all(not result.execution_allowed for result in results))
            self.assertTrue(all(not result.mutation_allowed for result in results))
            self.assertTrue(all(not result.write_authority_granted for result in results))

    def test_summary_records_counts_and_non_authority_flags(self):
        with TempSymlinkRepo() as fixture:
            if self._assert_not_checked_if_unsupported(fixture):
                return

            evaluations = tuple(self._evaluate(fixture, case) for case in self._fixture_cases())
            summary = build_symlink_realpath_fixture_summary(
                evaluations,
                symlink_support_status=fixture.support_status,
            )
            verification = verify_symlink_realpath_fixture_summary(summary)

            self.assertTrue(verification.ok, verification.errors)
            self.assertEqual(
                summary["symlink_realpath_fixture_status"],
                SYMLINK_REALPATH_FIXTURES_CHECKED,
            )
            self.assertTrue(summary["symlink_realpath_checked"])
            self.assertEqual(summary["symlink_realpath_support_status"], SYMLINK_SUPPORTED)
            self.assertEqual(summary["symlink_escape_allowed_count"], 0)
            self.assertEqual(summary["realpath_escape_allowed_count"], 0)
            self.assertEqual(summary["symlink_escape_rejected_count"], 7)
            self.assertEqual(summary["realpath_escape_rejected_count"], 7)
            self.assertEqual(summary["inert_propose_patch_data_only_count"], 1)
            self.assertFalse(summary["execution_allowed"])
            self.assertFalse(summary["mutation_allowed"])
            self.assertFalse(summary["write_authority_granted"])
            self.assertFalse(summary["live_executor_ready"])
            self.assertEqual(
                summary["live_executor_authority"],
                LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
            )

    def test_symlink_unsupported_environment_is_not_checked_not_pass(self):
        summary = build_symlink_realpath_fixture_summary(
            (),
            symlink_support_status=NOT_CHECKED_SYMLINK_UNSUPPORTED,
        )
        verification = verify_symlink_realpath_fixture_summary(summary)

        self.assertTrue(verification.ok, verification.errors)
        self.assertFalse(summary["symlink_realpath_checked"])
        self.assertEqual(
            summary["symlink_realpath_fixture_status"],
            NOT_CHECKED_SYMLINK_UNSUPPORTED,
        )
        self.assertNotEqual(summary["symlink_realpath_fixture_status"], "PASS")

    def test_not_checked_is_not_promoted_to_pass(self):
        summary = build_symlink_realpath_fixture_summary(
            (),
            symlink_support_status=NOT_CHECKED_PLATFORM_PERMISSION_LIMIT,
        )
        tampered = dict(summary)
        tampered["symlink_realpath_fixture_status"] = "PASS"

        verification = verify_symlink_realpath_fixture_summary(tampered)

        self.assertFalse(verification.ok)
        self.assertTrue(any("PASS" in error for error in verification.errors))

    def test_forbidden_symlink_safe_without_realpath_statuses_rejected(self):
        for forbidden_status in (
            "PASS_WITHOUT_SYMLINK_REALPATH_TEST",
            "SYMLINK_SAFE_WITHOUT_REALPATH_TEST",
        ):
            with self.subTest(forbidden_status=forbidden_status):
                summary = build_symlink_realpath_fixture_summary(
                    (),
                    symlink_support_status=NOT_CHECKED_SYMLINK_UNSUPPORTED,
                )
                tampered = dict(summary)
                tampered["symlink_realpath_fixture_status"] = forbidden_status

                verification = verify_symlink_realpath_fixture_summary(tampered)

                self.assertFalse(verification.ok)
                self.assertTrue(
                    any("forbidden symlink pass status" in error for error in verification.errors)
                )

    def test_summary_verify_rejects_allowed_escape_and_authority_overclaims(self):
        summary = build_symlink_realpath_fixture_summary(
            (),
            symlink_support_status=SYMLINK_SUPPORTED,
        )
        tampered = dict(summary)
        tampered.update(
            {
                "symlink_escape_allowed_count": 1,
                "realpath_escape_allowed_count": 1,
                "execution_allowed": True,
                "mutation_allowed": True,
                "write_authority_granted": True,
                "live_executor_ready": True,
            }
        )

        verification = verify_symlink_realpath_fixture_summary(tampered)

        self.assertFalse(verification.ok)
        self.assertTrue(any("symlink escape allowed" in error for error in verification.errors))
        self.assertTrue(any("realpath escape allowed" in error for error in verification.errors))
        self.assertTrue(any("execution_allowed" in error for error in verification.errors))
        self.assertTrue(any("mutation_allowed" in error for error in verification.errors))
        self.assertTrue(any("write_authority_granted" in error for error in verification.errors))
        self.assertTrue(any("live_executor_ready" in error for error in verification.errors))

    def test_pr_81_remains_untouched_draft_hold_by_contract(self):
        summary = build_symlink_realpath_fixture_summary(
            (),
            symlink_support_status=NOT_CHECKED_SYMLINK_UNSUPPORTED,
        )

        self.assertEqual(summary["pr_81_status"], "HOLD_OPEN_DRAFT_UNTOUCHED")
        self.assertEqual(summary["pr_81_draft_release"], "NOT_PERFORMED")
        self.assertEqual(summary["pr_81_merge"], "NOT_PERFORMED")

    def _evaluate(self, fixture, case):
        return evaluate_symlink_realpath_fixture(case, repo_root=fixture.repo)

    def _assert_rejected(self, result, fixture_status):
        self.assertTrue(result.rejected)
        self.assertFalse(result.allowed)
        self.assertTrue(result.expectation_met)
        self.assertEqual(result.fixture_status, fixture_status)
        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.mutation_allowed)
        self.assertFalse(result.write_authority_granted)
        self.assertEqual(result.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)

    def _assert_not_checked_if_unsupported(self, fixture):
        if fixture.support_status == SYMLINK_SUPPORTED:
            return False
        summary = build_symlink_realpath_fixture_summary(
            (),
            symlink_support_status=fixture.support_status,
        )
        verification = verify_symlink_realpath_fixture_summary(summary)

        self.assertTrue(verification.ok, verification.errors)
        self.assertFalse(summary["symlink_realpath_checked"])
        self.assertIn(
            summary["symlink_realpath_support_status"],
            {NOT_CHECKED_SYMLINK_UNSUPPORTED, NOT_CHECKED_PLATFORM_PERMISSION_LIMIT},
        )
        self.assertNotEqual(summary["symlink_realpath_fixture_status"], "PASS")
        return True

    def _fixture_cases(self):
        return (
            SymlinkRealpathFixture(
                case_id="symlink_to_aeg",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=propose_patch_for_paths(["link_to_aeg/evil.json"]),
                expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="symlink_to_outside_repo",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=propose_patch_for_paths(["link_to_outside/outside.txt"]),
                expected_fixture_status=OUTSIDE_REPO_ESCAPE_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="symlink_to_env",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=propose_patch_for_paths(["link_to_env"]),
                expected_fixture_status=ENV_SECRET_ACCESS_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="nested_symlink_chain_to_aeg",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=propose_patch_for_paths(["link_a/evil.json"]),
                expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="traversal_plus_symlink_to_aeg",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=propose_patch_for_paths(["safe_dir/../link_to_aeg/evil.json"]),
                expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="propose_patch_symlink_target_to_aeg",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=propose_patch_for_paths(["link_to_aeg/evil.json"]),
                expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="request_repo_read_symlink_target_to_aeg",
                category=CATEGORY_SYMLINK_REALPATH_ESCAPE,
                action=repo_read_for_paths(["link_to_aeg/ledger.jsonl"]),
                expected_fixture_status=AEG_SCOPE_ESCAPE_REJECTED,
            ),
            SymlinkRealpathFixture(
                case_id="inert_propose_patch_normal_target",
                category=CATEGORY_INERT_DATA,
                action=inert_propose_patch_action("src/normal.py"),
                expected_fixture_status=INERT_PROPOSE_PATCH_DATA_ONLY,
            ),
        )


class TempSymlinkRepo:
    def __enter__(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)
        self.repo = self.root / "repo"
        self.outside = self.root / "outside"
        self.support_status = SYMLINK_SUPPORTED
        self.support_error = None

        self.repo.mkdir()
        self.outside.mkdir()
        (self.repo / ".aeg").mkdir()
        (self.repo / ".aeg" / "ledger.jsonl").write_text("{}\n", encoding="utf-8")
        (self.repo / ".env").write_text("PLACEHOLDER=redacted\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "normal.py").write_text("old data\n", encoding="utf-8")
        (self.repo / "safe_dir").mkdir()
        (self.outside / "outside.txt").write_text("outside\n", encoding="utf-8")

        try:
            (self.repo / "link_to_aeg").symlink_to(
                self.repo / ".aeg",
                target_is_directory=True,
            )
            (self.repo / "link_to_outside").symlink_to(
                self.outside,
                target_is_directory=True,
            )
            (self.repo / "link_to_env").symlink_to(self.repo / ".env")
            (self.repo / "link_b").symlink_to(
                self.repo / ".aeg",
                target_is_directory=True,
            )
            (self.repo / "link_a").symlink_to(
                self.repo / "link_b",
                target_is_directory=True,
            )
        except (OSError, NotImplementedError) as exc:
            self.support_status = NOT_CHECKED_PLATFORM_PERMISSION_LIMIT
            self.support_error = exc

        return self

    def __exit__(self, exc_type, exc, traceback):
        self._tempdir.cleanup()


def snapshot_tree(root: Path) -> tuple[tuple[str, str, str | None], ...]:
    entries: list[tuple[str, str, str | None]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        for name in sorted(dirnames + filenames):
            path = current / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries.append((relative, "symlink", os.readlink(path)))
            elif path.is_dir():
                entries.append((relative, "dir", None))
            else:
                entries.append((relative, "file", path.read_text(encoding="utf-8")))
    return tuple(sorted(entries))


if __name__ == "__main__":
    unittest.main()
