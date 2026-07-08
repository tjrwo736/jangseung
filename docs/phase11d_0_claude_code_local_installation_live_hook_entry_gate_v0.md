# Aegis Phase 11-D-0 Claude Code Local Installation / Live Hook Entry Gate v0

## Purpose

This is a docs-only entry gate. It locks the safety conditions that must be
satisfied before any actual Claude Code local installation, actual hook
registration, or actual live PreToolUse execution is attempted.

This document does not install a hook, modify `.claude/settings.json`, execute
Claude Code, execute any tool, call a provider/model/network, write to
`.aeg/` state, or mutate any filesystem outside this single new markdown file.

Completion label:

```text
PHASE11D_0_CLAUDE_CODE_LOCAL_INSTALLATION_LIVE_HOOK_ENTRY_GATE_COMPLETE_NOT_INSTALLED_NOT_LIVE
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Accepted 11-C Baseline Summary

Phase 11-C is accepted as a runtime-readiness candidate baseline, not as a
live or installed system:

```text
Phase 11-C = COMPLETE_AS_CLAUDE_CODE_PRETOOLUSE_RUNTIME_READINESS_BUNDLE_NOT_INSTALLED_NOT_LIVE_RUNTIME
11-C-0 Hook Governance Direction Lock = merged
11-C-1 Claude Code PreToolUse Input Contract = merged
11-C-2 Tool Call to Structured Action Mapping = merged
11-C-3 Hook Decision Adapter = merged
11-C-4 Hook Evidence Binding = merged
11-C-5 Hook Evidence Verification Gate = merged
11-C-6 Hook Response Envelope Candidate = merged
11-C-7 Hook Response Serialization Candidate = merged
11-C-8 Hook Judgment Engine Alignment = merged
11-C runtime-readiness completion bundle = merged
hook input trust boundary = untrusted_raw_executor_output
protected-path judgment source = src.classify.is_protected_path (existing engine, not a hook-local duplicate)
capability judgment source = src.evidence.structured_action_capabilities.evaluate_action_capabilities
law/risk judgment source = src.classify.classify_task + src.law.apply_law
hook decision vocabulary = allow / deny / ask / defer
hook_command_implemented = False
hook_installation_implemented = False
claude_code_execution_performed = False
real_hook_response_emitted = False
```

This entry gate treats the 11-C engine-alignment baseline (11-C-8) as a
precondition, not as something re-opened here. Phase 11-D does not repeat or
re-litigate 11-C; it only gates the transition into actual local installation
and live execution.

## Why Actual Installation Must Be Gated Separately

The 11-C line produced a complete in-memory candidate pipeline: validated
hook-shaped input, tool-call-to-structured-action mapping, engine-aligned
judgment, evidence binding, verification, and response serialization. None of
that pipeline has ever touched a real filesystem hook registration, a real
Claude Code process, or real stdout/stderr hook output.

Actual installation is qualitatively different from candidate work because it:

```text
modifies a real .claude/settings.json (a user-environment configuration file)
causes a real external program (Claude Code) to invoke Aegis code on a schedule Aegis does not control
produces real stdout/stderr that a real substrate parses and acts on
can affect any project where the hook is installed, not just an in-memory fixture
is difficult to fully undo automatically if the install step is wrong
```

Because these effects reach outside the current in-memory/candidate boundary
and touch the user's actual environment, installation is deliberately split
into its own gated phase (11-D) rather than folded into 11-C.

## Required User Gates Before Actual Installation

None of the following are satisfied by this document. Each is a required gate
for a later 11-D phase, not a claim made here.

```text
1. explicit user gate required before any .claude/settings.json modification
2. project-local install only; user-global (~/.claude/settings.json) install is forbidden
3. first actual install attempt only in a disposable/throwaway repository, never a real/production project
4. backup of any pre-existing hook configuration is required before any modification, with a documented rollback step
5. no global install path (user-level or system-level) at any point in Phase 11-D
6. no public release material; public release remains a separate future gate outside Phase 11-D
7. a live Claude Code reproduction gate is required before any install claim is treated as verified
8. a stdout/stderr hook response schema verification gate is required (actual emitted bytes checked against the Claude Code hook response contract, not the candidate schema alone)
9. a dangerous-tool-call denial reproduction gate is required (an actual Claude Code session, in a disposable repo, must show a real dangerous tool call actually denied/deferred before this is called enforcement)
10. an uninstall/restore verification gate is required (removing the hook and confirming the disposable repo returns to its pre-install configuration)
```

## Non-Goals of Phase 11-D-0

Phase 11-D-0 does not implement or authorize:

```text
.claude/settings.json modification
hook installation
stdout/stderr live hook output emission
actual Claude Code execution
actual tool execution
provider/model/network implementation or calls
API key/env/secret loading
.aeg/ store write
runtime filesystem mutation (other than this single new document)
global or user-local install of any kind
public release material
direct push to main
```

Forbidden scope not implemented or claimed by this document:

```text
hook_command_implemented
hook_installation_implemented
claude_code_execution_performed
real_hook_response_emitted
tool_execution_performed
action_execution_engine_implemented
write_authority_granted
store_write_performed
public_release_performed
```

## 11-D Sequence

Proposed Phase 11-D sequence:

```text
11-D-0 Claude Code Local Installation / Live Hook Entry Gate (this document)
11-D-1 Install Dry-Run (no mutation; validates the install steps and rollback plan without touching any settings file)
11-D-2 Disposable-Repo Actual Install (explicit user gate required; project-local only; disposable repo only)
11-D-3 Live PreToolUse Reproduction (actual Claude Code session against the installed hook)
11-D-4 Live Hook Response Emission Verification (actual stdout/stderr bytes checked against the hook response contract)
11-D-5 Phase 11-D Completion Baseline (not public release)
```

Each future phase must preserve the safe default and `live_executor_authority
= LIVE_EXECUTOR_AUTHORITY_ON_HOLD` unless a later phase separately and
explicitly changes them through its own gate.

## 11-C Boundary Preservation Check

This entry gate confirms the following 11-C boundaries are carried forward
unchanged into Phase 11-D:

```text
engine-alignment baseline (11-C-8: is_protected_path, classify_task, apply_law,
  evaluate_action_capabilities as judgment source, not a hook-local duplicate) = preserved
@ file reference / non-tool-call context ingestion boundary = preserved
  (Aegis still does not claim to govern context that enters the model without
  a tool call; this remains outside the PreToolUse governance boundary)
Bash subprocess boundary = preserved
  (a governed Bash tool call decision is not governance of what a launched
  subprocess does afterward; no sandbox/process isolation is claimed)
hook evidence store binding = remains a future gate
  (11-C-4/11-C-5 evidence binding and verification are inert candidates;
  binding to real .aeg/ store write is not implemented and is not started
  by this document)
```

## Non-Equivalences

```text
entry gate != installation
entry gate != live execution
runtime-readiness candidate baseline != installed hook
documented user-gate requirement != user gate obtained
future gate listed != future gate satisfied
disposable-repo policy stated != disposable repo used
```

## Forbidden Overclaims Not Made By This Document

The following labels are not claimed as true by this document. Each remains
"not yet" until a later, separately gated phase demonstrates it:

```text
HOOK_RUNTIME_READY = NOT_CLAIMED
LIVE_HOOK_READY = NOT_CLAIMED
CLAUDE_CODE_HOOK_INSTALLED = NOT_CLAIMED
INSTALLED = NOT_CLAIMED
REAL_HOOK_RESPONSE_EMITTED = NOT_CLAIMED
CLAUDE_CODE_EXECUTION_PERFORMED = NOT_CLAIMED
TOOL_EXECUTION_READY = NOT_CLAIMED
WRITE_AUTHORITY_GRANTED = NOT_CLAIMED
STORE_WRITE_READY = NOT_CLAIMED
PUBLIC_RELEASE_READY = NOT_CLAIMED
BYPASS_IMPOSSIBLE = NOT_CLAIMED
TAMPER_PROOF = NOT_CLAIMED
```

## Transition Recommendation

Recommendation:

```text
hold current state
do not modify .claude/settings.json, install a hook, or execute Claude Code under Phase 11-D-0
proceed to 11-D-1 (install dry-run, no mutation) only with this entry gate merged as the recorded precondition
do not attempt 11-D-2 (actual disposable-repo install) without a separate, explicit user gate at that time
keep live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD and safe default = hold_current_state through all of Phase 11-D until a later phase explicitly and separately changes them
```

Main merge:

```text
main merge = NOT_PERFORMED
```
