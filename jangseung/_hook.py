r"""Start the hook with a Python interpreter directly, without site-packages.

On Windows, ``aeg install`` registers the Claude Code hook as
``<python.exe> -I -S <folder>\jangseung\_hook.py hook-run``. The ``aeg.exe``
launcher starts Python as a second process, and a virtual environment's
``python.exe`` starts the real interpreter as a third; each costs about 8 to
10 ms on every tool call. This file lets the interpreter run the hook itself.

-I keeps environment variables, the user's site-packages and the working
folder off ``sys.path``. -S skips site-packages and ``.pth`` files. This file
then adds only the folder that holds the ``jangseung`` package, after the
standard library, so no installed package can stand in for a standard module.

When that folder is a virtual environment's ``Lib\site-packages``, ``sys.prefix``
is set to the environment, as starting its own ``python.exe`` would. The guard
protects the folders it runs from, ``sys.prefix`` among them, so the hook judges
writes into the environment exactly as it did when started through ``aeg.exe``.
"""

import os
import sys

if __name__ == "__main__":
    _home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _lib = os.path.dirname(_home)
    _environment = os.path.dirname(_lib)
    if (
        os.path.basename(_home).lower() == "site-packages"
        and os.path.basename(_lib).lower() == "lib"
        and os.path.isfile(os.path.join(_environment, "pyvenv.cfg"))
    ):
        sys.prefix = sys.exec_prefix = _environment
    if _home not in sys.path:
        sys.path.append(_home)
    from jangseung.cli.entry import run

    raise SystemExit(run(launcher=os.path.abspath(__file__)))
