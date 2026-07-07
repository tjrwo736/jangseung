# Aegis Phase 11-C-4 Hook Evidence Binding v0

## Purpose

This document defines the initial evidence binding for Phase 11-C hook input,
structured action candidates, and hook decision candidates.

It is evidence-binding, docs, and test work only. It does not implement hook
runtime, hook commands, hook installation, Claude Code execution, Codex
execution, provider/model/network calls, action execution, write authority,
tool runtime, store routing, filesystem mutation by hook runtime or action
execution, patch application, real Claude Code hook response emission, or
public release behavior.

Completion label:

```text
PHASE11C_4_HOOK_EVIDENCE_BINDING_COMPLETE_NOT_HOOK_RUNTIME
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
11-C-4 = COMPLETE_AS_HOOK_EVIDENCE_BINDING_NOT_HOOK_RUNTIME
contract version = phase11c_4_hook_evidence_binding_v0
input contract = phase11c_1_claude_code_pretooluse_input_contract_v0
structured action source = phase11c_2_tool_call_to_structured_action_mapping_v0
hook decision source = phase11c_3_hook_decision_adapter_v0
binding output = inert hook evidence binding only
binding output != judgment basis by itself
binding output != execution
binding output != hook response
binding output != write authority
binding output != store write
binding output does not mutate filesystem
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

Phase 11-C-4 consumes these inert Phase 11-C objects:

```text
11-C-1 validated PreToolUse input
11-C-2 structured action candidate
11-C-3 hook decision candidate
```

The binding preserves source identity and provenance, but it does not promote
any source object into trusted runtime state. A valid binding is still not a
permission decision, not an allow decision, not a deny response, not execution,
not write authority, and not a store write.

## Required Bound Fields

The v0 binding records:

```text
tool_name
tool_use_id
tool_input_hash
source_tool_use_id
action_id
candidate_action_type
candidate_status
decision_candidate
decision reasons
declared_risk
risk_status
capability_requirements
provenance
safe_default
live_executor_authority
trust boundary
```

The binding also records deterministic hashes and metadata fingerprints for
candidate payload and target scope. Those hashes support later replay and
comparison without retaining raw full tool input by default.

## Hash And Redaction Behavior

Raw full `tool_input` is not stored by default.

The v0 binding stores:

```text
tool_input_hash = sha256_canonical_json_v0(tool_input)
tool_input_raw_stored = false
tool_input_redaction_policy = fingerprint_only_redact_secret_like_values_v0
raw value metadata = type / length / sha256 fingerprints
raw value retention = false
```

Likely secret material is redacted from metadata previews:

```text
.env path/value -> redacted
.env.* path/value -> redacted
api_key-like key/value -> redacted
token-like key/value -> redacted
secret-like key/value -> redacted
password/private-key/credential/bearer-like key/value -> redacted
```

The binding preserves enough metadata for verification:

```text
field paths
value kinds
string lengths
string hashes
redacted field paths
secret-like field paths
candidate payload hash
target scope hash
source tool_use_id / action_id provenance
```

The binding does not retain raw full command text, write content, edit strings,
or secret-bearing path values by default.

## Provenance Handling

The binding preserves provenance from all three sources:

```text
hook_input.contract_version
hook_input.tool_name
hook_input.tool_use_id
hook_input.tool_input_hash
hook_input.trust_boundary
hook_input optional metadata as redacted metadata
hook_input extra untrusted fields as redacted metadata

structured_action_candidate.contract_version
structured_action_candidate.source_contract_version
structured_action_candidate.source_tool_name
structured_action_candidate.source_tool_use_id
structured_action_candidate.action_id
structured_action_candidate.candidate_action_type
structured_action_candidate.candidate_status
structured_action_candidate.provenance as redacted metadata

hook_decision_candidate.contract_version
hook_decision_candidate.source_contract_version
hook_decision_candidate.source_tool_use_id
hook_decision_candidate.action_id
hook_decision_candidate.decision_candidate
hook_decision_candidate.decision_candidate_status
hook_decision_candidate.source_provenance as redacted metadata
hook_decision_candidate.ignored_reported_only_fields
```

Provenance is recorded as context for later deterministic checks. It is not a
judgment basis by itself and cannot grant authority.

## Required Invariants

Every Phase 11-C-4 binding preserves:

```text
evidence binding != judgment basis by itself
evidence binding != execution
evidence binding != hook response
evidence binding != write authority
evidence binding != store write
evidence binding does not mutate filesystem
reported_only != judgment basis
NOT_CHECKED != PASS
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
tool_input_raw_stored = false
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
filesystem_mutation_by_binding = false
patch_application_implemented = false
```

Binding consistency checks may reject a mismatched input/action/decision chain,
but rejection remains evidence-binding status only. It is not a real hook
response and does not execute any action.

## Reported-Only And NOT_CHECKED Handling

Reported-only or self-reported allow claims remain untrusted context:

```text
reported_only != judgment basis
self-reported allow != judgment basis
reported-only metadata may be fingerprinted and preserved
reported-only metadata cannot promote a binding to PASS
```

`NOT_CHECKED` remains fail-closed:

```text
NOT_CHECKED != PASS
unsupported/unknown/NOT_CHECKED != PASS
NOT_CHECKED does not create execution authority
NOT_CHECKED does not create write authority
NOT_CHECKED does not create hook response authority
safe default = hold_current_state
```

## Non-Goal Boundaries

Phase 11-C-4 does not implement or authorize:

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

Phase 11-C-4 produces only an inert evidence binding:

```text
validated PreToolUse input
-> structured action candidate
-> hook decision candidate
-> evidence binding with hashes/redacted metadata/provenance
-> hold_current_state unless a later explicit gate decides otherwise
```

Later phases may verify or consume the binding, but they must not treat the
binding as execution, authority, a store write, or a real Claude Code hook
response.
