# Aegis Phase 10 Capability Grant Matrix v0

## 1. Purpose

This document defines the Phase 10 capability grant matrix that must be
understood before any future live executor authority can be reviewed.

This is not a document that opens live executor authority. It does not grant a
live executor. It does not implement external enforcement, structured tool
execution, raw shell execution, provider/model/network calls, `read_file`,
`write_file`, `run_command`, `http_request`, provider tools, git tools, file
write mediation, or any runtime permission hardening.

The purpose is narrower:

- identify which capabilities must never be granted before live executor
  review.
- identify which capabilities are forbidden unless a specific enforcement
  boundary exists outside executor self-report.
- separate capability grants from evidence packets, manifests, and
  `reported_only` executor claims.
- preserve the current safe default:

```text
hold_current_state
```

Capability grants must be judged by an Aegis-controlled boundary or an
externally verifiable boundary. Executor self-report is not proof, and
`reported_only` is not a judgment basis.

This document aligns with the Phase 10 External Enforcement Boundary Scope Plan
and the Phase 10 `.aeg` Write Boundary Threat Model. It adds a grant matrix; it
does not implement the boundary described by either document.

Baseline for this matrix:

```text
current main SHA = 0cd54987abe4eca371d019c23ff8d6e3b0dc8002
latest completed PR = #40
latest completed status = PASS_PHASE10_AEG_WRITE_BOUNDARY_THREAT_MODEL_MAIN_SMOKE
latest completed gate = Aegis Phase 10 Aeg Write Boundary Threat Model v0
tests = 131 PASS
safe default = hold_current_state
live executor authority = ON_HOLD
Phase 10 scope plan = main reflected
.aeg/ write boundary threat model = main reflected
current no-op executor capability = NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION
.aeg/ evidence store = FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED
evidence store integrity status = NOT_CHECKED
```

Required purpose distinctions:

```text
capability grant matrix != live executor grant
capability grant conditions != external enforcement implementation
executor self-report != proof
reported_only != judgment basis
current no-op executor safe != future live executor safe
```

## 2. Capability Categories

The matrix covers these capability names:

```text
capability_read_repo
capability_write_repo
capability_read_aeg_state
capability_write_aeg_state
capability_read_outside_repo
capability_write_outside_repo
capability_delete_outside_repo
capability_network
capability_remote_write
capability_provider_call
capability_env_read
capability_secret_read
capability_process_spawn
capability_shell
capability_structured_tool_call
capability_git_operation
capability_runtime_recorder_write
```

The categories are deliberately broad. A structured tool, git helper, provider
adapter, or recorder path is not safe merely because it has a name or schema.
Each category is a capability that must be denied, mediated, or verified before
it can become a future live executor input.

## 3. Current No-op Baseline

The current no-op executor baseline remains:

```text
all executor capabilities = false
action_count = 0
expected_action_count = 0
provider_calls = false
network_calls = false
file_mutation = false
actions = []
status = NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION
```

This baseline is a current no-op executor fact. It is not a future live
executor safety proof.

Required distinction:

```text
current no-op executor safe != future live executor safe
```

Future live executor safety depends on denied or mediated capability grants,
not on the current no-op executor having no shell, no network, no provider
calls, no file mutation, and no actions.

## 4. Required Default Stance

Default stance before a reviewed enforcement boundary exists:

```text
current no-op default = false
future live executor pre-live default = DENIED or NOT_GRANTED
live executor authority = ON_HOLD
capability_write_aeg_state = HARD_DENY_UNTIL_EXTERNAL_ENFORCEMENT
capability_shell = HARD_DENY_PRE_LIVE
capability_write_outside_repo = HARD_DENY_PRE_LIVE
capability_delete_outside_repo = HARD_DENY_PRE_LIVE
capability_network = DENY_UNTIL_NETWORK_BOUNDARY
capability_provider_call = DENY_UNTIL_PROVIDER_BOUNDARY
capability_secret_read = HARD_DENY_PRE_LIVE
capability_env_read = HARD_DENY_PRE_LIVE
capability_remote_write = HARD_DENY_PRE_LIVE
capability_process_spawn = DENY_UNTIL_PROCESS_BOUNDARY
capability_structured_tool_call = NOT_SAFE_BY_DEFAULT
```

The future live executor default is deny-first. `GRANTED` is unavailable in this
matrix because the required enforcement boundary has not been implemented or
verified.

## 5. Grant Status Vocabulary

This document uses the following vocabulary:

| Status | Meaning |
| --- | --- |
| `GRANTED` | Capability is authorized by a reviewed grant and backed by the required enforcement or verification source. Not used as a current result in this matrix. |
| `NOT_GRANTED` | Capability has no grant. This is the ordinary pre-live default. |
| `DENIED` | Capability is explicitly denied by policy for the reviewed context. |
| `HARD_DENY_PRE_LIVE` | Capability must not be granted before a separate live executor review gate. |
| `DENY_UNTIL_BOUNDARY` | Capability is denied until a named technical boundary exists and is verified outside executor self-report. |
| `DENY_UNTIL_EXTERNAL_ENFORCEMENT` | Capability is denied until enforcement exists outside executor authorship and executor self-report. |
| `ALLOW_ONLY_WITH_MEDIATION` | Capability may be considered only through an Aegis-controlled broker, wrapper, or equivalent mediation layer. |
| `ALLOW_READ_ONLY_WITH_PROOF` | Read capability may be considered only when bounded read-only proof exists and the source cannot expose secrets, `.aeg/`, or uncontrolled paths. |
| `NOT_CHECKED` | No verification has been performed. This is not a pass result. |
| `FUTURE_NOT_IMPLEMENTED` | Capability or boundary is future design only and not implemented by this document. |
| `SCAFFOLD_ONLY_NOT_ENFORCED` | Metadata or scaffold exists, but it does not enforce denial or mediation. |

Additional matrix-specific deny labels refine the vocabulary above:

| Status | Relationship to vocabulary |
| --- | --- |
| `HARD_DENY_UNTIL_EXTERNAL_ENFORCEMENT` | Harder form of `DENY_UNTIL_EXTERNAL_ENFORCEMENT`; it is used for `capability_write_aeg_state` because direct executor writes to `.aeg/` collapse evidence into self-certification. |
| `DENY_UNTIL_NETWORK_BOUNDARY` | Specific `DENY_UNTIL_BOUNDARY` for network and exfiltration controls. |
| `DENY_UNTIL_PROVIDER_BOUNDARY` | Specific `DENY_UNTIL_BOUNDARY` for provider/model/API/secret/network crossing. |
| `DENY_UNTIL_PROCESS_BOUNDARY` | Specific `DENY_UNTIL_BOUNDARY` for process creation and child-process escape. |
| `NOT_SAFE_BY_DEFAULT` | Capability classification for structured tool transport; structured form is not itself a safety proof or grant. |

Vocabulary guardrails:

```text
NOT_CHECKED != PASS
DENIED_BY_METADATA != EXTERNALLY_ENFORCED_DENIAL
SCAFFOLD_ONLY_NOT_ENFORCED != SAFE_TO_RUN
```

## 6. Capability Grant Matrix

Columns in this matrix:

- capability name
- current no-op default
- future live executor default
- pre-live grant status
- required enforcement boundary
- `.aeg/` risk
- secret/env risk
- network/exfiltration risk
- repo mutation risk
- outside repo mutation risk
- evidence tamper risk
- allowed before enforcement?
- blocker if granted?
- verification source
- notes

| Capability name | Current no-op default | Future live executor default | Pre-live grant status | Required enforcement boundary | `.aeg/` risk | Secret/env risk | Network/exfiltration risk | Repo mutation risk | Outside repo mutation risk | Evidence tamper risk | Allowed before enforcement? | Blocker if granted? | Verification source | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `capability_read_repo` | `false` | `NOT_GRANTED` | `ALLOW_READ_ONLY_WITH_PROOF` | Repo-root read allowlist; `.aeg/` and secret path exclusion; externally checked path policy. | Medium: can reveal policy and evidence doc context. | Medium: repo may contain config or accidental secrets. | Low direct, medium if paired with network/provider. | None direct. | None direct. | Medium: helps targeted tamper. | No, except bounded read-only proof. | Yes if unbounded or paired with exfiltration. | Future Aegis-controlled read broker, static policy plus external verification. | Read-only is not harmless by default. |
| `capability_write_repo` | `false` | `DENIED` | `ALLOW_ONLY_WITH_MEDIATION` | Aegis-controlled write broker with normalized path policy and `.aeg/` denial. | High if `.aeg/` is reachable. | Medium via config writes or secret staging. | Medium if paired with exfiltration. | High. | Medium through symlink or path confusion. | High for tracked evidence docs and review context. | No. | Yes if unmediated. | Future mediated broker logs plus post-write diff review. | `write_repo` must not imply `write_aeg_state`. |
| `capability_read_aeg_state` | `false` | `DENIED` | `DENY_UNTIL_BOUNDARY` | Explicit Aegis-owned read policy for `.aeg/` state with minimization and redaction. | High: exposes ledger, manifests, run IDs, and provenance. | Medium: may reveal local paths or metadata. | Medium if paired with network/provider. | None direct. | None direct. | High: enables targeted rewrite. | No. | Yes if unbounded or paired with write/exfiltration. | Future mediated read logs and verifier policy. | Read access to evidence state is sensitive. |
| `capability_write_aeg_state` | `false` | `DENIED` | `HARD_DENY_UNTIL_EXTERNAL_ENFORCEMENT` | External enforcement that prevents executor-authored writes to `.aeg/`; future mediated recorder path only if reviewed separately. | Critical direct write authority. | Medium through evidence metadata. | Medium if paired with exfiltration. | High if evidence docs are modified. | High through resolved paths or anchors. | Critical: evidence can become self-certification. | No. | Yes, always before enforcement. | Future external enforcement proof, OS permission boundary, or mandatory broker logs. | Must remain denied; Aegis recorder/runtime writes `.aeg/` are not executor writes. |
| `capability_read_outside_repo` | `false` | `DENIED` | `DENY_UNTIL_BOUNDARY` | Outside-root read boundary with explicit allowlist, secret exclusion, and audit logs. | Medium: can discover anchors or alternate `.aeg/` paths. | High: can expose `.env`, tokens, keys, config. | Medium if paired with network/provider. | None direct. | None direct. | Medium through anchor discovery. | No. | Yes if secrets or anchors are reachable. | Future OS permission boundary or mediated broker logs. | Outside repo read is not safe without proof. |
| `capability_write_outside_repo` | `false` | `DENIED` | `HARD_DENY_PRE_LIVE` | External filesystem boundary or broker that denies writes outside approved roots. | High: may reach `.aeg/` by absolute/resolved path. | High: can alter config or secret-adjacent files. | Medium if paired with network/provider. | Medium through sibling worktrees. | Critical. | High through anchors/backups. | No. | Yes. | Future OS permission boundary or broker logs. | Hard deny before live review. |
| `capability_delete_outside_repo` | `false` | `DENIED` | `HARD_DENY_PRE_LIVE` | External filesystem boundary preventing deletes outside approved roots. | High: can destroy evidence anchors/backups. | High: can remove local security material. | Low direct. | Medium through sibling worktrees. | Critical. | High: can remove verifier inputs. | No. | Yes. | Future OS permission boundary or broker logs. | Delete is a separate destructive capability. |
| `capability_network` | `false` | `DENIED` | `DENY_UNTIL_NETWORK_BOUNDARY` | Network boundary that mediates destinations, payloads, and logs outside executor control. | Medium: evidence can be exfiltrated. | Critical if secrets are reachable. | Critical. | Low direct. | Low direct. | Medium: exfiltrated evidence can support later tamper. | No. | Yes if no network boundary. | Future network broker logs or OS/network policy proof. | Network grant is an exfiltration grant unless bounded. |
| `capability_remote_write` | `false` | `DENIED` | `HARD_DENY_PRE_LIVE` | Remote write mediation with explicit user approval and technical controls over refs, tags, releases, and remotes. | Medium for remote evidence docs. | High if credentials are involved. | High. | High remote mutation. | Medium through remote side effects. | High: can rewrite review history. | No. | Yes. | Future mediated git/remote logs plus user review gate; user review alone is not technical enforcement. | Includes push, force push, tags, releases, and remote config mutation. |
| `capability_provider_call` | `false` | `DENIED` | `DENY_UNTIL_PROVIDER_BOUNDARY` | Provider/model/API boundary with secret control, network mediation, prompt/context redaction, and logs. | Medium: evidence context can be sent. | Critical: provider credentials and prompts may expose secrets. | Critical. | Low direct. | Low direct. | Medium via externalized context. | No. | Yes if no provider boundary. | Future provider broker logs plus secret/network boundary proof. | Crosses model/API/secret/network boundary. |
| `capability_env_read` | `false` | `DENIED` | `HARD_DENY_PRE_LIVE` | Environment read boundary with explicit redaction and deny-by-default secret handling. | Medium: can reveal paths and runtime state. | Critical. | High if paired with network/provider. | Low direct. | Low direct. | Medium through token discovery. | No. | Yes. | Future OS/process boundary or redacted broker logs. | Environment values may be secrets. |
| `capability_secret_read` | `false` | `DENIED` | `HARD_DENY_PRE_LIVE` | Secret isolation boundary proving secrets are unavailable to executor. | Medium. | Critical. | Critical if paired with network/provider. | Low direct. | Medium through credential-backed mutation. | High through credential-backed tamper. | No. | Yes. | Future OS permission, secret broker, or external proof. | Secret read is hard denied before live. |
| `capability_process_spawn` | `false` | `DENIED` | `DENY_UNTIL_PROCESS_BOUNDARY` | Process boundary preventing unmediated child processes, shells, helpers, and background tasks. | High: child process can write `.aeg/`. | High: child process can read env/secrets. | High: child process can invoke network tools. | High through local commands. | High through filesystem tools. | High. | No. | Yes if no process boundary. | Future OS/process policy proof or mediated runner logs. | Process spawn can recreate shell-like authority. |
| `capability_shell` | `false` | `DENIED` | `HARD_DENY_PRE_LIVE` | No raw shell before live; any future command execution must be mediated and separately reviewed. | Critical. | Critical. | Critical. | Critical. | Critical. | Critical. | No. | Yes. | Future command broker or OS sandbox proof, not executor narrative. | Raw shell can bypass path hiding and tool policy. |
| `capability_structured_tool_call` | `false` | `NOT_GRANTED` | `NOT_SAFE_BY_DEFAULT` | Per-tool capability mediation; raw transport alone is not a grant. | Varies; high for `write_file` or `.aeg/` reads. | Varies; high for `read_file`, env, provider tools. | Varies; high for `http_request` or provider tools. | Varies; high for `write_file` or git tools. | Varies; high for broad file tools. | Varies; high for unmediated write tools. | No. | Yes if unmediated tool has write/network/provider/secret authority. | Future wrapper logs and per-tool grant proof. | `STRUCTURED_TOOL_CALL != SAFE_CAPABILITY`. |
| `capability_git_operation` | `false` | `DENIED` | `ALLOW_ONLY_WITH_MEDIATION` | Git broker limiting local diff operations and denying remote/history mutation unless separately approved. | Medium: tracked evidence docs can change; `.aeg/` may be ignored but context is mutable. | High if credentials/remotes are exposed. | High for fetch/push/remote side effects. | High. | Medium through worktrees/hooks/config. | High for branch/history/review tamper. | No. | Yes if unmediated or remote-capable. | Future mediated git logs plus user review; user review alone is not technical enforcement. | Git can mutate branches, history, tags, remotes, and hooks. |
| `capability_runtime_recorder_write` | `false` for executor | `NOT_GRANTED` for executor | `ALLOW_ONLY_WITH_MEDIATION` | Aegis runtime-owned recorder path; executor must not control recorder writes or payloads. | High if executor controls writes; expected if Aegis recorder writes. | Medium through metadata. | Low direct. | Medium for generated evidence docs if any. | Medium if recorder target is configurable. | High unless recorder remains distinct from executor. | Only for Aegis runtime, not executor. | Yes if executor receives it directly. | Aegis runtime records, manifest binding, and future external verification. | Aegis runtime/recorder may write `.aeg/`; executor must not. |

Matrix conclusion:

```text
GRANTED = unavailable in this matrix
live executor authority = ON_HOLD
future live executor default = DENIED or NOT_GRANTED
capability_write_aeg_state = HARD_DENY_UNTIL_EXTERNAL_ENFORCEMENT
```

## 7. `.aeg/` Specific Capability Rules

`.aeg/` rules:

- Aegis runtime/recorder may write `.aeg/`.
- executor must not write `.aeg/`.
- Aegis recorder/runtime writes `.aeg/` != executor writes `.aeg/`.
- `capability_write_aeg_state` must remain denied.
- `write_file`, raw shell, and repo-outside-write can bypass `.aeg/` denial if
  they are not mediated.
- path hiding is friction, not a security boundary.
- `.aeg/` gitignored != executor-isolated.
- evidence binding != tamper-proof evidence store.
- evidence store integrity status remains `NOT_CHECKED`.

The allowed recorder path is Aegis-controlled runtime behavior. It must not be
converted into an executor grant. If a future design needs executor-originated
data in `.aeg/`, it must pass through a mediated recorder path that keeps the
executor distinct from the evidence writer and records what was accepted.

Direct or indirect executor access to `.aeg/` keeps live executor authority on
hold.

## 8. Structured Tool Capability Caveat

Structured transport is not a safety boundary:

```text
STRUCTURED_TOOL_CALL != SAFE_CAPABILITY
NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY
```

Tool-specific caveats:

- `read_file` can expose secrets or `.aeg/`.
- `write_file` can tamper repo or `.aeg/`.
- `run_command` is shell-equivalent.
- `http_request` can exfiltrate.
- `git_operation` can mutate branches, history, tags, remotes, hooks, and
  release state.
- `provider_call` crosses model/API/secret/network boundaries.

Therefore a future structured tool system must be treated as a set of explicit
capability grants. It cannot be approved as a single safe transport.

## 9. Verification Source Rules

Verification source rules:

| Source | Judgment rule |
| --- | --- |
| Executor self-report | Not proof. |
| `reported_only` | Not judgment basis. |
| Static metadata | Scaffold only. |
| Manifest/evidence binding | Tamper-evident at best. |
| External enforcement | Future required for prevention claims. |
| Mediated broker logs | Future candidate when the broker is outside executor control and complete for the relevant surface. |
| OS permission boundary | Future candidate when configured and verified outside executor control. |
| User review gate | Approval boundary, not technical enforcement by itself. |

Required distinction:

```text
denied by metadata != externally enforced denial
manifest-bound evidence != tamper-proof evidence store
user approval != technical isolation
```

Post-hoc evidence can support detection claims within defined limits. It cannot
prove that a future executor lacked write, secret, network, provider, process,
or remote authority unless a pre-grant denial or mediation boundary existed.

## 10. Live Executor Blocker Matrix

If any item below is granted without the required enforcement boundary, live
executor authority remains `ON_HOLD`.

| Blocker | Why it blocks live executor authority without enforcement |
| --- | --- |
| `capability_write_aeg_state` | Direct evidence-store write authority collapses evidence into executor self-certification. |
| `capability_shell` | Raw shell can write files, spawn processes, read secrets, call network tools, and bypass path hiding. |
| `capability_write_outside_repo` | Outside writes can reach anchors, sibling worktrees, alternate roots, or `.aeg/` through resolved paths. |
| `capability_delete_outside_repo` | Deletes can destroy anchors, backups, verifier inputs, or evidence-supporting files. |
| `capability_secret_read` | Secrets can unlock provider, network, remote write, or external tamper paths. |
| `capability_env_read` | Environment values can expose tokens, paths, config, and runtime authority. |
| `capability_remote_write` | Remote refs, tags, releases, and history can be changed outside local review. |
| `capability_provider_call` | Provider calls cross model/API/secret/network boundaries and can leak context. |
| `capability_network` | Network capability can exfiltrate secrets, evidence, prompts, and repository data. |
| `capability_process_spawn` | Child processes can recreate shell, network, secret, git, or filesystem bypasses. |
| Unmediated `write_file` | Generic writes can target repo state or `.aeg/` unless path decisions are mediated. |
| Unmediated `git_operation` | Git can mutate branches, history, remotes, tags, hooks, and release state. |
| Unmediated structured tool with write/network/provider/secret capability | Structured form does not remove the underlying dangerous capability. |

These blockers are sufficient to keep authority closed. Removing a blocker in a
future gate may make review possible, but it does not itself grant live
executor authority.

## 11. Relationship To Evidence And Self-report

Capability grant decisions must be separated from evidence generation:

- an executor report that it did not use a capability is `reported_only`.
- a metadata field saying a capability is denied is scaffold-only unless the
  denial is externally enforced.
- a manifest hash can bind evidence to a packet, but evidence binding is not a
  tamper-proof evidence store.
- an Aegis recorder write can create evidence, but it does not prove the
  executor lacked broad filesystem authority.
- `NOT_CHECKED` remains `NOT_CHECKED`; it cannot be promoted to `PASS`.

Judgment basis must come from Aegis-controlled or externally verifiable
boundaries, not from executor-authored claims.

## 12. Explicit Non-goals

This document does not implement or authorize:

- live executor authority grant.
- external enforcement implementation.
- `.aeg/` permission hardening.
- `chmod`.
- `chown`.
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
- release, publish, or deploy.
- secret, token, or API key recording.
- actual `.env` value recording.
- `.aeg/` git inclusion.
- main direct push.
- main merge.

## 13. Proposed Next Gate

Recommended next gate:

```text
Phase 10 Mediated Write Boundary Design v0
```

Alternative next gate:

```text
Phase 10 Capability Grant Matrix Verify Scaffold v0
```

This document implements neither gate. The recommended next gate should define
how write mediation would work before any executor write capability, structured
tool write capability, or live executor authority is considered.

## 14. Canonical Distinctions To Preserve

The following distinctions are canonical:

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

These distinctions are mandatory review constraints. If a future change claims
that a scaffolded denial is externally enforced, that `.aeg/` is
executor-isolated because it is gitignored, that a structured tool is safe by
default, or that the current no-op baseline proves future live executor safety,
then the change must be fixed before review.

## 15. Review Checklist

This matrix is ready for user review only if:

- changed files are limited to this document or an explicitly approved short
  docs cross-reference.
- changes are docs-only.
- Phase 10 scope plan and `.aeg/` write boundary threat model remain
  consistent.
- live executor authority remains `ON_HOLD`.
- no external enforcement implementation is added.
- `.aeg/` is not described as executor-isolated.
- structured tool calls are not described as safe by default.
- `capability_write_aeg_state` remains denied.
- pre-live defaults are deny/not-granted centered.
- verification source rules reject executor self-report and `reported_only` as
  judgment basis.
- blocker matrix includes write, shell, outside repo, secret/env, remote,
  provider, network, process, unmediated write_file, unmediated git, and
  unmediated dangerous structured tool authority.
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
