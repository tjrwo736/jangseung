# Aegis Phase 11-C-0 PreToolUse Hook Governance Direction Lock v0

## Purpose

This document locks the Phase 11-C direction pivot from direct
provider/model/network execution toward PreToolUse-style substrate hook
governance.

Canonical positioning:

```text
Aegis = PreToolUse hook-backed evidence-first governance harness for coding-agent tool calls
```

Technical positioning:

```text
Aegis is a PreToolUse hook-backed governance harness that treats AI tool calls as untrusted input, maps them into structured actions, applies capability/risk gates, records evidence, and returns deterministic allow/deny/ask/defer decisions.
Aegis는 AI tool call을 신뢰하지 않는 입력으로 보고, structured action으로 변환한 뒤, capability/risk gate와 evidence/verify를 통해 allow/deny/ask/defer를 결정하는 PreToolUse hook-backed governance harness입니다.
```

This is a docs-only direction lock. It does not implement provider,
model, network, hook command, hook installation, Claude Code execution, Codex
hook behavior, action execution, write authority, tool runtime, store routing,
patch application, public release material, or autonomous loop behavior.

Completion label:

```text
PHASE11C_0_PRETOOLUSE_HOOK_GOVERNANCE_DIRECTION_LOCK_COMPLETE_NOT_HOOK_RUNTIME
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Current Status

Required Phase 11-C-0 status:

```text
direction pivot = accepted in substance
Phase 11-C = OPEN
11-C-0 = GO_DOCS_ONLY_DIRECTION_LOCK
Phase 11-C = SUBSTRATE_HOOK_GOVERNANCE_LINE_STARTED_AS_DIRECTION_LOCK
Aegis role = PRETOOLUSE_HOOK_BACKED_GOVERNANCE_LAYER
Claude Code PreToolUse = PRIMARY_SUBSTRATE_TARGET
Claude Code hook target = PRIMARY_SUBSTRATE_TARGET
direct provider line = PARKED
Codex hook target = FUTURE_SUBSTRATE_TARGET_PENDING_COVERAGE_VERIFICATION
provider direct target = PARKED / FUTURE_OPTIONAL
provider/model/network = NOT_STARTED / NOT_GRANTED
direct provider/model/network implementation = PARKED
actual provider adapter = NOT_STARTED
API key/env/secret loading = NOT_STARTED
network client = NOT_STARTED
provider response parser = NOT_STARTED
hook runtime implementation = NOT_STARTED
hook installation = NOT_STARTED
actual Claude Code execution = NOT_STARTED
Codex hook implementation = NOT_STARTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
patch application = NOT_STARTED
public release = NOT_STARTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Historical baseline status:

```text
Phase 11-B-4 pre-provider baseline = ACCEPTED_AS_HISTORICAL_PRE_PROVIDER_BASELINE
PR #100 = ACCEPTED / MERGED
current main SHA = d004e02f01852b59ac6ae9137a8200f6e6b81c7b
provider/model/network = NOT_STARTED / NOT_GRANTED
actual provider adapter = NOT_STARTED
API key/env/secret loading = NOT_STARTED
network client = NOT_STARTED
provider response parser = NOT_STARTED
action execution engine = NOT_STARTED
write authority = NOT_GRANTED
tool runtime = NOT_STARTED / NOT_GRANTED
store routing = NOT_GRANTED
patch application = NOT_STARTED
autonomous loop = NOT_STARTED
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

Main merge:

```text
main merge = NOT_PERFORMED
```

## Decision

Aegis will not directly call provider/model/network by default.

Aegis will target PreToolUse-style substrate hooks. In this line, the
substrate calls the model and emits tool call intent. Aegis receives the hook
input, treats it as untrusted raw executor output, maps it into a structured
action candidate, runs classify/capability gate/law/evidence/verify, and
returns a hook decision.

Claude Code is the primary substrate target.

Codex is a future and partial target pending coverage verification.

The direct provider line is parked. A future direct provider adapter remains
optional, lower priority, and separate from Phase 11-C hook governance.

The Phase 11-B-4 pre-provider baseline remains accepted as a historical
pre-provider baseline. It is not discarded.

## Rationale

The hook governance line is preferred because it lowers install friction and
does not require a separate Aegis API key or environment setup for provider
access.

Provider selection, provider authentication, network transport, and model
execution are handled by the substrate. Aegis can focus on governance,
evidence, and verification.

This aligns Aegis with real Claude Code and Codex users by making Aegis a
harness behind existing coding agents rather than another model/provider
runner.

This also avoids putting provider secret handling, provider network behavior,
prompt construction, raw prompt retention, and raw provider response retention
burden into Aegis core by default.

## Existing 11-B Assets Reused

Existing 11-B core remains useful. The executor output source changes from
provider output to hook input.

Reuse map:

```text
executor_output_ingress
  old source: provider output candidate
  new source: hook input candidate
  reused as: raw executor output ingress boundary

structured_actions
  old source: parsed provider output candidate
  new source: mapped hook tool call candidate
  reused as: normalized action representation

structured_action_capabilities
  old source: provider-originated candidate capability evaluation
  new source: hook-originated tool call capability evaluation
  reused as: capability gate and non-grant policy surface

action_decision_routing
  old source: provider candidate decision routing
  new source: hook candidate decision routing
  reused as: deterministic routing and stop/hold behavior

proposal evidence
  old source: proposal evidence for restricted executor output
  new source: proposal evidence for hook-derived structured action
  reused as: evidence binding for non-executing governance decisions

runtime-built decision packet
  old source: runtime-built packet from validated candidate
  new source: runtime-built packet from validated hook candidate
  reused as: trusted runtime packet construction, never substrate-owned

store mediation evidence layer
  old source: store-adjacent evidence for mediated write boundaries
  new source: hook decision evidence and later hook binding evidence
  reused as: evidence layer, not authority grant

verify overclaim rejection
  old source: reject provider/runtime overclaims
  new source: reject substrate/hook/report overclaims
  reused as: deterministic overclaim rejection

.aeg state / ledger
  old source: local Aegis state and ledger records
  new source: future hook governance evidence records only after separate gate
  reused as: state/ledger concept, not executor-isolated proof by itself

safe default
  old source: hold_current_state
  new source: hold_current_state
  reused as: fail-closed default

law/gate model
  old source: provider candidate law/gate evaluation
  new source: hook candidate law/gate evaluation
  reused as: deterministic governance gate

NOT_CHECKED != PASS
  old source: pre-provider verification discipline
  new source: hook coverage and substrate coverage verification discipline
  reused as: no unchecked coverage promotion

reported_only != judgment basis
  old source: provider/report claims cannot decide
  new source: substrate/report claims cannot decide
  reused as: deterministic evidence requirement
```

The useful 11-B invariant is preserved:

```text
raw executor output
-> executor_output_ingress
-> parse/normalize/map
-> structured action
-> capability gate
-> law/gate
-> evidence
-> verify
-> runtime-built decision packet
-> stop/hold or hook decision
```

## New Input Boundary

Old boundary:

```text
provider output -> Aegis ingress
```

New boundary:

```text
hook input(tool_name, tool_input, tool_use_id, optional metadata) -> Aegis hook ingress
```

Hook input must be treated as untrusted raw executor output.

Required hook input fields:

```text
tool_name
tool_input
tool_use_id
```

Optional metadata:

```text
cwd
session id
transcript path
substrate name/version
project root
timestamp
```

The substrate owns model execution. Aegis does not trust substrate claims about
safety, coverage, permissions, read/write status, command effects, or
verification. Hook input is candidate material only.

## Context Ingestion Boundary Limitation

This direction lock does not claim universal prompt-injection prevention.
Aegis governs tool-call execution boundaries.

Required boundary statements:

```text
Aegis does not claim universal prompt-injection prevention.
Aegis governs tool-call execution boundaries.
PreToolUse hook is a tool-call boundary, not a universal context boundary.
Context that enters the model without a tool call, including @ file references or substrate-level prompt context insertion, is outside the initial PreToolUse governance boundary.
@ file reference / prompt context insertion may not trigger Read tool calls.
Hidden instructions inside files referenced as context can enter the model without passing through Aegis PreToolUse governance.
This is not a minor caveat; it is a core injection-defense limitation.
```

Future required work, not implemented in Phase 11-C-0:

```text
Read deny rule
context-ingestion policy
prompt context provenance
@ reference coverage measurement
```

## New Output Boundary

New output boundary:

```text
Aegis decision -> substrate hook response
```

Generic decision options:

```text
allow
deny
ask
defer
```

Substrate-specific response mapping is future work. Phase 11-C-0 records only
the conceptual output boundary and generic decision vocabulary.

## Claude Code Primary Target

Claude Code hook target:

```text
Claude Code hook target = PRIMARY_SUBSTRATE_TARGET
```

Current target assumptions:

```text
PreToolUse hook receives tool call information before execution.
PreToolUse hook input includes tool_name / tool_input / tool_use_id.
permissionDecision can deny / ask / defer / allow or equivalent.
deny prevents the tool call.
defer can be used for approval/resume style flows in supported mode.
This is a tool-call boundary, not a universal context boundary.
PreToolUse does not cover non-tool prompt context insertion such as @ file references.
Read/path deny rules may be needed for prompt-context file access.
Hook coverage must be measured.
Do not assume total coverage.
```

Initial target tools:

```text
Bash
Write
Edit
Read
```

Known caveats:

```text
PreToolUse is tool-call scoped.
@ file references may bypass tool hook because no Read tool call fires.
hook decision mapping must be measured with actual Claude Code reproduction.
dangerously-skip-permissions interaction must be measured, not assumed.
hook install location / project-local vs user-local settings must be documented later.
```

This direction lock does not perform actual Claude Code execution and does not
install a Claude Code hook.

## Subprocess Boundary Limitation

Aegis PreToolUse governance catches the tool call before execution. It does not
govern every action performed by a subprocess after the tool call is allowed.

Required boundary statements:

```text
Aegis PreToolUse governance catches the tool call before execution.
It does not govern every action performed by a subprocess after the tool call is allowed.
Bash("python script.py") is governed as a Bash tool call.
Once that Bash command is allowed, behavior inside script.py is outside the PreToolUse hook boundary unless separately sandboxed or instrumented.
Tool call governance != subprocess behavior governance.
Bash deny/allow decision != sandbox.
PreToolUse hook != process/OS isolation.
Allowed Bash command != all child-process actions verified.
```

Initial conservative Bash policy:

```text
dangerous Bash = deny or defer
unknown Bash = deny or defer
NOT_CHECKED Bash = deny or defer
```

Forbidden subprocess overclaims:

```text
Aegis does not claim to prevent all effects of scripts launched by allowed Bash.
Aegis does not provide sandbox/process isolation in Phase 11-C-0.
Aegis does not make Bash safe.
```

## Codex Future Target

Codex hook status:

```text
Codex hook target = FUTURE / PARTIAL / NOT_CANONICAL_UNTIL_VERIFIED
Codex hook target = FUTURE_SUBSTRATE_TARGET_PENDING_COVERAGE_VERIFICATION
Codex hook implementation = NOT_STARTED
```

Codex may become a substrate target after coverage is verified. Bash coverage
may be the first target if verified.

File edit coverage, apply_patch coverage, and MCP coverage must be separately
verified. This document does not claim Codex full coverage.

## Provider Line Status

Phase 11-B-4 pre-provider baseline remains accepted.

Provider line status:

```text
Phase 11-B-4 pre-provider baseline = ACCEPTED_AS_HISTORICAL_PRE_PROVIDER_BASELINE
direct provider implementation = PARKED
direct provider/model/network implementation = PARKED
provider direct target = PARKED / FUTURE_OPTIONAL
future provider adapter = optional / lower priority
provider policy gate = PARKED until needed
actual provider adapter = NOT_STARTED
API key/env/secret loading = NOT_STARTED
network client = NOT_STARTED
provider response parser = NOT_STARTED
```

No API key, environment, secret, provider SDK, network client, prompt builder,
or provider response parser work is authorized now.

New priority:

```text
hook governance adapter first
provider direct adapter later, if ever
```

## Initial Hook Governance Mapping Direction

This is an initial conceptual mapping only. It is not implementation.

```text
Write(file_path, content)
  -> structured write candidate / risk by path

Edit(file_path, old_string, new_string)
  -> patch-like candidate / risk by path

Bash(command)
  -> run-command candidate / HIGH or DENY depending command

Read(file_path)
  -> read candidate / limited unless protected/secret path

Bash(git push/deploy/rm -rf/curl/env)
  -> HIGH / DENY / USER_GATE

Write/Edit targeting .aeg/.env/secrets/protected paths
  -> DENY or HIGH_USER_GATE
```

## Initial Hook Decision Policy

This is policy direction only. It is not hook runtime implementation.

```text
unknown = deny or defer
unsupported substrate = NOT_CHECKED
NOT_CHECKED != PASS
no hook coverage != allow
reported_only != judgment basis
provider/model output cannot override deterministic STOP
safe default = hold_current_state
```

Additional guard statements:

```text
hook input is not trusted runtime state
hook input is not a capability grant
hook input is not a verification result
hook coverage report is not coverage proof
substrate permission status is not Aegis authority
provider/model/network output is not Aegis authority
```

Initial conservative Bash handling:

```text
dangerous Bash = deny or defer
unknown Bash = deny or defer
NOT_CHECKED Bash = deny or defer
```

## Non-Goals

Phase 11-C-0 does not implement or authorize:

```text
no provider/model/network implementation
no OpenAI/Ollama/LLM call
no API key/env/secret loading
no hook command implementation
no .claude/settings.json mutation
no actual hook installation
no actual Claude Code execution
no Codex implementation
no action execution engine
no write authority
no store.py change
no runtime filesystem mutation
no filesystem mutation by hook runtime or action execution
no patch application
no public release material
no main direct push
```

Forbidden scope not implemented or claimed:

```text
provider/model/network implementation
OpenAI/Ollama/LLM call
API key/env/secret loading
provider SDK import
network client implementation
prompt builder implementation
provider response parser implementation
hook command implementation
.claude/settings.json modification
actual hook installation
actual Claude Code execution
Codex implementation
action execution engine
write authority grant
tool runtime
store.py change
runtime filesystem mutation
patch application
public release material
live_executor_authority change
safe default change
direct main push
universal prompt-injection prevention claim
sandbox/process isolation claim
Bash-safe claim
bypass-impossible claim
tamper-proof claim
live-ready claim
write-safe claim
arbitrary-code-safe claim
```

## Future 11-C Sequence

Proposed Phase 11-C sequence:

```text
11-C-0 Hook Governance Direction Lock
11-C-1 Claude Code PreToolUse Input Contract
11-C-2 Tool Call to Structured Action Mapping
11-C-3 Hook Decision Adapter
11-C-4 Hook Evidence Binding
11-C-5 Claude Code Hook Install Contract
11-C-6 Claude Code Hook Reproduction Harness
11-C-7 Phase 11-C Completion Baseline
```

Each future phase must preserve the safe default unless separately and
explicitly changed by a later gate.

## Public Positioning

This section splits public positioning into user-facing and technical layers.
It is positioning text only. It is not public release material.

User-facing positioning:

```text
Aegis helps Claude Code stop risky actions before they run, records what the AI tried to do, and blocks dangerous tool calls from becoming trusted truth.
Aegis는 Claude Code가 위험한 작업을 실행하기 전에 멈추고, AI가 무엇을 하려 했는지 기록하며, 위험한 tool call이 신뢰된 사실이 되는 것을 막습니다.
```

User-facing values:

```text
1. Claude Code가 위험한 걸 하기 전에 잡아준다.
2. AI가 무엇을 하려 했는지 evidence로 남긴다.
3. 외부 코드/instruction injection이 위험한 tool call로 이어지는 것을 tool-call boundary에서 막는다.
```

Boundary qualifier for the third value:

```text
tool-call boundary에서 막는다.
모든 prompt/context injection을 전부 막는다는 뜻은 아니다.
```

Technical positioning:

```text
Aegis is a PreToolUse hook-backed governance harness that treats AI tool calls as untrusted input, maps them into structured actions, applies capability/risk gates, records evidence, and returns deterministic allow/deny/ask/defer decisions.
Aegis는 AI tool call을 신뢰하지 않는 입력으로 보고, structured action으로 변환한 뒤, capability/risk gate와 evidence/verify를 통해 allow/deny/ask/defer를 결정하는 PreToolUse hook-backed governance harness입니다.
```

## Transition Recommendation

Recommendation:

```text
hold current state
continue with 11-C-1 Claude Code PreToolUse Input Contract before implementation
measure Claude Code hook coverage before claiming enforcement coverage
keep Codex as future/partial until coverage is verified
keep direct provider/model/network implementation parked
do not add provider SDKs, network clients, credential loading, prompt construction, response parsing, hook commands, hook installation, action execution, write authority, store routing, patch application, or public release material in Phase 11-C-0
```
