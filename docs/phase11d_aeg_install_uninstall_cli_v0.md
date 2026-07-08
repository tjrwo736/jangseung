# Aegis Phase 11-D aeg install / uninstall CLI v0

## Purpose

Make Aegis deployable: instead of `git clone` + hand-writing
`.claude/settings.json`, a user runs `pip install` then `aeg install` to
register the Aegis PreToolUse hook, and `aeg uninstall` to remove it. CLI
subcommands are now `{init, doctor, run, verify, hook-run, install, uninstall}`.

## What was done

```text
added `aeg install` and `aeg uninstall` (src/cli/install.py, wired in src/cli/main.py)
project-local only: writes ./.claude/settings.json; --global is explicitly unsupported (rc 2 + message)
merge, not overwrite: preserves every other hook and every other field; adds/removes only the Aegis hook
diff preview + y/N confirmation before any write (--yes to skip); default is to prompt
backs up an existing settings.json to settings.json.aegis-backup-<timestamp> before writing
aborts without writing on invalid JSON or an unexpected settings structure
idempotent install ("already installed"); uninstall with no Aegis hook exits quietly
generated hook command resolves the installed `aeg` (or `{sys.executable} -m src.cli`) so no PYTHONPATH is needed
pyproject.toml: version 0.1.0; console_scripts entry `aeg = src.cli:main` (already present) verified installable
```

## What was NOT done (honest scope)

```text
no PyPI / public release (verified only: local `pip install -e .` and `pip install .`)
no global (~/.claude) install
no automatic install without user confirmation (prompt is the default)
does not run Claude Code for the user
does not change the judgment engine, store seal, propose-only policy, or live_executor_authority (still ON_HOLD)
```

## Aegis hook identity

An Aegis hook is identified by its command containing `hook-run` and referencing
this package (`aeg` or `src.cli`). Install/uninstall/duplicate-detection all key
off this, so a user's own hooks are never matched, added-over, or removed.

## Measured reproduction (isolated temp dirs)

Install:

```text
no settings.json           -> new .claude/settings.json created with the Aegis PreToolUse entry
existing settings + other hook + model/env fields -> Aegis entry appended; my-own-hook.sh, PostToolUse, model, env all preserved; backup written
run install again          -> "already installed"; PreToolUse entry count stays 1 (no duplicate)
answer "n" at prompt       -> "cancelled"; no settings.json written
invalid JSON settings      -> "aborted"; rc 1; file left byte-identical
--global                   -> "not supported"; rc 2; nothing written
```

Uninstall:

```text
settings with user hook + Aegis hook -> only Aegis removed; my-own-hook.sh kept; backup written
no Aegis hook present               -> "nothing to remove"; file unchanged
```

Packaging + hook command:

```text
pip install -e .   -> `which aeg` = /usr/local/bin/aeg ; `aeg --help` lists install/uninstall
installed command  -> `echo '{"tool_name":"Write","tool_input":{"file_path":".env",...}}' | aeg hook-run` -> permissionDecision=deny, exit 2 (no PYTHONPATH needed)
                      `... "Read" README.md ...` -> permissionDecision=allow, exit 0
```

So the command `aeg install` writes into settings works end-to-end: the
registered `aeg hook-run` command runs and produces the correct fail-closed
decision without any manual environment setup.

## Not claimed

```text
PUBLIC_RELEASE / PYPI_PUBLISHED = NOT_CLAIMED
GLOBAL_INSTALL_SUPPORTED = NOT_CLAIMED
AUTO_INSTALL_WITHOUT_CONFIRMATION = NOT_CLAIMED (prompt is default)
```

Main merge:

```text
main merge = NOT_PERFORMED
```
