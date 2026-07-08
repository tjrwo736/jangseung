# Aegis Phase 11-D-2 aeg hook-run stdin/stdout/exit-code Wiring v0

## Purpose

This phase builds the real I/O boundary — an `aeg hook-run` CLI subcommand —
that lets the existing in-memory Aegis judgment brain (Phase 11-C-8
`judge_pretooluse_with_aeg_engine`) act as a Claude Code PreToolUse hook
command: it reads untrusted PreToolUse JSON from **stdin**, routes it through
the unchanged judgment brain, and writes a Claude Code
`hookSpecificOutput.permissionDecision` response to **stdout** with a
spec-aligned **exit code**.

This is the "mouth and hands" (I/O), not new judgment. The judgment brain is
not modified.

Completion label:

```text
PHASE11D_2_AEG_HOOK_RUN_STDIN_STDOUT_WIRING_COMPLETE_NOT_INSTALLED_NOT_LIVE
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## What Was Actually Done vs Not Done

Done (verified by direct stdin subprocess tests):

```text
added an "aeg hook-run" CLI subcommand (src/cli/hook_run.py, wired in src/cli/main.py)
real stdin read + stdout write + exit code: the 11-D-1 diagnostic now reports
  entrypoint_stdin_stdout_exit_wired = True and hook_run_subcommand_exists = True
fed JSON directly into "aeg hook-run" via stdin and observed the permissionDecision
  on stdout and the process exit code
```

Not done (this phase is wiring, not installation or live use):

```text
settings_json_modified = False        (no .claude/settings.json written)
hook_installed = False
claude_code_execution_performed = False   (tested by piping stdin directly, NOT by running Claude Code)
tool_execution_performed = False
provider_model_network = none
store_write_performed = False
filesystem_mutation_by_hook_run = False
```

Honest scope line: **"piping JSON into `aeg hook-run` on stdin produces the
right permissionDecision on stdout with the right exit code" is verified.
"Claude Code itself invokes this hook" is not — that is a later phase
(actual install requires the 11-D-0 user gate).**

## Flow

```text
stdin (Claude Code PreToolUse JSON: tool_name, tool_input, tool_use_id, ...)
  -> json.loads (fail-closed on parse error)
  -> validate_claude_code_pretooluse_input (fail-closed on invalid/missing/unsupported)
  -> judge_pretooluse_with_aeg_engine  (UNCHANGED 11-C-8 brain)
  -> map hook_decision -> permissionDecision + exit code
  -> stdout: {"hookSpecificOutput": {"hookEventName": "PreToolUse",
              "permissionDecision": "...", "permissionDecisionReason": "..."}}
  -> exit code (0 allow/ask, 2 deny)
```

## Untrusted Input (Safety Boundary A)

stdin JSON is treated as untrusted raw executor output even though Claude Code
produced it. It is never trusted as a decision or authority; it always passes
through validate → map → judge. Malformed JSON, wrong top-level type, missing
or wrong-typed fields, and unsupported tool names are all handled without
trusting the input.

## Fail-Closed (Safety Boundary B — the core property)

Every failure or uncertainty resolves to a non-`allow` decision. There is no
code path where a failure resolves to `allow`.

Decision mapping (from the unchanged brain's four outcomes):

```text
brain allow  -> permissionDecision "allow", exit 0   (only for genuinely safe reads)
brain ask    -> permissionDecision "ask",   exit 0   (normal Write/Edit: user confirms)
brain deny   -> permissionDecision "deny",  exit 2   (protected path / dangerous Bash)
brain defer  -> permissionDecision "ask",   exit 0   (valid input, uncertain risk: user decides)
```

Wiring-level failures (which never produced a trustworthy judgment) hard-deny:

```text
invalid / empty / non-object JSON stdin      -> deny, exit 2
invalid / missing-field / unsupported-tool   -> deny, exit 2 (before path judgment)
internal exception anywhere                  -> deny, exit 2
unmapped brain decision                      -> deny, exit 2
```

`defer` maps to `ask` (not a hard block) because the brain only returns
`defer` for VALID input whose risk is merely uncertain (e.g. a medium-risk
read, an unclassified but non-dangerous command); dangerous input always
returns `deny`, never `defer`. INVALID input is hard-denied at the wiring
layer before it can reach the brain and collapse to `defer` — this closes an
input-downgrade gap (e.g. a `.env` write with a missing `tool_use_id` must not
become `ask` by skipping path judgment).

### Measured fail-closed results (direct stdin, no Claude Code)

```text
Write .env / .github/workflows / .aeg/x / Dockerfile / pyproject.toml / src/law/x.py -> deny, exit 2
Bash rm -rf / , git reset --hard , git clean -fd                                     -> deny, exit 2
Write .env with missing tool_use_id                                                  -> deny, exit 2
invalid JSON / empty stdin / whitespace / array / string / number / null            -> deny, exit 2
missing fields / unknown tool / null tool_input / non-string tool_name              -> deny, exit 2
Write src/app.py , Edit app.py (normal)                                              -> ask,  exit 0
Read app.py (normal)                                                                 -> ask,  exit 0
Read docs/guide.md (safe docs read)                                                  -> allow, exit 0
Bash "ls -la" (unclassified, non-dangerous)                                          -> ask,  exit 0
```

Not one failure or dangerous case yields `allow`. The only `allow` observed is
a documentation-file read, which is the brain's intended safe-read path
(LIMITED read capability + CLEAN_CORE law), not a fail-open leak.

## stdout permissionDecision Format (Safety Boundary C)

The stdout payload is the documented Claude Code PreToolUse
`hookSpecificOutput` shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "aegis_pretooluse permissionDecision=deny; ..."
  }
}
```

`permissionDecision` is one of `allow` / `deny` / `ask` (the Claude Code
PreToolUse values). The reason string carries only decision codes and the tool
name; raw `tool_input` is never included, so secrets in tool input are not
echoed to stdout or stderr (verified by test).

## Exit Code (Safety Boundary D)

```text
allow / ask -> exit 0 (decision carried in the stdout JSON)
deny        -> exit 2 (Claude Code blocking exit code) AND the reason on stderr
               AND the deny JSON on stdout
```

For `deny`, both the exit-code blocking mechanism (exit 2 + stderr reason) and
the JSON `permissionDecision "deny"` are emitted, so the tool call is blocked
even if one mechanism were ignored (belt-and-suspenders fail-closed). Verified
end-to-end via an actual subprocess (`python -m src.cli hook-run` with piped
stdin): dangerous input returns exit code 2, normal input returns exit code 0.

## Judgment Brain Unchanged (Safety Boundary E)

```text
judgment_brain_source = src.evidence.hook_judgment_engine_alignment.judge_pretooluse_with_aeg_engine
judgment_brain_modified = False
```

No change was made to the judgment engine, the capability policy, the store
sink seal, or the input contract. Aegis's own propose-only self-execution
policy is untouched; `live_executor_authority` remains
`LIVE_EXECUTOR_AUTHORITY_ON_HOLD`; the safe default remains
`hold_current_state`. This phase only added the I/O layer around the brain.

## Non-Goals of Phase 11-D-2

```text
.claude/settings.json modification (project or global)
actual hook installation
actual Claude Code execution (input was piped to stdin directly, not produced by Claude Code)
real hook response emission by an installed hook
tool execution
provider/model/network implementation or calls
API key/env/secret loading
.aeg/ store write
runtime filesystem mutation (other than the new module, tests, and this document)
global or user-local install
public release material
direct push to main
```

## Forbidden Overclaims Not Made By This Document

```text
CLAUDE_CODE_HOOK_INSTALLED = NOT_CLAIMED
INSTALLED = NOT_CLAIMED
LIVE_HOOK_READY = NOT_CLAIMED
CLAUDE_CODE_EXECUTION_PERFORMED = NOT_CLAIMED
REAL_HOOK_RESPONSE_EMITTED_BY_CLAUDE_CODE = NOT_CLAIMED
TOOL_EXECUTION_READY = NOT_CLAIMED
WRITE_AUTHORITY_GRANTED = NOT_CLAIMED
BYPASS_IMPOSSIBLE = NOT_CLAIMED
TAMPER_PROOF = NOT_CLAIMED
```

What is claimed, precisely: the stdin/stdout/exit-code wiring exists and, when
fed JSON directly on stdin, produces a correct, fail-closed Claude Code
permissionDecision with a correct exit code. Whether Claude Code actually
invokes it is a later, separately gated phase.

## 11-D Sequence Status

```text
11-D-0 Entry Gate = merged
11-D-1 Hook Install Dry-Run / Settings Candidate = merged
11-D-2 aeg hook-run stdin/stdout/exit-code wiring = this document
11-D-3 Disposable-Repo Actual Install + Live PreToolUse Reproduction (explicit user gate) = NOT_STARTED
11-D-4 Live Hook Response Emission Verification = NOT_STARTED
11-D-5 Phase 11-D Completion Baseline (not public release) = NOT_STARTED
```

## Transition Recommendation

```text
hold current state
the wiring the 11-D-1 diagnostic found missing now exists and is fail-closed under direct stdin tests
do not modify .claude/settings.json or run Claude Code against this hook without the 11-D-0 user gate
keep live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD and safe default = hold_current_state
```

Main merge:

```text
main merge = NOT_PERFORMED
```
