# Aegis Phase 10 Write Mediation Verify Criteria v0

## 1. Criteria Purpose

This document defines verification criteria for judging a future actual write
mediation implementation after the mediated write boundary scaffold.

This is a criteria document only. It is written before implementation. It does
not implement actual mediation, broker execution, shell wrapping, tool
wrapping, external enforcement, OS isolation, `.aeg/` hardening, or live
executor authority.

The purpose is narrower:

- define what a future verifier must require before actual write mediation can
  be judged `PASS`.
- define failure and blocked conditions that must keep write mediation from
  being accepted.
- keep current scaffold-only metadata from being promoted into enforcement.
- keep live executor authority closed.
- preserve the distinction between evidence criteria and enforcement
  implementation.

This document must not be used to open a live executor. It must not be used to
treat scaffold-only metadata as a safe write boundary.

The safe default remains:

```text
hold_current_state
```

## 2. Baseline

Baseline for this criteria document:

```text
current main SHA = 159c9adcd1c5899134193940d9a360101a2d0582
latest completed PR = #44
latest completed status = PASS_PHASE10_MEDIATED_WRITE_BOUNDARY_SCAFFOLD_MAIN_SMOKE
latest completed gate = Aegis Phase 10 Mediated Write Boundary Scaffold v0
tests = 143 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
Mediated Write Boundary Design = main reflected
Mediated Write Boundary Scaffold = main reflected
scaffold metadata/schema/verify = present
dangerous direct write grant rejection = present
scaffold overclaim rejection = present
actual mediated write enforcement = NOT_IMPLEMENTED
external enforcement = NOT_IMPLEMENTED
```

Current scaffold baseline:

```text
mediated_write_boundary_scaffold_status=SCAFFOLD_ONLY_NOT_ENFORCED
write_mediation_enabled=false
write_mediation_enforced=false
write_classes_granted=[]
dangerous direct grants=false
write_mediation_evidence_status=NOT_CHECKED
NOT_CHECKED != PASS
```

The scaffold records vocabulary, default-deny metadata, manifest binding, and
verify rejection for overclaims. It does not prove that writes are mediated. It
does not make `.aeg/` executor-isolated. It does not prevent raw filesystem
writes.

## 3. Required Future PASS Criteria

A future actual write mediation implementation can be judged `PASS` only when
all minimum criteria below are satisfied by mechanism and verified evidence,
not by executor narrative.

Required future `PASS` criteria:

- all write attempts pass through a mediator.
- raw filesystem write is unavailable to the executor.
- direct executor writes to `.aeg/` are denied by mechanism, not by
  self-report.
- outside-repo writes are denied by mechanism.
- delete, chmod, chown, git-ref, and remote writes are denied unless explicitly
  mediated.
- mediator decisions are recorded by Aegis runtime.
- allowed writes are evidence-bound.
- denied writes are evidence-bound.
- verify rejects declared/observed mismatch.
- bypass tests exist.
- tamper tests exist.
- executor self-report is never proof.
- `reported_only` is never a judgment basis.

`PASS` requires both coverage and provenance. A mediator that handles only one
tool path is insufficient if another write path can bypass it. A log written
only by the executor is insufficient because it collapses the proof source into
the actor being judged.

## 4. Required Future Failure Criteria

The following conditions must be `FAIL` or `BLOCKED` for future actual write
mediation review:

- executor can directly write `.aeg/`.
- executor can bypass the mediator with `write_file`, raw shell, path
  traversal, or equivalent broad write authority.
- executor can write outside the repository.
- executor can delete, chmod, chown, mutate git refs, or perform remote writes
  without mediation.
- `write_mediation_enforced=true` is claimed without enforcement proof.
- `SCAFFOLD_ONLY_NOT_ENFORCED` is treated as safe or pass.
- `NOT_CHECKED` is treated as `PASS`.
- mediator logs are executor-written only.
- evidence binding mismatch is ignored.
- path canonicalization is missing.
- symlink or path traversal bypass is untested.

Any of these conditions blocks a future live executor authority review because
the write boundary would still depend on trust in the executor or on incomplete
path coverage.

## 5. Verify Dimensions

Future verify must evaluate these dimensions before accepting actual write
mediation:

- path canonicalization.
- path traversal rejection.
- symlink and alias path handling.
- `.aeg/` write denial.
- outside-repo write denial.
- declared output directory enforcement.
- runtime artifact separation.
- tracked and untracked mutation distinction.
- allowed write manifest binding.
- denied write evidence binding.
- mediator decision provenance.
- mismatch rejection.
- bypass attempts.
- auditability.
- fail-closed behavior.

The verifier must judge the resolved target, the write class, the mediator
decision, and the evidence binding together. Lexical path checks alone are not
enough. Missing or ambiguous information must fail closed.

## 6. Required Future Tests

Future actual write mediation requires tests in these categories before it can
be reviewed as `PASS`:

- direct `.aeg/` write bypass test.
- outside repo write bypass test.
- path traversal write test.
- symlink write bypass test.
- delete write denial test.
- chmod/chown denial test.
- git ref write denial test.
- remote write denial test.
- declared output dir allow test.
- undeclared output write denial test.
- allowed write evidence binding test.
- denied write evidence binding test.
- manifest/evidence mismatch rejection test.
- mediator log tamper test.
- executor self-report spoof test.
- `reported_only` spoof test.

These tests must exercise bypass surfaces, not only the expected successful
mediator path. A mediator that passes ordinary write tests but lacks bypass and
tamper tests remains unverified.

## 7. Relation To Existing Gates

This criteria document is downstream of the completed Phase 10 gates:

- Phase 10 External Enforcement Boundary Scope Plan v0 defines the external
  enforcement problem.
- Phase 10 `.aeg` Write Boundary Threat Model v0 defines `.aeg/` write risks.
- Phase 10 Capability Grant Matrix v0 defines deny and not-granted defaults.
- Aegis Ledger Chain Walk Integrity v0 strengthens tamper-evident
  verification.
- Phase 10 Mediated Write Boundary Design v0 defines the intended mediation
  model.
- Phase 10 Mediated Write Boundary Scaffold v0 adds metadata, schema, and
  verify scaffold.
- This criteria document defines future `PASS`, `FAIL`, and `BLOCKED`
  criteria for actual mediation.

This document does not supersede those gates. It turns their design and
scaffold constraints into review criteria for a later implementation.

## 8. Non-goals

This document does not implement or authorize:

- actual mediator.
- file broker.
- shell wrapper.
- tool wrapper.
- `read_file`, `write_file`, `run_command`, `http_request`, git, provider, or
  other tool implementation.
- external enforcement implementation.
- live executor authority grant.
- OS user separation.
- process separation.
- sandbox or container implementation.
- IPC implementation.
- `.aeg/` permission hardening.
- evidence store lock.
- external anchor.
- provider or model call.
- network or API call.
- planner, multi-step, resume, autonomous loop, or multi-citizen execution.
- release, publish, or deploy.
- secret, token, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- main direct push.
- main merge.

## 9. Recommended Next Gate

Recommended next gate:

```text
Phase 10 Mediated Write Boundary Implementation Scope Plan v0
```

More conservative next gate:

```text
Phase 10 Write Bypass Test Plan v0
```

This document implements neither gate. The conservative path is to define the
bypass and tamper test plan before implementation scope is approved.

## 10. Canonical Distinctions To Preserve

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
```

If a future change claims that this criteria document implements mediation,
opens live executor authority, proves `.aeg/` is executor-isolated, treats
scaffold status as enforcement, treats `reported_only` as proof, or promotes
`NOT_CHECKED` to `PASS`, that change must be fixed before review.

## 11. Review Checklist

This criteria document is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- no actual mediated write enforcement is added.
- no broker, shell wrapper, tool wrapper, or tool execution implementation is
  added.
- live executor authority remains `ON_HOLD`.
- current scaffold baseline remains `SCAFFOLD_ONLY_NOT_ENFORCED`.
- `write_mediation_enabled=false` remains a scaffold baseline fact.
- `write_mediation_enforced=false` remains a scaffold baseline fact.
- `write_classes_granted=[]` remains a scaffold baseline fact.
- dangerous direct grants remain false.
- `write_mediation_evidence_status=NOT_CHECKED` remains not pass.
- future `PASS` criteria require mechanism-backed mediation and evidence.
- future `FAIL` or `BLOCKED` criteria reject bypass, tamper, and overclaim
  conditions.
- verify dimensions include path, `.aeg/`, outside-repo, artifact, manifest,
  provenance, mismatch, bypass, auditability, and fail-closed behavior.
- future tests include bypass, denial, evidence binding, tamper, self-report,
  and `reported_only` spoof categories.
- canonical distinctions are preserved.
- secrets, runtime artifacts, tracked `.aeg/`, and tracked `.env` files are
  absent.

Expected review status when these checks pass:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```

Final safe default:

```text
hold_current_state
```
