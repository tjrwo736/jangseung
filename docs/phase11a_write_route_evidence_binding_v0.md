# Phase 11-A-3 write-route evidence binding v0

## Purpose

Phase 11-A-3 binds Phase 11-A-0 rollback evidence, Phase 11-A-1 pre-live
`save_run` route evidence, and Phase 11-A-2 known-gap blocked transition
evidence into one deterministic replay record.

This is evidence binding and replay verification only.

## Phase 11-A roadmap position

| Item | Status |
| --- | --- |
| Phase 11-A-0 rollback / kill-path | preserved |
| Phase 11-A-1 save_run routing | deterministic pre-live evidence preserved |
| Phase 11-A-2 known-gap transition | blocked transition evidence preserved |
| Phase 11-A-3 write-route evidence binding | cross-digest replay binding |
| Phase 11-B | `NOT_STARTED` |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Safe default | `hold_current_state` |

## 11-A-3 scope

11-A-3 adds:

- a deterministic binding record for 11-A-0, 11-A-1, and 11-A-2 evidence.
- internal replay verification of each source evidence record.
- cross-digest checks between 11-A-0 fallback evidence, 11-A-1 route evidence,
  and 11-A-2 transition evidence.
- replay rejection for caller-supplied verify bypasses, attribution spoofing,
  authority overclaims, runtime write claims, and enforcement claims.

11-A-3 does not add a live executor, actual runtime write, actual `save_run()`
write, runtime blocking, enforcement activation, provider/model/network
authority, raw command authority, or Phase 11-B behavior.

## Evidence chain binding semantics

The accepted binding is:

```text
phase11a_step = 11-A-3
binding_record_kind = phase11a_write_route_evidence_binding
binding_version = phase11a_write_route_evidence_binding_v0
binding_status = EVIDENCE_BINDING_ACCEPTED
binding_basis = phase11a_prelive_cross_digest_replay
```

The binding is accepted only when all three source evidence records replay
successfully and the binding record matches the recomputed deterministic
record.

## Source evidence requirements

The required inputs are:

- Phase 11-A-0 rollback / kill-path evidence.
- Phase 11-A-1 pre-live `save_run` route evidence.
- Phase 11-A-2 known-gap blocked transition evidence.

The source requirements are:

- 11-A-0 verifies with `VERIFY_REPLAY_ACCEPTED`.
- 11-A-1 verifies with `VERIFY_REPLAY_ACCEPTED`.
- 11-A-2 verifies with `VERIFY_REPLAY_ACCEPTED`.
- 11-A-1 fallback evidence digest matches the 11-A-0 source digest.
- 11-A-2 `save_run_route_evidence_digest` matches the 11-A-1 source digest.
- 11-A-2 remains based on internally recomputed 11-A-1 route replay.
- 11-A-1 deterministic attribution remains intact.
- 11-A-2 known-gap transition status remains
  `KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE`.

## Internal recompute verify rule

11-A-3 recomputes source verify results internally:

```text
verify_phase11a_rollback_kill_path_evidence(phase11a0_evidence)
verify_phase11a_save_run_write_routing_evidence(phase11a1_evidence)
verify_phase11a_known_gap_blocked_transition_evidence(
    phase11a2_evidence,
    save_run_route_evidence=phase11a1_evidence,
)
```

Caller-supplied verify objects are not acceptance authority. If supplied verify
summaries disagree with internally recomputed summaries, replay rejects.

## Cross-digest binding

The binding records the three source digests:

```text
source_phase11a0_digest
source_phase11a1_digest
source_phase11a2_digest
```

Replay recomputes all three digests from the current source evidence inputs.
Any mismatch rejects.

The cross-source chain is:

```text
phase11a1.fallback_evidence digest == source_phase11a0_digest
phase11a2.save_run_route_evidence_digest == source_phase11a1_digest
```

This prevents a valid source evidence object from being swapped into an
unrelated binding chain.

## Why this is not live enforcement

11-A-3 validates evidence relationships only. It does not make a runtime policy
decision, block a runtime write, perform a filesystem mutation, create an
executor, or claim OS/filesystem/sandbox/container hardening.

No `.aeg` write is made. No ledger write is made. No `.env`, secret, provider,
model, or network authority is read or granted.

## Relation to 11-A-0 fallback

11-A-3 requires the 11-A-0 evidence to replay successfully and requires the
11-A-1 fallback evidence digest to match that source. Candidate wired-path
success is still rejected as rollback proof.

The preserved fallback state is:

```text
runtime_write_path = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
safe_default = hold_current_state
write_performed = false
```

## Relation to 11-A-1 deterministic attribution

11-A-3 requires the 11-A-1 deterministic attribution tuple:

```text
write_attribution_type = executor_attributed
write_attribution_basis = deterministic_adapter_context
write_attribution_source = phase11a_save_run_pre_live_adapter
```

Self-reported attribution, trusted-runtime self-claims, `request_source`
spoofing, and mediator actor mismatch remain rejected by replay.

## Relation to 11-A-2 blocked transition

11-A-3 requires 11-A-2 to preserve:

```text
known_gap_transition_status = KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE
save_run_route_verify_source = recomputed_internal_replay
supplied_route_verify_trusted = false
route_verify_recomputed = true
```

The 11-A-2 evidence must verify against the supplied 11-A-1 evidence by
internal replay recomputation.

## Evidence schema

The 11-A-3 binding record includes:

- `phase11a_step`
- `binding_record_kind`
- `binding_version`
- `source_phase11a0_digest`
- `source_phase11a1_digest`
- `source_phase11a2_digest`
- `phase11a0_verify_status`
- `phase11a1_verify_status`
- `phase11a2_verify_status`
- `binding_status`
- `binding_basis`
- `source_verify_recomputed`
- `source_verify_source`
- `supplied_verify_trusted`
- `supplied_verify_mismatch_rejected`
- `cross_digest_binding_valid`
- `deterministic_attribution_preserved`
- `known_gap_blocked_transition_preserved`
- `fallback_preserved`
- `runtime_write_path_status`
- `live_executor_authority`
- `phase11b_status`
- `safe_default`
- `actual_runtime_write_performed`
- `actual_enforcement_activated`
- `live_executor_implemented`
- `tool_authority_granted`
- `provider_model_network_authority_granted`
- `os_filesystem_sandbox_container_hardening_claimed`
- `authority_snapshot`
- `source_verify_summary`
- `source_verify_rejection_reasons`
- `source_phase11a1_bound_phase11a0_digest`
- `source_phase11a2_bound_phase11a1_digest`
- `binding_rejection_reasons`
- `non_claim_caveats`
- `deterministic_evidence_digest`

## Verify replay behavior

Replay verification rejects:

- schema mismatches and unexpected fields.
- binding digest mismatch.
- any source evidence digest mismatch.
- source evidence tamper.
- any source verify rejection.
- caller-supplied verify mismatch.
- a fake supplied accepted verify for invalid source evidence.
- 11-A-2 evidence that no longer verifies against the 11-A-1 evidence.
- known-gap blocked transition mismatch.
- deterministic attribution mismatch.
- self-reported attribution accepted state.
- trusted-runtime self-claim accepted state.
- `request_source` spoof accepted state.
- mediator actor mismatch accepted state.
- candidate success treated as 11-A-0 rollback evidence.
- runtime write authority overclaim.
- live executor authority grant claim.
- Phase 11-B start claim.
- actual runtime write claim.
- actual enforcement claim.
- OS/filesystem/sandbox/container hardening claim.

## Accepted statuses

The binding status vocabulary is:

- `EVIDENCE_BINDING_READY`
- `EVIDENCE_BINDING_ACCEPTED`
- `EVIDENCE_BINDING_REJECTED`
- `SOURCE_EVIDENCE_VERIFY_REJECTED`
- `SOURCE_EVIDENCE_DIGEST_MISMATCH`

Only `EVIDENCE_BINDING_ACCEPTED` is an accepted replay result.

## Rejected overclaims

11-A-3 rejects claims that imply:

- runtime write authority has been granted.
- live executor authority has been granted.
- Phase 11-B has started.
- actual runtime write has occurred.
- actual enforcement has been activated.
- a live executor has been implemented.
- tool authority has been granted.
- provider, model, or network authority has been granted.
- OS/filesystem/sandbox/container hardening has been established.

## Current authority

The current authority snapshot remains:

```text
runtime_write_path_status = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
phase11b_status = NOT_STARTED
safe_default = hold_current_state
```

## Explicit non-claims

11-A-3 does not claim:

- actual runtime write.
- actual `save_run()` runtime write.
- runtime write blocking.
- enforcement activation.
- live executor readiness.
- runtime write authority.
- provider/model/network authority.
- raw shell, write-file, command runner, or process-spawn authority.
- OS/filesystem/sandbox/container hardening.
- `.aeg`, ledger, `.env`, secret, or runtime artifact tracking.
- Phase 11-B start or implementation.

## Handoff to 11-A-4

11-A-4 can consume the 11-A-3 binding as deterministic evidence that the
pre-live 11-A-0/1/2 evidence chain is internally consistent. 11-A-4 must still
avoid treating this binding as live runtime authority or enforcement.

## Safe default

The safe default remains:

```text
hold_current_state
```
