import unittest

from src.classify import classify_task
from src.contracts import CLEAN_CORE, HIGH, LOW, MEDIUM, NEEDS_USER_GATE
from src.law import apply_law


class ClassifyLawTests(unittest.TestCase):
    def test_readme_typo_is_low(self):
        result = classify_task("fix typo in README")
        self.assertEqual(result.intent_risk, LOW)
        self.assertEqual(result.risk_level, LOW)
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


if __name__ == "__main__":
    unittest.main()
