# Phase 11-A-2 known-gap blocked transition v0

## Purpose

Phase 11-A-2 records a replayable transition from a known-gap expected-red
baseline to blocked transition evidence. The transition is accepted only when it
is grounded in verified Phase 11-A-1 pre-live `save_run` route evidence.

This is evidence validation only.

## Phase 11-A roadmap position

| Item | Status |
| --- | --- |
| Phase 11-A-0 rollback / kill-path | preserved |
| Phase 11-A-1 save_run routing | deterministic pre-live evidence preserved |
| Phase 11-A-2 known-gap transition | blocked transition evidence |
| Phase 11-B | `NOT_STARTED` |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Safe default | `hold_current_state` |

## 11-A-2 scope

11-A-2 adds:

- a deterministic known-gap transition evidence record.
- replay verification for the transition evidence.
- strict dependence on 11-A-1 route evidence replay.
- strict preservation of 11-A-0 fallback evidence.
- strict rejection of authority, enforcement, runtime-write, and Phase 11-B
  overclaims.

11-A-2 does not add a live executor, live write path, actual write blocking,
provider/model/network authority, or Phase 11-B behavior.

## known-gap expected-red baseline

The prior transition input is:

```text
prior_known_gap_status = KNOWN_GAP_EXPECTED_RED_BASELINE
prior_known_gap_contract_status = B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE
```

The prior state means the gap was known and expected to remain red before this
phase. It does not mean the gap was already closed by runtime behavior.

## blocked transition semantics

The accepted transition output is:

```text
known_gap_transition_status = KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE
transition_basis = phase11a1_verified_prelive_save_run_route
transition_source_phase = 11-A-1
```

The transition is accepted only when all of these are true:

- 11-A-1 route evidence verifies.
- write attribution basis is `deterministic_adapter_context`.
- write attribution type is `executor_attributed`.
- self-reported attribution is rejected.
- trusted-runtime self-claim is rejected.
- `request_source` spoofing is rejected.
- mediator actor mismatch is rejected.
- route target is `SAVE_RUN_ROUTE_GUARD_MEDIATOR_COMPATIBLE`.
- guard decision status is `DENIED_BY_B1_AEG_INTEGRITY_GUARD`.
- route status is `SAVE_RUN_ROUTE_ACCEPTED_PRELIVE`.
- 11-A-0 fallback evidence verifies.
- runtime write path remains `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- live executor authority remains `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- Phase 11-B remains `NOT_STARTED`.
- no actual runtime write is recorded.

## why this is not live enforcement

Blocked transition evidence means the known-gap is classified as blocked under
the verified 11-A-1 pre-live route evidence. It does not claim OS, filesystem,
sandbox, container, runtime, or executor enforcement.

No `save_run()` call is made. No `.aeg` write is made. No ledger write is made.
No runtime write path is wired or granted. No live executor authority is
promoted.

## relation to 11-A-0 fallback

11-A-2 requires nested 11-A-0 fallback evidence to replay successfully.
Candidate wired-path success is still rejected as 11-A-0 rollback proof.

The fallback result must continue to record:

```text
runtime_write_path = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
safe_default = hold_current_state
write_performed = false
```

## relation to 11-A-1 deterministic attribution

11-A-2 does not create a new attribution path. It consumes the 11-A-1
deterministic adapter attribution:

```text
write_attribution_type = executor_attributed
write_attribution_basis = deterministic_adapter_context
write_attribution_source = phase11a_save_run_pre_live_adapter
```

Caller-controlled attribution, trusted-runtime self-claims, request metadata
self-claims, `request_source` spoofing, and mediator actor mismatch remain
rejected by replay.

## evidence schema

The 11-A-2 evidence record includes:

- `phase11a_step`
- `prior_known_gap_status`
- `prior_known_gap_contract_status`
- `known_gap_transition_status`
- `transition_basis`
- `transition_source_phase`
- `save_run_route_evidence_digest`
- `save_run_route_evidence_verified`
- `save_run_route_verify_status`
- `deterministic_attribution_verified`
- `self_reported_attribution_rejected`
- `trusted_runtime_self_claim_rejected`
- `request_source_spoof_rejected`
- `mediator_actor_mismatch_rejected`
- `route_target_verified`
- `guard_decision_verified`
- `route_status_verified`
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
- `authority_snapshot`
- `source_route_verify`
- `transition_rejection_reasons`
- `non_claim_caveats`
- `deterministic_evidence_digest`

## verify replay behavior

Replay verification rejects:

- schema mismatches and unexpected fields.
- deterministic digest mismatch.
- prior known-gap status mismatch.
- transition status mismatch.
- route evidence verify mismatch.
- deterministic attribution mismatch.
- self-reported attribution accepted state.
- trusted-runtime self-claim accepted state.
- `request_source` spoof accepted state.
- mediator actor mismatch accepted state.
- route target mismatch.
- guard decision mismatch.
- fallback preservation mismatch.
- candidate wired-path success treated as rollback evidence.
- runtime write authority overclaim.
- live executor authority grant claim.
- Phase 11-B claim.
- actual enforcement or runtime-write overclaim.

## accepted statuses

The status vocabulary is:

- `KNOWN_GAP_EXPECTED_RED_BASELINE`
- `KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE`
- `KNOWN_GAP_TRANSITION_NOT_APPLICABLE`
- `KNOWN_GAP_TRANSITION_REJECTED`
- `KNOWN_GAP_TRANSITION_VERIFY_REJECTED`

Only `KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE` is an accepted 11-A-2 transition
result.

## rejected overclaims

11-A-2 rejects claims that imply:

- runtime write authority has been granted.
- live executor authority has been granted.
- Phase 11-B has started.
- actual enforcement has been activated.
- an actual runtime write was performed.
- provider, model, or network authority has been granted.
- raw shell, write-file, command runner, or process-spawn authority has been
  granted.
- the `save_run` route has become a live runtime write path.

## current authority

Current authority remains:

```text
runtime write path = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
live executor authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
Phase 11-B = NOT_STARTED
safe default = hold_current_state
```

## explicit non-claims

11-A-2 makes no claim of:

- live executor implementation.
- Phase 11-B implementation.
- actual runtime write blocking.
- actual `save_run()` runtime write.
- raw shell, write-file, command runner, process-spawn, provider, model,
  network, or runtime write authority grant.
- OS, filesystem, sandbox, or container hardening.
- `.aeg`, ledger, `.env`, secret, or runtime artifact mutation.
- main merge, release, deploy, or ready-for-review transition.

## handoff to 11-A-3

11-A-3 may consume the blocked transition evidence as a verified pre-live
classification. Any future step must still preserve the authority snapshot and
must not treat this evidence as runtime enforcement.

## safe default

```text
safe default = hold_current_state
```
