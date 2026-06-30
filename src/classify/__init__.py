"""Deterministic task and impact classification."""

from src.classify.rules import Classification, ImpactClassification, classify_impact, classify_task, is_protected_path, merge_risks

__all__ = [
    "Classification",
    "ImpactClassification",
    "classify_impact",
    "classify_task",
    "is_protected_path",
    "merge_risks",
]
