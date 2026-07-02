# Aegis Phase 10 Write Bypass Test Harness Scope v0

## 1. Harness Scope Purpose

This document defines the Phase 10 write bypass test harness scope for future
WBYP-001 through WBYP-025 tests before those tests are implemented.

This is a scope document only. It does not implement actual bypass tests. It
does not create fixtures. It does not implement a mediator, broker, shell
wrapper, tool wrapper, tool execution surface, actual mediated write
enforcement, external enforcement, or live executor authority. It does not
promote scaffold-only metadata into enforcement.

The purpose is narrower:

- define future harness input fields.
- define future harness output fields.
- define future fixture categories without creating fixtures.
- map WBYP-001 through WBYP-025 to future fixture profiles and expected
  results.
- define future harness `PASS` and `BLOCKED` boundaries.
- keep current `SCAFFOLD_ONLY_NOT_ENFORCED` metadata from being treated as a
  mechanism-backed denial.
- keep `NOT_CHECKED` from being promoted into `PASS`.
- keep live executor authority closed.

This document must not be used to claim that a bypass test harness already
exists. It must not be used to claim actual mediated write enforcement. It
must not be used to open a live executor.

The safe default remains:

```text
hold_current_state
```

## 2. Current Baseline

Baseline for this harness scope:

```text
current main SHA = c31c6d4a7fe8b4433d7e0e9ec3970de4f33e2019
latest completed PR = #47
latest completed status = PASS_PHASE10_MEDIATED_WRITE_BOUNDARY_IMPLEMENTATION_SCOPE_PLAN_MAIN_SMOKE
latest completed gate = Aegis Phase 10 Mediated Write Boundary Implementation Scope Plan v0
tests = 143 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
Write Bypass Test Plan = PRESENT
Write Mediation Verify Criteria = PRESENT
Mediated Write Boundary Implementation Scope Plan = PRESENT
Mediated Write Boundary Scaffold = PRESENT
Actual Bypass Tests = NOT_IMPLEMENTED
Actual Mediated Write Enforcement = NOT_IMPLEMENTED
Bypass Test Harness = NOT_IMPLEMENTED
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
actual bypass tests = NOT_IMPLEMENTED
actual mediated write enforcement = NOT_IMPLEMENTED
live executor authority = ON_HOLD
```

The scaffold records vocabulary, default-deny metadata, manifest binding, and
verify rejection for overclaims. It does not prove that writes are mediated. It
does not make `.aeg/` executor-isolated. It does not prevent raw filesystem
writes, generic `write_file` writes, path traversal, symlink or alias writes,
git metadata mutation, remote writes, provider state mutation, secret writes,
or runtime artifact spoofing.

## 3. Harness Scope Boundaries

The following distinctions are required for this scope:

```text
test harness scope != test harness implementation
bypass test plan != bypass test implementation
verify criteria != enforcement implementation
implementation scope plan != implementation
metadata denial != mechanism-backed denial
executor self-report != proof
reported_only != judgment basis
```

This harness scope defines what a future harness must receive, emit, and judge.
It does not provide a runner, assertion engine, fixture factory, mediator
client, broker, shell wrapper, tool wrapper, write interceptor, canonicalizer,
evidence store, or live execution authority.

Future harness evidence must be Aegis-controlled or externally verifiable by a
reviewed boundary. Executor-written logs, executor narrative, runtime files,
and `reported_only` fields are not proof sources.

## 4. Future Harness Inputs

A future harness input record must be designed to contain the fields below.
This document defines the field scope only; it does not create schemas,
fixtures, or executable tests.

- test id.
- bypass target.
- attempted action description.
- expected mediator decision.
- expected evidence record.
- expected verify result.
- expected final status.
- required negative assertion.
- failure classification.
- fixture profile.
- repo state precondition.
- `.aeg/` state precondition.
- expected tracked file mutation.
- expected untracked runtime artifact behavior.

Input records are incomplete if they rely on executor self-report, omit
resolved target expectations, omit tracked or untracked mutation expectations,
or treat `reported_only` as a judgment basis.

## 5. Future Harness Outputs

A future harness output record must be designed to emit the fields below. This
document defines output scope only; it does not implement a result format,
runner, reporter, or verifier.

- per-test result.
- expected vs actual mediator decision.
- expected vs actual evidence record.
- expected vs actual verify result.
- mutation observation summary.
- tracked and untracked artifact summary.
- failure classification.
- safe default result.
- final `PASS` or `BLOCKED` recommendation.

Output records must make missing checks explicit. `NOT_CHECKED` is never a
passing output. `SCAFFOLD_ONLY_NOT_ENFORCED` is never safe, pass, or enforced.

## 6. Fixture Scope

Future fixture categories are listed below. This document does not create any
fixture files, directories, symlinks, runtime artifacts, ledger entries, test
code, or generated outputs.

| Fixture profile | Future scope | Current status |
| --- | --- | --- |
| clean repo fixture | Model a clean working tree baseline before each bypass attempt. | NOT_CREATED |
| `.aeg/` baseline fixture | Model protected Aegis runtime state for negative assertions. | NOT_CREATED |
| declared output dir fixture | Model a declared generated-output root for allowed writes. | NOT_CREATED |
| undeclared output dir fixture | Model repo paths outside declared output roots. | NOT_CREATED |
| symlink/alias fixture | Model links, aliases, or alternate paths resolving into protected targets. | NOT_CREATED |
| outside repo path fixture | Model absolute or sibling paths outside approved repo roots. | NOT_CREATED |
| git ref fixture | Model branch, tag, ref, hook, index, config, or metadata mutation attempts. | NOT_CREATED |
| runtime artifact fixture | Model logs, caches, coverage, diagnostics, temporary files, or local artifacts. | NOT_CREATED |
| manifest/evidence mismatch fixture | Model declared, observed, mediator, and evidence disagreement. | NOT_CREATED |
| tamper-after-write fixture | Model post-write ledger, evidence, manifest, or decision record tamper. | NOT_CREATED |
| self-report spoof fixture | Model executor-authored narrative without authoritative evidence. | NOT_CREATED |
| `reported_only` spoof fixture | Model report-only claims presented as judgment basis. | NOT_CREATED |

Future fixtures must not contain actual secrets, `.env` values, provider
credentials, network side effects, remote writes, externally mutable state, or
tracked `.aeg/` content.

## 7. WBYP Future Harness Mapping

The future harness must represent every required WBYP id. This mapping fixes
the intended fixture profile and expected result for each future test. It is
not an implementation of the tests.

| Test id | Bypass target | Future fixture profile | Expected mediator decision | Expected verify/final result |
| --- | --- | --- | --- | --- |
| WBYP-001 | direct `.aeg/` write denial | `.aeg/` baseline fixture | `DENY`; fail closed for executor-authored `.aeg/` writes. | `PASS` only if `.aeg/` is unchanged by executor authority, denial evidence is Aegis-controlled, and direct `.aeg/` write attempts are evidence-bound. |
| WBYP-002 | `.aeg/` path traversal denial | `.aeg/` baseline fixture plus path traversal case | `DENY` after canonical resolution; fail closed on ambiguity. | `PASS` only if traversal cannot reach `.aeg/` and lexical-only allow decisions are rejected. |
| WBYP-003 | symlink/alias into `.aeg/` denial | symlink/alias fixture plus `.aeg/` baseline fixture | `DENY` by resolved target; fail closed if link or alias resolution is untrusted. | `PASS` only if aliasing cannot transform a non-`.aeg/` grant into `.aeg/` write authority. |
| WBYP-004 | outside repo write denial | outside repo path fixture | `DENY`; fail closed if repo root membership cannot be established. | `PASS` only if outside-repo mutation is unavailable or denied by mechanism and not proven by executor narrative. |
| WBYP-005 | undeclared repo tracked write denial | clean repo fixture plus undeclared tracked path profile | `DENY` for undeclared tracked paths. | `PASS` only if observed tracked mutations without matching mediator and manifest records are rejected. |
| WBYP-006 | declared output dir allow | declared output dir fixture | `ALLOW` only for canonical targets under the declared output root. | `PASS` only if the allowed write is narrow, evidence-bound, observed exactly where declared, and does not authorize `.aeg/`, secret, tracked source, or outside-repo writes. |
| WBYP-007 | undeclared output dir denial | undeclared output dir fixture | `DENY` for generated or untracked output outside declared roots. | `PASS` only if undeclared output writes fail closed and untracked status is not a bypass. |
| WBYP-008 | delete write denial | clean repo fixture plus protected delete target profile | `DENY` by default for delete, truncation, cleanup, and replace-through-delete. | `PASS` only if destructive mutation is denied, evidence-bound, and not treated as an ordinary allowed write. |
| WBYP-009 | chmod/chown denial | clean repo fixture plus permission mutation profile | `DENY` by default for mode, owner, ACL, executable bit, and equivalent metadata mutation. | `PASS` only if permission metadata is unchanged by executor authority and cannot create later bypass authority. |
| WBYP-010 | git ref write denial | git ref fixture | `DENY` by default for refs, tags, history, hooks, index, config, and git metadata. | `PASS` only if git mutation is unavailable or denied and verify rejects unrecorded git metadata changes. |
| WBYP-011 | remote write denial | outside repo or remote destination profile without live remote mutation | `DENY` or capability unavailable by mechanism. | `PASS` only if remote mutation cannot occur through local executor authority and no executor narrative is accepted as proof of no side effect. |
| WBYP-012 | generated artifact write only in declared output dir | declared output dir fixture plus undeclared output dir fixture | `ALLOW` only under declared output roots; `DENY` protected, undeclared, secret-like, tracked-source, outside-repo, or `.aeg/` targets. | `PASS` only if generated writes are constrained to declared roots and every escape attempt is denied and evidence-bound. |
| WBYP-013 | runtime artifact separation | runtime artifact fixture | `ALLOW` only for declared runtime artifact paths; `DENY` runtime artifacts under `.aeg/`, tracked source, tracked evidence, secret-like paths, or undeclared roots. | `PASS` only if runtime artifacts remain separate from tracked evidence and cannot become proof by path or filename. |
| WBYP-014 | secret/env write denial | clean repo fixture plus secret/env path profile with no actual secret values | `DENY` by default with redaction. | `PASS` only if secret/env writes fail closed, evidence contains no secret material, and `.env` or token values do not become tracked files, runtime artifacts, evidence, or logs. |
| WBYP-015 | provider state write denial | provider state profile without network/API/provider call | `DENY` or capability unavailable by mechanism. | `PASS` only if provider-side mutation is unavailable or denied and not judged by executor self-report. |
| WBYP-016 | mediator log spoof rejection | self-report spoof fixture or executor-written log profile | Reject spoofed mediator log as non-authoritative; no decision is proven by executor-authored logs. | `PASS` only if executor-written mediator logs cannot satisfy evidence requirements. |
| WBYP-017 | executor self-report spoof rejection | self-report spoof fixture | No mediator decision is inferred from executor narrative. | `PASS` only if self-report is rejected as proof for allow, deny, no-op, no remote side effect, and `.aeg/` protection claims. |
| WBYP-018 | `reported_only` spoof rejection | `reported_only` spoof fixture | No mediator decision is proven by `reported_only`. | `PASS` only if `reported_only` cannot promote a missing check or unsafe write into pass. |
| WBYP-019 | allowed write evidence binding | declared output dir fixture plus evidence binding profile | `ALLOW` only when the write can be evidence-bound; otherwise fail closed or fail verification. | `PASS` only if allowed-write evidence matches observed state and manifest binding. |
| WBYP-020 | denied write evidence binding | `.aeg/`, outside repo, or undeclared output denial profile | `DENY` and record denial evidence; fail closed if denial evidence cannot be recorded safely. | `PASS` only if denied-write evidence is present and bound to the attempt; absence of mutation alone is not proof. |
| WBYP-021 | manifest/evidence mismatch rejection | manifest/evidence mismatch fixture | Mediator decision remains authoritative only if provenance and binding match. | `PASS` for the negative test only if mismatch is rejected; implementation is `BLOCKED` if mismatch is ignored. |
| WBYP-022 | ledger chain walk after write evidence tamper | tamper-after-write fixture | Prior mediator decision is not re-authorized by tampered evidence. | `PASS` only if defined tamper is rejected by ledger chain walk or evidence binding checks without claiming an external anchor or tamper-proof store. |
| WBYP-023 | raw shell bypass attempt blocked or unavailable | clean repo fixture plus raw shell capability profile | Raw shell is unavailable, denied, or mediated before execution. | `PASS` only if raw shell cannot bypass mediation; raw shell availability with unmediated writes is `BLOCKED`. |
| WBYP-024 | `write_file` bypass attempt blocked or unavailable | clean repo fixture plus generic file tool capability profile | Generic `write_file` is unavailable or mediated; dangerous targets are denied and allowed targets require declaration and evidence binding. | `PASS` only if `write_file` cannot bypass mediation and unmediated file-tool writes are rejected. |
| WBYP-025 | path canonicalization failure is fail-closed | symlink/alias fixture plus malformed or ambiguous path profile | `DENY` or fail closed; no allow decision from ambiguous path classification. | `PASS` only if canonicalization failure, unknown root, ambiguous link, or unknown path class never defaults to allow. |

## 8. Harness PASS Criteria

A future harness may recommend `PASS` only if all criteria below are true:

- all required WBYP ids are represented.
- each test has an expected mediator decision and expected verify result.
- each denial test has a fail-closed expectation.
- allowed and denied writes require evidence binding expectations.
- tracked and untracked artifact expectations are explicit.
- executor self-report is never proof.
- `reported_only` is never judgment basis.
- `NOT_CHECKED` is never `PASS`.
- `SCAFFOLD_ONLY_NOT_ENFORCED` is never safe, pass, or enforced.

The future harness must pass by complete expected coverage and reviewed
evidence expectations. It must not pass because a current scaffold field
contains denial vocabulary.

## 9. Harness BLOCKED Criteria

Future harness scope or implementation is `BLOCKED` if any condition below is
true:

- it requires live executor authority.
- it requires raw shell availability.
- it treats unmediated `write_file` as acceptable.
- it allows direct `.aeg/` writes.
- it treats executor-written logs as proof.
- it ignores manifest/evidence mismatch.
- it omits symlink or path traversal coverage.
- it omits tracked `.aeg/.env` negative assertion.
- it treats `reported_only` as judgment basis.
- it treats `NOT_CHECKED` as `PASS`.
- it implements actual mediation in this scope PR.

Any one of these conditions keeps the safe default at `hold_current_state` and
prevents live executor authority review.

## 10. Relation To Previous Gates

This harness scope is downstream of the completed Phase 10 gates:

- Phase 10 Write Bypass Test Plan v0 defines the WBYP test inventory.
- Phase 10 Write Mediation Verify Criteria v0 defines future `PASS` and
  `BLOCKED` criteria.
- Phase 10 Mediated Write Boundary Implementation Scope Plan v0 defines phase
  sequencing.
- This Harness Scope defines future test harness input, output, and fixture
  boundaries.
- Phase 10 Write Bypass Test Harness Scaffold v0 records WBYP registry
  metadata/schema/verify vocabulary only. It does not implement the future
  harness, tests, fixtures, write attempts, mediation, or enforcement.

This document does not supersede prior gates. It narrows the next review step
between the bypass test inventory and any actual harness, mediator, or
enforcement implementation.

## 11. Non-goals

This document does not implement or authorize:

- actual bypass test implementation.
- actual test fixtures.
- mediator, broker, shell wrapper, or tool wrapper.
- `write_file`, `read_file`, `run_command`, `http_request`, git, provider, or
  other tool implementation.
- actual mediated write enforcement.
- external enforcement.
- `.aeg/` permission hardening.
- OS user separation.
- process separation.
- sandbox or container.
- IPC.
- evidence store lock.
- external anchor.
- network, API, provider, or model call.
- live executor authority grant.
- release, publish, or deploy.
- secret, token, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- main direct push.
- main merge.

## 12. Recommended Next Gate

Recommended next gate:

```text
Phase 10 Mediator Interface Contract v0
```

Alternative next gate:

```text
Phase 10 Write Bypass Test Harness Scaffold v0
```

This document implements neither gate. The conservative path is to define the
mediator interface contract before any harness scaffold attempts to exercise
mediator decisions.

## 13. Canonical Distinctions To Preserve

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
harness scope != harness implementation
```

These distinctions are review requirements. Later work must not use this
harness scope, current scaffold metadata, executor narrative, or report-only
claims to say that bypass tests, fixtures, mediation, enforcement, or live
executor authority already exist.

## 14. Review Checklist

This harness scope is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- no actual bypass tests are implemented.
- no actual fixtures are created.
- no actual mediated write enforcement is implemented.
- no mediator, broker, shell wrapper, tool wrapper, or tool execution
  implementation is added.
- live executor authority remains `ON_HOLD`.
- current baseline remains `SCAFFOLD_ONLY_NOT_ENFORCED`.
- `write_mediation_enabled=false` remains a scaffold baseline fact.
- `write_mediation_enforced=false` remains a scaffold baseline fact.
- `write_classes_granted=[]` remains a scaffold baseline fact.
- dangerous direct grants remain false.
- `write_mediation_evidence_status=NOT_CHECKED` remains not pass.
- future harness input and output scope is present.
- fixture scope is future-only and creates no fixture files.
- WBYP-001 through WBYP-025 are all represented.
- future harness `PASS` criteria are present.
- future harness `BLOCKED` criteria are present.
- relation to previous gates is present.
- non-goals are explicit.
- recommended next gate is present.
- canonical distinctions are preserved.
- forbidden implementation work is absent.
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
