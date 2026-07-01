# Aegis Phase 10 `.aeg` Write Boundary Threat Model v0

## 1. Purpose

This document defines the threat model for the `.aeg/` evidence store write
boundary before any future live executor authority can be considered.

This is a threat model only. It does not implement live executor authority,
external enforcement, `.aeg/` executor isolation, permission hardening, `chmod`,
`chown`, OS user or process separation, sandboxing, containers, IPC, evidence
store locks, shell wrappers, tool wrappers, file write mediation, structured
tool execution, provider calls, model calls, network calls, planner behavior,
multi-step execution, resume behavior, autonomous loops, or multi-citizen
execution.

The safe default remains:

```text
hold_current_state
```

The purpose of this threat model is to make the `.aeg/` write boundary a hard
blocker before a live executor. It identifies the conditions where the evidence
boundary collapses into executor self-certification and therefore cannot be
used as proof that a future live executor is safe.

This document aligns with the Phase 9 canonical baseline and the Phase 10
External Enforcement Boundary Scope Plan. It does not open live executor
authority. It defines conditions under which live executor authority must
remain closed.

Baseline for this threat model:

```text
current main SHA = c124b87cb47e78c1e9a3ebdf1027421b8d88d308
latest completed PR = #39
latest completed status = PASS_PHASE10_EXTERNAL_ENFORCEMENT_BOUNDARY_SCOPE_PLAN_MAIN_SMOKE
latest completed gate = Aegis Phase 10 External Enforcement Boundary Scope Plan v0
tests = 131 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
.aeg/ evidence store = FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED
evidence store integrity status = NOT_CHECKED
Candidate E = SCAFFOLDED_NOT_ENFORCEMENT_COMPLETE
gate result = NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR
```

Required baseline distinctions:

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

## 2. Protected Assets

The protected assets are the local state, metadata, and review artifacts whose
integrity must not depend on executor authorship or executor self-report.

Protected `.aeg/` files:

- `.aeg/config.json`
- `.aeg/ledger.jsonl`
- `.aeg/runs/<run_id>/run.json`
- `.aeg/runs/<run_id>/evidence.json`
- `.aeg/runs/<run_id>/manifest.json`

Protected evidence and provenance concepts:

- evidence packet
- manifest hash
- ledger chain
- pre-live executor gate evidence
- capability grant/deny metadata
- run provenance

The protected status of these assets does not mean they are currently isolated
from every future executor. The current `.aeg/` state remains folder-local and
not executor-isolated. Integrity remains `NOT_CHECKED` until a separate gate
implements and verifies an enforcement boundary.

## 3. Trust Boundaries

The threat model separates components that record, execute, verify, store, and
review state. The `.aeg/` boundary fails when the executor can author or rewrite
the same evidence that is later used to judge the executor.

Trust boundaries to preserve:

- Aegis runtime / recorder: owns legitimate evidence writes and must remain
  distinct from executor-authored claims.
- executor: future live action source that must not be able to certify its own
  `.aeg/` write denial.
- verifier: evaluates evidence and must not rely on executor self-report as a
  proof source.
- local filesystem: shared storage that may give same-user processes broad
  authority unless a separate boundary changes that fact.
- repository working tree: tracked source and docs state, distinct from
  runtime `.aeg/` state.
- `.aeg/` folder-local state: local evidence store that currently exists under
  the repo but is not executor-isolated.
- future mediated write layer: possible enforcement owner if every write path
  is forced through it.
- optional external verifier or backup hash: possible tamper-evidence anchor,
  but not a required account or a substitute for prevention.
- user-controlled merge/review gate: final human-controlled gate for promotion,
  not an implementation of technical isolation.

The required trust rule is:

```text
evidence recorder != executor
executor self-report = reported_only
reported_only is not judgment basis
verification source must be outside executor self-report
deny boundary must exist before capability grant
```

## 4. Threat Actors And Threat Sources

This threat model treats the following as possible sources of `.aeg/` boundary
failure:

- compromised future live executor
- model-backed executor producing dangerous actions
- structured tool executor with write capability
- raw shell-capable executor
- `write_file`-capable executor
- repo-outside-write-capable executor
- same OS user process
- accidental internal bug
- malicious or buggy recorder plugin
- user misconfiguration

These sources can be malicious, compromised, confused, overbroad, or simply
buggy. The boundary must not depend on an executor promise that it did not touch
`.aeg/`.

## 5. Capability Risk Matrix

The matrix evaluates `.aeg/` risk by capability. It is not a grant matrix and
does not authorize any capability.

| Capability | `.aeg/` risk | Minimum pre-live stance |
| --- | --- | --- |
| `capability_read_repo` | Can reveal source, test, docs, and policy context that helps target later evidence tamper. It is not direct `.aeg/` write authority. | Must be bounded to approved repo paths and separated from `.aeg/` state reads before any future grant. |
| `capability_write_repo` | Can mutate tracked evidence docs, scope plans, tests, or code. If repo write policy treats `.aeg/` as ordinary repo content, the evidence boundary collapses. | Must deny `.aeg/` writes and keep runtime evidence state outside ordinary repo write grants. |
| `capability_read_aeg_state` | Can reveal ledger, manifest, evidence packet, capability metadata, run IDs, and provenance needed for targeted rewriting. | Must be explicit, minimized, and not treated as harmless just because it is read-only. |
| `capability_write_aeg_state` | Direct write authority to protected evidence assets. This collapses the boundary into executor self-certification. | Must be denied before live executor authority unless a future reviewed mediated recorder path exists. |
| `capability_read_outside_repo` | Can expose secrets, external anchors, alternate worktrees, local config, or backup hashes that affect evidence trust. | Must be denied or explicitly bounded with secret-safe policy. |
| `capability_write_outside_repo` | Can mutate anchors, sibling clones, external verifier inputs, or reach `.aeg/` through absolute/resolved paths when policy checks are incomplete. | Must be denied or mediated before live executor authority. |
| `capability_delete_outside_repo` | Can destroy anchors, backups, local verifier records, or evidence-supporting files outside the repo. | Must be denied before live executor authority. |
| `capability_network` | Can exfiltrate secrets, prompts, evidence, manifests, or run provenance and can fetch attacker-controlled instructions or tools. | Must remain denied unless a later network boundary explicitly mediates it. |
| `capability_remote_write` | Can push branches, tags, releases, or remote evidence docs, bypassing local review and altering history. | Must be denied before live executor authority. |
| `capability_provider_call` | Crosses model/API/secret/network boundaries and may transmit prompt, repo, evidence, or secret context. | Must be denied until provider, network, and secret boundaries are separately enforced. |
| `capability_env_read` | Can expose environment variables, including tokens or configuration that unlock remote write, provider, or filesystem behavior. | Must be denied or redacted under a secret-safe boundary. |
| `capability_secret_read` | Can expose credentials that allow remote write, provider calls, network exfiltration, or external verifier tamper. | Must be denied before live executor authority. |
| `capability_process_spawn` | Can run helpers, shells, interpreters, git, network tools, or background processes outside structured mediation. | Must be denied or mediated before live executor authority. |
| `capability_shell` | Can write `.aeg/`, rewrite ledger state, spawn processes, read secrets, invoke network tools, run provider SDKs, and bypass path hiding. | Must be denied or fully mediated before live executor authority. |

Capability conclusions:

```text
capability_write_aeg_state denial is necessary but not sufficient
write_repo must not imply write_aeg_state
read-only does not always mean harmless
NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY
structured tool call != safe capability
```

## 6. Attack Paths

The following attack paths must be blocked, mediated, or explicitly detected
before live executor authority can move beyond `ON_HOLD`.

### Direct `.aeg/` Write

An executor writes directly to `.aeg/` using filesystem authority. This can
create, modify, delete, or replace evidence without passing through the Aegis
recorder.

Boundary failure:

```text
executor can write .aeg/ -> executor can self-certify evidence
```

### `.aeg/ledger.jsonl` Rewrite

An executor rewrites, truncates, reorders, or appends misleading ledger records.
If the ledger chain and prior anchors are not verified, the rewrite may appear
consistent to local review.

Required distinction:

```text
tamper-evident ledger != tamper-proof ledger
```

### `.aeg/runs/<run_id>/evidence.json` Tamper

An executor edits the evidence packet after the run to change status, changed
files, gate evidence, capability metadata, or risk classification. This can
make unsafe behavior appear clean if verification trusts the modified packet.

### `.aeg/runs/<run_id>/manifest.json` Tamper

An executor edits the manifest to match tampered evidence. If the verifier
trusts only current local files and lacks a trustworthy prior anchor, tamper may
be difficult to distinguish from legitimate recorder output.

### Manifest Hash Recompute By Attacker

An executor changes evidence and recomputes matching manifest hashes. Evidence
binding detects inconsistency only when the expected binding is outside the
attacker's rewrite authority.

Required distinction:

```text
evidence binding != tamper-proof evidence store
```

### Evidence Packet Rewrite After Run

An executor rewrites completed run evidence after actions finish. Post-run
verification can only help if it has an independent basis for expected state,
such as previous-run anchoring, append-only ledger semantics, or an optional
external verifier.

### Run Metadata Substitution

An executor substitutes `run_id`, timestamps, branch, commit, tree hash,
capability grant metadata, deny metadata, or provenance fields to make evidence
look like it belongs to a different run or safer authority context.

### Path Traversal Into `.aeg/`

An executor uses `../`, symlinks, absolute paths, case or Unicode ambiguity,
platform-specific separators, or resolved-path mismatches to target `.aeg/`
through a path that a lexical denylist does not catch.

### Repo-Outside Write Into `.aeg/`

An executor uses a broad outside-repo write capability, alternate worktree,
mount point, symlink, or absolute path to reach evidence state. The boundary
fails if policy checks apply only to the submitted path string rather than the
resolved target.

### Raw Shell Write To `.aeg/`

An executor with shell authority uses shell redirection, scripts, interpreters,
`git`, filesystem utilities, or process spawning to mutate `.aeg/`.

Required distinction:

```text
path hiding is friction, not a security boundary
```

### Structured `write_file` Tool Writing `.aeg/`

An executor with a generic `write_file` tool targets `.aeg/` directly or through
path traversal. The structured shape of the tool call does not make the
capability safe.

Required distinction:

```text
structured tool call != safe capability
```

### Git Operation Altering Branch, History, Or Evidence Docs

An executor uses git operations to modify branch history, force-push, retag,
rewrite evidence-related docs, alter remote refs, or make local state appear
reviewed when it is not. Runtime `.aeg/` may be gitignored, but tracked
evidence docs and review context remain sensitive.

### Network Exfiltration Of Secrets Or Evidence

An executor sends secrets, prompts, evidence, manifests, capability metadata,
or run provenance over the network. Exfiltration can enable later remote write,
provider misuse, or external manipulation beyond local review.

### `provider_call` Crossing Model/API/Secret Boundary

An executor invokes a provider or model API using credentials or context that
crosses network and secret boundaries. The returned model output or provider
side effect is not proof of `.aeg/` integrity and may leak evidence context.

### Path Hiding Bypass

An executor discovers `.aeg/` through repository listing, conventional path
guessing, environment context, prior docs, shell commands, or filesystem search.
Not telling the executor the path is useful hygiene only.

### Same-User Filesystem Authority Bypass

An executor running as the same OS user with broad filesystem authority writes
any file that the Aegis runtime can write. Without a separate control, this
bypasses folder-local assumptions and direct path policy.

## 7. Failure Modes

The following failures would make the threat model unsatisfied:

- folder-local `.aeg/` treated as executor-isolated.
- gitignored `.aeg/` treated as a security boundary.
- tamper-evident treated as tamper-proof.
- executor self-report treated as proof.
- `reported_only` treated as judgment basis.
- structured tool call treated as safe capability.
- no raw shell treated as no dangerous capability.
- evidence binding treated as tamper-proof evidence store.
- current no-op safety generalized to future live executor.

Each failure collapses a required distinction. Any one of them is enough to keep
live executor authority on hold.

## 8. Controls And Mitigations To Evaluate

The following controls are evaluation candidates only. This document does not
implement any of them.

| Control | What it could address | Evaluation question |
| --- | --- | --- |
| `capability_write_aeg_state` denial | Direct writes to protected `.aeg/` state. | Is denial enforced outside executor self-report and outside executor-controlled tools? |
| Denying repo-outside writes | Bypasses through absolute paths, alternate roots, anchors, and sibling worktrees. | Can the executor still reach `.aeg/` or supporting anchors through resolved paths? |
| Denying raw shell | Shell writes, process spawning, secret reads, provider calls, and network utilities. | Are equivalent capabilities still available through structured tools or spawned processes? |
| Mediated write broker | Centralized path normalization and write policy. | Are all writes forced through the broker, including helpers, plugins, and recorder paths? |
| Path allowlist/denylist | Rejecting known protected paths and bounding approved roots. | Does it normalize and resolve paths before decision, and does it handle symlinks and platform differences? |
| `.aeg/` write deny policy | Explicit refusal to let executor-controlled writes target evidence state. | Is the deny policy external to executor authorship and applied to every write surface? |
| Append-only ledger semantics | Detecting missing, reordered, truncated, or rewritten records. | What prior anchor or chain rule prevents complete local rewrite from looking valid? |
| Hash chain / manifest chain | Binding records and manifests across runs. | Is canonical serialization defined and is replay failure deterministic? |
| Previous-run hash anchoring | Carrying trust from one run to the next. | Where is the previous hash stored, and can the executor rewrite both current and prior anchors? |
| Post-run integrity verification | Detecting defined tamper cases after execution. | Does verification depend on evidence the executor could have rewritten? |
| Separate process/user model | OS-enforced prevention against executor writes. | Can the model be portable without violating single-entry and low-friction operation? |
| Optional external verifier | Independent hash or state backup for tamper evidence. | Can it remain optional and avoid required external accounts? |
| User review gate | Human-controlled merge and promotion review. | Does the gate review deterministic evidence rather than executor narrative? |
| Pre-live executor gate promotion criteria | Explicit conditions for moving beyond scaffold-only. | Are criteria based on enforced denial and verified integrity, not `reported_only` metadata? |

## 9. Control Limitations

Controls must be evaluated with their limits visible:

- path hiding is friction, not security boundary.
- same OS user plus raw shell can bypass path policy.
- `write_file` can be shell-equivalent for state tamper.
- broker is only useful if all writes are mediated.
- tamper-evident does not prevent tamper.
- external verifier may conflict with zero required external accounts if it
  becomes mandatory.
- OS permission hardening may increase setup friction.
- folder-local constitution may conflict with strong isolation.

These limits do not make the controls useless. They prevent any single control
from being overstated as a completed external enforcement boundary.

## 10. Minimum Live-Executor Blocker Conditions

Live executor authority remains `ON_HOLD` if any of the following are
unresolved:

- executor can write `.aeg/`.
- executor can write outside allowed workspace.
- executor has raw shell without mediation.
- `write_file` can target `.aeg/`.
- evidence store integrity status remains `NOT_CHECKED`.
- pre-live executor gate result remains
  `NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR`.
- capability grants cannot distinguish
  read/write/repo/outside/aeg/network/provider/secret/process/shell.
- verifier depends on executor self-report.

These blockers are minimum conditions, not a complete safety proof. Satisfying
them in a future gate may make review possible, but it does not by itself grant
live executor authority.

## 11. Recommended Next Gate

Recommended next gate:

```text
Phase 10 Capability Grant Matrix v0
```

Alternative next gate:

```text
Phase 10 Mediated Write Boundary Design v0
```

This document implements neither gate. It recommends one of them as the next
review step because the threat model identifies capability distinction and
write mediation as the next unresolved boundaries.

## 12. Review Checklist

This threat model is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- Phase 10 scope plan facts remain unchanged.
- live executor authority remains `ON_HOLD`.
- no external enforcement implementation is added.
- `.aeg/` is not described as executor-isolated.
- tamper-evident is not described as tamper-proof.
- capability denied by scaffold is not described as externally enforced denial.
- evidence binding is not described as a tamper-proof evidence store.
- current no-op executor safety is not generalized to future live executor
  safety.
- all required protected assets, trust boundaries, threat actors, capabilities,
  attack paths, failure modes, mitigations, limitations, blocker conditions, and
  canonical distinctions are present.
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
