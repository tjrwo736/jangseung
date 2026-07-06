# Aegis Phase 11-B-3-1 Structural Contract Enforcement v0

## 1. Purpose

Phase 11-B-3-1 implements restricted propose-only structural enforcement for
the Phase 11-B-3 entry gate.

This batch is limited to local packet provenance, evidence verification, and
store-adjacent metadata guard hardening. It does not add a provider, model,
network path, live executor, action execution engine, store write path, patch
apply path, or write authority.

Safe default remains:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## 2. Enforced Runtime Packet Contract

`ActionDecisionPacket` now records whether it was built by
`ingest_executor_output`. Evidence binding includes
`packet_runtime_built_by_ingress`, and evidence verification rejects records
that do not supply the matching runtime packet object.

Executor-provided packet-shaped material is rejected as input data:

```text
direct ActionDecisionPacket-shaped dict -> DIRECT_PACKET_SUBMISSION_PARSE_REJECTED
direct packet evidence dict -> DIRECT_PACKET_EVIDENCE_SUBMISSION_PARSE_REJECTED
direct store-adjacent candidate dict -> DIRECT_STORE_ADJACENT_CANDIDATE_PARSE_REJECTED
```

The runtime-built packet remains data-only:

```text
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
```

## 3. Self-Report Rejection

Executor self-report is not authority. The ingress adapter strips or records
self-reported runtime, capability, eligibility, and store fields as ignored
input metadata. Store-adjacent eligibility now requires no ignored self-report
fields.

Covered self-report rejection fixtures include:

```text
created_by=runtime_ingress_adapter
packet_id=<spoofed>
capability_gate_result=CAPABILITY_GATE_ALLOWED
execution_allowed=true
mutation_allowed=true
write_authority_granted=true
store_routing_allowed=true
store_path_reachable=true
```

These fields do not become packet authority, capability authority, execution
authority, mutation authority, write authority, or store reachability.

## 4. Store-Adjacent Guard

The store-adjacent guard accepts only metadata derived from a verified
runtime-built packet. It rejects:

```text
raw output skipping ingress
unvalidated action reaching the store-adjacent path
denied capability reaching the store-adjacent path
reported_only authority reaching the store-adjacent path
direct packet-shaped dict reaching the store-adjacent path
direct store-adjacent candidate dict reaching the store-adjacent path
forged ActionDecisionPacket reaching the store-adjacent path
self-reported authority fields reaching the store-adjacent path
```

Accepted candidate status remains metadata-only and terminal. It does not make
the store path reachable.

## 5. Rule Summary

The implemented checks preserve these rules:

```text
executor self-report is not authority
reported_only is not judgment basis
valid structured action != authorized capability
authorized capability != action executed
PROPOSE_PATCH != write
PROPOSE_PATCH != mutation
metadata-only candidate != store write
store-adjacent metadata != store path reachability
ActionDecisionPacket remains runtime-built
store-adjacent candidate remains metadata-only
```

## 6. Out Of Scope

This batch does not implement:

```text
deterministic stub executor
proposal evidence binding
provider/model/network integration
live executor authority promotion
action execution engine
filesystem mutation path
store write execution
direct patch apply
shell/process/run command surface
eval/exec/dynamic import execution path
runtime introspection path
autonomous loop
```
