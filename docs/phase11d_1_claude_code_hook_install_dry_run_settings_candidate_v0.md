# Aegis Phase 11-D-1 Claude Code Hook Install Dry-Run / Settings Candidate v0

## Purpose

This phase builds and validates a `.claude/settings.json`-shaped candidate
for registering a Claude Code PreToolUse hook, and honestly diagnoses whether
the Aegis hook entrypoint currently performs the real stdin/stdout/exit-code
I/O a Claude Code hook command requires. This is a dry-run: it produces and
checks a candidate, it does not install anything.

This document does not claim actual installation, actual hook operation, or
actual live execution. It records exactly what was built and checked, and
exactly what was not done.

Completion label:

```text
PHASE11D_1_CLAUDE_CODE_HOOK_INSTALL_DRY_RUN_SETTINGS_CANDIDATE_COMPLETE_NOT_INSTALLED_NOT_LIVE
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## What This Phase Actually Did

```text
built an in-memory .claude/settings.json-shaped hook registration candidate
validated the candidate's structural shape against the documented PreToolUse hook contract
confirmed the candidate is project-local scoped, not user-global
diagnosed, by scanning source text under src/, whether any module performs real stdin/stdout/exit-code hook I/O
confirmed the aeg-hook-run command referenced by the candidate does not exist yet as a registered CLI subcommand
added one new source module, one new test module, and this document
```

## What This Phase Did Not Do

```text
settings_json_modified = False
settings_json_modified_global = False
hook_installed = False
claude_code_execution_performed = False
real_hook_response_emitted = False
stdout_stderr_hook_output_written = False
tool_execution_performed = False
filesystem_mutation_by_dry_run = False
```

No `.claude/settings.json` (project or global) was created, read, or
modified. No hook was installed. No Claude Code process was executed. No
tool was executed. No file was written outside this single new source
module, test module, and document.

## Settings Candidate

Source: `src/evidence/claude_code_hook_install_dry_run_candidate.py`,
`build_claude_code_settings_candidate()`.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|Bash|Read",
        "hooks": [
          {
            "type": "command",
            "command": "aeg hook-run"
          }
        ]
      }
    ]
  }
}
```

This candidate is not `.claude/settings.json` and is not
`.claude/settings.local.json`. It is an in-memory dict returned by a
function; nothing on disk was created or changed to produce it.

Candidate properties:

```text
hookEventName = "PreToolUse"
matcher = "Write|Edit|Bash|Read" (covers all four Phase 11-C target tools)
hook type = "command"
hook command = "aeg hook-run"
```

## Scope: Project-Local, Not Global

```text
settings_candidate_scope = project_local
settings_candidate_path_if_installed = .claude/settings.json
forbidden_global_settings_path = ~/.claude/settings.json
global_settings_path_referenced_by_candidate = False
```

The candidate targets the project-local settings path only. The user-global
settings path is recorded only as a forbidden reference point; the candidate
does not reference it, and no phase up to and including 11-D-1 writes to it.
A later phase's actual install step (11-D-2) must also merge into, not
overwrite, any pre-existing project-local `.claude/settings.json` content —
that merge behavior is out of scope here and is not implemented by this
dry-run.

## Structural Validation Result

Source: `validate_claude_code_settings_candidate()`.

```text
status = VALID_SETTINGS_CANDIDATE
matcher_covers_target_tools = True
command_references_aeg_entrypoint = True
reasons = ()
```

The validator checks, without performing any I/O: the `hooks.PreToolUse`
section exists and is non-empty; each entry has a non-empty `matcher`
covering `Write`, `Edit`, `Bash`, and `Read`; each entry has a non-empty
`hooks` list of `{"type": "command", "command": ...}` objects; and the
command references the Aegis entrypoint. Malformed candidates (missing
`hooks` section, a matcher missing a target tool, a non-`command` hook type,
or a command not referencing the Aegis entrypoint) are rejected with
specific reasons, verified by unit tests.

## Entrypoint stdin/stdout/exit-Code Wiring Diagnosis (Most Important Section)

This is the honest answer to whether the current Aegis hook code could
actually serve as a real Claude Code hook command today.

A real Claude Code PreToolUse hook command must, at minimum: read JSON from
stdin, write a `hookSpecificOutput`/`permissionDecision`-shaped JSON response
to stdout, and exit with a status code the substrate interprets. Source:
`diagnose_hook_entrypoint_stdin_stdout_wiring()`, which scans every `.py`
file under `src/` for real stdin/stdout/exit-code I/O tokens.

Diagnosis result:

```text
scanned_root = src/
stdin_stdout_exit_tokens_checked = (sys.stdin, sys.stdout, sys.stderr, sys.exit()
files_with_stdin_stdout_exit_io = ()
entrypoint_stdin_stdout_exit_wired = False
diagnosis = stdin_stdout_exit_wiring_not_present_anywhere_in_src_entrypoint_is_memory_candidate_only
hook_run_subcommand_exists = False
```

Plainly stated:

```text
The settings candidate shape is ready and validated.
The Aegis hook entrypoint chain (Phase 11-C-1 through 11-C-8, and the
  Phase 11-C runtime-readiness dry entrypoint) remains an in-memory
  candidate pipeline only. It does not read stdin, does not write stdout,
  and does not call exit with a hook status code, anywhere in src/.
The "aeg hook-run" command referenced by the settings candidate does not
  exist yet as a registered CLI subcommand of "aeg".
Therefore: copying this settings candidate into a real
  .claude/settings.json today, and having Claude Code invoke it, would fail
  or no-op, because there is nothing on the other end to read the hook
  input from stdin or write a permissionDecision to stdout.
Building that stdin/stdout/exit-code wiring (an "aeg hook-run" subcommand
  that reads stdin, calls judge_pretooluse_with_aeg_engine, and writes the
  serialized response to stdout) is required work for a later 11-D phase.
  It is not implemented by this dry-run.
```

## Non-Equivalences

```text
settings candidate != installed settings.json
structurally valid candidate != working hook
dry-run diagnosis != stdin/stdout wiring implemented
candidate references an entrypoint command != entrypoint command exists
project-local scope stated != any install performed
```

## Non-Goals of Phase 11-D-1

Phase 11-D-1 does not implement or authorize:

```text
.claude/settings.json modification (project or global)
hook installation
actual Claude Code execution
stdin/stdout/exit-code hook entrypoint implementation
real hook response emission
tool execution
provider/model/network implementation or calls
API key/env/secret loading
.aeg/ store write
runtime filesystem mutation (other than the new module, test, and this document)
global or user-local install of any kind
public release material
direct push to main
```

## Forbidden Overclaims Not Made By This Document

```text
HOOK_RUNTIME_READY = NOT_CLAIMED
LIVE_HOOK_READY = NOT_CLAIMED
CLAUDE_CODE_HOOK_INSTALLED = NOT_CLAIMED
INSTALLED = NOT_CLAIMED
REAL_HOOK_RESPONSE_EMITTED = NOT_CLAIMED
CLAUDE_CODE_EXECUTION_PERFORMED = NOT_CLAIMED
STDIN_STDOUT_WIRING_COMPLETE = NOT_CLAIMED
TOOL_EXECUTION_READY = NOT_CLAIMED
WRITE_AUTHORITY_GRANTED = NOT_CLAIMED
BYPASS_IMPOSSIBLE = NOT_CLAIMED
TAMPER_PROOF = NOT_CLAIMED
```

## 11-D Sequence Status

```text
11-D-0 Claude Code Local Installation / Live Hook Entry Gate = merged
11-D-1 Hook Install Dry-Run / Settings Candidate = this document
11-D-2 Disposable-Repo Actual Install (explicit user gate required) = NOT_STARTED
  (requires: an "aeg hook-run" subcommand implementing real stdin/stdout/exit
  wiring, built and tested before any actual settings.json write)
11-D-3 Live PreToolUse Reproduction = NOT_STARTED
11-D-4 Live Hook Response Emission Verification = NOT_STARTED
11-D-5 Phase 11-D Completion Baseline (not public release) = NOT_STARTED
```

## Transition Recommendation

```text
hold current state
do not modify .claude/settings.json (project or global) under Phase 11-D-1
do not attempt 11-D-2 without first implementing and testing the stdin/stdout/exit-code
  wiring this diagnosis found missing (an "aeg hook-run" subcommand)
do not attempt 11-D-2 without a separate, explicit user gate at that time
keep live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD and safe default =
  hold_current_state until a later phase explicitly and separately changes them
```

Main merge:

```text
main merge = NOT_PERFORMED
```
