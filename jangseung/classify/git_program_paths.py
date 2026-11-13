"""Project files that git runs or loads because its configuration names them.

Agents can write ordinary project files, and read-only git commands run without a
prompt. A hook folder, an included config or a program that a person's git
configuration points at must therefore stay out of an agent's reach, or the agent
chooses what ``git status`` runs. The configuration is only read here, never run.
"""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shlex

from jangseung._resolve import resolved as _resolved

MAX_CONFIG_BYTES = 1024 * 1024
MAX_CONFIG_FILES = 32

# Keys whose value is a shell command git starts during status, diff, log or blame.
_COMMAND_KEYS = frozenset({"fsmonitor", "external", "command", "textconv", "clean", "smudge", "process"})


def git_program_paths(repo_root: str | Path, working_dir: str | Path | None = None) -> tuple[str, ...]:
    """Repo-relative paths the configuration of the repository in use points at."""

    try:
        root = _resolved(repo_root)
        found = _repository_configs(_resolved(root if working_dir is None else working_dir))
        if found is None:
            return ()
        top, configs, hooks = found
        return _inside_project([*_named_by_configs([*configs, *_user_configs()], top), *_linked_hooks(hooks)], root)
    except (OSError, ValueError, RuntimeError):
        return ()


def _repository_configs(start: Path) -> tuple[Path, list[Path], Path] | None:
    """The worktree top, config files and hooks folder of the repository git finds from ``start``."""

    for directory in (start, *start.parents):
        dot_git = directory / ".git"
        if dot_git.is_dir():
            return directory, [dot_git / "config", dot_git / "config.worktree"], dot_git / "hooks"
        if dot_git.is_file():
            # A linked worktree: its .git file points at a folder holding the shared one's path.
            text = dot_git.read_text(encoding="utf-8", errors="replace").strip()
            if not text.startswith("gitdir:"):
                return None
            git_dir = (directory / text[len("gitdir:") :].strip()).resolve()
            pointer = git_dir / "commondir"
            common = git_dir
            if pointer.is_file():
                common = (git_dir / pointer.read_text(encoding="utf-8", errors="replace").strip()).resolve()
            return directory, [common / "config", git_dir / "config.worktree"], common / "hooks"
    return None


def _linked_hooks(hooks: Path) -> list[Path]:
    """Where a hooks folder or its hooks really live, when linked out of ``.git``."""

    if _resolved(hooks) != _resolved(hooks.parent) / hooks.name:
        return [hooks]
    return [entry for entry in hooks.iterdir() if entry.is_symlink()] if hooks.is_dir() else []


def _user_configs() -> list[Path]:
    explicit = os.environ.get("GIT_CONFIG_GLOBAL")
    if explicit:
        return [Path(explicit)]
    xdg = os.environ.get("XDG_CONFIG_HOME")
    home = Path.home()
    return [(Path(xdg) if xdg else home / ".config") / "git" / "config", home / ".gitconfig"]


def _named_by_configs(configs: list[Path], top: Path) -> list[Path]:
    named: list[Path] = []
    pending = list(configs)
    seen: set[Path] = set()
    while pending and len(seen) < MAX_CONFIG_FILES:
        config = pending.pop()
        if config in seen:
            continue
        seen.add(config)
        text = _read_small(config)
        if text is not None:
            programs, included = _paths_in_config(text, config.parent, top)
            named += [*programs, *included]
            pending += included
    return named


def _read_small(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_CONFIG_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _paths_in_config(text: str, config_dir: Path, top: Path) -> tuple[list[Path], list[Path]]:
    """Paths a config names: programs relative to the worktree, includes to the file."""

    programs: list[Path] = []
    included: list[Path] = []
    for name, value in config_entries(text):
        section, _, key = name.rpartition(".")
        base = section.split(".", 1)[0]
        if not value:
            continue
        if section == "core" and key == "hookspath":
            programs.append(top / Path(value).expanduser())
        elif base in {"include", "includeif"} and key == "path":
            included.append(config_dir / Path(value).expanduser())
        elif key in _COMMAND_KEYS or (base == "gpg" and key == "program"):
            programs += [top / Path(word).expanduser() for word in _path_words(value)]
    return programs, included


def _path_words(command: str) -> list[str]:
    """Words of a shell command that can be project files; ``git-lfs clean -- %f`` holds none."""

    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    return [
        word
        for index, word in enumerate(words)
        if "/" in word or "\\" in word or (index > 0 and "." in word and not word.startswith(("-", "%")))
    ]


def config_entries(text: str) -> Iterator[tuple[str, str | None]]:
    """``(section.key, value)`` read the way git reads a config file.

    Ends where git would refuse the file. Sections and keys are lower case, except a
    quoted subsection; a key without ``=`` has no value.
    """

    text = text.removeprefix("﻿").replace("\r\n", "\n")
    index = 0
    section = ""
    while index < len(text):
        char = text[index]
        index += 1
        if char in " \t\r\n":
            continue
        if char in "#;":
            newline = text.find("\n", index)
            index = len(text) if newline == -1 else newline + 1
        elif char == "[":
            header = _section_header(text, index)
            if header is None:
                return
            section, index = header
        elif char.isascii() and char.isalpha():
            end = index
            while end < len(text) and _is_key_character(text[end]):
                end += 1
            key = text[index - 1 : end].lower()
            while end < len(text) and text[end] in " \t\r":
                end += 1
            if end >= len(text) or text[end] == "\n":
                yield f"{section}.{key}", None
                index = end + 1
                continue
            if text[end] != "=":
                return
            parsed = _value(text, end + 1)
            if parsed is None:
                return
            value, index = parsed
            yield f"{section}.{key}", value
        else:
            return


def _is_key_character(char: str) -> bool:
    return char == "-" or (char.isascii() and char.isalnum())


def _section_header(text: str, index: int) -> tuple[str, int] | None:
    base: list[str] = []
    while index < len(text):
        char = text[index]
        index += 1
        if char == "]":
            return "".join(base), index
        if char in " \t\r\n":
            return _subsection(text, index, "".join(base))
        if not _is_key_character(char) and char != ".":
            return None
        base.append(char.lower())
    return None


def _subsection(text: str, index: int, base: str) -> tuple[str, int] | None:
    while index < len(text) and text[index] in " \t\r":
        index += 1
    if index >= len(text) or text[index] != '"':
        return None
    index += 1
    name: list[str] = []
    while index < len(text):
        char = text[index]
        index += 1
        if char == "\n":
            return None
        if char == '"':
            if index < len(text) and text[index] == "]":
                return f"{base}.{''.join(name)}", index + 1
            return None
        if char == "\\":
            if index >= len(text) or text[index] == "\n":
                return None
            char = text[index]
            index += 1
        name.append(char)
    return None


def _value(text: str, index: int) -> tuple[str, int] | None:
    escapes = {"t": "\t", "b": "\b", "n": "\n", "\\": "\\", '"': '"'}
    value: list[str] = []
    spaces = 0
    quoted = False
    comment = False
    while True:
        if index >= len(text):
            return None if quoted else ("".join(value), index)
        char = text[index]
        index += 1
        if char == "\n":
            return None if quoted else ("".join(value), index)
        if comment:
            continue
        if char in " \t\r" and not quoted:
            spaces += 1 if value else 0
            continue
        if not quoted and char in "#;":
            comment = True
            continue
        value.append(" " * spaces)
        spaces = 0
        if char == "\\":
            if index >= len(text):
                return None
            escaped = text[index]
            index += 1
            if escaped == "\n":
                continue
            if escaped not in escapes:
                return None
            value.append(escapes[escaped])
        elif char == '"':
            quoted = not quoted
        else:
            value.append(char)


def _inside_project(paths: list[Path], root: Path) -> tuple[str, ...]:
    inside: list[str] = []
    for path in paths:
        try:
            relative = _resolved(path).relative_to(root)
        except (OSError, ValueError, RuntimeError):
            continue
        if relative.parts:
            inside.append(relative.as_posix())
    return tuple(dict.fromkeys(inside))


__all__ = ["config_entries", "git_program_paths"]
