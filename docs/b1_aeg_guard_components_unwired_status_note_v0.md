# B1 `.aeg/` Guard Components Unwired Status Note v0

This is a docs-only lightweight status note. It records that the B1 `.aeg/`
guard components are verified but unwired, using only constants that already
exist in `src/contracts.py`.

It does not add a closure label, runtime wiring, tests, live executor authority,
or a claim that the B1 hard blocker is fully closed.

## Actual Constants Checked

`src/contracts.py` already contains these B1-A through B1-D status constants:

- B1-A known-gap baseline: `B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE`.
- B1-A raw/direct path result: `CURRENTLY_BYPASSABLE` via
  `WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE`.
- B1-B deny-only guard: `B1_AEG_INTEGRITY_DENY_ONLY_GUARD`.
- B1-C evidence binding: `B1_AEG_GUARD_EVIDENCE_BINDING`.
- B1-D verify-only rejection: `B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION`.
- B1-D verify-only scope: `B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT`.
- Runtime write path status: `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- Live executor authority status: `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- Phase 11-A status: `PHASE11A_NOT_STARTED`.

These constants support the status note that the B1 `.aeg/` guard component
package is verified but unwired. That phrase is descriptive only; it is not a
new code constant or official closure label.

## Preserved Baseline

B1-A known-gap baseline is preserved. The raw/direct `.aeg/` path remains
recorded as `CURRENTLY_BYPASSABLE`, and B1 does not assert OS, filesystem, or
executor isolation enforcement.

B1-B deny-only guard is present as a guard component. Its runtime status remains
`NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.

B1-C evidence binding is present as a component-level evidence record and digest
binding. It is not a tamper-proof evidence store and is not externally anchored.

B1-D verify-only rejection is present. `B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT`
keeps the rejection path scoped to verification, not runtime prevention.

The safe default is:

```text
hold_current_state
```

## Current Non-Protection Boundary

B1 completion does not mean any of the following:

- An executor cannot write `.aeg/`.
- Raw or direct `.aeg/` writes are blocked.
- The B1 hard blocker is fully closed.
- OS or filesystem enforcement exists.
- Executor isolation exists.
- The evidence store is tamper-proof.
- An external anchor exists.
- Live executor authority is ready.

Runtime write path remains `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.

Live executor authority remains `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.

Phase 11-A remains `PHASE11A_NOT_STARTED`.

## B1/B2/B3 Boundary

B1 is the `.aeg/` guard component package, verified but unwired.

B2 is executor write routing through the mediator and guard path.

B3 is raw shell, general write-file, and out-of-scope path capability not
granted, with worktree scope enforced.

The Live Executor Entry Gate's B1 condition is actually green only when B1, B2,
and B3 are satisfied together. B1 alone must not be treated as live executor
entry approval.

This note does not implement B2 routing or B3 capability denial.
