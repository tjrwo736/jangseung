"""Minimal deterministic CLASSIFY heart for Day-1."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.contracts import HIGH, LOW, MEDIUM, NO_CHANGED_FILES, NOT_CHECKED_NO_MUTATION


@dataclass(frozen=True)
class Classification:
    intent_risk: str
    impact_risk: str
    risk_level: str
    classification_reasons: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "intent_risk": self.intent_risk,
            "impact_risk": self.impact_risk,
            "risk_level": self.risk_level,
            "classification_reasons": list(self.classification_reasons),
        }


@dataclass(frozen=True)
class Rule:
    risk: str
    reason: str
    patterns: tuple[str, ...]
    require_all: bool = False

    def matches(self, text: str) -> bool:
        checks = [re.search(pattern, text, re.IGNORECASE) is not None for pattern in self.patterns]
        return all(checks) if self.require_all else any(checks)


HIGH_RULES: tuple[Rule, ...] = (
    Rule(HIGH, "intent.high.main_merge", (r"\bmerge\b.*\bmain\b", r"\bmain\b.*\bmerge\b")),
    Rule(HIGH, "intent.high.deploy_release_publish", (r"\bdeploy(?:ment)?\b", r"\brelease\b", r"\bpublish\b")),
    Rule(HIGH, "intent.high.secret_or_credential", (r"\bsecret(?:s)?\b", r"\btoken(?:s)?\b", r"\bapi\s*key\b")),
    Rule(
        HIGH,
        "intent.high.protection_workflow_ci",
        (r"\bbranch\s+protection\b", r"\bworkflow\b", r"\bci\b", r"\bgithub\s+actions\b"),
    ),
    Rule(
        HIGH,
        "intent.high.destructive_or_external_share",
        (r"\bdelete\b", r"\bdrop\b", r"\bdestroy\b", r"\brm\s+-rf\b", r"\bexternal\s+share\b", r"\bshare\s+externally\b"),
    ),
)

LOW_RULES: tuple[Rule, ...] = (
    Rule(LOW, "intent.low.readme_typo", (r"\breadme\b", r"\btypo\b|\bspelling\b|\bgrammar\b"), require_all=True),
    Rule(LOW, "intent.low.docs_only", (r"\bdocs?\s*-?\s*only\b", r"\bdocumentation\s*-?\s*only\b")),
    Rule(LOW, "intent.low.documentation", (r"\bdocumentation\b", r"\bdocs?\b")),
    Rule(LOW, "intent.low.formatting_only", (r"\bformatting\s*-?\s*only\b", r"\bformat\s+only\b", r"\bwhitespace\s+only\b")),
)

MEDIUM_RULES: tuple[Rule, ...] = (
    Rule(
        MEDIUM,
        "intent.medium.code_or_test_change",
        (r"\bcode\b", r"\btest(?:s|ing)?\b", r"\bbug\b", r"\bimplement\b", r"\badd\b", r"\bupdate\b", r"\bchange\b"),
    ),
    Rule(MEDIUM, "intent.medium.small_refactor", (r"\brefactor\b", r"\bcleanup\b")),
    Rule(MEDIUM, "intent.medium.general_fix", (r"\bfix\b",)),
)


def classify_task(task_text: str, changed_files: list[str] | None = None, no_mutation: bool = True) -> Classification:
    text = " ".join(task_text.strip().split())
    reasons: list[str] = []

    for rule in HIGH_RULES:
        if rule.matches(text):
            reasons.append(rule.reason)

    if reasons:
        intent_risk = HIGH
    else:
        for rule in LOW_RULES:
            if rule.matches(text):
                reasons.append(rule.reason)
        if reasons:
            intent_risk = LOW
        else:
            for rule in MEDIUM_RULES:
                if rule.matches(text):
                    reasons.append(rule.reason)
            if reasons:
                intent_risk = MEDIUM
            else:
                intent_risk = MEDIUM
                reasons.append("intent.medium.ambiguous_default")

    impact_risk = _classify_impact(changed_files or [], no_mutation=no_mutation)
    # Day-1 starts from intent because the executor is no-op. This must not
    # remain text-only once a mutating executor exists; changed-file taxonomy
    # must participate in future risk escalation.
    risk_level = intent_risk
    return Classification(
        intent_risk=intent_risk,
        impact_risk=impact_risk,
        risk_level=risk_level,
        classification_reasons=reasons,
    )


def _classify_impact(changed_files: list[str], no_mutation: bool) -> str:
    if no_mutation and not changed_files:
        return NO_CHANGED_FILES
    return NOT_CHECKED_NO_MUTATION
