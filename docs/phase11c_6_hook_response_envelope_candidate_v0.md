# Aegis Phase 11-C-6 Hook Response Envelope Candidate v0

## Purpose

This document defines an inert hook response envelope candidate from verified
Phase 11-C evidence and decision data.

It is envelope, docs, and test work only. It does not implement hook runtime,
hook commands, hook installation, Claude Code execution, Codex execution,
provider/model/network calls, action execution, write authority, tool runtime,
store routing, stdout/stderr hook output, filesystem mutation by hook runtime
or action execution, patch application, real Claude Code hook response
emission, or public release behavior.

Completion label:

```text
PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_COMPLETE_NOT_HOOK_RUNTIME
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
11-C-6 = COMPLETE_AS_HOOK_RESPONSE_ENVELOPE_CANDIDATE_NOT_HOOK_RUNTIME
contract version = phase11c_6_hook_response_envelope_candidate_v0
verification input = phase11c_5_hook_evidence_verification_gate_v0
binding input = phase11c_4_hook_evidence_binding_v0
decision input = phase11c_3_hook_decision_adapter_v0, optional consistency source
envelope output = inert hook response envelope candidate only
envelope candidate != real Claude Code hook response
envelope candidate != stdout/stderr emission
envelope candidate != hook runtime
envelope candidate != execution
envelope candidate != action execution engine
envelope candidate != write authority
envelope candidate != store write
envelope candidate does not mutate filesystem
allow envelope candidate != execution
deny envelope candidate != real denial response
ask envelope candidate != user prompt implementation
defer/hold envelope candidate preserves safe default
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
```

## Input

Phase 11-C-6 consumes:

```text
11-C-5 HookEvidenceVerificationGateResult
11-C-4 HookEvidenceBinding object or serialized record
11-C-3 HookDecisionCandidate data, optional consistency source
```

The helper uses the 11-C-5 verification output as the gate. `VERIFIED` and
`REJECTED` verification outputs are usable source data only when the
verification result and binding record agree on `binding_id`, `binding_hash`,
safe default, live executor authority, trust boundary, and binding status.

If optional 11-C-3 decision data is provided, it must agree with the binding's
`decision_candidate`, `source_tool_use_id`, and `action_id`. A mismatch routes
to `hold_current_state`.

The envelope helper accepts only already-provided data. It does not read Claude
Code hook configuration, install hooks, execute Claude Code, invoke Codex, call
a provider, call a model, load API keys, read environment secrets, spawn a
process, execute an action, write store state, or mutate the filesystem.

## Envelope Candidate Fields

The v0 envelope candidate records:

```text
envelope_id
envelope_hash
envelope_version
source_binding_id
source_binding_hash
source_verification_output
source_decision_candidate
source_tool_use_id
action_id
response_candidate_type
response_reason_codes
redacted_user_message
audit_summary
safe_default
live_executor_authority
trust_boundary
```

The implementation also records the completion label, hash algorithm, redaction
policy, and explicit invariant flags. The envelope hash is deterministic over
the envelope payload, excluding `envelope_id` and `envelope_hash`:

```text
envelope_hash = sha256_canonical_json_v0(phase11c_6_envelope_payload)
envelope_id = phase11c-6-hook-response-envelope:{envelope_hash}
```

## Response Candidate Types

The v0 response candidate types are:

```text
allow
deny
ask
defer
hold_current_state
```

These are candidate labels only. They are not Claude Code hook responses, not
permission decisions, not stdout/stderr hook output, not execution, and not
write authority.

## Mapping Policy

```text
VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=allow -> allow envelope candidate only
VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=deny -> deny envelope candidate only
VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=ask -> ask envelope candidate only
VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE + decision_candidate=defer -> defer envelope candidate
REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE -> hold_current_state envelope candidate
HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE -> hold_current_state envelope candidate
Unknown/malformed input -> hold_current_state envelope candidate
```

`REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE` maps to
`hold_current_state` in v0. This is intentionally conservative and remains an
inert envelope candidate, not a real denial response.

## Redaction Behavior

The v0 envelope contains only source identifiers, source hashes, source
verification output, source decision candidate labels, response candidate type,
reason codes, and redacted summaries.

Required redaction posture:

```text
No raw full tool_input in envelope.
No raw secret-bearing path/content/command text in envelope by default.
User-facing/audit message uses redacted summaries and reason codes only.
response_reason_codes are generated Phase 11-C-6 codes plus safe 11-C-5 rejection codes.
11-C-4 decision reason strings are not copied into the envelope.
11-C-4 target scope, payload, and provenance metadata are not copied into the envelope.
```

For malformed, hold-state, or mismatched inputs, the envelope does not copy
source binding id, binding hash, source tool use id, action id, or decision
candidate fields. This prevents unverified source text from being promoted into
the envelope.

## Verification Binding Behavior

Phase 11-C-6 treats Phase 11-C-5 as the verification gate:

```text
verification_passed must be true for VERIFIED or REJECTED source use
source binding_id must match verification binding_id
source binding_hash must match verification binding_hash
source safe_default must be hold_current_state
source live_executor_authority must be LIVE_EXECUTOR_AUTHORITY_ON_HOLD
source trust_boundary must be untrusted_raw_executor_output
VERIFIED output requires binding_status = HOOK_EVIDENCE_BOUND
REJECTED output requires binding_status = HOOK_EVIDENCE_BINDING_REJECTED
decision_candidate must be allow/deny/ask/defer
optional decision source must match binding decision/source ids when provided
```

A mismatch routes to:

```text
hold_current_state envelope candidate
```

The envelope does not grant judgment-basis authority. It is downstream data
that preserves the verified binding/decision posture without becoming a live
executor permission decision.

## Required Invariants

Every Phase 11-C-6 envelope candidate preserves:

```text
envelope candidate != real Claude Code hook response
envelope candidate != stdout/stderr emission
envelope candidate != hook runtime
envelope candidate != execution
envelope candidate != action execution engine
envelope candidate != write authority
envelope candidate != store write
envelope candidate does not mutate filesystem
allow envelope candidate != execution
deny envelope candidate != real denial response
ask envelope candidate != user prompt implementation
defer/hold envelope candidate preserves safe default
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
filesystem_mutation_by_envelope = false
patch_application_implemented = false
```

## Non-Goal Boundaries

Phase 11-C-6 does not implement or authorize:

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

Phase 11-C-6 produces only an inert response envelope candidate:

```text
response envelope candidate != real hook response
response envelope candidate != stdout/stderr hook output
response envelope candidate != runtime execution
response envelope candidate != store write
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Next phases must continue to treat this envelope as data only unless a later,
separate, explicitly reviewed phase defines and verifies runtime behavior.
