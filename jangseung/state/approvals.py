"""User-owned approval storage, independent of checkout files and environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from jangseung._resolve import resolved
from jangseung._sha256 import sha256


def _user_home() -> Path:
    # HOME, USERPROFILE, XDG_* and the current directory are not authorities: a
    # host can launch a hook with environment settings originating in the project.
    if os.name != "nt":
        import pwd

        return Path(pwd.getpwuid(os.geteuid()).pw_dir)
    import ctypes

    home = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x28, None, 0, home) != 0:  # CSIDL_PROFILE
        raise OSError("cannot locate the current user's profile")
    return Path(home.value)


def _local(info: os.stat_result) -> bool:
    return not (getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _owned(info: os.stat_result) -> bool:
    return os.name == "nt" or (info.st_uid == os.geteuid() and not info.st_mode & 0o022)


def approval_root(project: str | Path, *, create: bool = False) -> Path:
    repo = resolved(Path(project), strict=True)
    identity = repo.stat()
    if not stat.S_ISDIR(identity.st_mode):
        raise ValueError("the approval subject must be a project directory")
    home = _user_home()
    if not home.is_absolute():
        raise ValueError("user profile must be an absolute path")
    info = home.lstat()
    if not stat.S_ISDIR(info.st_mode) or not _local(info) or not _owned(info):
        raise ValueError("personal approvals require an unlinked, user-owned home directory")
    home = resolved(home, strict=True)
    root = home / ".jangseung"
    if repo.is_relative_to(root) or root.is_relative_to(repo):
        raise ValueError("project and personal approval storage must be separate")
    key = sha256(os.fsencode(os.path.normcase(str(repo))) + b"\0" +
                 f"{identity.st_dev}:{identity.st_ino}".encode("ascii")).hexdigest()
    current = home
    for part in (".jangseung", "approvals", key):
        current = current / part
        if create:
            current.mkdir(mode=0o700, exist_ok=True)
        try:
            info = current.lstat()
        except FileNotFoundError:
            # No child can exist below a missing directory. Reads create nothing.
            return root / "approvals" / key
        if not stat.S_ISDIR(info.st_mode) or not _local(info) or not _owned(info):
            raise ValueError("personal approval storage must be an unlinked, user-owned directory")
    return current


def read_small_file(path: Path, limit: int, *, personal: bool = False) -> bytes | None:
    """Absent is not invalid. Never read a link, device, oversized or shared approval file."""

    try:
        before = path.lstat()
    except FileNotFoundError:
        return None

    def valid(info: os.stat_result) -> bool:
        return (stat.S_ISREG(info.st_mode) and _local(info) and info.st_nlink == 1
                and info.st_size <= limit and (not personal or _owned(info)))

    if not valid(before):
        raise ValueError("not a small, unlinked regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
                         | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not valid(opened) or not os.path.samestat(before, opened):
            raise ValueError("approval file changed while opening")
        data = handle.read(limit + 1)
        if len(data) > limit:
            raise ValueError("approval file too large")
        return data


def write_private(path: Path, data: bytes) -> None:
    """Replace an authority file without following or truncating an existing leaf."""

    import tempfile

    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".approval-", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(data)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
