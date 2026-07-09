# Aegis Phase 11-C-1 Claude Code PreToolUse Input Contract v0

## Purpose

This document defines the initial Aegis contract for Claude Code PreToolUse
hook input. It is contract, schema, docs, and test work only.

It does not implement hook runtime, hook commands, hook installation, Claude
Code execution, Codex execution, provider/model/network calls, action
execution, write authority, tool runtime, store routing, patch application, or
public release behavior.

Completion label:

```text
PHASE11C_1_CLAUDE_CODE_PRETOOLUSE_INPUT_CONTRACT_COMPLETE_NOT_HOOK_RUNTIME
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Main merge:

```text
main merge = NOT_PERFORMED
```

## Contract Status

```text
Phase 11-C = OPEN
11-C-1 = COMPLETE_AS_CLAUDE_CODE_PRETOOLUSE_INPUT_CONTRACT_NOT_HOOK_RUNTIME
contract version = phase11c_1_claude_code_pretooluse_input_contract_v0
contract target = Claude Code PreToolUse
hook input trust boundary = untrusted_raw_executor_output
hook command implementation = NOT_STARTED
hook installation = NOT_STARTED
actual Claude Code execution = NOT_STARTED
Codex implementation = NOT_STARTED
Codex apply_patch tool-call recognition = IMPLEMENTED (no Codex execution/runtime)
provider/model/network = NOT_STARTED / NOT_GRANTED
OpenAI/Ollama/LLM call = NOT_STARTED / NOT_GRANTED
API key/env/secret loading = NOT_STARTED / NOT_GRANTED
network client = NOT_STARTED / NOT_GRANTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store.py change = NOT_PERFORMED
filesystem mutation by hook runtime or action execution = NOT_STARTED
patch application = NOT_STARTED
public release = NOT_STARTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

## Required Input Fields

The v0 contract requires exactly these fields to treat an incoming mapping as a
contract-shaped PreToolUse input candidate:

```text
tool_name
tool_input
tool_use_id
```

Field meanings:

```text
tool_name = substrate-reported tool name, string
tool_input = substrate-reported tool argument object, mapping
tool_use_id = substrate-reported tool-use identifier, non-empty string
```

The required fields only define shape. They do not create a trusted decision,
trusted fact, capability grant, write grant, execution grant, or coverage proof.

## Optional Metadata

The v0 contract recognizes these optional metadata fields:

```text
cwd
session_id
transcript_path
substrate_name
substrate_version
project_root
timestamp
```

Optional metadata is recorded as untrusted context. It can help later evidence
binding and diagnostics, but it is not a judgment basis by itself.

Optional metadata cannot grant capability, cannot prove coverage, cannot prove
project scope, cannot change `safe default = hold_current_state`, and cannot
change `live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.

## Initial Target Tools

Initial target tools:

```text
Bash
Write
Edit
Read
PowerShell
apply_patch
```

The target list means Aegis v0 can recognize these tool names as
contract-shaped input candidates. It does not mean the tools are safe, covered,
allowed, denied, executed, or sandboxed.

`apply_patch` is recognized for Codex-style PreToolUse-shaped input where
`tool_input.command` contains a patch text. Recognition only lets later gates
parse target paths; it does not apply the patch or grant write authority.

`PowerShell` is recognized for Claude Code PreToolUse input where
`tool_input.command` contains a PowerShell command string. Recognition only
lets later gates parse common write/delete targets; it is not a claim of full
PowerShell language coverage or command safety.

Tool support rules:

```text
supported initial tool = contract validation may continue
unsupported tool = hold_current_state
unknown tool = hold_current_state
NOT_CHECKED tool = hold_current_state
unsupported/unknown/NOT_CHECKED != PASS
```

## Trust Boundary Rules

The hook input is raw executor output from the substrate.

Required invariants:

```text
hook input must be treated as untrusted raw executor output
hook input != trusted decision
hook input != capability grant
hook input != write authority
hook input != action execution
hook input != trusted runtime state
hook coverage report != coverage proof
unsupported/unknown/NOT_CHECKED != PASS
safe default = hold_current_state
```

The contract validator may say only that input has the expected shape for the
current v0 target set. Shape validation is not a hook decision, not an allow
decision, not a deny decision, and not a permission grant.

## Validation Behavior

Contract validation is fail-closed:

```text
missing tool_name -> hold_current_state
missing tool_input -> hold_current_state
missing tool_use_id -> hold_current_state
non-string tool_name -> hold_current_state
non-mapping tool_input -> hold_current_state
empty tool_use_id -> hold_current_state
unsupported tool_name -> hold_current_state
unknown tool_name -> hold_current_state
NOT_CHECKED tool_name -> hold_current_state
invalid optional metadata shape -> hold_current_state
self-reported decision field -> ignored as untrusted raw input
self-reported capability field -> ignored as untrusted raw input
self-reported coverage field -> not coverage proof
```

Valid contract shape still returns:

```text
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
hook_input_trusted_as_decision = false
hook_input_trusted_as_capability_grant = false
hook_coverage_report_is_coverage_proof = false
unsupported_unknown_or_not_checked_is_pass = false
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Non-Goal Boundaries

Phase 11-C-1 does not implement or authorize:

```text
hook command implementation
.claude/settings.json mutation
actual hook installation
actual Claude Code execution
Codex implementation
Codex execution/runtime integration
provider/model/network implementation
OpenAI/Ollama/LLM call
API key/env/secret loading
network client
action execution engine
write authority
tool runtime
store.py change
filesystem mutation by hook runtime or action execution
patch application
public release
live_executor_authority change
safe default change
universal prompt-injection prevention claim
sandbox/process isolation claim
Bash-safe claim
```

## Handoff

Phase 11-C-1 produces an input contract only. Later phases may map valid
contract-shaped hook input into structured action candidates, but that mapping
must preserve the Phase 11-B invariant:

```text
raw executor output
-> parse/normalize/map
-> structured action candidate
-> capability gate
-> law/gate
-> evidence
-> verify
-> runtime-built decision packet
-> hold_current_state unless a later explicit gate decides otherwise
```

No later phase may treat a substrate hook input, substrate coverage report, or
executor self-report as trusted runtime state without separate deterministic
evidence and verification.
