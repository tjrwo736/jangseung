# Aegis Phase 11-C-5 Hook Evidence Verification Gate v0

## Purpose

This document defines a verification gate for Phase 11-C-4 hook evidence
binding records.

It is verification, docs, and test work only. It does not implement hook
runtime, hook commands, hook installation, Claude Code execution, Codex
execution, provider/model/network calls, action execution, write authority,
tool runtime, store routing, filesystem mutation by hook runtime or action
execution, patch application, real Claude Code hook response emission, or
public release behavior.

Completion label:

```text
PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_COMPLETE_NOT_HOOK_RUNTIME
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
11-C-5 = COMPLETE_AS_HOOK_EVIDENCE_VERIFICATION_GATE_NOT_HOOK_RUNTIME
contract version = phase11c_5_hook_evidence_verification_gate_v0
input contract = phase11c_4_hook_evidence_binding_v0
input completion label = PHASE11C_4_HOOK_EVIDENCE_BINDING_COMPLETE_NOT_HOOK_RUNTIME
verification output = inert hook evidence binding verification candidate only
verification output != judgment basis by itself
verification output != execution
verification output != hook response
verification output != write authority
verification output != store write
verification output does not mutate filesystem
verified evidence binding candidate != real Claude Code hook response
rejected evidence binding candidate != real Claude Code hook response
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

Phase 11-C-5 consumes a Phase 11-C-4 `HookEvidenceBinding` object or its
serialized record.

The gate accepts only evidence-binding records as data. It does not read
Claude Code hook configuration, install hooks, execute Claude Code, invoke
Codex, call a provider, call a model, load API keys, read environment secrets,
spawn a process, execute an action, write store state, or mutate the
filesystem.

## Verification Outputs

The v0 gate emits one of three inert verification candidates:

```text
VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE
REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE
HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE
```

Output behavior:

```text
HOOK_EVIDENCE_BOUND + all verification checks matched
-> VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE

HOOK_EVIDENCE_BINDING_REJECTED + all verification checks matched
-> REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE

any verification mismatch, malformed record, retained raw input, retained known secret fragment, authority flag, runtime flag, store-write flag, or provenance inconsistency
-> HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE
```

`REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE` means the Phase 11-C-4 binding
itself was an internally consistent rejected binding record. It is not a real
Claude Code hook response and does not deny, allow, ask, or execute in a
runtime.

## Required Verification Checks

The v0 gate verifies:

```text
binding_hash recomputes deterministically
binding_id matches binding_hash
completion label matches PHASE11C_4_HOOK_EVIDENCE_BINDING_COMPLETE_NOT_HOOK_RUNTIME
binding_status is either HOOK_EVIDENCE_BOUND or HOOK_EVIDENCE_BINDING_REJECTED
tool_input_raw_stored = false
tool_input_hash_algorithm = sha256_canonical_json_v0
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
trust_boundary = untrusted_raw_executor_output
source_tool_use_id/action_id provenance is internally consistent
decision_candidate is one of allow/deny/ask/defer
reported_only != judgment basis
NOT_CHECKED != PASS
no authority flags are true
no runtime flags are true
no store-write flags are true
no raw secret fragments appear in serialized record for known probes
raw full tool_input is not retained by default
```

The binding hash replay is over the Phase 11-C-4 payload fields only. The gate
rejects missing or unexpected serialized fields instead of treating a rebound
record with extra raw material as valid.

## Hash Replay Behavior

The gate recomputes:

```text
binding_hash = sha256_canonical_json_v0(phase11c_4_payload)
binding_id = phase11c-4-hook-evidence:{binding_hash}
```

Hash replay is deterministic. A mismatch in either the hash or the binding id
routes to:

```text
HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE
```

## Raw Retention And Secret Probes

The gate requires:

```text
tool_input_raw_stored = false
raw full tool_input is not retained by default
raw_value_stored = false in metadata
raw_values_stored = false in metadata
known secret probe fragments absent from serialized record
```

Known probe checks are caller-supplied strings used only for serialization
inspection. The gate does not claim universal secret discovery or universal
prompt-injection prevention.

## Provenance Consistency

The gate checks that source provenance agrees across the binding, hook input,
structured action candidate, and hook decision candidate:

```text
binding.tool_use_id == binding.source_tool_use_id
binding.action_id == pretooluse:{source_tool_use_id}
hook_input.tool_use_id == binding.source_tool_use_id
structured_action_candidate.source_tool_use_id == binding.source_tool_use_id
hook_decision_candidate.source_tool_use_id == binding.source_tool_use_id
structured_action_candidate.action_id == binding.action_id
hook_decision_candidate.action_id == binding.action_id
hook_input.tool_input_hash == binding.tool_input_hash
hook_input.tool_input_raw_stored = false
structured_action_candidate contract version = phase11c_2_tool_call_to_structured_action_mapping_v0
hook_decision_candidate contract version = phase11c_3_hook_decision_adapter_v0
```

Provenance consistency is verification context only. It is not a judgment basis
by itself and cannot grant authority.

## Required Invariants

Every Phase 11-C-5 verification result preserves:

```text
verification output != judgment basis by itself
verification output != execution
verification output != hook response
verification output != write authority
verification output != store write
verification output does not mutate filesystem
verified evidence binding candidate != real Claude Code hook response
rejected evidence binding candidate != real Claude Code hook response
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
reported_only != judgment basis
NOT_CHECKED != PASS
hook_command_implemented = false
hook_installation_implemented = false
claude_code_execution_performed = false
real_hook_response_emitted = false
provider_model_network_implemented = false
api_key_env_secret_loading_implemented = false
network_client_implemented = false
action_execution_engine_implemented = false
tool_runtime_implemented = false
write_authority_granted = false
state_store_module_changed = false
filesystem_mutation_by_verification = false
patch_application_implemented = false
```

## Non-Goal Boundaries

Phase 11-C-5 does not implement or authorize:

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

Phase 11-C-5 produces only an inert verification candidate:

```text
HookEvidenceBinding record
-> deterministic binding_hash replay
-> invariant/provenance/raw-retention checks
-> verified, rejected, or hold-current-state verification candidate
-> hold_current_state unless a later explicit gate decides otherwise
```

Later phases may consume the verification candidate, but they must not treat it
as execution, authority, a store write, or a real Claude Code hook response.
