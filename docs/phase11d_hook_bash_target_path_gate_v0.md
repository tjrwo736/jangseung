# Aegis Phase 11-D Hook Bash Write/Delete Target-Path Gate v0

## Problem (found in live Claude Code testing)

Claude Code often creates or overwrites files with a **Bash** command
(`echo "KEY=x" > .env`) rather than the Write tool. Aegis denied `.env` via the
Write tool but classified Bash as "not proven safe → ask", so a `.env` write
via Bash slipped to `ask` instead of `deny` — the most common dangerous path
was not blocked.

## Fix

A Bash command's file **write/delete target paths** are now parsed structurally
and, if a target is a protected path or outside the repo, the command is denied.

### Structural parsing, not string matching (bypass-resistant)

`extract_bash_write_delete_targets` (in `claude_code_tool_call_mapping.py`) uses
`shlex` to tokenize the command (case-preserving) and extracts write/delete
targets from: output redirection (`>`, `>>`, and `&>`/`1>`/`2>` variants — fd
duplications like `2>&1` are ignored), `tee`, `cp`/`mv`/`install` (destination),
`rm`, `dd of=`, `truncate`, `ln`. Because `shlex` resolves quoting, obfuscation
like `echo x > .en"v"` is normalized to the real target `.env` and caught —
string matching on the raw command would miss it.

The extracted target is then judged by the existing engine in the hook
(`_bash_write_delete_target_gate` in `hook_judgment_engine_alignment.py`): each
target is resolved with `resolve_repo_boundary_path` and checked with the
existing `is_protected_path` and `.aeg` integrity guard — the same policy used
for Write/Edit paths. No new protected-path list was invented.

### Fail-closed on unparseable commands (no "pretend to block")

A command is reported **ambiguous** (no target claimed) when it uses variable
or command or process substitution (`$VAR`, `$(...)`, `` `...` ``, `<(...)`),
a nested shell (`bash -c`, `sh -c`, `eval`, `exec`, ...), or `xargs`/`find
-exec`/`-delete`. In that case the command is **not** denied on target grounds
and is **not** promoted to allow — it stays on the existing `ask/defer` path.
This is recorded honestly in the reason code
(`bash_target_unparseable_maps_to_ask_defer_not_allow_not_falsely_denied:...`).

**This does not claim to block all dangerous Bash.** It blocks Bash whose
write/delete target is *structurally* a protected/out-of-repo path. Obfuscated
or dynamically-constructed targets are not precisely judged — they resolve to
`ask` (never `allow`), not a false `deny`.

## Isolated reproduction (cwd = temp repo; Bash targets relative to cwd)

| Bash command | before | after |
|---|---|---|
| `echo "KEY=x" > .env` | ask | **deny** |
| `echo x >> .env` | ask | **deny** |
| `echo x \| tee .env` | ask | **deny** |
| `cp src/app.py .env` / `mv src/app.py .env` | ask | **deny** |
| `rm .env` | ask | **deny** |
| `rm -rf .aeg` | deny | deny (unchanged) |
| `echo x > .github/workflows/ci.yml` | ask | **deny** |
| `dd of=.env if=/dev/zero` | ask | **deny** |
| `echo x > .en"v"` (quote-split obfuscation) | ask | **deny** (shlex resolves it) |
| `echo x > /tmp/other/.env` (out of repo) | ask | **deny** (scope) |
| `echo x > /etc/cron.d/x` (out of repo) | ask | **deny** (scope) |
| `echo x > src/app.py` (normal in-repo) | ask | ask (unchanged, not a protected target) |
| `pwd` / `ls` / `git status` / `cat README.md` / `grep` | ask | ask (no false positive) |
| `bash -c 'echo x > .env'` (nested shell) | ask | **ask** (ambiguous → not allow, not falsely denied) |
| `E=.env; echo x > $E` (variable) | ask | **ask** |
| `echo x > $(echo .env)` / `` `...` `` (substitution) | ask | **ask** |
| `rm -rf /` / `git reset --hard` / `git clean -fd` / `sudo ...` | deny | deny (unchanged) |

"clear protected/out-of-repo write/delete → deny", "safe Bash → ask (no false
positive)", "bypass/complex → ask (never allow, never falsely denied)" hold
simultaneously. No bypass case reaches `allow`.

## Unchanged

```text
Write/Edit path judgment (already denies protected paths)
existing dangerous-command detection (rm -rf, git reset --hard, git clean -fd, sudo, ...)
absolute-path normalization (#116), clearly-safe normal allow (#117)
engine logic (classify/law/capability/is_protected_path/aeg-guard/repo-boundary)
store sink seal, propose-only policy, live_executor_authority = ON_HOLD
fail-closed: unparseable / ambiguous -> ask/defer, never allow
Bash never reaches allow (RUN_COMMAND is excluded from the clearly-safe allow set)
```

## Not Claimed

```text
"blocks all dangerous Bash" = NOT_CLAIMED
obfuscated/dynamic Bash targets are precisely judged = NOT_CLAIMED (they map to ask, honestly)
BYPASS_IMPOSSIBLE / TAMPER_PROOF = NOT_CLAIMED
```

Main merge:

```text
main merge = NOT_PERFORMED
```
