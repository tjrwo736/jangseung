# Aegis Phase 11-C Completion Baseline Not Installed v0

## Baseline Marker

```text
PHASE11C_COMPLETION_BASELINE_NOT_INSTALLED_NOT_LIVE_RUNTIME
```

Completion status:

```text
Phase 11-C = COMPLETE_AS_CLAUDE_CODE_PRETOOLUSE_RUNTIME_READINESS_BUNDLE_NOT_INSTALLED_NOT_LIVE_RUNTIME
11-C-0 Direction Lock = merged
11-C-1 Claude Code PreToolUse Input Contract = merged
11-C-2 Tool Call to Structured Action Mapping = merged
11-C-3 Hook Decision Adapter = merged
11-C-4 Hook Evidence Binding = merged
11-C-5 Hook Evidence Verification Gate = merged
11-C-6 Hook Response Envelope Candidate = merged
11-C-7 Hook Response Serialization Candidate = merged
11-C runtime-readiness response schema candidate = complete as candidate
11-C dry entrypoint candidate = complete as candidate
main merge = NOT_PERFORMED
```

This baseline records a runtime-readiness candidate state only. It is not live
runtime, not installed, not public release, not write authority, not store
write authority, and not provider/model/network work.

## Source Status

```text
docs checked date: 2026-07-07
source type: Claude Code Hooks reference
schema status: current_docs_checked_but_runtime_not_executed
Claude Code PreToolUse candidate shape = hookSpecificOutput / hookEventName / permissionDecision / permissionDecisionReason
final Claude Code hook response schema claim = NOT_CLAIMED
```

## Candidate Boundaries

```text
runtime readiness candidate != real Claude Code hook response
response schema candidate != stdout/stderr emission
dry runtime entrypoint candidate != hook runtime
dry runtime entrypoint candidate != installed hook
dry runtime entrypoint candidate != execution
dry runtime entrypoint candidate != action execution engine
dry runtime entrypoint candidate != write authority
dry runtime entrypoint candidate != store write
dry runtime entrypoint candidate does not mutate filesystem
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
reported_only != judgment basis
NOT_CHECKED != PASS
```

## Behavior Baseline

Expected end-to-end dry-run behavior:

```text
Read normal path -> allow candidate chain
Write normal path -> ask candidate chain
Read .env or protected path -> deny candidate chain
Bash dangerous command -> deny candidate chain
Bash NOT_CHECKED/unknown -> hold_current_state candidate chain
malformed input -> hold_current_state candidate chain
source hash mismatch at 11-C-7 -> hold_current_state candidate chain
runtime flag true anywhere -> hold_current_state candidate chain
raw secret/path/content/command probe -> not present in final candidate records
final dry-run result -> no stdout/stderr/install/runtime/write/store/provider/process flags
```

The hold-current-state serialization case maps to `permissionDecision = deny`
only as an inert PreToolUse response schema candidate because the checked
PreToolUse permissionDecision values do not include `hold_current_state`.

## Non-Install Baseline

```text
.claude/settings.json mutation = NOT_PERFORMED
.claude/settings.local.json mutation = NOT_PERFORMED
hook command implementation = NOT_STARTED
hook installation = NOT_STARTED
actual CLI main that reads stdin = NOT_STARTED
actual stdout/stderr hook output = NOT_STARTED
actual Claude Code execution = NOT_STARTED
real Claude Code hook response emission = NOT_STARTED
```

Any template in this Phase 11-C bundle is documentation-only and labeled:

```text
NOT_INSTALLED
DO_NOT_COPY_WITHOUT_USER_APPROVAL
EXAMPLE_ONLY
```

## Non-Goals

```text
Codex implementation = NOT_STARTED
provider/model/network implementation = NOT_STARTED / NOT_GRANTED
OpenAI/Ollama/LLM call = NOT_STARTED / NOT_GRANTED
API key/env/secret loading = NOT_STARTED / NOT_GRANTED
network client = NOT_STARTED / NOT_GRANTED
subprocess/shell execution = NOT_STARTED / NOT_GRANTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store.py change = NOT_PERFORMED
src/state/store.py change = NOT_PERFORMED
filesystem mutation = NOT_STARTED
patch application = NOT_STARTED
public release = NOT_STARTED
universal prompt-injection prevention claim = NOT_CLAIMED
sandbox/process isolation claim = NOT_CLAIMED
Bash-safe claim = NOT_CLAIMED
```
