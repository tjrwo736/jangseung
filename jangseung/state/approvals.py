"""User-owned approval storage, independent of checkout files and environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from jangseung._resolve import resolved
from jangseung._sha256 import sha256

_PROFILE_LIST = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
# Hives Windows keeps loaded for its own service accounts; never a person's profile.
_SERVICE_SIDS = frozenset({"S-1-5-18", "S-1-5-19", "S-1-5-20"})


class ApprovalStorageUnavailable(ValueError):
    """This user has no usable place for personal approvals, so none exist.

    The profile folder cannot be found, is a link or belongs to someone else.
    ``aeg policy add`` refuses to write there for the same
    reasons, so nothing a person approved can be waiting in it. That is different
    from storage that exists and cannot be trusted, which stays an error.
    """


def _user_home() -> Path:
    # HOME, USERPROFILE, XDG_* and the current directory are not authorities: a
    # host can launch a hook with environment settings originating in the project.
    if os.name != "nt":
        import pwd

        return Path(pwd.getpwuid(os.geteuid()).pw_dir)
    found = _profile_from_registry()
    if found is not None:
        return found
    import ctypes

    home = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x28, None, 0, home) != 0:  # CSIDL_PROFILE
        raise OSError("cannot locate the current user's profile")
    return Path(home.value)


def _profile_from_registry() -> Path | None:
    """The profile folder Windows records for this user, read without loading ``ctypes``.

    ``ctypes`` and the shell library cost about 13 ms on every hook call. Windows
    keeps each profile's folder under ``HKLM``, which only administrators can
    change, keyed by the user's SID. A process can open its own user's hive under
    ``HKEY_USERS`` and no other person's, so when exactly one is open to it, that
    SID is its own. Anything else (none, several as an administrator sees, a value
    that needs expanding) returns None and the shell is asked instead.
    """

    try:
        import winreg

        mine = []
        index = 0
        while True:
            try:
                name = winreg.EnumKey(winreg.HKEY_USERS, index)
            except OSError:
                break
            index += 1
            if not name.startswith("S-1-") or name.endswith("_Classes") or name in _SERVICE_SIDS:
                continue
            try:
                winreg.CloseKey(winreg.OpenKey(winreg.HKEY_USERS, name))
            except OSError:
                continue
            mine.append(name)
        if len(mine) != 1:
            return None
        access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _PROFILE_LIST + "\\" + mine[0], 0, access) as key:
            value, kind = winreg.QueryValueEx(key, "ProfileImagePath")
    except (OSError, ImportError):
        return None
    if not isinstance(value, str) or "%" in value or not os.path.isabs(value):
        return None
    return Path(value)


def _local(info: os.stat_result) -> bool:
    return not (getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _owned(info: os.stat_result) -> bool:
    return os.name == "nt" or (info.st_uid == os.geteuid() and not info.st_mode & 0o022)


def _project_keys(repo: Path, identity: os.stat_result) -> tuple[str, str]:
    """The folder name approvals for ``repo`` are kept under, and the name 0.3.2 used.

    On Windows, Python 3.12 and later report a 64-bit volume serial in ``st_dev``
    and a file id of up to 128 bits in ``st_ino``; earlier versions report their
    low 32 and 64 bits. Only those low bits go into the name, so a hook and an
    ``aeg`` running on different Python versions find the same approvals.
    """

    device, inode = identity.st_dev, identity.st_ino
    if os.name == "nt":
        device, inode = device & 0xFFFFFFFF, inode & 0xFFFFFFFFFFFFFFFF
    prefix = os.fsencode(os.path.normcase(str(repo))) + b"\0"
    key = sha256(prefix + f"{device}:{inode}".encode("ascii")).hexdigest()
    legacy = sha256(prefix + f"{identity.st_dev}:{identity.st_ino}".encode("ascii")).hexdigest()
    return key, legacy


def approval_root(project: str | Path, *, create: bool = False) -> Path:
    repo = resolved(Path(project), strict=True)
    identity = repo.stat()
    if not stat.S_ISDIR(identity.st_mode):
        raise ValueError("the approval subject must be a project directory")
    try:
        home = _user_home()
    except (OSError, KeyError, RuntimeError, ValueError) as exc:
        raise ApprovalStorageUnavailable("the user's profile folder cannot be located") from exc
    try:
        usable = home.is_absolute()
        info = home.lstat() if usable else None
        located = resolved(home, strict=True) if usable else None
    except OSError as exc:
        raise ApprovalStorageUnavailable("the user's profile folder cannot be inspected") from exc
    if located is not None:
        root = located / ".jangseung"
        # Checked before anything else and never relaxed: a project that holds, or
        # sits inside, the storage could write approval files as ordinary project files.
        if repo.is_relative_to(root) or root.is_relative_to(repo):
            raise ValueError("project and personal approval storage must be separate")
    if info is None or not stat.S_ISDIR(info.st_mode) or not _local(info) or not _owned(info):
        raise ApprovalStorageUnavailable("personal approvals require an unlinked, user-owned home directory")
    home = located
    key, legacy = _project_keys(repo, identity)
    current = home
    for part in (".jangseung", "approvals", key):
        parent = current
        current = current / part
        if part == key and legacy != key:
            current = _adopt_0_3_2_folder(parent, key, legacy, create=create)
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


def _adopt_0_3_2_folder(parent: Path, key: str, legacy: str, *, create: bool) -> Path:
    """Keep approvals 0.3.2 stored under a name that depended on the Python version.

    A read uses that folder where it is; the next write renames it to the stable name.
    """

    wanted, old = parent / key, parent / legacy
    if os.path.lexists(wanted) or not os.path.lexists(old):
        return wanted
    if not create:
        return old
    try:
        os.rename(old, wanted)
    except OSError:
        return old
    return wanted


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
