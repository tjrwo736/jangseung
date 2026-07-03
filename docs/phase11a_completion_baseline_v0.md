# Phase 11-A-4 completion baseline v0

## Purpose

Phase 11-A-4 records the deterministic completion baseline for Phase 11-A.
It binds the completed Phase 11-A-0, 11-A-1, 11-A-2, and 11-A-3 evidence
records into one replay-verifiable closure record.

## Phase 11-A roadmap position

| Roadmap item | Position |
| --- | --- |
| Phase 11-A-0 rollback / kill-path | preserved |
| Phase 11-A-1 save_run routing | deterministic pre-live evidence preserved |
| Phase 11-A-2 known-gap transition | internally recomputed blocked transition preserved |
| Phase 11-A-3 write-route evidence binding | deterministic cross-digest binding preserved |
| Phase 11-A-4 completion baseline | closure evidence only |
| Phase 11-B | `NOT_STARTED` |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |

## 11-A-4 scope

11-A-4 is completion baseline evidence. It is not Phase 11-B, not a live
executor, not an actual runtime write path, not actual enforcement, and not a
runtime write authority grant.

The module added for this phase is:

```text
src/evidence/phase11a_completion_baseline.py
```

The replay tests are:

```text
tests/test_phase11a_completion_baseline.py
```

## Completion baseline semantics

The baseline is accepted only when all four source records verify through
internal replay and the 11-A-3 binding proves the 11-A-0/1/2 chain by
deterministic source digests.

The accepted completion status is:

```text
PHASE11A_COMPLETION_BASELINE_ACCEPTED
```

Rejected status vocabulary includes:

```text
SOURCE_EVIDENCE_VERIFY_REJECTED
SOURCE_EVIDENCE_DIGEST_MISMATCH
COMPLETION_CHAIN_BINDING_REJECTED
PHASE11A_COMPLETION_BASELINE_REJECTED
```

## Source evidence requirements

The builder requires these source records:

```text
phase11a0_evidence
phase11a1_evidence
phase11a2_evidence
phase11a3_binding_evidence
```

The completion record stores deterministic digests for all four sources:

```text
source_phase11a0_digest
source_phase11a1_digest
source_phase11a2_digest
source_phase11a3_digest
```

The accepted source verify statuses are:

```text
phase11a0_verify_status = VERIFY_REPLAY_ACCEPTED
phase11a1_verify_status = VERIFY_REPLAY_ACCEPTED
phase11a2_verify_status = VERIFY_REPLAY_ACCEPTED
phase11a3_verify_status = EVIDENCE_BINDING_ACCEPTED
```

## Internal recompute verify rule

Caller-supplied verify objects are not acceptance authority. 11-A-4 recomputes
all source verifies internally:

```text
verify_phase11a_rollback_kill_path_evidence(phase11a0_evidence)
verify_phase11a_save_run_write_routing_evidence(phase11a1_evidence)
verify_phase11a_known_gap_blocked_transition_evidence(
    phase11a2_evidence,
    save_run_route_evidence=phase11a1_evidence,
)
verify_phase11a_write_route_evidence_binding(
    phase11a3_binding_evidence,
    phase11a0_evidence=phase11a0_evidence,
    phase11a1_evidence=phase11a1_evidence,
    phase11a2_evidence=phase11a2_evidence,
)
```

The record stores:

```text
source_verify_recomputed = true
source_verify_source = recomputed_internal_replay
supplied_verify_trusted = false
```

If a caller supplies a fake accepted verify for invalid source evidence, replay
still rejects the source evidence through internal recomputation.

## Closure chain binding

11-A-4 accepts the closure chain only when 11-A-3 verifies and its bound source
digests match the current 11-A-0/1/2 source digests:

```text
source_phase11a3_bound_phase11a0_digest == source_phase11a0_digest
source_phase11a3_bound_phase11a1_digest == source_phase11a1_digest
source_phase11a3_bound_phase11a2_digest == source_phase11a2_digest
completion_chain_binding_valid = true
completion_chain_binding_result = COMPLETION_CHAIN_BINDING_ACCEPTED
```

## Why this is not live enforcement

11-A-4 only produces deterministic closure evidence. It does not call
`save_run`, mutate runtime state, block a runtime write, activate a mediator,
activate filesystem enforcement, implement a live executor, call providers, use
network authority, or grant tool authority.

## Relation to 11-A-0/1/2/3

11-A-4 preserves these prior guarantees:

- 11-A-0 candidate success is not accepted as rollback evidence.
- 11-A-1 deterministic attribution is preserved.
- 11-A-1 self-reported or trusted-runtime attribution is rejected.
- 11-A-1 request_source spoofing is rejected.
- 11-A-1 mediator actor mismatch is rejected.
- 11-A-2 uses internally recomputed 11-A-1 verify only.
- 11-A-2 transition status remains `KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE`.
- 11-A-3 binding over 11-A-0/1/2 remains verified.

## Evidence schema

The completion record contains:

```text
record_kind
record_version
claim_type
phase11a_step
completion_status
completion_basis
completion_chain_binding_result
source_phase11a0_digest
source_phase11a1_digest
source_phase11a2_digest
source_phase11a3_digest
phase11a0_verify_status
phase11a1_verify_status
phase11a2_verify_status
phase11a3_verify_status
phase11a3_binding_status
source_verify_recomputed
source_verify_source
supplied_verify_trusted
supplied_verify_mismatch_rejected
completion_chain_binding_valid
phase11a3_deterministic_binding_verified
phase11a2_internal_route_verify_preserved
deterministic_attribution_preserved
spoof_rejection_preserved
known_gap_blocked_transition_preserved
fallback_preserved
candidate_success_rejected_as_rollback_evidence
runtime_write_path_status
live_executor_authority
phase11b_status
safe_default
actual_runtime_write_performed
actual_enforcement_activated
live_executor_implemented
runtime_write_authority_granted
tool_authority_granted
provider_model_network_authority_granted
os_filesystem_sandbox_container_hardening_claimed
current_authority_snapshot
source_verify_summary
source_verify_rejection_reasons
source_phase11a3_bound_phase11a0_digest
source_phase11a3_bound_phase11a1_digest
source_phase11a3_bound_phase11a2_digest
completion_rejection_reasons
non_claim_caveats
deterministic_evidence_digest
```

## Verify replay behavior

`verify_phase11a_completion_baseline()` rebuilds the expected baseline from
the supplied source records, recomputes all source verifies, compares every
schema field except the digest, checks source digests, checks overclaim flags,
and then recomputes the deterministic baseline digest.

Source tamper, source digest mismatch, rejected source verify, fake accepted
verify, 11-A-3 binding breakage, 11-A-2 supplied verify bypass, attribution
spoofing, runtime authority overclaim, Phase 11-B claim, actual runtime write
claim, actual enforcement claim, and OS/filesystem/sandbox/container hardening
claim all reject replay.

## Accepted and rejected statuses

Accepted:

```text
PHASE11A_COMPLETION_BASELINE_ACCEPTED
```

Rejected:

```text
SOURCE_EVIDENCE_VERIFY_REJECTED
SOURCE_EVIDENCE_DIGEST_MISMATCH
COMPLETION_CHAIN_BINDING_REJECTED
PHASE11A_COMPLETION_BASELINE_REJECTED
```

## Rejected overclaims

11-A-4 rejects claims of:

- runtime write authority grant
- live executor authority grant
- Phase 11-B start
- actual runtime write
- actual enforcement
- live executor implementation
- tool authority grant
- provider, model, or network authority grant
- raw shell, write_file, run_command, or process_spawn authority grant
- OS/filesystem/sandbox/container hardening

## Current authority

The current authority snapshot remains:

```text
runtime_write_path_status = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
phase11b_status = NOT_STARTED
safe_default = hold_current_state
```

## Explicit non-claims

This baseline does not claim:

- Phase 11-B implementation or start.
- Live executor implementation.
- Actual runtime write.
- Actual save_run runtime write.
- Actual blocking or enforcement activation.
- Runtime write authority grant.
- Tool/provider/model/network authority grant.
- Raw shell/write_file/run_command/process_spawn authority grant.
- OS/filesystem/sandbox/container hardening.
- Executor-isolated evidence storage.

## Handoff to Phase 11-B gate

11-A-4 hands off a deterministic completion baseline. Phase 11-B remains a
future gate and must separately authorize any live executor, runtime write path,
or enforcement behavior.

## Safe default

The safe default remains:

```text
hold_current_state
```
