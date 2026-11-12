"""``aeg allow-once`` — let an agent run one exact command, once, in this project.

Meant for Codex, where the hook cannot ask a person and denies what it cannot prove
safe. Only a person runs this: the hook denies an agent's call to it. The approval
covers the exact text given, expires after a few minutes and is spent on first use.
It lifts what an ``allow_commands`` entry lifts; secret, guard and target rules still
apply.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from jangseung.state.allow_once import DEFAULT_MINUTES, DEFAULT_TOOL, MAX_MINUTES, TOOLS, clear_all, grant_once, pending_count

_MAX_COMMAND_CHARACTERS = 4000


def cmd_allow_once(
    project: str | Path,
    command: str | None,
    *,
    minutes: int = DEFAULT_MINUTES,
    clear: bool = False,
    status: bool = False,
    tool: str = DEFAULT_TOOL,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    if clear:
        count = clear_all(project)
        print(f"aeg allow-once: removed {count} pending approval(s).", file=out)
        return 0
    if status or command is None:
        print(f"aeg allow-once: {pending_count(project)} pending approval(s).", file=out)
        return 0
    if not command.strip() or len(command) > _MAX_COMMAND_CHARACTERS or "\x00" in command:
        print("aeg allow-once: give the exact command text, in quotes.", file=out)
        return 2
    if not 1 <= minutes <= MAX_MINUTES:
        print(f"aeg allow-once: --minutes must be between 1 and {MAX_MINUTES}.", file=out)
        return 2
    if tool not in TOOLS:
        print(f"aeg allow-once: --tool must be one of: {', '.join(TOOLS)}.", file=out)
        return 2
    expires = grant_once(command, project, minutes, tool)
    print("aeg allow-once: approved once, for this exact text:", file=out)
    print(f"  {command}", file=out)
    print(f"For the {tool} tool, run from the project folder itself (not a subfolder).", file=out)
    print(f"Expires at {expires.strftime('%H:%M:%S')} UTC or on first use, whichever comes first.", file=out)
    print("Secret, guard and target rules still apply; a session that wrote text naming a secret file is still asked.",
          file=out)
    return 0


__all__ = ["cmd_allow_once"]
