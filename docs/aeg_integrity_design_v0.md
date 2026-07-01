# Aegis .aeg Integrity Design v0

## 1. Purpose

This document opens the design question for protecting the folder-local
`.aeg/` evidence store from a future live executor.

This is a design document only. It does not implement `.aeg/` permission
hardening, ownership changes, OS user separation, subprocess separation,
sandboxing, containers, IPC, hash chains, signatures, evidence locks, live
executor write attempts, structured tool execution, shell access, provider
calls, network calls, or runtime behavior changes.

The safe default remains:

```text
hold_current_state
```

The pre-live-executor blocker is:

```text
.aeg/ integrity must be resolved before any live executor receives authority
that could mutate the evidence store.
```

## 2. Current State

The current `.aeg/` state is:

```text
.aeg evidence store = FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED
```

Current facts:

- `.aeg/` is folder-local state.
- Aegis runtime writes under `.aeg/`.
- `.aeg/` is expected to be gitignored and must not be tracked.
- Current code does not guarantee that an executor cannot write `.aeg/`.
- The current no-op executor does not directly write `.aeg/`, so this is not
  an immediate exploit in the current no-op executor path.
- Future live executor authority changes the risk model.

The current code can bind evidence records to manifests and replay them, but
that is not the same as making the evidence store tamper-proof against an
executor with filesystem write authority.

If a future live executor runs as the same OS user, with the same filesystem
authority, and receives raw shell or `write_file` tool authority, it may be
able to mutate `.aeg/`. Hiding the path from the executor would reduce casual
exposure but would not be a security boundary under those conditions.

Therefore:

```text
.aeg/ integrity is a hard blocker before live executor authority.
```

## 3. Core Distinctions

### Tamper-proof

Tamper-proof means the executor is prevented from modifying the protected
state. A tamper-proof `.aeg/` design would need an actual isolation or
capability boundary that makes unauthorized writes impossible by construction
or by an enforced external mechanism.

### Tamper-evident

Tamper-evident means modification can be detected after it happens. A hash
chain, manifest chain, signature, keyed hash, or post-run consistency check may
make tampering visible, but detection is not prevention.

Required distinction:

```text
tamper-evident != tamper-proof
```

### Folder-local

Folder-local means Aegis state lives under the repository-local `.aeg/`
directory. This supports portability, single-entry operation, and no required
external account.

Folder-local does not mean isolated from an executor running with the same
filesystem authority.

### Executor-isolated

Executor-isolated means the executor cannot write the evidence store even if
it tries. This requires a real boundary such as capability denial, process/user
separation, sandboxing, a mediated recorder, or another enforced mechanism.

### Capability-denied

Capability-denied means the executor never receives the authority needed to
perform the operation. For `.aeg/`, this candidate means the live executor does
not receive `capability_write_aeg_state`, raw shell authority, or a file write
tool that can target `.aeg/`.

Capability denial is a prevention strategy only if the denial is enforced
outside executor control.

### Path-hidden

Path-hidden means the executor is not told where `.aeg/` is. This may reduce
accidental writes and prompt exposure, but it is not a security boundary when
the executor has raw shell authority, broad filesystem access, or a generic
write tool.

Required distinction:

```text
path-hidden != secure
```

## 4. Required Invariants

These invariants must remain explicit in future design and review:

```text
.aeg/ exists and is gitignored != .aeg/ is executor-isolated
evidence binding exists != evidence store is tamper-proof against executor
tamper-evident != tamper-proof
folder-local != isolated
path-hidden != secure
capability not currently used != capability impossible
```

The current no-op executor not writing `.aeg/` is useful current behavior, but
it must not be interpreted as proof that a future live executor cannot write
`.aeg/`.

## 5. Design Question 1: Can Same OS User / Same Filesystem / Single Process Enforce Isolation?

Question:

```text
Can Aegis enforce executor isolation for .aeg/ when the executor shares the
same OS user, same filesystem authority, and same process authority?
```

Initial judgment:

```text
UNRESOLVED_DESIGN_BLOCKER
```

The concern is that a future live executor with raw shell authority or broad
`write_file` authority may be able to write any path the OS user can write,
including `.aeg/`. In that model, hiding `.aeg/` from prompts or tool metadata
does not reliably prevent writes.

Candidates to evaluate:

- run the executor as a subprocess with different permissions.
- make the Aegis runtime the only evidence writer.
- place an IPC boundary between executor and recorder.
- avoid exposing the `.aeg/` path to the executor.
- use append-only ledger semantics.
- use a hash chain, signature, or tamper-evident ledger.
- run post-run `.aeg/` integrity verification.

Candidate notes:

- Separate-permission subprocesses may support executor isolation, but they
  can increase portability and setup cost.
- Aegis-runtime-only writing is a strong design direction if the executor has
  no direct state-write capability.
- An IPC recorder boundary could preserve evidence writes outside executor
  control, but it is an implementation and compatibility question.
- Not exposing `.aeg/` is useful hygiene, not sufficient security.
- Append-only and hash-chain approaches may provide tamper evidence, not
  tamper-proof isolation by themselves.
- Post-run verification can detect inconsistency only if the verifier has a
  trustworthy prior anchor or externalized expected state.

Required warning:

```text
same OS user + raw shell/write_file authority means path-hidden is not a
security boundary.
```

## 6. Design Question 2: Constitution Compatibility Cost

The `.aeg/` integrity design must be evaluated against Aegis constitutional
constraints:

- zero required external accounts.
- single entry point.
- folder-local state under `.aeg/`.

Candidate compatibility matrix:

| Candidate | Portability cost | Setup complexity | Single entry point impact | Folder-local state impact | External dependency impact | User friction |
| --- | --- | --- | --- | --- | --- | --- |
| Separate OS user or permission subprocess | high | high | medium | may preserve `.aeg/`, but with ownership constraints | low if local-only | high |
| Sandbox or container | high | high | medium to high | may preserve `.aeg/`, but mount rules matter | medium, depends on platform | high |
| IPC recorder with Aegis-only evidence writer | medium | medium | low to medium | preserves `.aeg/` as recorder output | low if local-only | medium |
| Capability model denying `.aeg/` writes | low to medium | medium | low | preserves folder-local state | low | low to medium |
| Path-hidden only | low | low | low | preserves folder-local state | none | low |
| Tamper-evident ledger | low to medium | low to medium | low | preserves folder-local state | none unless external anchor is used | low |
| External optional backup hash | medium | medium | low to medium | keeps `.aeg/`, adds optional anchor | optional external dependency | medium |

Compatibility observations:

- A complete tamper-proof design may conflict with the easiest form of
  folder-local single-user operation.
- A pure external trust anchor can conflict with zero required external
  accounts if it becomes mandatory.
- A local-only tamper-evident ledger fits the constitution better, but it does
  not by itself prove the executor could not modify `.aeg/`.
- A capability-denial design may be the lightest constitutional fit if Aegis
  can ensure the executor receives no raw shell and no generic file write path
  into `.aeg/`.

## 7. Design Question 3: If Tamper-proof Is Hard, What Is the Partial Answer?

If full tamper-proof executor isolation is difficult under the constitutional
constraints, the partial answer may be a tamper-evident design paired with
capability denial.

Tamper-evident candidates:

- append-only ledger semantics.
- hash chain.
- manifest chain.
- run sequence hash.
- previous ledger hash.
- signed or keyed hash, if key handling can be kept outside executor control.
- optional external backup hash.
- post-run self-consistency check.

Candidate ledger fields for future design discussion:

```text
ledger_version
run_sequence_number
previous_ledger_hash
current_manifest_hash
current_evidence_hash
current_ledger_hash
recorder_identity
integrity_check_status
integrity_check_reason
```

Design limits:

- If the executor can rewrite the whole ledger and all local anchors, a local
  hash chain alone may not prove tampering happened.
- A signature or keyed hash is only useful if the signing key is not available
  to the executor.
- An optional external backup hash may strengthen detection, but it must not
  become a required external account unless the constitution changes.
- Post-run self-consistency checks detect contradictions; they do not prevent
  writes.

Required distinction:

```text
tamper-evident != tamper-proof
```

## 8. Design Question 4: Minimum Pre-live-executor Criteria

Future live executor work must choose a minimum criterion before authority is
granted.

Candidate A:

```text
complete executor-isolated evidence store
```

Strength:

- strongest prevention model.

Cost:

- highest compatibility burden with single-user, folder-local operation.
- likely requires OS, sandbox, process, or recorder boundary implementation.

Candidate B:

```text
tamper-evident ledger
```

Strength:

- fits folder-local operation better.
- improves replay and post-run detection.

Cost:

- does not prevent executor writes by itself.
- requires clear language that this is detection, not prevention.

Candidate C:

```text
capability_write_aeg_state is never granted to executor
```

Strength:

- light constitutional fit if enforced by the tool/capability surface.
- aligns with Aegis runtime as the only evidence writer.

Cost:

- insufficient if the executor also receives raw shell or generic file write
  authority that can reach `.aeg/`.
- requires enforcement outside executor self-report.

Candidate D:

```text
A + B
```

Strength:

- prevention plus detection.

Cost:

- highest implementation and compatibility cost.

Candidate E:

```text
B + C
```

Strength:

- likely lightest viable pre-live-executor candidate.
- combines local tamper evidence with explicit capability denial.
- preserves the possibility of folder-local state and a single entry point.

Cost:

- still must prove raw shell, broad `write_file`, and repo-outside write are
  denied by construction or mediated by Aegis.

The light candidate answer is:

```text
Do not grant capability_write_aeg_state to the live executor.
```

That answer must be evaluated together with:

- no raw shell by default.
- no `write_file` to `.aeg/`.
- no repo-outside write by default.
- Aegis-controlled recorder only.

Candidate E is not equivalent to tamper-proof isolation unless the capability
model actually prevents all executor-controlled write paths into `.aeg/`.

## 9. Evidence Binding Relationship

Existing evidence binding remains valuable, but it answers a different
question from executor isolation.

Evidence binding can answer:

```text
Does this evidence replay against the expected manifest and recorded fields?
```

Evidence binding does not automatically answer:

```text
Was the executor physically unable to rewrite the evidence store?
```

Required invariant:

```text
evidence binding exists != evidence store is tamper-proof against executor
```

Future design should keep the binding layer and the evidence-store integrity
layer separate in naming, statuses, and review gates.

## 10. Non-goals

This document does not implement:

- `.aeg/` permission hardening.
- `chmod`.
- `chown`.
- OS user separation.
- process separation.
- sandboxing.
- containers.
- IPC.
- signature or hash chain behavior.
- evidence store lock behavior.
- live executor write attempts.
- runtime behavior changes.
- structured tool execution.
- `read_file`, `write_file`, `run_command`, or `http_request` tools.
- live executor capability grants.
- shell calls.
- network calls.
- provider calls.
- model calls.
- release, publish, or deploy behavior.
- secret, token, API key, or `.env` value recording.
- `.aeg/` git inclusion.
- main merge behavior.

This document only records the current trust gap, required distinctions,
design questions, compatibility costs, candidate criteria, and non-goals.

## 11. Review Gate

This document is acceptable only if all of the following remain true:

- changed files are limited to this design document.
- no source code changes are included.
- no test code changes are included.
- no README, architecture, or package metadata changes are included.
- `.aeg/` is not tracked.
- `.env` is not tracked.
- tamper-evident and tamper-proof are not conflated.
- folder-local and executor-isolated are not conflated.
- path-hidden is not presented as a secure boundary.
- capability not currently used is not presented as capability impossible.
- no forbidden implementation is introduced.

Expected review status when those checks pass:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```
