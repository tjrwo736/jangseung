# Aegis Phase 11-B-2-1 Executor Output Ingress Adapter Scaffold v0

## 1. Purpose

Phase 11-B-2-1 adds a pre-live ingress adapter for fixture executor output.
The adapter treats executor output as data, not code, and produces a
runtime-owned `ActionDecisionPacket`.

The flow is intentionally narrow:

```text
raw executor output
-> parse / normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-owned ActionDecisionPacket
-> stop
```

Implementation:

```text
src/evidence/executor_output_ingress.py
tests/test_phase11b_executor_output_ingress_adapter.py
```

## 2. Scope

Allowed inputs are limited to:

```text
test fixture dict
test fixture JSON string
predefined raw output sample
```

The adapter does not connect to a live executor, model provider, action
execution engine, process boundary, sandbox, IPC channel, store routing guard,
or write mediation path.

## 3. Packet Contract

`ActionDecisionPacket` is created by the runtime ingress adapter, not by the
executor. Its contract records:

```text
packet_id
raw_output_hash
parse_status
parse_error
normalized_action
validation_result
capability_result
decision_basis
ignored_reported_only_fields
adapter_version
execution_allowed
mutation_allowed
write_authority_granted
store_routing_allowed
store_path_reachable
live_executor_authority
safe_default
created_by
```

The runtime-owned constants are:

```text
created_by = runtime_ingress_adapter
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe_default = hold_current_state
```

`ActionDecisionPacket` is not an executor self-report.

## 4. Parse / Normalize

The adapter accepts fixture dictionaries and fixture JSON strings. Malformed
JSON returns a packet with:

```text
parse_status = PARSE_FAILED
validation_result = None
capability_result = None
safe_default = hold_current_state
```

Wrapper metadata outside the structured action is not authority. Runtime-like
or executor-reported fields such as `created_by`, `execution_allowed`,
`write_authority_granted`, `live_executor_authority`, and `reported_only` are
recorded in `ignored_reported_only_fields` and not trusted.

## 5. Validation

After parsing and normalization, the adapter calls:

```text
validate_structured_action
```

Validation answers only whether the normalized action is valid structured
action data. It does not execute the action, apply a patch, mutate files, grant
write authority, route to the store, or make the live executor ready.

Important non-equivalence:

```text
validator pass != execution
validator pass != mutation
validator pass != write authority
```

## 6. Capability Gate

After validation, the adapter calls:

```text
evaluate_action_capabilities
```

Capability evaluation answers only whether the action's declared capabilities
pass the current non-executing gate policy. A gate pass remains data-only.

Important non-equivalence:

```text
capability gate pass != execution
capability gate pass != mutation
capability gate pass != write authority
capability gate pass != store reachability
```

`PROPOSE_PATCH` remains a proposal packet. It is not a repo mutation and does
not grant `write_file`, mediated write, direct store, ledger append, or runtime
write authority.

## 7. Self-Report Handling

Raw executor output is never accepted as a trusted decision or authority grant.

Wrapper self-report fields are ignored and recorded. Self-report fields inside
the structured action remain visible to the capability gate and are rejected
under the existing `reported_only` / executor self-claim policy.

Non-authority rules:

```text
reported_only != judgment basis
executor self-report != capability grant
raw output != trusted decision
ActionDecisionPacket != executor self-report
```

## 8. Store Non-Reachability

This scaffold does not import or call `src/state/store.py`. It does not add a
store-adjacent routing guard and does not create a path to store writes.

Every packet records:

```text
store_routing_allowed = false
store_path_reachable = false
```

## 9. Pre-Live Authority

The live executor remains on hold:

```text
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe_default = hold_current_state
```

Main merge is not part of this phase:

```text
main merge = NOT_PERFORMED
```
