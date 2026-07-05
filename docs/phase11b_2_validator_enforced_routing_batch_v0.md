# Aegis Phase 11-B-2 Validator-Enforced Routing Implementation Batch v0

## 1. Scope

This batch implements the pre-live Phase 11-B-2 routing pieces:

- `11-B-2-2`: ActionDecisionPacket evidence binding.
- `11-B-2-3`: store-adjacent candidate guard for validated runtime-owned decision packets.
- `11-B-2-4`: rejection fixtures for raw, unvalidated, denied, and reported-only store-path attempts.

Implementation:

```text
src/evidence/action_decision_routing.py
tests/test_phase11b_validator_enforced_routing_batch.py
```

## 2. Required Flow

The implemented pre-live flow is:

```text
raw executor output
-> executor output ingress adapter
-> parse / normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-owned ActionDecisionPacket
-> ActionDecisionPacket evidence binding
-> verify_action_decision_packet_evidence
-> store-adjacent candidate gate metadata
-> stop
```

The guard does not call `store.py`, write `.aeg`, append the ledger, execute an
action, apply a patch, call a provider, use a network path, spawn a process, run
a command, evaluate code, import code dynamically, or grant write authority.

## 3. Evidence Binding

`bind_action_decision_packet_evidence` binds runtime-owned packet fields,
including:

```text
packet_id
packet_created_by
raw_output_hash
parse_status
validation_status
validation_valid
capability_gate_result
required_capabilities
decision_basis_hash
ignored_reported_only_fields
store_adjacent_candidate_eligible
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_ready = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe_default = hold_current_state
```

`verify_action_decision_packet_evidence` rejects evidence that overclaims:

```text
raw_executor_output_reaches_store = true
unvalidated_action_reaches_store = true
denied_capability_reaches_store = true
reported_only_authority_reaches_store = true
execution_allowed = true
mutation_allowed = true
write_authority_granted = true
live_executor_ready = true
```

When a runtime packet is supplied to verification, evidence fields must still
match the packet after hash rebinding.

## 4. Store-Adjacent Guard

`evaluate_store_adjacent_candidate_gate` accepts only a verified,
runtime-owned `ActionDecisionPacket` whose:

```text
parse_status = PARSE_OK
validation_status = VALID_STRUCTURED_ACTION
validation_valid = true
capability_gate_result in {CAPABILITY_GATE_ALLOWED, CAPABILITY_GATE_LIMITED_ALLOWED}
created_by = runtime_ingress_adapter
```

Acceptance means metadata-only candidate acceptance. It does not mean store
reachability or execution.

Fixed non-authority fields remain:

```text
store_routing_allowed = false
store_path_reachable = false
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
live_executor_ready = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## 5. Rejection Fixtures

The deterministic rejection fixture set covers:

```text
raw_executor_output -> RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED
unsupported_executor_output -> RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED
unvalidated_action_packet -> UNVALIDATED_ACTION_STORE_PATH_REJECTED
denied_capability_packet -> DENIED_CAPABILITY_STORE_PATH_REJECTED
reported_only_authority_packet -> REPORTED_ONLY_STORE_PATH_REJECTED
```

All fixture outputs preserve:

```text
candidate_accepted = false
store_adjacent_candidate = false
store_routing_allowed = false
store_path_reachable = false
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
live_executor_ready = false
safe_default = hold_current_state
```

## 6. Non-Goals

This batch does not implement:

- a live executor.
- an action execution engine.
- provider/model/network integration.
- shell, command, or process authority.
- write authority.
- unrestricted mutation.
- a bypass-impossibility proof.
- a tamper-proof runtime boundary.
- live executor readiness.
- a main merge.

Safe default remains:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```
