# B3-1 Raw Capability and Worktree Scope Boundary Inventory v0

## 1. Purpose

B3-1 establishes a raw capability inventory, a worktree scope boundary
inventory, and a non-grant baseline for B3.

This is docs-only inventory and boundary documentation. It is not implementation
completion, capability enforcement, worktree enforcement, path normalization
enforcement, a physical impossibility proof, a live executor authority grant, or
the start of Phase 11-A.

Required invariants:

```text
CAPABILITY_NOT_GRANTED_BY_POLICY != CAPABILITY_PHYSICALLY_IMPOSSIBLE
raw shell not granted != shell-equivalent capability impossible
INDIVIDUAL_CAPABILITY_FALSE != COMPOSITION_SAFE
STRUCTURED_TOOL_CALL != SAFE_CAPABILITY
NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL
```

## 2. B2 Status Recap

Current recap from B2-5 and the current source/docs inspection:

| Item | Current status |
| --- | --- |
| B2 evidence line | ACCEPTED |
| B2 hard blocker | PARTIAL / NOT_GREEN |
| Executor-like routing evidence | Documented as fixture-only / pre-live |
| Actual executor write mediation | Not established by B2 |
| Live runtime wiring | Not established by B2 |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Phase 11-A | `PHASE11A_NOT_STARTED` |
| B3 | `NOT_STARTED` |
| Safe default | `hold_current_state` |

The B2 evidence records executor-like and fixture-only routing evidence. It does
not make the runtime write path live and does not mediate actual executor
writes.

## 3. B3 Scope Definition

B3 is the line for declaring capability non-grants as policy/contract, recording
evidence, and detecting violation possibilities, composition bypass candidates,
and future closure candidates.

B3 is not OS-level enforcement, filesystem permission hardening, sandboxing,
containerization, or a physical impossibility proof. B3-1 is the inventory step:
it records what has not been granted by policy and what could still be reached
through composition if later tool surfaces are added without sufficient scope.

## 4. Raw Capability Inventory

| Capability | B3-1 baseline status | Inventory note | Per-item caveat |
| --- | --- | --- | --- |
| `raw_shell_authority` | `NOT_GRANTED_BY_POLICY` | Current no-op/scaffold evidence records no raw shell grant. This is not proof that shell-equivalent behavior could never appear through future composition. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `write_file_authority` | `NOT_GRANTED_BY_POLICY` | No general executor `write_file` authority is granted by current B3-1 policy baseline. A future structured file tool would still be a capability. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `run_command_authority` | `NOT_GRANTED_BY_POLICY` | No executor command runner authority is granted by current B3-1 policy baseline. A process-capable tool or script path could become command-like if later exposed. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `process_spawn_authority` | `NOT_GRANTED_BY_POLICY` | Current inspected scaffold does not grant process spawn authority. Test harnesses may invoke subprocesses as tests, not live executor authority. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `network_authority` | `NOT_GRANTED_BY_POLICY` | Current no-op/scaffold evidence records no network grant. This is policy/evidence baseline only. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `provider_model_call_authority` | `NOT_GRANTED_BY_POLICY` | Current no-op/scaffold evidence records no provider/model call grant. Provider adapter scope remains separate from a live executor grant. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `remote_write_authority` | `NOT_GRANTED_BY_POLICY` | No remote write grant is present in the B3-1 baseline. This includes repo/API/release/package side effects unless separately reviewed later. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `repo_outside_write_authority` | `NOT_GRANTED_BY_POLICY` | No outside-repo write authority is granted by the B3-1 baseline. Current boundary work is not a live OS/filesystem denial. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `aeg_state_write_authority` | `NOT_GRANTED_BY_POLICY` | Executor-authored `.aeg/` writes remain outside the intended future executor write scope. Current runtime/recorder state writes are distinct from executor write authority. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `aeg_state_read_authority` | `NOT_GRANTED_BY_POLICY` | B3-1 does not grant executor read access to `.aeg/` evidence, ledger, or manifest material. This is not a claim that the path is unreadable at the filesystem level. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `env_read_authority` | `NOT_GRANTED_BY_POLICY` | B3-1 does not grant environment or secret read authority. This is not a secret isolation proof. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |
| `secret_read_authority` | `NOT_GRANTED_BY_POLICY` | B3-1 does not grant secret read authority. Future provider/network composition must treat this as a closure candidate. | `NOT_GRANTED_BY_POLICY != PHYSICALLY_IMPOSSIBLE`; `NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL`; `NOT_GRANTED_BY_POLICY != SAFE`. |

## 5. Worktree Scope Boundary Inventory

The statuses below intentionally avoid completion language. They identify
requirements that must be handled by later B3 work before live executor entry.

| Boundary condition | B3-1 status | Inventory note |
| --- | --- | --- |
| `worktree_scope_required` | `REQUIRED_BUT_NOT_LIVE_WIRED` | Future executor writes must be scoped to the canonical worktree. B3-1 does not wire that path. |
| `aeg_state_scope_out_required` | `REQUIRED_BUT_NOT_ENFORCED` | `.aeg/` state, evidence, ledger, and manifest material must be outside executor write scope. |
| `repo_outside_write_denial_required` | `REQUIRED_BUT_NOT_ENFORCED` | Outside-repo targets must be denied by a future live boundary. B3-1 only records the requirement. |
| `path_canonicalization_required` | `FUTURE_CLOSURE_REQUIRED` | Future checks must canonicalize submitted and resolved targets before allow decisions. |
| `symlink_escape_denial_required` | `FUTURE_CLOSURE_REQUIRED` | Future checks must account for symlink or alias escapes from an allowed-looking path. |
| `parent_traversal_denial_required` | `FUTURE_CLOSURE_REQUIRED` | Future checks must account for `../` traversal into `.aeg/` or outside the repo. |
| `absolute_path_denial_required` | `FUTURE_CLOSURE_REQUIRED` | Future checks must account for absolute paths that bypass relative worktree assumptions. |
| `sibling_worktree_denial_required` | `FUTURE_CLOSURE_REQUIRED` | Future checks must account for sibling checkout/worktree confusion. |
| `unicode_path_ambiguity_handling_required` | `FUTURE_CLOSURE_REQUIRED` | Future checks must define behavior for normalization, confusables, and platform ambiguity. |

## 6. `.aeg/` Scope-Out Requirement

The `.aeg/` state/evidence/ledger area must be excluded from any future executor
write scope. This includes direct `.aeg/` paths, evidence files, manifests,
ledger material, and aliases that resolve into that area.

B3-1 does not claim this is currently guaranteed by OS permissions, filesystem
permissions, sandboxing, or containerization. B1/B2 evidence and B3
worktree/capability scope are separate lines: B1/B2 can document guard and
fixture-only routing evidence without closing B3 scope.

## 7. Path / Escape Risk Inventory

These risks are inventoried as open candidates. B3-1 does not claim they are
blocked.

| Risk | B3-1 inventory |
| --- | --- |
| Path canonicalization risk | Lexical allow/deny decisions can diverge from resolved targets. Future B3 work must measure this. |
| Symlink escape risk | A path under an allowed-looking directory may resolve into `.aeg/` or outside the repo through a symlink or alias. |
| `../` parent traversal risk | Parent traversal can move a submitted path into `.aeg/`, a sibling worktree, or outside the repo. |
| Absolute path outside repo risk | Absolute paths can bypass relative worktree assumptions unless explicitly classified. |
| Sibling worktree risk | Adjacent checkouts or worktrees can be confused with the intended repo root if scope is weak. |
| Unicode ambiguity risk | Normalization, casing, separator, and confusable-character ambiguity can defeat naive path comparison. |

## 8. Combination-Bypass Inventory

Individual non-grants do not establish composition safety:

```text
INDIVIDUAL_CAPABILITY_FALSE != COMPOSITION_SAFE
STRUCTURED_TOOL_CALL != SAFE_CAPABILITY
```

| Composition candidate | Inventory question | B3-1 result |
| --- | --- | --- |
| `write_file + weak path scope` | Could this write into `.aeg/`? | Open candidate for future closure. |
| `write_file + symlink` | Could this write outside the repo through an alias? | Open candidate for future closure. |
| `write_repo + ../ traversal` | Could this write outside the repo? | Open candidate for future closure. |
| `process_spawn + script path` | Could this become shell-equivalent execution? | Open candidate for future closure. |
| `env_read + network later` | Could this prepare secret exfiltration once network exists? | Open candidate for future closure. |
| `read_file + .aeg path exposure` | Could this expose evidence/ledger material? | Open candidate for future closure. |
| `structured tool + broad filesystem scope` | Could a dangerous capability exist without raw shell? | Open candidate for future closure. |

## 9. Non-Grant Baseline

At B3-1, the baseline records that raw shell, generic file write, command run,
process spawn, network, provider/model call, remote write, outside-repo write,
`.aeg/` state write/read, environment read, and secret read capabilities are not
granted by B3 policy.

This baseline is a policy, contract, and evidence baseline. It is not physical
enforcement proof, not external denial proof, and not a closure claim. Later B3
steps must decide how to bind, replay, and measure violations or bypass
candidates.

## 10. Future B3 Closure Candidates

Future B3 work candidates:

| Candidate | Purpose |
| --- | --- |
| B3-2 Capability Policy Contract | Define a machine-checkable capability policy contract and vocabulary. |
| B3-3 Capability Evidence + Verify Replay | Bind capability violation evidence and reject mismatches/overclaims by replay. |
| B3-4 Worktree Scope / Path Normalization Fixture Harness | Measure worktree scope and path escape candidates. Initial results may be expected red / known gap rather than blocked. |
| B3-5 B3 Status Note | Summarize evidence-supported status without upgrading to live executor authority. |

## 11. Explicit Non-Claims

B3-1 makes no claim of:

- raw shell authority grant.
- `write_file` tool.
- `run_command` tool.
- `process_spawn` tool.
- network authority grant.
- provider/model call authority grant.
- remote write authority grant.
- repo outside write authority grant.
- OS/filesystem enforcement.
- sandbox/container.
- physical impossibility proof.
- executor isolation.
- live executor.
- runtime write authority grant.
- Phase 11-A start.
- B3 closure.
- B1 hard blocker fully green.
- Live Executor Entry Gate approval.

## 12. Recommended B3 Flow

| Step | Completion meaning | Not completion of |
| --- | --- | --- |
| B3-1 Inventory / Non-grant baseline | Current capabilities, worktree scope requirements, and composition risks are documented as inventory. | Does not enforce, wire, or close B3. |
| B3-2 Capability Policy Contract | Capability vocabulary and non-grant policy become explicit contract inputs. | Does not prove runtime denial or path safety. |
| B3-3 Evidence + Verify Replay for Capability Violation | Capability records can be bound and replay can reject mismatches/overclaims. | Does not by itself grant live executor authority or enforce OS boundaries. |
| B3-4 Worktree Scope / Path Normalization Fixture Harness | Escape candidates can be measured with fixtures. Early outcomes may be expected red / known gap measurements. | Does not initially mean attempts are blocked or closure is complete. |
| B3-5 B3 Status Note | Evidence-supported B3 status is summarized for gate review. | Does not start Phase 11-A and does not approve live executor entry. |

## 13. Static Inventory Notes

Read-only inspection for B3-1 covered:

- `src/agents/noop.py`
- `src/cli/main.py`
- `src/evidence/action_boundary.py`
- `src/evidence/capability_isolation.py`
- `src/evidence/b2_executor_like_ingress_harness.py`
- `src/evidence/b2_executor_like_routing_evidence.py`
- `docs/b2_executor_like_routing_evidence_status_note_v0.md`
- `docs/live_executor_entry_gate_v0.md`
- `src/contracts.py`

Observed static inventory summary:

- Current executor path is contract-first no-op and records no provider calls,
  no network calls, no file mutation, and no actions.
- Action boundary and capability isolation modules are scaffold metadata and
  explicitly record non-live/non-implemented boundary status.
- B2 executor-like ingress and routing evidence are fixture-only/pre-live and
  keep runtime write path, live executor authority, Phase 11-A, and B3 on hold
  or not started.
- Repository tracked-file review found no tracked `.aeg/`, `.env`, ledger, run,
  manifest, evidence, key, token, secret, or PEM artifacts.

## 14. Safe Default

```text
safe default = hold_current_state
```
