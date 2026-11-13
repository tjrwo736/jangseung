# Jangseung 0.3.1 release notes

Korean original: [release_0.3.1.md](release_0.3.1.md)

This release makes the hook call faster. Decisions did not change.

```bash
python -m pip install --upgrade jangseung
```

If you registered the hook with `aeg install` on Windows, run `aeg install` again in the project after upgrading. The registration changes to a faster form that uses the resident judging process (below). Without it, the existing registration keeps working and is faster too. If you use the plugin, update the plugin.

## How much faster

Medians of 240 runs each, 0.3.0 and 0.3.1 in turn, in the same project (Windows 11, Python 3.14.5, real-time virus scanning on, a new process per call as Claude Code starts the hook, packages on the C: drive).

| How the hook runs | 0.3.0 | 0.3.1 | Change |
|---|---|---|---|
| Registered by re-running `aeg install` on Windows (`python.exe -I -S …\jangseung\_hook.py hook-run`) | 150.7 ms (`aeg.exe`) | 32.7 ms | −78% |
| The same registration with the resident process off (judged per call) | 150.7 ms | 50.8 ms | −66% |
| Existing registration, `aeg install` not re-run (`aeg.exe hook-run`) | 150.7 ms | 86.4 ms | −43% |
| `python -I -m jangseung.cli hook-run` | 137.8 ms | 66.0 ms | −52% |
| Plugin hook | 276.1 ms | 79.5 ms | −71% |
| Plugin with the resident process off | 276.1 ms | 109.8 ms | −60% |

- The PC was slower when this table was measured than in the morning. Bare start-up measured at the same time was about 14 ms for a small native program, 22.7 ms for Python and 38.1 ms for Node.js, against about 10 ms, 17.3 ms and 34.5 ms in the morning. 0.3.0 and 0.3.1 were measured in turn, so the ratios hold.
- Against other tools: on this PC a native executable (such as dcg) needs about 14 ms just to start, and a Node.js tool (such as cc-safety-net) cannot be faster than 38 ms. Those tools themselves were not measured.
- The 0.3.1 figures are with the module cache file and the resident judging process ready. The first call after an upgrade takes a little longer while it prepares them.
- Measured shortly after the files were installed, each figure was about 10 ms higher. Virus scanning checking newly written files more is the likely cause; it was not confirmed.
- The plugin's 0.3.0 figure was measured on a PC where `python3` is the Microsoft Store stub. Where a real `python3` exists, the difference is smaller by one Python start (about 30 ms).
- The plugin figures include starting Git Bash and the shell starting Python as a child process (about 30 ms together). The `python3` the plugin picks on this PC is the Python install manager's, and in its folder one file status check is about ten times slower than in `C:\Python314` (67 µs against 5 µs).

## What changed

The hook runs as a new Python process on every tool call, so starting processes, loading modules and one-time costs are paid every time. A 0.3.0 call took about 30 ms to start Python, about 77 ms to load modules and about 20 ms to judge and record.

The resident judging process (Windows):

- **A process with the judging code already loaded answers.** The judgment itself takes about 5 ms; starting Python and loading modules for every call took several times that. A hook call now reads its input, hands it over a named pipe to the resident judging process and writes the answer it gets back. It is the same Jangseung kept awake, under these rules:
  - **Same code and start.** The resident process is started through the same launcher, with the same Python and the same interpreter options as the hook command, and judges with the same function a per-call hook uses.
  - **Same inputs.** Each call is judged with its own arguments, working folder, full environment, input bytes and output encodings. Nothing one judgment leaves behind is read by the next. The recursion headroom is set to what a per-call hook has.
  - **Same files.** Before every answer, the folders its code came from and those on `sys.path` are compared with the disk. If a file changes, appears or disappears, or a folder appears that could stand in for a module, it does not answer and stops, and that call is judged directly. An upgrade or a code edit takes effect from the very next call.
  - **Fail-closed.** If the resident process is missing, does not prove it holds the key within 1 second, does not answer within 10 seconds, or its answer's signature does not match, the hook judges the call itself as before. Ending the resident process only makes calls slower; protection stays. When it is missing or cannot prove itself, a new one is started.
  - **Recorded.** The judgment writes the ledger record, before the answer is sent. A call the hook has stopped waiting for is not judged, so it is not recorded twice.
  - **Local and private.** The pipe takes no remote clients, and only the current user and SYSTEM can open it. The hook first sends a challenge; only after the resident process proves it holds the key in `%LOCALAPPDATA%\jangseung\resident` does the hook send the call. The answer is signed with the same key, bound to that call.
- **Where it is used:** `hook-run` started on Windows by `jangseung/_hook.py` (the new registration) or the `aeg` launcher (the plugin). `aeg.exe`, `python -m`, Codex registrations, macOS and Linux judge per call.
- **Lifetime:** the session-start check starts it, so the first tool call of a session is already fast. It stops by itself after 15 minutes without a call.
- **Turning it off:** set `JANGSEUNG_RESIDENT=off` in the hook's environment, for example in the `env` of Claude Code's settings.
- **What you see:** one `python.exe` in Task Manager (no window, about 30 MB). Real `claude -p` sessions took 7.1 s with it on and 6.9 s with it off; Claude Code does not wait for this process.

Starting the process:

- **On Windows, `aeg install` starts Python directly (about 22 ms).** `aeg.exe` starts Python as a second process, and a virtual environment's `python.exe` starts the real interpreter as a third. `aeg install` now registers the Claude Code hook as `<python.exe> -I -S <...>\jangseung\_hook.py hook-run`: one process.
  - When the package is installed in a virtual environment, `_hook.py` sets `sys.prefix` to that environment, as starting its own `python.exe` does. Commands that change files in the environment are therefore still judged as touching the guard's own runtime folder.
  - When the package is not in the environment's `Lib\site-packages` (an editable install, for one), when Python is a Microsoft Store alias, or when the program is not named `python*.exe`, install registers `aeg.exe` as before.
  - The Codex hook and macOS and Linux registrations are unchanged. Codex switches off a hook whose command changed until it is approved again in `/hooks`.
- **No site-packages (`-S`, about 3 ms).** The plugin and the new registration start Python with `-S`. Site-packages and `.pth` files are not processed; only the folder holding the Jangseung package is added, after the standard library.
- **The process ends once the answer is out (about 3 ms).** `hook-run` and `session-check` flush their output and leave with `os._exit`, skipping the interpreter's teardown of every module and object. The hook path leaves no open file, thread or exit handler. If standard output cannot be flushed, `hook-run` exits with 2 (block); before, Python exited with 120.

Loading modules:

- **Compiled modules are read from one file (about 10–16 ms on Windows).** Python opens one compiled file under `__pycache__` for each module. On Windows with real-time virus scanning, opening a file costs about 0.3 ms, and the hook loads about 60 modules, the standard library's included. A hook process now keeps the compiled forms it loaded in one file, `__pycache__/hook-run-imports.<version>.bin` in the package folder, and from the next call opens only that file. The session-start check keeps its own file (`session-check-imports.<version>.bin`).
  - It is used on Windows only. On Linux (WSL Ubuntu, Python 3.14.4) opening a file is cheap and the cache made no difference (20.5 ms without, 20.7 ms with), so macOS and Linux keep Python's own importing.
  - Only where the bytes are read from changes. Python still finds each module through the same paths in the same order. A cached form is used only when its header's modification time and size match the source file, and Python checks it again exactly as it checks a `__pycache__` file. Otherwise the `__pycache__` file is read, or the source compiled again, and the cache file is rewritten when the call ends.
  - It is turned on only in a process started to run a hook command (`hook-run`, `session-check`). Code that imports the package is not affected. Whatever fails in the cache, normal importing carries on.
  - When Python is set not to write compiled files (`-B`, `PYTHONDONTWRITEBYTECODE`), the cache file is not written either; an existing one is still read. The new registration, `python -I -m` and the plugin start with `-I`, which ignores that variable, so they always write it. Claude Code 2.1.316's CLI did not pass `PYTHONDONTWRITEBYTECODE` to hooks.
  - If the package folder cannot be written, no cache file appears and everything works as before.
  - Hash-based compiled files (installed with `SOURCE_DATE_EPOCH` set, for one) are not cached; they are always read from `__pycache__`.
  - The cache file carries a checksum. A damaged file, one larger than 8 MB, or one written by another Python is ignored and written again. Under `-O` a separately named file (`.opt-1`) is used.
  - A form that matches its source is still read from the cache after its `__pycache__` file is deleted. To force everything to compile again, delete the package's `__pycache__` folder; the cache file is in it.
  - Like the `__pycache__` files beside it, the cache file holds code. Jangseung protects its whole package folder as part of its runtime, so agent commands cannot write to it either.
  - `pip uninstall` does not remove the cache file, because it is not in the install record. The `jangseung` folder left behind can be deleted.
- **Nothing else is loaded before the cache is on.** `jangseung.cli.entry` no longer imports `json` or `__future__`, and the plugin launcher no longer uses `pathlib`. With the new registration and the plugin, the only modules read from disk before the cache starts are four of the package's own. `aeg.exe` gains less, because the script pip writes for it imports `re` first.
- **No `dataclasses` (about 25 ms).** `@dataclass` generates code for each class and compiles it with `exec`, and importing it also loads `inspect`. For the 34 classes the hook uses, that was about 25 ms. The hook path now uses `jangseung.records`, which gives the same behavior without generating code. Uses it does not support (inheritance, `ClassVar`, other options) raise an error instead of quietly behaving differently.
- **OpenSSL is not loaded (about 4 ms).** SHA-256 comes from Python's built-in module. The results are the same.
- **Loaded only when needed (about 3.5 ms).** `typing` is read only by type checkers. The one-time-allow and MCP modules and `datetime` load only for the calls that use them. Record times are written with `time`, in the same text `datetime` gave.

Judging and recording:

- **Each path is resolved once per judgment (about 2 ms on Windows).** One judgment resolved a few paths, such as the project root and the guard's own folders, 35 times. On Windows each resolution opens the file, about 0.1 ms. Within one judgment the same path is now resolved once and the answer reused. A judgment changes no files, so the answer is the same. The memory ends with the judgment and never carries over to another call. A failed resolution is not remembered.
- **File-name patterns are matched without regular expressions (about 3 ms).** The roughly 90 patterns in the built-in protection lists were compiled to regular expressions in every process. They are now matched with string comparisons that give the same answers. A test checks every pattern against `fnmatchcase`.
- **The end of the ledger is not read again (about 4–6 ms on Windows).** Each record used to read the previous record to continue the chain. Opening a file that has just changed for reading makes Windows virus scanning check it first, about 4 ms. Now, after writing, the last record's number and hash and the ledger's size and modification time go into the name of an empty file, `.aeg/hook_ledger.head.*`. The next call checks only that name and the size and time, without opening the ledger. If anything differs (another version wrote, a repair, an archive, a torn record), it reads and checks as before.
- **Input is read 64 KiB at a time (about 3 ms on Windows).** Asking for the whole input limit (16 MiB) in one read made Windows prepare a 16 MiB buffer, about 3 ms on every call. The input is now read in pieces up to the same limit. The bytes received, and the handling of input over the limit, are the same.
- **Input decoding (about 1.7 ms).** The BOM is removed directly and the input decoded as UTF-8, with the same result as `utf-8-sig`.
- **The plugin starts Python once.** 0.3.0 ran `python3` a second time to check its version, and when `python3` was the Microsoft Store stub that check alone took about 110 ms. Now the shell picks a `python3` from PATH that is not in `WindowsApps` (otherwise `python`), and the launcher checks the version. On a Python older than 3.10 the launcher exits with status 97 before reading input, and the shell hands the same input to `python`. This is the same fallback order as 0.3.0.

## What did not change

- **Decisions.**
  - 24,814 calls built from 3,818 strings in the test files (Bash, PowerShell, Read, Edit, Write, four modes) were judged by 0.3.0 and 0.3.1 in a project without a policy and in one with a policy. All 49,628 matched, including the output, exit code, reason codes, recorded fields and input hash.
  - Real hook processes were compared too. 1,241 of those calls were each run through PyPI 0.3.0's `aeg.exe`, the new registration judging per call, the new registration with the resident process, the plugin launcher with the resident process, and the new `aeg.exe`. Exit codes, standard output and standard error all matched, and each left 1,241 records. Before that, 414 calls compared the module cache on and off.
- **The Codex hook and the macOS and Linux registration forms.**
- **Python start-up.** Of a call answered by the resident process, about 33 ms, about 23 ms is Python's own start-up (measured at the same time), about 2 ms loads Jangseung's four modules in the hook, and about 6 ms is the resident process judging and recording. The gap to native tools is the difference in program start (about 14 ms against 23 ms) plus the judgment.

## New residual risks

- **RR-16:** because the end of the ledger is taken from the marker file's name, an edit that changes bytes and puts the modification time back is not caught at the moment of recording. `aeg evidence verify-hooks` reports it as a broken chain. The agent cannot write to `.aeg/`, and tampering that recomputed hashes was not caught at recording time before either.
- **RR-17:** code running with the same user's rights can impersonate the resident judging process, by reading or replacing its key file. With those rights it can already change Jangseung's code or settings. Other users cannot open the pipe, and the hook sends nothing to a server that cannot prove it holds the key.
- **RR-18:** if the resident process proves itself but does not answer within 10 seconds, the hook judges the call directly. Should the resident process finish its judgment meanwhile, that call has two records. A judgment waits at most 1 second for the ledger lock, so this does not happen in normal operation.

They are recorded in the [residual risk register](residual_risk.en.md).

## Check results

- Automated tests: 1939 passed, 20 skipped on Windows, Python 3.14. The new tests are in `tests/test_hook_speed_0_3_1.py`, `tests/test_hook_speed_0_3_1_start.py`, `tests/test_hook_import_cache.py` and `tests/test_resident.py`.
  - Resident judging, started and answering through real hook processes:
    - The answer is byte for byte the direct one for many tool calls in three modes, invalid input, a BOM, a subfolder as working folder, `CDPATH`, `--ensure-state`, Codex, an unknown option and deeply nested input.
    - Changed code or a new package folder makes it stop without answering.
    - A pipe whose server lacks the key receives nothing but the challenge, and is replaced by a new process.
    - A hung process costs about 1 second before the call is judged directly and a new one is started.
    - A left-over key whose process number now belongs to another process is corrected at session start.
    - Also checked: the off switch, hooks started without a launcher, parallel calls with the ledger chain, not holding the project folder, answering nothing but `hook-run`, and stopping when idle.
  - An independent review found six defects in resident judging, all fixed: call contents leaking to a pipe without the key, a hung process making every call wait 15 seconds, other users' read-only connections holding it up, the pipe-name check, detection of new package folders, and a recursion-depth difference.
  - One builds a real virtual environment and checks that the `aeg.exe`-style start and the new registration give the same `sys.prefix` and decisions.
  - Module cache, with real hook processes: the cache is written once and read on the next call; an edited source runs; a damaged cache is ignored and rewritten; nothing is written under `-B`; a mismatched entry falls back to the `__pycache__` file; no cache, writing and reading give the same answers. Also: hash-based compiled files do not make the cache be rewritten on every call; the checksum catches a damaged entry and the file is written again; an oversized file is ignored; `-O` uses its own file.
- Decision comparison: 0 differences over the 49,628 calls and the 1,241 process calls (five ways of running) above.
- Real sessions (Claude Code 2.1.316 `claude -p`, Windows, default mode, once each), both loaded as a plugin and with the new form registered by `aeg install`. Both behaved the same, and in both the hook processes created the module cache file and started the resident judging process:
  - `ls -la; pwd` and three calls in a row: ran. The record count matched the marker's number, and the chain verified.
  - `cat .env && pwd`: blocked.
  - `git add -A && git commit -m wip`: the host asked for approval.
  - Editing `CLAUDE.md`: asked, and with no person to approve, the file did not change.
  - Damaged policy file: the session-start warning appeared. A healthy project showed no warning.
- Not checked:
  - Real sessions on macOS and Linux. CI's Linux and macOS tests include a test that runs the plugin line with bash.
  - Real Codex sessions.
  - The fallback path on an actually old Python (3.9 or earlier). Only a simulation test that swaps in the version was run.
  - The new registration with pipx, uv, conda or Microsoft Store Python installs. Only the selection rules were tested.
  - Timing outside Windows. Without virus scanning, the ledger, path-resolution and module-cache gains are small.
  - The module cache on Python 3.10–3.13 locally. The importlib internals it uses exist from 3.10, but on this PC it ran on 3.14 only. CI runs the same tests on 3.10–3.14.
  - Whether the Claude Code desktop app passes `PYTHONDONTWRITEBYTECODE` to hooks. If it does, an `aeg.exe` registration cannot write the cache file and only reads one another form wrote.
  - Resident judging: opening or squatting the pipe from another Windows account was simulated with the same account, not tried with a real second account. Sharing one resident process between an elevated session and a normal one was not checked. Two records for a judgment longer than 10 seconds (RR-18) was not reproduced in a test.
