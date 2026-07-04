# Aegis Phase 11-B-1d Tool Injection / Escape Fixture Harness v0

## 1. Purpose

Phase 11-B-1d adds a deterministic fixture harness for adversarial structured
action data that tries to bypass the Phase 11-B-1b schema validator and the
Phase 11-B-1c capability gate.

The target claim is narrow:

```text
schema-valid-looking action data must not bypass the capability gate
```

Implementation:

```text
src/evidence/structured_action_injection_fixtures.py
tests/test_phase11b_tool_injection_escape_fixtures.py
```

The harness evaluates fixture data only. It does not execute actions.

## 2. Relationship to 11-B-1a / 11-B-1b / 11-B-1c

Phase roles remain distinct:

```text
11-B-1a = structured executor capability model design
11-B-1b = structured action shape and schema validation
11-B-1c = structured action capability authorization gate
11-B-1d = injection and escape fixtures against 11-B-1b plus 11-B-1c
```

Non-equivalences preserved by this phase:

```text
valid schema != authorized capability
authorized capability != action executed
fixture rejected != runtime executor safe
fixture coverage != proof that no bypass exists
```

11-B-0 remains `NOT_COMPLETE`. Live executor authority remains
`LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.

## 3. Fixture threat model

The harness fixes representative adversarial action candidates as deterministic
fixtures:

- executable payload injection.
- nested executable field injection.
- executable alias and synonym injection.
- path escape and protected target requests.
- self-reported capability and authority smuggling.
- action type confusion.

Fixtures are static in-memory mappings. There is no random fuzzing, dynamic
payload generation, model call, provider call, network call, shell runner,
process spawn, filesystem mutation, or action dispatch.

## 4. Executable payload injection

The fixture set covers executable-looking payload fields such as:

```text
python_code
eval_code
exec_code
import_path
module
function_name
callback
callable_reference
shell_command
command
args = ["python", "-c", "..."]
```

Expected result: `EXECUTABLE_PAYLOAD_REJECTED`.

These are rejected as structured action data before any action execution path
could be considered.

## 5. Nested/alias injection

Nested executable fixtures include:

```text
payload.metadata.python_code
payload.options.shell_command
payload.patch_plan.steps[].command
payload.extras.import_module
payload.context.eval
```

Alias fixtures include representative tool and command synonyms:

```text
cmd
command_line
terminal
bash
powershell
subprocess
spawn
proc
module_name
plugin
hook
callback_url
```

Expected results:

```text
NESTED_EXECUTABLE_PAYLOAD_REJECTED
ALIAS_EXECUTABLE_PAYLOAD_REJECTED
```

The alias list is intentionally representative rather than exhaustive.

## 6. Path escape

Path escape fixtures cover:

```text
.aeg/...
../.aeg/...
/absolute/path
../../outside-repo
.env
secrets.json
```

Expected results:

```text
PATH_ESCAPE_REJECTED
AEG_SCOPE_ESCAPE_REJECTED
ENV_SECRET_ACCESS_REJECTED
```

The symlink-to-`.aeg` case is classified as
`SYMLINK_ESCAPE_FUTURE_FIXTURE` because this phase does not create symlinks or
perform realpath-based filesystem checks.

## 7. Capability smuggling

Capability smuggling fixtures cover self-reported grant or authority fields:

```text
capability_granted = true
authority = write_file
trusted = true
approved_by_executor = true
safe = true
write_authority_granted = true
execution_allowed = true
mutation_allowed = true
live_executor_ready = true
grant_source = reported_only
```

Expected results:

```text
CAPABILITY_SMUGGLING_REJECTED
REPORTED_ONLY_AUTHORITY_REJECTED
REPORTED_ONLY_CAPABILITY_GRANT_REJECTED
```

Executor self-report remains data, not authority.

## 8. Action type confusion

Action type confusion fixtures cover:

```text
PROPOSE_PATCH payload requests direct write
REQUEST_REPO_READ payload targets .aeg
REQUEST_EXPLANATION payload contains shell command
NOOP payload contains hidden action
```

Expected result: `ACTION_TYPE_CONFUSION_REJECTED`.

An allowed action type cannot borrow authority from hidden payload semantics.

## 9. PROPOSE_PATCH data-vs-execution distinction

`PROPOSE_PATCH` remains a patch proposal data type. The fixture harness
preserves this distinction:

```text
patch_diff as data is allowed
patch_plan as data is allowed
patch content as data is not code execution
patch proposal is not mutation
patch proposal is not write authority
```

Forbidden `PROPOSE_PATCH` variants include:

```text
patch metadata that requests shell, run, import, eval, or exec behavior
patch target under .aeg
patch target under .env or secret paths
patch target outside allowed repo scope
patch payload that claims write authority
```

## 10. Expected rejection states

The harness uses these rejection and classification states:

```text
TOOL_INJECTION_REJECTED
EXECUTABLE_PAYLOAD_REJECTED
NESTED_EXECUTABLE_PAYLOAD_REJECTED
ALIAS_EXECUTABLE_PAYLOAD_REJECTED
PATH_ESCAPE_REJECTED
AEG_SCOPE_ESCAPE_REJECTED
ENV_SECRET_ACCESS_REJECTED
CAPABILITY_SMUGGLING_REJECTED
ACTION_TYPE_CONFUSION_REJECTED
REPORTED_ONLY_AUTHORITY_REJECTED
SYMLINK_ESCAPE_FUTURE_FIXTURE
```

`SYMLINK_ESCAPE_FUTURE_FIXTURE` is a classification state, not a runtime
denial claim.

## 11. Non-execution guarantee

The harness calls only:

```text
validate_structured_action
evaluate_action_capabilities
```

The result flags remain:

```text
execution_allowed = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

This is a fixture-level non-execution guarantee. It is not a runtime sandbox
claim and not a live executor readiness claim.

## 12. Non-mutation guarantee

The harness operates on in-memory fixture dictionaries and result objects. It
does not write files, create symlinks, mutate `.aeg`, update `.env`, or apply
patches.

The result flags remain:

```text
mutation_allowed = false
write_authority_granted = false
```

`PROPOSE_PATCH` control data may pass the gate as non-executing,
non-mutating proposal data.

## 13. Evidence / verify direction

`build_tool_injection_fixture_summary()` records:

```text
tool_injection_fixture_set_version
tool_injection_fixtures_evaluated
tool_injection_rejected_count
tool_injection_allowed_count = 0
escape_fixture_rejected_count
escape_fixture_allowed_count = 0
future_fixture_count
capability_smuggling_rejected
action_type_confusion_rejected
execution_allowed = false
mutation_allowed = false
write_authority_granted = false
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

`verify_tool_injection_fixture_summary()` rejects pass-like summaries that
claim allowed adversarial fixtures, enabled execution, enabled mutation,
write authority, live executor readiness, or physical impossibility of bypass.

This is local summary verification only. Broader evidence-store binding can be
done in a later closure phase if needed.

## 14. Relationship to PR #81

PR #81 remains outside this phase:

```text
status = HOLD / OPEN / draft
draft release = NOT_PERFORMED
merge = NOT_PERFORMED
```

Phase 11-B-1d does not release, merge, modify, or depend on PR #81.

## 15. Explicit non-goals

Phase 11-B-1d does not implement or authorize:

- live executor runtime.
- actual executor action execution engine.
- provider, model, OpenAI, Ollama, LLM, or network contact.
- raw shell authority.
- generic write-file authority.
- run-command authority.
- process spawn.
- arbitrary Python execution.
- eval, exec, or dynamic import execution paths.
- filesystem mutation.
- store sink guard strengthening.
- process, OS, sandbox, container, or IPC isolation.
- PR #81 draft release.
- PR #81 merge.
- main direct push.

## 16. Safe default

The safe default remains:

```text
safe_default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

Fixture rejection is a pre-execution schema and capability-gate result. It does
not change live executor authority.
