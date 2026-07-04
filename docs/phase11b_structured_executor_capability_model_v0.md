# Aegis Phase 11-B-1 Structured Executor Capability Model Design Sketch v0

## 1. Purpose

Phase 11-B-1 defines the first design sketch for a structured executor
capability model.

This document is docs-only. It does not implement a live executor, connect a
provider or model, open network access, add raw shell authority, add a general
`write_file` tool, add a `run_command` tool, add process spawn authority, add
trusted-context guard code, or implement OS, filesystem, sandbox, container, or
IPC enforcement.

The core principle is:

```text
executor output = data, not code
```

Required executor rule:

```text
executor must output structured actions only
executor must not execute arbitrary Python code
executor cannot import Python modules
executor cannot eval/exec
executor cannot inspect memory
executor cannot call store.py sinks directly
executor cannot obtain trusted context/capability
executor can only request mediated structured actions
```

Current authority remains:

```text
11-B-0 = NOT_COMPLETE
11-B-0-b/c = NOT_READY_FOR_COMPLETION
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
safe default = hold_current_state
```

## 2. Why 11-B-1 Design Must Precede 11-B-0-b Completion

11-B-0-b sink guard work is not enough to complete the pre-live boundary if the
future executor is allowed to run arbitrary Python in the same process as Aegis
trusted code.

The reason is structural: same-process arbitrary Python can reach in-process
objects, modules, callbacks, monkeypatchable functions, and trusted context that
token secrecy alone cannot reliably protect. If the executor can execute
Python, hiding a trusted token or context object in memory is not a durable
prevention boundary.

Therefore 11-B-1 must define the executor capability model before 11-B-0-b can
be treated as completion-ready. The primary prevention requirement is not
"make trusted token secrecy perfect." The primary requirement is to ensure the
executor never receives an execution surface that can reach trusted token,
context, capability, store sinks, process state, imports, `eval`, `exec`, or
memory inspection.

11-B-0-b can still be valuable, but its role depends on the executor model:

- if the executor outputs structured actions only and cannot reach sinks
  directly, sink guard is defense-in-depth and a tamper-evident boundary.
- if the executor can run arbitrary same-process code and reach sinks directly,
  sink guard becomes more important but remains insufficient for prevention.

Completion of 11-B-0-b must not imply that a same-process arbitrary Python
executor is safe.

## 3. Current PR #81 Status

Read-only GitHub metadata checked on 2026-07-04:

| Field | Value |
| --- | --- |
| PR | `#81` |
| URL | `https://github.com/tjrwo736/aegis/pull/81` |
| Title | `Phase 11-B-0 store write mediation v0` |
| State | `OPEN` |
| Draft | `true` |
| Base | `main` |
| Head | `codex/phase11b-0-store-write-mediation-v0` |
| Merge state | `CLEAN` |

Required handling for this document:

```text
PR #81 = HOLD
PR #81 draft release = HOLD / NOT_PERFORMED
PR #81 merge = HOLD / NOT_PERFORMED
```

This 11-B-1 document does not release PR #81 from draft and does not merge PR
#81.

## 4. In-process Arbitrary Code Limitation

An executor that can run arbitrary Python inside the Aegis process cannot be
treated as an untrusted actor constrained by in-process secrets.

Same-process arbitrary Python can potentially:

- import modules that expose privileged behavior.
- call functions that were meant to be internal.
- inspect stack frames, globals, closures, module registries, and object
  references.
- monkeypatch guards, callbacks, or sink functions.
- trigger callbacks or hooks that execute trusted code.
- access environment variables or process-local configuration if exposed.
- call store or recorder paths with trusted-looking arguments.

For this reason:

```text
token secrecy != executor capability restriction
same-process trusted context != isolation boundary
arbitrary Python executor != acceptable live executor prerequisite
```

The 11-B-1 prevention model is to remove the arbitrary Python execution surface
from the executor. The executor submits data. A separate Aegis-controlled
mediator interprets and gates that data.

## 5. Executor Output Model: Data, Not Code

The executor output model is serialized structured data. It is not Python code,
shell code, a callback, an import path, a plugin reference, or an object handle.

Allowed output shape at this design level:

- an action request identifier.
- an action type from an allowlisted action vocabulary.
- structured arguments matching the future action schema.
- declared requested capability.
- target path or resource identifier when the action type needs one.
- explanation or rationale text.
- optional precondition metadata.

Denied output semantics:

- no executable Python source.
- no dynamic import target.
- no `eval` payload.
- no `exec` payload.
- no shell command.
- no function pointer.
- no object reference.
- no callback registration.
- no direct store sink call.
- no hidden executable semantics inside JSON fields.

Required distinction:

```text
structured action != safe by default
executor requests an action != executor executes Python
propose_patch != mutation
write_repo allowed != raw write_file allowed
```

Structured output only means the executor emitted data. Safety comes from the
mediator, capability gate, schema validation, path policy, and review policy
that decide whether that data may be acted on.

## 6. Structured Action Model

11-B-1 defines the model conceptually. It does not implement the runtime or the
final schema contract.

A future structured action should be interpreted as a request:

```text
executor -> structured action request -> mediator -> capability gate -> sink/tool
```

The executor does not call the sink or tool. The mediator may accept, reject,
rewrite, queue, or ask for user review before any mutation occurs.

Initial action classes:

| Action class | Meaning | Mutation status |
| --- | --- | --- |
| `read_repo` | Request bounded repository context. | Read-only when permitted. |
| `propose_patch` | Emit a patch proposal as reviewable data. | Not mutation by itself. |
| `request_write_repo` | Ask a mediator to apply an approved repo change. | Mutation only after mediation and gate approval. |
| `request_aeg_state_write` | Ask for an Aegis state write. | Denied by default for executor. |
| `read_aeg_state` | Ask for Aegis state context. | Limited or denied until a gate exists. |

The future schema contract must make capability names explicit and must avoid
ambiguous fields that can smuggle executable behavior. Free-form text can be
used for rationale, but it must not be treated as an instruction to execute
code.

## 7. Capability Taxonomy Mapping From B3

B3 provided the non-grant vocabulary for raw capability and worktree scope.
11-B-1 maps that vocabulary into executor-facing structured action capabilities.

| 11-B-1 capability | B3 / Phase 10 mapping | 11-B-1 interpretation |
| --- | --- | --- |
| `read_repo` | `capability_read_repo` | Bounded repo read context. Must exclude secrets and protected `.aeg/` state unless later gated. |
| `propose_patch` | structured proposal, not direct B3 mutation authority | Executor may produce patch data for review. This is not write authority. |
| `request_write_repo` | `capability_write_repo` with mediation requirement | Executor can only ask the mediator for a repo write. It does not receive raw write capability. |
| `request_aeg_state_write` | `capability_write_aeg_state` / `aeg_state_write_authority` | Denied for executor. Direct or indirect `.aeg/` writes collapse evidence into self-certification. |
| `read_aeg_state` | `capability_read_aeg_state` / `aeg_state_read_authority` | Sensitive read; limited or denied until a separate gate defines minimization. |
| `raw_shell` | `raw_shell_authority` / `capability_shell` | Denied. Shell-like authority can bypass structured mediation. |
| `process_spawn` | `process_spawn_authority` / `capability_process_spawn` | Denied. Child processes can recreate shell, network, secret, or filesystem bypasses. |
| `network` | `network_authority` / `capability_network` | Denied. Network is exfiltration-capable unless a future boundary exists. |
| `provider_model_call` | `provider_model_call_authority` / `capability_provider_call` | Denied until explicit provider, network, secret, and prompt/context gates exist. |
| `general_write_file` | `write_file_authority` / unmediated `write_file` | Denied. Repo writes must go through mediated structured actions, not raw file writes. |
| `run_command` | `run_command_authority` | Denied. Command execution is shell-equivalent for this pre-live model. |
| `env_read` | `env_read_authority` / `capability_env_read` | Denied unless explicitly scoped and redacted by a later gate. |
| `secret_read` | `secret_read_authority` / `capability_secret_read` | Denied. Secret read unlocks provider, network, remote write, and tamper paths. |

This mapping preserves the B3 distinction:

```text
NOT_GRANTED_BY_POLICY != EXTERNALLY_ENFORCED_DENIAL
INDIVIDUAL_CAPABILITY_FALSE != COMPOSITION_SAFE
STRUCTURED_TOOL_CALL != SAFE_CAPABILITY
```

## 8. Allowed / Denied / Future-gated Capability Matrix

Initial 11-B-1 defaults:

| Capability | Initial default | Notes |
| --- | --- | --- |
| `read_repo` | `LIMITED` | Only bounded repository reads through a future read broker or policy surface. Not broad filesystem read. |
| `propose_patch` | `ALLOWED_UNDER_POLICY` | Produces reviewable patch data. Does not mutate files. |
| `request_write_repo` | `MEDIATED_AND_GATED` | Executor may request, but the mediator decides. This is not raw `write_file`. |
| `request_aeg_state_write` | `DENIED` | Executor must not write `.aeg/` state, ledger, manifest, evidence, or recorder-owned data. |
| `read_aeg_state` | `LIMITED_OR_DENIED_UNTIL_GATED` | Sensitive because it can reveal evidence, run IDs, policy, and provenance. |
| `raw_shell` | `DENIED` | No shell authority. |
| `process_spawn` | `DENIED` | No child process, helper, interpreter, background job, or subprocess authority. |
| `network` | `DENIED` | No network access. |
| `provider_model_call` | `DENIED_UNTIL_EXPLICIT_GATE` | No OpenAI, Ollama, LLM, provider, or model call by this document. |
| `general_write_file` | `DENIED` | Generic write-file capability is not granted. |
| `run_command` | `DENIED` | No command runner. |
| `env_read` | `DENIED_UNLESS_EXPLICITLY_SCOPED` | No broad environment access; future scoped reads require secret-safe design. |
| `secret_read` | `DENIED` | No secret or token read authority. |

Capability matrix conclusions:

```text
write_repo allowed != raw write_file allowed
propose_patch != mutation
structured action != safe by default
executor requests an action != executor executes Python
```

`GRANTED` is not used for dangerous capabilities in this design sketch. Future
movement from `DENIED` or `MEDIATED_AND_GATED` requires a separate reviewed
contract and verification source.

## 9. Store / Sink / Trusted Context Access Model

The executor does not receive store, sink, trusted context, or capability
objects.

Required model:

```text
executor cannot call store.py sinks directly
executor cannot import store.py
executor cannot access in-process Python objects
executor cannot obtain trusted context/capability
executor can only submit structured action requests
```

The mediator is the only component that may decide whether a structured action
request maps to a store or sink operation. If a request is accepted, the
mediator must preserve the boundary between executor-authored data and
Aegis-trusted write authority.

Non-authorized routes:

- direct import of `store.py`.
- direct function call into store sinks.
- object reference passed to executor output.
- trusted token or capability embedded in executor context.
- dynamic callback that executes executor-chosen Python.
- tool object that exposes broad filesystem, process, provider, or environment
  behavior.

## 10. Tool-call Injection And Escape Risk Inventory

Structured action transport creates a new injection surface. It must be treated
as untrusted input.

Risk inventory:

| Risk | Why it matters |
| --- | --- |
| Tool argument code injection | A data field may be interpreted by a tool as code, query, template, shell, or Python. |
| Tool internally calls `eval`/`exec` | A structured request can become code execution inside the tool implementation. |
| Broad filesystem path exposure | A path argument may reveal or reach repo secrets, `.aeg/`, sibling worktrees, or outside-repo files. |
| Python object reference exposure | Passing objects, handles, or repr-based references can leak trusted capability. |
| Import/module access exposure | Allowing module names or import paths reintroduces arbitrary Python reachability. |
| Callback/hook executing code | Hook fields or plugin callbacks can become executor-controlled code paths. |
| Environment/secret access | Env and secret reads can unlock provider, network, remote write, or filesystem authority. |
| Path traversal into `.aeg` | `../`, absolute paths, platform separators, or path aliases can target evidence state. |
| Symlink escape | Allowed-looking paths can resolve into `.aeg/` or outside the repo. |
| Executable semantics hidden in JSON schema | Fields such as `handler`, `command`, `python`, `module`, `template`, or `script` can smuggle execution. |

The future fixture harness should test that tools reject executable semantics
even when the transport is valid JSON.

## 11. Relationship To 11-B-0-b Sink Guard

11-B-0-b sink guard should be reclassified based on the executor capability
model.

Case A:

```text
executor outputs structured actions only
executor cannot directly access store.py sinks
executor cannot import store.py
executor cannot execute arbitrary Python
```

In Case A:

```text
primary defense = executor capability restriction
11-B-0-b sink guard = defense-in-depth / tamper-evident boundary
```

The sink guard helps detect or reject unexpected trusted-context misuse, but it
is not the first prevention boundary. The first prevention boundary is that the
executor never receives arbitrary code, store access, trusted context, raw
write, raw shell, process, provider, network, env, or secret authority.

Case B:

```text
executor can access sinks directly
executor can import store.py
executor can execute arbitrary same-process Python
```

In Case B:

```text
sink guard becomes more important
sink guard is still not tamper-proof against arbitrary same-process code
Case B is not acceptable as live executor prerequisite
```

11-B-0-b must not be completed with a claim that it prevents arbitrary
same-process Python from bypassing in-process trusted context.

## 12. Relationship To Optional Process / OS Isolation

Process and OS isolation may still be valuable later, but they are not
implemented by 11-B-1.

Optional future isolation could include a separate OS user, process boundary,
filesystem permission policy, sandbox, container, IPC broker, seccomp-like
policy, network deny policy, or secret manager boundary. Those mechanisms could
provide stronger prevention evidence if configured and verified outside
executor control.

This document does not rely on those future mechanisms. 11-B-1 instead sets the
minimum design stance:

```text
do not give the executor arbitrary code execution
do not give the executor raw capability
do not give the executor trusted context
make executor output structured data only
mediate every requested action
```

If optional isolation is added later, it should strengthen the capability model
rather than replace it.

## 13. Explicit Non-goals

This document does not implement or authorize:

- live model executor implementation.
- OpenAI, Ollama, LLM, provider, model, or network calls.
- provider/model/network contact.
- raw shell authority.
- general `write_file` tool.
- `run_command` tool.
- process spawn.
- `eval`, `exec`, or `import` execution paths.
- arbitrary Python executor runtime.
- actual executor runtime implementation.
- trusted context guard strengthening implementation.
- process isolation implementation.
- OS/filesystem permission enforcement.
- sandbox, container, or IPC implementation.
- `.aeg/` permission hardening.
- main direct push.
- PR #81 draft release.
- PR #81 merge.

## 14. Recommended Next Sequence

Recommended 11-B-1 sequence:

| Step | Name | Purpose |
| --- | --- | --- |
| `11-B-1a` | Structured Executor Capability Model Design | Finalize the executor-as-data capability model. |
| `11-B-1b` | Structured Action Schema Contract | Define the machine-checkable action schema and deny executable fields. |
| `11-B-1c` | Capability Gate / Non-grant Enforcement for Executor Actions | Define and implement the gate that rejects non-granted capabilities. |
| `11-B-1d` | Tool Injection / Escape Fixture Harness | Add fixtures for tool argument injection, path escape, hidden executable semantics, and gate bypass attempts. |
| `11-B-1e` | 11-B-1 Completion Status Note | Summarize evidence-supported status without overclaiming live executor readiness. |

Recommended order:

```text
11-B-1a -> 11-B-1b -> 11-B-1c -> 11-B-1d -> 11-B-1e
```

Do not resume sink guard hardening as the next primary task until the executor
capability model and structured action contract are clear enough to prevent
Case B from becoming the live executor prerequisite.

## 15. Safe Default

The safe default remains:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PR #81 draft release = NOT_PERFORMED
PR #81 merge = NOT_PERFORMED
```

This document supports the draft-review state for 11-B-1 design. It does not
unlock live executor authority and does not complete 11-B-0-b/c.
