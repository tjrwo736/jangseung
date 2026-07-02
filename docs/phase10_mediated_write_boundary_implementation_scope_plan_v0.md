# Aegis Phase 10 Mediated Write Boundary Implementation Scope Plan v0

## 1. Scope Plan Purpose

This document defines the Phase 10 implementation scope, ordering, and gate
boundaries for a future actual mediated write boundary implementation.

This is a scope plan document only. It is written before implementation. It
does not implement actual mediation. It does not implement bypass tests. It
does not open live executor authority. It does not promote scaffold-only
metadata into enforcement.

The purpose is narrower:

- decompose future mediated write boundary implementation into reviewable
  stages.
- define what must be scaffolded, tested, and verified before any enforcement
  claim.
- define `PASS` and `BLOCKED` boundaries for later implementation gates.
- keep current scaffold-only metadata from being treated as a mechanism-backed
  denial.
- keep `NOT_CHECKED` from being promoted into `PASS`.
- keep live executor authority closed.

This document must not be used to claim actual mediation, bypass test
coverage, mediator execution, broker execution, shell wrapping, tool wrapping,
external enforcement, or live executor authority.

The safe default remains:

```text
hold_current_state
```

## 2. Current Baseline Summary

Baseline for this implementation scope plan:

```text
current main SHA = fa9f1ddd0a82914b4d1e724d7d8545c6a5c6ca23
latest completed PR = #46
latest completed status = PASS_PHASE10_WRITE_BYPASS_TEST_PLAN_MAIN_SMOKE
latest completed gate = Aegis Phase 10 Write Bypass Test Plan v0
tests = 143 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
Mediated Write Boundary Design = PRESENT
Mediated Write Boundary Scaffold = PRESENT
Write Mediation Verify Criteria = PRESENT
Write Bypass Test Plan = PRESENT
Ledger Chain Walk Integrity = PRESENT
Actual Mediated Write Enforcement = NOT_IMPLEMENTED
Bypass Tests = NOT_IMPLEMENTED
Broker / Wrapper / Tool Execution = NOT_IMPLEMENTED
External Enforcement = NOT_IMPLEMENTED
Live Executor Authority = ON_HOLD
```

Current mediated write scaffold baseline:

```text
mediated_write_boundary_scaffold_status=SCAFFOLD_ONLY_NOT_ENFORCED
write_mediation_enabled=false
write_mediation_enforced=false
write_classes_granted=[]
dangerous direct grants=false
write_mediation_evidence_status=NOT_CHECKED
NOT_CHECKED != PASS
actual mediated write enforcement = NOT_IMPLEMENTED
live executor authority = ON_HOLD
```

The scaffold records vocabulary, default-deny metadata, manifest binding, and
verify rejection for overclaims. It does not prove that writes are mediated. It
does not make `.aeg/` executor-isolated. It does not prevent raw filesystem
writes, generic `write_file` writes, git metadata mutation, remote writes,
provider state mutation, path traversal, or symlink and alias bypass.

## 3. Implementation Scope Decomposition

Future actual mediated write boundary work must be split into the phases below.
This PR implements none of these phases.

### Phase A: Bypass Test Harness Scope

Future Phase A defines the harness shape for WBYP-001 through WBYP-025 without
turning the test plan into implementation inside this scope plan.

Scope outputs for a later gate:

- test fixture boundaries and safe temporary roots.
- expected attempted action model for allowed and denied writes.
- observed-state collection requirements.
- evidence and mediator provenance assertions.
- negative assertions for `.aeg/`, outside repo, raw shell, `write_file`,
  traversal, symlink, delete, chmod, git-ref, remote, and provider bypasses.

Phase A must be reviewed before enabling any write mediation.

### Phase B: Mediator Interface Contract Scope

Future Phase B defines the mediator interface contract before building a
mediator, broker, shell wrapper, tool wrapper, or command runner.

Scope outputs for a later gate:

- request fields for submitted path, operation, write class, declared output
  root, and actor.
- decision fields for allow or deny, reason, resolved target classification,
  and fail-closed status.
- provenance fields that prove the decision source is Aegis-controlled.
- evidence hooks for allowed and denied decisions.
- mismatch inputs for verify.

Phase B must not make executor narrative, `reported_only`, or executor-written
logs a proof source.

### Phase C: Deny-only Path Policy Scope

Future Phase C lands deny-only path policy before any allow policy.

Scope outputs for a later gate:

- `.aeg/` direct write denial.
- outside repo write denial.
- path traversal rejection.
- symlink and alias resolution expectations.
- delete, chmod, git-ref, and remote hard-deny defaults.
- fail-closed behavior for unknown, ambiguous, or uncanonical targets.

Phase C must prove denial by mechanism before any executor write capability is
considered.

### Phase D: Declared Output Directory Allow Scope

Future Phase D defines the first narrow allow path for declared output
directories after deny-only policy lands.

Scope outputs for a later gate:

- declared output root model.
- generated artifact classification.
- runtime artifact separation.
- exclusion rules for `.aeg/`, `.env`, secrets, tracked source, git metadata,
  and outside-repo targets.
- canonical path membership checks.
- manifest binding requirements.

Declared output directories must not become a general repo write grant.

### Phase E: Evidence Binding For Allowed/Denied Writes Scope

Future Phase E binds allowed and denied write decisions to evidence.

Scope outputs for a later gate:

- allowed write evidence record.
- denied write evidence record.
- mediator decision provenance record.
- manifest or digest binding for allowed writes.
- denial reason binding for denied writes.
- separation between Aegis runtime/recorder writes and executor writes.

Evidence binding must land before `PASS` claims. Evidence binding remains
tamper-evident support, not a tamper-proof evidence store.

### Phase F: Verify Mismatch Rejection Scope

Future Phase F makes verify reject mismatches between declared writes, observed
writes, mediator decisions, and evidence binding.

Scope outputs for a later gate:

- declared/observed write comparison.
- allowed write record validation.
- denied write record validation.
- missing mediator decision rejection.
- executor-written-only log rejection.
- `reported_only` and executor self-report rejection as judgment basis.

Verify mismatch rejection must land before enforcement claims.

### Phase G: Raw Shell/Write File Bypass Control Scope

Future Phase G controls bypass surfaces that could avoid the mediator.

Scope outputs for a later gate:

- raw shell unavailable or mediated.
- generic `write_file` unavailable or mediated.
- command execution unavailable or mediated.
- git operation writes unavailable or mediated.
- remote, network, provider, and secret-affecting writes denied unless a
  separate reviewed boundary exists.
- no unreviewed tool path can write `.aeg/` or outside the repo.

Phase G must prove all write paths are covered; a mediator that protects only
one tool path is insufficient.

### Phase H: Pre-live Integration Gate Scope

Future Phase H is the pre-live integration gate for actual mediation review.

Scope outputs for a later gate:

- all required bypass tests exist and pass.
- all required denial cases fail closed.
- `.aeg/` and outside-repo denial are mechanism-backed.
- allowed and denied writes are evidence-bound.
- verify rejects declared/observed mismatch.
- raw shell and `write_file` are unavailable or mediated.
- live executor authority remains `ON_HOLD` until every required gate passes.

Phase H is still not a live executor grant by itself. Any live executor
authority review remains a separate gate.

## 4. Future Candidate Implementation Components

The following components are future candidates only. This document does not
implement, scaffold, configure, or enable them.

| Candidate component | Future role | Current status |
| --- | --- | --- |
| path canonicalizer | Resolve targets before policy decisions. | FUTURE_CANDIDATE_ONLY |
| path traversal rejector | Deny traversal or ambiguous submitted paths. | FUTURE_CANDIDATE_ONLY |
| symlink/alias resolver | Decide from resolved target, not lexical path only. | FUTURE_CANDIDATE_ONLY |
| write mediation decision object | Represent allow or deny decisions with reasons. | FUTURE_CANDIDATE_ONLY |
| write class classifier | Classify repo, `.aeg/`, outside repo, destructive, remote, generated, runtime, and secret-affecting writes. | FUTURE_CANDIDATE_ONLY |
| declared output directory policy | Narrowly allow generated artifacts under declared roots. | FUTURE_CANDIDATE_ONLY |
| `.aeg/` direct write deny policy | Deny executor-authored writes to Aegis state. | FUTURE_CANDIDATE_ONLY |
| outside repo write deny policy | Deny writes outside approved roots. | FUTURE_CANDIDATE_ONLY |
| delete/chmod/git-ref/remote hard-deny policy | Deny destructive, permission, git ref, and remote writes before separate grants. | FUTURE_CANDIDATE_ONLY |
| generated artifact policy | Separate generated artifacts from source and evidence. | FUTURE_CANDIDATE_ONLY |
| runtime artifact separation policy | Keep runtime output distinct from tracked evidence and source. | FUTURE_CANDIDATE_ONLY |
| evidence binding writer | Record allowed write evidence under Aegis control. | FUTURE_CANDIDATE_ONLY |
| denied write evidence recorder | Record denied attempts under Aegis control. | FUTURE_CANDIDATE_ONLY |
| mediator decision provenance recorder | Bind decisions to Aegis-controlled provenance. | FUTURE_CANDIDATE_ONLY |
| verify mismatch checker | Reject declared, observed, decision, and evidence mismatches. | FUTURE_CANDIDATE_ONLY |
| bypass test harness | Exercise WBYP-001 through WBYP-025 bypass attempts. | FUTURE_CANDIDATE_ONLY |

No candidate component above is present as actual mediated write enforcement
because of this document.

## 5. Required Sequencing Rule

The following order is mandatory for future implementation:

- bypass test plan exists before implementation.
- test harness/scope must be reviewed before enabling any write mediation.
- deny-only policy must land before allow policy.
- `.aeg/` direct write denial must land before any executor write capability.
- outside repo denial must land before any write capability.
- evidence binding must land before `PASS` claims.
- verify mismatch rejection must land before enforcement claims.
- live executor authority remains `ON_HOLD` until all required gates pass.

This sequencing is a gate boundary. Later work must not collapse these stages
into a single implementation claim.

## 6. Scope Boundaries

The following distinctions are required:

```text
scope plan != implementation
implementation scaffold != enforcement
metadata denial != mechanism-backed denial
verify criteria != enforcement implementation
bypass test plan != bypass test implementation
local hash chain != external anchor
Aegis runtime/recorder write != executor write
```

Current Aegis runtime and recorder writes to `.aeg/` are expected local runtime
behavior. They must not be converted into executor write authority. A future
executor write must be denied, mediated, and evidence-bound through a
mechanism-backed boundary before it can be reviewed as safe.

## 7. Future PASS Criteria Before Actual Enforcement Claim

Future actual mediated write enforcement may be claimed only if all criteria
below are satisfied by mechanism and verified evidence:

- all WBYP-001 through WBYP-025 tests exist.
- all required denial cases fail closed.
- `.aeg/` write denial is mechanism-backed.
- outside repo write denial is mechanism-backed.
- raw shell and `write_file` bypass is unavailable or mediated.
- mediator decisions are Aegis-controlled.
- allowed writes are evidence-bound.
- denied writes are evidence-bound.
- verify rejects declared/observed mismatch.
- executor self-report is not proof.
- `reported_only` is not judgment basis.
- `NOT_CHECKED` is not `PASS`.
- `SCAFFOLD_ONLY_NOT_ENFORCED` is not safe, pass, or enforced.

`PASS` requires coverage of bypass surfaces and provenance of the decision
source. A mediator that covers only one write path is not sufficient if another
write path can bypass it.

## 8. Future BLOCKED Criteria

Future implementation is `BLOCKED` if any condition below is true:

- executor can directly write `.aeg/`.
- executor can write outside repo.
- executor can bypass mediator via traversal, symlink, or alias.
- executor can delete, chmod, mutate git refs, or perform remote writes without
  mediation.
- raw shell exists without mediation.
- `write_file` exists without mediation.
- mediator logs are executor-written only.
- evidence binding mismatch is ignored.
- `reported_only` is used as judgment basis.
- executor self-report is used as proof.
- `.aeg/` or `.env` becomes tracked.
- live executor authority opens before bypass tests pass.

Any `BLOCKED` condition keeps live executor authority on hold and requires a
new reviewed gate before the implementation can be considered again.

## 9. Relation To Previous Phase 10 Gates

This scope plan is downstream of the completed Phase 10 gates:

- Phase 10 External Enforcement Boundary Scope Plan v0 defines the external
  enforcement boundary.
- Phase 10 Aeg Write Boundary Threat Model v0 defines `.aeg/` write risks.
- Phase 10 Capability Grant Matrix v0 defines deny and not-granted defaults.
- Aegis Ledger Chain Walk Integrity v0 strengthens tamper-evident
  verification.
- Phase 10 Mediated Write Boundary Design v0 defines the intended mediation
  model.
- Phase 10 Mediated Write Boundary Scaffold v0 adds metadata, schema, and
  verify scaffold.
- Phase 10 Write Mediation Verify Criteria v0 defines future `PASS` and
  `BLOCKED` criteria.
- Phase 10 Write Bypass Test Plan v0 defines concrete future bypass tests.
- This scope plan defines implementation sequencing and gate boundaries.

This document does not supersede earlier gates. It fixes the order in which a
later actual implementation must satisfy them.

## 10. Non-goals

This document does not implement or authorize:

- actual mediation implementation.
- bypass tests implementation.
- mediator.
- broker.
- shell wrapper.
- tool wrapper.
- `read_file`, `write_file`, `run_command`, `http_request`, git, provider, or
  other tool implementation.
- OS user separation.
- sandbox or container.
- IPC.
- `.aeg/` permission hardening.
- external anchor.
- live executor authority grant.
- release or deploy.
- external enforcement implementation.
- evidence store lock.
- chmod or chown.
- network or API call.
- provider or model call.
- planner, multi-step, resume, autonomous loop, or multi-citizen execution.
- secret, token, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- main direct push.
- main merge.

## 11. Recommended Next Gate

Recommended next gate:

```text
Phase 10 Write Bypass Test Harness Scope v0
```

Alternative next gate:

```text
Phase 10 Mediator Interface Contract v0
```

This document implements neither gate. The conservative path is to scope the
test harness before any mediator or write mediation implementation.

## 12. Canonical Distinctions To Preserve

The following distinctions are mandatory:

```text
tamper-evident != tamper-proof
folder-local != executor-isolated
capability denied by scaffold != externally enforced denial
evidence binding != tamper-proof evidence store
current no-op executor safe != future live executor safe
structured tool call != safe capability
NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY
NOT_CHECKED != PASS
reported_only != judgment basis
executor self-report != proof
ledger chain walk != external anchor
mediation design != mediation implementation
mediation scaffold != mediation enforcement
verify criteria != enforcement implementation
bypass test plan != bypass test implementation
implementation scope plan != implementation
```

These distinctions are review requirements. Later documents and code must not
use this scope plan, current scaffold metadata, or executor narrative to claim
that a mechanism-backed mediated write boundary already exists.
