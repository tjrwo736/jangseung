"""Locate project state without traversing a redirected .aeg directory."""

from pathlib import Path
import stat

from jangseung._resolve import resolved
from jangseung.contracts import STATE_DIR


def state_root(repo_root: str | Path) -> Path:
    """Return the project's lexical state path; a missing directory is allowed.

    Inspect the directory entry itself (including dangling links). Windows
    junctions can look like directories to lstat, so reject reparse points too.
    """

    root = resolved(repo_root) / STATE_DIR
    try:
        info = root.lstat()
    except FileNotFoundError:
        return root
    if not stat.S_ISDIR(info.st_mode) or (
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise ValueError(".aeg must be an unlinked project-local directory")
    return root
