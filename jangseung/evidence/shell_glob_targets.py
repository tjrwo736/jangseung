"""Which existing project files a wildcard word in a shell command would reach.

Read-only: it lists directories and returns names. It decides nothing; the caller
judges each name with the same path rules as a literal argument.

The command text comes from the agent, so two things are fixed in advance:

* Only folders inside the project are ever listed. The check is made on the text
  of the path, before the file system is touched: a wildcard under ``\\\\host\\share``
  or another drive must not make the hook open a network connection.
* Every call shares one ``GlobBudget``. When it runs out the listing stops and
  nothing more is claimed.
"""

from __future__ import annotations

from collections.abc import Sequence
from fnmatch import fnmatchcase
from functools import lru_cache
import os
from pathlib import Path
import stat

GLOB_CHARACTERS = frozenset("*?[")
MAX_GLOB_WORD_LENGTH = 512
MAX_GLOB_PARTS = 40
MAX_WILDCARD_PARTS = 6
MAX_GLOB_CANDIDATES = 1024
MAX_RECURSION_DEPTH = 8

_WORKING_FOLDER_VARIABLES = ("$pwd", "${pwd}", "~+")

# Programs that use the matched names without opening the files. ``ls .env`` is
# allowed, so ``ls .en?`` is not treated as reaching the secret either. This only
# holds while no other command in the same line reads files: ``ls .en? | xargs cat``
# and ``cat $(ls .en?)`` pass the names on, and the caller checks for that.
_NAMES_ONLY_PROGRAMS = frozenset(
    {
        "ls", "dir", "test", "[", "[[", "stat", "du", "tree", "echo", "printf", "basename", "dirname",
        "realpath", "readlink", "which", "mkdir", "case", "esac", "fi", "done",
    }
)
_FIND_ACTIONS = frozenset({"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls", "-fprint0"})
_GIT_NAMES_ONLY_SUBCOMMANDS = frozenset({"status", "add", "ls-files", "ls-tree", "branch", "tag", "check-ignore"})
# PowerShell hands a wildcard to the command itself, and only file commands read
# what it matches: ``Get-Process *e*`` and ``git tag -l '*v*'`` name no file.
_POWERSHELL_FILE_COMMANDS = frozenset(
    {
        "get-content", "gc", "cat", "type", "select-string", "sls", "findstr", "more", "copy-item", "cp", "copy",
        "cpi", "move-item", "mv", "move", "mi", "rename-item", "ren", "rni", "remove-item", "rm", "del", "erase",
        "ri", "rd", "rmdir", "import-csv", "ipcsv", "get-filehash", "format-hex", "fhx", "invoke-item", "ii",
        "compress-archive", "certutil", "notepad", "code", "start",
    }
)
# An argument in one of these places is a pattern for the program, not a file the
# shell hands it: ``tar --exclude '.e*'``, ``grep -rn '.en?' src``.
_PATTERN_OPTIONS = frozenset(
    {
        "--exclude", "--exclude-dir", "--include", "-name", "-iname", "-path", "-ipath", "-wholename",
        "-iwholename", "-regex", "-iregex", "--ignore", "--glob", "--iglob",
    }
)
_PATTERN_FIRST_PROGRAMS = frozenset(
    {"grep", "egrep", "fgrep", "rg", "ag", "ack", "jq", "yq", "sed", "awk", "gawk", "mawk"}
)
_PATTERN_PROGRAM_OPTIONS = frozenset({"-e", "--regexp", "-g", "-f", "--file"})
_ARCHIVE_EXCLUDE_PROGRAMS = frozenset({"zip", "unzip", "7z"})
_REPARSE_POINT = 0x400


def project_roots(repo_root: str | Path, base_dir: str | Path) -> tuple[str, ...]:
    """Every spelling of the project folder that the hook itself was given.

    The working folder may reach the project through a link or a short name, and
    then no path under it starts with the project root as text. Only paths the
    host supplied are resolved here, never text from the command.
    """

    roots = [_as_text(repo_root)]
    try:
        real_root = os.path.normcase(os.path.realpath(str(repo_root)))
        real_base = os.path.normcase(os.path.realpath(str(base_dir)))
        roots.append(real_root)
        if os.path.commonpath([real_base, real_root]) == real_root:
            depth = 0 if real_base == real_root else len(os.path.relpath(real_base, real_root).split(os.sep))
            alias = _as_text(os.path.join(str(base_dir), *([".."] * depth)))
            if os.path.normcase(os.path.realpath(alias)) == real_root:
                roots.append(alias)
    except (OSError, ValueError):
        pass
    return tuple(dict.fromkeys(roots))


def _as_text(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


class GlobBudget:
    """How much one hook call may list, and where: only inside the project."""

    def __init__(self, roots: str | Path | Sequence[str], directories: int = 64, entries: int = 6000) -> None:
        if isinstance(roots, (str, Path)):
            roots = (_as_text(roots),)
        self._roots = tuple(roots)
        self._plain_folders: set[str] = set()
        self.directories = directories
        self.entries = entries

    def allows(self, folder: str | Path) -> bool:
        """True when ``folder`` is the project or below it, judged from the text alone."""

        return self._root_of(folder) is not None

    def _root_of(self, folder: str | Path) -> tuple[str, str] | None:
        text = str(folder)
        if "\x00" in text:
            return None
        try:
            path = os.path.normcase(os.path.abspath(text))
        except (ValueError, OSError):
            return None
        for root in self._roots:
            try:
                if os.path.commonpath([path, root]) == root:
                    return path, root
            except (ValueError, OSError):  # Another drive, a share, a malformed path.
                continue
        return None

    def _passes_a_link(self, path: str, root: str) -> bool:
        """A link or junction between the project root and ``path`` may lead outside."""

        if path == root:
            return False
        current = root
        for part in os.path.relpath(path, root).split(os.sep):
            current = os.path.join(current, part)
            if current in self._plain_folders:
                continue
            try:
                info = os.lstat(current)
            except (OSError, ValueError):
                return True
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
                return True
            self._plain_folders.add(current)
        return False

    def _scan(self, folder: Path, *, folders_only: bool) -> list[str]:
        if self.directories <= 0 or self.entries <= 0:
            return []
        placed = self._root_of(folder)
        if placed is None or self._passes_a_link(*placed):
            return []
        self.directories -= 1
        names: list[str] = []
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if self.entries <= 0:
                        break
                    self.entries -= 1
                    if folders_only:
                        try:
                            if not entry.is_dir(follow_symlinks=False):
                                continue
                        except OSError:
                            continue
                    names.append(entry.name)
        except (OSError, ValueError):
            return []
        return names

    def list_names(self, folder: Path) -> list[str]:
        return self._scan(folder, folders_only=False)

    def list_folders(self, folder: Path) -> list[str]:
        return self._scan(folder, folders_only=True)


def has_glob(word: str) -> bool:
    return bool(GLOB_CHARACTERS.intersection(word))


def names_something(word: str) -> bool:
    """False for a bare ``*``, ``.*`` or ``*.*``, which name no particular file.

    Those words are also arithmetic, a regular expression or "every property" in
    everyday commands, so matching them against the folder would stop ordinary
    work. They stay with the person asked, as before.
    """

    return any(char.isalnum() for char in word)


def glob_forms(word: str, *, windows_style: bool) -> tuple[str, ...]:
    """The path a word hands to the command: itself, or the value of ``-Path:value``.

    ``--exclude=.e*`` is not here: a POSIX shell expands a word as a whole, so the
    part after ``=`` reaches the program as a pattern, not as file names.
    """

    if not word.startswith("-"):
        return (word,)
    if windows_style and ":" in word:
        value = word.split(":", 1)[1]
        return (value,) if value else ()
    return ()


def reads_matched_files(argv: Sequence[str], program: str, git_verb: str | None, *, windows_style: bool) -> bool:
    """Whether the command opens, moves or deletes the files a wildcard hands it."""

    if windows_style:
        return program in _POWERSHELL_FILE_COMMANDS
    if program in _NAMES_ONLY_PROGRAMS:
        return False
    if program == "find":
        return any(arg in _FIND_ACTIONS for arg in argv[1:])
    if program == "git":
        return git_verb not in _GIT_NAMES_ONLY_SUBCOMMANDS
    return True


def path_words(argv: Sequence[str], program: str, *, windows_style: bool) -> list[str]:
    """The arguments that can be file names, leaving out those that are patterns."""

    takes_pattern = not windows_style and program in _PATTERN_FIRST_PROGRAMS
    words: list[str] = []
    skip = False
    for word in argv[1:]:
        if skip:
            skip = False
            continue
        # ``find -name`` is left in: with an action, or piped on, the names it matches are read.
        if (word in _PATTERN_OPTIONS and program != "find") or (word == "-x" and program in _ARCHIVE_EXCLUDE_PROGRAMS):
            skip = True
            continue
        if takes_pattern and word in _PATTERN_PROGRAM_OPTIONS:
            skip = True
            takes_pattern = False  # The pattern was given by option; every other word is a file.
            continue
        if not word.startswith("-") and takes_pattern:
            takes_pattern = False
            continue
        words.append(word)
    return words


def expand_glob_word(
    word: str,
    base_dir: str | Path,
    *,
    windows_style: bool,
    include_hidden: bool,
    budget: GlobBudget,
) -> tuple[str, ...]:
    """Existing paths inside the project that ``word`` matches now.

    A relative word gives paths relative to ``base_dir``; an absolute word gives
    absolute paths. A name is tried as written and without regard to case, which
    only widens the result. A POSIX shell does not match a leading dot with a
    wildcard unless ``dotglob`` is set, so hidden names are skipped unless
    ``include_hidden`` or the pattern part itself starts with a dot. ``**`` is
    read as any depth. Home folders and other places outside the project are not
    looked at. Past the limits the result is cut short, never widened.
    """

    if len(word) > MAX_GLOB_WORD_LENGTH or "\x00" in word:
        return ()
    text = "/".join(word.split("\\")) if windows_style else word
    parts = text.split("/")
    if len(parts) > MAX_GLOB_PARTS or sum(1 for part in parts if has_glob(part)) > MAX_WILDCARD_PARTS:
        return ()

    root, parts = _starting_folder(parts)
    if root is None:
        return ()
    absolute = root != ""
    start = Path(root) if absolute else Path(base_dir)
    if not budget.allows(start) and not absolute:
        return ()
    candidates = [""]
    for part in parts:
        if not part or part == ".":
            continue
        if part == "**":
            candidates = _with_descendants(candidates, start, budget, include_hidden)
        elif not has_glob(part):
            candidates = [_join(prefix, part) for prefix in candidates]
        else:
            pattern = _fnmatch_pattern(part)
            folded = pattern.lower()
            expanded: list[str] = []
            for prefix in candidates:
                for name in budget.list_names(start / prefix if prefix else start):
                    if name.startswith(".") and not include_hidden and not part.startswith("."):
                        continue
                    if fnmatchcase(name, pattern) or fnmatchcase(name.lower(), folded):
                        expanded.append(_join(prefix, name))
            candidates = expanded
        # ``*/../`` comes back to the same folder: without this each step multiplies.
        candidates = list(dict.fromkeys(os.path.normpath(item) if item else "" for item in candidates))
        candidates = ["" if item == "." else item for item in candidates][:MAX_GLOB_CANDIDATES]
        if not candidates:
            return ()
    found = [item for item in candidates if item]
    if absolute:
        return tuple(os.path.join(root, item) for item in found)
    return tuple("/".join(item.split(os.sep)) for item in found)


def repository_relative_text(candidate: str, folder: str | Path, repo_root: str | Path) -> str:
    """``candidate`` as the path rules expect it: relative to the project when inside it."""

    path = candidate if os.path.isabs(candidate) else os.path.join(str(folder), candidate)
    path = os.path.normpath(path)
    try:
        relative = os.path.relpath(path, str(repo_root))
    except ValueError:  # Another drive.
        relative = ".."
    chosen = path if relative == ".." or relative.startswith(".." + os.sep) else relative
    return "/".join(chosen.split(os.sep))


def _starting_folder(parts: list[str]) -> tuple[str | None, list[str]]:
    """``("", parts)`` for a relative word, ``(folder, rest)`` for an absolute one.

    ``None`` for a home folder, a share, a variable or a provider: those are never
    listed. An absolute folder is still listed only if the budget finds it inside
    the project.
    """

    first = parts[0]
    if first.lower() in _WORKING_FOLDER_VARIABLES:
        return "", parts[1:]
    if first.startswith(("~", "$")):
        return None, parts
    if first == "":
        if len(parts) > 1 and parts[1] == "":
            return None, parts  # ``//host/share``.
        if os.name == "nt" and len(parts) > 2 and len(parts[1]) == 1 and parts[1].isalpha():
            return f"{parts[1]}:\\", parts[2:]  # Git Bash writes C:\x as /c/x.
        return os.path.abspath(os.sep), parts[1:]
    if len(first) == 2 and first[1] == ":" and first[0].isalpha():
        return f"{first}\\", parts[1:]
    if first.endswith(":"):
        return None, parts
    return "", parts


def _with_descendants(candidates: list[str], start: Path, budget: GlobBudget, include_hidden: bool) -> list[str]:
    found = list(candidates)
    frontier = list(candidates)
    for _ in range(MAX_RECURSION_DEPTH):
        deeper: list[str] = []
        for prefix in frontier:
            for name in budget.list_folders(start / prefix if prefix else start):
                if name.startswith(".") and not include_hidden:
                    continue
                deeper.append(_join(prefix, name))
        if not deeper or len(found) + len(deeper) > MAX_GLOB_CANDIDATES:
            break
        found.extend(deeper)
        frontier = deeper
    return found


@lru_cache(maxsize=256)
def _fnmatch_pattern(part: str) -> str:
    """``part`` in the spelling ``fnmatch`` knows, read in one pass.

    ``[^a]`` becomes ``[!a]``. A bracket expression holding a POSIX class
    (``[[:alpha:]]``, ``[[=a=]]``, ``[[.a.]]``) becomes ``?``, any one character,
    which is wider. Once a ``[`` is found with no closing ``]`` the rest is left
    as written, so a word of many open brackets is not scanned again and again.
    """

    if "[" not in part:
        return part
    out: list[str] = []
    index = 0
    length = len(part)
    while index < length:
        char = part[index]
        if char != "[":
            out.append(char)
            index += 1
            continue
        cursor = index + 1
        if cursor < length and part[cursor] in "!^":
            cursor += 1
        if cursor < length and part[cursor] == "]":
            cursor += 1
        has_class = False
        closed = False
        while cursor < length:
            if part[cursor] == "]":
                closed = True
                break
            if part[cursor] == "[" and cursor + 1 < length and part[cursor + 1] in ":=.":
                end = part.find(part[cursor + 1] + "]", cursor + 2)
                if end == -1:
                    break
                has_class = True
                cursor = end + 2
            else:
                cursor += 1
        if not closed:
            out.append(part[index:])
            break
        if has_class:
            out.append("?")
        else:
            body = part[index + 1 : cursor]
            out.append("[!" + body[1:] + "]" if body.startswith("^") else "[" + body + "]")
        index = cursor + 1
    return "".join(out)


def _join(prefix: str, name: str) -> str:
    return f"{prefix}/{name}" if prefix else name


__all__ = [
    "GLOB_CHARACTERS",
    "GlobBudget",
    "expand_glob_word",
    "glob_forms",
    "has_glob",
    "names_something",
    "path_words",
    "project_roots",
    "reads_matched_files",
    "repository_relative_text",
]
