"""Recognize a small, explicit shell read grammar; never execute commands.

This is a positive classifier, not a general shell parser. Unsupported options,
expansions, redirection and control flow receive no allow classification. Paths
must subsequently pass the hook's existing repository/protected-path gates.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import shlex


@dataclass(frozen=True)
class ShellRead:
    classified: bool = False
    paths: tuple[str, ...] = ()


def classify_shell_read(command: str, *, tool_name: str) -> ShellRead:
    if not isinstance(command, str) or not command.strip() or len(command) > 16000:
        return ShellRead()
    # Check before tokenization: quoted/escaped syntax must never become new
    # grammar after quote removal. Conservative rejection is intentional.
    if any(char in command for char in "\n\r\x00$`{}()&;<>#"):
        return ShellRead()
    powershell = tool_name == "PowerShell" or bool(
        re.match(r"(?i)^\s*Get-Content(?:\s|$)", command)
    )
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
    paths: list[str] = []
    for index, segment in enumerate(segments):
        if not segment:
            return ShellRead()
        parsed = _powershell_read(segment, index > 0) if powershell else _posix_read(segment, index > 0)
        if parsed is None:
            return ShellRead()
        paths.extend(parsed)
    if any(not _literal_path(path) for path in paths):
        return ShellRead()
    return ShellRead(True, tuple(dict.fromkeys(paths)))


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


def _posix_read(tokens: list[str], piped: bool) -> list[str] | None:
    name, *args = tokens
    if name not in {"cat", "head", "tail", "sed", "rg"}:
        return None
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
                if re.fullmatch(r"-[nc]\d+", arg):
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
    return paths


def _powershell_read(tokens: list[str], piped: bool) -> list[str] | None:
    name, *args = tokens
    name = name.lower()
    if name == "select-object":
        if not piped or not args:
            return None
        while args:
            if len(args) < 2 or args[0].lower() not in {"-first", "-last", "-skip"} or not args[1].isdigit():
                return None
            args = args[2:]
        return []
    if name != "get-content":
        return None
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
    return paths if paths else None
