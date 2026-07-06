# Aegis Phase 11-B-3-0 Restricted Propose-Only Executor Entry Gate and Forced Routing Design v0

## 1. Purpose

Phase 11-B-3-0 is an entry gate design for future restricted propose-only
executor work. It is not the actual Phase 11-B-3 implementation, not a live
executor, not a model-backed executor, not an action execution engine, and not
a provider/model/network integration.

This gate locks two rules before any actual executor work begins:

```text
ActionDecisionPacket is runtime-built only from raw executor output.
executor cannot execute arbitrary code and may output only propose-only structured data.
```

Completion target for this document:

```text
11-B-3-0 = RESTRICTED_PROPOSE_ONLY_EXECUTOR_ENTRY_GATE_DESIGN_V0
```

Safe default:

```text
safe default = hold_current_state
```

## 2. Current Baseline

Baseline context:

```text
repo = /mnt/d/Codex/Aegis
base main = d7216f0d4c564b6d7fe0b94f3c7df1abf6d768a5
accepted audit result = ACCEPT_PHASE11B_2_PRELIVE_BASELINE
Phase 11-B-2 = PHASE11B_2_VALIDATOR_ENFORCED_ROUTING_PRELIVE_BASELINE_COMPLETE
11-B-2 meaning = validator-enforced routing metadata/evidence/guard pre-live baseline
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Current authority status remains:

```text
Phase 11-B live executor = NOT_STARTED
actual model executor = NOT_STARTED
action execution engine = NOT_STARTED
provider/model/network = NOT_STARTED / NOT_GRANTED
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

## 3. Runtime-Build Packet Only Rule

`ActionDecisionPacket` must be built only by the runtime ingress adapter from
raw executor output. The executor may submit raw structured proposal data to
the ingress boundary, but it must not submit a completed `ActionDecisionPacket`
or any object that claims to be a completed decision packet.

Required rule:

```text
raw executor output
-> runtime ingress adapter
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
```

The following executor-provided fields are never a judgment basis:

```text
packet_id
created_by
authority
eligibility
store fields
execution_allowed
mutation_allowed
write_authority_granted
store_routing_allowed
store_path_reachable
capability_gate_result
live_executor_authority
safe_default
```

Executor self-report is not authority:

```text
executor self-report != authority grant
executor-provided runtime field != runtime-owned fact
executor-provided packet metadata != judgment basis
reported_only != judgment basis
```

Required rejection cases:

```text
executor submits ActionDecisionPacket directly -> REJECT
executor submits created_by=runtime_ingress_adapter -> REJECT
executor submits store_routing_allowed=true -> REJECT
executor submits store_path_reachable=true -> REJECT
executor submits execution_allowed=true -> REJECT
executor submits write_authority_granted=true -> REJECT
executor submits capability_gate_result=ALLOWED as self-report -> REJECT
```

These rejections apply even if other fields look valid. Runtime ownership is
derived from the runtime path that built the packet, not from text supplied by
the executor.

## 4. Forced Routing Rule

Executor-originated output must flow only through this route:

```text
raw executor output
-> executor_output_ingress
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
-> evidence/verify
-> metadata-only store-adjacent candidate guard
-> stop
```

The route is mandatory and terminal. It does not dispatch an action, apply a
patch, write to the store, write `.aeg`, append a ledger, call a provider, open
a network path, spawn a process, run a command, import code dynamically,
evaluate code, or grant write authority.

Required forced-routing rejections:

```text
raw executor output reaches store.py -> REJECT
unvalidated action reaches store-adjacent path -> REJECT
denied capability reaches store-adjacent path -> REJECT
reported_only/self-report reaches store-adjacent path -> REJECT
executor-built packet reaches store-adjacent path -> REJECT
```

The metadata-only store-adjacent candidate guard may inspect verified
runtime-built packet metadata only. Candidate acceptance remains metadata-only
and does not make the store path reachable.

## 5. Restricted Propose-Only Execution Surface

The executor output surface is restricted to structured proposal data only.
Initial allowed action candidates are:

| Action candidate | Interpretation |
| --- | --- |
| `NOOP` | Structured no-op proposal data only. |
| `REQUEST_EXPLANATION` | Structured request for explanation data only. |
| `REQUEST_RISK_CLASSIFICATION` | Structured risk-classification request data only. |
| `PROPOSE_PATCH` | Inert patch proposal data only. |

The allowed candidates are not an execution allowlist. They are only the first
structured data shapes that may be parsed, normalized, validated, capability
checked, and represented in a runtime-built packet.

Required non-equivalences:

```text
PROPOSE_PATCH != write
PROPOSE_PATCH != mutation
PROPOSE_PATCH != store write
PROPOSE_PATCH != apply patch
metadata-only candidate != store write
valid structured action != authorized capability
authorized capability != action executed
```

The executor must not:

```text
execute code
call tools
call shell/process
call provider/model/network
mutate filesystem
import modules dynamically
introspect runtime internals
call internal functions
read process/module/frame/memory state
submit completed decision packet
```

The executor must not receive an arbitrary-code surface. If executor output can
run in-process code, the executor can forge runtime-like objects, read or call
internal runtime state, and bypass the structured proposal boundary. Therefore
restricted propose-only work must begin from a data-only executor contract,
not from a callable code contract.

## 6. Relationship To 11-B-2

11-B-2 is accepted as the pre-live validator-enforced routing
metadata/evidence/guard baseline:

```text
ACCEPT_PHASE11B_2_PRELIVE_BASELINE
PHASE11B_2_VALIDATOR_ENFORCED_ROUTING_PRELIVE_BASELINE_COMPLETE
```

11-B-2 does not prove live executor safety. It records the current metadata
flow, evidence binding, verification expectations, metadata-only
store-adjacent candidate guard, and rejection fixtures. It does not implement
a live executor, provider/model/network path, action execution engine, write
authority, process isolation, sandbox, or arbitrary-code security boundary.

11-B-3-0 exists because a runtime-owned packet can be forged if arbitrary
in-process code is allowed. A future executor that can execute arbitrary code
could construct packet-shaped data, set `created_by=runtime_ingress_adapter`,
claim `capability_gate_result=ALLOWED`, call internal functions, inspect
runtime state, or attempt to route around the ingress adapter.

Therefore 11-B-3-0 must prevent an executor arbitrary-code surface before any
model/provider work. Runtime-build packet ownership and forced routing only
remain meaningful if executor-originated material is constrained to
propose-only structured data.

## 7. Fable 5 Comprehensive Audit Gate

Before actual 11-B-3 implementation, require a Fable 5 comprehensive audit
over:

```text
B1 / B2 / B3
11-A
11-B-0 PR #81 defense-in-depth evidence layer
11-B-1 structured executor pre-live baseline
11-B-2 validator-enforced routing pre-live baseline
11-B-3-0 entry gate design
```

Required audit questions:

```text
Is the structure ready for restricted propose-only executor work?
Is runtime-build packet only sufficiently designed?
Is executor arbitrary-code surface sufficiently blocked by design?
Are user gate conditions sufficient before live/model/provider work?
```

Actual 11-B-3 implementation must not start until this audit is complete and
accepted by the user gate described below.

## 8. User Gate

Actual 11-B-3 implementation requires an explicit user gate after the Fable 5
comprehensive audit. The gate must explicitly authorize restricted
propose-only executor implementation work and must preserve the distinction
between data-only proposal handling and actual execution.

Model/provider/network remains a separate future gate:

```text
restricted propose-only executor implementation gate != model/provider/network gate
model/provider/network = NOT_STARTED / NOT_GRANTED
```

No implicit gate is created by this document, by the audit request, by a draft
PR, by a passing check, or by acceptance of 11-B-2.

## 9. Forbidden Scope

This design gate does not implement or authorize:

```text
live model executor implementation
OpenAI/Ollama/provider connection
network call
action execution engine
write authority grant
store.py write path change
filesystem mutation
raw shell/run_command/process_spawn
eval/exec/import execution path
runtime introspection permission
sandbox/process isolation implementation
main direct push
```

Any later work that introduces one of those items is outside 11-B-3-0 and must
remain held unless a separate explicit gate authorizes it.

## 10. Required Checks For This Design Gate

This docs-only design gate should be reviewed for:

```text
docs-only preferred
runtime-build packet only rule present
forced routing rule present
restricted propose-only execution surface present
direct packet submission rejection present
introspection/internal access forbidden
relationship to 11-B-2 present
Fable 5 comprehensive audit gate present
explicit user gate present
forbidden scope scan
forbidden label / overclaim scan
secret/runtime artifact scan
tracked .aeg/.env review
git diff --check PASS
```

Expected draft PR result:

```text
PASS_DRAFT_PR_CREATED_READY_FOR_REVIEW
main merge = NOT_PERFORMED
```

## 11. Final Hold Conditions

Hold current state if any future work attempts to treat:

```text
executor-created ActionDecisionPacket as runtime-owned
executor self-report as authority
reported_only as judgment basis
valid structured action as authorized capability
authorized capability as action execution
PROPOSE_PATCH as mutation
metadata-only candidate as store write
store-adjacent metadata as store path reachability
11-B-2 pre-live baseline as live executor safety
11-B-3-0 design as actual 11-B-3 implementation
```

Final authority state:

```text
Phase 11-B live executor = NOT_STARTED
actual model executor = NOT_STARTED
action execution engine = NOT_STARTED
provider/model/network = NOT_STARTED / NOT_GRANTED
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```
