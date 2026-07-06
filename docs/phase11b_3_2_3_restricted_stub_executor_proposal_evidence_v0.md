# Aegis Phase 11-B-3-2/3 Restricted Propose-Only Stub Executor and Proposal Evidence v0

## Purpose

This batch implements the restricted propose-only stub executor and proposal
evidence binding for Phase 11-B-3 PR B.

It is not model/provider/network work. It is not action execution. It is not a
write path, mutation path, store write path, patch application path, or live
executor authority promotion.

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Implemented Flow

The required terminal flow is:

```text
stub executor output
-> raw output ingress
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
-> evidence/verify
-> metadata-only candidate
-> proposal evidence/verify where applicable
-> stop
```

The stub executor output is raw structured action candidate data only. It does
not return or submit an `ActionDecisionPacket`.

## 11-B-3-2 Restricted Stub Executor

Implemented file:

```text
src/evidence/restricted_propose_only_executor.py
```

The stub accepts only deterministic fixture input:

```text
{"fixture_id": "<known fixture id>"}
```

Allowed deterministic fixture outputs are:

```text
NOOP
REQUEST_EXPLANATION
REQUEST_RISK_CLASSIFICATION
PROPOSE_PATCH
```

The stub records and tests these restrictions:

```text
deterministic_fixture_input_only = true
deterministic_structured_output_only = true
output_is_raw_structured_action_candidate_data = true
output_is_action_decision_packet = false
completed_action_decision_packet_submission_allowed = false
tool_calls_allowed = false
code_execution_allowed = false
provider_model_network_allowed = false
shell_process_allowed = false
filesystem_mutation_allowed = false
store_direct_access_allowed = false
dynamic_import_allowed = false
eval_exec_allowed = false
runtime_introspection_allowed = false
executor_authority_claim_allowed = false
```

## 11-B-3-3 Proposal Evidence

Implemented file:

```text
src/evidence/proposal_evidence.py
```

Proposal evidence binds only verified runtime-built `PROPOSE_PATCH` packet
metadata. The evidence includes:

```text
proposal_id
proposal_summary
target_files
patch_summary
patch_plan
patch_diff
risk_classification
capability_gate_result
packet_evidence_hash
metadata_candidate_gate_status
```

`patch_diff` is inert proposal data. It is not applied.

Required false fields are bound and verified:

```text
proposal_applied = false
patch_applied = false
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_ready = false
safe_default = hold_current_state
```

## Proposal Verify Rejections

Proposal verification rejects rehashed true-value overclaims for:

```text
proposal_applied
patch_applied
patch_proposal_claims_applied
execution_allowed
mutation_allowed
write_authority_granted
store_routing_allowed
store_path_reachable
live_executor_ready
executor_claims_done
executor_claims_safe
executor_claims_verified
executor_claims_write_authority
executor_claims_mutation_authority
```

The verifier requires a runtime-built `ActionDecisionPacket` argument. Direct
proposal evidence without the runtime packet is rejected.

## Non-Equivalences

This batch binds and verifies:

```text
PROPOSE_PATCH != write
PROPOSE_PATCH != mutation
PROPOSE_PATCH != store write
PROPOSE_PATCH != apply patch
proposal evidence != patch application
metadata-only candidate != store write
valid structured action != authorized capability
authorized capability != action executed
proposal accepted != proposal applied
```

## Forbidden Scope Not Implemented

This batch does not implement:

```text
OpenAI/Ollama/provider/model call
provider/model/network integration
action execution engine
write authority grant
filesystem mutation by the stub or proposal evidence path
store write execution
direct patch apply
raw shell/write_file/run_command/process_spawn
eval/exec/dynamic import execution path
runtime introspection/internal object access
autonomous loop
live_executor_authority promotion
true execution_allowed
true mutation_allowed
true write_authority_granted
true store_routing_allowed
true store_path_reachable
```

Main merge remains:

```text
main merge = NOT_PERFORMED
```
