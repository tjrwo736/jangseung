import unittest

from src.classify import classify_task, is_protected_path
from src.contracts import (
    CLEAN_CORE,
    GIT_WORKING_TREE,
    HIGH,
    LOW,
    MEDIUM,
    NEEDS_USER_GATE,
    NO_CHANGED_FILES,
    NO_CHANGED_FILES_SOURCE,
    NOT_CHECKED,
    SAFE_DEFAULT,
)
from src.law import apply_law


class ClassifyLawTests(unittest.TestCase):
    def test_readme_typo_is_low(self):
        result = classify_task("fix typo in README")
        self.assertEqual(result.intent_risk, LOW)
        self.assertEqual(result.risk_level, LOW)
        self.assertEqual(result.impact_risk, NO_CHANGED_FILES)
        self.assertIn("intent.low.readme_typo", result.classification_reasons)

    def test_merge_deploy_is_high(self):
        result = classify_task("merge to main and deploy")
        self.assertEqual(result.intent_risk, HIGH)
        self.assertEqual(result.risk_level, HIGH)
        self.assertIn("intent.high.deploy_release_publish", result.classification_reasons)

    def test_ambiguous_task_is_not_low(self):
        result = classify_task("do the thing")
        self.assertIn(result.intent_risk, {MEDIUM, HIGH})
        self.assertNotEqual(result.intent_risk, LOW)

    def test_low_law_is_clean_core(self):
        law = apply_law(classify_task("fix typo in README"))
        self.assertEqual(law.status, CLEAN_CORE)

    def test_high_law_requires_user_gate(self):
        law = apply_law(classify_task("merge to main and deploy"))
        self.assertEqual(law.status, NEEDS_USER_GATE)
        self.assertIn("law.high.requires_user_gate", law.status_reasons)
        self.assertIsNotNone(law.user_gate_reason_card)
        card = law.user_gate_reason_card or {}
        self.assertEqual(card["risk_level"], HIGH)
        self.assertEqual(card["status"], NEEDS_USER_GATE)
        self.assertEqual(card["safe_default"], SAFE_DEFAULT)
        self.assertTrue(card["irreversible_action_blocked"])
        self.assertIn("explicit user gate", card["why_gate_is_required"])

    def test_medium_law_is_not_clean_core_by_default(self):
        law = apply_law(classify_task("do the thing"))
        self.assertEqual(law.status, NOT_CHECKED)
        self.assertNotEqual(law.status, CLEAN_CORE)
        self.assertIn("law.medium.evidence_binding_required", law.status_reasons)
        self.assertIn("law.medium.completion_contract_placeholder_required", law.status_reasons)

    def test_docs_only_change_has_low_impact(self):
        result = classify_task(
            "update documentation",
            changed_files=["docs/phase2.md", "README.md"],
            changed_files_source=GIT_WORKING_TREE,
            no_mutation=False,
        )
        self.assertEqual(result.impact_risk, LOW)
        self.assertEqual(result.risk_level, LOW)
        self.assertIn("impact.low.docs_or_formatting_only", result.impact_reasons)

    def test_normal_non_protected_src_change_has_medium_impact(self):
        result = classify_task(
            "fix typo in README",
            changed_files=["src/agents/noop.py"],
            changed_files_source=GIT_WORKING_TREE,
            no_mutation=False,
        )
        self.assertEqual(result.intent_risk, LOW)
        self.assertEqual(result.impact_risk, MEDIUM)
        self.assertEqual(result.risk_level, MEDIUM)

    def test_tests_only_change_has_medium_impact(self):
        result = classify_task(
            "fix typo in README",
            changed_files=["tests/test_cli_runtime.py"],
            changed_files_source=GIT_WORKING_TREE,
            no_mutation=False,
        )
        self.assertEqual(result.impact_risk, MEDIUM)
        self.assertEqual(result.risk_level, MEDIUM)

    def test_protected_taxonomy_paths_are_high_impact(self):
        protected_paths = [
            ".github/workflows/ci.yml",
            ".env",
            "scripts/deploy_prod.sh",
            "src/classify/rules.py",
        ]
        for path in protected_paths:
            with self.subTest(path=path):
                result = classify_task(
                    "fix typo in README",
                    changed_files=[path],
                    changed_files_source=GIT_WORKING_TREE,
                    no_mutation=False,
                )
                self.assertTrue(is_protected_path(path))
                self.assertEqual(result.impact_risk, HIGH)
                self.assertEqual(result.risk_level, HIGH)
                self.assertEqual(result.protected_paths_touched, [path])
                self.assertTrue(result.risk_escalation_applied)

    def test_protected_taxonomy_v0_representative_patterns(self):
        protected_paths = [
            ".github/actions/build/action.yml",
            ".github/workflows/ci.yml",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.prod.yml",
            "pyproject.toml",
            "requirements-dev.txt",
            "setup.py",
            "setup.cfg",
            "src/cli/main.py",
            "src/classify/rules.py",
            "src/law/gates.py",
            "src/evidence/packet.py",
            "src/state/git.py",
            ".env",
            ".env.local",
            "secrets/prod.key",
            "config/prod/secrets.yml",
            "release/v1.txt",
            "deploy/prod.yml",
            "scripts/release_notes.sh",
            "scripts/deploy_prod.sh",
        ]
        for path in protected_paths:
            with self.subTest(path=path):
                self.assertTrue(is_protected_path(path))
        self.assertFalse(is_protected_path("src/agents/noop.py"))

    def test_low_intent_plus_protected_path_escalates_final_risk_to_high(self):
        result = classify_task(
            "fix typo in README",
            changed_files=[".github/workflows/ci.yml"],
            changed_files_source=GIT_WORKING_TREE,
            no_mutation=False,
        )
        self.assertEqual(result.intent_risk, LOW)
        self.assertEqual(result.impact_risk, HIGH)
        self.assertEqual(result.risk_level, HIGH)
        self.assertEqual(apply_law(result).status, NEEDS_USER_GATE)

    def test_no_changed_files_final_risk_follows_intent(self):
        result = classify_task(
            "fix typo in README",
            changed_files=[],
            changed_files_source=NO_CHANGED_FILES_SOURCE,
        )
        self.assertEqual(result.impact_risk, NO_CHANGED_FILES)
        self.assertEqual(result.risk_level, LOW)
        self.assertEqual(apply_law(result).status, CLEAN_CORE)

    def test_missing_changed_files_source_is_not_clean_pass(self):
        result = classify_task(
            "fix typo in README",
            changed_files=["README.md"],
            changed_files_source=None,
            no_mutation=False,
        )
        self.assertEqual(result.intent_risk, LOW)
        self.assertEqual(result.impact_risk, NOT_CHECKED)
        self.assertEqual(result.risk_level, LOW)
        self.assertEqual(apply_law(result).status, NOT_CHECKED)


if __name__ == "__main__":
    unittest.main()
