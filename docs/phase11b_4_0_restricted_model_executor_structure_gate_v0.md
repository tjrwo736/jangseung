# Aegis Phase 11-B-4-0 Restricted Model Executor Structure Gate v0

## Purpose

Phase 11-B-4-0 is a design gate for the structure of a future restricted
model executor. It is not an implementation of a model executor, provider
adapter, network path, response parser, tool runtime, action execution engine,
write path, or patch application path.

Core principle:

```text
restricted model executor = no tools, propose-only, data-only
```

Completion label:

```text
PHASE11B_4_0_RESTRICTED_MODEL_EXECUTOR_STRUCTURE_GATE_COMPLETE_NOT_PROVIDER
```

Required limits:

```text
NOT_MODEL_PROVIDER_INTEGRATION
NOT_PROVIDER_READY
NOT_NETWORK_ENABLED
NOT_ACTION_EXECUTION_ENGINE
NOT_WRITE_AUTHORITY
NOT_TOOL_RUNTIME
NOT_PATCH_APPLY
NOT_LIVE_EXECUTOR_READY
STRUCTURED_EXECUTOR_ASSUMPTION_REQUIRED
PROVIDER_GATE_REQUIRED
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Current Authority Status

Current status remains:

```text
provider/model/network = NOT_STARTED / NOT_GRANTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store.py access by model = NOT_GRANTED
trusted context access by model = NOT_GRANTED
runtime internals access by model = NOT_GRANTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Phase 11-B-4-0 does not change `live_executor_authority` and does not change
the safe default.

## Required Design Answers

1. Restricted model executor output type

The future restricted model executor output type is raw executor output only:

```text
RestrictedModelRawOutputV0 =
  provider_or_adapter_text_candidate
  OR JSON object text candidate
  OR parsed structured proposal data candidate
```

It is data. It is not a callable object, not a Python object with behavior, not
an `ActionDecisionPacket`, not a provider response trusted directly, not a tool
call, not a command, not a file write request, and not an internal runtime call.

The only accepted downstream shape is proposal data suitable for
`executor_output_ingress`. Any text form must first become raw executor output
and then pass the same parse, normalize, validation, capability, packet-build,
evidence, and metadata-only candidate path as other executor output.

2. Model output is raw executor output only

Model output has no direct authority. If a future provider returns text, that
text is converted only into raw executor output. It is then routed through:

```text
model/provider text
-> raw executor output
-> executor_output_ingress
-> parse/normalize
-> validate_structured_action
-> evaluate_action_capabilities
-> runtime-built ActionDecisionPacket
-> evidence/verify
-> metadata-only candidate where applicable
-> stop
```

Provider output is never trusted directly. Model self-report, provider
self-report, claimed safety, claimed validation, claimed authority, claimed
execution, claimed file status, or claimed runtime ownership is not a judgment
basis.

3. Non-JSON or malformed JSON fails closed

If the expected restricted output is JSON object data and the raw text is not a
JSON object, cannot be decoded, decodes to a scalar/list instead of a mapping,
or is missing required structured proposal fields, the result is a closed
failure:

```text
parse_status = PARSE_FAILED
validation_result = None
capability_result = None
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
store_routing_allowed = false
store_path_reachable = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Plain text may exist only as raw text candidate material. Plain text has no
automatic action meaning and cannot be coerced into a command, write, patch
application, tool call, or internal runtime call.

4. Completed ActionDecisionPacket-shaped output is rejected

The model must not submit a completed `ActionDecisionPacket` or any
packet-shaped object. Packet-like fields from a model are treated as an
attempted direct packet submission and fail closed, including fields such as:

```text
packet_id
raw_output_hash
parse_status
normalized_action
validation_result
capability_result
decision_basis
adapter_version
created_by
runtime_built_by_ingress
execution_allowed
mutation_allowed
write_authority_granted
store_routing_allowed
store_path_reachable
```

Runtime ownership is path-owned, not text-owned. `ActionDecisionPacket` remains
runtime-built only by `executor_output_ingress`.

5. Tool calls, commands, code blocks, mutation requests, and internal calls are rejected

The future restricted model executor has no tool surface. Any model-originated
payload is rejected if it contains or requests:

```text
tool calls
function calls
internal function calls
runtime introspection
shell commands
process spawn requests
command-like fields
code blocks
eval or exec intent
dynamic import intent
filesystem mutation
file write requests
store writes
ledger appends
patch application
provider/network calls
autonomous loop control
```

Rejected command-like fields include future equivalents of `tool_calls`,
`function_call`, `tools`, `tool_choice`, `command`, `cmd`, `shell`, `run`,
`process`, `spawn`, `exec`, `eval`, `import`, `write_file`, `delete_file`,
`move_file`, `apply_patch`, `store_write`, and `ledger_append`.

Structured proposal data may describe an inert proposal, but it cannot contain
an instruction to execute, write, apply, spawn, inspect runtime internals, or
call a tool. Accepted downstream proposal material remains metadata-only until
a separate future gate changes that status.

6. "Model has no tools" is structural

The no-tool condition is represented as structure, not trust in model behavior:

```text
available_tools = ()
tool_schemas = ()
tool_runtime = disabled
tool_choice = none
max_tool_calls = 0
function_calling_allowed = false
shell_process_allowed = false
filesystem_mutation_allowed = false
provider_network_allowed_by_model_executor = false
runtime_internal_call_handles = ()
trusted_context_handles = ()
store_module_handles = ()
```

The future model request context must not include callable handles, tool
schemas, shell/process APIs, filesystem mutation APIs, store module objects,
trusted runtime context, `.aeg` authority state, environment secrets, or
runtime internals.

7. Provider and network are a future explicit provider gate

Phase 11-B-4-0 does not implement provider selection, network use, API key
loading, environment loading, prompt construction, live response parsing, raw
prompt retention, raw response retention, provider SDK calls, or a live model
adapter.

Provider/network work remains separated:

```text
11-B-4-0 = restricted model executor structure gate
11-B-4-1 = deterministic no-provider model-like adapter or dry structure
11-B-4-2 = optional provider boundary scope
11-B-4-3 = actual provider adapter only after explicit provider gate
```

A later provider adapter, if ever approved, may only produce raw executor
output candidate material. It must not bypass `executor_output_ingress`.

8. Next implementation step

The next implementation step should be deterministic and no-provider:

```text
recommended next step = 11-B-4-1 deterministic no-provider model-like adapter or dry structure
```

That step should exercise the structure without provider calls, network calls,
secret loading, live response parsing, tools, action execution, write
authority, or runtime authority promotion.

9. Duration of live executor authority hold

`live_executor_authority` remains `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` through
Phase 11-B-4-0 and remains on hold until a later explicit gate authorizes a
different state. A design PR, passing tests, draft PR review, main merge,
deterministic dry adapter, provider boundary scope, or provider adapter
existence does not promote authority by itself.

10. Conditions required before provider gate can open

Before a provider gate can open, all of these conditions are required:

```text
explicit user authorization for provider work
accepted 11-B-4-1 deterministic no-provider structure
accepted provider boundary scope if 11-B-4-2 is used
secret and environment loading policy approved
network opt-in policy approved
prompt and response redaction policy approved
raw prompt and raw response retention policy approved or explicitly denied
provider error handling defined as secret-safe metadata
provider output trust boundary preserved as raw executor output only
provider output forced through executor_output_ingress
ActionDecisionPacket remains runtime-built only
tool runtime remains absent unless a separate gate explicitly authorizes it
action execution engine remains absent unless a separate gate explicitly authorizes it
write authority remains absent unless a separate gate explicitly authorizes it
safe default remains hold_current_state unless a separate gate explicitly changes it
tests and scans prove no forbidden provider/model/network implementation is present
```

Opening a provider gate is not the same as enabling a live executor, action
execution, write authority, tool runtime, or mutation authority.

## Fail-Closed Rejection Rules

Rejected model-originated material:

```text
non-JSON object where JSON object is required
malformed JSON
scalar or list JSON where mapping is required
completed ActionDecisionPacket-shaped output
packet evidence-shaped output
store-adjacent candidate-shaped output
tool call or function call payload
shell/process command payload
code block payload
filesystem mutation request
patch application request
store or ledger write request
internal runtime function call request
runtime introspection request
provider/network request
authority self-report
reported_only self-report as judgment basis
```

Closed failure means:

```text
no validation authority
no capability authority
no execution
no mutation
no write authority
no store route
no store path
no tool call
no provider/network call
no autonomous loop
hold_current_state
```

## Non-Equivalences

Required non-equivalences:

```text
model output != code execution
model output != shell command
model output != file write
model output != internal function call
model output != runtime introspection
model output != ActionDecisionPacket
provider output != trusted decision
provider output != authority grant
raw executor output != runtime-built packet
structured proposal != executed action
accepted downstream proposal != mutation
accepted downstream proposal != write authority
metadata-only candidate != store write
provider gate != live executor authority
```

## Forbidden Scope Not Implemented

This phase does not implement or authorize:

```text
actual model/provider/network call
OpenAI/Ollama/LLM call
API key loading
environment secret loading
live provider adapter
provider response parser for live calls
action execution engine
write authority grant
file mutation by executor output
shell/run_command/process_spawn authority
eval/exec/import execution path
tool calling runtime
autonomous loop
patch application
public release material
live_executor_authority change
safe default change
store.py mutation
```

This phase also does not claim physical impossibility, tamper-proof storage,
live readiness, write safety, or arbitrary-code safety.

Main merge:

```text
main merge = NOT_PERFORMED
```
