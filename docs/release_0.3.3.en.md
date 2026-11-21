# Jangseung 0.3.3 — four fixes to the personal approval storage of 0.3.2

[한국어](release_0.3.3.md)

Fixes defects that came with moving personal approvals into the user's profile in 0.3.2. Decision rules did not change.

```bash
python -m pip install --upgrade jangseung==0.3.3
```

If you use the plugin, update the plugin too. There is no need to run `aeg install` again.

## What was fixed

- **Hooks that judge per call were about 13 ms slower in 0.3.2.** Finding the profile folder loaded `ctypes` and the shell library on every call. It is now read from the registry where Windows records each profile's folder (`HKLM`, which only administrators can change). Environment variables are still not trusted. When more or fewer than one user hive is open to the process (as an administrator, for one), the shell is asked as before.
  - Medians of 160 alternating runs on one PC: 0.3.1 52.2 ms, 0.3.2 65.5 ms, 0.3.3 54.0 ms. Calls answered by the resident process were not affected in 0.3.2 either (34.5 ms against 34.7 ms).
- **Approvals were not found across Python versions (Windows).** The folder approvals are kept under had `st_dev` in its name. Python 3.12 and later report a 64-bit volume serial there; 3.11 and earlier report its low 32 bits. Approvals did not apply when `aeg policy add` and the hook ran on different Pythons, or after moving to Python 3.12 or later. Only the bits every version reports are used now.
  - A folder 0.3.2 created under Python 3.12 or later is still read, and moves to the new name the next time an approval is written. Nothing needs approving again.
- **A profile folder that could not be used blocked every file edit.** That included users with no personal policy: a profile folder that is a link or junction, a container without a user entry, a group-writable home folder. `aeg policy add` does not write to such a place either, so nothing a person approved can be there. It now means "no personal approvals". The built-in rules, the team policy and the checkout's `protect_paths` still apply, and the session-start check and `aeg doctor --hooks` report it.
  - Unchanged: a project that holds the approval storage, or sits inside it, still has every path protected. So does storage whose own folders or files are links or damaged.
- **Old grants were ignored without a word.** `allow_paths`, `allow_commands` and `allow_mcp_tools` left in `.aeg/policy.json` have not been used since 0.3.2. When entries that were not adopted remain, the session start now says so in one line and `aeg doctor --hooks` gives a WARN. Review and adopt them with `aeg policy adopt`, or remove them from that file, and the note goes away.

## Check results

- Automated tests: 1990 passed, 21 skipped on Windows, Python 3.14. The new tests are in `tests/test_approval_storage_0_3_3.py`.
- Approval folder name: Python 3.10.20 and 3.14.5 gave the same name for the same project (they differed in 0.3.2).
- Profile path: on this PC the registry and the shell gave the same folder (0.24 ms).
- Answers of 0.3.1, 0.3.2 and 0.3.3: the same for four commands.
- Not checked: an elevated session (falls back to asking the shell), profiles of domain and Azure AD accounts, real macOS sessions, a real container without a user entry (only simulated in a test).
