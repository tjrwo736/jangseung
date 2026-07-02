# Aegis Live Executor Entry Gate v0

## 1. Purpose

This document is not an implementation document for enabling a live executor.

This document fixes the hard blocker checklist that must be cleared before
live executor entry. The entry decision must not be based on intuition,
momentum, or a few successful runs.

Safe default:

```text
safe default = hold_current_state
```

Current authority:

```text
live_executor_authority = ON_HOLD
```

If any hard blocker in this document remains unmet, Aegis must keep:

```text
live_executor_authority = ON_HOLD
safe default = hold_current_state
```

## 2. Current baseline

Current Phase 10-E completion state:

```text
Phase 10-E final label = PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED
E1~E6 write mediation components are verified.
Runtime write path is not wired.
Actual enforcement is not active.
Live executor authority remains ON_HOLD.
Phase 11-A = NOT_STARTED.
```

Required status labels:

```text
live_executor_authority = ON_HOLD
safe default = hold_current_state
Phase 11-A Pre-live Executor Write Path Wiring Gate = NOT_STARTED
Runtime write path wiring = NOT_IMPLEMENTED
mediator wiring = NOT_IMPLEMENTED
.aeg integrity hardening = NOT_IMPLEMENTED
capability scope implementation = NOT_IMPLEMENTED
```

Phase 10-E closed as
`PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED`, but runtime wiring
remains `NOT_WIRED`. That label is component verification only. It is not live
executor authority, not runtime enforcement, and not Phase 11-A start.

## 3. HARD BLOCKER B1. `.aeg/` integrity

B1 requires evidence-store integrity hardening before live executor entry.

The executor must not be able to manipulate its own monitoring record under
`.aeg/`, including evidence, ledger, and manifest material. A manipulation
attempt must be measured by verification as `REPLAY_FAILED`.

The verification basis must live outside the evidence being judged. Rewriting
evidence alone must not be enough to flip a verdict from failure to pass.

B1 must never be skipped. B1은 절대 건너뛰지 않는다. If B1 is broken, the
executor can edit its own grade sheet. In that state, Aegis collapses into
self-certification instead of independent verification.

Current B1 state:

```text
.aeg integrity hardening = NOT_IMPLEMENTED
live_executor_authority = ON_HOLD
```

## 4. HARD BLOCKER B2. mediator wiring

B2 requires the executor's actual write path to route through the mediator.

Every executor write must pass through the E2 through E6 component set. It is
not enough for `save_run` or `build_evidence_packet` to use evidence helpers;
the executor's own write operation must be routed to the mediator.

After wiring, some E1 bypass tests must change in the blocking direction. If
the verified components are not connected to executor writes, they are not a
defense.

Current B2 state:

```text
Runtime write path wiring = NOT_IMPLEMENTED
mediator wiring = NOT_IMPLEMENTED
Actual enforcement is not active.
live_executor_authority = ON_HOLD
```

## 5. HARD BLOCKER B3. capability not granted plus worktree scope

B3 requires capability restriction and canonical worktree scoping before live
executor entry.

The executor must not receive raw shell or general-purpose `write_file`
capability. Its write capability must be scoped to the worktree, and `.aeg/`
must remain outside that scope.

The scope boundary must canonicalize paths and block symlink, `../`, and
absolute-path bypass attempts.

Current B3 state:

```text
capability scope implementation = NOT_IMPLEMENTED
live_executor_authority = ON_HOLD
```

## 6. First executor restrictions

L1. The first executor starts close to propose-only.

L2. Only low-risk tasks are allowed.

L3. The first runs happen in an isolated test repository, not in a real
project.

The first executor's goal is not usefulness. Its goal is real-world validation
that the safety controls stop unsafe behavior.

## 7. Success criteria

The initial Phase 11 success criterion is not that the executor wrote good
code.

The success criterion is that the safeguards actually block the executor when
it tries to do something dangerous.

A few successful early runs must not be mistaken for evidence that live
execution is safe.

## 8. Final gate before enabling live executor

F1. Run a Fable 5 comprehensive audit immediately before attaching a live
executor.

F2. Until B1 through B3, L1 through L3, and the success criteria above are all
met, Aegis must keep:

```text
live_executor_authority = ON_HOLD
safe default = hold_current_state
```

Enabling the live executor is a user gate. It is not implied by Phase 10-E
completion, component verification, document creation, or a passing smoke
check.

## 9. Read this when urgency appears

안 지워진 blocker가 하나라도 있으면 아직이다.

조급함은 "빨리 켜자"가 아니라 "빨리 blocker를 닫자"로 방향을 바꾼다.

Operational restatement:

```text
safe default = hold_current_state
live_executor_authority = ON_HOLD
Phase 11-A Pre-live Executor Write Path Wiring Gate = NOT_STARTED
Runtime write path wiring = NOT_IMPLEMENTED
mediator wiring = NOT_IMPLEMENTED
.aeg integrity hardening = NOT_IMPLEMENTED
capability scope implementation = NOT_IMPLEMENTED
```
