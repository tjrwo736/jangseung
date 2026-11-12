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
class GitOutput:
    """A git command that can print file content, in parts so pathspecs can be added.

    ``arguments`` came before any ``--``, so each is a revision or a path. git tells
    them apart by what exists, and whoever adds a ``--`` has to do the same.
    """

    head: tuple[str, ...]
    options: tuple[str, ...]
    arguments: tuple[str, ...]
    paths: tuple[str, ...]
    prints_file_content: bool = True

    @property
    def can_be_narrowed(self) -> bool:
        # --follow accepts one pathspec only, and it reaches a file's earlier names.
        words = (*self.options, *self.arguments, *self.paths)
        return "--follow" not in self.options and not any("'" in word or '"' in word for word in words)


@dataclass(frozen=True)
class ShellRead:
    """A proven read-only command and what it touches.

    ``paths`` have their content printed and must be regular files, ``tree_paths``
    have content printed but may also be directories or revisions, and
    ``metadata_paths`` only have their names or attributes reported.
    ``compared_paths`` are like ``tree_paths``, but git compares them as paths and
    walks directories when it finds no usable repository. ``runs_git`` says git
    reads its config, which can name programs, from whatever repository it finds.
    """

    classified: bool = False
    paths: tuple[str, ...] = ()
    tree_paths: tuple[str, ...] = ()
    metadata_paths: tuple[str, ...] = ()
    compared_paths: tuple[str, ...] = ()
    runs_git: bool = False
    git_output: GitOutput | None = None
    # Programs found on PATH that a status or version command runs. The caller
    # checks that each one lives outside the project, where an agent cannot write it.
    programs: tuple[str, ...] = ()


@dataclass
class _Reads:
    files: list[str] = field(default_factory=list)
    trees: list[str] = field(default_factory=list)
    metadata: list[str] = field(default_factory=list)
    compared: list[str] = field(default_factory=list)
    git: bool = False
    git_output: GitOutput | None = None
    programs: list[str] = field(default_factory=list)


_POWERSHELL_COMMAND = re.compile(r"(?i)^\s*(?:Get-Content|Get-ChildItem|Test-Path|Select-String)(?:\s|$)")
_POWERSHELL_CONTENT_COMMANDS = frozenset({"get-content", "gc", "cat", "type"})
_POWERSHELL_LIST_COMMANDS = frozenset({"get-childitem", "gci", "dir", "ls"})
_POWERSHELL_SELECT_STRING_COMMANDS = frozenset({"select-string", "sls"})
_POWERSHELL_TYPOGRAPHIC_CHARACTERS = frozenset("\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u2013\u2014\u2015")
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
_GIT_NAMES_ONLY_FLAGS = frozenset(
    {"--stat", "--numstat", "--shortstat", "--name-only", "--name-status", "--summary", "--raw", "--no-patch", "--quiet"}
)
_GIT_PATCH_FLAGS = frozenset({"-p", "--patch", "--word-diff", "--color-words", "--check"})
# ``git log`` prints no file content by default; these ask for a diff or shape one.
_GIT_LOG_DIFF_FLAGS = frozenset({"--minimal", "--patience", "--histogram", "-w", "-b", "--ignore-all-space", "--ignore-space-change"})
_GIT_RANGE = re.compile(r"(\.\.\.?)")
# A bare id, or the ``v1-3-g<id>`` that git describe prints and git resolves to that id.
_GIT_OBJECT_ID = re.compile(r"(\^?)((?:[^~^]*-g)?[0-9a-fA-F]{4,64})((?:[~^].*)?)")
# git show would print whatever these refs name, and a ref may name a blob.
_GIT_ALL_REFS_FLAGS = frozenset({"--all", "--branches", "--tags", "--remotes"})
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

# Commands that only report on the machine or wait. They take no file argument.
_NO_ARGUMENT_COMMANDS = frozenset({"true", "false", "whoami", "id", "nproc", "arch", "tty", "hostname"})
_UNAME_FLAGS = frozenset({"-a", "-s", "-r", "-m", "-n", "-v", "-o", "-p", "-i", "--all"})
_DATE_FLAGS = frozenset({"-u", "--utc", "-R", "--rfc-email", "-I", "-Iseconds", "-Iminutes", "-Ihours", "-Idate"})
_DURATION = re.compile(r"\d{1,6}(?:\.\d{1,3})?[smhd]?")
_PROGRAM_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]{0,63}")
# Programs whose version form only prints a version, with that one exact form.
# A bare word is not a version form: ``python version`` runs a file named
# ``version``, ``npm version`` changes package.json and ``pytest -v`` runs the
# tests. ``pytest --version`` loads conftest.py, so pytest is not here at all.
# Launchers that hand over to a program a project file names are left out too:
# yarn (``yarnPath``), cargo and rustc (``rust-toolchain.toml``), dotnet
# (``global.json``), go (``toolchain`` in go.mod), npm and pnpm (``packageManager``),
# poetry, pdm and composer (project plugins), and the per-project node tools.
_VERSION_FORMS = {
    **dict.fromkeys(
        ("python", "python3", "node", "deno", "gh", "docker", "jq", "rg", "fd", "bash", "pwsh", "gcc", "clang",
         "cmake", "ruff"),
        frozenset({"--version"}),
    ),
    "java": frozenset({"-version", "--version"}),
    "javac": frozenset({"-version", "--version"}),
}
_SEQUENCE_OPERATORS = (";", "&&", "||")
MAX_SEQUENCE_SEGMENTS = 16


def classify_shell_read(command: str, *, tool_name: str) -> ShellRead:
    if not isinstance(command, str) or not command.strip() or len(command) > 16000:
        return ShellRead()
    # Check before tokenization: quoted/escaped syntax must never become new
    # grammar after quote removal. Conservative rejection is intentional.
    if any(char in command for char in "\n\r\x00$`{}()&;<>#"):
        return ShellRead()
    # PowerShell splits words on any Unicode space; the lexer below does not. Either
    # shell can be behind the name Bash: Codex on Windows runs it in PowerShell.
    if any(char.isspace() and char not in " \t" for char in command):
        return ShellRead()
    powershell = tool_name == "PowerShell" or bool(_POWERSHELL_COMMAND.match(command))
    if not _quotes_read_alike(command, powershell=powershell):
        return ShellRead()
    if not powershell and ("\\" in command or _has_unquoted_glob(command)):
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
        reads.compared.extend(parsed.compared)
        reads.git = reads.git or parsed.git
        reads.git_output = reads.git_output or parsed.git_output
        reads.programs.extend(parsed.programs)
    # Select-String opens the files a listing hands it: this is not a text filter.
    if powershell and segments[0][0].lower() in _POWERSHELL_LIST_COMMANDS and any(
        segment[0].lower() in _POWERSHELL_SELECT_STRING_COMMANDS for segment in segments[1:]
    ):
        return ShellRead()
    if any(not _literal_path(path) for path in (*reads.files, *reads.trees, *reads.metadata, *reads.compared)):
        return ShellRead()
    return ShellRead(
        True,
        tuple(dict.fromkeys(reads.files)),
        tuple(dict.fromkeys(reads.trees)),
        tuple(dict.fromkeys(reads.metadata)),
        tuple(dict.fromkeys(reads.compared)),
        reads.git,
        reads.git_output,
        tuple(dict.fromkeys(reads.programs)),
    )


def _has_unquoted_glob(command: str) -> bool:
    """A POSIX shell expands these in any word, not only in the paths parsed below.

    ``grep -v .* README.md`` hands grep every dotfile. Backslashes never get here.
    """

    quote = ""
    for char in command:
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in "*?[":
            return True
    return False


def _quotes_read_alike(command: str, *, powershell: bool) -> bool:
    """False when a shell could split the words differently from the lexer.

    PowerShell takes typographic quotes and dashes as ASCII ones, and ends a word at
    the quote closing it when a quote opened the word: ``'.env'-Raw`` is two arguments
    there and one in bash. In PowerShell ``''`` inside a quoted word is a literal quote,
    which the lexer would drop, so a quote in mid-word is refused there as well.
    """

    if _POWERSHELL_TYPOGRAPHIC_CHARACTERS.intersection(command):
        return False
    quote = ""
    previous = " "
    opened_word = False
    must_end_word = False
    for char in command:
        if quote:
            if char == quote:
                quote = ""
                must_end_word = opened_word
        else:
            if must_end_word and char not in " \t|":
                return False
            must_end_word = False
            if char in "'\"":
                opened_word = previous in " \t|"
                if powershell and not opened_word:
                    return False
                quote = char
        previous = char
    return not quote


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
        return _git_command_read(args)
    return _posix_status_read(name, args)


_SHELL_BUILTINS = frozenset({"true", "false", "cd", "command"})


def _posix_status_read(name: str, args: list[str]) -> _Reads | None:
    """Commands that print a status, a version or nothing, and read no file."""

    parsed = _posix_status_form(name, args)
    if parsed is not None and name not in _SHELL_BUILTINS:
        parsed.programs.append(name)
    return parsed


def _posix_status_form(name: str, args: list[str]) -> _Reads | None:
    if name in _NO_ARGUMENT_COMMANDS:
        return _Reads() if not args else None
    if name == "uname":
        return _Reads() if all(arg in _UNAME_FLAGS for arg in args) else None
    if name == "date":
        # ``date -s`` would set the clock; only formats and zones are taken.
        return _Reads() if all(arg in _DATE_FLAGS or arg.startswith("+") for arg in args) else None
    if name == "sleep":
        return _Reads() if len(args) == 1 and _DURATION.fullmatch(args[0]) else None
    if name == "which":
        names = [arg for arg in args if arg != "-a"]
        return _Reads() if names and all(_PROGRAM_NAME.fullmatch(arg) for arg in names) else None
    if name == "command":
        return _Reads() if len(args) == 2 and args[0] == "-v" and _PROGRAM_NAME.fullmatch(args[1]) else None
    if name == "cd":
        # The folder is judged like any listed path. A shell that has CDPATH set may
        # enter another folder; the host then reports that folder on the next call.
        return _Reads(metadata=[args[0]]) if len(args) == 1 and not args[0].startswith("-") else None
    if name in _VERSION_FORMS:
        return _Reads() if len(args) == 1 and args[0] in _VERSION_FORMS[name] else None
    return None


def split_command_sequence(command: str) -> tuple[tuple[str, str], ...] | None:
    """A Bash command cut at ``;``, ``&&`` and ``||`` outside quotes, with the operator after each part.

    ``None`` unless there are two or more parts and nothing the read grammar refuses
    anyway: substitutions, redirections, grouping, comments, backslashes, newlines and
    background jobs (a single ``&``) are left out before splitting.
    """

    if not isinstance(command, str) or len(command) > 16000:
        return None
    if any(char in command for char in "\n\r\x00$`{}()<>#\\"):
        return None
    parts: list[tuple[str, str]] = []
    current: list[str] = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            current.append(char)
            quote = "" if char == quote else quote
            index += 1
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            continue
        pair = command[index : index + 2]
        if pair in ("&&", "||"):
            operator = pair
            index += 2
        elif char == ";":
            if command[index + 1 : index + 2] == ";":
                return None
            operator = ";"
            index += 1
        elif char == "&":
            return None
        else:
            current.append(char)
            index += 1
            continue
        segment = "".join(current).strip()
        if not segment:
            return None
        parts.append((segment, operator))
        current = []
        if len(parts) > MAX_SEQUENCE_SEGMENTS:
            return None
    if quote:
        return None
    tail = "".join(current).strip()
    if tail:
        parts.append((tail, ""))
    elif not parts or parts[-1][1] != ";":
        return None
    else:
        parts[-1] = (parts[-1][0], "")
    if len(parts) < 2 or len(parts) > MAX_SEQUENCE_SEGMENTS:
        return None
    return tuple(parts)


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


def _git_command_read(args: list[str]) -> _Reads | None:
    parsed = _git_read(args)
    if parsed is not None:
        parsed.git = True
        parsed.git_output = _git_output(args)
    return parsed


def _git_output(args: list[str]) -> GitOutput | None:
    head = ["git"]
    rest = list(args)
    if rest[0] == "--no-pager":
        head.append(rest.pop(0))
    subcommand = rest.pop(0)
    if subcommand not in {"diff", "show", "log"}:
        return None
    head.append(subcommand)
    options: list[str] = []
    arguments: list[str] = []
    paths: list[str] = []
    index = 0
    while index < len(rest):
        arg = rest[index]
        index += 1
        if arg == "--":
            paths = rest[index:]
            break
        if arg == "-n":
            options += [arg, rest[index]]
            index += 1
        elif arg.startswith("-"):
            options.append(arg)
        else:
            arguments.append(arg)
    prints = _git_prints_file_content(subcommand, options)
    # git show prints a blob named by its id whatever its options ask of a commit.
    if not prints and subcommand != "show":
        return None
    return GitOutput(tuple(head), tuple(options), tuple(arguments), tuple(paths), prints)


def _git_prints_file_content(subcommand: str, options: list[str]) -> bool:
    if any(option in _GIT_PATCH_FLAGS or option.startswith(("-U", "--unified=")) for option in options):
        return True
    if subcommand == "log":
        return any(option in _GIT_LOG_DIFF_FLAGS for option in options)
    return not any(option in _GIT_NAMES_ONLY_FLAGS or option.startswith("--stat=") for option in options)


def git_output_command(
    command: str,
    output: GitOutput,
    *,
    revisions: tuple[str, ...],
    paths: tuple[str, ...],
    exclusions: tuple[str, ...],
) -> str | None:
    """Rebuild ``command`` so its git output leaves out what ``exclusions`` name.

    None when there is nothing to change: no pathspec to add and no object id to peel.
    """

    peeled = tuple(map(_commit_only, revisions))
    if not paths and not exclusions and peeled == revisions:
        return None
    limits = ("--", *(paths or (":/",)), *exclusions) if paths or exclusions else ()
    # A pathspec makes log and show skip commits it leaves empty; the caller gave none.
    every_commit = ("--full-history", "--sparse") if exclusions and not paths and output.head[-1] != "diff" else ()
    words = (*output.head, *output.options, *every_commit, *peeled, *limits)
    rebuilt = " ".join(word if re.fullmatch(r"[\w./=%~-]+", word) else f"'{word}'" for word in words)
    # Git is only ever the first segment, and the grammar leaves no other | in the text.
    _, pipe, piped_into = command.partition("|")
    return f"{rebuilt} | {piped_into.strip()}" if pipe else rebuilt


def _commit_only(revision: str) -> str:
    """Make an object id name a commit, on either side of a range.

    A pathspec cannot stop a blob named by its id, as in ``git show e5943a1``, and
    ``git log --raw`` prints those ids. Peeling to a commit turns a blob into an error.
    """

    return "".join(
        _GIT_OBJECT_ID.sub(r"\1\2^{commit}\3", part) if _GIT_OBJECT_ID.fullmatch(part) else part
        for part in _GIT_RANGE.split(revision)
    )


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
        parsed = _git_paths(rest, _GIT_DIFF_FLAGS | _GIT_DIFF_ONLY_FLAGS, _GIT_DIFF_VALUE_FLAGS)
        if parsed is not None and len(parsed.trees) >= 2:
            parsed.compared, parsed.trees = parsed.trees, []
        return parsed
    if subcommand == "show" and _GIT_ALL_REFS_FLAGS.intersection(rest):
        return None
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
    if name in _POWERSHELL_SELECT_STRING_COMMANDS:
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
        return _git_command_read(args)
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
