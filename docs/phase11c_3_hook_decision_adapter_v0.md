# Aegis Phase 11-C-3 Hook Decision Adapter v0

## Purpose

This document defines the initial contract-only adapter from Phase 11-C-2
Aegis structured action candidates to generic hook decision candidates.

It is adapter, contract, docs, and test work only. It does not implement hook
runtime, hook commands, hook installation, Claude Code execution, Codex
execution, provider/model/network calls, action execution, write authority,
tool runtime, store routing, filesystem mutation by hook runtime or action
execution, patch application, real Claude Code hook response emission, or
public release behavior.

Completion label:

```text
PHASE11C_3_HOOK_DECISION_ADAPTER_COMPLETE_NOT_HOOK_RUNTIME
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Main merge:

```text
main merge = NOT_PERFORMED
```

## Contract Status

```text
Phase 11-C = OPEN
11-C-3 = COMPLETE_AS_HOOK_DECISION_ADAPTER_NOT_HOOK_RUNTIME
contract version = phase11c_3_hook_decision_adapter_v0
input contract = phase11c_2_tool_call_to_structured_action_mapping_v0
adapter output = hook decision candidate only
adapter output != actual hook response emission
adapter output != execution
adapter output != action execution engine
adapter output != write authority
adapter output != patch application
adapter output does not mutate filesystem
adapter output preserves source tool_use_id and action_id provenance
hook command implementation = NOT_STARTED
hook installation = NOT_STARTED
actual Claude Code execution = NOT_STARTED
real Claude Code hook response emission = NOT_STARTED
Codex implementation = NOT_STARTED
provider/model/network = NOT_STARTED / NOT_GRANTED
OpenAI/Ollama/LLM call = NOT_STARTED / NOT_GRANTED
API key/env/secret loading = NOT_STARTED / NOT_GRANTED
network client = NOT_STARTED / NOT_GRANTED
subprocess/shell execution = NOT_STARTED / NOT_GRANTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store.py change = NOT_PERFORMED
filesystem mutation = NOT_STARTED
patch application = NOT_STARTED
public release = NOT_STARTED
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Input

Phase 11-C-3 consumes only Phase 11-C-2 structured action candidates.

Required source provenance preserved by the adapter:

```text
source_tool_use_id = original source tool_use_id
action_id = original source action_id
source_contract_version = phase11c_2_tool_call_to_structured_action_mapping_v0
source_provenance = carried as untrusted context
```

Invalid input is not promoted to an allow candidate.

```text
invalid input -> defer candidate
invalid input != allow
safe default = hold_current_state
```

## Generic Output Decision Candidates

The adapter emits only generic hook decision candidates:

```text
allow
deny
ask
defer
```

These are candidate values only. They are not actual Claude Code hook
responses, not runtime decisions, not execution, not write authority, and not
patch application.

## Decision Candidate Mapping

Initial policy:

```text
READ_REPO normal repo path / LOW / STRUCTURED_ACTION_CANDIDATE
  -> allow candidate

WRITE_FILE normal repo path / LOW / STRUCTURED_ACTION_CANDIDATE
  -> ask candidate

EDIT_FILE normal repo path / LOW / STRUCTURED_ACTION_CANDIDATE
  -> ask candidate

DENY_CANDIDATE
  -> deny candidate

protected path DENY_CANDIDATE
  -> deny candidate

dangerous Bash DENY_CANDIDATE
  -> deny candidate

RUN_COMMAND with HOLD_CURRENT_STATE_CANDIDATE / NOT_CHECKED
  -> defer candidate

unknown/unsupported/NOT_CHECKED
  -> defer candidate

invalid input
  -> defer candidate
```

The v0 adapter chooses `allow` for only the narrow low-risk normal repo read
candidate shape. It chooses `ask` for normal repo write/edit candidates because
write/edit is not allowed by default. It chooses `deny` for explicit
`DENY_CANDIDATE` inputs. It chooses `defer` for hold-current-state,
unknown, unsupported, NOT_CHECKED, invariant-mismatched, and invalid inputs.

## Deny / Defer / Ask / Allow Policy

```text
deny = explicit structured action DENY_CANDIDATE only
defer = hold_current_state, unknown, unsupported, NOT_CHECKED, invalid, or invariant mismatch
ask = write/edit normal repo candidate requiring a later explicit gate
allow = read-only low-risk normal repo candidate only
```

`allow` remains a hook decision candidate. It is not execution and not a real
hook response.

`ask` remains a hook decision candidate. It is not a user prompt implementation
and not a permission grant.

`deny` remains a hook decision candidate. It is not a real Claude Code hook
response emission.

`defer` preserves the safe default:

```text
safe default = hold_current_state
```

## NOT_CHECKED Handling

The adapter never maps NOT_CHECKED to allow:

```text
NOT_CHECKED != allow
unsupported/unknown != allow
unsupported/unknown/NOT_CHECKED != allow
reported_only != judgment basis
```

RUN_COMMAND candidates with `HOLD_CURRENT_STATE_CANDIDATE`, `NOT_CHECKED`,
unknown Bash posture, invalid tool input posture, or unsupported tool posture
map to `defer candidate`, not `allow candidate`.

## Reported-Only Handling

The adapter ignores reported-only or self-reported allow claims:

```text
reported_only/self-reported allow is ignored
reported_only != judgment basis
self-reported allow != judgment basis
```

Reported-only metadata may be carried as context so that it can be rejected or
ignored by deterministic checks. It cannot promote write/edit, command, unknown,
invalid, or NOT_CHECKED input to allow.

## Required Invariants

Every Phase 11-C-3 adapter output preserves:

```text
adapter output is hook decision candidate only
adapter output != actual hook response emission
adapter output != execution
adapter output != action execution engine
adapter output != write authority
adapter output != patch application
adapter output does not mutate filesystem
adapter output preserves source tool_use_id and action_id provenance
safe default = hold_current_state
NOT_CHECKED != allow
unsupported/unknown != allow
reported_only != judgment basis
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
action_executed = false
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
hook_response_produced = false
patch_application_performed = false
```

## Non-Goal Boundaries

Phase 11-C-3 does not implement or authorize:

```text
hook command implementation
.claude/settings.json mutation
actual hook installation
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
filesystem mutation
patch application
public release
live_executor_authority change
safe default change
universal prompt-injection prevention claim
sandbox/process isolation claim
Bash-safe claim
```

## Handoff

Phase 11-C-3 produces only generic hook decision candidates:

```text
structured action candidate
-> adapt as untrusted candidate data
-> allow / deny / ask / defer candidate
-> hold_current_state unless a later explicit gate emits a real response
```

Later phases may bind candidate decisions into hook response emission, evidence,
and verify flows, but they must not treat this adapter as hook runtime,
execution, authority, write permission, patch application, or final Claude Code
hook behavior.
