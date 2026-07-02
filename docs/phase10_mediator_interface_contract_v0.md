# Aegis Phase 10 Mediator Interface Contract v0

## 1. Contract Purpose

This document defines the Phase 10 mediator interface contract that must exist
before a future mediated write boundary implementation can be reviewed.

This is an interface contract document only. It is written before implementation
and before scaffold work for the contract. It does not implement an actual
mediator, broker, wrapper, tool execution surface, bypass test, fixture, actual
mediated write enforcement, external enforcement, or live executor authority.
It does not promote scaffold-only metadata into enforcement.

The purpose is narrower:

- define the future mediator request fields.
- define the future mediator decision fields.
- define required evidence and provenance binding expectations.
- define what future verify must reject.
- keep current `SCAFFOLD_ONLY_NOT_ENFORCED` metadata from being treated as a
  mechanism-backed denial.
- keep `NOT_CHECKED` from being promoted into `PASS`.
- keep live executor authority closed.

This contract must not be used to claim that a mediator already exists. It must
not be used to claim broker execution, shell wrapping, tool wrapping, bypass
test coverage, actual write enforcement, external enforcement, or live executor
authority.

The safe default remains:

```text
hold_current_state
```

## 2. Current Baseline

Baseline for this mediator interface contract:

```text
current main SHA = 7bc5d69758eb82404316949b52ba4df933914b21
latest completed PR = #48
latest completed status = PASS_PHASE10_WRITE_BYPASS_TEST_HARNESS_SCOPE_MAIN_SMOKE
latest completed gate = Aegis Phase 10 Write Bypass Test Harness Scope v0
tests = 143 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
Write Bypass Test Plan = PRESENT
Write Bypass Test Harness Scope = PRESENT
Mediated Write Boundary Implementation Scope Plan = PRESENT
Write Mediation Verify Criteria = PRESENT
Mediated Write Boundary Scaffold = PRESENT
Actual Mediator = NOT_IMPLEMENTED
Actual Broker / Wrapper / Tool Execution = NOT_IMPLEMENTED
Actual Bypass Tests = NOT_IMPLEMENTED
Actual Fixtures = NOT_IMPLEMENTED
Actual Mediated Write Enforcement = NOT_IMPLEMENTED
External Enforcement = NOT_IMPLEMENTED
Live Executor Authority = ON_HOLD
```

Current mediated write scaffold baseline:

```text
mediated_write_boundary_scaffold_status=SCAFFOLD_ONLY_NOT_ENFORCED
write_mediation_enabled=false
write_mediation_enforced=false
write_classes_granted=[]
write_mediation_evidence_status=NOT_CHECKED
NOT_CHECKED != PASS
actual mediator = NOT_IMPLEMENTED
actual broker / wrapper / tool execution = NOT_IMPLEMENTED
actual bypass tests = NOT_IMPLEMENTED
actual fixtures = NOT_IMPLEMENTED
actual mediated write enforcement = NOT_IMPLEMENTED
live executor authority = ON_HOLD
```

The current scaffold records vocabulary, default-deny metadata, manifest
binding, and verify rejection for overclaims. It does not prove that writes are
mediated. It does not make `.aeg/` executor-isolated. It does not prevent raw
filesystem writes, generic `write_file` writes, path traversal, symlink or
alias writes, delete, chmod, chown, git metadata mutation, remote writes,
secret writes, provider state mutation, network/API mutation, or runtime
artifact spoofing.

## 3. Contract Boundary

This contract defines the interface a future mediator must receive and emit. It
does not create a schema file, executable policy, mediator class, broker,
wrapper, test harness, fixture, enforcement hook, permission boundary, IPC
boundary, sandbox, network boundary, or live authority grant.

The future mediator boundary must separate these records:

- executor request.
- mediator decision.
- Aegis-controlled decision provenance.
- evidence binding for allowed and denied writes.
- verifier observation and mismatch judgment.

Executor-authored statements may be inputs to review. They are not proof of
mediation, denial, absence of mutation, absence of remote side effects, or
`.aeg/` protection.

## 4. Future Mediator Request Contract

A future mediator request record must be designed to contain the fields below.
This document defines field scope only; it does not create a schema, parser,
canonicalizer, broker, wrapper, tool, or validator.

| Field | Required contract meaning | Current status |
| --- | --- | --- |
| request id | Stable identifier for the submitted write attempt. It must be bound to any later decision and evidence record. | FUTURE_CONTRACT_ONLY |
| actor / executor identity placeholder | Placeholder for the future actor, executor, or mediated caller identity. It must not be treated as proof by itself. | FUTURE_CONTRACT_ONLY |
| operation type | Requested operation class such as create, modify, append, replace, delete, rename, chmod, chown, git ref mutation, remote mutation, or provider/API mutation. | FUTURE_CONTRACT_ONLY |
| write class | Future classification such as `repo_tracked_write`, `repo_untracked_write`, `aeg_state_write`, `outside_repo_write`, `delete_write`, `chmod_permission_write`, `git_ref_write`, `remote_write`, `secret_env_write`, `provider_state_write`, `generated_artifact_write`, or `runtime_artifact_write`. | FUTURE_CONTRACT_ONLY |
| target path | Submitted target path or destination descriptor. It may be lexical, relative, absolute, remote, or provider-backed, and therefore cannot be trusted without classification. | FUTURE_CONTRACT_ONLY |
| canonical path | Resolved local target where applicable after future canonicalization. Ambiguous, missing, untrusted, or non-local canonicalization must fail closed. | FUTURE_CONTRACT_ONLY |
| declared output scope | Future manifest or grant scope that names approved output roots, artifact categories, or allowed write classes. Missing scope must not default to allow. | FUTURE_CONTRACT_ONLY |
| repo boundary classification | Future classification of the canonical target as inside approved repo root, outside repo, sibling worktree, git metadata, remote, provider-backed, or unknown. | FUTURE_CONTRACT_ONLY |
| `.aeg` boundary classification | Future classification of whether the submitted or resolved target is under `.aeg/`, aliases `.aeg/`, traverses into `.aeg/`, or is unknown. | FUTURE_CONTRACT_ONLY |
| attempted action summary | Non-secret summary of the attempted action, with destructive, remote, secret-affecting, and provider/API-affecting behavior called out. | FUTURE_CONTRACT_ONLY |
| expected evidence binding fields | Required future evidence references for request id, decision id, actor placeholder, operation type, write class, target, canonical target, declared scope, decision status, reason, provenance, and observed result. | FUTURE_CONTRACT_ONLY |

A request is incomplete if it omits the resolved target expectation, omits the
write class, omits repo and `.aeg/` boundary classifications, collapses remote
or provider mutation into local file writes, relies on executor self-report as
proof, or treats `reported_only` as a judgment basis.

## 5. Future Mediator Decision Contract

A future mediator decision record must be designed to contain the fields below.
This document defines field scope only; it does not create decision code,
policy code, enforcement code, or logs.

| Field | Required contract meaning | Current status |
| --- | --- | --- |
| decision id | Stable identifier for the mediator decision. It must bind to the request id and evidence record. | FUTURE_CONTRACT_ONLY |
| decision status | One of `ALLOW`, `DENY`, `BLOCKED`, `NEEDS_REVIEW`, or `NOT_CHECKED`. `NOT_CHECKED` is never `PASS`. | FUTURE_CONTRACT_ONLY |
| reason code | Structured reason for the decision, including denial, blocked, needs-review, or fail-closed classification. | FUTURE_CONTRACT_ONLY |
| mechanism-backed requirement flag | Indicates whether the decision is expected to be backed by an actual mechanism in a future implementation. Current contract records are not mechanism-backed enforcement. | FUTURE_CONTRACT_ONLY |
| evidence required flag | Indicates whether an allowed or denied decision requires evidence binding. For write mediation, allowed and denied writes both require evidence binding. | FUTURE_CONTRACT_ONLY |
| verify required flag | Indicates whether future verify must compare declared, observed, decision, and evidence state before any pass claim. | FUTURE_CONTRACT_ONLY |
| fail-closed behavior | Defines the required result for ambiguous, missing, uncanonical, unclassified, untrusted, remote, provider-backed, secret-affecting, or destructive cases. | FUTURE_CONTRACT_ONLY |
| provenance source | Identifies the future Aegis-controlled source that records or attests the decision. Executor-written-only logs are not sufficient. | FUTURE_CONTRACT_ONLY |

Decision status meanings:

| Status | Required meaning |
| --- | --- |
| `ALLOW` | Future mediator permits a narrow, declared, classified, canonical, evidence-bound write. This status is invalid for protected, unknown, unclassified, or undeclared targets. |
| `DENY` | Future mediator rejects the attempted write by policy. Denials still require evidence binding to the request and reason. |
| `BLOCKED` | Future review cannot proceed because a required mechanism, provenance source, coverage input, or safe boundary is absent or unsafe. |
| `NEEDS_REVIEW` | Future mediator cannot safely decide without a separate reviewed grant or boundary. It must not write by default. |
| `NOT_CHECKED` | No valid mediator judgment has been made. This is not pass, not allow, not deny proof, and not enforcement. |

Missing, ambiguous, or non-authoritative decision records must fail closed.

## 6. Required Denial Classes

A future mediator must deny or block the classes below unless a later,
separate, reviewed boundary explicitly narrows and implements them. This
document does not implement those denials.

| Denial class | Required future stance |
| --- | --- |
| direct `.aeg/` write | Deny executor-authored create, modify, append, replace, delete, rename, chmod, chown, move, or metadata mutation under `.aeg/`. |
| path traversal into `.aeg/` | Deny submitted paths that resolve into `.aeg/` through traversal, alternate separators, encoding, normalization, case ambiguity, or lexical gaps. |
| symlink/alias into `.aeg/` | Deny symlink, hardlink where applicable, mount, worktree, absolute path, or platform alias attempts that resolve into `.aeg/`. |
| outside repo write | Deny writes outside approved repository roots or approved declared output roots. Unknown root membership fails closed. |
| undeclared repo write | Deny tracked or untracked repo mutation outside declared future manifest or grant scope. |
| delete/chmod/chown | Deny destructive and permission mutation by default, including truncation, recursive cleanup, ACL, executable bit, owner, and mode changes. |
| git ref / git metadata write | Deny branch, tag, ref, history, index, hook, config, worktree, remote, release ref, and equivalent git metadata mutation. |
| remote write | Deny push, force push, release, package, issue, PR state mutation, external storage, or other network-backed mutation. |
| raw shell or unmediated `write_file` bypass | Deny or make unavailable any write path that can bypass the mediator. Structured tool calls are still capabilities. |
| secret/.env write | Deny creating, modifying, exporting, printing, staging, persisting, logging, or transmitting secrets, tokens, credentials, `.env` values, or environment-derived sensitive data. |
| provider/network/API mutation | Deny provider-side state, model state, prompt storage, fine-tuning inputs, API-side files, credentials, network/API mutation, or externally mutable state. |

Each denial class must be evidence-bound in a future implementation. Absence of
observed mutation alone is not enough if the decision provenance and denial
reason are missing or executor-written only.

## 7. Evidence And Provenance Contract

Future mediator evidence and provenance records must satisfy the contract below.
This document does not create an evidence store, ledger record, recorder,
external anchor, permission boundary, or tamper-proof storage.

Required future evidence rules:

- allowed writes require evidence binding.
- denied writes require evidence binding.
- mediator decision provenance must be Aegis-controlled.
- executor self-report is not proof.
- `reported_only` is not a judgment basis.
- executor-written-only mediator logs are not proof.
- mismatch between request, decision, evidence, and observed state must be
  verify-rejected.
- mediator logs cannot be executor-written only.
- missing evidence must fail closed.
- secret material must not be recorded in evidence.
- runtime artifacts must not become proof merely by path or filename.

Minimum future evidence binding fields:

- request id.
- decision id.
- actor / executor identity placeholder.
- operation type.
- write class.
- submitted target path or safe redacted descriptor.
- canonical path or fail-closed canonicalization status.
- declared output scope or explicit absence.
- repo boundary classification.
- `.aeg/` boundary classification.
- decision status.
- reason code.
- fail-closed status where applicable.
- provenance source.
- evidence recorder identity or Aegis-controlled record source.
- expected observed-state summary.
- tracked/untracked artifact classification.
- verification requirement.

Evidence binding is support for future verification. It is not a tamper-proof
evidence store by itself and does not prove external enforcement.

## 8. Verify Contract

Future verify must reject unsafe or incomplete mediator records. This document
does not implement verify code, tests, fixtures, or enforcement.

Required future verify rejection rules:

- reject declared vs observed decision mismatch.
- reject expected vs actual evidence mismatch.
- reject canonical path mismatch.
- reject lexical-only allow decisions that ignore resolved targets.
- reject missing or ambiguous repo boundary classification.
- reject missing or ambiguous `.aeg/` boundary classification.
- reject allowed writes outside declared output scope.
- reject denied writes with missing denial evidence.
- reject mediator decisions whose provenance is executor-written only.
- reject executor self-report as proof.
- reject `reported_only` as judgment basis.
- reject missing tracked/untracked artifact distinction.
- reject runtime artifacts masquerading as tracked source or evidence.
- reject tracked `.aeg/.env` presence as a negative assertion failure.
- reject `NOT_CHECKED` as pass.

Tracked and untracked artifacts must be judged separately. Future verify must
not accept an untracked file as harmless merely because it is absent from git
diff, and must not accept a tracked file as safe merely because it appears in a
declared path list. The classification, mediator decision, evidence binding,
and observed state must agree.

The `.aeg/.env` tracked negative assertion is mandatory:

```text
tracked .aeg/.env = BLOCKED
tracked .env = BLOCKED unless a separate reviewed secret boundary explicitly
               authorizes non-secret placeholder tracking
NOT_CHECKED != PASS
```

## 9. PASS Criteria

This mediator interface contract is ready for user review only if all criteria
below are true:

- the contract is complete for request, decision, evidence/provenance, verify,
  denial classes, previous-gate relation, non-goals, and canonical
  distinctions.
- the contract is future-only.
- the contract is conservative and fail-closed.
- the contract does not claim enforcement.
- the contract does not implement a mediator, broker, wrapper, tool, bypass
  test, fixture, enforcement hook, external boundary, or live executor grant.
- live executor authority remains `ON_HOLD`.
- current scaffold state remains `SCAFFOLD_ONLY_NOT_ENFORCED`.
- `write_mediation_enabled=false` remains the current baseline.
- `write_mediation_enforced=false` remains the current baseline.
- `write_classes_granted=[]` remains the current baseline.
- `write_mediation_evidence_status=NOT_CHECKED` remains not pass.
- executor self-report is not proof.
- `reported_only` is not a judgment basis.
- `.aeg/` is not described as executor-isolated.

Expected review status when these checks pass:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```

## 10. BLOCKED Criteria

This mediator interface contract or any later scaffold/implementation review is
`BLOCKED` if any condition below is true:

- it grants live executor authority.
- it implements an actual mediator.
- it implements broker, wrapper, shell wrapper, tool wrapper, or tool
  execution.
- it implements bypass tests or fixtures.
- it implements actual mediated write enforcement.
- it implements external enforcement, `.aeg/` permission hardening, OS
  separation, sandboxing, IPC, or network/provider/API call control.
- it treats scaffold metadata as enforcement.
- it treats `SCAFFOLD_ONLY_NOT_ENFORCED` as safe, pass, or enforced.
- it treats `NOT_CHECKED` as `PASS`.
- it uses executor self-report as proof.
- it uses `reported_only` as a judgment basis.
- it claims `.aeg/` is executor-isolated.
- it records or tracks secrets, `.env` values, release artifacts, deploy
  outputs, or live runtime evidence as part of this contract.
- it performs main direct push or main merge.

Any one of these conditions keeps the safe default at `hold_current_state` and
prevents live executor authority review.

## 11. Relation To Previous Gates

This mediator interface contract is downstream of the completed Phase 10 gates:

- Phase 10 Write Bypass Test Plan v0 defines the WBYP inventory.
- Phase 10 Write Bypass Test Harness Scope v0 defines future harness input,
  output, and fixture boundaries.
- Phase 10 Mediated Write Boundary Implementation Scope Plan v0 defines the
  sequencing for future mediation work.
- Phase 10 Write Mediation Verify Criteria v0 defines future `PASS`,
  `BLOCKED`, and mismatch-rejection expectations.
- Phase 10 Mediated Write Boundary Scaffold v0 records scaffold metadata and
  overclaim rejection, but not enforcement.
- Phase 10 Write Bypass Test Harness Scaffold v0 records WBYP-001 through
  WBYP-025 registry metadata/schema/verify vocabulary only, without actual
  bypass tests, fixtures, write attempts, mediation, or enforcement.
- This contract defines mediator interface boundaries for future request,
  decision, evidence/provenance, and verify records.

This document does not supersede prior gates. It narrows the next review step
between harness scope, implementation sequencing, and any future mediator
contract scaffold or harness scaffold.

## 12. Non-goals

This document does not implement or authorize:

- actual mediator.
- broker, wrapper, shell wrapper, or tool wrapper.
- `write_file`, `read_file`, `run_command`, `http_request`, git, provider, or
  other tool implementation.
- bypass tests.
- test fixtures.
- actual mediated write enforcement.
- external enforcement.
- `.aeg/` permission hardening.
- OS user separation.
- process separation.
- sandbox or container.
- IPC.
- evidence store lock.
- external anchor.
- network call.
- API call.
- provider call.
- model call.
- provider/network/API mutation.
- live executor authority grant.
- release, publish, or deploy.
- secret, token, credential, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- `.aeg/.env` tracking.
- main direct push.
- main merge.

## 13. Recommended Next Gate

Recommended next gate:

```text
Phase 10 Write Bypass Test Harness Scaffold v0
```

Alternative next gate:

```text
Phase 10 Mediator Contract Scaffold v0
```

This document implements neither gate. The conservative path is to scaffold the
future harness or mediator contract without creating actual enforcement or live
executor authority.

## 14. Canonical Distinctions To Preserve

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
harness scope != harness implementation
mediator interface contract != mediator implementation
```

These distinctions are review requirements. Later work must not use this
contract, current scaffold metadata, executor narrative, executor-written logs,
or report-only claims to say that mediation, enforcement, harness
implementation, evidence isolation, external anchoring, or live executor
authority already exists.

## 15. Review Checklist

This mediator interface contract is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- no actual mediator is implemented.
- no broker, wrapper, shell wrapper, tool wrapper, or tool execution is added.
- no actual bypass tests are implemented.
- no actual fixtures are created.
- no actual mediated write enforcement is implemented.
- no external enforcement is implemented.
- no `.aeg/` permission hardening, OS separation, sandbox, IPC, network/API, or
  provider/model boundary is implemented.
- no live executor authority is granted.
- current baseline remains `SCAFFOLD_ONLY_NOT_ENFORCED`.
- `write_mediation_enabled=false` remains a baseline fact.
- `write_mediation_enforced=false` remains a baseline fact.
- `write_classes_granted=[]` remains a baseline fact.
- `write_mediation_evidence_status=NOT_CHECKED` remains not pass.
- future mediator request fields are present.
- future mediator decision fields are present.
- required denial classes are present.
- evidence/provenance contract is present.
- verify contract is present.
- `PASS` and `BLOCKED` criteria are present.
- relation to previous gates is present.
- non-goals are explicit.
- recommended next gate is present.
- canonical distinctions are preserved.
- forbidden implementation work is absent.
- secrets, runtime artifacts, tracked `.aeg/`, tracked `.aeg/.env`, and tracked
  `.env` files are absent.

Expected review status when these checks pass:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```

Final safe default:

```text
hold_current_state
```
