"""Keep hooks registered as ``python -m src.cli hook-run`` protecting after an upgrade.

Versions up to 0.1.4 register this command when ``aeg`` is not on PATH. Without
this module it cannot start, and Claude Code lets the tool call through when a
hook fails that way, so upgrading alone would switch the guard off until
``aeg install`` runs again.

``src`` and ``src.cli`` have no ``__init__.py`` on purpose: as namespace packages
they never shadow a project's own ``src`` package.
"""

from __future__ import annotations

import sys

# Exit 2 with a reason on stderr is how both hosts document a block.
_EXIT_BLOCK = 2
_UPDATE_HINT = "jangseung: this hook uses the old 'python -m src.cli' form. Run 'aeg install' to update it."
_BROKEN = "jangseung: the hook could not start, so the tool call is blocked. Run 'aeg doctor --hooks'."
_REFUSED = "jangseung: 'python -m src.cli' only runs registered hooks now. Use the 'aeg' command."


def _notify(message: str) -> None:
    try:
        sys.stderr.write(message + "\n")
    except Exception:  # noqa: BLE001 - nothing can be written; the exit code still decides.
        pass


def main() -> int:
    arguments = sys.argv[1:]
    if arguments[:1] != ["hook-run"]:
        _notify(_REFUSED)
        return _EXIT_BLOCK
    try:
        from jangseung.cli.entry import main as guard_main

        code = guard_main(arguments)
    except Exception:  # noqa: BLE001 - any failure of the hook path must block.
        _notify(_BROKEN)
        return _EXIT_BLOCK
    _notify(_UPDATE_HINT)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
