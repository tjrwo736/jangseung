# B2-1 Executor Write Routing Through Mediator Guard Path v0

## Summary

B2-1 adds a pre-live routing component for executor-like write requests. The
component models the requested target path, intended operation, payload digest
or metadata, request source, and authority state before any file mutation.

Protected `.aeg/` targets are routed through a guard/mediator-compatible path:

- B1-B `.aeg` deny-only guard decision.
- B1-C guard evidence binding and no-mutation observation.
- Phase 10-E deny-only mediator request/decision model.

The routed result is a denial/no-mutation record. It does not claim direct
filesystem prevention, runtime authority, external enforcement, or executor
isolation.

## Scope

In scope:

- `src/evidence/b2_executor_write_router.py`
- `tests/test_b2_executor_write_routing.py`
- This status note.
- Minimal B2 routing vocabulary in `src/contracts.py`.

Out of scope:

- Live executor implementation.
- Runtime write authority.
- Raw command or broad file mutation capability.
- OS permission hardening.
- Executor isolation.
- External anchor implementation.
- Phase 11-A start.
- Main merge or PR ready transition.

## B1/B2/B3 Boundary

B1 remains `.aeg` guard components verified but unwired. B2-1 routes
pre-live executor-like write requests through the B1/mediator-compatible path.
B3 remains required for raw capability and worktree-scope closure.

B2-1 does not close the B1 hard blocker by itself and does not establish live
executor readiness. The Live Executor Entry Gate still needs B1+B2+B3 together.

## B1 Component Reuse

The router reuses:

- B1-B `decide_b1_aeg_integrity_guard`.
- B1-C `build_b1_aeg_guard_evidence_record`.
- B1-C `build_b1_aeg_guard_no_mutation_observation`.
- The B1-D verify-only rejection path remains compatible because the embedded
  B1-C record is replayable with `verify_b1_aeg_guard_evidence_record`.

B1-A is preserved: raw/direct known-gap baseline remains recorded as currently
bypassable, not upgraded by B2-1.

## Routed Path Boundary

The B2-1 routed denial means the structured pre-live request was routed to the
guard/mediator-compatible denial path and no mutation was performed by that
component. It does not mean raw/direct filesystem writes are impossible. It
also does not mean OS enforcement, filesystem enforcement, external enforcement,
or executor isolation exists.

Current authority remains:

- Runtime write path: `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`
- Live executor authority: `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`
- Phase 11-A: `PHASE11A_NOT_STARTED`
- Safe default: `hold_current_state`

## Status Vocabulary

The minimal B2 vocabulary added to `src/contracts.py` describes routing and
no-mutation observations only:

- `B2_EXECUTOR_WRITE_ROUTER`
- `B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST`
- `B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE`
- `B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE`
- `B2_AEG_PROTECTED_TARGET_ROUTED`
- `B2_ROUTED_DENIAL`
- `B2_NO_MUTATION_OBSERVATION_BOUND`
- `B2_NOT_PROTECTED_TARGET_OUT_OF_SCOPE`

These labels do not indicate completion, safety, external enforcement, or live
executor authority.
