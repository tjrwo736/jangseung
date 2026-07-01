# Aegis Phase 10 External Enforcement Boundary Scope Plan v0

## 1. Purpose

This document defines the Phase 10 scope plan for the external enforcement
boundary that must exist before any live executor authority can be considered.

This is a scope plan only. It does not implement external enforcement, live
executor authority, `.aeg/` executor isolation, permission hardening, `chmod`,
`chown`, OS user or process separation, sandboxing, containers, IPC, evidence
store locks, shell wrappers, tool wrappers, file write mediation, structured
tool execution, provider calls, model calls, network calls, planner behavior,
multi-step execution, resume behavior, autonomous loops, or multi-citizen
execution.

The safe default remains:

```text
hold_current_state
```

## 2. Baseline

The current baseline for this scope plan is:

```text
current main SHA = 680c7a5a9216448cdcefedec105f02ed666c9dd3
latest completed PR = #38
latest completed status = PASS_PHASE9_COMPLETION_CANONICAL_BASELINE_MAIN_SMOKE
Claude audit reconciliation status = PASS_NO_DELTA_NEEDED
tests = 131 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
```

Phase 9 fixed Candidate E as a scaffold baseline:

```text
Candidate E = tamper-evident ledger + capability_write_aeg_state denial model
Candidate E status = SCAFFOLDED_NOT_ENFORCEMENT_COMPLETE
Pre-live Executor Integrity Gate = IMPLEMENTED_AND_BOUND_SCAFFOLD_ONLY
Gate result = NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR
Live Executor Authority = ON_HOLD
.aeg/ evidence store = FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED
evidence store integrity status = NOT_CHECKED
```

This baseline is a handoff point from scaffolded metadata to enforcement design.
It is not a permission grant and not a claim that `.aeg/` is executor-isolated.

## 3. Phase 10 Problem Statement

Phase 9 completed the scaffold and canonical baseline needed to keep live
executor authority on hold. The scaffold records a tamper-evident ledger
direction, a default-denied `capability_write_aeg_state` metadata model, and a
pre-live gate result that still requires enforcement before live execution.

The remaining problem is that external enforcement does not yet exist. The
current `.aeg/` evidence boundary is folder-local runtime state written by
Aegis. Without an enforcement boundary outside executor self-report, a future
live executor could cause the evidence boundary to collapse into
self-certification.

The Phase 10 scope question is therefore:

```text
What minimum external enforcement boundary must be designed before Aegis can
promote the pre-live gate toward any live executor authority review?
```

Required problem statement distinctions:

```text
Phase 9 scaffold/canonical baseline complete != external enforcement complete
.aeg/ evidence binding != tamper-proof evidence store
current no-op executor safe != future live executor safe
live executor authority = ON_HOLD
```

The current no-op executor being safe is not enough to prove a future live
executor is safe. Future live executor safety depends on denying or mediating
dangerous capabilities before they are granted.

## 4. External Enforcement Definition

External enforcement means the relevant deny, mediate, or isolate decision is
controlled outside executor authorship and outside executor self-report.

External enforcement is not:

- an executor statement that it did not write `.aeg/`.
- an executor statement that it did not use a dangerous capability.
- `reported_only` metadata.
- path hiding by itself.
- command string enumeration by itself.
- a post-hoc statement that no failure was observed.

External enforcement is a candidate judgment basis only when it comes from at
least one of these sources:

- an Aegis-controlled enforcement layer.
- a mediated broker or wrapper outside executor control.
- OS, process, sandbox, container, or equivalent isolation outside executor
  control.
- externally verifiable proof that the denied capability was unavailable or
  mediated.

The trust boundary to preserve is:

```text
evidence recorder != executor
executor self-report = reported_only
reported_only is not judgment basis
verification source must be outside executor self-report
deny boundary must exist before capability grant
```

The evidence recorder may write `.aeg/`. The executor must not be able to write
`.aeg/` directly or indirectly through a granted dangerous capability unless a
future gate explicitly defines and verifies a safe mediated path.

Post-hoc verification may be sufficient when the only claim is detection within
defined limits. Examples include checking a hash chain for missing or reordered
records, replaying manifest-bound metadata, or detecting inconsistent evidence
after the run.

Post-hoc verification is not sufficient when the claim is prevention. Examples
include claiming that the executor could not write `.aeg/`, could not read
secrets, could not exfiltrate data, could not mutate remote branches, or could
not invoke provider/model APIs. Those claims require a pre-grant deny or
mediation boundary.

## 5. Threat Model

The Phase 10 external enforcement boundary must treat the following as threat
model inputs, not as solved facts:

- same OS user / same filesystem authority: a future executor may share the
  same filesystem write authority as the Aegis runtime unless an external
  boundary changes that fact.
- raw shell capability: an unrestricted shell can write paths, spawn processes,
  read files, invoke network tools, run provider SDKs, and bypass command text
  assumptions.
- `write_file` capability: a generic write tool can target `.aeg/` unless the
  tool is mediated by policy outside executor control.
- repo outside write capability: writes outside approved repository roots can
  become a bypass around folder-local assumptions.
- `read_file` secret read / `.aeg/` read risk: reading secrets, `.env`, local
  config, or `.aeg/` evidence can expose sensitive data or enable targeted
  evidence tampering.
- network/http exfiltration risk: outbound HTTP or network capability can move
  repository data, secrets, prompts, or evidence outside local review.
- `provider_call` / model API / secret boundary risk: provider or model calls
  may require secrets, use the network, and transmit prompt or context data.
- `git_operation` remote write / branch mutation risk: push, tag, branch
  mutation, force push, remote config mutation, or release operations can change
  remote state without a local tracked diff.
- path hiding is friction, not a security boundary.
- structured tool call != safe capability.
- no raw shell != no dangerous capability.

Required threat model distinctions:

```text
NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY
structured tool call != safe capability
path-hidden != secure
executor self-report != proof
```

An executor without raw shell can still be dangerous if it receives mediated or
unmediated tools that read secrets, write files, write outside the repo, make
network calls, call providers, or mutate git remotes.

## 6. `.aeg/` Write Boundary Problem

Aegis runtime writes `.aeg/` evidence. That is expected runtime behavior and is
part of the folder-local state model.

A live executor must not be able to write `.aeg/` evidence directly. It must
also not be able to reach `.aeg/` indirectly through raw shell authority, a
generic write tool, repo outside write capability, an executor-controlled
recorder path, or another broad filesystem authority.

Current facts:

```text
.aeg/ evidence store = FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED
.aeg/ gitignored != executor-isolated
evidence binding != tamper-proof evidence store
tamper-evident != tamper-proof
evidence store integrity status = NOT_CHECKED
```

Binding evidence to manifests can detect inconsistent metadata and can support
replay. It does not prove that the executor could not mutate `.aeg/`. A
tamper-evident ledger can improve detection, but it is not a tamper-proof
store by itself.

The boundary question for Phase 10 is not whether `.aeg/` exists or whether it
is gitignored. The question is which enforcement layer prevents or mediates
executor-controlled writes into `.aeg/` before live executor authority is
granted.

## 7. Enforcement Mechanism Candidates

The following candidates are design candidates only. This document does not
implement any of them.

### Candidate A: OS Permission / Separate User Model

Candidate A runs the executor as a separate OS user, process, or equivalent
permission domain. `.aeg/` remains writable by Aegis runtime but not writable
by the executor.

Review focus:

- prevention strength is high if the OS boundary is correctly configured.
- portability cost is high because behavior differs across operating systems,
  filesystems, shells, and user environments.
- setup complexity and user friction are high because account, ownership, or
  launcher setup may be required.
- folder-local `.aeg/` can be preserved, but ownership and write rules become
  part of correctness.

Candidate A is a strong prevention model, but it is not the lowest-friction
minimal Phase 10 path.

### Candidate B: Broker-Mediated Write Model

Candidate B prevents executor direct writes. All writes pass through an
Aegis-controlled broker, and the broker denies writes to `.aeg/`.

Review focus:

- the broker becomes the single write entry point.
- the broker must own path normalization, root policy, `.aeg/` denial, and
  failure behavior outside executor control.
- single entry point impact can be low to medium if the broker is integrated
  into the existing `aeg` runtime path.
- bypass risk remains if raw shell, generic write tools, or repo outside write
  authority exist outside the broker.

Candidate B is a strong fit for mediated local operation if every write path is
forced through the broker.

### Candidate C: Wrapper-Mediated Structured Tool Model

Candidate C exposes structured tools such as `write_file`, `read_file`, `git`,
`http`, and `provider` only through Aegis-controlled wrappers. Dangerous
capabilities are explicit grants. Raw shell remains unavailable.

Review focus:

- structured calls are easier to mediate than unrestricted shell commands.
- each tool still represents a capability and must be reviewed as such.
- `write_file` must deny `.aeg/` writes unless a future mediated recorder path
  is explicitly designed.
- `read_file` must handle secret, `.env`, and `.aeg/` read boundaries.
- `git`, `http`, and `provider` tools must default to denied authority until
  later gates define safe opt-in behavior.

Candidate C is useful only if structured tool availability is treated as a
grant matrix, not as proof of safety.

### Candidate D: Tamper-Evident Ledger Hardening

Candidate D hardens the tamper-evident ledger with append-only semantics, a
hash chain or manifest chain, previous ledger hash linkage, post-run
consistency checks, and optional external backup hash support.

Review focus:

- append-only semantics can make missing, reordered, or inconsistent records
  detectable.
- hash chain / manifest chain design must define canonical serialization and
  replay failure behavior.
- previous ledger hash linkage can bind each run to earlier state when a
  trustworthy prior anchor exists.
- post-run consistency check can detect defined tamper cases.
- optional external backup hash may improve anchoring but must remain optional
  if zero required external accounts is preserved.

Candidate D is tamper-evident, not tamper-proof. It improves detection but does
not prevent an executor with broad write authority from rewriting local state
and local anchors.

### Candidate E: Capability Denial Model

Candidate E keeps live executor authority from ever receiving
`capability_write_aeg_state`.

Review focus:

- direct Aegis state write authority remains denied.
- denial must be enforced outside executor self-report.
- raw shell, generic `write_file`, repo outside write, or another broad
  filesystem capability can bypass this denial if granted.
- the denial model must be combined with a full capability model covering read,
  write, shell, git, network, provider, secret, and remote authority.

Candidate E is the Phase 9 scaffolded minimum path, but its current state is
`SCAFFOLDED_NOT_ENFORCEMENT_COMPLETE`. It cannot by itself justify live
executor authority.

### Candidate F: Hybrid Model

Candidate F combines multiple candidates into a minimal viable enforcement
boundary. The likely combinations are:

- B + C + D + E: broker-mediated writes, wrapper-mediated tools,
  tamper-evident ledger hardening, and explicit `.aeg/` state write denial.
- A + D: OS permission separation plus tamper-evident ledger hardening.

Review focus:

- B + C + D + E preserves local operation and the existing single entry point
  better, but it must prove that no unmediated write path remains.
- A + D has stronger prevention if implemented correctly, but carries higher
  portability and setup cost.
- the minimal viable enforcement boundary should first close `.aeg/` write
  bypasses before any broader live executor capability is considered.

Candidate F is the recommended comparison frame for Phase 10 design, not an
implementation grant.

## 8. Constitution Compatibility Review

Aegis constitutional constraints for this review are:

```text
Zero required external accounts
Single entry point
Folder-local state under .aeg/
```

Compatibility matrix:

| Candidate | Portability cost | Setup complexity | Single entry point impact | Folder-local state impact | External dependency impact | User friction | Enforcement strength | Implementation risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. OS permission / separate user model | High | High | Medium to high | Can preserve `.aeg/`, but ownership and write permissions become correctness requirements | Low if local-only; higher if platform tooling is required | High | High prevention if correctly configured | High |
| B. Broker-mediated write model | Low to medium | Medium | Low to medium if broker is inside `aeg` entry point | Preserves `.aeg/` as Aegis runtime state | Low | Low to medium | High for writes forced through broker; weak if bypass paths remain | Medium to high |
| C. Wrapper-mediated structured tool model | Medium | Medium | Low to medium if wrappers are invoked by `aeg` | Preserves `.aeg/`, but tool policy must deny direct state writes | Low | Medium | Medium to high when all tools are mediated; weak for unwrapped capabilities | Medium to high |
| D. Tamper-evident ledger hardening | Low to medium | Low to medium | Low | Preserves folder-local `.aeg/` | None locally; optional anchor only if non-required | Low | Detection only; not prevention | Medium |
| E. Capability denial model | Low to medium | Medium | Low | Preserves `.aeg/` and denies named state write capability | Low | Low to medium | Medium for named capability; insufficient against broad bypasses | Medium |
| F. Hybrid model | Medium for B+C+D+E; high for A+D | Medium to high | Low to medium for B+C+D+E; medium to high for A+D | Preserves `.aeg/` if designed carefully | Low for local-only hybrid; optional anchors must remain optional | Medium | Highest practical strength when prevention and detection are combined | High |

Candidate observations:

- Candidate A provides the clearest prevention story but has the highest
  portability and setup friction.
- Candidate B fits the constitution if it becomes the mandatory write path and
  preserves the `aeg` entry point.
- Candidate C fits only when structured tools are treated as explicit grants
  with deny-by-default capability policy.
- Candidate D fits the constitution well but cannot be the prevention boundary.
- Candidate E fits the current scaffold direction but needs full capability
  coverage before it becomes externally enforced denial.
- Candidate F is the realistic Phase 10 comparison because no single lightweight
  candidate covers prevention, detection, and bypass control alone.

## 9. Recommended Phase 10 Path

Recommended Phase 10 sequencing:

1. Do not implement a live executor now.
2. Add an external enforcement design gate first.
3. Add a minimal enforcement scaffold only after the design gate is reviewed.
4. Add a mediated write boundary before any executor write authority is
   considered.
5. Promote the pre-live executor gate only after enforcement evidence exists
   outside executor self-report.
6. Review live executor authority last, in a separate explicit gate.

Recommended minimum design direction:

```text
Candidate F comparison, with B + C + D + E as the likely minimal local-first
path and A + D retained as the stronger prevention fallback.
```

The next Phase 10 work should define the exact `.aeg/` write boundary and
capability grant matrix. It should not open live executor authority.

## 10. Proposed Next Gates

Proposed next gates:

- Phase 10 External Enforcement Boundary Scope Plan v0
- Phase 10 `.aeg` Write Boundary Threat Model v0
- Phase 10 Capability Grant Matrix v0
- Phase 10 Mediated Write Boundary Scaffold v0
- Phase 10 Pre-live Gate Promotion Criteria v0

Gate intent:

- the scope plan fixes the enforcement problem statement and candidate space.
- the `.aeg` write boundary threat model defines bypass paths and deny
  requirements.
- the capability grant matrix defines dangerous capabilities and default-deny
  behavior before any structured tool or live executor work.
- the mediated write boundary scaffold can record policy without granting live
  executor authority.
- the pre-live gate promotion criteria define what evidence is needed before
  the gate can move beyond scaffold-only.

## 11. Explicit Non-goals

This document does not implement or authorize:

- live executor authority grant.
- external enforcement implementation.
- `.aeg/` executor isolation implementation.
- permission hardening.
- `chmod`.
- `chown`.
- OS user/process separation implementation.
- sandbox/container implementation.
- IPC implementation.
- evidence store lock implementation.
- shell wrapper implementation.
- tool wrapper implementation.
- file write mediation implementation.
- structured tool execution implementation.
- `read_file`, `write_file`, `run_command`, or `http_request` tool
  implementation.
- provider/model/network execution.
- planner, multi-step, resume, autonomous loop, or multi-citizen execution.
- release, publish, or deploy.
- secret, token, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- main direct push.
- main merge.

## 12. Canonical Distinctions To Preserve

The following distinctions are canonical for Phase 10:

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
```

These distinctions prevent Phase 9 scaffold metadata from being treated as a
completed enforcement boundary. They also prevent a current no-op executor
baseline from being used as proof that a future live executor can safely receive
dangerous capabilities.

## 13. Review Checklist

This scope plan is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- Phase 9 baseline facts remain scaffold-only.
- live executor authority remains `ON_HOLD`.
- no external enforcement implementation is added.
- `.aeg/` is not described as executor-isolated.
- tamper-evident is not described as tamper-proof.
- capability denial scaffold is not described as externally enforced denial.
- constitution compatibility review is present.
- recommended next gates are present.
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
