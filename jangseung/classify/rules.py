"""Deterministic CLASSIFY heart with Phase 2 impact awareness."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
import re

from jangseung.contracts import (
    CHANGED_FILES_SOURCES,
    HIGH,
    LOW,
    MEDIUM,
    NO_CHANGED_FILES,
    NO_CHANGED_FILES_SOURCE,
    NOT_CHECKED,
    NOT_CHECKED_SOURCE,
    RISK_LEVELS,
    RISK_ORDER,
    STATE_DIR,
)


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


# Paths below are compared after _policy_parts(), so they are lower case here.
PROTECTED_EXACT_PATHS = {
    ".env",
    ".gitlab-ci.yml",
    ".travis.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "jenkinsfile",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
}

# Container builds run from any directory of a project, so depth does not matter.
PROTECTED_FILE_NAME_GLOBS = (
    "dockerfile",
    "dockerfile.*",
    "*.dockerfile",
    "docker-compose.yml",
    "docker-compose.*.yml",
)

PROTECTED_PREFIXES = (
    ".circleci/",
    ".github/actions/",
    ".github/workflows/",
    "deploy/",
    "release/",
    "secrets/",
    "jangseung/classify/",
    "jangseung/cli/",
    "jangseung/evidence/",
    "jangseung/law/",
    "jangseung/state/",
)

PROTECTED_GLOBS = (
    "requirements*.txt",
    "scripts/deploy*",
    "scripts/release*",
)

# The guard's own configuration and state. Nothing, including a project policy,
# can make these writable: an agent that edits them can turn the guard off.
GUARD_DIRECTORY_NAMES = frozenset({".aeg", ".git", ".codex", ".husky"})
GUARD_FILE_NAMES = frozenset({".mcp.json", ".claude.json", ".gitconfig", ".gitmodules"})
CLAUDE_DIRECTORY = ".claude"
CLAUDE_AGENT_AUTHORED_DIRECTORIES = frozenset({"commands", "agents", "skills", "worktrees"})
CLAUDE_WORKTREES_DIRECTORY = "worktrees"

SECRET_DIRECTORY_NAMES = frozenset(
    {"secret", "secrets", ".ssh", ".gnupg", ".aws", ".azure", ".gcloud", ".kube"}
)
SECRET_FILE_NAMES = frozenset(
    {
        ".env",
        ".envrc",
        ".npmrc",
        ".pypirc",
        ".netrc",
        "_netrc",
        ".git-credentials",
        ".dockercfg",
        ".htpasswd",
        "credentials",
        "credentials.json",
        "application_default_credentials.json",
        "secrets.json",
        "secrets.yml",
        "secrets.yaml",
        "secrets.toml",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
)
SECRET_FILE_GLOBS = (
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "*.ppk",
    "*.tfvars",
    "service-account*.json",
)
SECRET_SUBPATHS = ((".docker", "config.json"),)
ENV_TEMPLATE_SUFFIXES = frozenset({"example", "sample", "template", "dist", "defaults", "tpl"})

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
    protected_check: Callable[[str], bool] | None = None,
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
        protected_check=protected_check,
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
    protected_check: Callable[[str], bool] | None = None,
) -> ImpactClassification:
    files = _normalize_changed_files(changed_files or [])
    source = _resolve_changed_files_source(files, changed_files_source, no_mutation)

    if source not in CHANGED_FILES_SOURCES:
        return ImpactClassification(
            impact_risk=NOT_CHECKED,
            impact_reasons=["impact.not_checked.invalid_changed_files_source"],
            protected_paths_touched=_protected_paths(files, protected_check),
            changed_files=files,
            changed_files_source=source,
        )

    if source == NOT_CHECKED_SOURCE:
        return ImpactClassification(
            impact_risk=NOT_CHECKED,
            impact_reasons=["impact.not_checked.changed_files_source_not_checked"],
            protected_paths_touched=_protected_paths(files, protected_check),
            changed_files=files,
            changed_files_source=source,
        )

    if source == NO_CHANGED_FILES_SOURCE:
        if files:
            return ImpactClassification(
                impact_risk=NOT_CHECKED,
                impact_reasons=["impact.not_checked.no_changed_files_source_with_files"],
                protected_paths_touched=_protected_paths(files, protected_check),
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

    protected_paths = _protected_paths(files, protected_check)
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


def _protected_paths(paths: Iterable[str], protected_check: Callable[[str], bool] | None = None) -> list[str]:
    check = is_protected_path if protected_check is None else protected_check
    return [path for path in paths if check(path)]


@dataclass(frozen=True)
class PathPolicy:
    """Project-specific path exceptions; see ``jangseung.classify.hook_policy``."""

    allow_paths: tuple[str, ...] = ()
    protect_paths: tuple[str, ...] = ()

    def allows(self, parts: tuple[str, ...]) -> bool:
        return _matches_any(parts, self.allow_paths)

    def protects(self, parts: tuple[str, ...]) -> bool:
        return _matches_any(parts, self.protect_paths)


# str.strip() and JavaScript's trim() disagree on a few characters. A host that
# trims a path before opening it must not open a different path from the one judged.
_PATH_PADDING = (
    " \t\n\v\f\r\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


def strip_path_decorations(path: str) -> str:
    """Remove spelling that Windows ignores when it opens a path.

    Trailing dots and spaces and ``:stream`` suffixes name the same file on
    NTFS. They are removed on every platform so the judgment stays conservative.
    A drive-relative ``C:x`` loses its prefix so the rules still see the name ``x``;
    ``is_host_resolved_path`` is what keeps such a path out of the project.
    """

    text = str(path).strip(_PATH_PADDING).replace("\\", "/")
    drive, rest = (text[:2], text[2:]) if re.match(r"^[A-Za-z]:(?=/)", text) else ("", text)
    if not drive and re.match(r"^[A-Za-z]:", rest):
        rest = rest[2:]
    cleaned = []
    for part in rest.split("/"):
        cleaned.append(part if part in {".", ".."} else part.split(":", 1)[0].rstrip(". "))
    return drive + "/".join(cleaned)


def is_host_resolved_path(path: str) -> bool:
    """True for a spelling the host resolves itself, outside any project judgment.

    ``~`` is the user's home and ``C:x`` is relative to that drive's own current
    directory, so what they name cannot be told from the path alone.
    """

    text = str(path).strip(_PATH_PADDING).replace("\\", "/")
    return text == "~" or text.startswith("~/") or bool(re.match(r"^[A-Za-z]:(?!/)", text))


def _policy_parts(path: str) -> tuple[str, ...]:
    """Case-folded path components with no spelling aliases left."""

    text = strip_path_decorations(path)
    if re.match(r"^[A-Za-z]:/", text):
        text = text[2:]
    return tuple(part.casefold() for part in text.split("/") if part and part != ".")


def _matches_any(parts: tuple[str, ...], patterns: Iterable[str]) -> bool:
    item = "/".join(parts)
    for pattern in patterns:
        pattern_parts = _policy_parts(pattern)
        if not pattern_parts:
            continue
        joined = "/".join(pattern_parts)
        if item == joined or item.startswith(f"{joined}/") or fnmatchcase(item, joined):
            return True
        if len(pattern_parts) == 1 and fnmatchcase(parts[-1], joined):
            return True
    return False


def _is_guard_path(parts: tuple[str, ...]) -> bool:
    for index, part in enumerate(parts):
        if part in GUARD_DIRECTORY_NAMES or part in GUARD_FILE_NAMES:
            return True
        if part == CLAUDE_DIRECTORY:
            following = parts[index + 1 : index + 2]
            if following and following[0] not in CLAUDE_AGENT_AUTHORED_DIRECTORIES:
                return True
    return False


def _without_claude_worktree(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Judge ``.claude/worktrees/<name>/x`` as ``x``: it is the same repository."""

    for index in range(len(parts) - 2):
        if parts[index] == CLAUDE_DIRECTORY and parts[index + 1] == CLAUDE_WORKTREES_DIRECTORY:
            return parts[index + 3 :]
    return parts


def _is_builtin_secret(parts: tuple[str, ...]) -> bool:
    if any(part in SECRET_DIRECTORY_NAMES for part in parts):
        return True
    if any(parts[index : index + len(sub)] == sub for sub in SECRET_SUBPATHS for index in range(len(parts))):
        return True
    name = parts[-1]
    if name in SECRET_FILE_NAMES:
        return True
    if name.startswith(".env.") and name.rsplit(".", 1)[-1] not in ENV_TEMPLATE_SUFFIXES:
        return True
    return any(fnmatchcase(name, pattern) for pattern in SECRET_FILE_GLOBS)


def is_secret_path(path: str, policy: PathPolicy | None = None) -> bool:
    """True for a path whose content must not reach an agent, at any depth."""

    parts = _policy_parts(path)
    if not parts or not _is_builtin_secret(parts):
        return False
    return policy is None or not policy.allows(parts)


def is_protected_path(path: str, policy: PathPolicy | None = None) -> bool:
    """True for a path an agent must not change."""

    parts = _policy_parts(path)
    if not parts:
        return False
    if _is_guard_path(parts):
        return True
    if policy is not None and policy.protects(parts):
        return True
    if policy is not None and policy.allows(parts):
        return False
    if _is_builtin_secret(parts):
        return True

    if any(fnmatchcase(parts[-1], pattern) for pattern in PROTECTED_FILE_NAME_GLOBS):
        return True
    item = "/".join(_without_claude_worktree(parts))
    if item in PROTECTED_EXACT_PATHS:
        return True
    if any(item.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    if any(fnmatchcase(item, pattern) for pattern in PROTECTED_GLOBS):
        return True
    if item.startswith("config/") and any(part.startswith("secrets") for part in item.split("/")[1:]):
        return True
    return False


def contains_protected_path(path: str) -> bool:
    """True when deleting or moving this directory would take protected paths with it."""

    parts = _policy_parts(path)
    if not parts:
        return True
    item = f"{'/'.join(parts)}/"
    return any(prefix.startswith(item) for prefix in PROTECTED_PREFIXES)


def is_read_protected_path(path: str, policy: PathPolicy | None = None) -> bool:
    """True for a path an agent must not read; build files stay readable."""

    parts = _policy_parts(path)
    if not parts:
        return False
    return STATE_DIR in parts or is_secret_path(path, policy)


def _any_case(glob: str) -> str:
    return "".join(f"[{char}{char.upper()}]" if char.isalpha() else char for char in glob)


def _exclusion_rules(policy: PathPolicy | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Name patterns of read-protected folders and files, for tools that can only exclude.

    Re-including one file would turn the rest of the project off. So ``.env.*`` also
    skips templates, and an approval in the policy reopens a file rule only when it
    covers the whole rule. It never reopens a folder rule: approving ``secrets`` opens
    that one folder, while ``deep/secrets`` stays protected. All of these stay readable
    by name when the gates allow it.
    """

    folders = (STATE_DIR, *sorted(SECRET_DIRECTORY_NAMES), *("/".join(parts) for parts in SECRET_SUBPATHS))
    files = (*sorted(SECRET_FILE_NAMES), ".env.*", *SECRET_FILE_GLOBS)
    return folders, tuple(rule for rule in files if policy is None or not policy.allows(_policy_parts(rule)))


def search_exclusion_globs(policy: PathPolicy | None = None) -> tuple[str, ...]:
    """Ripgrep globs that keep a directory search out of read-protected files."""

    folders, files = _exclusion_rules(policy)
    # A name without a slash matches at any depth; a nested rule has to ask for that.
    return tuple(f"!{'**/' if '/' in rule else ''}{_any_case(rule)}" for rule in (*folders, *files))


def git_exclusion_pathspecs(
    policy: PathPolicy | None = None,
    *,
    named_files: Iterable[str] = (),
) -> tuple[str, ...]:
    """Pathspecs that keep git output out of read-protected files, tracked or in history.

    ``named_files`` passed the read gates, so a rule that would hide them is left out.
    """

    names = [parts[-1] for parts in map(_policy_parts, named_files) if parts]
    folders, files = _exclusion_rules(policy)
    specs: list[str] = []
    for rule in folders:
        specs += [f":(top,exclude,glob,icase)**/{rule}", f":(top,exclude,glob,icase)**/{rule}/**"]
    for rule in files:
        if not any(fnmatchcase(name, rule) for name in names):
            specs.append(f":(top,exclude,glob,icase)**/{rule}")
    return tuple(specs)


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
