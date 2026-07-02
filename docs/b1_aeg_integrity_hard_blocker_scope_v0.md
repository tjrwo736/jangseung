# Aegis B1 `.aeg/` Integrity Hard Blocker Scope Plan v0

## 1. Purpose

This document fixes the scope and acceptance plan for closing B1, the
`.aeg/` integrity hard blocker before any live executor authority can be
granted.

This is a docs-only scope plan. It is not B1 implementation, not `.aeg/`
integrity hardening, not runtime write path wiring, not Phase 11-A start, and
not live executor enablement.

B1 exists because an executor must not be able to manipulate its own monitoring
record. If the executor can rewrite `.aeg/`, evidence, ledger, manifest, or
verify basis material, Aegis collapses into self-certification instead of
independent verification.

B1 must never be skipped. B1은 절대 건너뛰지 않는다.

Until B1 is actually implemented, tested, and accepted by measured evidence:

```text
live_executor_authority = ON_HOLD
safe default = hold_current_state
```

## 2. Current baseline

Current baseline for this scope plan:

```text
repo path = /mnt/d/Codex/Aegis
GitHub repo = tjrwo736/aegis
current main SHA = c29f4858c96f4651b479f3651e72f2357f4cec46
latest completed PR = #59
latest completed gate = Aegis Live Executor Entry Gate v0
Phase 10-E final label = PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED
live executor authority = ON_HOLD
Phase 11-A = NOT_STARTED
safe default = hold_current_state
```

Current implementation state:

```text
B1 scope plan = DOCUMENTED_ONLY
B1 implementation = NOT_STARTED
.aeg integrity hardening = NOT_IMPLEMENTED
runtime write path wiring = NOT_IMPLEMENTED
actual enforcement = NOT_ACTIVE
live executor authority = ON_HOLD
Phase 11-A = NOT_STARTED
```

This plan does not upgrade the current baseline. B1 acceptance criteria are not
B1 completion.

## 3. Why B1 is non-skippable

B1 is non-skippable because `.aeg/` is the local monitoring and replay record
for Aegis execution. A future executor with write authority must not be able to
alter the record that judges its own behavior.

If B1 is bypassed, all downstream signals become suspect:

- evidence can be rewritten after a dangerous action.
- ledger material can be removed, reordered, appended, or replaced.
- manifest material can be made to describe a different run than the one that
  happened.
- reported-only claims can be promoted into judgment basis.
- `NOT_CHECKED` can be falsely promoted into `PASS`.
- a failed replay can be hidden by rewriting the local evidence packet.

The verification basis must live outside the evidence being judged. Rewriting
evidence alone must not be enough to flip a verdict from failure to pass.

Required distinctions:

```text
tamper-evident != tamper-proof
evidence binding != tamper-proof evidence store
ledger chain walk != external anchor
REPLAY_CONSISTENT != external oracle proof
NOT_CHECKED != PASS
reported_only != judgment basis
.aeg folder-local != executor-isolated
B1 scope plan != B1 implementation
B1 acceptance criteria != B1 completed
live_executor_authority remains ON_HOLD
```

## 4. Threat model

The B1 threat model assumes a future executor may try to influence the record
used to judge it. The relevant attacker is not an external network adversary;
it is the executor or an executor-controlled write path attempting to mutate
audit state.

In-scope threat actions:

- direct writes into `.aeg/`.
- traversal into `.aeg/` through `../` path construction.
- symlink aliases that resolve into `.aeg/`.
- evidence record overwrite or replacement.
- evidence packet rewrite.
- manifest overwrite or replacement.
- ledger append, deletion, reorder, or tamper.
- verify result basis rewrite.
- replay material rewrite after a failed or unsafe action.
- promotion of reported-only data into judgment basis.
- promotion of unchecked state into pass-like state.
- future executor-written audit records being edited by the executor itself.

The required verifier behavior for manipulation attempts is rejection in a
`REPLAY_FAILED` or `INVALID_EVIDENCE` family result. A clean-looking local
evidence rewrite is not sufficient evidence that the run was safe.

## 5. Protected targets

B1 protected targets are:

- `.aeg/`
- `.aeg/ledger.jsonl`
- `.aeg/manifest`
- evidence records
- evidence packet
- verify result basis
- ledger chain / replay material
- any future executor-written audit record

Protection applies to direct paths and resolved paths. A path that reaches a
protected target through traversal, symlink aliasing, canonicalization gaps, or
future helper APIs is still a protected target.

## 6. Required acceptance criteria

B1 may be considered ready for completion review only when measured evidence
shows all of the following:

- direct `.aeg/` write attempts are rejected.
- traversal into `.aeg/` is rejected.
- symlink aliases into `.aeg/` are rejected.
- evidence overwrite is rejected.
- manifest overwrite is rejected.
- ledger overwrite is rejected.
- ledger append or tamper is rejected unless it uses an approved audited path.
- evidence rewrite cannot flip a verdict.
- `reported_only` cannot become judgment basis.
- `NOT_CHECKED` cannot become `PASS`.
- each rejection is reproducible by verify.
- normal valid evidence still replays consistently.

The acceptance evidence must distinguish detection from prevention. A
tamper-evident result may prove that a mutation is visible; it does not prove
that mutation was impossible. A replay-consistent ledger may prove local replay
consistency; it does not prove an external oracle.

## 7. Required rejection cases

B1 implementation work must include rejection coverage for at least these
cases before B1 can be closed:

- direct `.aeg/` file create, overwrite, append, and delete attempts.
- direct `.aeg/ledger.jsonl` append, overwrite, truncate, reorder, and delete
  attempts.
- direct `.aeg/manifest` overwrite and replacement attempts.
- direct evidence record overwrite and replacement attempts.
- direct evidence packet rewrite attempts.
- traversal paths that resolve under `.aeg/`.
- symlink paths that resolve under `.aeg/`.
- alias paths that differ textually but canonicalize to a protected target.
- ledger chain material missing, reordered, inconsistent, or replaced.
- verify basis material changed after evidence was recorded.
- failed evidence rewritten into pass-like evidence.
- `reported_only` evidence promoted to judgment basis.
- `NOT_CHECKED` evidence promoted to `PASS`.
- future executor-written audit records rewritten by the executor.

Expected rejection families:

```text
REPLAY_FAILED
INVALID_EVIDENCE
```

The exact implementation may define narrower sublabels, but the rejection must
remain replay-measurable and must not depend on executor self-report.

## 8. Required evidence outside `.aeg/`

B1 cannot be accepted using only evidence that the executor can rewrite. The
basis that decides whether `.aeg/` evidence is valid must be outside the
evidence being judged.

Required evidence properties:

- the verifier has a basis independent of the mutable evidence record under
  review.
- evidence packet rewrite alone cannot change the final verdict from failure
  to pass.
- ledger chain walk material is checked against a basis that is not merely the
  rewritten ledger body.
- manifest consistency is checked against replay material outside the manifest
  being judged.
- reported-only claims remain informational unless independently bound into a
  judgment basis.
- unchecked state remains unchecked and cannot be upgraded by local evidence
  text.

This scope plan does not require a specific external anchor design. It requires
the later B1 implementation plan to identify what the verifier trusts, where
that basis lives, and why the executor cannot rewrite that basis through the
same authority being judged.

## 9. Required tests / smoke candidates

Future B1 implementation should include focused tests and smoke candidates for:

- direct `.aeg/` write denial.
- traversal into `.aeg/` denial.
- symlink alias into `.aeg/` denial.
- evidence overwrite denial.
- manifest overwrite denial.
- ledger overwrite denial.
- ledger append or tamper rejection outside an approved audited path.
- evidence rewrite verdict-flip rejection.
- `reported_only` promotion rejection.
- `NOT_CHECKED` to `PASS` promotion rejection.
- verify reproducibility for each rejection.
- replay consistency for normal valid evidence.

Smoke candidates should prove both sides of the boundary:

- manipulated evidence fails verification with a replay or invalid-evidence
  result.
- valid unmodified evidence still replays consistently.

## 10. Explicit non-goals

This document does not implement:

- `.aeg` integrity enforcement.
- OS permission hardening.
- ownership or mode changes.
- sandbox or container boundaries.
- IPC boundaries.
- executor user or process separation.
- runtime write path wiring.
- mediator wiring.
- a live executor.
- a write-capable executor.
- raw shell, generic file write, command execution, network, or provider tool
  capability.
- actual enforcement activation.
- test changes.
- source changes.
- packaging changes.
- release, publish, deploy, main direct push, or main merge.

This document also does not claim that `.aeg/` is tamper-proof,
executor-isolated, externally enforced, filesystem-enforced, OS-enforced, safe
for write authority, safe to run, or ready for live executor authority.

## 11. Relation to B2/B3 and Phase 11-A

B1 is separate from B2 and B3:

- B1 covers integrity of `.aeg/`, evidence, ledger, manifest, and replay basis.
- B2 covers runtime write path routing through mediation.
- B3 covers capability restriction and canonical worktree scoping.

B1 cannot be replaced by B2 or B3. Mediator wiring does not prove evidence
store integrity. Capability scoping does not prove replay basis integrity.
Evidence replay does not prove a live write boundary.

Phase 11-A remains not started:

```text
Phase 11-A = NOT_STARTED
live executor authority = ON_HOLD
runtime write path wiring = NOT_IMPLEMENTED
actual enforcement = NOT_ACTIVE
```

No B1 scope document, acceptance list, or future B1 implementation by itself
opens live executor authority. Live executor authority requires the full entry
gate to be satisfied and a separate user decision.

## 12. Safe default

Safe default:

```text
safe default = hold_current_state
live_executor_authority = ON_HOLD
Phase 11-A = NOT_STARTED
```

If any B1 acceptance criterion is missing, ambiguous, executor-self-reported,
or only stored inside the evidence being judged, the result remains:

```text
B1 = NOT_CLOSED
live_executor_authority = ON_HOLD
safe default = hold_current_state
```
