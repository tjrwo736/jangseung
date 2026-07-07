# Aegis Phase 11-B-4-1 Deterministic No-Provider Model-like Adapter v0

## Purpose

Phase 11-B-4-1 implements a deterministic no-provider model-like adapter dry
structure. It simulates the restricted model executor output surface without a
provider, model, network call, tool runtime, action execution engine, write
authority, store route, or patch application path.

Core principle:

```text
deterministic model-like adapter = no provider, no tools, propose-only, data-only, raw executor output only
```

Completion label:

```text
PHASE11B_4_1_DETERMINISTIC_NO_PROVIDER_MODEL_LIKE_ADAPTER_COMPLETE_NOT_PROVIDER
```

Required limits:

```text
DETERMINISTIC_NO_PROVIDER_ONLY
NOT_MODEL_PROVIDER_INTEGRATION
NOT_PROVIDER_READY
NOT_NETWORK_ENABLED
NOT_ACTION_EXECUTION_ENGINE
NOT_WRITE_AUTHORITY
NOT_TOOL_RUNTIME
NOT_PATCH_APPLY
NOT_LIVE_EXECUTOR_READY
PROVIDER_GATE_REQUIRED
```

Safe default:

```text
safe_default = hold_current_state
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Implemented Files

Implemented adapter:

```text
src/evidence/deterministic_model_like_adapter.py
```

Focused tests:

```text
tests/test_phase11b_4_1_deterministic_model_like_adapter.py
```

The adapter accepts only this deterministic input shape:

```text
{"fixture_id": "<known fixture id>"}
```

The only accepted fixture in this phase is a safe structured proposal data
candidate. Unknown fixture ids, extra fixture input fields, non-mapping input,
and required rejection fixtures fail closed before raw output is released.

## Raw Output Surface

The safe fixture produces raw executor output candidate material only:

```text
action_type = PROPOSE_PATCH
declared_intent = deterministic proposal data
capability_requirements = ["propose_patch"]
payload = metadata-only proposal fields
```

The adapter does not return an `ActionDecisionPacket`. It does not submit a
completed packet-shaped object as trusted runtime packet data. Its output is
only candidate material for:

```text
raw executor output
-> executor_output_ingress
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
-> evidence/verify
-> metadata-only candidate where applicable
-> stop
```

Runtime-built `ActionDecisionPacket` creation remains owned only by
`executor_output_ingress`.

## Evidence Metadata

The adapter evidence records:

```text
adapter_is_no_provider = true
adapter_is_deterministic = true
adapter_output_is_raw_executor_output_only = true
adapter_output_is_action_decision_packet = false
provider_network_called = false
tool_runtime_enabled = false
tool_calls_allowed = false
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe_default = hold_current_state
provider_gate_required = true
```

## No-Tool Structure

The no-tool condition is structural metadata, not a trust claim:

```text
available_tools = ()
tool_schemas = ()
tool_runtime = disabled
tool_choice = none
max_tool_calls = 0
function_calling_allowed = false
shell_process_allowed = false
filesystem_mutation_allowed = false
provider_network_allowed_by_model_executor = false
runtime_internal_call_handles = ()
trusted_context_handles = ()
store_module_handles = ()
```

The adapter has no callable handles, no tool schema surface, no shell/process
surface, no filesystem mutation surface, no provider/network surface, no
trusted context handles, and no store module handles.

## Fail-Closed Fixtures

The deterministic rejection fixtures cover:

```text
malformed JSON text
scalar JSON
list JSON
missing required structured proposal fields
completed ActionDecisionPacket-shaped object
packet_id / created_by spoof
capability_gate_result self-report
execution_allowed=true
mutation_allowed=true
write_authority_granted=true
store_routing_allowed=true
store_path_reachable=true
tool_calls
function_call
command
cmd
shell
run
process
spawn
exec
eval
import
write_file
delete_file
move_file
apply_patch
store_write
ledger_append
runtime introspection
internal function call
provider request
network request
authority self-report
reported_only self-report
```

These fixtures fail closed before adapter output is returned. They are not
converted into trusted packets and do not reach a store route.

## Downstream Result

The accepted safe fixture is routed through `executor_output_ingress` by tests.
The downstream result is:

```text
parse_status = PARSE_OK
validation_status = VALID_STRUCTURED_ACTION
capability_gate_result = CAPABILITY_GATE_LIMITED_ALLOWED
packet_created_by = runtime_ingress_adapter
packet_runtime_built_by_ingress = true
store_adjacent_candidate_gate_metadata_only = true
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
```

Accepted downstream proposal material remains metadata-only. It is not action
execution, mutation, write authority, store routing, store path reachability,
or patch application.

## Authority Status

Current status remains:

```text
provider/model/network = NOT_STARTED / NOT_GRANTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store routing = NOT_GRANTED
store path reachability = NOT_GRANTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Phase 11-B-4-1 does not change `live_executor_authority` and does not change
the safe default.

## Non-Claims

This phase does not implement or claim:

```text
live provider integration
model/provider/network readiness
provider response parsing for live calls
tool runtime
tool calling
action execution engine
write authority
filesystem mutation by executor output
store write routing
store path reachability
patch application
autonomous loop
runtime internal access
public release material
```

Main merge:

```text
main merge = NOT_PERFORMED
```
