# Aegis Phase 11-B-3-6 Store-Adjacent Runtime Seal v0

## Purpose

This document records the Phase 11-B-3-6 store-adjacent runtime seal.

Completion label:

```text
PHASE11B_3_STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_NOT_MODEL
```

Required limits:

```text
NOT_MODEL_EXECUTOR
NOT_PROVIDER_READY
NOT_ACTION_EXECUTION_ENGINE
NOT_WRITE_AUTHORITY
NOT_PATCH_APPLY
NOT_BYPASS_IMPOSSIBLE
NOT_TAMPER_PROOF
STRUCTURED_EXECUTOR_ASSUMPTION_REQUIRED
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Forced Runtime Path

The accepted store-adjacent path is:

```text
raw executor output
-> executor_output_ingress
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
-> evidence/verify
-> metadata-only store-adjacent candidate guard
-> store-adjacent decision
-> stop
```

No raw executor output, packet-shaped dict, direct packet evidence, direct
store-adjacent candidate dict, unvalidated action, denied capability, or
reported-only authority field is accepted as store-adjacent candidate material.

## Store Sink Boundary

The `src/state/store.py` write sinks remain guarded:

- `_write_json` before `Path.write_text`
- `_append_ledger_unmediated` before append-mode ledger writes

Executor-attributed direct writes through these sinks are blocked before disk
mutation. Traversal-shaped `.aeg` targets are blocked by the same sink guard.
Forged ledger appends are blocked before a ledger entry is added.

Measured evidence fields:

```text
store_adjacent_runtime_seal_enabled = true
runtime_build_packet_only_enforced = true
packet_origin_basis = runtime_build_path
direct_packet_submission_rejected = true
executor_built_packet_rejected = true
raw_store_sink_bypass_rejected = measured from store.py sink events
direct_write_json_bypass_created_files_count = 0
direct_ledger_bypass_appended_count = 0
trusted_runtime_write_preserved = true
trusted_runtime_ledger_preserved = true
sealing_failure_fallback_status = NO_FALLBACK_USED
```

Trusted runtime `save_run` still writes `run.json`, `evidence.json`, and
`manifest.json`. Trusted runtime ledger append still succeeds. The ledger chain
remains replay-verified by the existing ledger integrity verifier.

## Packet Origin

Runtime ownership is based on the runtime build path, not text fields.

Rejected:

- completed packet-shaped dict submission
- direct packet evidence submission
- `created_by` text spoof
- `packet_id` text spoof
- executor-built `ActionDecisionPacket` with runtime-looking text
- capability gate self-report
- execution, mutation, write, store-route, store-path, or live-authority
  self-report
- live authority promotion self-report

Accepted store-adjacent candidates remain metadata-only:

```text
accepted_store_adjacent_candidate_metadata_only = true
accepted_store_adjacent_candidate_execution_allowed = false
accepted_store_adjacent_candidate_mutation_allowed = false
accepted_store_adjacent_candidate_write_authority_granted = false
accepted_store_adjacent_candidate_store_routing_allowed = false
accepted_store_adjacent_candidate_store_path_reachable = false
```

## Verify Rejections

`aeg verify` rejects rehashed evidence that claims:

- direct packet submission was accepted
- executor-built packet was runtime-built
- `created_by` or `packet_id` text proves ownership
- raw output reached the store-adjacent path
- unvalidated, denied, or reported-only paths reached the store-adjacent guard
- execution, mutation, write, store routing, store path, or live authority was
  granted
- live executor authority was promoted
- a direct write bypass created files
- a forged ledger append added entries
- trusted runtime write preservation failed while success was claimed
- trusted runtime ledger preservation failed while success was claimed
- sealing failed while success was claimed
- fallback was used while success was claimed

The seal evidence is bound into `STORE_WRITE_MEDIATION_FIELDS`, the run
manifest, and the ledger-backed evidence hash group.

## Non-Claims

This phase is not:

```text
model executor
provider/model/network readiness
action execution engine
write authority
mutation authority
patch application
public release
autonomous loop
process/OS isolation
sandbox/container/IPC boundary
tamper-proof store
arbitrary-code safety
physical impossibility proof
```

Main merge:

```text
main merge = NOT_PERFORMED
```
