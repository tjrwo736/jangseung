# Phase 11-A-0 Rollback / Kill-path v0

## 1. Purpose

Phase 11-A-0 creates a rollback and kill-path scaffold before any later
`save_run` write path work. The goal is to prove that a future candidate wired
write path can fail or raise and still fall back to the existing unwired
behavior without crashing.

This line is safety preparation only.
Candidate wired path success handling is outside 11-A-0 scope.

## 2. Phase 11-A Roadmap Position

Phase 11-A entry is approved, but this step is only `11-A-0`.

The current roadmap state remains:

| Item | Status |
| --- | --- |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Phase 11-A-1 wiring | `NOT_STARTED` |
| Phase 11-B | `NOT_STARTED` |
| Safe default | `hold_current_state` |

## 3. 11-A-0 Scope

11-A-0 adds:

- an in-memory candidate wired path simulation hook.
- automatic fallback when that candidate returns failure or raises.
- an in-memory manual kill-path candidate through explicit config/function
  arguments.
- no-candidate evidence that the runtime write path remains unwired.
- deterministic fallback evidence.
- verify replay for schema, digest, mismatch, authority, and overclaim
  rejection.

11-A-0 does not add runtime write path wiring, runtime mediation wiring, actual
mediator activation, actual enforcement activation, live executor authority, or
Phase 11-B behavior.

11-A-0 accepts rollback evidence only for no-candidate, manual kill-path,
candidate failure, and candidate exception modes. A successful candidate wired
path return is not accepted as fallback proof and must be rejected by replay.

## 4. Rollback / Kill-path Behavior

The scaffold records these paths:

| Scenario | Behavior |
| --- | --- |
| No candidate wired path supplied | Keep current unwired behavior and record `NOT_WIRED`. |
| Candidate returns failure | Record attempted candidate path, record failure reason, fall back to `existing_unwired_path`, and continue. |
| Candidate raises | Catch the exception, record exception type, fall back to `existing_unwired_path`, and continue. |
| Manual kill-path config set | Skip the candidate path, fall back to `existing_unwired_path`, and record manual reason. |
| Candidate returns success | Reject as outside 11-A-0 scope. Do not treat success as fallback proof. |

The fallback result always records:

```text
runtime_write_path = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
safe_default = hold_current_state
write_performed = false
```

## 5. Fallback Trigger Modes

Automatic trigger:

- `candidate_wired_path_failure_or_exception`

Manual/config trigger candidate:

- `Phase11aKillPathConfig(manual_kill_path_triggered=True)`
- explicit function argument only.
- in-memory only.
- no environment-file reads or writes.
- no credential material reads or writes.
- no runtime config mutation.

## 6. Fallback Evidence Schema

The evidence record includes:

| Field | Meaning |
| --- | --- |
| `record_kind` | `phase11a_rollback_kill_path_evidence`. |
| `record_version` | `phase11a_rollback_kill_path_v0`. |
| `write_path_mode` | Rollback / kill-path only mode. |
| `write_path_wiring_attempted` | Whether the simulated candidate path was attempted. |
| `write_path_wiring_status` | One of the allowed statuses below. |
| `write_path_fallback_triggered` | Whether fallback was used. |
| `write_path_fallback_reason` | Deterministic fallback reason. |
| `write_path_fallback_target` | `existing_unwired_path`. |
| `write_path_runtime_mode` | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`. |
| `safe_default` | `hold_current_state`. |
| `live_executor_authority` | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`. |
| `phase11a_step` | `11-A-0`. |
| `phase11a1_wiring_status` | `NOT_STARTED`. |
| `phase11b_status` | `NOT_STARTED`. |
| `known_gap_status` | B1 known-gap baseline status preserved. |
| `deterministic_evidence_digest` | SHA-256 digest of the evidence payload without this field. |

## 7. Verify Replay Behavior

Verify replay:

1. checks required schema fields.
2. rejects unexpected fields.
3. recomputes the deterministic evidence digest.
4. checks fallback target is `existing_unwired_path`.
5. checks runtime mode remains `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
6. checks live executor authority remains on hold.
7. checks Phase 11-A-1 and Phase 11-B remain `NOT_STARTED`.
8. rejects candidate wired path success evidence, including `success=true`,
   `status=returned_success`, and the legacy
   `candidate_wired_path_success_not_activated_in_11a0` fallback reason.
9. rejects overclaims for runtime wiring, runtime authority, live executor
   authority, actual enforcement, or Phase 11-B start.

Verify replay is evidence validation only. It is not runtime enforcement.

## 8. Allowed Statuses

Allowed `write_path_wiring_status` values:

- `NOT_WIRED`
- `FALLBACK_READY`
- `FALLBACK_USED`
- `WIRING_FAILED_FALLBACK_USED`

## 9. Rejected Overclaims

Verify replay rejects:

- fallback target mismatch.
- fallback field tamper.
- `write_path_wiring_status` outside the allowed set.
- candidate wired path success claims.
- `candidate_wired_path_success_not_activated_in_11a0`.
- active runtime write path claims.
- live executor authority grant claims.
- runtime write authority grant claims.
- actual mediator activation claims.
- actual enforcement activation claims.
- Phase 11-B start claims.

## 10. Test Strategy

The unit tests cover:

- simulated candidate exception fallback.
- simulated candidate failure fallback reason recording.
- candidate success rejection.
- legacy candidate success fallback-proof rejection.
- preservation of existing unwired behavior.
- presence of fallback evidence fields.
- deterministic digest tamper rejection.
- fallback target mismatch rejection.
- wiring status overclaim rejection.
- default no-candidate path remaining unwired.
- known-gap preservation.
- live executor authority hold.
- Phase 11-A-1 and Phase 11-B not-started status.
- source scan for runtime side-effect helpers.

## 11. Known-gap Preservation

11-A-0 does not convert known-gap expected-red status to blocked or closed. The
B1 known-gap baseline remains preserved as evidence context for later steps.

## 12. Handoff To 11-A-1

11-A-1 may later introduce reviewed `save_run` write path wiring. This document
does not authorize that work. It only provides the rollback and kill-path
precondition so a future candidate path has a safe fallback target before any
activation is considered.

Successful candidate wired path handling belongs to 11-A-1 or later design. It
is not evidence of 11-A-0 readiness and is not accepted by 11-A-0 replay.

## 13. Current Authority

Current authority remains:

```text
runtime write path = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
live executor authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
Phase 11-A-1 wiring = NOT_STARTED
Phase 11-B = NOT_STARTED
safe default = hold_current_state
```

## 14. Explicit Non-claims

11-A-0 makes no claim of:

- `save_run` write path mediator wiring.
- `build_evidence_packet` runtime mediation wiring.
- actual mediator activation.
- actual enforcement activation.
- raw shell, write-file, run-command, process-spawn, provider, model, network,
  or runtime write authority grant.
- live executor authority.
- provider/model-backed executor behavior.
- Phase 11-B implementation.
- protected evidence state, ledger, environment-file, credential material, or
  runtime artifact mutation.
- release, deploy, main merge, or ready-for-review transition.

## 15. Safe Default

```text
safe default = hold_current_state
```
