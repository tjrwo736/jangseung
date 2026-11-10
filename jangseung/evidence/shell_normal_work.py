"""Small positive grammars for normal file work and host-controlled execution.

These helpers do not judge paths or grant permission. A file operation needs the
engine's filesystem gates; an execution candidate can only use the host's normal
permission flow, never a hook allow. Unknown programs and shell syntax stay out.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import shlex


# Deliberately shared by Bash and PowerShell: no expansion, escaped characters,
# concatenated quotes, glob, providers, response files, or shell control syntax.
_WORD = r'''(?:[A-Za-z0-9_./:=+\-]+|'[A-Za-z0-9_ ./:=+\-]*'|"[A-Za-z0-9_ ./:=+\-]*")'''
_WORDS = re.compile(rf"[ \t]*{_WORD}(?:[ \t]+{_WORD})*[ \t]*")
_PATH = re.compile(r"(?:\./)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
_DEVICES = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))})
_INTERPRETERS = re.compile(r"python(?:3(?:\.\d+)?)?|node|ruby|perl|lua")
_EXECUTION_PROGRAMS = frozenset({
    "pytest", "ruff", "mypy", "pyright", "pylint", "black", "isort", "coverage", "tox", "nox",
    "pip", "pip3", "uv", "poetry", "pdm", "pipx", "npm", "npx", "pnpm", "yarn", "bun",
    "make", "gmake", "cmake", "ninja", "cargo", "rustc", "go", "dotnet", "gradle", "mvn",
})
_GIT_EXECUTION = frozenset({"add", "commit", "fetch", "pull", "merge", "rebase", "switch", "checkout", "stash", "cherry-pick"})
# Leaving a request to the host is only safe when the host itself asks a person.
# Claude Code runs read-only git forms on its own: measured with 2.1.316, it ran
# ``git stash show -p`` with no approval and printed a stashed .env. So only stash
# forms that change state are left to it, and no form that prints file content.
_GIT_STASH_STATE_CHANGES = frozenset({"push", "pop", "apply", "save", "branch"})
# git takes bundled short flags (``-pq``) and any unique prefix of a long option
# (``--patc``), so options are matched by letter and by prefix, not by spelling.
# ``--long``, ``--short`` and ``--porcelain`` make ``git commit`` a dry run that prints.
_GIT_CONTENT_SHORT_FLAGS = frozenset("pvi")
_GIT_CONTENT_LONG_OPTIONS = (
    "patch", "verbose", "dry-run", "show-current-patch", "interactive", "long", "short", "porcelain",
)


def _git_option_prints_content(word: str) -> bool:
    if word.startswith("--"):
        name = word[2:].partition("=")[0]
        return bool(name) and any(option.startswith(name) for option in _GIT_CONTENT_LONG_OPTIONS)
    if word.startswith("-") and len(word) > 1:
        return bool(_GIT_CONTENT_SHORT_FLAGS.intersection(word[1:]))
    return False
_GH_EXECUTION = frozenset({"pr", "issue", "run", "workflow"})


def plain_command_words(command: str) -> tuple[str, ...]:
    if not isinstance(command, str) or len(command) > 16000 or not _WORDS.fullmatch(command):
        return ()
    return tuple(shlex.split(command))


def host_execution_candidate(command: str) -> bool:
    """Recognized execution family, not a known read command or a shell wrapper.

The programs can run project code. This is NOT a claim they are safe: the person
and the host permission rules, including existing allow rules, decide execution.
"""
    words = plain_command_words(command)
    if not words or not re.fullmatch(r"[a-z][a-z0-9]*", words[0]):
        return False
    name, *arguments = words
    if any(word.lower() in {"install", "uninstall", "policy", "repair-hooks"} for word in arguments):
        guard_names = {"aeg", "aeg.py", "aeg.exe", "aeg.cmd"}
        if any(
            word.rsplit("/", 1)[-1].lower().rstrip(".") in guard_names
            or word.lower().startswith(("jangseung", "src.cli"))
            for word in arguments
        ):
            # Wrappers outside the danger parser's grammar must not turn a
            # suspected guard-control invocation into host-delegated execution.
            return False
    if name == "git":
        if not arguments or arguments[0] not in _GIT_EXECUTION:
            return False
        if any(_git_option_prints_content(word) for word in arguments[1:]):
            return False
        if arguments[0] == "stash":
            subcommand = next((word for word in arguments[1:] if not word.startswith("-")), None)
            return subcommand is None or subcommand in _GIT_STASH_STATE_CHANGES
        return True
    if name == "gh":
        return bool(arguments) and arguments[0] in _GH_EXECUTION
    if _INTERPRETERS.fullmatch(name):
        # Inline code is not a simple project execution request. Its contents
        # deserve the old explicit ask even if the narrow lexer happened to fit.
        if not arguments or any(arg in {"-c", "-e", "-p", "--eval", "--print"} for arg in arguments):
            return False
        return not arguments[0].startswith("-") or arguments[0] == "-m"
    return name in _EXECUTION_PROGRAMS


@dataclass(frozen=True)
class ShellFileOperation:
    operation: str
    paths: tuple[str, ...]


def _literal_project_path(path: str) -> bool:
    if not _PATH.fullmatch(path) or path.startswith("-"):
        return False
    parts = path.removeprefix("./").split("/")
    return all(
        part not in {".", ".."} and not part.endswith(".")
        and part.split(".", 1)[0].lower() not in _DEVICES
        for part in parts
    )


def classify_shell_file_operation(command: str, *, tool_name: str) -> ShellFileOperation | None:
    """Only nonrecursive, literal operations; caller verifies every source/destination."""
    if tool_name not in {"Bash", "PowerShell"} or not isinstance(command, str):
        return None
    operation = ""
    paths: tuple[str, ...] = ()
    if ">" in command:
        # A single echo/Write-Output redirect. No descriptors, pipeline, nested
        # shell, escape, echo switches or second redirect can enter this grammar.
        match = re.fullmatch(r"(.+?)[ \t]+(>>?)[ \t]+(.+)", command)
        if match is None:
            return None
        left, right = plain_command_words(match[1]), plain_command_words(match[3])
        if not left or left[0] not in {"echo", "Write-Output", "write-output"} or len(left) < 2 or len(right) != 1:
            return None
        if any(word.startswith("-") for word in left[1:]):
            return None
        operation, paths = "write", right
    else:
        words = plain_command_words(command)
        if not words:
            return None
        name, *args = words
        if tool_name == "PowerShell":
            name = name.lower()
        aliases = {"copy-item": "cp", "move-item": "mv", "remove-item": "rm"}
        if name in aliases:
            # Native commands must use literal paths; no abbreviated options.
            if not args or args.pop(0).lower() != "-literalpath":
                return None
            if name in {"copy-item", "move-item"}:
                if len(args) != 3 or args[1].lower() != "-destination":
                    return None
                args = [args[0], args[2]]
            name = aliases[name]
        if name == "mkdir" and args and args[0] == "-p":
            args.pop(0)
        if any(arg.startswith("-") for arg in args):
            return None
        if name in {"mkdir", "touch"} and 1 <= len(args) <= 16:
            operation, paths = name, tuple(args)
        elif name in {"cp", "mv"} and len(args) == 2:
            operation, paths = name, tuple(args)
        elif name == "rm" and len(args) == 1:
            operation, paths = name, tuple(args)
    if not paths or not all(_literal_project_path(path) for path in paths):
        return None
    return ShellFileOperation(operation, paths)
