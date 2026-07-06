# Aegis Phase 11-B-3 Completion Baseline v0

## Purpose

This document records the Phase 11-B-3 PR C completion baseline for the
restricted propose-only stub line.

Completion label:

```text
PHASE11B_3_RESTRICTED_PROPOSE_ONLY_STUB_BASELINE_COMPLETE_NOT_MODEL
```

This baseline is not model/provider/network work. It is not action execution,
write authority, mutation authority, store write execution, patch application,
autonomous operation, public release, or live executor promotion.

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Completion Status

```text
11-B-3-1 = COMPLETE_AS_STRUCTURAL_CONTRACT_ENFORCEMENT
11-B-3-2 = COMPLETE_AS_DETERMINISTIC_RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR
11-B-3-3 = COMPLETE_AS_INERT_PROPOSAL_EVIDENCE_VERIFY_BINDING
11-B-3-4 = COMPLETE_AS_DETERMINISTIC_NO_PROVIDER_DEMO_RUNTIME_FLOW
11-B-3-5 = COMPLETE_AS_COMPLETION_BASELINE
```

## Demo Harness Summary

Implemented file:

```text
src/evidence/demo_runtime_flow.py
```

Test coverage:

```text
tests/test_phase11b_demo_runtime_flow.py
```

The demo harness is deterministic and no-provider. It accepts only the two
canonical PR C demo tasks and stops at result evidence.

Scenario A:

```text
task = fix typo in README
classification = LOW_SAFE_PROPOSAL
fixture = restricted_stub_readme_typo_propose_patch_v0
outcome = PROPOSE_PATCH_INERT_PROPOSAL_DATA
proposal target = README.md
proposal evidence verify = accepted
```

Scenario A terminal flow:

```text
demo task
-> deterministic fixture selection
-> deterministic request classification
-> restricted stub output
-> raw output ingress
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
-> evidence/verify
-> metadata-only candidate
-> proposal evidence/verify
-> demo result evidence
-> stop
```

Scenario B:

```text
task = delete .env and push
classification = HIGH_DANGEROUS_REQUEST
outcome = HIGH_BLOCKED_DENIED_USER_GATE_REQUIRED
structured action candidate = not produced
raw output ingress = not run
proposal evidence = not applicable
```

Scenario B terminal flow:

```text
demo task
-> deterministic fixture selection
-> deterministic request classification
-> deterministic denied/gated outcome
-> demo result evidence
-> stop
```

The dangerous request evidence explains that the request targets `.env` secret
material, asks for deletion and remote push, and would require authority and a
future explicit gate that are not present in this baseline.

## Authority Status

```text
deterministic stub only = true
provider/model = not implemented
live write = not implemented
autonomous loop = not implemented
action execution engine = not implemented
write authority = not granted
proposal is data, not mutation = true
demo harness is deterministic/no-provider = true
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
```

## Non-Equivalences

```text
demo harness != live executor
deterministic stub != model executor
PROPOSE_PATCH != write
PROPOSE_PATCH != mutation
PROPOSE_PATCH != store write
PROPOSE_PATCH != apply patch
proposal evidence != patch application
demo result != action execution
dangerous request denial != filesystem protection proof
metadata-only candidate != store write
valid structured action != authorized capability
authorized capability != action executed
proposal accepted != proposal applied
completion baseline != provider readiness
completion baseline != write authority
completion baseline != proof that bypass is impossible
completion baseline != proof of tamper resistance
```

## Verification Boundaries

The demo result evidence verifier rejects rehashed overclaims that a dangerous
request was executed, applied, written, pushed, verified safe, completed, or
granted execution, mutation, write, store-routing, or store-path authority.

The safe proposal path still binds proposal evidence as inert data. A verified
proposal is not a patch application, not a store write, not a repository write,
and not action execution.

## Not Implemented

```text
provider/model adapter
OpenAI/Ollama integration
real repository mutation
real patch apply
public release materials
external unaided run
process/OS isolation
11-B-4 implementation
```

Main merge:

```text
main merge = NOT_PERFORMED
```

## Next Gate

Next gate:

```text
Phase 11-B-3 full Claude/Fable audit and user decision
```

Optional future gates only after audit/user decision:

```text
provider demo adapter scope gate
public-facing demo/README prep
true external unaided run
process/OS isolation optional strategy
11-B-4 planning
```
