# Aegis Phase 11-B-2-0 Validator-Enforced Structured Action Routing Design Gate v0

## 1. Purpose

Phase 11-B-2-0 defines the pre-live routing design gate that forces future
executor output through the Phase 11-B-1 structured action validator and
capability gate before any store-adjacent path can receive derived data.

The core conclusion is:

```text
validator contract exists != validator-enforced routing exists
```

11-B-1 established the structured action contract, schema validator, capability
gate, and deterministic fixture baseline. This document defines the forced
routing design needed between actual executor-output ingress and any
store-adjacent path.

This phase is a design gate only. It does not implement a live executor,
model-backed executor, provider/model/network integration, action execution
engine, mutation engine, filesystem mutation path, or write authority grant.

## 2. Current baseline

Current baseline:

```text
repo = /mnt/d/Codex/Aegis
current main = b3e66038fbc75e346417142024c395e3c00e63de
PR #81 = ACCEPT_PR81_AS_DEFENSE_IN_DEPTH_EVIDENCE_LAYER
PR #81 merge != 11-B-0 complete
Phase 11-B-1 = ACCEPT_PHASE11B_1_PRELIVE_BASELINE
Post-11-B-1 symlink realpath fixture gap = CLOSED_AS_DETERMINISTIC_FIXTURE_BASELINE
Phase 11-B live executor = NOT_STARTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

The accepted baseline means:

- PR #81 is store write mediation defense-in-depth and evidence-layer work.
- PR #81 merge does not make 11-B-0 complete.
- PR #81 merge does not make a live executor ready.
- PR #81 merge does not make write authority safe.
- PR #81 merge does not prove bypass impossibility.
- PR #81 merge is not an arbitrary-code security boundary.
- Phase 11-B-1 is a pre-live structured executor baseline, not live executor
  readiness.
- The symlink realpath fixture closure is a deterministic fixture baseline, not
  a bypass-impossibility proof.

## 3. Why validator-enforced routing is needed

11-B-1 made structured action validation and capability evaluation available
as contracts and code-level gates. That is not the same as proving that all
executor-originated output must pass through those gates.

The remaining design gap is routing enforcement:

```text
raw executor output must not be able to choose a store-adjacent route
raw executor output must not be able to self-report authority
raw executor output must not be treated as runtime-owned decision data
```

Without a mandatory ingress route, the validator can exist while a future
executor path still bypasses it by sending raw strings, JSON-like data, opaque
model output, or self-reported authority into a sink-facing path. Phase
11-B-2-0 therefore defines the forced boundary before implementation begins.

## 4. Executor output ingress boundary

The single executor-output ingress boundary is named:

```text
executor_output_ingress
```

All raw executor output enters Aegis through this boundary. The raw input may
arrive as:

- string output.
- JSON-like dictionary output.
- opaque model output.
- any future provider-adapter output object.

The ingress boundary must treat all such material as untrusted executor output.
It must not forward raw output to `store.py`, a ledger append path, a trusted
context path, or a store-adjacent evidence path.

The recommended routing flow is:

```text
executor_output_ingress
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> produce action_decision_packet
-> stop
```

This phase ends at the runtime-owned decision packet. It does not execute the
action, mutate files, call providers, spawn processes, run commands, or grant
write authority.

## 5. Structured action validation step

`validate_structured_action` is mandatory after parse/normalize and before
capability evaluation or store-adjacent routing.

The validation step must reject:

- unparsable raw executor output.
- unknown action types.
- forbidden action types.
- payload fields with executable semantics.
- direct store, ledger, `.aeg`, env, secret, shell, import, provider, network,
  process, callback, or arbitrary path semantics.
- structured data that tries to treat executor self-report as authority.

Validation answers only whether normalized executor output is valid structured
action data under the 11-B-1 contract. It does not answer whether the requested
capability is authorized, and it does not execute anything.

Required distinctions:

```text
valid structured action != authorized capability
validator pass != action executed
validator pass != mutation
validator pass != write authority
```

## 6. Capability gate step

`evaluate_action_capabilities` is mandatory after structured action validation.

The capability gate must decide whether a valid structured action's declared
capability requirements are allowed, limited, denied, future-gated,
user-gated, not implemented, or unknown under current policy.

The gate must reject or stop routing for:

- denied capabilities.
- future-gated capabilities without a future gate.
- user-gated capabilities without explicit user gate evidence.
- not-implemented capabilities.
- unknown capabilities.
- executor-authored `reported_only` grants.
- executor self-reported authority.

Capability evaluation answers whether validated action data may become a
runtime-owned decision packet. It does not execute the action and does not
grant write authority.

Required distinctions:

```text
authorized capability != action executed
capability gate pass != write authority
reported_only != judgment basis
executor self-report != authority grant
```

## 7. Action decision packet concept

The output of the mandatory validator and capability route is a
runtime-owned:

```text
action_decision_packet
```

The packet is not the executor's structured action object. It is Aegis runtime
data derived from validated action data and the runtime's capability decision.

Recommended packet fields for later implementation:

- `packet_id`
- `ingress_id`
- `normalized_action_ref`
- `validation_status`
- `validation_reasons`
- `capability_gate_status`
- `capability_reasons`
- `allowed_initial_action`
- `store_adjacent_eligible`
- `execution_allowed = false`
- `mutation_allowed = false`
- `write_authority_granted = false`
- `live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD`
- `decision_source = runtime_owned`

Packet rules:

```text
runtime-owned decision packet != executor self-report
validated action is not passed directly to store.py
capability decision is runtime-owned, not executor-owned
```

Packet safety depends on constrained executor capability. A runtime-owned
`action_decision_packet` must not be confused with executor self-report, but
that distinction is only meaningful if the future executor cannot run
arbitrary code that reads or tampers with runtime internals outside the action
contract. Packet safety therefore depends on both preventing arbitrary executor
code execution and forbidding introspection/internal-access actions. This is
not a claim of process isolation, sandboxing, tamper-proofing, bypass
impossibility, or live executor readiness.

## 8. Store-adjacent path boundary

The store-adjacent path is any future path that can approach `store.py`, ledger
append behavior, store mediation metadata, evidence records, or sink-facing
runtime state.

Boundary rules:

- `store.py` must not receive raw executor output.
- `store.py` must not receive executor self-reported authority.
- `store.py` must not receive a bare validated action as if it were trusted
  routing data.
- `store.py` may only receive runtime-owned data derived from validated
  structured action decisions.
- Capability decision must exist before any executor-originated request can
  reach a store-adjacent path.
- A denied capability must not reach the store-adjacent path.
- An unvalidated action must not reach the store-adjacent path.
- Executor self-report must not become the judgment basis for store-adjacent
  routing.

Preferred design:

```text
validated structured action
-> runtime-owned capability decision
-> runtime-owned action_decision_packet
-> store-adjacent path may inspect packet data only
```

The store-adjacent path must not become an execution path in 11-B-2-0. Any
future store-facing binding must remain evidence/routing metadata unless a
separate user gate grants a later mutation path.

## 9. Relationship to PR #81 store mediation

PR #81 is accepted as a store write mediation defense-in-depth and evidence
layer. It is not the primary prevention layer for executor output.

The role split is:

```text
primary prevention = validator-enforced structured action routing
defense-in-depth = PR #81 store mediation evidence layer
```

Primary prevention means a future executor cannot emit arbitrary code,
forbidden action types, forbidden capabilities, direct store writes, direct
ledger appends, raw shell requests, provider/model calls, or generic file-write
requests into the store-adjacent path.

Defense-in-depth means PR #81 store sink mediation can record and reject unsafe
store-facing attempts under the structured executor assumption. It does not
make arbitrary same-process code safe, does not prove physical prevention, and
does not replace validator-enforced ingress routing.

Required PR #81 distinctions:

```text
sink guard != arbitrary-code prevention
trusted context != arbitrary-code security boundary
defense-in-depth != physical prevention
PR #81 merge != 11-B-0 complete
PR #81 merge != live executor ready
PR #81 merge != write authority safe
```

## 10. Relationship to 11-B-1 structured executor line

11-B-1 provides the pre-live structured executor baseline:

- structured action contract.
- schema validator.
- capability gate.
- injection and escape fixtures.
- symlink realpath fixture closure.
- non-execution and non-mutation result fields.

11-B-2-0 does not replace those outputs. It defines the missing enforced route
that makes those outputs mandatory for future executor ingress.

Required distinctions:

```text
validator contract exists != validator-enforced routing exists
structured executor pre-live baseline != live executor ready
symlink fixture closure != bypass impossible
valid structured action != authorized capability
authorized capability != action executed
capability gate pass != write authority
```

11-B-3 remains a separate future candidate line for a restricted propose-only
model executor gate. It requires a Fable 5 comprehensive audit and an explicit
user gate before work begins. This phase does not move into 11-B-3.

## 11. Allowed initial actions

The initial action types eligible to become runtime-owned decision packet data
for the store-adjacent design are:

| Action type | Store-adjacent interpretation |
| --- | --- |
| `NOOP` | Runtime-owned no-op decision data only. |
| `REQUEST_EXPLANATION` | Explanation request or response data only. |
| `REQUEST_RISK_CLASSIFICATION` | Risk-classification request data only. |
| `PROPOSE_PATCH` | Inert patch proposal data only. |

`PROPOSE_PATCH` constraints:

```text
PROPOSE_PATCH != write
PROPOSE_PATCH != mutation
PROPOSE_PATCH != store write
patch content as data != code execution
```

The allowed initial actions list is not an execution allowlist. It only defines
which validated and capability-approved action decisions may be represented as
runtime-owned packet data in a pre-live store-adjacent design.

## 12. Forbidden actions/capabilities

The following executor-originated action types or capabilities must not reach
the store-adjacent path:

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
INTROSPECT_RUNTIME
INSPECT_RUNTIME_STATE
READ_RUNTIME_STATE
READ_PROCESS_STATE
READ_INTERNAL_OBJECTS
LIST_INTERNAL_OBJECTS
CALL_INTERNAL_FUNCTION
READ_MEMORY
READ_STACK
READ_FRAME_LOCALS
READ_MODULE_GLOBALS
```

The gate also rejects executor-originated attempts to smuggle those capabilities
through aliases, payload fields, target scope, self-report metadata, or
declared capability grants.

The introspection entries above are contract-level rejections, not a complete
runtime security boundary by themselves. Blocking runtime introspection is not
completed by an action allowlist alone; it also depends on an execution
environment constraint that prevents the executor from running arbitrary
Python or other arbitrary code. If arbitrary code execution is allowed, that
code can bypass action typing and directly read process state, frames, module
globals, internal objects, memory-facing data, or other runtime internals.
Therefore the design dependency is:

```text
introspection blocked
= validator/capability gate rejection
+ no arbitrary executor code execution environment constraint
```

This document fixes that relationship as a design gate. It does not implement
a live executor sandbox, arbitrary-code security boundary, process isolation,
tamper-proof runtime boundary, or proof that bypass is impossible.

## 13. Non-execution / non-mutation rule

Validation and capability approval do not execute actions.

Required fixed fields:

```text
validated action + capability gate pass != execution
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
live_executor_ready = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

This phase does not dispatch an action, apply a patch, write to `.aeg`, append
to the ledger, write files, read env or secrets, spawn a process, run a command,
import modules, evaluate code, execute code, contact providers, or open network
access.

## 14. Evidence / verify direction

Future evidence should bind the validator-enforced routing design with fields
like:

```text
validator_enforced_routing_required = true
executor_output_ingress_defined = true
raw_executor_output_reaches_store = false
structured_action_validation_required = true
capability_gate_required = true
unvalidated_action_reaches_store = false
denied_capability_reaches_store = false
reported_only_authority_reaches_store = false
store_path_accepts_only_runtime_owned_decision = true
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Future verify logic should reject evidence that asserts:

```text
raw_executor_output_reaches_store = true
unvalidated_action_reaches_store = true
denied_capability_reaches_store = true
reported_only_authority_reaches_store = true
execution_allowed = true
mutation_allowed = true
write_authority_granted = true
live_executor_ready = true
```

Hold conditions for later gates:

- raw executor output reaches a store-adjacent path.
- validation is optional or bypassable.
- capability evaluation is optional or bypassable.
- denied capabilities reach a store-adjacent path.
- executor self-report becomes authority or judgment basis.
- store path accepts raw executor output.
- PR #81 is treated as 11-B-0 completion.
- any later evidence claims action execution, mutation, write authority, live
  executor readiness, bypass impossibility, or tool-system safety.

## 15. Recommended implementation sequence

Recommended sequence:

| Step | Name | Purpose |
| --- | --- | --- |
| `11-B-2-0` | Validator-enforced routing design gate | Define the enforced ingress and store-adjacent routing design. |
| `11-B-2-1` | Executor output ingress adapter scaffold | Add the non-executing ingress adapter shape. |
| `11-B-2-2` | Structured action decision packet evidence binding | Bind runtime-owned decision packet evidence. |
| `11-B-2-3` | Store-adjacent routing guard for validated action decisions | Guard store-adjacent routing so only runtime-owned decisions can approach it. |
| `11-B-2-4` | Rejection fixtures for unvalidated / denied / reported-only actions reaching store path | Prove rejection of invalid, denied, and self-reported authority routes. |
| `11-B-2-5` | Validator-enforced routing completion baseline | Record the completion baseline without authority overclaim. |
| `11-B-3` | Restricted propose-only model executor gate | Future candidate line only after Fable 5 audit and explicit user gate. |

11-B-2 remains pre-live. 11-B-3 is the first candidate line for a restricted
model-backed executor, and this document does not start it.

## 16. Explicit non-goals

This design gate does not implement or authorize:

- live model executor implementation.
- actual executor runtime implementation.
- provider, model, OpenAI, Ollama, LLM, or network contact.
- action execution engine implementation.
- mutation engine implementation.
- write authority grant.
- raw shell authority.
- general `write_file` tool.
- `run_command` tool.
- process spawn.
- `eval`, `exec`, or import execution path.
- filesystem mutation.
- `store.py` sink guard strengthening.
- arbitrary-code security boundary.
- runtime introspection proof.
- process isolation.
- sandbox guarantee.
- OS or filesystem permission enforcement.
- sandbox or container.
- bypass-impossibility proof.
- live executor readiness.
- IPC.
- main direct push.

## 17. Safe default

The safe default remains:

```text
safe default = hold_current_state
Phase 11-B live executor = NOT_STARTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
```

If any future implementation cannot prove that executor output passed through
`executor_output_ingress`, parse/normalize, `validate_structured_action`,
`evaluate_action_capabilities`, and runtime-owned `action_decision_packet`
production before approaching a store-adjacent path, the state must remain
held.
