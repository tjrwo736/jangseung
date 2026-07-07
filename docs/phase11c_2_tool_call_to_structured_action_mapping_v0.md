# Aegis Phase 11-C-2 Tool Call to Structured Action Mapping v0

## Purpose

This document defines the initial contract-only mapping from validated Claude
Code PreToolUse input into Aegis structured action candidates.

It is mapping, contract, docs, and test work only. It does not implement hook
runtime, hook commands, hook installation, Claude Code execution, Codex
execution, provider/model/network calls, action execution, write authority,
tool runtime, store routing, filesystem mutation by hook runtime or action
execution, patch application, or public release behavior.

Completion label:

```text
PHASE11C_2_TOOL_CALL_TO_STRUCTURED_ACTION_MAPPING_COMPLETE_NOT_HOOK_RUNTIME
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
11-C-2 = COMPLETE_AS_TOOL_CALL_TO_STRUCTURED_ACTION_MAPPING_NOT_HOOK_RUNTIME
contract version = phase11c_2_tool_call_to_structured_action_mapping_v0
input contract = phase11c_1_claude_code_pretooluse_input_contract_v0
hook input trust boundary = untrusted_raw_executor_output
mapping output = structured action candidate only
mapping output != execution
mapping output != permission decision
mapping output != hook response
mapping output != write authority
mapping output != patch application
hook command implementation = NOT_STARTED
hook installation = NOT_STARTED
actual Claude Code execution = NOT_STARTED
Codex implementation = NOT_STARTED
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

## Input

Phase 11-C-2 consumes only validated Phase 11-C-1 Claude Code PreToolUse input:

```text
tool_name
tool_input
tool_use_id
optional metadata
```

The hook input remains untrusted raw executor output. Shape validation from
11-C-1 is not a permission decision, not an authority grant, not coverage proof,
and not trusted runtime state.

The mapping preserves provenance:

```text
source_tool_name
source_tool_use_id
source_contract_version
trust_boundary = untrusted_raw_executor_output
optional metadata as untrusted context
```

`tool_use_id` is carried into both the candidate source field and the candidate
action id:

```text
source_tool_use_id = original tool_use_id
action_id = pretooluse:<tool_use_id>
```

## Supported Tool Mappings

Initial mapping targets:

```text
Read(file_path)
  -> READ_REPO candidate

Write(file_path, content)
  -> WRITE_FILE candidate

Edit(file_path, old_string, new_string)
  -> EDIT_FILE candidate

Bash(command)
  -> RUN_COMMAND candidate
```

These are candidate intents only. They do not execute, apply patches, write
files, read files, spawn processes, return hook decisions, or grant write
authority.

## Protected Path Handling

The mapping does not maintain a hook-local protected path taxonomy.
Repository protected path classification is delegated to:

```text
src.classify.is_protected_path
```

The only extra path checks here are boundary checks needed to keep the
candidate fail-closed before later engine gates:

```text
.aeg state dir target -> DENY_CANDIDATE
absolute path -> DENY_CANDIDATE
parent traversal path -> DENY_CANDIDATE
```

Normal repo path handling:

```text
Read normal repo path = READ_REPO candidate only, no authority
Write normal repo path = WRITE_FILE candidate only, no execution, no authority
Edit normal repo path = EDIT_FILE candidate only, no patch application, no authority
```

Protected path handling:

```text
.env target -> DENY_CANDIDATE
.env.* target -> DENY_CANDIDATE
.github/workflows/ci.yml -> DENY_CANDIDATE
Dockerfile -> DENY_CANDIDATE
pyproject.toml -> DENY_CANDIDATE
deploy/prod.yml -> DENY_CANDIDATE
src/law/policy.py -> DENY_CANDIDATE
.aeg state dir target -> DENY_CANDIDATE
absolute path -> DENY_CANDIDATE
parent traversal path -> DENY_CANDIDATE
```

`DENY_CANDIDATE` is a mapping posture, not a hook response and not a final
permission decision.

## Bash Handling

Dangerous Bash examples map to `RUN_COMMAND` with `DENY_CANDIDATE` posture:

```text
rm -rf
git reset --hard
git clean -fd
git push
deploy
curl
wget
env
printenv
chmod
chown
sudo
```

Unknown or not-checked Bash maps to `RUN_COMMAND` with
`HOLD_CURRENT_STATE_CANDIDATE` posture:

```text
unknown Bash = hold_current_state
NOT_CHECKED Bash = hold_current_state
unparsed Bash = hold_current_state
unsupported/unknown/NOT_CHECKED != PASS
```

Phase 11-C-2 does not claim Bash safety. A non-dangerous string match is still
not proof that a Bash command is safe.

## Unknown Tool Handling

Unknown, unsupported, or NOT_CHECKED tool names map to:

```text
HOLD_CURRENT_STATE candidate
safe default = hold_current_state
unsupported/unknown/NOT_CHECKED != PASS
```

## Required Invariants

Every Phase 11-C-2 mapping output preserves:

```text
mapping output is structured action candidate only
mapping output != execution
mapping output != permission decision
mapping output != hook response
mapping output != write authority
mapping output != patch application
mapping output preserves tool_use_id provenance
hook input remains untrusted raw executor output
unsupported/unknown/NOT_CHECKED != PASS
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
hook_response_produced = false
patch_application_performed = false
```

## Non-Goal Boundaries

Phase 11-C-2 does not implement or authorize:

```text
hook command implementation
.claude/settings.json mutation
actual hook installation
actual Claude Code execution
Codex implementation
provider/model/network implementation
OpenAI/Ollama/LLM call
API key/env/secret loading
network client
subprocess execution
shell execution
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

Phase 11-C-2 produces mapping candidates only:

```text
validated PreToolUse input
-> map as untrusted tool-call data
-> structured action candidate
-> hold_current_state unless a later explicit gate decides otherwise
```

Later phases may bind these candidates into capability/risk/law/evidence/verify
flows, but they must not treat this mapping as execution, authority, hook
response, or a final permission decision.
