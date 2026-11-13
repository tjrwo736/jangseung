"""Load the hook's compiled modules from one file.

The hook runs as a new Python process on every tool call. Python keeps each
module's compiled form in a file of its own under ``__pycache__`` and opens one
file per module. On Windows with real-time virus scanning, opening a file costs
about 0.3 ms, and the hook loads about 60 modules, the standard library's
included. This keeps the compiled forms the hook loaded in one file next to the
package's compiled files, so a call opens one file instead of about 60. It is
used on Windows only: on Linux (measured under WSL) opening a file is cheap and
the cache made no difference, so other systems keep Python's import as it is.

Only where the bytes come from changes:

* Python still finds every module itself, through the same path entries in the
  same order. This only stands in for reading the ``__pycache__`` file Python
  has already chosen.
* A stored form is used only while its header names the source file's current
  modification time and size, the check Python makes on a ``__pycache__`` file,
  and Python then checks it again itself. Otherwise the ``__pycache__`` file is
  read as usual, and the stored form is replaced when the call ends. Only
  timestamp-based compiled files are stored; hash-based ones are always read
  from ``__pycache__``.
* A stored form that still matches its source is used even when its
  ``__pycache__`` file was deleted. Deleting the package's ``__pycache__``
  folder deletes this file too.
* Only the hook commands of a real process start turn it on
  (:func:`jangseung.cli.entry.run`). Code that imports the package never does.
* When anything here fails, the normal import path stays in place. A file that
  is damaged (its checksum does not match), too large or from another Python is
  ignored and written again.

Each hook command has its own file, ``__pycache__/<command>-imports.<cache
tag>.bin`` in the package folder (with ``.opt-1`` or ``.opt-2`` under ``-O``),
so a tool call does not read the modules only the once-a-session check loads.
It is written only when it was missing or out of date, and never when Python is
told not to write compiled files; it is still read then, as ``__pycache__``
files are. It holds code, like the ``__pycache__`` files beside it, and the
guard protects the package folder as part of its runtime.
"""

import binascii
import io
import marshal
import os
import sys

_FORMAT = 2
_SIZE_LIMIT = 8 * 1024 * 1024
_CACHE_NAME = "{command}-imports.{tag}{optimization}.bin"
_COMMANDS = ("hook-run", "session-check")
_TIMESTAMP_FLAGS = bytes(4)


class _State:
    path = None  # the cache file, once this process has started using it
    stored: dict = {}  # compiled-file path -> bytes read from the cache file
    used: dict = {}  # compiled-file path -> bytes this process loaded
    changed = False


def start(command: str) -> bool:
    """Serve compiled modules from ``command``'s cache file for the rest of this process.

    Returns whether the cache is in use. Calling it again changes nothing.
    """

    if _State.path is not None:
        return True
    if sys.platform != "win32" or command not in _COMMANDS:
        return False
    external = sys.modules.get("_frozen_importlib_external")
    tag = getattr(sys.implementation, "cache_tag", None)
    supported = getattr(external, "_get_supported_file_loaders", None)
    if external is None or tag is None or supported is None:
        return False
    position = _file_finder_hook_position()
    loaders = supported()
    if position is None or not any(loader is external.SourceFileLoader for loader, _ in loaders):
        return False
    package = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.dirname(external.cache_from_source(os.path.join(package, "__init__.py")))
    optimization = f".opt-{sys.flags.optimize}" if sys.flags.optimize else ""
    path = os.path.join(folder, _CACHE_NAME.format(command=command, tag=tag, optimization=optimization))
    cached = _cached_loader(external)
    hook = external.FileFinder.path_hook(
        *[(cached if loader is external.SourceFileLoader else loader, suffixes) for loader, suffixes in loaders]
    )
    _State.stored = _read(path, external.MAGIC_NUMBER)
    sys.path_hooks[position] = hook
    # Finders made before this point would keep reading __pycache__ files.
    sys.path_importer_cache.clear()
    _State.path = path
    return True


def save() -> None:
    """Write the cache file if this process found it missing or out of date."""

    if _State.path is None or not _State.changed or sys.dont_write_bytecode:
        return
    _State.changed = False
    temporary = f"{_State.path}.{os.getpid()}.tmp"
    try:
        # Opened first, so a folder that cannot be written costs no serialising.
        stream = open(temporary, "xb")
    except OSError:
        return
    try:
        with stream:
            entries = dict(_State.stored)
            entries.update(_State.used)
            if sum(len(data) for data in entries.values()) > _SIZE_LIMIT:
                entries = dict(_State.used)
            magic = sys.modules["_frozen_importlib_external"].MAGIC_NUMBER
            body = marshal.dumps((_FORMAT, magic, entries))
            stream.write(binascii.crc32(body).to_bytes(4, "little"))
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, _State.path)
    except OSError:
        # Another hook process is reading the file, or the disk refused: the next call tries again.
        try:
            os.remove(temporary)
        except OSError:
            pass


def _file_finder_hook_position():
    for position, hook in enumerate(sys.path_hooks):
        if getattr(hook, "__qualname__", "") == "FileFinder.path_hook.<locals>.path_hook_for_FileFinder":
            return position
    return None


def _read(path: str, magic: bytes) -> dict:
    try:
        # open_code is how Python itself opens code, so a code-verification hook still sees it.
        with io.open_code(path) as stream:
            if os.fstat(stream.fileno()).st_size > _SIZE_LIMIT + 4096:
                return {}
            data = stream.read()
        body = memoryview(data)[4:]
        if binascii.crc32(body) != int.from_bytes(data[:4], "little"):
            return {}  # damaged: every module is read from __pycache__ and the file written again
        version, cache_magic, entries = marshal.loads(body)
    except Exception:  # noqa: BLE001 - missing, unreadable or damaged: start empty.
        return {}
    if version != _FORMAT or cache_magic != magic or type(entries) is not dict:
        return {}
    return {key: value for key, value in entries.items() if type(key) is str and type(value) is bytes}


def _cached_loader(external):
    bytecode_suffixes = tuple(external.BYTECODE_SUFFIXES)
    magic = external.MAGIC_NUMBER

    def storable(data) -> bool:
        # A timestamp-based compiled file for this Python: magic, then flags 0.
        return len(data) >= 16 and data[:4] == magic and data[4:8] == _TIMESTAMP_FLAGS

    def current(data, stats) -> bool:
        # Then the source's modification time and size, each 32 bits, as Python checks them.
        return (
            stats is not None
            and storable(data)
            and int.from_bytes(data[8:12], "little") == (int(stats["mtime"]) & 0xFFFFFFFF)
            and int.from_bytes(data[12:16], "little") == (stats["size"] & 0xFFFFFFFF)
        )

    def remember(path, data) -> None:
        data = bytes(data)
        _State.used[path] = data
        if _State.stored.get(path) != data:
            _State.changed = True

    class CachedSourceFileLoader(external.SourceFileLoader):
        """Python's source loader, reading compiled files from the cache file first."""

        _source_stats = None

        def path_stats(self, path):
            stats = super().path_stats(path)
            if path == self.path:
                self._source_stats = stats
            return stats

        def get_data(self, path):
            data = _State.stored.get(path)
            if data is not None and current(data, self._source_stats):
                _State.used[path] = data
                return data
            data = super().get_data(path)
            if path.endswith(bytecode_suffixes) and storable(data):
                remember(path, data)
            return data

        def set_data(self, path, data, **options):
            # Python compiled the source again because the compiled form was missing or stale.
            if storable(data):
                remember(path, data)
            return super().set_data(path, data, **options)

    return CachedSourceFileLoader
