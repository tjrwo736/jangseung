# Aegis Phase 11-C-8 Hook Judgment Engine Alignment v0

Completion marker:

```text
PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_COMPLETE_NOT_INSTALLED_NOT_LIVE_RUNTIME
```

Safe default:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```

## Status

```text
Phase 11-C-8 = COMPLETE_AS_ENGINE_ALIGNMENT_CANDIDATE
actual hook install = NOT_PERFORMED
local install / live hook = HOLD
main merge = NOT_PERFORMED
write authority = NOT_GRANTED
public release = NOT_PERFORMED
```

This phase adds a thin, pure adapter from Claude Code PreToolUse tool-call data
to the existing Aegis judgment components. It does not implement a Claude Code
hook command, install a hook, emit stdout/stderr hook output, execute Claude
Code, call a provider/model/network, load API keys/env/secrets, bind an
evidence store, write `.aeg`, or grant write authority.

## Why Divergence Was Unsafe

Hook policy divergence was unsafe because a hook-local protected path list could
be weaker than the existing Aegis judgment engine. That created a path where
`Write` or `Edit` calls against protected files such as
`.github/workflows/ci.yml`, `Dockerfile`, `pyproject.toml`, `deploy/prod.yml`,
or `src/law/policy.py` could leak into an `ask` posture even when the existing
engine classified the target as protected/high-risk and capability/law gates
would deny or require a stronger hold.

hook policy divergence was unsafe.

The 11-C-8 rule is:

```text
existing engine reuse rule
hook policy must reuse existing Aegis judgment components
hook decision must match or be stricter than existing engine decision
hook-local protected path taxonomy = forbidden
protected path policy source = src.classify.is_protected_path
```

## Engine Reuse Points

The adapter records an engine decision basis from these existing components:

```text
src.classify.classify_task
src.classify.is_protected_path
src.law.apply_law
src.evidence.structured_action_capabilities.evaluate_action_capabilities
src.evidence.b1_aeg_integrity_guard.decide_b1_aeg_integrity_guard
src.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path
```

`src.classify` supplies risk and protected-path taxonomy. `src.law` supplies
the law gate. `structured_action_capabilities` supplies capability denial,
limited read scope, reported-only rejection, and write/run-command denial.
The existing `.aeg` guard and repo-boundary helpers supply state-dir and
outside-repo denial basis.

The hook adapter does not duplicate protected path lists. It records:

```text
protected_path_policy_duplicated_in_hook = false
hook_policy_divergence_allowed = false
reported_only_trusted_as_judgment_basis = false
not_checked_is_allow = false
```

## Decision Rule

The adapter collapses the engine basis to a hook decision candidate:

```text
engine deny -> hook deny
engine user gate / protected high risk -> hook deny
engine capability denied -> hook deny
engine outside repo / .aeg guard denial -> hook deny
engine clean read-only + limited capability accepted -> hook allow
NOT_CHECKED / unsupported / unknown without deny basis -> hook defer
```

This means the hook decision can be stricter than the engine decision, but not
weaker. A protected or denied engine basis must not become `ask` or `allow`.

## Protected Path Parity

The following paths are covered by classifier-owned protected path parity and
must not leak as `ask` for `Write` or `Edit`:

```text
.github/workflows/ci.yml -> deny
Dockerfile -> deny
pyproject.toml -> deny
deploy/prod.yml -> deny
src/law/policy.py -> deny
```

Additional existing gate coverage:

```text
Read .env -> deny via protected path and read scope gate
Write .aeg/state.json -> deny via capability gate and .aeg integrity guard
../outside.txt -> deny via repo-boundary gate
/absolute/path.txt -> deny via repo-boundary gate
normal low-risk Read -> allow only with clean law and limited read capability
normal low-risk Edit -> allow as clearly safe normal work; self-execution write capability remains denied
```

## Codex apply_patch Target-Aware Handling

`apply_patch` is a supported PreToolUse-shaped tool name. The adapter extracts
target paths from structural patch directives and then reuses the same existing
path gates as Write/Edit:

```text
apply_patch Update File: README.md -> allow when classified as normal non-protected in-repo work
apply_patch Update File: src/app.py -> allow when classified as normal non-protected in-repo work
apply_patch Add File: .env -> deny via protected path gate
apply_patch Add File: .github/workflows/x.yml -> deny via protected path gate
apply_patch Delete File: .env -> deny via protected path gate
apply_patch Update File: /etc/passwd -> deny via repo-boundary gate
apply_patch mixed normal + protected targets -> deny
apply_patch malformed/unparseable command -> deny fail-closed
```

The apply_patch denial basis is target-aware. A protected target denial must
show the protected/repo-boundary gate basis, not an unsupported-tool basis.
Patch application is not performed.

## Bash Safety Net

Dangerous Bash safety net:

dangerous Bash safety net.

```text
git reset --hard -> deny
git clean -fd -> deny
rm -rf -> deny
git push -> deny
deploy -> deny
curl/wget/env/printenv/chmod/chown/sudo -> deny
```

Unclassified Bash is not treated as safe:

```text
unclassified Bash = deny/defer, never allow
NOT_CHECKED Bash = deny/defer, never allow
Bash-safe claim = NOT_CLAIMED
```

The current adapter reaches `deny` for Bash through the existing
`run_command` capability denial. If a future engine changes Bash routing, the
floor remains deny/defer and never allow without a separate explicit gate.

## Reported-Only And NOT_CHECKED

Reported-only fields may be retained as ignored context, but they are not
judgment basis:

```text
reported_only != judgment basis
reported_only allow claim -> ignored
executor self-report -> not authority
NOT_CHECKED != allow
NOT_CHECKED != PASS
```

The hook decision record includes `engine_decision_basis`, and the basis source
list excludes reported-only/self-reported claims.

## @ File Reference Limitation

Aegis PreToolUse governance is a tool-call boundary, not a universal
prompt/context boundary. `@` file references may not trigger `Read` tool calls
and may be outside the initial PreToolUse boundary.

@ file references may not trigger Read tool calls.

Aegis does not claim universal prompt-injection prevention. 11-C-8 governs the
tool call records it receives; it does not guarantee that every prompt-context
file reference is mediated by a PreToolUse `Read` event.

## Evidence Store Binding Future Gate

Evidence store binding is future gate. Actual hook evidence store binding
requires separate gate store mediation must be used no direct .aeg write. Store
write binding and direct `.aeg` writes are not part of 11-C-8.

evidence store binding is future gate.

```text
store write binding = NOT_IMPLEMENTED
no direct .aeg write
evidence store executor-isolated binding = FUTURE_GATE
```

## Forbidden Scope

11-C-8 does not perform:

```text
.claude/settings.json mutation = NOT_PERFORMED
.claude/settings.local.json mutation = NOT_PERFORMED
actual hook install = NOT_PERFORMED
stdout/stderr live hook emission = NOT_PERFORMED
actual Claude Code execution = NOT_PERFORMED
provider/model/network = NOT_PERFORMED
API key/env/secret loading = NOT_PERFORMED
store write binding = NOT_PERFORMED
.aeg write = NOT_PERFORMED
write authority grant = NOT_PERFORMED
public release = NOT_PERFORMED
main direct push = NOT_PERFORMED
```

## Handoff

11-D local install and live hook remain on hold:

```text
safe default = hold_current_state
live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
```
