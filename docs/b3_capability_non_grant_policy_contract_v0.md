# B3-2 Capability Non-Grant Policy Contract v0

## 1. Purpose

B3-2 defines a machine-checkable policy contract for raw capability non-grants.
It means the capability grant policy contract exists. It does not mean a runtime
boundary has denied an operation, a tool has been gated, or a filesystem layer
has made a capability unreachable.

## 2. B3-1 Recap

B3-1 documented the raw capability inventory, worktree scope requirements, and
non-grant baseline. It preserved the current authority line:

| Item | Current status |
| --- | --- |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Phase 11-A | `PHASE11A_NOT_STARTED` |
| Safe default | `hold_current_state` |

B3-1 also kept composition bypass candidates open. B3-2 preserves that reading
and does not convert those candidates into closure.

## 3. B3-2 Scope

B3-2 is policy and schema work only:

- define capability policy object fields.
- define default non-grant values.
- reject overclaim candidates in contract validation.
- prepare a B3-3 evidence and verify replay handoff.

B3-2 does not add enforcement, sandboxing, command execution, runtime write path
wiring, live executor authority, or Phase 11-A work.

## 4. Capability Policy Schema

Each capability policy object contains:

| Field | Meaning |
| --- | --- |
| `capability_name` | One capability from the B3-2 capability field list. |
| `granted` | Boolean policy grant status. Defaults to `false`. |
| `grant_source` | The grant source. Defaults to `policy_default_non_grant`. |
| `check_status` | Validation state. Defaults to `NOT_CHECKED`. |
| `scope_note` | Human-readable policy scope note. |
| `evidence_required` | Whether grant evidence is required. Defaults to `false` for non-grants. |
| `overclaim_risk` | Whether the object is already marked as overclaim-prone. |
| `non_claim_caveat` | Caveat that policy non-grant is not runtime denial, path safety, or closure. |

The B3-2 capability fields are:

- `raw_shell_authority`
- `write_file_authority`
- `run_command_authority`
- `process_spawn_authority`
- `network_authority`
- `provider_model_call_authority`
- `remote_write_authority`
- `repo_outside_write_authority`
- `aeg_state_write_authority`
- `aeg_state_read_authority`
- `env_read_authority`
- `secret_read_authority`

## 5. Default Non-Grant Fields

The default contract sets every capability to:

| Field | Default |
| --- | --- |
| `granted` | `false` |
| `policy_status` | `NOT_GRANTED_BY_POLICY` |
| `grant_source` | `policy_default_non_grant` |
| `check_status` | `NOT_CHECKED` |
| `evidence_required` | `false` |
| `overclaim_risk` | `false` |

The contract-level defaults remain:

- `live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD`
- `runtime_write_path = NOT_WIRED_TO_EXECUTOR_WRITE_PATH`
- `phase11a_status = PHASE11A_NOT_STARTED`
- `safe_default = hold_current_state`

## 6. Overclaim Rejection Candidates

Contract validation rejects these candidates:

- `granted=true` with missing `evidence_ref`.
- `grant_source=reported_only` with a PASS-like claim.
- `check_status=NOT_CHECKED` with a PASS-like claim.
- `granted=true` with an unknown grant source.
- claims that policy non-grant proves physical impossibility.
- claims that policy non-grant proves outside denial.
- claims that individual false capability fields prove composition closure.
- claims that structured tool shape proves capability safety.
- claims that live executor authority is ready.
- claims that Phase 11-A has started.

The validator also reports overclaim candidates when `granted=true` is combined
with `grant_source=reported_only` and an unchecked status.

## 7. reported_only / NOT_CHECKED Handling

`reported_only` data is not a judgment basis for a PASS-like capability claim.
`NOT_CHECKED`, missing, and unknown check states are also not PASS-like
capability proof. They can be represented in a contract object, but validation
rejects promotion to PASS-like status.

## 8. Physical Enforcement Non-Claims

B3-2 policy validation is not runtime enforcement, tool execution gating,
OS/filesystem hardening, sandboxing, containerization, command mediation,
provider mediation, network mediation, or remote write mediation.

## 9. Composition Bypass Caution

An individual capability set to `granted=false` does not prove that a later
composition of structured tools, weak path scope, provider access, network
access, or environment access is closed. B3-1 bypass candidates remain open
until later evidence and fixture work measures them.

## 10. B3-3 Evidence / Verify Handoff

B3-2 provides the contract foundation for B3-3. B3-3 can bind capability records
to evidence, replay the contract, and reject mismatches or overclaims. B3-2
itself does not bind live evidence or add replay to the runtime verifier.

## 11. Current Authority

Current authority remains:

- raw capability grants: `NOT_GRANTED_BY_POLICY` by default.
- live executor authority: `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- runtime write path: `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- Phase 11-A: `PHASE11A_NOT_STARTED`.
- B3 overall: in progress, not enforced, not closed.

## 12. Explicit Non-Claims

B3-2 makes no claim of:

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

## 13. Safe Default

```text
safe default = hold_current_state
```
