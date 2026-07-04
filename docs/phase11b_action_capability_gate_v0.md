# Aegis Phase 11-B-1c Action Capability Gate v0

## 1. Purpose

Phase 11-B-1c adds a deterministic capability authorization gate after the
Phase 11-B-1b structured action schema validator.

The flow is intentionally narrow:

```text
raw executor output
-> structured action schema validation
-> capability gate evaluation
-> result only
```

The gate decides whether the declared action capabilities are allowed,
limited, denied, future-gated, user-gated, not implemented, or unknown under
the current policy. It does not execute the action.

Implementation:

```text
src/evidence/structured_action_capabilities.py
tests/test_phase11b_action_capability_gate.py
```

## 2. Relationship to 11-B-1a and 11-B-1b

11-B-1a is the docs-only structured executor capability model baseline.
11-B-1b is the structured action schema contract and validator baseline.
11-B-1c adds the capability gate that evaluates validated action data.

The phase boundaries remain:

```text
11-B-1a = design baseline
11-B-1b = action schema validation
11-B-1c = action capability authorization gate
11-B-0 = NOT_COMPLETE
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

## 3. Schema validation vs capability gate distinction

Schema validation answers whether executor output is well-formed structured
action data under the Phase 11-B-1b contract.

Capability gate evaluation answers whether the action's required capabilities
are authorized under the Phase 11-B-1c non-grant policy.

These are separate claims:

```text
valid schema != authorized capability
capability gate pass != action execution
capability gate pass != mutation
capability gate pass != write authority granted
capability gate pass != live executor ready
```

## 4. Capability status vocabulary

The Phase 11-B-1c capability status vocabulary is:

```text
ALLOWED_UNDER_POLICY
LIMITED
DENIED
FUTURE_GATED
USER_GATED
NOT_IMPLEMENTED
```

Gate policy:

| Status | Gate behavior |
| --- | --- |
| `ALLOWED_UNDER_POLICY` | Allowed as validated action data only. |
| `LIMITED` | Allowed only when declared scope stays within policy limits. |
| `DENIED` | Rejected. |
| `FUTURE_GATED` | Rejected as `FUTURE_GATE_REQUIRED`. |
| `USER_GATED` | Rejected as `USER_GATE_REQUIRED` unless explicit user gate evidence is supplied. |
| `NOT_IMPLEMENTED` | Rejected as `NOT_IMPLEMENTED_REJECTED`. |

## 5. Default denied capabilities

The default denied capability surface is:

```text
raw_shell
process_spawn
network
provider_model_call
general_write_file
write_file
run_command
eval_exec
import_module
store_sink_direct_access
aeg_state_write
direct_ledger_append
ledger_append_direct_access
env_read
read_env
secret_read
read_secret
```

`provider_model_call` is deny-by-default and currently represented as a
future-gated capability, so it rejects as `FUTURE_GATE_REQUIRED` rather than
becoming executable authority.

## 6. Allowed / limited action-capability mapping

Allowed or limited action mappings:

| Action type | Required capabilities | Gate status |
| --- | --- | --- |
| `NOOP` | `noop` | `ALLOWED_UNDER_POLICY` |
| `REQUEST_EXPLANATION` | `explanation` | `ALLOWED_UNDER_POLICY` |
| `REQUEST_RISK_CLASSIFICATION` | `risk_classification` | `ALLOWED_UNDER_POLICY` |
| `PROPOSE_PATCH` | `propose_patch`, `repo_target_scope` | `ALLOWED_UNDER_POLICY` plus `LIMITED` scope |
| `REQUEST_REPO_READ` | `read_repo` | `LIMITED` scope |

Important non-equivalences:

```text
PROPOSE_PATCH != write_repo
REQUEST_REPO_READ != unrestricted filesystem read
LIMITED read != .aeg read
LIMITED read != env/secret read
```

## 7. Future-gated and user-gated handling

`FUTURE_GATED` capabilities return `FUTURE_GATE_REQUIRED`. They do not pass as
execution candidates and do not grant any write, network, provider, model, or
runtime authority.

`USER_GATED` capabilities return `USER_GATE_REQUIRED` unless explicit user gate
evidence is supplied to the gate. Executor self-report is not user gate
evidence.

## 8. reported_only / self-report rejection

The gate rejects or ignores executor-authored authority claims. The v0 gate
rejects these claims deterministically:

```text
capability_granted = true
granted = true
trusted = true
authority = write_file
approved_by_executor = true
safe = true
grant_source = reported_only
source = reported_only
```

The result is `REPORTED_ONLY_CAPABILITY_GRANT_REJECTED`.

Non-authority rules:

```text
reported_only != judgment basis
executor self-report != capability grant
schema payload claim != authority
```

## 9. Non-execution guarantee

The capability gate returns a result object only. It contains no execution
engine and no runtime dispatch path.

Every gate result records:

```text
execution_allowed = false
live_executor_ready = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

`CAPABILITY_GATE_ALLOWED` and `CAPABILITY_GATE_LIMITED_ALLOWED` mean only that
the action data passed the current non-executing policy gate.

## 10. Non-mutation guarantee

The capability gate has no mutation sink and performs no filesystem writes.

Every gate result records:

```text
mutation_allowed = false
write_authority_granted = false
```

`PROPOSE_PATCH` remains a proposal. It is not applied to the repository.
`REQUEST_REPO_READ` remains a request. It is not a filesystem read.

## 11. Evidence / verify contract

`build_action_capability_gate_evidence()` records deterministic evidence for:

```text
capability gate version
schema validation function
capability gate function
capability status vocabulary
capability gate result vocabulary
default denied capabilities
allowed/limited action-capability mapping
reported_only grant rejection
executor self-report rejection
non-execution flags
non-mutation flags
live executor authority snapshot
safe default
```

This evidence is a contract record only. It is not external enforcement, not a
runtime permission proof, and not live executor readiness.

## 12. Relationship to PR #81

PR #81 remains:

```text
HOLD / OPEN / draft
draft release = NOT_PERFORMED
merge = NOT_PERFORMED
```

Phase 11-B-1c does not release, merge, or modify PR #81.

## 13. Explicit non-goals

Phase 11-B-1c does not implement or authorize:

- live executor runtime.
- actual executor action execution engine.
- provider, model, OpenAI, Ollama, LLM, or network contact.
- raw shell authority.
- generic `write_file` authority.
- `run_command` authority.
- process spawn.
- arbitrary Python execution.
- `eval`, `exec`, or dynamic import execution paths.
- filesystem mutation.
- store sink guard strengthening.
- process, OS, sandbox, container, or IPC isolation.
- PR #81 draft release.
- PR #81 merge.
- main direct push.

## 14. Safe default

The safe default remains:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
11-B-0 = NOT_COMPLETE
PR #81 = HOLD / OPEN / draft
main merge = NOT_PERFORMED
```

If capability status or scope is unknown, the gate rejects. If evidence is only
reported by the executor, the gate rejects. If scope points at `.aeg`, env, or
secret targets, the gate rejects.
