# Aegis Phase 11-B-1b Structured Action Schema Contract v0

## 1. Purpose

Phase 11-B-1b adds the first machine-checkable structured action schema
contract and validator for future executor output.

The goal is narrow:

```text
executor output = data, not code
validator pass != action executed
validator pass != mutation
validator pass != write authority granted
validator pass != live executor ready
```

This phase creates a contract surface. It does not create a live model
executor, action runtime, execution engine, provider call path, network path,
raw shell authority, command runner, generic file write tool, process spawn
surface, or filesystem permission boundary.

Implementation:

```text
src/evidence/structured_actions.py
tests/test_phase11b_structured_actions.py
```

## 2. Relationship to PR #82 / 11-B-1a

PR #82 merged the Phase 11-B-1a design baseline:

```text
Phase 11-B-1a = COMPLETE_AS_DOCS_ONLY_DESIGN_BASELINE
```

11-B-1a defined the design stance that future executor output must be
structured action data rather than arbitrary same-process Python or shell
authority.

11-B-1b turns that design baseline into an import-safe schema contract and
validator. It preserves the 11-B-1a non-claims:

```text
11-B-0 = NOT_COMPLETE
11-B-0-b/c = NOT_READY_FOR_COMPLETION
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
PR #81 draft release = NOT_PERFORMED
PR #81 merge = NOT_PERFORMED
```

## 3. Structured action definition

A structured action is a mapping with the required fields:

| Field | Meaning |
| --- | --- |
| `action_type` | One action type from the finite action vocabulary. |
| `action_id` | Stable identifier for this proposed action data item. |
| `declared_intent` | Human-readable intent, not executable instruction. |
| `declared_risk` | Declared risk label. It is metadata, not authority. |
| `capability_requirements` | Data declaration of requested capability names. |
| `target_scope` | Bounded scope data. It must not smuggle `.aeg/`, absolute write targets, env, secret, shell, import, callback, provider, network, or process semantics. |
| `payload` | Action-specific data. It must not contain executable fields or direct sink/write semantics. |

The v0 schema is intentionally conservative. A valid schema means the object is
well-formed data under the current policy. It does not mean the action should
be performed.

## 4. Executor output = data, not code

The executor output model is:

```text
executor_output_model = DATA_NOT_CODE
structured_action_schema_enforced = true
```

The contract records these explicit defaults:

```text
arbitrary_python_execution_allowed = false
eval_exec_allowed = false
import_allowed = false
raw_shell_allowed = false
run_command_allowed = false
process_spawn_allowed = false
store_sink_direct_access_allowed = false
aeg_state_write_allowed = false
general_write_file_allowed = false
network_allowed = false
provider_model_call_allowed = false
```

Structured data is not safe by default. It is only eligible for later
mediation. Any future action performance still needs a separate capability
gate, path policy, review policy, and evidence binding.

## 5. Allowed action type set

Initial allowed action types:

| Action type | Interpretation |
| --- | --- |
| `PROPOSE_PATCH` | Produce reviewable patch proposal data. Not mutation and not `write_repo`. |
| `REQUEST_REPO_READ` | Request bounded repository context. Not unrestricted filesystem read. |
| `REQUEST_RISK_CLASSIFICATION` | Request risk classification. Not authority grant. |
| `REQUEST_EXPLANATION` | Request or provide explanatory data. |
| `NOOP` | Explicit no-op. It is not a hidden action. |

The allowlist is finite in `ALLOWED_ACTION_TYPES`.

## 6. Forbidden action type set

Initial forbidden action types:

```text
WRITE_AEG_STATE
DIRECT_STORE_WRITE
DIRECT_LEDGER_APPEND
WRITE_FILE
RUN_COMMAND
RAW_SHELL
PROCESS_SPAWN
NETWORK_REQUEST
PROVIDER_MODEL_CALL
IMPORT_MODULE
EVAL_EXEC
READ_ENV
READ_SECRET
OPEN_ARBITRARY_PATH
CALL_INTERNAL_FUNCTION
PYTHON_CODE
```

The denylist is finite in `FORBIDDEN_ACTION_TYPES`. Unknown action types are
also rejected.

## 7. Capability taxonomy mapping

11-B-1b maps executor-facing action types to capability names and policy
statuses. This is a policy contract, not a grant.

| Action type | Capability | Status |
| --- | --- | --- |
| `PROPOSE_PATCH` | `propose_patch` | `ALLOWED_UNDER_POLICY` |
| `REQUEST_REPO_READ` | `read_repo` | `LIMITED` |
| `REQUEST_REPO_WRITE` | `write_repo` | `MEDIATED_AND_FUTURE_GATED` |
| `WRITE_AEG_STATE` | `aeg_state_write` | `DENIED` |
| `DIRECT_STORE_WRITE` | `store_sink_direct_access` | `DENIED` |
| `DIRECT_LEDGER_APPEND` | `ledger_append_direct_access` | `DENIED` |
| `WRITE_FILE` | `general_write_file` | `DENIED` |
| `RAW_SHELL` | `raw_shell` | `DENIED` |
| `RUN_COMMAND` | `run_command` | `DENIED` |
| `PROCESS_SPAWN` | `process_spawn` | `DENIED` |
| `NETWORK_REQUEST` | `network` | `DENIED` |
| `PROVIDER_MODEL_CALL` | `provider_model_call` | `DENIED_UNTIL_EXPLICIT_GATE` |
| `READ_ENV` | `env_read` | `DENIED` |
| `READ_SECRET` | `secret_read` | `DENIED` |

The B3 reference fields in the mapping are checked against
`src.evidence.b3_capability_policy_contract.CAPABILITY_FIELDS`. The contract
preserves the B3 distinction:

```text
NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL
STRUCTURED_TOOL_CALL != SAFE_CAPABILITY
PROPOSE_PATCH != write_repo
REQUEST_REPO_READ != unrestricted filesystem read
REQUEST_RISK_CLASSIFICATION != authority grant
request_write_repo != raw write_file
```

## 8. Payload rules

`PROPOSE_PATCH` payload may contain:

```text
target_files
patch_summary
patch_diff
patch_plan
```

Forbidden payload fields or semantics include:

```text
python_code
eval_code
exec_code
shell
command
shell_command
callback
callback_name
function_name
function_pointer
callable_reference
module
import_module
import_path
raw_file_write
absolute_write_path
aeg_path
env_key
secret_key
provider
network
url
process_spawn
store_sink
store_sink_direct_access
direct_store_write
direct_ledger_append
ledger_append
```

The validator also rejects path-like payload or target-scope values that point
at `.aeg/` or use absolute paths. Env or secret read requests are rejected
through forbidden fields, forbidden action types, and capability requirement
checks.

## 9. Validator behavior

The validator returns a `StructuredActionValidationResult` with:

```text
valid
status
reasons
action_type
live_executor_authority
action_executed
filesystem_mutated
write_authority_granted
live_executor_ready
```

Validation statuses:

```text
VALID_STRUCTURED_ACTION
INVALID_ACTION_SCHEMA
UNKNOWN_ACTION_TYPE_REJECTED
FORBIDDEN_ACTION_TYPE_REJECTED
FORBIDDEN_PAYLOAD_FIELD_REJECTED
CAPABILITY_DENIED
FUTURE_GATE_REQUIRED
USER_GATE_REQUIRED
```

Validator requirements implemented in v0:

- valid structured action schema passes.
- unknown action types reject.
- forbidden action types reject.
- executable payload fields reject.
- direct store/sink and direct ledger access reject.
- `.aeg/` state write requests reject.
- raw shell, `run_command`, and process spawn reject.
- provider/model/network requests reject unless a future explicit gate exists.
- env and secret read requests reject.
- `reported_only` capability grant claims are rejected.

## 10. Non-execution guarantee

The validator is pure schema and policy validation. It has no action execution
API and no mutation sink.

The result object always records:

```text
action_executed = false
filesystem_mutated = false
write_authority_granted = false
live_executor_ready = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

A valid `PROPOSE_PATCH` remains data. It is not applied to the repository. A
valid `REQUEST_REPO_READ` remains a request. It is not a filesystem read. A
valid `NOOP` remains no operation. It cannot hide action semantics in payload
fields.

## 11. Relationship to 11-B-0-b sink guard

11-B-0-b sink guard remains separate and not completion-ready:

```text
11-B-0 = NOT_COMPLETE
11-B-0-b/c = NOT_READY_FOR_COMPLETION
```

11-B-1b does not strengthen `store.py` sink guards. It also does not wire
store sinks, add trusted context, or add process isolation.

This contract supports the 11-B-1a model:

```text
executor cannot call store.py sinks directly
executor cannot execute arbitrary Python
executor submits structured action data only
```

That model makes sink guard a later defense-in-depth and tamper-evidence topic.
It does not complete sink guard work by itself.

## 12. Relationship to 11-B-1c capability gate / evidence / verify

11-B-1b scope:

```text
schema contract + validator
```

11-B-1c candidate scope:

```text
capability gate
evidence binding
verify overclaim rejection
tool injection and escape fixtures
```

11-B-1b intentionally stops before implementing a mediator or gate that
performs actions. A future gate must independently decide whether valid
structured data may become a read, patch proposal review, mediated write
request, or denial record.

## 13. Explicit non-goals

11-B-1b does not implement or authorize:

- live model executor implementation.
- actual executor runtime implementation.
- action execution engine implementation.
- provider, model, OpenAI, Ollama, LLM, or network contact.
- raw shell authority.
- general `write_file` tool.
- `run_command` tool.
- process spawn.
- arbitrary Python executor runtime.
- `eval`, `exec`, or dynamic import execution path.
- `store.py` sink guard strengthening.
- process isolation.
- OS or filesystem permission enforcement.
- sandbox, container, or IPC boundary.
- PR #81 draft release.
- PR #81 merge.
- main direct push.

## 14. Safe default

The safe default remains:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PR #81 = HOLD / OPEN / draft
PR #81 draft release = NOT_PERFORMED
PR #81 merge = NOT_PERFORMED
main merge = NOT_PERFORMED
```

11-B-1b is ready for draft review only after tests and scans pass. It does not
unlock live executor authority and does not complete 11-B-0-b/c.
