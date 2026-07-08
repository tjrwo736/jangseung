# Aegis Phase 11-D Hook Absolute-Path Normalization Fix v0

## Problem (found in live Claude Code testing)

Claude Code sends `tool_input.file_path` as an **absolute** path
(`/tmp/.../repo/README.md`). The Aegis judgment engine treats absolute paths
as out-of-scope (`SCOPE_LIMIT_REJECTED`, and the tool-call mapping's
absolute-path deny-candidate rule), so normal `Read`/`Write`/`Edit` of
in-repo files were denied. Direct stdin tests had used relative paths
(`README.md`) and therefore passed, hiding the mismatch. Result: attaching the
hook to a real Claude Code session blocked ordinary safe work.

## Fix

A normalization layer was added at the hook boundary, **before** the input
reaches the judgment engine, in
`src/evidence/hook_judgment_engine_alignment.py`
(`_normalize_hook_input_repo_paths` / `_normalize_repo_internal_absolute_path`,
called at the top of `judge_pretooluse_with_aeg_engine`):

```text
non-absolute path              -> unchanged (relative behaviour preserved, incl. relative traversal denial)
Windows-style absolute path    -> unchanged (mapping's absolute deny-candidate rejects it)
POSIX absolute path:
  resolve via the existing resolve_repo_boundary_path helper (absorbs .. and symlinks)
  if resolved target is under repo root -> rewrite to repo-relative, judge normally
  if resolved target is outside repo    -> keep absolute, existing scope defense rejects it
  on any resolution/relativize error    -> keep absolute (fail-closed)
```

Key point: this only rewrites the **input path the engine sees**. It does not
change any engine logic (`is_protected_path`, `classify_task`, `apply_law`,
`evaluate_action_capabilities`, the `.aeg` guard, or the repo-boundary gate are
all unmodified). Repo-internal absolute paths become the repo-relative form the
engine already judges correctly; everything outside the repo stays absolute and
stays rejected.

The repo boundary is computed with `resolve_repo_boundary_path`, which uses
component-wise `Path.relative_to` (not string-prefix matching) on
`.resolve(strict=False)`-canonicalized paths, so `..`, `.`, and symlinks are
absorbed and a sibling directory that merely shares the repo-name prefix
(`/tmp/x/repo-evil` vs `/tmp/x/repo`) is correctly treated as outside.

## Before / After (isolated temp repo, absolute paths as Claude Code sends them)

| tool call (absolute file_path) | before | after |
|---|---|---|
| Read `<repo>/README.md` (internal normal) | deny | **allow** |
| Write `<repo>/src/app.py` (internal normal) | deny | **ask** |
| Edit `<repo>/README.md` (internal normal) | deny | **ask/allow** |
| Read `<repo>/docs/guide.md` (internal docs) | deny | **allow** |
| Write `<repo>/.env` (internal protected) | deny | deny (unchanged) |
| Write `<repo>/.github/workflows/ci.yml` (internal protected) | deny | deny (unchanged) |
| Write `<repo>/.aeg/x` (internal protected) | deny | deny (unchanged) |
| Read `/etc/passwd` (outside) | deny | deny (unchanged) |
| Read `/root/.ssh/id_rsa` (outside) | deny | deny (unchanged) |
| Write `<repo>/../outside.txt` (traversal out) | deny | deny (unchanged) |
| Write `/tmp/other/x` (outside) | deny | deny (unchanged) |
| relative `README.md` | allow | allow (unchanged) |
| relative `../outside.txt` | deny | deny (unchanged) |

### Adversarial scope-bypass vectors (all remain deny)

```text
sibling prefix directory  /tmp/x/repo-evil/secret.txt   -> deny  (not treated as under /tmp/x/repo)
symlink inside repo -> /etc/passwd                       -> deny  (resolve follows the symlink outside)
symlink inside repo -> sibling/secret.txt                -> deny
deep traversal  <repo>/../../../../etc/passwd            -> deny
internal middle-dotdot  <repo>/src/../README.md          -> allow (correctly resolved to inside)
```

"repo-internal normal absolute passes" and "repo-external absolute still
denied" hold simultaneously; no out-of-repo path was observed to pass.

## Invariants Preserved

```text
judgment engine logic unchanged (classify/law/capability/is_protected_path/aeg-guard/repo-boundary)
fail-closed: normalization error / ambiguous path keeps the path absolute -> rejected (never allow)
hook input still treated as untrusted raw executor output
store sink seal, propose-only self-execution policy: untouched
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
no .claude/settings.json modification, no hook install, no Claude Code execution,
  no provider/network, no store write, no filesystem mutation (module + tests + doc only)
```

## Not Claimed

```text
CLAUDE_CODE_HOOK_INSTALLED = NOT_CLAIMED
LIVE_HOOK_READY = NOT_CLAIMED
BYPASS_IMPOSSIBLE = NOT_CLAIMED
TAMPER_PROOF = NOT_CLAIMED
```

The reproduction was run by piping JSON (with absolute paths) into
`aeg hook-run` on stdin. This closes the absolute-path mismatch that live
Claude Code exposed; the separately gated actual-install / live-run phase is
still not performed here.

Main merge:

```text
main merge = NOT_PERFORMED
```
