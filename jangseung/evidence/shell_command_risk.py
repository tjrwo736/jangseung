"""Command-position risk rules shared by the Bash and PowerShell judgments.

These helpers only read command text and never execute anything. A finding here
can deny a command; finding nothing never allows one, because automatic allow
comes only from the positive grammar in ``shell_read_only``.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
import re

from jangseung.classify import PathPolicy, is_secret_path

GUARD_SELF_DISABLE_REASON = "dangerous_bash_guard_self_disable"
MAX_NESTED_SHELL_DEPTH = 4

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_EXECUTABLE_SUFFIXES = (".exe", ".cmd", ".bat", ".com")
_OPERATORS = (
    "&>>", "<<<", "<<-", "&&", "||", ";;", "|&", "&>", ">>", ">|", ">&", "<<", "<&",
    ";", "|", "&", "(", ")", "<", ">",
)
_WRITE_REDIRECTS = frozenset({"&>>", "&>", ">>", ">|", ">&", ">"})
_HEREDOCS = frozenset({"<<", "<<-"})

_DANGEROUS_COMMANDS = frozenset(
    {
        "curl", "wget", "env", "printenv", "chmod", "chown", "sudo", "doas", "su", "runas",
        "scp", "sftp", "ftp", "rsync", "ssh", "nc", "ncat", "netcat", "socat", "telnet",
    }
)
_WRAPPER_COMMANDS = frozenset(
    {"command", "builtin", "exec", "nohup", "time", "nice", "ionice", "stdbuf", "timeout", "setsid", "busybox"}
)
_POSIX_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "ash", "fish"})
_FIND_EXEC_FLAGS = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
_PUBLISH_SUBCOMMANDS = {
    "npm": frozenset({"publish", "unpublish"}),
    "pnpm": frozenset({"publish"}),
    "yarn": frozenset({"publish"}),
    "bun": frozenset({"publish"}),
    "cargo": frozenset({"publish"}),
    "poetry": frozenset({"publish"}),
    "uv": frozenset({"publish"}),
    "twine": frozenset({"upload"}),
    "gem": frozenset({"push"}),
    "docker": frozenset({"push"}),
    "podman": frozenset({"push"}),
    "kubectl": frozenset({"apply", "create", "delete", "replace", "patch", "scale", "rollout", "edit", "drain"}),
    "helm": frozenset({"install", "upgrade", "uninstall", "delete", "rollback"}),
    "terraform": frozenset({"apply", "destroy", "import"}),
    "tofu": frozenset({"apply", "destroy", "import"}),
    "pulumi": frozenset({"up", "destroy"}),
}
_PUBLISH_SEQUENCES = {
    "gh": (
        ("release", "create"), ("release", "delete"), ("release", "upload"), ("release", "edit"),
        ("pr", "merge"), ("repo", "delete"), ("repo", "archive"),
    ),
    "dotnet": (("nuget", "push"),),
}
# Commands that only ever treat ``deploy`` as a path or as text.
_DEPLOY_INERT_COMMANDS = frozenset(
    {
        "ls", "cd", "cat", "git", "grep", "rg", "mkdir", "touch", "echo", "find", "head", "tail", "sed",
        "awk", "wc", "cp", "mv", "stat", "file", "tree", "code", "vim", "nano", "less", "more", "test",
        "pip", "pip3",
    }
)
_GIT_GLOBAL_VALUE_OPTIONS = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--config-env"})
_GUARD_MODULES = frozenset(
    {
        "jangseung", "jangseung.__main__", "jangseung.cli", "jangseung.cli.__main__", "jangseung.cli.main",
        "jangseung.cli.entry", "src", "src.cli", "src.cli.__main__",
    }
)
_PYTHON_INTERPRETER = re.compile(r"python[\d.]*|pythonw|py|pypy[\d.]*")
_PYTHON_MODULE_FLAG = re.compile(r"-[bBdEhiIOPqsSuvVx]*m(.*)")
_PYTHON_VALUE_OPTIONS = frozenset({"-W", "-X", "--check-hash-based-pycs"})
_TOOL_RUNNERS = frozenset({"uv", "pipx", "poetry", "pdm", "hatch"})
# ``policy`` is here because it widens what agents may do; only a person runs it.
_GUARD_COMMANDS = frozenset({"uninstall", "install", "repair-hooks", "policy"})

_POWERSHELL_DYNAMIC = frozenset({"invoke-expression", "iex"})
_POWERSHELL_NETWORK = frozenset({"invoke-webrequest", "iwr", "invoke-restmethod", "irm", "start-bitstransfer"})
_POWERSHELL_PROCESS = frozenset(
    {"start-process", "saps", "start", "invoke-command", "icm", "set-executionpolicy", "add-type"}
)
_POWERSHELL_RECURSIVE_DELETE = frozenset({"remove-item", "ri", "rm", "rmdir", "rd", "del", "erase"})
_POWERSHELL_SHELLS = frozenset({"powershell", "pwsh"})
_POWERSHELL_ENCODED_FLAG = "encodedcommand"
_INLINE_CODE_INTERPRETER = re.compile(r"python[\d.]*|pythonw|py|node|deno|bun|perl|ruby|php|lua")
_INLINE_CODE_FLAGS = frozenset({"-c", "-e", "-p", "-r", "-pe", "-ne", "--eval", "--print"})
_INLINE_CODE_SEPARATORS = re.compile(r"[\s'\"`(),;=+\[\]{}<>|&]+")
# Words that only count as a secret reference inside a path, never as bare text.
_BARE_SECRET_WORDS = frozenset({"secret", "secrets", "credentials"})


@dataclass(frozen=True)
class BashWord:
    value: str
    dynamic: bool = False


@dataclass(frozen=True)
class BashScan:
    """Simple commands and file redirects of one Bash command string.

    ``dynamic`` means substitution or expansion was seen, so the words are a
    lower bound of what will really run. ``error`` means quoting was unbalanced.
    """

    segments: tuple[tuple[BashWord, ...], ...]
    write_redirects: tuple[BashWord, ...]
    dynamic: bool
    error: str | None = None
    # For each write redirect, how many segments had already finished before it.
    redirect_positions: tuple[int, ...] = ()

    def argvs(self) -> tuple[tuple[str, ...], ...]:
        return tuple(tuple(word.value for word in segment) for segment in self.segments)


def scan_bash_command(command: str) -> BashScan:
    try:
        return _BashScanner(command).scan()
    except ValueError as exc:
        return BashScan((), (), True, str(exc))


class _BashScanner:
    def __init__(self, command: str) -> None:
        self.command = command
        self.index = 0
        self.buffer: list[str] = []
        self.in_word = False
        self.word_dynamic = False
        self.words: list[BashWord] = []
        self.segments: list[tuple[BashWord, ...]] = []
        self.redirects: list[BashWord] = []
        self.redirect_positions: list[int] = []
        self.dynamic = False
        self.pending: str | None = None
        self.heredocs: list[tuple[str, bool]] = []

    def scan(self) -> BashScan:
        command = self.command
        while self.index < len(command):
            char = command[self.index]
            if char == "\\":
                self._backslash()
            elif char == "'":
                self._single_quote()
            elif char == '"':
                self._double_quote()
            elif char in " \t\r":
                self._flush_word()
                self.index += 1
            elif char == "\n":
                self._end_segment()
                self.index = self._skip_heredocs(self.index + 1)
            elif char == "#" and not self.in_word:
                newline = command.find("\n", self.index)
                self.index = len(command) if newline == -1 else newline
            elif command.startswith("$(", self.index):
                self.dynamic = True
                self._end_segment()
                self.index += 2
            elif char == "`":
                self.dynamic = True
                self._end_segment()
                self.index += 1
            elif char == "$":
                self.dynamic = True
                self.word_dynamic = True
                self.in_word = True
                self.buffer.append(char)
                self.index += 1
            elif not self._operator():
                self.in_word = True
                self.buffer.append(char)
                self.index += 1
        self._end_segment()
        return BashScan(
            tuple(self.segments),
            tuple(self.redirects),
            self.dynamic,
            redirect_positions=tuple(self.redirect_positions),
        )

    def _backslash(self) -> None:
        following = self.command[self.index + 1 : self.index + 2]
        self.index += 2
        if following != "\n":
            self.in_word = True
            self.buffer.append(following or "\\")

    def _single_quote(self) -> None:
        end = self.command.find("'", self.index + 1)
        if end == -1:
            raise ValueError("unterminated_single_quote")
        self.in_word = True
        self.buffer.append(self.command[self.index + 1 : end])
        self.index = end + 1

    def _double_quote(self) -> None:
        command = self.command
        index = self.index + 1
        self.in_word = True
        while index < len(command):
            char = command[index]
            if char == '"':
                self.index = index + 1
                return
            if char == "\\" and index + 1 < len(command):
                following = command[index + 1]
                if following in '"$`\\':
                    self.buffer.append(following)
                elif following != "\n":
                    self.buffer.append(char + following)
                index += 2
                continue
            if char in "$`":
                self.dynamic = True
                self.word_dynamic = True
            self.buffer.append(char)
            index += 1
        raise ValueError("unterminated_double_quote")

    def _operator(self) -> bool:
        for operator in _OPERATORS:
            if not self.command.startswith(operator, self.index):
                continue
            self.index += len(operator)
            if operator[0] in "<>" and self.in_word and "".join(self.buffer).isdigit():
                # A file descriptor number belongs to the redirect, not the command.
                self.buffer.clear()
                self.in_word = False
                self.word_dynamic = False
            self._flush_word()
            if operator == "(" and self.pending in {"read", "write"}:
                self.dynamic = True
                self.pending = None
            elif operator in _WRITE_REDIRECTS:
                self.pending = "write"
            elif operator in _HEREDOCS:
                self.pending = "strip_heredoc" if operator == "<<-" else "heredoc"
            elif operator == "<":
                self.pending = "read"
            elif operator in {"<<<", "<&"}:
                self.pending = "skip"
            else:
                self._end_segment()
            return True
        return False

    def _flush_word(self) -> None:
        if not self.in_word:
            return
        word = BashWord("".join(self.buffer), self.word_dynamic)
        self.buffer.clear()
        self.in_word = False
        self.word_dynamic = False
        pending, self.pending = self.pending, None
        if pending == "write":
            if not (word.value.isdigit() or word.value == "-"):
                self.redirects.append(word)
                self.redirect_positions.append(len(self.segments))
        elif pending in {"heredoc", "strip_heredoc"}:
            self.heredocs.append((word.value, pending == "strip_heredoc"))
        elif pending != "skip":
            self.words.append(word)

    def _end_segment(self) -> None:
        self._flush_word()
        self.pending = None
        if self.words:
            self.segments.append(tuple(self.words))
            self.words = []

    def _skip_heredocs(self, index: int) -> int:
        command = self.command
        for delimiter, strip_tabs in self.heredocs:
            while index < len(command):
                newline = command.find("\n", index)
                line = command[index:] if newline == -1 else command[index:newline]
                index = len(command) if newline == -1 else newline + 1
                candidate = line.lstrip("\t") if strip_tabs else line
                if candidate.rstrip("\r") == delimiter:
                    break
        self.heredocs = []
        return index


def nested_shell_payloads(argv: Sequence[str]) -> tuple[str, ...]:
    """Return command text that ``argv`` hands to another POSIX shell."""

    argv = strip_assignments(argv)
    if not argv:
        return ()
    name = command_name(argv[0])
    args = argv[1:]
    if name == "eval":
        return (" ".join(args),) if args else ()
    if name == "cmd":
        for index, arg in enumerate(args):
            if arg.lower() in {"/c", "/k"}:
                return (" ".join(args[index + 1 :]),)
        return ()
    if name in _POSIX_SHELLS or name in _POWERSHELL_SHELLS:
        for index, arg in enumerate(args):
            if arg == "-c" or (
                arg.startswith("-") and not arg.startswith("--") and name in _POSIX_SHELLS and "c" in arg[1:]
            ) or (name in _POWERSHELL_SHELLS and _is_powershell_abbreviation(arg, "command")):
                return (" ".join(args[index + 1 :]),)
    return ()


def bash_dangerous_reasons(scan: BashScan, *, depth: int = 0) -> tuple[str, ...]:
    reasons = [
        reason
        for argv in scan.argvs()
        for reason in (dangerous_argv_reason(argv, depth=depth),)
        if reason is not None
    ]
    return tuple(dict.fromkeys(reasons))


def dangerous_argv_reason(argv: Sequence[str], *, depth: int = 0) -> str | None:
    """Judge one simple command by the word in command position only."""

    argv = strip_assignments(argv)
    if not argv:
        return None
    if depth > MAX_NESTED_SHELL_DEPTH:
        return "dangerous_bash_nested_shell_too_deep"
    name = command_name(argv[0])
    args = argv[1:]

    if guard_self_disable(argv):
        return GUARD_SELF_DISABLE_REASON
    for payload in nested_shell_payloads(argv):
        reasons = bash_dangerous_reasons(scan_bash_command(payload), depth=depth + 1)
        if reasons:
            return reasons[0]
    if name == "xargs" or name in _WRAPPER_COMMANDS:
        for index in range(len(args)):
            reason = dangerous_argv_reason(args[index:], depth=depth + 1)
            if reason is not None:
                return reason
        return None
    if name == "find":
        return _find_reason(args, depth)
    if name in _DANGEROUS_COMMANDS:
        return f"dangerous_bash_token:{name}"
    if name == "rm" and _rm_recursive_force(args):
        return "dangerous_bash_rm_recursive_force"
    if name == "git":
        return _git_reason(args)
    return _publish_reason(name, args) or _deploy_reason(name, args)


def guard_self_disable(argv: Sequence[str]) -> bool:
    """True when a command would remove or rewrite the guard's own state.

    Only what the command line itself starts is read: ``aeg``, a Python interpreter
    running the guard's module or launcher script, or a tool runner in front of
    either. A program that merely receives ``aeg policy`` as arguments is not it.
    """

    argv = strip_assignments(argv)
    if not argv:
        return False
    name = command_name(argv[0])
    args = list(argv[1:])
    positional = [arg.lower() for arg in args if not arg.startswith("-")]
    if name == "aeg":
        return _names_guard_command(args)
    if name in {"pip", "pip3", "pipx", "uv"} and "uninstall" in positional and "jangseung" in positional:
        return True
    if name in _TOOL_RUNNERS and "run" in args:
        return guard_self_disable(args[args.index("run") + 1 :])
    if not _PYTHON_INTERPRETER.fullmatch(name):
        return False
    program = _python_program(args)
    if program is None:
        return False
    kind, target, rest = program
    target = target.lower().rstrip(". ")
    if kind == "module":
        if target in _GUARD_MODULES:
            return _names_guard_command(rest)
        if target == "pip":
            after = [item.lower() for item in rest if not item.startswith("-")]
            return "uninstall" in after and "jangseung" in after
        return False
    return command_name(target) == "aeg" and _names_guard_command(rest)


def _python_program(args: Sequence[str]) -> tuple[str, str, Sequence[str]] | None:
    """What a Python command line runs: a module or a script, and the arguments after it."""

    index = 0
    while index < len(args):
        arg = args[index]
        if arg in _PYTHON_VALUE_OPTIONS:
            index += 2
            continue
        module_flag = _PYTHON_MODULE_FLAG.fullmatch(arg)
        if module_flag is not None:
            # ``-m module``, ``-mmodule`` and clusters such as ``-Im module``.
            rest = list(args[index + 1 :])
            module = module_flag.group(1) or (rest.pop(0) if rest else "")
            if module.lower() == "runpy":
                while rest and rest[0].startswith("-"):
                    rest.pop(0)
                module = rest.pop(0) if rest else ""
            return ("module", module, rest) if module else None
        if arg.startswith("-"):
            if not arg.startswith("--") and "c" in arg[1:]:
                return None  # inline code; its words are judged elsewhere
            index += 1
            continue
        return ("script", arg, args[index + 1 :])
    return None


def _names_guard_command(args: Sequence[str]) -> bool:
    positional = [arg.lower() for arg in args if not arg.startswith("-")]
    return any(item in _GUARD_COMMANDS for item in positional[:2])


def powershell_dangerous_reasons(argvs: Iterable[Sequence[str]], *, depth: int = 0) -> tuple[str, ...]:
    reasons = [
        reason
        for argv in argvs
        for reason in (_powershell_argv_reason(argv, depth=depth),)
        if reason is not None
    ]
    return tuple(dict.fromkeys(reasons))


def _powershell_argv_reason(argv: Sequence[str], *, depth: int) -> str | None:
    if not argv:
        return None
    name = command_name(argv[0])
    args = list(argv[1:])
    if name in _POWERSHELL_DYNAMIC:
        return "dangerous_powershell_dynamic_code"
    if name in _POWERSHELL_NETWORK:
        return "dangerous_powershell_network"
    if name in _POWERSHELL_PROCESS:
        return "dangerous_powershell_process_control"
    if name in _POWERSHELL_SHELLS and any(_is_powershell_abbreviation(arg, _POWERSHELL_ENCODED_FLAG) for arg in args):
        return "dangerous_powershell_dynamic_code"
    if name in _POWERSHELL_RECURSIVE_DELETE and _powershell_recursive_force(args):
        return "dangerous_bash_rm_recursive_force"
    if any(arg.lower().startswith("env:") for arg in args):
        return "dangerous_bash_token:env"
    return dangerous_argv_reason(argv, depth=depth)


def secret_references(tokens: Iterable[str], *, policy: PathPolicy | None = None) -> tuple[str, ...]:
    """Return literal arguments that name a secret path.

    Text containing whitespace is a message or a script, not a path, and a bare
    word such as ``secret`` is far more often a search term than a file.
    """

    found: list[str] = []
    for token in tokens:
        if not token or any(char.isspace() for char in token):
            continue
        for candidate in _reference_candidates(token):
            if candidate.casefold() in _BARE_SECRET_WORDS:
                continue
            if is_secret_path(candidate, policy):
                found.append(candidate)
                break
    return tuple(dict.fromkeys(found))


def inline_code_words(argv: Sequence[str]) -> tuple[str, ...]:
    """Split ``python -c`` style source so a file name inside it can be recognized."""

    argv = strip_assignments(argv)
    if not argv or not _INLINE_CODE_INTERPRETER.fullmatch(command_name(argv[0])):
        return ()
    words: list[str] = []
    for index, arg in enumerate(argv[1:-1], start=1):
        if arg in _INLINE_CODE_FLAGS:
            words.extend(piece for piece in _INLINE_CODE_SEPARATORS.split(argv[index + 1]) if piece)
    return tuple(words)


def bash_words(scan: BashScan, *, depth: int = 0) -> Iterator[str]:
    """Yield literal words of a command, including nested shell payloads."""

    for word in scan.write_redirects:
        yield word.value
    for argv in scan.argvs():
        yield from argv
        yield from inline_code_words(argv)
        if depth < MAX_NESTED_SHELL_DEPTH:
            for payload in nested_shell_payloads(argv):
                yield from bash_words(scan_bash_command(payload), depth=depth + 1)


def strip_assignments(argv: Sequence[str]) -> tuple[str, ...]:
    index = 0
    while index < len(argv) and _ASSIGNMENT.match(argv[index]):
        index += 1
    return tuple(argv[index:])


def command_name(token: str) -> str:
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in _EXECUTABLE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _reference_candidates(token: str) -> Iterator[str]:
    yield token
    if "=" in token:
        yield token.split("=", 1)[1]
    if ":" in token:
        yield token.rsplit(":", 1)[1]


def _is_powershell_abbreviation(arg: str, parameter: str) -> bool:
    if not arg.startswith("-") or arg.startswith("--") or len(arg) < 2:
        return False
    return parameter.startswith(arg[1:].lower())


def _powershell_recursive_force(args: Sequence[str]) -> bool:
    lowered = [arg.lower() for arg in args]
    if "/s" in lowered and ("/q" in lowered or "/f" in lowered):
        return True
    recursive = any(_is_powershell_abbreviation(arg, "recurse") for arg in args)
    force = any(_is_powershell_abbreviation(arg, "force") for arg in args)
    return (recursive and force) or _rm_recursive_force(args)


def _rm_recursive_force(args: Sequence[str]) -> bool:
    recursive = False
    force = False
    for flag in args:
        if flag == "--":
            break
        if flag in {"--recursive", "--dir"}:
            recursive = True
        elif flag == "--force":
            force = True
        elif flag.startswith("-") and not flag.startswith("--"):
            recursive = recursive or "r" in flag or "R" in flag
            force = force or "f" in flag
    return recursive and force


def _find_reason(args: Sequence[str], depth: int) -> str | None:
    if "-delete" in args:
        return "dangerous_bash_find_delete"
    for index, arg in enumerate(args):
        if arg in _FIND_EXEC_FLAGS:
            tail = [item for item in args[index + 1 :] if item not in {";", "+"}]
            reason = dangerous_argv_reason(tail, depth=depth + 1)
            if reason is not None:
                return reason
    return None


def git_subcommand(args: Sequence[str]) -> tuple[str | None, tuple[str, ...]]:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in _GIT_GLOBAL_VALUE_OPTIONS:
            index += 2
        elif arg.startswith("-"):
            index += 1
        else:
            return arg.lower(), tuple(args[index + 1 :])
    return None, ()


def _git_reason(args: Sequence[str]) -> str | None:
    subcommand, rest = git_subcommand(args)
    if subcommand is None:
        return None
    positional = [arg for arg in rest if not arg.startswith("-")]
    if subcommand == "push":
        return "dangerous_bash_git_push"
    if subcommand == "reset" and "--hard" in rest:
        return "dangerous_bash_git_reset_hard"
    if subcommand == "clean" and _git_clean_forced(rest):
        return "dangerous_bash_git_clean_force_delete"
    if subcommand == "checkout" and ("--" in rest or "." in positional or "-f" in rest or "--force" in rest):
        return "dangerous_bash_git_checkout_discard"
    if subcommand == "restore" and "--staged" not in rest and "-S" not in rest:
        return "dangerous_bash_git_restore_discard"
    if subcommand == "stash" and positional[:1] in (["drop"], ["clear"]):
        return "dangerous_bash_git_stash_discard"
    if subcommand == "branch" and ("-D" in rest or ("--delete" in rest and "--force" in rest)):
        return "dangerous_bash_git_branch_force_delete"
    if subcommand in {"filter-branch", "filter-repo"} or (subcommand == "reflog" and positional[:1] == ["expire"]):
        return "dangerous_bash_git_history_rewrite"
    if subcommand == "update-ref" and "-d" in rest:
        return "dangerous_bash_git_history_rewrite"
    if subcommand == "config" and _git_config_writes(rest, positional):
        return "dangerous_bash_git_config_write"
    return None


def _git_clean_forced(args: Sequence[str]) -> bool:
    for flag in args:
        if flag == "--":
            break
        if flag == "--force" or (flag.startswith("-") and not flag.startswith("--") and "f" in flag):
            return True
    return False


def _git_config_writes(rest: Sequence[str], positional: Sequence[str]) -> bool:
    readers = {"--get", "--get-all", "--get-regexp", "--list", "-l", "--show-origin", "--show-scope"}
    if any(flag in readers for flag in rest):
        return False
    return len(positional) >= 2 or any(
        flag in {"--unset", "--unset-all", "--add", "--replace-all", "--edit", "-e", "--rename-section", "--remove-section"}
        for flag in rest
    )


def _publish_reason(name: str, args: Sequence[str]) -> str | None:
    positional = [arg.lower() for arg in args if not arg.startswith("-")]
    subcommands = _PUBLISH_SUBCOMMANDS.get(name)
    if subcommands is not None and any(item in subcommands for item in positional[:3]):
        return f"dangerous_bash_publish:{name}"
    for sequence in _PUBLISH_SEQUENCES.get(name, ()):
        if tuple(positional[: len(sequence)]) == sequence:
            return f"dangerous_bash_publish:{name}"
    return None


def _deploy_reason(name: str, args: Sequence[str]) -> str | None:
    if name.split(".", 1)[0] == "deploy" or name.startswith(("deploy-", "deploy_")):
        return "dangerous_bash_deploy"
    if name in _DEPLOY_INERT_COMMANDS:
        return None
    for arg in args:
        lowered = arg.lower()
        if lowered == "deploy" or lowered.endswith(":deploy") or lowered.startswith("deploy:"):
            return "dangerous_bash_deploy"
    return None


__all__ = [
    "GUARD_SELF_DISABLE_REASON",
    "BashScan",
    "BashWord",
    "bash_dangerous_reasons",
    "bash_words",
    "command_name",
    "dangerous_argv_reason",
    "git_subcommand",
    "guard_self_disable",
    "inline_code_words",
    "nested_shell_payloads",
    "powershell_dangerous_reasons",
    "scan_bash_command",
    "secret_references",
    "strip_assignments",
]
