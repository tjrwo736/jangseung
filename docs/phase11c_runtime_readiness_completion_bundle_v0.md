# Aegis Phase 11-C Runtime Readiness Completion Bundle v0

## Purpose

This document closes the Phase 11-C candidate line as a bounded Claude Code
PreToolUse runtime-readiness bundle.

Completion marker:

```text
PHASE11C_RUNTIME_READINESS_COMPLETION_BUNDLE_COMPLETE_NOT_INSTALLED_NOT_LIVE_RUNTIME
```

Target outcome:

```text
Phase 11-C = COMPLETE_AS_CLAUDE_CODE_PRETOOLUSE_RUNTIME_READINESS_BUNDLE_NOT_INSTALLED_NOT_LIVE_RUNTIME
runtime readiness candidate != real Claude Code hook response
response schema candidate != stdout/stderr emission
dry runtime entrypoint candidate != hook runtime
dry runtime entrypoint candidate != installed hook
dry runtime entrypoint candidate != execution
dry runtime entrypoint candidate != action execution engine
dry runtime entrypoint candidate != write authority
dry runtime entrypoint candidate != store write
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
main merge = NOT_PERFORMED
```

This bundle is still not live runtime, not installed, not public release, not
write authority, and not provider/model/network work.

## Docs Source

Claude Code PreToolUse response schema source status for this candidate:

```text
docs checked date: 2026-07-07
source type: Claude Code Hooks reference
schema status: current_docs_checked_but_runtime_not_executed
```

The candidate uses only the currently documented PreToolUse candidate shape:

```text
hookSpecificOutput
hookEventName = "PreToolUse"
permissionDecision = "allow" | "deny" | "ask" | "defer"
permissionDecisionReason = redacted reason string
```

Deprecated top-level `decision` / `reason` fields are not used for the
PreToolUse schema candidate. This document does not claim a final Claude Code
hook response schema beyond the current documented PreToolUse candidate shape.

## Input Chain

The dry-readiness chain remains:

```text
11-C-1 ClaudeCodePreToolUseInput
11-C-2 ToolCallStructuredActionCandidate
11-C-3 HookDecisionCandidate
11-C-4 HookEvidenceBinding
11-C-5 HookEvidenceVerificationGateResult
11-C-6 HookResponseEnvelopeCandidate
11-C-7 HookResponseSerializationCandidate
11-C runtime-readiness response schema candidate
11-C dry entrypoint candidate
```

Each stage is deterministic and data-only. The new runtime-readiness stage
accepts a Phase 11-C-7 `HookResponseSerializationCandidate` and returns an
inert `ClaudeCodePreToolUseResponseSchemaCandidate` only.

## Response Schema Candidate

Required fields:

```text
response_schema_candidate_id
response_schema_candidate_hash
response_schema_candidate_version
source_serialization_id
source_serialization_hash
source_response_candidate_type
claude_code_hook_event_name = PreToolUse
hook_specific_output_candidate
permission_decision_candidate
permission_decision_reason_redacted
response_transport_candidate = data_only_not_stdout
response_schema_status = claude_code_pretooluse_candidate_not_runtime
docs_checked_date
docs_source_status
safe_default
live_executor_authority
trust_boundary
```

Mapping behavior:

```text
allow serialization candidate -> permissionDecision allow candidate only
deny serialization candidate -> permissionDecision deny candidate only
ask serialization candidate -> permissionDecision ask candidate only
defer serialization candidate -> permissionDecision defer candidate only
hold_current_state serialization candidate -> permissionDecision deny candidate by default
malformed/unknown/mismatched serialization candidate -> hold_current_state candidate and no source ids copied
```

Hold-state rationale:

```text
Claude Code PreToolUse permissionDecision has no hold_current_state value in the checked docs shape.
The inert candidate maps hold_current_state to permissionDecision deny as a conservative data-only candidate.
deny candidate != actual denial response unless emitted by a later runtime phase.
```

Critical policy:

```text
allow candidate != execution
allow candidate != write authority
allow candidate != installed hook output
allow candidate must not be emitted to stdout in this PR
live_executor_authority remains LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

The schema candidate recomputes and checks the Phase 11-C-7 serialization hash,
serialization id, serialized payload hash, transport, schema status, safe
default, live executor authority, trust boundary, and runtime/emission/store
flags. If the source is malformed, unknown, hash-mismatched, or runtime-flagged,
the candidate holds and copies no source serialization ids.

## Dry Entrypoint Candidate

The dry entrypoint candidate accepts a raw PreToolUse JSON object or mapping
fixture that has already been provided in memory. It returns only an in-memory
`HookRuntimeDryRunResultCandidate`.

Required returned fields:

```text
dry_run_result_id
dry_run_result_hash
source_tool_use_id
resulting_candidate_type
response_schema_candidate_hash
would_emit_stdout = false
stdout_payload = null
stderr_payload = null
install_performed = false
execution_performed = false
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Dry entrypoint invariants:

```text
must not read stdin
must not write stdout
must not write stderr
must not call sys.exit
must not install hook
must not mutate filesystem
must not execute Claude Code
must not execute tools
must not call provider/model/network
must not load API keys/env/secrets
```

Malformed input, unknown input, source mismatch, or any runtime-surface flag set
to true routes to `hold_current_state`.

## Redaction Behavior

The response schema candidate and dry result do not retain raw full tool input.
They do not copy raw secret-bearing path, content, or command text. The
`permissionDecisionReason` value is a redacted reason string built from
candidate type and boundary status only.

Required redaction posture:

```text
raw tool_input retention = false
raw path/content/command retention = false
raw secret retention = false
permissionDecisionReason = redacted reason string
reported_only != judgment basis
NOT_CHECKED != PASS
```

## Non-Install Settings Template

The following is documentation only.

```text
NOT_INSTALLED
DO_NOT_COPY_WITHOUT_USER_APPROVAL
EXAMPLE_ONLY
```

Example-only placeholder template:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/NON_EXISTING/PATH/PHASE11C_RUNTIME_READINESS_PLACEHOLDER_NOT_INSTALLED"
          }
        ]
      }
    ]
  }
}
```

This template is not `.claude/settings.json`, is not
`.claude/settings.local.json`, and is not an installed hook command. It
references a non-existing placeholder command path and must not be copied
without explicit user approval in a later runtime installation phase.

## Required Invariants

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
allow candidate != execution
deny candidate != actual denial response unless emitted by later runtime phase
ask candidate != user prompt implementation
defer candidate != actual subprocess defer behavior
hold candidate preserves safe default
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
reported_only != judgment basis
NOT_CHECKED != PASS
```

## Non-Goals

This bundle does not implement or authorize:

```text
hook command implementation
actual CLI main that reads stdin
actual stdout/stderr hook output
actual hook installation
.claude/settings.json mutation
.claude/settings.local.json mutation
actual Claude Code execution
real Claude Code hook response emission
Codex implementation
provider/model/network implementation
OpenAI/Ollama/LLM call
API key/env/secret loading
network client
subprocess/shell execution
action execution engine
write authority
tool runtime
store.py change
src/state/store.py change
filesystem mutation
patch application
public release
final Claude Code hook response schema claim
universal prompt-injection prevention claim
sandbox/process isolation claim
Bash-safe claim
```
