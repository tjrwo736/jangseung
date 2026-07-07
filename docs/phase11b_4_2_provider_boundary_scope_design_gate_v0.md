# Aegis Phase 11-B-4-2 Provider Boundary Scope Design Gate v0

## Purpose

Phase 11-B-4-2 defines the future provider boundary scope before any provider
adapter work is authorized. This is a design gate only. It does not implement a
provider, model call, network call, provider SDK path, API key loading,
environment secret loading, live response parsing, prompt construction, action
execution engine, tool runtime, write authority, patch application, or
autonomous loop.

Core principle:

```text
provider boundary scope = explicit user authorization first, no provider code, raw executor output only
```

Completion label:

```text
PHASE11B_4_2_PROVIDER_BOUNDARY_SCOPE_DESIGN_GATE_COMPLETE_NOT_PROVIDER
```

Required limits:

```text
NOT_PROVIDER_IMPLEMENTATION
NOT_MODEL_PROVIDER_INTEGRATION
NOT_PROVIDER_READY
NOT_NETWORK_ENABLED
NOT_API_KEY_LOADING
NOT_ENV_SECRET_LOADING
NOT_LIVE_PROVIDER_ADAPTER
NOT_ACTION_EXECUTION_ENGINE
NOT_WRITE_AUTHORITY
NOT_TOOL_RUNTIME
NOT_PATCH_APPLY
NOT_LIVE_EXECUTOR_READY
PROVIDER_GATE_REQUIRED
USER_AUTHORIZATION_REQUIRED
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
store routing = NOT_GRANTED
store path reachability = NOT_GRANTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Phase 11-B-4-2 does not change `live_executor_authority` and does not change
the safe default.

## Required Design Scope

1. Explicit user authorization is required before provider work

Provider implementation work requires a later explicit user and provider gate.
Phase 11-B-4-2 only records the boundary that must be satisfied before any
future provider adapter can be considered.

2. Provider and network remain not started and not granted

Provider, model, and network work remain:

```text
provider/model/network = NOT_STARTED / NOT_GRANTED
```

No provider selection, network path, SDK call, request client, credential
loading, prompt building, or live response handling is added by this phase.

3. Provider output is never trusted directly

Future provider output, if ever separately authorized, is untrusted external
material. It is not a judgment basis. Provider self-report about safety,
validation, authority, execution, file status, runtime ownership, or
verification cannot grant authority and cannot replace deterministic runtime
checks.

4. Provider output may only become raw executor output candidate material

A future provider adapter may only emit raw executor output candidate material.
It may not emit trusted runtime state, completed packet data, store-adjacent
candidate state, execution status, write status, or a capability grant.

5. Provider output must pass through executor_output_ingress

Any future provider-originated candidate must use the same downstream route as
all other raw executor output:

```text
provider output candidate
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

6. ActionDecisionPacket remains runtime-built only

`ActionDecisionPacket` creation remains owned by `executor_output_ingress`.
Provider-originated text, objects, metadata, or response fields cannot create or
own a trusted packet.

7. Provider cannot submit packet-shaped trusted material

Provider output cannot submit an `ActionDecisionPacket`, packet-shaped trusted
material, packet evidence-shaped material, or store-adjacent candidate-shaped
material. Such material must be treated as untrusted raw input and rejected or
failed closed by runtime-owned ingress rules.

8. Provider cannot access trusted runtime surfaces

A future provider adapter cannot access:

```text
store.py
trusted runtime context
runtime internals
filesystem mutation
shell/process surfaces
eval/exec/import execution path
tool runtime
```

No callable handles, store module handles, trusted context handles, runtime
internal handles, shell/process handles, filesystem mutation handles, or tool
schemas may be exposed to a provider boundary by this design.

9. Secret, environment, and API key loading policy is future-gated

Secret loading is not implemented.
Environment loading is not implemented.
API key loading is not implemented.

Any future policy must be separately approved before code can read provider
credentials, environment variables, `.env` data, tokens, or secret-like
deployment values.

10. Network opt-in policy is future-gated

Network opt-in is not implemented. A provider adapter, if ever approved, still
requires a separate explicit network policy before any outbound call can exist.
The presence of provider code, credentials, or configuration must not imply
network permission.

11. Prompt construction policy is future-gated

Prompt construction is not implemented. Future prompt construction must define
allowed inputs, excluded trusted runtime state, redaction requirements, and
retention behavior before any prompt-building code is added.

12. Raw prompt and raw response retention policy is future-gated

Raw prompt retention is not implemented.
Raw response retention is not implemented.

A later gate must explicitly decide whether raw content can be stored at all,
where it may be stored, and how tests prove sensitive content is not leaked.

13. Prompt and response redaction policy is future-gated

Prompt redaction is not implemented. Response redaction is not implemented.
Future redaction rules must be approved before prompt or response content can
enter evidence, logs, telemetry, manifests, stdout, stderr, or tracked files.

14. Provider error handling is secret-safe metadata only

Future provider errors must be represented as secret-safe metadata only. Error
records may include coarse classes and safe summaries, but must not include
credentials, tokens, raw prompts, raw responses, request bodies, response
bodies, private runtime values, or environment-derived secret content.

15. Provider telemetry and logging cannot leak sensitive content

Future telemetry and logging must not contain secret values, raw sensitive
content, raw prompts, raw responses, provider request bodies, provider response
bodies, private runtime values, or credential-like values. Logging must remain
metadata-only unless a later retention and redaction gate grants a narrower
policy.

16. Provider adapter remains separate from action execution

A provider adapter, if ever approved, is not an executor. It cannot execute
actions, apply patches, mutate files, spawn processes, call tools, grant write
authority, route to store, or change runtime authority.

17. Provider gate is not live executor readiness

Approving provider boundary scope does not make a live executor ready and does
not change `live_executor_authority`.

18. Provider gate is not write authority

Approving provider boundary scope does not grant write authority, mutation
authority, store routing, store path reachability, or patch application.

19. Provider gate is not tool runtime

Approving provider boundary scope does not enable tool schemas, tool calls,
function calling, shell/process access, filesystem mutation, or a tool runtime.

20. Provider gate is not an action execution engine

Approving provider boundary scope does not implement or authorize action
execution. Accepted future provider output would still be only raw executor
output candidate material unless a separate future action execution gate is
approved.

## Future Gate Separation

Required separation:

```text
11-B-4-2 = provider boundary scope design only
11-B-4-3 = actual provider adapter only after explicit user/provider gate
provider adapter still outputs raw executor output only
action execution/write/patch/tool runtime remains separate future gate
```

Phase 11-B-4-2 is not an implementation bridge. Passing this gate means only
that the future provider boundary is documented before provider adapter work
starts.

## Non-Equivalences

Required non-equivalences:

```text
provider output != trusted decision
provider output != authority grant
provider output != ActionDecisionPacket
provider output != store-adjacent candidate
provider output != tool call
provider output != shell/process request
provider output != filesystem mutation
provider output != direct store access
provider output != runtime internal access
provider gate != live executor ready
provider gate != write authority
provider gate != tool runtime
provider gate != action execution engine
```

## Forbidden Scope Not Implemented

This phase does not implement or authorize:

```text
actual provider/model/network call
provider SDK import
network client implementation
API key loading
environment secret loading
credential loading
live provider adapter
provider response parser for live calls
action execution engine
write authority grant
file mutation by executor output
shell/process/write_file/run_command/process_spawn authority
eval/exec/import execution path
tool runtime
store.py mutation
direct store access
runtime introspection/internal access implementation
patch application
autonomous loop
public release material
live_executor_authority change
safe default change
```

This phase makes no absolute safety or readiness claim beyond the documented
not-started and not-granted authority status.

Main merge:

```text
main merge = NOT_PERFORMED
```
