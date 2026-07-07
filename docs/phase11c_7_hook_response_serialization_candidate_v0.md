# Aegis Phase 11-C-7 Hook Response Serialization Candidate v0

## Purpose

This document defines an inert serialization candidate for Phase 11-C hook
response envelopes.

It is serialization-candidate, docs, and test work only. It does not implement
hook runtime, hook commands, hook installation, Claude Code execution, Codex
execution, provider/model/network calls, action execution, write authority,
tool runtime, store routing, stdout/stderr hook output, filesystem mutation by
hook runtime or action execution, patch application, real Claude Code hook
response emission, or public release behavior.

Completion label:

```text
PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_COMPLETE_NOT_HOOK_RUNTIME
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
11-C-7 = COMPLETE_AS_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_NOT_HOOK_RUNTIME
contract version = phase11c_7_hook_response_serialization_candidate_v0
input = phase11c_6_hook_response_envelope_candidate_v0
serialization output = inert hook response serialization candidate only
response_transport_candidate = data_only_not_stdout
response_schema_status = generic_candidate_not_substrate_runtime
serialization candidate != real Claude Code hook response
serialization candidate != stdout/stderr emission
serialization candidate != hook runtime
serialization candidate != hook command
serialization candidate != execution
serialization candidate != action execution engine
serialization candidate != write authority
serialization candidate != store write
serialization candidate does not mutate filesystem
allow serialization candidate != execution
deny serialization candidate != real denial response
ask serialization candidate != user prompt implementation
defer/hold serialization candidate preserves safe default
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
reported_only != judgment basis
NOT_CHECKED != PASS
hook command implementation = NOT_STARTED
hook installation = NOT_STARTED
actual Claude Code execution = NOT_STARTED
real Claude Code hook response emission = NOT_STARTED
stdout/stderr hook output = NOT_STARTED
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
filesystem mutation = NOT_STARTED
patch application = NOT_STARTED
public release = NOT_STARTED
```

This is not the final Claude Code hook response schema. It is a generic
candidate record with a generic candidate schema status.

## Input

Phase 11-C-7 consumes:

```text
11-C-6 HookResponseEnvelopeCandidate object or serialized record
```

The helper accepts only already-provided envelope data. It does not read Claude
Code hook configuration, install hooks, execute Claude Code, invoke Codex, call
a provider, call a model, load API keys, read environment secrets, start a
network client, run a process, execute an action, write store state, or mutate
the filesystem.

## Serialization Candidate Fields

The v0 serialization candidate records:

```text
serialization_id
serialization_hash
serialization_version
source_envelope_id
source_envelope_hash
source_response_candidate_type
serialized_payload_candidate
serialized_payload_hash
response_transport_candidate = data_only_not_stdout
response_schema_status = generic_candidate_not_substrate_runtime
redacted_user_message
reason_codes
audit_summary
safe_default
live_executor_authority
trust_boundary
```

The implementation also records the completion label, hash algorithms,
redaction policy, and explicit invariant flags. The serialization hash is
deterministic over the serialization payload, excluding `serialization_id` and
`serialization_hash`:

```text
serialized_payload_hash recomputes deterministically
serialization_hash recomputes deterministically
serialization_id matches serialization_hash
serialization_hash = sha256_canonical_json_v0(phase11c_7_serialization_payload)
serialization_id = phase11c-7-hook-response-serialization:{serialization_hash}
```

`serialized_payload_candidate` is canonical JSON data carried inside the
serialization candidate record. It is data-only and is not stdout/stderr hook
output.

## Mapping Policy

```text
allow envelope candidate -> allow serialization candidate only
deny envelope candidate -> deny serialization candidate only
ask envelope candidate -> ask serialization candidate only
defer envelope candidate -> defer serialization candidate only
hold_current_state envelope candidate -> hold_current_state serialization candidate
malformed/unknown envelope -> hold_current_state serialization candidate
```

These are candidate labels only. They are not Claude Code hook responses, not
permission decisions, not stdout/stderr hook output, not execution, and not
write authority.

## Redaction Behavior

The v0 serialized payload candidate contains only response candidate type,
source envelope hash, redacted message, reason codes, hashes, and safe
summaries.

Required redaction posture:

```text
No raw full tool_input in serialized payload candidate.
No raw secret-bearing path/content/command text in serialized payload candidate by default.
Do not copy 11-C-4 target scope, payload, provenance metadata, or raw decision reason strings.
Payload must use response candidate type, redacted message, reason codes, hashes, and safe summaries only.
```

For malformed, hold-state, unknown, or mismatched source envelopes, the
serialization candidate does not copy source envelope id, source envelope hash,
or source response candidate type fields. This prevents unchecked source text
or mismatched identifiers from being promoted.

## Source Envelope Consistency

Phase 11-C-7 treats the Phase 11-C-6 envelope as the only source.

Required source checks:

```text
source_envelope_hash must match envelope.envelope_hash
source envelope safe_default must be hold_current_state
source envelope live_executor_authority must be LIVE_EXECUTOR_AUTHORITY_ON_HOLD
source envelope trust_boundary must be untrusted_raw_executor_output
source envelope runtime/emission/authority/store-write flags must be false
source envelope response_candidate_type must be allow, deny, ask, defer, or hold_current_state
```

If the source envelope is malformed, unknown, hash-mismatched, or boundary
mismatched, Phase 11-C-7 routes to:

```text
hold_current_state serialization candidate
source identifiers copied = false
```

The serialization candidate does not grant judgment-basis authority. It is
downstream data that preserves the envelope posture without becoming a live
executor permission decision.

## Required Invariants

Every Phase 11-C-7 serialization candidate preserves:

```text
serialization candidate != real Claude Code hook response
serialization candidate != stdout/stderr emission
serialization candidate != hook runtime
serialization candidate != hook command
serialization candidate != execution
serialization candidate != action execution engine
serialization candidate != write authority
serialization candidate != store write
serialization candidate does not mutate filesystem
allow serialization candidate != execution
deny serialization candidate != real denial response
ask serialization candidate != user prompt implementation
defer/hold serialization candidate preserves safe default
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
reported_only != judgment basis
NOT_CHECKED != PASS
hook_command_implemented = false
hook_installation_implemented = false
claude_code_execution_performed = false
real_hook_response_emitted = false
stdout_stderr_hook_output_written = false
provider_model_network_implemented = false
api_key_env_secret_loading_implemented = false
network_client_implemented = false
action_execution_engine_implemented = false
tool_runtime_implemented = false
write_authority_granted = false
state_store_module_changed = false
filesystem_mutation_by_serialization = false
patch_application_implemented = false
```

## Non-Goal Boundaries

Phase 11-C-7 does not implement or authorize:

```text
hook command implementation
.claude/settings.json mutation
actual hook installation
actual Claude Code execution
real Claude Code hook response emission
stdout/stderr hook output
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

Phase 11-C-7 produces only an inert serialization candidate:

```text
serialization candidate != real hook response
serialization candidate != stdout/stderr hook output
serialization candidate != runtime execution
serialization candidate != store write
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Next phases must continue to treat this serialization candidate as data only
unless a later, separate, explicitly reviewed phase defines and verifies
runtime behavior.
