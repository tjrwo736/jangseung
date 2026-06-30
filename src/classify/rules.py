"""Deterministic CLASSIFY heart with Phase 2 impact awareness."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
import re

from src.contracts import (
    CHANGED_FILES_SOURCES,
    GIT_STAGED,
    GIT_TRACKED_DIFF,
    GIT_WORKING_TREE,
    HIGH,
    LOW,
    MEDIUM,
    NO_CHANGED_FILES,
    NO_CHANGED_FILES_SOURCE,
    NOT_CHECKED,
    NOT_CHECKED_SOURCE,
    RISK_LEVELS,
    RISK_ORDER,
)


CHECKED_CHANGED_FILES_SOURCES = (GIT_WORKING_TREE, GIT_STAGED, GIT_TRACKED_DIFF)
FINAL_RISK_RULE_MAX = "max(intent_risk, impact_risk)"
FINAL_RISK_RULE_NO_CHANGED_FILES = "impact_risk=NO_CHANGED_FILES => intent_risk"
FINAL_RISK_RULE_NOT_CHECKED = "impact_risk=NOT_CHECKED => intent_risk with NOT_CHECKED status"


@dataclass(frozen=True)
class Classification:
    intent_risk: str
    impact_risk: str
    risk_level: str
    classification_reasons: list[str]
    impact_reasons: list[str]
    protected_paths_touched: list[str]
    changed_files: list[str]
    changed_files_source: str
    risk_escalation_applied: bool
    final_risk_rule: str

    def as_dict(self) -> dict[str, object]:
        return {
            "intent_risk": self.intent_risk,
            "impact_risk": self.impact_risk,
            "risk_level": self.risk_level,
            "classification_reasons": list(self.classification_reasons),
            "impact_reasons": list(self.impact_reasons),
            "protected_paths_touched": list(self.protected_paths_touched),
            "changed_files": list(self.changed_files),
            "changed_files_source": self.changed_files_source,
            "risk_escalation_applied": self.risk_escalation_applied,
            "final_risk_rule": self.final_risk_rule,
        }


@dataclass(frozen=True)
class ImpactClassification:
    impact_risk: str
    impact_reasons: list[str]
    protected_paths_touched: list[str]
    changed_files: list[str]
    changed_files_source: str

    def as_dict(self) -> dict[str, object]:
        return {
            "impact_risk": self.impact_risk,
            "impact_reasons": list(self.impact_reasons),
            "protected_paths_touched": list(self.protected_paths_touched),
            "changed_files": list(self.changed_files),
            "changed_files_source": self.changed_files_source,
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


PROTECTED_EXACT_PATHS = {
    ".env",
    "Dockerfile",
    "docker-compose.yml",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
}

PROTECTED_PREFIXES = (
    ".github/actions/",
    ".github/workflows/",
    "deploy/",
    "release/",
    "secrets/",
    "src/classify/",
    "src/cli/",
    "src/evidence/",
    "src/law/",
    "src/state/",
)

PROTECTED_GLOBS = (
    ".env.*",
    "docker-compose.*.yml",
    "requirements*.txt",
    "scripts/deploy*",
    "scripts/release*",
)

DOCS_OR_FORMATTING_EXTENSIONS = (
    ".adoc",
    ".markdown",
    ".md",
    ".rst",
    ".txt",
)

DOCS_OR_FORMATTING_NAMES = {
    ".gitignore",
    "CHANGELOG",
    "CHANGELOG.md",
    "LICENSE",
    "README",
    "README.md",
}


def classify_task(
    task_text: str,
    changed_files: Iterable[str] | None = None,
    changed_files_source: str | None = None,
    no_mutation: bool = True,
) -> Classification:
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

    impact = classify_impact(
        changed_files=changed_files,
        changed_files_source=changed_files_source,
        no_mutation=no_mutation,
    )
    risk_level, risk_escalation_applied, final_risk_rule = merge_risks(intent_risk, impact.impact_risk)
    return Classification(
        intent_risk=intent_risk,
        impact_risk=impact.impact_risk,
        risk_level=risk_level,
        classification_reasons=reasons,
        impact_reasons=impact.impact_reasons,
        protected_paths_touched=impact.protected_paths_touched,
        changed_files=impact.changed_files,
        changed_files_source=impact.changed_files_source,
        risk_escalation_applied=risk_escalation_applied,
        final_risk_rule=final_risk_rule,
    )


def classify_impact(
    changed_files: Iterable[str] | None = None,
    changed_files_source: str | None = None,
    no_mutation: bool = False,
) -> ImpactClassification:
    files = _normalize_changed_files(changed_files or [])
    source = _resolve_changed_files_source(files, changed_files_source, no_mutation)

    if source not in CHANGED_FILES_SOURCES:
        return ImpactClassification(
            impact_risk=NOT_CHECKED,
            impact_reasons=["impact.not_checked.invalid_changed_files_source"],
            protected_paths_touched=_protected_paths(files),
            changed_files=files,
            changed_files_source=source,
        )

    if source == NOT_CHECKED_SOURCE:
        return ImpactClassification(
            impact_risk=NOT_CHECKED,
            impact_reasons=["impact.not_checked.changed_files_source_not_checked"],
            protected_paths_touched=_protected_paths(files),
            changed_files=files,
            changed_files_source=source,
        )

    if source == NO_CHANGED_FILES_SOURCE:
        if files:
            return ImpactClassification(
                impact_risk=NOT_CHECKED,
                impact_reasons=["impact.not_checked.no_changed_files_source_with_files"],
                protected_paths_touched=_protected_paths(files),
                changed_files=files,
                changed_files_source=source,
            )
        return ImpactClassification(
            impact_risk=NO_CHANGED_FILES,
            impact_reasons=["impact.no_changed_files"],
            protected_paths_touched=[],
            changed_files=[],
            changed_files_source=source,
        )

    if not files:
        return ImpactClassification(
            impact_risk=NO_CHANGED_FILES,
            impact_reasons=["impact.no_changed_files"],
            protected_paths_touched=[],
            changed_files=[],
            changed_files_source=NO_CHANGED_FILES_SOURCE,
        )

    protected_paths = _protected_paths(files)
    if protected_paths:
        return ImpactClassification(
            impact_risk=HIGH,
            impact_reasons=["impact.high.protected_path_touched"],
            protected_paths_touched=protected_paths,
            changed_files=files,
            changed_files_source=source,
        )

    if all(_is_docs_or_formatting_path(path) for path in files):
        return ImpactClassification(
            impact_risk=LOW,
            impact_reasons=["impact.low.docs_or_formatting_only"],
            protected_paths_touched=[],
            changed_files=files,
            changed_files_source=source,
        )

    if all(_is_tests_path(path) for path in files):
        return ImpactClassification(
            impact_risk=MEDIUM,
            impact_reasons=["impact.medium.tests_only"],
            protected_paths_touched=[],
            changed_files=files,
            changed_files_source=source,
        )

    return ImpactClassification(
        impact_risk=MEDIUM,
        impact_reasons=["impact.medium.non_protected_change"],
        protected_paths_touched=[],
        changed_files=files,
        changed_files_source=source,
    )


def merge_risks(intent_risk: str, impact_risk: str) -> tuple[str, bool, str]:
    if impact_risk in RISK_LEVELS:
        if RISK_ORDER[impact_risk] > RISK_ORDER[intent_risk]:
            return impact_risk, True, FINAL_RISK_RULE_MAX
        return intent_risk, False, FINAL_RISK_RULE_MAX
    if impact_risk == NO_CHANGED_FILES:
        return intent_risk, False, FINAL_RISK_RULE_NO_CHANGED_FILES
    return intent_risk, False, FINAL_RISK_RULE_NOT_CHECKED


def _resolve_changed_files_source(files: list[str], changed_files_source: str | None, no_mutation: bool) -> str:
    if changed_files_source:
        return changed_files_source
    if no_mutation and not files:
        return NO_CHANGED_FILES_SOURCE
    return NOT_CHECKED_SOURCE


def _normalize_changed_files(changed_files: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for path in changed_files:
        item = str(path).strip().replace("\\", "/")
        while item.startswith("./"):
            item = item[2:]
        if item:
            normalized.append(item)
    return sorted(dict.fromkeys(normalized))


def _protected_paths(paths: Iterable[str]) -> list[str]:
    return [path for path in paths if is_protected_path(path)]


def is_protected_path(path: str) -> bool:
    normalized = _normalize_changed_files([path])
    if not normalized:
        return False
    item = normalized[0]

    if item in PROTECTED_EXACT_PATHS:
        return True
    if any(item.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    if any(fnmatchcase(item, pattern) for pattern in PROTECTED_GLOBS):
        return True
    if item.startswith("config/") and any(part.startswith("secrets") for part in item.split("/")[1:]):
        return True
    return False


def _is_docs_or_formatting_path(path: str) -> bool:
    item = _normalize_changed_files([path])[0]
    name = item.rsplit("/", 1)[-1]
    if item.startswith("docs/"):
        return True
    if name in DOCS_OR_FORMATTING_NAMES:
        return True
    return any(name.endswith(extension) for extension in DOCS_OR_FORMATTING_EXTENSIONS)


def _is_tests_path(path: str) -> bool:
    item = _normalize_changed_files([path])[0]
    name = item.rsplit("/", 1)[-1]
    return item.startswith("tests/") or name.startswith("test_") or name.endswith("_test.py")
