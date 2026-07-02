# Phase 10-E E6 Write Mediation Verify Mismatch Rejection v0

Phase 10-E E6 adds deterministic verify replay rejection for forged or
inconsistent write mediation component evidence.

This is not runtime write path wiring. The component state remains
`PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED`,
`RUNTIME_WIRING_NOT_IMPLEMENTED`, and `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
Runtime write path wiring belongs to a later Phase 11-A gate.

E6 rejects these evidence shapes as `REPLAY_FAILED` with `INVALID_EVIDENCE`
details:

- `STATUS_OVERCLAIM_REJECTED` for mediated write or scaffold-only status
  overclaims.
- `BYPASS_RESULT_MISMATCH_REJECTED` for WBYP expected-red or known-gap result
  upgrades.
- `MEDIATED_WRITE_EVIDENCE_MISMATCH_REJECTED` for mediated write binding hash
  tamper.
- `WRITE_MEDIATION_COMPONENT_MISMATCH_REJECTED` for mediator contract or
  component status mismatch.
- `REPORTED_ONLY_PROOF_REJECTED` for reported-only write denial promoted to a
  judgment basis.
- `NOT_CHECKED_PASS_OVERCLAIM_REJECTED` for NOT_CHECKED or scaffold-only
  statuses promoted to pass-like results.

E1 through E5 scaffold/component evidence remains replay-consistent when the
recorded state is unmodified.
