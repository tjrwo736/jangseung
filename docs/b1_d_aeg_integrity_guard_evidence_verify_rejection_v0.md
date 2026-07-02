# Aegis B1-D `.aeg/` Integrity Guard Evidence Verify Rejection v0

## Scope

This note records the B1-D verify-only rejection component for B1-C guard
decision evidence records. The component replays canonical digests and rejects
mismatch, tamper, reported-only promotion, known-gap promotion, and scope
overclaim fields.

This component is not B1 completion, not a tamper-proof evidence store, not an
external anchor, not OS or filesystem hardening, not executor isolation, not
runtime write-path wiring, and not a live executor or Phase 11-A start.

## Verify Behavior

- A valid B1-C guard evidence record replays as
  `B1_AEG_GUARD_EVIDENCE_REPLAY_CONSISTENT`.
- Guard decision digest tamper is rejected with
  `B1_AEG_GUARD_DECISION_DIGEST_MISMATCH_REJECTED`.
- Evidence record digest or record id mismatch is rejected with
  `B1_AEG_GUARD_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED`.
- `submitted_path`, `resolved_path`, `protected_root`, `target_class`,
  `denial_reason`, and `wiring_status` mismatch is rejected with
  `B1_AEG_GUARD_FIELD_MISMATCH_REJECTED`.
- No-mutation observation mismatch is rejected with
  `B1_AEG_GUARD_NO_MUTATION_OBSERVATION_MISMATCH_REJECTED`.
- Completion, hardening, external anchor, isolation, live-authority, and
  run-safety overclaims are rejected with
  `B1_AEG_GUARD_EVIDENCE_OVERCLAIM_REJECTED`.
- `reported_only` guard denial evidence promotion is rejected with
  `B1_AEG_GUARD_REPORTED_ONLY_PROMOTION_REJECTED`.
- `NOT_CHECKED` or known-gap promotion to passlike labels is rejected with
  `B1_AEG_GUARD_NOT_CHECKED_PROMOTION_REJECTED`.

## Boundary

The verifier records:

```text
B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION
B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT
NOT_TAMPER_PROOF
NOT_EXTERNAL_ANCHORED
NOT_WIRED_TO_EXECUTOR_WRITE_PATH
NOT_OS_ENFORCED
NOT_FILESYSTEM_ENFORCED
LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PHASE11A_NOT_STARTED
```

Verify rejection means deterministic mismatch rejection only. It does not make
raw filesystem writes impossible. The B1-A `CURRENTLY_BYPASSABLE` raw/direct
baseline remains valid.

## Preservation

- B1-A known-gap baseline remains preserved.
- B1-B deny-only guard component remains preserved.
- B1-C evidence binding remains preserved.
- Live executor authority remains on hold.
- Phase 11-A remains not started.

## Safe Default

```text
hold_current_state
```
