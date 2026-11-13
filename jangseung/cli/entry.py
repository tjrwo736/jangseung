"""Process entry point that keeps ``aeg hook-run`` fail-closed.

Claude Code treats any exit code other than 0 or 2 as a non-blocking error, so
an import failure or an uncaught exception must still produce a deny response.
This module imports nothing from the package until it is inside that protection.
It also imports nothing that Python has not already loaded when it starts, so the
hook commands can turn on :mod:`jangseung._import_cache` before any other module
is read.
"""

import sys

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_ENTRYPOINT_FAILED_REASON = "hook_entrypoint_failed_fail_closed_deny"


def _load_cli_main() -> "Callable[[Sequence[str] | None], int]":
    from jangseung.cli.main import main

    return main


def _load_hook_main() -> "Callable[[Sequence[str]], int]":
    # The hook runs on every tool call, so it skips the commands it does not need.
    from jangseung.cli.hook_run import run_hook_cli

    return run_hook_cli


def main(argv: "Sequence[str] | None" = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["session-check"]:
        # A SessionStart hook: it must never stop a session from starting.
        try:
            from jangseung.cli.session_check import main as session_check_main

            return session_check_main(arguments[1:])
        except Exception:  # noqa: BLE001
            return 0
    if arguments[:1] != ["hook-run"]:
        return _load_cli_main()(arguments)
    try:
        return _load_hook_main()(arguments[1:])
    except Exception:  # noqa: BLE001 - any failure of the hook path must deny.
        return _deny(arguments)


def _deny(arguments: "Sequence[str]") -> int:
    codex = "codex" in arguments[1:]
    substrate = "codex" if codex else "claude-code"
    reason = (
        "aegis_pretooluse permissionDecision=deny; hook_decision=none;"
        f" substrate={substrate}; tool_name=unknown; reason_codes={_ENTRYPOINT_FAILED_REASON}"
    )
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    try:
        import json

        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        print(reason, file=sys.stderr)
    except Exception:  # noqa: BLE001 - nothing can be written; block by exit code alone.
        return 2
    # Codex reads the decision from JSON and expects exit 0, as hook-run does.
    return 0 if codex else 2


# The hook commands end the process as soon as the answer is written. A normal
# interpreter shutdown tears down every module and object first, about 3 ms on
# each tool call, and the hook path leaves no file, thread or exit handler open.
_QUICK_EXIT_COMMANDS = ("hook-run", "session-check")


def run(argv: "Sequence[str] | None" = None, *, launcher: "str | None" = None) -> int:
    """Program entry for ``aeg``, ``python -m jangseung.cli`` and the launchers.

    The same as :func:`main`, except for the hook commands. They leave the
    process with ``os._exit`` once their output is flushed, and when the process
    was started for them (arguments taken from ``sys.argv``) they load compiled
    modules through :mod:`jangseung._import_cache`. Code that calls ``main``, or
    ``run`` with arguments, keeps Python's import system as it is.

    ``launcher`` is the launcher file that started this process
    (``jangseung/_hook.py`` or the ``aeg`` script). With it, ``hook-run`` asks
    the resident judging process (:mod:`jangseung._resident`) first and judges
    the call itself only when that process cannot answer.
    """

    arguments = list(sys.argv[1:] if argv is None else argv)
    process_start = argv is None
    if process_start and launcher is not None and arguments == [_RESIDENT_SERVE]:
        return _serve_resident(launcher)
    quick = bool(arguments) and arguments[0] in _QUICK_EXIT_COMMANDS
    if quick and process_start:
        if launcher is not None and sys.platform == "win32":
            _use_resident(arguments[0], launcher)
        _start_import_cache(arguments[0])
    code = main(arguments)
    if quick:
        _exit_now(code, session_check=arguments[0] == "session-check")
    return code


_RESIDENT_SERVE = "resident-serve"


def _use_resident(command: str, launcher: str) -> None:
    """Have the resident process answer; returns only when this process must judge."""

    try:
        from jangseung import _resident

        if command == "session-check":
            _resident.plan_session(launcher)
            return
        answer = _resident.ask(launcher)
    except Exception:  # noqa: BLE001 - the call is judged here instead.
        return
    if answer is None:
        return
    code, out, err = answer
    try:
        sys.stdout.buffer.write(out)
    except Exception:  # noqa: BLE001 - the answer did not leave; only exit 2 can still block.
        code = 2
    try:
        sys.stderr.buffer.write(err)
    except Exception:  # noqa: BLE001 - the decision already went to stdout.
        pass
    _exit_now(code, session_check=False)


def _serve_resident(launcher: str) -> int:
    from jangseung import _resident_server

    return _resident_server.serve(launcher)


def _start_resident() -> None:
    resident = sys.modules.get("jangseung._resident")
    if resident is None:
        return
    try:
        resident.start_if_needed()
    except Exception:  # noqa: BLE001 - the next call judges directly and tries again.
        pass


def _start_import_cache(command: str) -> None:
    try:
        from jangseung import _import_cache

        _import_cache.start(command)
    except Exception:  # noqa: BLE001 - the normal import path stays in place.
        pass


def _save_import_cache() -> None:
    cache = sys.modules.get("jangseung._import_cache")
    if cache is None:
        return
    try:
        cache.save()
    except Exception:  # noqa: BLE001 - the answer is already out; the next call tries again.
        pass


def _exit_now(code: int, *, session_check: bool) -> None:
    import os

    try:
        sys.stdout.flush()
    except Exception:  # noqa: BLE001
        # The answer did not leave. Only exit 2 can still block the call; a
        # session check never blocks.
        code = 0 if session_check else 2
    try:
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - the decision already went to stdout.
        pass
    _save_import_cache()
    _start_resident()
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(run())
