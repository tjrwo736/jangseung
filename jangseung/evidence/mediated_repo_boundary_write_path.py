"""Phase 10-E4 mediated outside-repo write path denial helper.

The helper models an in-process mediated write request for targets that
canonicalize outside the repository boundary, calls the E2 deny-only mediator
skeleton, and returns a repo-boundary denial result without writing. It is not
OS, filesystem, or external enforcement and raw/direct writes remain bypassable.
"""

from __future__ import annotations

from jangseung.records import asdict, dataclass
from jangseung._sha256 import sha256
import json
import os
from pathlib import Path, PureWindowsPath

from jangseung._resolve import resolved as _resolved

TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Any



@dataclass(frozen=True)
class RepoBoundaryPathResolution:
    """Canonical repo-boundary path view used by the Phase 10-E4 policy."""

    repo_root: str
    submitted_target: str
    absolute_target: str
    canonical_target: str
    target_under_repo: bool
    target_outside_repo: bool

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def resolve_repo_boundary_path(
    *,
    repo_root: str | Path,
    submitted_target: str | Path,
) -> RepoBoundaryPathResolution:
    windows_resolution = _resolve_windows_repo_boundary_path(
        repo_root=repo_root,
        submitted_target=submitted_target,
    )
    if windows_resolution is not None:
        return windows_resolution

    repo_root_path = _resolved(repo_root)
    submitted_path = Path(submitted_target)
    absolute_target = submitted_path if submitted_path.is_absolute() else repo_root_path / submitted_path
    canonical_target = _resolved(absolute_target)
    target_under_repo = _is_relative_to_or_same(canonical_target, repo_root_path)
    return RepoBoundaryPathResolution(
        repo_root=str(repo_root_path),
        submitted_target=str(submitted_target),
        absolute_target=str(absolute_target),
        canonical_target=str(canonical_target),
        target_under_repo=target_under_repo,
        target_outside_repo=not target_under_repo,
    )


def _resolve_windows_repo_boundary_path(
    *,
    repo_root: str | Path,
    submitted_target: str | Path,
) -> RepoBoundaryPathResolution | None:
    # On a real Windows host, defer to the generic filesystem resolver in
    # resolve_repo_boundary_path so that Path.resolve() canonicalizes the target
    # (expanding 8.3 short names such as ``RUNNER~1`` -> ``runneradmin`` and
    # resolving symlinks). This purely-lexical PureWindowsPath branch only models
    # Windows-style path strings when analyzed on a non-Windows host, where
    # Path.resolve() cannot interpret a ``C:\\`` drive path.
    if os.name == "nt":
        return None

    repo_root_value = str(repo_root)
    submitted_value = str(submitted_target)
    repo_root_path = PureWindowsPath(repo_root_value)
    submitted_path = PureWindowsPath(submitted_value)
    repo_root_is_windows_absolute = repo_root_path.is_absolute()
    submitted_is_windows_absolute = submitted_path.is_absolute()

    if not repo_root_is_windows_absolute and not submitted_is_windows_absolute:
        return None

    if not repo_root_is_windows_absolute:
        canonical_target = _normalize_absolute_windows_path(submitted_path)
        target = canonical_target if canonical_target is not None else submitted_path
        return RepoBoundaryPathResolution(
            repo_root=str(_resolved(repo_root)),
            submitted_target=submitted_value,
            absolute_target=str(target),
            canonical_target=str(target),
            target_under_repo=False,
            target_outside_repo=True,
        )

    canonical_repo_root = _normalize_absolute_windows_path(repo_root_path)
    if canonical_repo_root is None:
        return RepoBoundaryPathResolution(
            repo_root=repo_root_value,
            submitted_target=submitted_value,
            absolute_target=submitted_value,
            canonical_target=submitted_value,
            target_under_repo=False,
            target_outside_repo=True,
        )

    if submitted_is_windows_absolute:
        absolute_target = submitted_path
    elif submitted_path.drive or submitted_path.root:
        return RepoBoundaryPathResolution(
            repo_root=str(canonical_repo_root),
            submitted_target=submitted_value,
            absolute_target=str(submitted_path),
            canonical_target=str(submitted_path),
            target_under_repo=False,
            target_outside_repo=True,
        )
    else:
        absolute_target = canonical_repo_root / submitted_path

    canonical_target = _normalize_absolute_windows_path(absolute_target)
    if canonical_target is None:
        return RepoBoundaryPathResolution(
            repo_root=str(canonical_repo_root),
            submitted_target=submitted_value,
            absolute_target=str(absolute_target),
            canonical_target=str(absolute_target),
            target_under_repo=False,
            target_outside_repo=True,
        )

    target_under_repo = _is_windows_relative_to_or_same(canonical_target, canonical_repo_root)
    return RepoBoundaryPathResolution(
        repo_root=str(canonical_repo_root),
        submitted_target=submitted_value,
        absolute_target=str(absolute_target),
        canonical_target=str(canonical_target),
        target_under_repo=target_under_repo,
        target_outside_repo=not target_under_repo,
    )


def _normalize_absolute_windows_path(path: PureWindowsPath) -> PureWindowsPath | None:
    if not path.is_absolute():
        return None

    normalized_parts: list[str] = []
    for part in path.parts[1:]:
        if part == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(part)
    return PureWindowsPath(path.anchor, *normalized_parts)


def _is_windows_relative_to_or_same(path: PureWindowsPath, root: PureWindowsPath) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_relative_to_or_same(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "RepoBoundaryPathResolution",
    "resolve_repo_boundary_path",
]
