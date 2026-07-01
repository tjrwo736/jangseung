# Aegis Phase 9 Evidence Store Integrity Implementation Scope Plan v0

## 1. Purpose

This document narrows the minimum implementation path for `.aeg/` evidence
store integrity before any live executor receives authority.

This is a scope plan only. It does not implement `.aeg/` permission hardening,
ownership changes, process isolation, sandboxing, containers, IPC, evidence
store locks, signatures, hash chains, structured tool execution, shell access,
network access, provider access, live executor capability grants, or runtime
behavior changes.

The safe default remains:

```text
hold_current_state
```

The current baseline is:

```text
main = 00c52b0750284a8a377f27b28908de6e5bb9d863
latest completed PR = #33
latest completed status = PASS_PHASE9_TOOL_SURFACE_CAPABILITY_EXPOSURE_EVIDENCE_STORE_INTEGRITY_MAIN_SMOKE
```

This plan builds on:

```text
docs/aeg_integrity_design_v0.md
```

## 2. Current Blocker Statement

`.aeg/` evidence store integrity is a hard blocker before live executor
authority. The current evidence store is folder-local but not
executor-isolated.

Current state:

```text
.aeg/ evidence store = FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED
evidence_store_is_executor_isolated = false
evidence_store_integrity_status = NOT_CHECKED
current no-op executor capability = NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION
live executor authority = ON_HOLD
```

The current code guarantees:

- Aegis runtime writes under `.aeg/`.
- evidence and manifest binding exists.
- replay and tamper checks exist for current scaffold metadata.

The current code does not guarantee:

- an executor cannot write `.aeg/`.
- `.aeg/` is executor-isolated.
- the evidence store is tamper-proof.
- a future live executor is safe.

Required invariants:

```text
.aeg/ exists and is gitignored != .aeg/ is executor-isolated
evidence binding exists != evidence store is tamper-proof
tamper-evident != tamper-proof
structured tool call != safe capability
current no-op executor safe != future live executor safe
capability-denied != path-hidden
NOT_CHECKED != PASS
```

## 3. Candidate Comparison

Prevention means the executor is prevented from mutating `.aeg/`. Detection
means mutation is made visible after the fact. Detection is useful, but it is
not prevention.

| Candidate | Prevention vs detection | Portability cost | Setup complexity | Single entry point impact | Folder-local state impact | External dependency impact | User friction | Implementation complexity | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Complete executor-isolated evidence store | Prevention first. Detection still useful but secondary. | High. Likely platform-sensitive if OS permissions, process separation, sandboxing, or containers are used. | High. Requires a real boundary outside executor control. | Medium to high. May need launcher, subprocess, recorder, or sandbox lifecycle. | May preserve `.aeg/`, but ownership, mount, or write-routing rules become part of correctness. | Low to medium if local-only; higher if an external trust or sandbox dependency becomes mandatory. | High. Users may need setup steps or platform-specific behavior. | High. Requires enforcement, verification, and failure-mode design. | Lowest write-prevention risk if implemented correctly, but compatibility and bypass review remain hard. |
| B. Tamper-evident ledger | Detection only. It can show inconsistency, not stop writes. | Low to medium. Fits local operation unless an external anchor is required. | Low to medium. Needs sequencing, replay, and verification semantics. | Low. Can be added to existing evidence flow. | Preserves folder-local `.aeg/`. | None for a local-only ledger; optional external anchors would add dependency. | Low. Mostly automatic after implementation. | Medium. Ledger fields, replay, tamper cases, and status vocabulary must be exact. | Executor with broad write authority may rewrite ledger and local anchors. Tamper-evident is not tamper-proof. |
| C. `capability_write_aeg_state` denial model | Prevention for the named capability if enforced outside executor control. | Low to medium. Compatible with local execution when the tool surface is mediated. | Medium. Must define and verify denied authority paths. | Low. Aligns with one Aegis entry point and Aegis runtime as recorder. | Preserves folder-local `.aeg/`. | Low. No required external account. | Low to medium. Users see denied authority rather than setup burden. | Medium. Hard part is proving denial is not executor self-report. | Insufficient if raw shell, generic `write_file`, repo-outside write, or another broad filesystem path can reach `.aeg/`. |
| D. A + B | Prevention plus detection. Strongest combined model. | Highest. Inherits A and B costs. | Highest. Requires both real isolation and ledger verification. | Medium to high. | May preserve `.aeg/`, but with stricter boundary rules. | Low to medium, depending on isolation design. | High. | Very high. | Best security direction long term, but too heavy as the immediate minimum path. |
| E. B + C | Detection plus enforced capability denial for `.aeg/` state writes. | Low to medium. Designed to fit local, single-entry operation. | Medium. Requires ledger verification and externally enforced capability denial. | Low. Keeps Aegis runtime as the recorder and avoids a new required launcher boundary for the first step. | Preserves folder-local `.aeg/` while admitting it is not inherently isolated. | Low. No required external account or service. | Low to medium. | Medium. Smaller than A or D, but must close broad write bypasses before live authority. | Not tamper-proof. Residual risk remains if raw shell, generic file writes, repo-outside writes, or executor-controlled recorder paths can mutate `.aeg/`. |

### Candidate A Notes

Candidate A is the clean prevention answer: make `.aeg/` executor-isolated by
construction. It is the strongest option for a future live executor, but it is
not the lightest immediate implementation path under the current Aegis
constitution. A complete isolation answer likely needs OS/user separation,
process separation, sandboxing, a mediated recorder, or equivalent enforcement.
Those mechanisms add portability cost, setup complexity, and review surface.

Candidate A is desirable as a later hardening destination. It is not the
recommended next step because the current blocker needs a minimal path that can
be implemented and verified before live authority while preserving folder-local
state and a single entry point.

### Candidate B Notes

Candidate B adds a tamper-evident ledger. This improves detection and replay:
future verification can identify missing, reordered, inconsistent, or rewritten
ledger state if there is a trustworthy prior anchor or internally consistent
expected chain.

Candidate B does not prevent executor writes. If an executor can rewrite the
ledger and all local anchors, local tamper evidence may be destroyed or made
ambiguous. Candidate B must therefore never claim `EVIDENCE_STORE_CLEAN` or
tamper-proof status by itself.

### Candidate C Notes

Candidate C denies `capability_write_aeg_state` to the executor and keeps Aegis
runtime as the evidence writer. This is a prevention direction only when denial
is enforced outside executor control.

Candidate C is insufficient if the executor can still reach `.aeg/` through raw
shell authority, a generic `write_file` tool, repo-outside write authority, an
unmediated path traversal, or a recorder path controlled by the executor.
Capability denial cannot be accepted as an executor self-report.

### Candidate D Notes

Candidate D combines complete executor isolation and a tamper-evident ledger.
It is the strongest combined answer, but it has the highest implementation and
compatibility burden. It should remain a later target or a stricter future
pre-live requirement if Candidate E cannot close the broad write bypasses.

### Candidate E Notes

Candidate E combines a tamper-evident ledger with an enforced
`capability_write_aeg_state` denial model. It does not claim `.aeg/` is
tamper-proof. It creates a practical minimum path:

- ledger evidence makes `.aeg/` mutation detectable within defined limits.
- capability denial keeps the executor from receiving direct Aegis state write
  authority.
- broad write paths must be denied or mediated before live executor authority.
- Aegis runtime remains the recorder for evidence state.

Candidate E is the recommended next implementation path candidate.

## 4. Recommended Path

Recommended next implementation path candidate:

```text
Candidate E: tamper-evident ledger + capability_write_aeg_state denial model
```

Rationale:

- It best matches the current Aegis constitution: zero required external
  accounts, one entry point, and folder-local state under `.aeg/`.
- It directly addresses the current hard blocker without pretending that
  folder-local state is already executor-isolated.
- It separates detection from prevention. The ledger provides detection. The
  capability denial model provides prevention only for explicitly denied and
  externally enforced write paths.
- It keeps `NOT_CHECKED` honest until implementation and verification exist.
- It is smaller than Candidate A or D, while still requiring proof that broad
  write paths cannot bypass `.aeg/` protection.

Candidate E is sufficient as the next minimum path only if the future
implementation proves all of the following before live executor authority:

- `capability_write_aeg_state` is denied by enforcement outside executor
  self-report.
- raw shell authority is denied or mediated so it cannot write `.aeg/`.
- generic file write authority is denied or mediated so it cannot target
  `.aeg/`.
- repo-outside write authority cannot become a path around `.aeg/` controls.
- the ledger verifier detects defined missing, reordered, inconsistent, or
  tampered evidence-store state.
- status vocabulary distinguishes `NOT_CHECKED`, tamper-evident, tamper-proof,
  and any future clean state.

Candidate E is not sufficient to claim complete tamper-proof isolation. If a
future live executor must receive broad filesystem or raw shell authority,
Candidate A or D must be revisited before that authority is granted.

## 5. Proposed Next Gates

### Gate 1: Phase 9 Evidence Store Tamper-Evident Ledger Scope/Scaffold v0

Goal:

- define local ledger semantics, status names, manifest binding relationship,
  expected failure modes, and replay scope.

Acceptance direction:

- ledger state is explicitly tamper-evident, not tamper-proof.
- ledger status cannot promote `.aeg/` integrity to `CLEAN` by existence alone.
- missing, reordered, or inconsistent ledger metadata has a `REPLAY_FAILED`,
  `INVALID_EVIDENCE`, `NOT_CHECKED`, or `BLOCKED` path as appropriate.
- no signature, hash chain, lock, sandbox, or permission behavior is introduced
  in the scope gate itself.

### Gate 2: Phase 9 Capability Denial for `.aeg/` State Scope/Scaffold v0

Goal:

- define denied `.aeg/` write capability names, enforcement ownership, manifest
  fields, and verify replay expectations.

Acceptance direction:

- `capability_write_aeg_state` is denied by a control outside executor
  self-report.
- raw shell, generic `write_file`, repo-outside write, and recorder mutation
  paths are explicitly treated as possible bypass paths.
- path hiding is allowed only as hygiene, not as the security boundary.
- no live executor capability is granted.

### Gate 3: Phase 9 Evidence Store Integrity Verify Replay v0

Goal:

- add verify behavior that checks ledger metadata and capability denial
  metadata without promoting unchecked integrity to clean status.

Acceptance direction:

- evidence binding remains separate from evidence-store integrity.
- `evidence_store_integrity_status = NOT_CHECKED` is not promoted to `PASS` or
  `CLEAN` by partial metadata.
- tampered or contradictory ledger/capability metadata is rejected by replay.
- verification proves the metadata relationship, not complete OS-level
  isolation.

### Gate 4: Phase 9 Pre-live Executor Integrity Gate v0

Goal:

- require evidence-store integrity gates to pass before any live executor,
  shell, network, provider, or broad filesystem write authority is granted.

Acceptance direction:

- live executor authority remains `ON_HOLD` until the ledger, capability denial,
  and bypass-path review pass.
- any raw shell, generic file write, repo-outside write, provider, or network
  grant remains blocked until the relevant Phase 9 boundaries are implemented
  and verified.
- if broad filesystem authority is still required, Candidate A or D is reopened
  before live authority.

## 6. Acceptance Criteria For Future Implementation

Future implementation is acceptable only if all of the following remain true:

- `.aeg/` integrity is not overstated as `CLEAN` while executor isolation or
  write-denial proof is missing.
- tamper-evident and tamper-proof are separate statuses and separate review
  claims.
- folder-local and executor-isolated are separate facts.
- capability-denied and path-hidden are separate facts.
- `capability_write_aeg_state` denial is enforced by Aegis-controlled code or
  another boundary outside executor self-report.
- raw shell authority cannot be a path to write `.aeg/`.
- generic `write_file` authority cannot be a path to write `.aeg/`.
- repo-outside write authority cannot be a path around `.aeg/` controls.
- evidence binding is not treated as proof that the executor could not modify
  the evidence store.
- the current no-op executor capability status is not used as proof that a
  future live executor is safe.
- `NOT_CHECKED` is not promoted to `PASS` or `CLEAN`.
- live executor authority remains blocked until the pre-live integrity gate
  explicitly passes.

Minimum live-executor precondition:

```text
Before live executor authority, Aegis must have both tamper-evident evidence
store verification and externally enforced denial or mediation of every
executor-controlled write path into .aeg/.
```

This minimum is still not a complete tamper-proof claim. It is the minimum
Candidate E gate for moving from design blocker to a reviewable pre-live
implementation candidate.

## 7. Non-goals

This scope plan does not implement:

- `.aeg/` permission hardening.
- `chmod`.
- `chown`.
- OS user separation.
- process separation.
- sandboxing.
- containers.
- IPC.
- signatures.
- hash chains.
- evidence store locks.
- runtime behavior changes.
- structured tool execution.
- `read_file`, `write_file`, `run_command`, or `http_request` tools.
- live executor capability grants.
- shell calls.
- network calls.
- provider calls.
- model calls.
- planner, multi-step, resume, autonomous loop, or multi-citizen behavior.
- release, publish, or deploy behavior.
- secret, token, API key, or `.env` value recording.
- `.aeg/` git inclusion.
- README, architecture, package metadata, source, or test changes.
- main merge behavior.

## 8. Review Checklist

This document is ready for user review only if:

- changed files are limited to
  `docs/evidence_store_integrity_implementation_scope_plan_v0.md`.
- Candidate A, B, C, D, and E are all compared.
- Candidate E is explicitly recommended as the next implementation path
  candidate.
- proposed next gates are listed.
- tamper-evident is not described as tamper-proof.
- folder-local is not described as executor-isolated.
- capability-denied is not described as path-hidden.
- live executor safety is not overstated.
- forbidden implementation work is absent.
- secrets, `.env` values, and `.aeg/` runtime artifacts are absent.

Expected review status when those checks pass:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```
