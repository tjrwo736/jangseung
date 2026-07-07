# Aegis Phase 11-B-4-A Pre-provider AST Source Scan Guard v0

## Purpose

Phase 11-B-4-A adds a pre-provider source scan guard that parses Python AST
surfaces and reports executable/import surfaces before any provider gate exists.
It is a detection and provenance refresh step only.

This phase does not implement provider, model, network, OpenAI/Ollama/LLM, API
key, environment secret, credential, live provider adapter, prompt builder,
provider response parser, action execution, tool runtime, write authority, store
routing, patch application, or autonomous loop work.

Completion label:

```text
PHASE11B_4_A_PRE_PROVIDER_AST_SOURCE_SCAN_GUARD_COMPLETE_NOT_PROVIDER
```

Required status:

```text
provider/model/network implementation = NOT_STARTED / NOT_GRANTED
provider SDK import = NOT_ADDED
network client implementation = NOT_ADDED
API key/env/secret loading = NOT_ADDED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store routing = NOT_GRANTED
patch application = NOT_STARTED
autonomous loop = NOT_STARTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
main merge = NOT_PERFORMED
```

## Source Baseline

Provenance:

```text
repo = /mnt/d/Codex/Aegis
source_of_truth = GitHub metadata / merged main
current main SHA = d004e02f01852b59ac6ae9137a8200f6e6b81c7b
PR #100 merge commit = d004e02f01852b59ac6ae9137a8200f6e6b81c7b
PR #100 merged_at = 2026-07-07T03:11:47Z
stale local pre-merge snapshot SHA = 2cf5dfabdceb2ec038bdf7be932fb38b7d92bb4d
stale local pre-merge snapshot SHA != current main SHA
```

The stale local pre-merge snapshot SHA is recorded only as historical context.
It is not the current merged main SHA and is not the source of truth for this
refresh.

## Guard Scope

The guard reports structured findings with:

```text
finding_type
symbol
lineno
col_offset
reason
severity
source_surface
is_executable_surface
```

The guard detects AST import, call, attribute, and assignment surfaces for:

```text
provider/model SDK imports
network client imports and calls
dynamic import calls
API/env/secret loading surfaces
shell/process/eval/exec/compile surfaces
provider-context sensitive variable names
```

Documentation strings and forbidden-scope status text may mention OpenAI,
Ollama, LLM, API key, env, secret, and network as negative status text. Text-only
mentions are not executable/import surfaces and are not reported by this guard.

## Forbidden Scope Not Implemented

This phase does not implement or authorize:

```text
actual provider/model/network call
OpenAI/Ollama/LLM call
provider SDK import in runtime/source implementation
network client implementation
API key/env/secret loading
credential loading
prompt builder implementation
provider response parser implementation
provider error handling runtime implementation
action execution engine
write authority grant
tool runtime
store routing
patch application
autonomous loop
public release material
live_executor_authority change
safe default change
direct main push
```

Main merge for this Phase 11-B-4-A branch remains:

```text
main merge = NOT_PERFORMED
```
