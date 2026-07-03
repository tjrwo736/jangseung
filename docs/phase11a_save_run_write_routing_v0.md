# Phase 11-A-1 save_run write routing v0

## Purpose

Phase 11-A-1 adds a pre-live routing line for the `save_run` write path. It
models a `save_run` target write as an in-memory request, converts that request
into guard/mediator-compatible input, and records replayable evidence for the
route decision.

## Phase 11-A roadmap position

| Item | Status |
| --- | --- |
| Phase 11-A-0 rollback / kill-path | ready and reused |
| Phase 11-A-1 save_run routing | pre-live evidence scaffold |
| Phase 11-B | `NOT_STARTED` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Safe default | `hold_current_state` |

## 11-A-1 scope

11-A-1 is limited to pre-live `save_run` routing evidence:

- build an in-memory `SaveRunWriteRequest`.
- route the expected `.aeg/runs/<run_id>/<target>` target through the B1 guard.
- convert the guarded result into a `WriteMediationRequest`.
- call the deny-only mediator skeleton or a test double.
- record allow/deny/failure/fallback route state as evidence.
- verify replay by checking schema, digest, route target, guard decision,
  fallback fields, deterministic write attribution, and authority
  preservation.

## deterministic write attribution

11-A-1 treats this route as an executor-attributed pre-live write route. The
accepted attribution basis is deterministic adapter context:

```text
write_attribution_type = executor_attributed
write_attribution_basis = deterministic_adapter_context
write_attribution_source = phase11a_save_run_pre_live_adapter
deterministic_entrypoint = phase11a_save_run_pre_live_adapter
write_attribution_is_self_reported = false
trusted_runtime_claim_allowed = false
executor_self_claim_used = false
```

Executor-attributed versus trusted-runtime write status is not accepted from a
caller, executor, request payload, route result, or metadata self-report.
`request_source` remains a canonical replay field only; it is not the basis for
mediator actor selection and must equal the deterministic adapter source.

Trusted-runtime internal writes require a separate future deterministic
entrypoint and scope. This PR does not add that scope, and an executor request
payload cannot claim `trusted_runtime_internal`.

## save_run routing design

`src/state/store.py::save_run` is the real state recorder. It writes run,
evidence, manifest, and ledger records under `.aeg`. Phase 11-A-1 does not call
that function and does not replace it.

The new adapter in `src/evidence/phase11a_save_run_write_routing.py` only
models one expected target at a time. The default request target is:

```text
.aeg/runs/<run_id>/run.json
```

The payload is digested, not written. The route result is an in-memory record
that can be tested with a deterministic mediator double.

## guard/mediator adapter boundary

The adapter boundary is:

1. `SaveRunWriteRequest`
2. `decide_b1_aeg_integrity_guard(...)`
3. `WriteMediationRequest`
4. deny-only mediator skeleton or injected test double
5. deterministic 11-A-1 evidence record

The guard and mediator records remain compatibility signals. They do not prove
runtime mediation, runtime enforcement, filesystem hardening, or executor
isolation.

The mediator actor is derived from the deterministic adapter context, not from a
caller-controlled request field. Avoiding self-mediation in this pre-live
adapter does not create a guard bypass.

## fallback / kill-path integration with 11-A-0

11-A-1 reuses `src/evidence/phase11a_rollback_kill_path.py`.

When the mediator route returns a failure-like result or raises an exception,
11-A-1 records:

- `save_run_route_status = SAVE_RUN_ROUTE_FAILED_FALLBACK_USED`
- `save_run_route_target = existing_unwired_path`
- `fallback_triggered = true`
- a nested 11-A-0 rollback evidence record
- a nested 11-A-0 replay verification summary

Successful pre-live routing is not treated as accepted 11-A-0 rollback
evidence. The 11-A-1 record has a separate record kind and claim type.

## evidence schema

Required evidence fields:

- `phase11a_step`
- `save_run_route_attempted`
- `save_run_route_status`
- `save_run_route_target`
- `mediator_route_used`
- `guard_decision_status`
- `fallback_available`
- `fallback_triggered`
- `fallback_reason`
- `runtime_write_path_status`
- `live_executor_authority`
- `phase11b_status`
- `safe_default`
- `known_gap_status`
- `write_attribution_type`
- `write_attribution_basis`
- `write_attribution_source`
- `write_attribution_is_self_reported`
- `trusted_runtime_claim_allowed`
- `executor_self_claim_used`
- `deterministic_entrypoint`
- `attribution_spoofing_rejected`
- `request`
- `guard_decision`
- `mediator_request`
- `mediator_decision`
- `route_result`
- `fallback_evidence`
- `fallback_verify`
- `authority_snapshot`
- `non_claim_caveats`
- `deterministic_evidence_digest`

## verify replay behavior

Replay verification rejects:

- schema mismatches and unexpected fields.
- deterministic digest mismatch.
- route target mismatch.
- guard decision mismatch.
- fallback field mismatch.
- attribution source, basis, entrypoint, request source, or mediator actor
  mismatch.
- request metadata or route result claims to be `trusted_runtime_internal`.
- self-reported attribution claims.
- executor self-claim usage.
- trusted-runtime claim allowance.
- runtime authority overclaims.
- live executor authority promotion claims.
- Phase 11-B start claims.
- `save_run` routing overclaims.

## accepted statuses

The accepted route status vocabulary is:

- `SAVE_RUN_ROUTE_NOT_ATTEMPTED`
- `SAVE_RUN_ROUTE_PRELIVE_READY`
- `SAVE_RUN_ROUTE_ATTEMPTED`
- `SAVE_RUN_ROUTE_FAILED_FALLBACK_USED`
- `SAVE_RUN_ROUTE_REJECTED_BY_GUARD`
- `SAVE_RUN_ROUTE_ACCEPTED_PRELIVE`

## rejected overclaims

Replay rejects claims that imply:

- the `save_run` path has become a live write path.
- runtime write authority has been granted.
- live executor authority has been promoted.
- Phase 11-B has started.
- provider, model, or network authority has been granted.
- raw shell, generic file mutation, or command runner authority has been
  granted.
- actual enforcement has been activated.
- trusted-runtime internal write status was accepted from request payload,
  metadata, route result, caller, or executor self-report.

## known-gap preservation

The evidence preserves:

```text
known_gap_status = B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE
```

11-A-1 keeps the known-gap expected-red state unchanged. Any transition
handling remains Phase 11-A-2 scope.

## what 11-A-1 does not do

11-A-1 does not:

- implement a live executor.
- implement a model-backed executor.
- grant raw shell, write_file, run_command, or process-spawn capability.
- grant provider, model, or network authority.
- grant runtime write authority.
- treat caller or executor self-report as trusted-runtime authority.
- allow self-mediation avoidance to become a guard bypass.
- implement Phase 11-B.
- change `src/cli/main.py`, `src/agents`, or `pyproject.toml`.
- write `.aeg`, `.env`, ledger, secret, or runtime artifact files.
- activate enforcement or harden OS/filesystem/sandbox/container behavior.

## handoff to 11-A-2

11-A-2 can consume this adapter as a pre-live evidence line. The next phase
must still decide how known-gap expected-red evidence transitions, if at all.
This document does not make that transition.

## current authority

```text
runtime_write_path_status = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
phase11b_status = NOT_STARTED
safe_default = hold_current_state
```

## explicit non-claims

The evidence is a route scaffold only. It is not proof of complete mediation,
not proof of enforcement, not a capability grant, not a filesystem hardening
claim, and not a Phase 11-B start.

## safe default

The safe default remains:

```text
hold_current_state
```
