"""Recognize a small, explicit shell read grammar; never execute commands.

This is a positive classifier, not a general shell parser. Unsupported options,
expansions, redirection and control flow receive no allow classification. Paths
must subsequently pass the hook's existing repository/protected-path gates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import shlex


@dataclass(frozen=True)
class ShellRead:
    """A proven read-only command and what it touches.

    ``paths`` have their content printed and must be regular files, ``tree_paths``
    have content printed but may also be directories or revisions, and
    ``metadata_paths`` only have their names or attributes reported.
    """

    classified: bool = False
    paths: tuple[str, ...] = ()
    tree_paths: tuple[str, ...] = ()
    metadata_paths: tuple[str, ...] = ()


@dataclass
class _Reads:
    files: list[str] = field(default_factory=list)
    trees: list[str] = field(default_factory=list)
    metadata: list[str] = field(default_factory=list)


_POWERSHELL_COMMAND = re.compile(r"(?i)^\s*(?:Get-Content|Get-ChildItem|Test-Path|Select-String)(?:\s|$)")
_POWERSHELL_CONTENT_COMMANDS = frozenset({"get-content", "gc", "cat", "type"})
_POWERSHELL_LIST_COMMANDS = frozenset({"get-childitem", "gci", "dir", "ls"})
_POWERSHELL_LOCATION_COMMANDS = frozenset({"get-location", "gl", "pwd"})
_POWERSHELL_ECHO_COMMANDS = frozenset({"echo", "write-output"})
_POWERSHELL_LIST_SWITCHES = frozenset({"-recurse", "-force", "-file", "-directory", "-name", "-hidden"})
_POSIX_TEST_FLAGS = frozenset({"-f", "-d", "-e", "-s", "-r"})
_GREP_SWITCHES = frozenset({"-n", "-i", "-l", "-c", "-v", "-w", "-F", "-E", "-H", "-h", "-s", "-q", "-o"})
_WC_SWITCHES = frozenset({"-l", "-c", "-w", "-m", "--lines", "--bytes", "--words", "--chars"})
_LS_LONG_FLAGS = re.compile(r"--(?:all|almost-all|human-readable|recursive|reverse|color(?:=\w+)?|sort=\w+)")

_GIT_DIFF_FLAGS = frozenset(
    {
        "--stat", "--numstat", "--shortstat", "--name-only", "--name-status", "--summary", "--raw", "--check",
        "--color", "--no-color", "--minimal", "--patience", "--histogram", "--word-diff", "--color-words",
        "-p", "--patch", "--no-patch", "-w", "-b", "--ignore-all-space", "--ignore-space-change",
    }
)
_GIT_DIFF_ONLY_FLAGS = frozenset({"--cached", "--staged", "--exit-code", "--quiet", "-q", "--merge-base"})
_GIT_DIFF_VALUE_FLAGS = re.compile(r"-U\d+|--unified=\d+|--stat=\d+(?:,\d+)*|--diff-filter=[A-Za-z]+")
_GIT_LOG_FLAGS = frozenset(
    {
        "--oneline", "--graph", "--all", "--decorate", "--no-decorate", "--abbrev-commit", "--no-merges",
        "--merges", "--reverse", "--first-parent", "--follow", "--branches", "--tags", "--remotes", "--source",
    }
)
_GIT_LOG_VALUE_FLAGS = re.compile(
    r"-\d+|-n\d+|--max-count=\d+|--skip=\d+|--date=[\w:%-]+"
    r"|--(?:pretty|format)=.*|--(?:since|until|after|before|author|committer|grep)=.*",
    re.DOTALL,
)
_GIT_STATUS_FLAGS = frozenset(
    {
        "-s", "--short", "-b", "--branch", "--porcelain", "--porcelain=v1", "--porcelain=v2", "--long", "-v",
        "--verbose", "-uno", "-unormal", "-uall", "--ignored", "--renames", "--no-renames",
    }
)
_GIT_LS_FILES_FLAGS = frozenset(
    {"-c", "--cached", "-m", "--modified", "-o", "--others", "--exclude-standard", "-d", "--deleted", "--error-unmatch"}
)
_GIT_BRANCH_FLAGS = frozenset(
    {"-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "--list", "-l", "--show-current", "--color", "--no-color"}
)
_GIT_REV_PARSE_FLAGS = frozenset(
    {
        "--show-toplevel", "--abbrev-ref", "--short", "--git-dir", "--is-inside-work-tree", "--verify",
        "--show-prefix", "--show-cdup", "--absolute-git-dir", "--symbolic-full-name",
    }
)
_GIT_DESCRIBE_FLAGS = frozenset({"--tags", "--always", "--dirty", "--long"})
_GIT_REVISION = re.compile(r"[\w./@^~-]+")


def classify_shell_read(command: str, *, tool_name: str) -> ShellRead:
    if not isinstance(command, str) or not command.strip() or len(command) > 16000:
        return ShellRead()
    # Check before tokenization: quoted/escaped syntax must never become new
    # grammar after quote removal. Conservative rejection is intentional.
    if any(char in command for char in "\n\r\x00$`{}()&;<>#"):
        return ShellRead()
    powershell = tool_name == "PowerShell" or bool(_POWERSHELL_COMMAND.match(command))
    if not powershell and "\\" in command:
        return ShellRead()
    if powershell and any(char in command for char in ",@"):
        return ShellRead()
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        if powershell:
            lexer.escape = ""
        tokens = list(lexer)
    except ValueError:
        return ShellRead()
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token == "|":
            if not segments[-1]:
                return ShellRead()
            segments.append([])
        elif "|" in token:
            return ShellRead()
        else:
            segments[-1].append(token)
    reads = _Reads()
    for index, segment in enumerate(segments):
        if not segment:
            return ShellRead()
        parsed = _powershell_read(segment, index > 0) if powershell else _posix_read(segment, index > 0)
        if parsed is None:
            return ShellRead()
        reads.files.extend(parsed.files)
        reads.trees.extend(parsed.trees)
        reads.metadata.extend(parsed.metadata)
    if any(not _literal_path(path) for path in (*reads.files, *reads.trees, *reads.metadata)):
        return ShellRead()
    return ShellRead(
        True,
        tuple(dict.fromkeys(reads.files)),
        tuple(dict.fromkeys(reads.trees)),
        tuple(dict.fromkeys(reads.metadata)),
    )


def _literal_path(path: str) -> bool:
    if not path or path == "-" or path.startswith(("~", "//", "\\\\")):
        return False
    if any(char in path for char in "*?[]\x00"):
        return False
    if ".." in path.replace("\\", "/").split("/"):
        return False
    # Exclude providers, URLs, ADS and drive-relative paths. Native Windows
    # drive-absolute paths are the only supported colon form.
    return ":" not in path or bool(re.fullmatch(r"[A-Za-z]:[\\/][^:]+", path))


def _posix_read(tokens: list[str], piped: bool) -> _Reads | None:
    name, *args = tokens
    if name in {"cat", "head", "tail", "sed", "rg"}:
        return _posix_content_read(name, args, piped)
    if name == "grep":
        return _grep_read(args, piped)
    if name == "wc":
        return _wc_read(args, piped)
    if piped:
        return None
    if name == "pwd":
        return _Reads() if all(arg in {"-P", "-L"} for arg in args) else None
    if name == "echo":
        return _Reads()
    if name == "ls":
        return _ls_read(args)
    if name == "test":
        if len(args) == 2 and args[0] in _POSIX_TEST_FLAGS:
            return _Reads(metadata=[args[1]])
        return None
    if name == "git":
        return _git_read(args)
    return None


def _posix_content_read(name: str, args: list[str], piped: bool) -> _Reads | None:
    paths: list[str] = []
    expression: str | None = None
    no_config = False
    sed_quiet = False
    index = 0
    options = True
    while index < len(args):
        arg = args[index]
        index += 1
        if options and arg == "--":
            options = False
            continue
        if options and arg.startswith("-"):
            if name == "cat" and arg in {"-n", "-b", "-s", "-E", "-T", "-A"}:
                continue
            if name in {"head", "tail"}:
                if arg in {"-q", "-v"}:
                    continue
                if re.fullmatch(r"-[nc]?\d+", arg):
                    continue
                if arg in {"-n", "-c"} and index < len(args) and args[index].isdigit():
                    index += 1
                    continue
            if name == "sed" and arg == "-n":
                sed_quiet = True
                continue
            if name == "rg":
                if arg == "--no-config":
                    no_config = True
                    continue
                if arg in {"-n", "--line-number", "-i", "--ignore-case", "-F", "--fixed-strings", "-l", "--files-with-matches", "--no-heading"}:
                    continue
                if arg in {"-e", "--regexp"} and expression is None and index < len(args):
                    expression = args[index]
                    index += 1
                    continue
            return None
        if name in {"sed", "rg"} and expression is None:
            expression = arg
        else:
            paths.append(arg)
    if name == "sed" and (not sed_quiet or not expression or not re.fullmatch(r"[1-9]\d*(?:,[1-9]\d*)?p", expression)):
        return None
    # RIPGREP_CONFIG_PATH can inject --pre (a subprocess) even when the visible
    # command looks read-only. Require ripgrep to disable its config explicitly.
    if name == "rg" and (not no_config or expression is None):
        return None
    if not paths and not piped:
        return None
    return _Reads(files=paths)


def _grep_read(args: list[str], piped: bool) -> _Reads | None:
    expression: str | None = None
    paths: list[str] = []
    options = True
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if options and arg == "--":
            options = False
        elif options and arg.startswith("-"):
            if arg in {"-e", "--regexp"} and expression is None and index < len(args):
                expression = args[index]
                index += 1
            elif arg not in _GREP_SWITCHES and not re.fullmatch(r"-[ABC]\d+", arg):
                return None
        elif expression is None:
            expression = arg
        else:
            paths.append(arg)
    if expression is None or (not paths and not piped):
        return None
    return _Reads(files=paths)


def _wc_read(args: list[str], piped: bool) -> _Reads | None:
    paths: list[str] = []
    for arg in args:
        if arg.startswith("-"):
            if arg not in _WC_SWITCHES:
                return None
        else:
            paths.append(arg)
    return _Reads(files=paths) if paths or piped else None


def _ls_read(args: list[str]) -> _Reads | None:
    paths: list[str] = []
    for arg in args:
        if arg.startswith("--"):
            if not _LS_LONG_FLAGS.fullmatch(arg):
                return None
        elif arg.startswith("-"):
            if not re.fullmatch(r"-[A-Za-z1]+", arg):
                return None
        else:
            paths.append(arg)
    return _Reads(metadata=paths)


def _git_read(args: list[str]) -> _Reads | None:
    """Read-only git forms. ``-c``/``-C`` prefixes and writing options never match."""

    if args[:1] == ["--no-pager"]:
        args = args[1:]
    if not args:
        return None
    subcommand, *rest = args
    if subcommand == "status":
        return _git_paths(rest, _GIT_STATUS_FLAGS, None, metadata=True)
    if subcommand == "diff":
        return _git_paths(rest, _GIT_DIFF_FLAGS | _GIT_DIFF_ONLY_FLAGS, _GIT_DIFF_VALUE_FLAGS)
    if subcommand in {"log", "show"}:
        return _git_log_read(rest)
    if subcommand == "blame":
        return _git_blame_read(rest)
    if subcommand == "ls-files":
        return _git_paths(rest, _GIT_LS_FILES_FLAGS, None, metadata=True)
    if subcommand == "check-ignore":
        return _git_paths(rest, frozenset({"-v", "--verbose", "-q", "--quiet"}), None, metadata=True)
    if subcommand == "branch":
        return _Reads() if all(arg in _GIT_BRANCH_FLAGS for arg in rest) else None
    if subcommand == "remote":
        return _Reads() if rest in ([], ["-v"], ["--verbose"]) else None
    if subcommand == "rev-parse":
        return _Reads() if all(arg in _GIT_REV_PARSE_FLAGS or _is_git_revision(arg) for arg in rest) else None
    if subcommand == "describe":
        return _Reads() if all(arg in _GIT_DESCRIBE_FLAGS or _is_git_revision(arg) for arg in rest) else None
    if subcommand == "merge-base":
        return _Reads() if len(rest) == 2 and all(_is_git_revision(arg) for arg in rest) else None
    if subcommand == "tag":
        return _Reads() if rest in ([], ["-l"], ["--list"]) else None
    if subcommand == "stash":
        return _Reads() if rest == ["list"] else None
    if subcommand == "worktree":
        return _Reads() if rest in (["list"], ["list", "--porcelain"]) else None
    return None


def _is_git_revision(arg: str) -> bool:
    return not arg.startswith("-") and bool(_GIT_REVISION.fullmatch(arg))


def _git_paths(
    args: list[str],
    flags: frozenset[str],
    value_flags: re.Pattern[str] | None,
    *,
    metadata: bool = False,
) -> _Reads | None:
    paths: list[str] = []
    options = True
    for arg in args:
        if options and arg == "--":
            options = False
        elif options and arg.startswith("-"):
            if arg not in flags and not (value_flags is not None and value_flags.fullmatch(arg)):
                return None
        else:
            paths.append(arg)
    return _Reads(metadata=paths) if metadata else _Reads(trees=paths)


def _git_log_read(args: list[str]) -> _Reads | None:
    flags = _GIT_DIFF_FLAGS | _GIT_LOG_FLAGS
    remaining: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--":
            remaining.extend(args[index - 1 :])
            break
        if arg == "-n" and index < len(args) and args[index].isdigit():
            index += 1
            continue
        remaining.append(arg)
    return _git_paths(remaining, flags, _GIT_LOG_VALUE_FLAGS)


def _git_blame_read(args: list[str]) -> _Reads | None:
    paths: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "-L" and index < len(args) and re.fullmatch(r"\d+(?:,\+?\d+)?", args[index]):
            index += 1
        elif arg.startswith("-") and arg != "--":
            if not re.fullmatch(r"-L\d+(?:,\+?\d+)?", arg):
                return None
        elif arg != "--":
            paths.append(arg)
    return _Reads(trees=paths) if paths else None


def _powershell_read(tokens: list[str], piped: bool) -> _Reads | None:
    name, *args = tokens
    name = name.lower()
    if name == "select-object":
        if not piped or not args:
            return None
        while args:
            if len(args) < 2 or args[0].lower() not in {"-first", "-last", "-skip"} or not args[1].isdigit():
                return None
            args = args[2:]
        return _Reads()
    if name == "measure-object":
        return _Reads() if piped and all(arg.lower() in {"-line", "-word", "-character"} for arg in args) else None
    if name in {"select-string", "sls"}:
        return _powershell_select_string(args, piped)
    if piped:
        return None
    if name in _POWERSHELL_CONTENT_COMMANDS:
        return _powershell_content_read(args)
    if name in _POWERSHELL_LIST_COMMANDS:
        return _powershell_list_read(args)
    if name == "test-path":
        return _powershell_test_path(args)
    if name in _POWERSHELL_LOCATION_COMMANDS:
        return None if args else _Reads()
    if name in _POWERSHELL_ECHO_COMMANDS:
        return _Reads()
    if name == "git":
        return _git_read(args)
    return None


def _powershell_content_read(args: list[str]) -> _Reads | None:
    paths: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        flag = arg.lower()
        if flag == "-raw":
            continue
        if flag in {"-path", "-literalpath"}:
            if index >= len(args) or args[index].startswith("-"):
                return None
            paths.append(args[index])
            index += 1
        elif flag in {"-totalcount", "-head", "-tail"}:
            if index >= len(args) or not args[index].isdigit():
                return None
            index += 1
        elif arg.startswith("-"):
            return None
        else:
            paths.append(arg)
    return _Reads(files=paths) if paths else None


def _powershell_list_read(args: list[str]) -> _Reads | None:
    paths: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        flag = arg.lower()
        if flag in _POWERSHELL_LIST_SWITCHES:
            continue
        if flag in {"-path", "-literalpath"}:
            if index >= len(args) or args[index].startswith("-"):
                return None
            paths.append(args[index])
            index += 1
        elif flag == "-depth":
            if index >= len(args) or not args[index].isdigit():
                return None
            index += 1
        elif flag == "-filter":
            if index >= len(args) or args[index].startswith("-") or ":" in args[index]:
                return None
            index += 1
        elif arg.startswith("-"):
            return None
        else:
            paths.append(arg)
    return _Reads(metadata=paths) if len(paths) <= 1 else None


def _powershell_test_path(args: list[str]) -> _Reads | None:
    paths: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        flag = arg.lower()
        if flag in {"-path", "-literalpath"}:
            if index >= len(args) or args[index].startswith("-"):
                return None
            paths.append(args[index])
            index += 1
        elif flag == "-pathtype":
            if index >= len(args) or args[index].lower() not in {"leaf", "container", "any"}:
                return None
            index += 1
        elif arg.startswith("-"):
            return None
        else:
            paths.append(arg)
    return _Reads(metadata=paths) if len(paths) == 1 else None


def _powershell_select_string(args: list[str], piped: bool) -> _Reads | None:
    pattern: str | None = None
    paths: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        flag = arg.lower()
        if flag in {"-simplematch", "-casesensitive", "-quiet", "-list", "-notmatch"}:
            continue
        if flag == "-pattern" and pattern is None and index < len(args):
            pattern = args[index]
            index += 1
        elif flag in {"-path", "-literalpath"}:
            if index >= len(args) or args[index].startswith("-"):
                return None
            paths.append(args[index])
            index += 1
        elif arg.startswith("-"):
            return None
        elif pattern is None:
            pattern = arg
        else:
            paths.append(arg)
    if pattern is None or (not paths and not piped):
        return None
    return _Reads(files=paths)
