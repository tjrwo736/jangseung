# Aegis Phase 10 Mediated Write Boundary Design v0

## 1. Design Purpose

This document defines a design for the mediated write boundary that must be
reviewed before any future live executor write capability can be considered.

This is a design document only. It is not an implementation document for
opening a live executor. It does not grant live executor authority. It does not
implement external enforcement, write mediation, file tools, shell wrappers,
tool wrappers, broker IPC, OS user/process separation, permission hardening,
provider/model/network calls, git operation tools, or evidence store locks.

The design purpose is narrower:

- define how future write capabilities should be controlled by an
  Aegis-controlled mediation boundary.
- require future writes to pass through mediation rather than raw filesystem
  write authority.
- preserve the distinction between Aegis runtime/recorder writes and executor
  writes.
- define evidence expectations for allowed and denied writes without claiming a
  tamper-proof evidence store.
- keep live executor authority on hold.

All future write capability must be mediated. A future executor must not receive
raw filesystem write authority as the proof source for its own safety.

Executor self-report is not proof. `reported_only` is not a judgment basis.

The safe default remains:

```text
hold_current_state
```

## 2. Baseline

Baseline for this design:

```text
current main SHA = e37836cd66f5f01640e9ec80a3c3105baf7716c3
latest completed PR = #42
latest completed status = PASS_AEGIS_LEDGER_CHAIN_WALK_INTEGRITY_MAIN_SMOKE
latest completed gate = Aegis Ledger Chain Walk Integrity v0
tests = 138 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
capability grant matrix = main reflected
.aeg/ write boundary threat model = main reflected
ledger chain walk integrity = main reflected
tamper-evident ledger verification = strengthened
tamper-proof store = NOT_IMPLEMENTED
external anchor = NOT_IMPLEMENTED
.aeg/ executor isolation = NOT_IMPLEMENTED
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
ledger chain walk != external anchor
mediation design != mediation implementation
```

## 3. Boundary Problem

The current `.aeg/` state is folder-local. It is not executor-isolated. A
gitignored folder is not a security boundary, and path hiding is not security.

The write boundary problem is that a future executor with raw shell, a generic
`write_file` capability, broad repo write authority, or repo-outside write
authority can bypass metadata denial. In that case,
`capability_write_aeg_state` being denied by scaffold metadata is not enough.
The denial must either be externally enforced or every write path must be
mediated outside executor authorship.

Ledger chain walk integrity strengthens tamper-evidence. It can help detect
missing, reordered, or inconsistent ledger history under defined checks. It does
not prevent a full local rewrite by an actor with broad same-user filesystem
authority and control over local anchors.

Required problem statement:

```text
current .aeg/ = folder-local, not executor-isolated
write_file/raw shell/repo-outside-write can bypass metadata denial
capability_write_aeg_state denial must be externally enforced or mediated
ledger chain walk strengthens tamper-evidence
ledger chain walk does not prevent full local rewrite
tamper-evident != tamper-proof
```

## 4. Write Classes

This design uses the following write classes. A future implementation may split
or refine them, but it must not collapse dangerous capabilities into a generic
"safe write" category.

| Write class | Definition |
| --- | --- |
| `repo_tracked_write` | Create, modify, or replace a file that is tracked by git or intended to become tracked source, docs, config, tests, or project metadata. |
| `repo_untracked_write` | Create, modify, or replace an untracked file under the repository root that is not runtime evidence, not a declared generated artifact, and not `.aeg/` state. |
| `aeg_state_write` | Any create, modify, append, replace, delete, chmod, chown, rename, or move operation whose resolved target is under `.aeg/` or equivalent Aegis evidence state. |
| `outside_repo_write` | Any write whose resolved target is outside the approved repository root or outside an explicitly declared output root. |
| `delete_write` | Any file, directory, symlink, ref, or artifact deletion, including truncation treated as destructive replacement. |
| `rename_move_write` | Any rename, move, replace-through-rename, cross-directory move, or atomic swap operation. |
| `chmod_permission_write` | Any chmod, chown, ACL, executable-bit, permission, ownership, or mode mutation. |
| `git_ref_write` | Any mutation of local or remote git refs, branches, tags, history, remotes, hooks, worktrees, config that changes git behavior, or release refs. |
| `remote_write` | Any write to a network, provider, API, remote repository, external storage service, issue tracker, package registry, release endpoint, or other non-local system. |
| `generated_artifact_write` | A deterministic or tool-generated output file written only to a declared output directory and bound to a manifest. |
| `runtime_artifact_write` | Non-source runtime output such as logs, caches, temporary files, coverage output, or local diagnostic artifacts written only to an untracked runtime directory. |
| `secret_env_write` | Any write that creates, modifies, exports, persists, prints, stages, or transmits secrets, tokens, `.env` values, credentials, or environment-derived sensitive values. |
| `provider_state_write` | Any write to provider/model state, provider logs, provider-side files, prompts, fine-tuning inputs, API-side memory, network-backed state, or provider credentials. |

## 5. Required Default Stance

Default stance before a reviewed and verified write mediation boundary exists:

```text
aeg_state_write = HARD_DENY_PRE_LIVE
outside_repo_write = HARD_DENY_PRE_LIVE
delete_write = HARD_DENY_PRE_LIVE
rename_move_write = HARD_DENY_PRE_LIVE
chmod_permission_write = HARD_DENY_PRE_LIVE
git_ref_write = HARD_DENY_PRE_LIVE
remote_write = HARD_DENY_PRE_LIVE
secret_env_write = HARD_DENY_PRE_LIVE
provider_state_write = HARD_DENY_PRE_LIVE
generated_artifact_write = ALLOW_ONLY_IN_DECLARED_OUTPUT_DIR
runtime_artifact_write = ALLOW_ONLY_UNTRACKED_RUNTIME_DIR
repo_tracked_write = DENY_UNTIL_MEDIATED_WRITE_BOUNDARY
repo_untracked_write = DENY_UNTIL_MEDIATED_WRITE_BOUNDARY
```

These labels are design defaults. They do not implement enforcement and do not
grant a future executor.

## 6. Mediation Decision Matrix

The matrix below defines the minimum design decision for each write class. The
"verification source" entries are future candidate sources unless explicitly
marked as current docs-only review.

| Write class | Default pre-live status | Allowed before enforcement? | Required mediator | Required evidence | Required denial rule | `.aeg/` risk | Repo mutation risk | Outside repo risk | Secret/runtime artifact risk | Allowed output location | Verification source | Failure mode | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `repo_tracked_write` | `DENY_UNTIL_MEDIATED_WRITE_BOUNDARY` | No. | Aegis-controlled write broker or capability-scoped file API with resolved-path policy. | Declared path, before/after digest or diff summary, manifest binding, mediator allow decision. | Deny if path is unknown, protected, `.aeg/`, outside repo, secret-like, or not declared. | Medium: tracked docs can alter review claims; must not reach `.aeg/`. | High. | Medium through symlink or path confusion. | Medium if config or generated secrets are staged. | Declared tracked repo path only. | Future mediator logs plus git diff and manifest check. | Unmediated repo mutation becomes executor-authored state. | Current docs-only work is not this future executor capability. |
| `repo_untracked_write` | `DENY_UNTIL_MEDIATED_WRITE_BOUNDARY` | No. | Aegis-controlled write broker with untracked path classification. | Declared path, classification, digest, manifest entry, mediator allow decision. | Deny if path is undeclared, secret-like, runtime-confused, `.aeg/`, or outside approved root. | Medium if untracked path hides evidence tamper. | Medium. | Medium through resolved path bypass. | High if it creates `.env`, tokens, caches, or logs with secrets. | Declared non-runtime repo output path only. | Future mediator logs plus untracked-file review. | Untracked files hide mutations outside normal diff review. | Separate from generated and runtime artifact classes. |
| `aeg_state_write` | `HARD_DENY_PRE_LIVE` | No. | None for executor; only Aegis runtime/recorder path may write `.aeg/`. | Denial evidence for executor attempts; recorder evidence for Aegis-owned writes. | Deny every executor-authored resolved target under `.aeg/` or equivalent evidence state. | Critical. | High if evidence docs or manifests are altered. | High through absolute paths, symlinks, or anchors. | Medium through evidence metadata. | No executor output location. Aegis recorder may use `.aeg/`. | Future runtime recorder logs, mediator denial logs, ledger chain walk as supporting tamper-evidence. | Evidence boundary collapses into executor self-certification. | Recorder writes `.aeg/` != executor writes `.aeg/`. |
| `outside_repo_write` | `HARD_DENY_PRE_LIVE` | No. | External filesystem boundary or broker that rejects targets outside approved roots. | Denial evidence with canonical path and reason. | Deny unless a separate explicit reviewed grant names the outside root and class. | High if outside path reaches `.aeg/` or anchors. | Medium through sibling worktrees. | Critical. | High for secrets, configs, anchors, and runtime state. | None before enforcement. | Future OS boundary or broker logs outside executor control. | Repo boundary can be bypassed by absolute or resolved paths. | Same OS user plus raw shell remains out of scope until separately controlled. |
| `delete_write` | `HARD_DENY_PRE_LIVE` | No. | Destructive-operation broker with explicit grant, target class, and rollback policy. | Denial evidence by default; future allow evidence must include target digest and explicit grant. | Deny delete, truncate-as-delete, recursive delete, and replace-through-delete unless explicitly granted. | Critical if evidence or ledger records are removed. | High. | High. | High for secrets cleanup claims and runtime artifact removal. | None before enforcement. | Future mediator logs plus post-run filesystem observation. | Deletes erase review inputs or anchors. | Treat truncation as destructive replacement. |
| `rename_move_write` | `HARD_DENY_PRE_LIVE` | No. | Destructive-operation broker with source and destination canonicalization. | Denial evidence by default; future allow evidence must bind source, destination, and digests. | Deny rename, move, replace-through-rename, cross-root moves, and atomic swaps unless explicitly granted. | Critical if `.aeg/` can be replaced or moved. | High. | High. | Medium to high for moving secrets or runtime artifacts. | None before enforcement. | Future mediator logs plus before/after manifest. | Atomic swap can bypass simple write or delete checks. | Rename is not a harmless metadata-only operation. |
| `chmod_permission_write` | `HARD_DENY_PRE_LIVE` | No. | Permission-operation broker or OS boundary; not executor-controlled. | Denial evidence with target and attempted mode/owner where safe. | Deny chmod, chown, ACL, executable-bit, ownership, and permission mutations. | High if permissions expose or hide `.aeg/`. | Medium. | High. | High if secrets become readable or executable helpers appear. | None before enforcement. | Future OS/process policy proof or mediator denial logs. | Permission changes create later bypass paths. | This design does not implement chmod/chown or permission hardening. |
| `git_ref_write` | `HARD_DENY_PRE_LIVE` | No. | Git broker that denies ref/history/remote mutation unless separately reviewed. | Denial evidence by default; future allow evidence must bind command intent, refs, before/after SHA, and remote status. | Deny branch, tag, history, remote, hook, worktree, config, push, force-push, release, and ref mutation. | Medium: `.aeg/` may be ignored, but review context can be rewritten. | Critical. | Medium through worktrees/hooks/config. | High if credentials or hooks are involved. | None before enforcement. | Future git broker logs plus independent git state inspection. | Ref or history mutation bypasses local docs-only review. | Main direct push and main merge remain forbidden here. |
| `remote_write` | `HARD_DENY_PRE_LIVE` | No. | Network/remote/provider broker with explicit reviewed grant. | Denial evidence by default; future allow evidence must bind destination, payload class, credentials policy, and result. | Deny network-backed writes, API mutations, releases, packages, issues, PR state mutation, and remote storage writes. | Medium if evidence or metadata leaves local review. | High for remote repo state. | High through remote side effects. | Critical for secret exfiltration or credential-backed mutation. | None before enforcement. | Future remote broker logs plus external verification where applicable. | Remote side effect has no reliable local diff. | External anchor remains optional and not required by this design. |
| `generated_artifact_write` | `ALLOW_ONLY_IN_DECLARED_OUTPUT_DIR` | Only for declared outputs under a future mediator; current document implements none. | Declared output directory policy plus write broker. | Declared artifact manifest, digest, generator identity, source inputs, mediator allow decision. | Deny if output path is undeclared, protected, `.aeg/`, tracked source unless explicitly classified, outside repo, or secret-like. | Low if output root excludes `.aeg/`; high if policy is lexical only. | Medium if generated files are mistaken for source changes. | Medium through symlink or absolute path confusion. | Medium if generated artifacts include secrets. | Declared output directory only. | Future mediator logs plus artifact manifest. | Generated output pollutes source or hides unsafe writes. | Declared output directory policy is not a general write grant. |
| `runtime_artifact_write` | `ALLOW_ONLY_UNTRACKED_RUNTIME_DIR` | Only for untracked runtime output under a future mediator; current document implements none. | Runtime artifact policy with untracked runtime root and cleanup rules. | Runtime path, classification, digest or size metadata, retention policy, mediator allow decision. | Deny if tracked, `.aeg/`, secret-like, outside runtime root, or not declared as runtime. | Medium if runtime logs are confused with evidence. | Low to medium. | Medium through path confusion. | High if logs capture secrets, env, prompts, or provider responses. | Untracked runtime artifact directory only. | Future mediator logs plus runtime artifact scan. | Runtime output becomes hidden evidence or secret leakage. | Runtime artifacts must stay distinct from Aegis evidence. |
| `secret_env_write` | `HARD_DENY_PRE_LIVE` | No. | Secret boundary, redaction layer, and write broker; not executor-controlled. | Denial evidence without recording secret values. | Deny writing, exporting, printing, staging, persisting, or transmitting secrets, tokens, `.env` values, and sensitive env-derived data. | Medium through evidence metadata leaks. | High if `.env` or config files are created. | High if credentials are written outside repo. | Critical. | None before enforcement. | Future secret broker or redaction logs that never contain actual secret values. | Secret material becomes persisted, exfiltrated, or used for remote writes. | Do not record actual secrets or `.env` values. |
| `provider_state_write` | `HARD_DENY_PRE_LIVE` | No. | Provider/model/network broker with secret and payload boundaries. | Denial evidence by default; future allow evidence must bind provider, destination class, redaction policy, and result metadata. | Deny provider-side state mutation, prompt storage, fine-tuning writes, credential updates, model memory, and provider file writes. | Medium if evidence context is sent to provider state. | Low direct, high if provider output drives repo writes. | High through network-backed state. | Critical for prompts, secrets, credentials, and runtime data. | None before enforcement. | Future provider broker logs plus network/secret boundary proof. | Provider side effect cannot be judged from local executor report. | Provider/model output remains `reported_only` unless separately verified. |

## 7. `.aeg/` Write Mediation Rule

The `.aeg/` write rule is mandatory:

```text
executor must never directly write .aeg/
Aegis runtime/recorder may write .aeg/
recorder writes .aeg/ != executor writes .aeg/
```

Design implications:

- direct executor writes to `.aeg/` are always denied pre-live.
- executor-originated content for evidence, if ever allowed by a future gate,
  must pass through an Aegis-controlled recorder that records what was accepted.
- the recorder must remain distinct from the executor.
- path hiding is not security.
- gitignored is not isolated.
- ledger chain walk catches defined history tamper, but it does not make
  `.aeg/` tamper-proof.
- same OS user plus raw shell remains out of scope until separately controlled.

This document does not implement `.aeg/` executor isolation, permission
hardening, or a tamper-proof store.

## 8. Mediator Candidates

The following mediator candidates are design candidates only. This document does
not implement any of them.

| Candidate | What it can provide | Main limitation | Fit for this design |
| --- | --- | --- | --- |
| In-process write broker | Central path policy inside the Aegis runtime entry point; low integration cost. | Weak if executor can call around it, mutate broker state, or access raw shell/filesystem writes. | Useful only when executor cannot bypass the process-owned API. |
| Subprocess broker | Separate broker process can own write decisions and record attempts outside executor call frames. | Still weak without process/user separation if same-user raw filesystem authority remains available. | Better mediation boundary than in-process broker, but not complete isolation by itself. |
| Capability-scoped file API | Exposes narrow file operations with explicit grants, path classes, and evidence binding. | Structured API is not safe by default; every operation remains a capability. | Good for future `write_file` replacement only if raw writes are unavailable. |
| Denylist/allowlist path policy | Defines protected paths, allowed roots, and default-deny path classes. | Lexical policy is bypassable without canonicalization, symlink handling, and complete write coverage. | Required as a policy input, insufficient alone. |
| Declared output directory policy | Keeps generated artifacts and runtime artifacts in known roots. | Does not authorize general repo writes and does not protect `.aeg/` by itself. | Useful for low-risk artifacts when bound to mediation and manifests. |
| Append-only evidence writer | Records mediator decisions and write attempts in a tamper-evident sequence. | Append-only local records remain tamper-evident, not tamper-proof, without stronger isolation or anchors. | Useful supporting evidence, not write prevention. |
| OS user/process separation | Can prevent same-user filesystem bypass when configured correctly. | High portability, setup, ownership, and UX cost. | Strong prevention fallback or future hardening path. |
| Optional external verifier or anchor | Can strengthen tamper-evidence beyond local state. | Must remain optional; external anchor is not required and not equivalent to write prevention. | Useful future support, not a prerequisite in this design. |
| Hybrid broker + ledger chain walk + capability denial | Combines mediated write decisions, tamper-evident ledger verification, and deny-first capability policy. | Still must prove all write paths are covered; ledger chain walk is detection, not prevention. | Recommended comparison frame before any live executor review. |

Recommended design direction:

```text
hybrid broker + ledger chain walk + capability denial
```

This recommendation is not an implementation grant. It is the design frame for
future review because no single lightweight candidate covers path control,
dangerous capability denial, and tamper-evidence alone.

## 9. Required Mediator Behavior

A future mediator must satisfy these behavior requirements before any live
executor write capability is considered. These are design requirements, not
current implementation claims.

Required behavior:

- canonicalize paths before decision.
- reject path traversal.
- reject `.aeg/` writes from executor.
- reject outside-repo writes unless an explicit reviewed grant exists.
- reject chmod, chown, ACL, permission, ownership, and executable-bit writes.
- reject delete and rename unless an explicit reviewed grant exists.
- separate runtime artifacts from tracked artifacts.
- record attempted write metadata.
- bind allowed writes into evidence or a manifest.
- produce a denial reason for denied writes.
- fail closed on unknown paths, unknown write classes, and ambiguous resolved
  targets.
- never treat executor self-report as proof.

The mediator must make decisions from Aegis-controlled policy and observed
targets, not from executor narrative. The executor may request a write; it must
not be the authority that certifies the write was safe.

## 10. Verification And Evidence Model

The verification model for mediated writes is:

- mediator decisions should be recorded by Aegis runtime, not by executor.
- allowed writes need evidence binding.
- denied writes need denial evidence.
- verification should reject mismatch between declared writes and
  observed/recorded writes.
- `reported_only` is not a judgment basis.
- executor self-report is not proof.
- write mediation logs are a future candidate, not a current implementation.
- ledger chain walk is supporting tamper-evidence, not write prevention.

Allowed write evidence should bind at least:

- write class.
- canonical target path.
- declared output location or grant identifier.
- mediator decision.
- digest, diff summary, size, or other non-secret integrity metadata.
- source input or generator identity where applicable.
- evidence/manifest linkage.

Denied write evidence should bind at least:

- attempted write class.
- canonical target path or safe redacted path.
- denial rule.
- denial reason.
- timestamp or run-local sequence.
- mediator identity.

Verification should fail closed if:

- a write appears in the filesystem but not in mediator records.
- a mediator record allows a path that policy should deny.
- declared writes omit observed writes.
- observed writes appear outside allowed output locations.
- `.aeg/` is modified by an executor-authorized path.
- denied write attempts are reported only by executor narrative.
- secret values are recorded as evidence.

This evidence model is not a tamper-proof store. Evidence binding is not
tamper-proof evidence storage. Ledger chain walk can support detection, but it
is not an external anchor and not write prevention.

## 11. Relation To Existing Phase 10 Docs

This design is downstream of the existing Phase 10 documents and the completed
ledger chain walk gate:

- Phase 10 External Enforcement Boundary Scope Plan v0 defines the external
  enforcement problem and candidate enforcement space.
- Phase 10 `.aeg` Write Boundary Threat Model v0 defines `.aeg/` threat paths,
  write bypasses, and failure modes.
- Phase 10 Capability Grant Matrix v0 defines deny-first capability defaults
  and grant review vocabulary.
- Ledger Chain Walk Integrity v0 strengthens tamper-evidence by checking ledger
  chain consistency.
- This design defines how mediated writes could be controlled before any live
  executor write capability is considered.

This document does not supersede those documents. It relies on their canonical
distinctions and adds the write-class mediation design layer.

## 12. Non-goals

This document does not implement or authorize:

- live executor authority grant.
- external enforcement implementation.
- `.aeg/` permission hardening.
- `.aeg/` executor isolation.
- `chmod` or `chown` implementation.
- OS user/process separation.
- sandbox/container implementation.
- IPC implementation.
- evidence store lock implementation.
- shell wrapper implementation.
- tool wrapper implementation.
- file write mediation implementation.
- structured tool execution implementation.
- `read_file`, `write_file`, `run_command`, or `http_request` tool
  implementation.
- provider/model/network call implementation.
- git operation tool implementation.
- planner, multi-step, resume, autonomous loop, or multi-citizen execution.
- external anchor requirement.
- release, publish, or deploy.
- secret, token, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- main direct push.
- main merge.

## 13. Recommended Next Gate

Recommended next gate:

```text
Phase 10 Mediated Write Boundary Scaffold v0
```

Alternative next gate:

```text
Phase 10 Write Mediation Verify Criteria v0
```

This document implements neither gate. The next gate should either scaffold the
write boundary metadata without granting write authority or define verification
criteria for future mediated write evidence.

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
```

If a future change uses this design to justify live executor authority, claims
external enforcement already exists, upgrades `.aeg/` beyond folder-local state,
upgrades ledger chain walk beyond supporting tamper-evidence, or treats a
structured tool call as safe by default, that change needs review fixes before
it can be used as a gate input.

## 15. Review Checklist

This design is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- live executor authority remains `ON_HOLD`.
- no external enforcement implementation is added.
- `.aeg/` is not described as executor-isolated.
- ledger chain walk is not described as tamper-proof.
- the design is not described as implementation.
- all required write classes are defined.
- the mediation decision matrix includes every required write class.
- `.aeg/` write mediation rule is explicit.
- mediator candidates are compared.
- required mediator behavior is design-level only.
- verification and evidence model rejects executor self-report and
  `reported_only` as proof.
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
