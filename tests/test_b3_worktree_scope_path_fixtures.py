import unittest

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    SAFE_DEFAULT,
)
from src.evidence.b3_worktree_scope_path_fixtures import (
    AEG_SCOPE_OUT_REQUIRED,
    ABSOLUTE_PATH_CANDIDATE,
    AUTHORITY_SNAPSHOT,
    EXPECTED_RED_OR_KNOWN_GAP,
    FUTURE_CLOSURE_REQUIRED,
    IN_WORKTREE_CANDIDATE,
    OUTSIDE_REPO_SCOPE_REQUIRED,
    PARENT_TRAVERSAL_CANDIDATE,
    SIBLING_WORKTREE_CANDIDATE,
    STRUCTURED_TOOL_SCOPE_CANDIDATE,
    SYMLINK_ESCAPE_CANDIDATE,
    UNICODE_AMBIGUITY_CANDIDATE,
    build_fixture_report,
    classify_fixture_case,
    default_fixture_cases,
    fixture_report_digest,
)


class B3WorktreeScopePathFixtureTests(unittest.TestCase):
    def test_default_fixture_set_covers_required_categories(self):
        cases = default_fixture_cases()
        by_id = {case.case_id: case for case in cases}

        self.assertEqual(len(cases), 10)
        for case_id in (
            "normal_in_worktree_relative_path",
            "aeg_direct_path",
            "aeg_via_parent_traversal",
            "outside_repo_via_parent_traversal",
            "absolute_path_outside_repo",
            "sibling_worktree_path",
            "symlink_escape_to_aeg",
            "symlink_escape_to_outside_repo",
            "unicode_path_ambiguity_candidate",
            "structured_tool_broad_filesystem_scope",
        ):
            self.assertIn(case_id, by_id)

    def test_fixture_case_schema_and_expected_classification_match(self):
        for fixture_case in default_fixture_cases():
            with self.subTest(case_id=fixture_case.case_id):
                result = classify_fixture_case(fixture_case)

                self.assertEqual(result.case_id, fixture_case.case_id)
                self.assertEqual(result.input_path, fixture_case.input_path)
                self.assertEqual(result.candidate_type, fixture_case.expected_candidate_type)
                self.assertEqual(result.interpretation, EXPECTED_RED_OR_KNOWN_GAP)
                self.assertIn(FUTURE_CLOSURE_REQUIRED, result.classification_statuses)
                self.assertIn(EXPECTED_RED_OR_KNOWN_GAP, result.classification_statuses)
                for closure in fixture_case.expected_required_closure:
                    self.assertIn(closure, result.required_closure)

    def test_aeg_scope_out_cases_are_classified_without_enforcement_claims(self):
        results = {
            case.case_id: classify_fixture_case(case)
            for case in default_fixture_cases()
            if case.case_id in {"aeg_direct_path", "aeg_via_parent_traversal"}
        }

        self.assertEqual(results["aeg_direct_path"].candidate_type, AEG_SCOPE_OUT_REQUIRED)
        self.assertIn(AEG_SCOPE_OUT_REQUIRED, results["aeg_direct_path"].classification_statuses)
        self.assertEqual(results["aeg_via_parent_traversal"].candidate_type, AEG_SCOPE_OUT_REQUIRED)
        self.assertIn(PARENT_TRAVERSAL_CANDIDATE, results["aeg_via_parent_traversal"].classification_statuses)

    def test_outside_traversal_absolute_and_sibling_cases_are_classified(self):
        results = {case.case_id: classify_fixture_case(case) for case in default_fixture_cases()}

        self.assertEqual(
            results["outside_repo_via_parent_traversal"].candidate_type,
            OUTSIDE_REPO_SCOPE_REQUIRED,
        )
        self.assertIn(
            PARENT_TRAVERSAL_CANDIDATE,
            results["outside_repo_via_parent_traversal"].classification_statuses,
        )
        self.assertEqual(results["absolute_path_outside_repo"].candidate_type, OUTSIDE_REPO_SCOPE_REQUIRED)
        self.assertIn(ABSOLUTE_PATH_CANDIDATE, results["absolute_path_outside_repo"].classification_statuses)
        self.assertEqual(results["sibling_worktree_path"].candidate_type, SIBLING_WORKTREE_CANDIDATE)
        self.assertIn(SIBLING_WORKTREE_CANDIDATE, results["sibling_worktree_path"].classification_statuses)

    def test_symlink_unicode_and_structured_scope_cases_are_classified(self):
        results = {case.case_id: classify_fixture_case(case) for case in default_fixture_cases()}

        self.assertEqual(results["symlink_escape_to_aeg"].candidate_type, SYMLINK_ESCAPE_CANDIDATE)
        self.assertIn(AEG_SCOPE_OUT_REQUIRED, results["symlink_escape_to_aeg"].classification_statuses)
        self.assertEqual(results["symlink_escape_to_outside_repo"].candidate_type, SYMLINK_ESCAPE_CANDIDATE)
        self.assertIn(OUTSIDE_REPO_SCOPE_REQUIRED, results["symlink_escape_to_outside_repo"].classification_statuses)
        self.assertEqual(
            results["unicode_path_ambiguity_candidate"].candidate_type,
            UNICODE_AMBIGUITY_CANDIDATE,
        )
        self.assertEqual(
            results["structured_tool_broad_filesystem_scope"].candidate_type,
            STRUCTURED_TOOL_SCOPE_CANDIDATE,
        )

    def test_fixture_report_is_deterministic_and_preserves_current_authority(self):
        first = build_fixture_report()
        second = build_fixture_report()

        self.assertEqual(first, second)
        self.assertEqual(first["fixture_report_digest"], fixture_report_digest(first))
        self.assertEqual(first["authority_snapshot"], AUTHORITY_SNAPSHOT)
        self.assertEqual(first["authority_snapshot"]["runtime_write_path"], NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(first["authority_snapshot"]["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(first["authority_snapshot"]["phase11a_status"], PHASE11A_NOT_STARTED)
        self.assertEqual(first["authority_snapshot"]["safe_default"], SAFE_DEFAULT)
        self.assertFalse(first["b3_1_b3_2_b3_3_preservation"]["b3_5_status_note_started"])
        self.assertEqual(first["digest_interpretation"], "fixture report digest only; not enforcement proof")


if __name__ == "__main__":
    unittest.main()
